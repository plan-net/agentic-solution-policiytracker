"""LangWatch observability configuration."""

import json
import logging
import time
import uuid
from collections.abc import Callable
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


class LangWatchConfig:
    """LangWatch observability configuration manager."""

    def __init__(self) -> None:
        # Import settings lazily to avoid circular imports
        from src.config import settings

        self.enabled = settings.ENABLE_LANGWATCH
        self.api_key = settings.LANGWATCH_API_KEY
        self.endpoint = settings.LANGWATCH_ENDPOINT
        self.otlp_endpoint = (
            settings.LANGWATCH_OTLP_ENDPOINT
            or f"{settings.LANGWATCH_ENDPOINT}/api/otel/v1/traces"
        )
        self.enable_anthropic_instrumentation = settings.ENABLE_ANTHROPIC_INSTRUMENTATION
        self._initialized = False
        self._otel_provider_initialized = False
        self._anthropic_instrumented = False
        # Session collectors for accumulating data before sending to LangWatch
        self._session_collectors: dict[str, dict] = {}

    def get_session_collector(self, session_id: str) -> dict:
        """Get or create a session collector for accumulating observability data.

        Args:
            session_id: The session ID to get/create collector for

        Returns:
            Dict containing lists for turns, tool_calls, and summary data
        """
        if session_id not in self._session_collectors:
            self._session_collectors[session_id] = {
                "session_id": session_id,
                "turns": [],
                "tool_calls": [],
                "total_tokens": 0,
                "model": "",
                "user_query": "",
                "final_response": "",
            }
        return self._session_collectors[session_id]

    def set_session_query(self, session_id: str, query: str) -> None:
        """Set the user query for a session."""
        if session_id:
            collector = self.get_session_collector(session_id)
            collector["user_query"] = query

    def set_session_response(self, session_id: str, response: str) -> None:
        """Set the final response for a session."""
        if session_id:
            collector = self.get_session_collector(session_id)
            # Truncate response if too long
            max_len = 5000
            if len(response) > max_len:
                response = response[:max_len] + "...[truncated]"
            collector["final_response"] = response

    def finalize_session(self, session_id: str) -> dict:
        """Finalize and return session data, then clean up.

        Call this at the end of a traced function to get the full session data
        that should be sent to LangWatch.

        Args:
            session_id: The session ID to finalize

        Returns:
            Complete session data as a dict
        """
        if session_id and session_id in self._session_collectors:
            data = self._session_collectors.pop(session_id)
            logger.debug(f"Finalized session {session_id}: {len(data['turns'])} turns, {len(data['tool_calls'])} tool calls")
            return data
        return {}

    def _truncate_tool_calls_to_fit(self, tool_calls: list, target_size: int) -> list:
        """Truncate tool calls list to fit within target size.

        Keeps all tool calls but reduces the output size of each.
        Uses a minimum per-call budget to ensure entity/relationship data is preserved.
        """
        if not tool_calls:
            return tool_calls

        # Minimum 10KB per tool call to preserve entity/relationship data
        MIN_PER_CALL_BUDGET = 10000
        truncated = []
        per_call_limit = max(target_size // len(tool_calls), MIN_PER_CALL_BUDGET)

        for tc in tool_calls:
            truncated_tc = {
                "tool_name": tc.get("tool_name"),
                "tool_use_id": tc.get("tool_use_id"),
                "success": tc.get("success"),
                "execution_time_ms": tc.get("execution_time_ms"),
                "turn_number": tc.get("turn_number"),
                # Truncate input/output with minimum budget for output to preserve entities
                "input": self._smart_truncate_output(tc.get("input"), max_len=max(per_call_limit // 4, 2000)),
                "output": self._smart_truncate_output(tc.get("output"), max_len=max(per_call_limit // 2, 5000)),
            }
            truncated.append(truncated_tc)

        return truncated

    def send_trace_via_rest_api(self, session_data: dict) -> bool:
        """Send trace data directly to LangWatch REST API.

        This method bypasses the OTEL SDK and sends traces directly to the
        LangWatch collector endpoint which accepts properly formatted trace data.

        Includes payload size validation and will truncate data if needed.

        Args:
            session_data: The complete session data from finalize_session()

        Returns:
            True if trace was sent successfully, False otherwise
        """
        if not self.enabled or not self.api_key:
            return False

        if not session_data:
            logger.warning("No session data to send")
            return False

        session_id = session_data.get("session_id", "unknown")
        trace_id = uuid.uuid4().hex

        # Build structured output summary with all captured data
        output_summary = {
            "session_id": session_id,
            "total_turns": len(session_data.get("turns", [])),
            "total_tool_calls": len(session_data.get("tool_calls", [])),
            "total_tokens": session_data.get("total_tokens", 0),
            "model": session_data.get("model", ""),
            "turns": session_data.get("turns", []),
            "tool_calls": session_data.get("tool_calls", []),
        }

        # Validate and potentially truncate the output summary
        MAX_PAYLOAD_SIZE = 1_000_000  # 1MB limit

        try:
            output_json = json.dumps(output_summary, default=str)
            if len(output_json) > MAX_PAYLOAD_SIZE:
                logger.warning(f"Output summary too large ({len(output_json)} bytes), truncating tool calls")
                # Truncate tool calls to fit
                output_summary["tool_calls"] = self._truncate_tool_calls_to_fit(
                    output_summary["tool_calls"],
                    MAX_PAYLOAD_SIZE // 2  # Leave room for other data
                )
                output_summary["_truncated"] = True
                output_json = json.dumps(output_summary, default=str)
                logger.info(f"Truncated output summary to {len(output_json)} bytes")
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize output summary: {e}")
            # Try with minimal data
            output_summary = {
                "session_id": session_id,
                "total_turns": len(session_data.get("turns", [])),
                "total_tool_calls": len(session_data.get("tool_calls", [])),
                "error": f"Serialization failed: {str(e)[:100]}",
            }
            output_json = json.dumps(output_summary, default=str)

        # Build the trace payload for LangWatch collector API
        trace_data = {
            "trace_id": trace_id,
            "spans": [
                {
                    "type": "llm",
                    "name": "policy_tracker_query",
                    "span_id": uuid.uuid4().hex[:16],
                    "trace_id": trace_id,
                    "input": {
                        "type": "text",
                        "value": session_data.get("user_query", "")
                    },
                    "output": {
                        "type": "json",
                        "value": output_json
                    },
                    "timestamps": {
                        "started_at": int(time.time() * 1000) - 5000,
                        "finished_at": int(time.time() * 1000)
                    },
                    "metrics": {
                        "prompt_tokens": sum(t.get("input_tokens", 0) for t in session_data.get("turns", [])),
                        "completion_tokens": sum(t.get("output_tokens", 0) for t in session_data.get("turns", []))
                    },
                    "params": {
                        "model": session_data.get("model", "claude-sonnet-4-20250514")
                    }
                }
            ],
            "metadata": {
                "thread_id": session_id,
                "user_id": "policy_tracker",
                "labels": ["agent", "policy_tracker"],
                "total_turns": len(session_data.get("turns", [])),
                "total_tool_calls": len(session_data.get("tool_calls", [])),
            }
        }

        # Send to LangWatch collector endpoint
        collector_url = f"{self.endpoint}/api/collector"
        headers = {
            "Content-Type": "application/json",
            "X-Auth-Token": self.api_key,
        }

        try:
            # Final payload size check
            payload_json = json.dumps(trace_data, default=str)
            payload_size = len(payload_json)
            logger.debug(f"Sending trace payload: {payload_size} bytes")

            response = requests.post(
                collector_url,
                headers=headers,
                json=trace_data,
                timeout=10
            )

            if response.status_code == 200:
                logger.info(f"Trace sent successfully to LangWatch: trace_id={trace_id}, session_id={session_id}, size={payload_size}")
                return True
            else:
                # Log full error for debugging (not truncated)
                logger.error(
                    f"LangWatch API error: status={response.status_code}, "
                    f"payload_size={payload_size}, "
                    f"response={response.text}"
                )
                return False

        except json.JSONDecodeError as e:
            logger.error(f"JSON serialization failed: {e}, session_id={session_id}")
            return False
        except requests.exceptions.Timeout:
            logger.error(f"Timeout sending trace to LangWatch, session_id={session_id}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error sending trace to LangWatch: {e}, session_id={session_id}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending trace to LangWatch: {e}, session_id={session_id}", exc_info=True)
            return False

    def initialize(self, instrumentation_mode: str = "auto") -> bool:
        """Initialize LangWatch instrumentation.

        Args:
            instrumentation_mode: "langchain", "anthropic", "both", "manual", or "auto"
                - "langchain": Only LangChain instrumentation
                - "anthropic": Only Anthropic auto-instrumentation (creates trace per API call)
                - "both": Both LangChain and Anthropic auto-instrumentation
                - "manual": Only setup LangWatch, no auto-instrumentation (recommended for
                           agents using @langwatch_config.trace() decorator)
                - "auto": Initializes both if packages available

        Note: For agentic workflows where you want ONE trace per session (not per API call),
        use instrumentation_mode="manual" and decorate your entry point with @langwatch_config.trace().
        """
        if not self.enabled:
            logger.info("LangWatch observability disabled")
            return False

        if not self.api_key:
            logger.warning("LangWatch enabled but LANGWATCH_API_KEY not set")
            return False

        if self._initialized:
            logger.debug("LangWatch already initialized")
            return True

        success = False

        # For "manual" mode, just setup LangWatch without auto-instrumentation
        if instrumentation_mode == "manual":
            success = self._setup_langwatch_only()
        else:
            # Determine what to instrument
            do_langchain = instrumentation_mode in ("langchain", "both", "auto")
            do_anthropic = (
                instrumentation_mode in ("anthropic", "both", "auto")
                and self.enable_anthropic_instrumentation
            )

            if do_langchain:
                success = self._instrument_langchain() or success

            if do_anthropic:
                success = self._instrument_anthropic() or success

        self._initialized = success
        return success

    def _setup_langwatch_only(self) -> bool:
        """Setup LangWatch without any auto-instrumentation.

        This is the recommended mode for agentic workflows where you want
        a single trace per session/query, using @langwatch_config.trace() decorator.
        """
        try:
            import langwatch

            langwatch.setup(
                api_key=self.api_key,
                endpoint_url=self.endpoint,
                instrumentors=[],  # No auto-instrumentation
            )
            logger.info(f"LangWatch initialized (manual mode) at {self.endpoint}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize LangWatch: {e}")
            return False

    def _instrument_langchain(self) -> bool:
        """Initialize LangChain instrumentation."""
        try:
            import langwatch
            from openinference.instrumentation.langchain import LangChainInstrumentor

            langwatch.setup(
                api_key=self.api_key,
                endpoint_url=self.endpoint,
                instrumentors=[LangChainInstrumentor()],
            )
            logger.info(f"LangChain instrumentation initialized at {self.endpoint}")
            return True
        except ImportError as e:
            logger.warning(f"LangChain instrumentor not available: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize LangChain instrumentation: {e}")
            return False

    def _setup_otel_tracer_provider(self) -> bool:
        """Configure OpenTelemetry TracerProvider with LangWatch OTLP exporter."""
        if self._otel_provider_initialized:
            return True

        try:
            from opentelemetry import trace
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            otlp_exporter = OTLPSpanExporter(
                endpoint=self.otlp_endpoint,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            provider = TracerProvider()
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            trace.set_tracer_provider(provider)
            self._otel_provider_initialized = True
            logger.info(f"OpenTelemetry TracerProvider configured for {self.otlp_endpoint}")
            return True
        except ImportError as e:
            logger.warning(f"OpenTelemetry OTLP exporter not available: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to setup OTel TracerProvider: {e}")
            return False

    def _instrument_anthropic(self) -> bool:
        """Initialize OpenTelemetry instrumentation for Anthropic SDK."""
        if self._anthropic_instrumented:
            return True

        try:
            from opentelemetry.instrumentation.anthropic import AnthropicInstrumentor

            if not self._otel_provider_initialized:
                if not self._setup_otel_tracer_provider():
                    return False

            AnthropicInstrumentor().instrument()
            self._anthropic_instrumented = True
            logger.info("Anthropic SDK instrumentation initialized")
            return True
        except ImportError as e:
            logger.warning(f"Anthropic instrumentor not available: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to instrument Anthropic SDK: {e}")
            return False

    def trace(
        self,
        name: str,
        metadata: Optional[dict[str, Any]] = None,
        session_id_param: Optional[str] = None,
    ) -> Callable:
        """Decorator for tracing functions with LangWatch.

        Note: This decorator defers the initialization check to runtime,
        allowing decorators to be applied at import time before initialize() is called.

        Args:
            name: Name for the trace
            metadata: Optional metadata dict to attach to trace
            session_id_param: Name of the function parameter that contains the session_id.
                             If provided, this will be used as thread_id for grouping traces.
        """
        import functools

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                # Check initialization at runtime, not decoration time
                if not self.enabled or not self._initialized:
                    return await func(*args, **kwargs)

                try:
                    import langwatch

                    # Build metadata with thread_id for session correlation
                    trace_metadata = dict(metadata or {})

                    # Extract session_id from kwargs if param name is specified
                    session_id = None
                    if session_id_param and session_id_param in kwargs:
                        session_id = kwargs[session_id_param]
                    elif session_id_param:
                        # Try to find session_id in positional args by inspecting signature
                        import inspect
                        sig = inspect.signature(func)
                        params = list(sig.parameters.keys())
                        if session_id_param in params:
                            param_idx = params.index(session_id_param)
                            # Account for 'self' parameter in methods
                            if len(args) > param_idx:
                                session_id = args[param_idx]

                    if session_id:
                        trace_metadata["thread_id"] = session_id

                    # Use langwatch.trace as a context manager for async functions
                    with langwatch.trace(name=name, metadata=trace_metadata) as trace:
                        # Also update the trace with thread_id for proper grouping
                        if session_id and hasattr(trace, "update"):
                            trace.update(metadata={"thread_id": session_id})
                        return await func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"LangWatch trace failed for {name}: {e}")
                    return await func(*args, **kwargs)

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                # Check initialization at runtime, not decoration time
                if not self.enabled or not self._initialized:
                    return func(*args, **kwargs)

                try:
                    import langwatch

                    # Build metadata with thread_id for session correlation
                    trace_metadata = dict(metadata or {})

                    # Extract session_id from kwargs if param name is specified
                    session_id = None
                    if session_id_param and session_id_param in kwargs:
                        session_id = kwargs[session_id_param]
                    elif session_id_param:
                        # Try to find session_id in positional args by inspecting signature
                        import inspect
                        sig = inspect.signature(func)
                        params = list(sig.parameters.keys())
                        if session_id_param in params:
                            param_idx = params.index(session_id_param)
                            if len(args) > param_idx:
                                session_id = args[param_idx]

                    if session_id:
                        trace_metadata["thread_id"] = session_id

                    # Use langwatch.trace as a context manager for sync functions
                    with langwatch.trace(name=name, metadata=trace_metadata) as trace:
                        if session_id and hasattr(trace, "update"):
                            trace.update(metadata={"thread_id": session_id})
                        return func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"LangWatch trace failed for {name}: {e}")
                    return func(*args, **kwargs)

            # Return appropriate wrapper based on function type
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper

        return decorator

    def capture_tool_execution(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_output: Any,
        execution_time: float,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """Capture a tool execution as a LangWatch span.

        Use this to explicitly log tool executions with full metadata.
        """
        if not self.enabled or not self._initialized:
            return

        try:
            import langwatch

            # Create span with tool metadata
            with langwatch.trace(
                name=f"tool:{tool_name}",
                metadata={
                    "tool_name": tool_name,
                    "tool_input": tool_input,
                    "execution_time_seconds": execution_time,
                    "success": success,
                    "error": error,
                },
            ) as span:
                # Set span attributes for better visibility
                if hasattr(span, "set_attribute"):
                    span.set_attribute("tool.name", tool_name)
                    span.set_attribute("tool.success", success)
                    span.set_attribute("tool.execution_time", execution_time)
                    if error:
                        span.set_attribute("tool.error", error)

        except Exception as e:
            logger.warning(f"Failed to capture tool execution for {tool_name}: {e}")

    def _filter_embeddings(self, data: Any) -> Any:
        """Recursively filter out embedding/vector properties from data structures.

        Removes:
        - Properties named 'embedding', 'embeddings', 'vector', 'vectors', etc.
        - Arrays that look like embedding vectors (100+ floats)

        This significantly reduces payload size while keeping important metadata.
        """
        # Expanded list of embedding-related keys
        embedding_keys = {
            'embedding', 'embeddings', 'vector', 'vectors', 'embed',
            'dense_vector', 'sparse_vector', 'text_embedding', 'node_embedding',
            'relationship_embedding', 'fact_embedding'
        }

        if isinstance(data, dict):
            filtered = {}
            for k, v in data.items():
                # Skip embedding keys
                if k.lower() in embedding_keys:
                    continue
                # Skip if value looks like an embedding (list of many floats)
                if isinstance(v, list) and len(v) > 100:
                    # Check if first 10 elements are all numbers (likely embedding)
                    sample = v[:10]
                    if all(isinstance(x, (int, float)) for x in sample):
                        continue  # Skip - looks like embedding vector
                filtered[k] = self._filter_embeddings(v)
            return filtered
        elif isinstance(data, list):
            return [self._filter_embeddings(item) for item in data]
        else:
            return data

    def _smart_truncate_output(self, data: Any, max_len: int = 50000) -> Any:
        """Truncate large data while preserving valid JSON structure.

        Instead of cutting JSON strings mid-way (which creates invalid JSON),
        this method:
        1. For dict/list: recursively truncates nested structures
        2. For strings: truncates with marker
        3. Preserves important fields (name, type, uuid) over large content

        Args:
            data: The data to truncate
            max_len: Maximum size in bytes for the serialized output

        Returns:
            Truncated data that remains valid JSON-serializable
        """
        if data is None:
            return None

        if isinstance(data, str):
            if len(data) > max_len:
                return data[:max_len] + "...[truncated]"
            return data

        if isinstance(data, (int, float, bool)):
            return data

        if isinstance(data, list):
            # Limit list items if too many
            result = []
            current_size = 0
            for item in data:
                truncated_item = self._smart_truncate_output(item, max(max_len // 10, 1000))
                try:
                    item_size = len(json.dumps(truncated_item, default=str))
                except (TypeError, ValueError):
                    item_size = 1000  # Fallback estimate
                if current_size + item_size > max_len:
                    result.append({"_truncated": f"...{len(data) - len(result)} more items"})
                    break
                result.append(truncated_item)
                current_size += item_size
            return result

        if isinstance(data, dict):
            # Prioritize important fields including knowledge graph data
            priority_keys = {
                'name', 'type', 'uuid', 'id', 'status', 'success', 'error', 'tool_name',
                # Knowledge graph critical keys - preserve entity/relationship data
                'entities', 'relationships', 'nodes', 'edges', 'properties',
                'entity', 'relationship', 'node', 'source', 'target'
            }
            # Verbose fields to truncate aggressively (non-critical content)
            verbose_keys = {'description', 'summary', 'content', 'text', 'body', 'raw_response', 'fact'}
            result = {}
            current_size = 0

            # First pass: add priority keys
            for key in priority_keys:
                if key in data:
                    value = self._smart_truncate_output(data[key], max(max_len // 20, 500))
                    result[key] = value
                    try:
                        current_size += len(json.dumps({key: value}, default=str))
                    except (TypeError, ValueError):
                        current_size += 100  # Fallback estimate

            # Second pass: add remaining keys up to limit
            for key, value in data.items():
                if key in priority_keys:
                    continue
                # Aggressive truncation for verbose fields
                if key in verbose_keys:
                    truncated_value = self._smart_truncate_output(value, max_len=500)
                else:
                    truncated_value = self._smart_truncate_output(value, max(max_len // 10, 1000))
                try:
                    value_size = len(json.dumps({key: truncated_value}, default=str))
                except (TypeError, ValueError):
                    value_size = 500  # Fallback estimate
                if current_size + value_size > max_len:
                    # Don't break - add summary placeholder for critical keys that weren't processed
                    remaining_keys = [k for k in data.keys() if k not in result and k not in priority_keys]
                    for rkey in remaining_keys:
                        if rkey in {'entities', 'relationships', 'nodes'}:
                            rval = data[rkey]
                            # Add count info instead of full data
                            result[rkey] = {"_count": len(rval) if isinstance(rval, list) else 1, "_truncated": True}
                    if remaining_keys:
                        result["_truncated_keys"] = [k for k in remaining_keys if k not in result][:10]
                    break
                result[key] = truncated_value
                current_size += value_size

            return result

        # Fallback: convert to string and truncate
        try:
            str_data = str(data)
            if len(str_data) > max_len:
                return str_data[:max_len] + "...[truncated]"
            return str_data
        except Exception:
            return "[unserializable data]"

    def _parse_tool_output(self, tool_output: Any) -> Any:
        """Parse tool output and extract structured data.

        Handles string outputs that may contain JSON or markdown-formatted results.
        Filters out embeddings to reduce size.
        """
        if tool_output is None:
            return None

        # If already a dict/list, filter embeddings and return
        if isinstance(tool_output, (dict, list)):
            return self._filter_embeddings(tool_output)

        # Try to parse as JSON
        output_str = str(tool_output)
        try:
            parsed = json.loads(output_str)
            return self._filter_embeddings(parsed)
        except json.JSONDecodeError:
            pass

        # Return as string (might be markdown or plain text)
        return output_str

    def capture_tool_call_with_response(
        self,
        tool_name: str,
        tool_use_id: str,
        tool_input: dict[str, Any],
        tool_output: Any,
        execution_time: float,
        success: bool = True,
        error: Optional[str] = None,
        turn_number: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Capture a complete tool call with full request/response for troubleshooting.

        Stores tool call data in the session collector for later sending to LangWatch.
        Uses smart truncation to preserve valid JSON structure and important fields.

        Data captured:
        - Full tool input parameters (for reproducing issues)
        - Complete tool output/response with node/relationship metadata (excluding embeddings)
        - Execution timing and success status
        - Context (turn number, session) for correlation
        """
        if not self.enabled or not self._initialized:
            return

        # Store in session collector (synchronous - no async needed)
        if session_id:
            collector = self.get_session_collector(session_id)

            # Filter embeddings FIRST, then parse
            parsed_output = self._filter_embeddings(self._parse_tool_output(tool_output))
            filtered_input = self._filter_embeddings(tool_input) if tool_input else {}

            # Smart truncate while keeping valid JSON structure
            # Output gets more space (50KB) than input (10KB)
            final_output = self._smart_truncate_output(parsed_output, max_len=50000)
            final_input = self._smart_truncate_output(filtered_input, max_len=10000)

            collector["tool_calls"].append({
                "tool_name": tool_name,
                "tool_use_id": tool_use_id,
                "input": final_input,  # Always valid JSON-serializable
                "output": final_output if success else {"error": error},
                "success": success,
                "execution_time_ms": int(execution_time * 1000),
                "turn_number": turn_number,
            })
            logger.debug(f"Collected tool call: {tool_name} for session {session_id}")

    def set_thread_id(self, thread_id: str) -> None:
        """Set the thread_id for the current trace to enable session grouping.

        Call this method early in your traced function after determining the session_id.
        This ensures all spans within the trace are grouped under the same thread.

        Args:
            thread_id: The session/thread ID to associate with the current trace
        """
        if not self.enabled or not self._initialized:
            return

        try:
            import langwatch

            trace = langwatch.get_current_trace()
            if trace and hasattr(trace, "update"):
                trace.update(metadata={"thread_id": thread_id})
                logger.debug(f"Set thread_id={thread_id} for current trace")
        except Exception as e:
            logger.warning(f"Failed to set thread_id: {e}")

    def capture_agentic_turn(
        self,
        turn_number: int,
        session_id: str,
        stop_reason: str,
        tool_calls: list[dict],
        input_tokens: int,
        output_tokens: int,
        model: str,
    ) -> None:
        """Capture metadata for each turn in an agentic loop.

        Stores turn data in the session collector for later sending to LangWatch.

        Data captured:
        - Turn number and stop reason
        - What tools were called in each turn
        - Token consumption per turn
        """
        if not self.enabled or not self._initialized:
            return

        # Store in session collector (synchronous - no async needed)
        if session_id:
            collector = self.get_session_collector(session_id)
            tool_names = [tc.get("name", "unknown") for tc in tool_calls]

            collector["turns"].append({
                "turn_number": turn_number,
                "stop_reason": stop_reason,
                "tool_calls_count": len(tool_calls),
                "tool_names": tool_names,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "model": model,
            })

            # Update totals
            collector["total_tokens"] += input_tokens + output_tokens
            collector["model"] = model

            logger.debug(f"Collected turn {turn_number} for session {session_id}")


# Global configuration instance
langwatch_config = LangWatchConfig()
