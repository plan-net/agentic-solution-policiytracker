"""
Unified Agent Tracer for Observability.

Provides a single tracer interface that integrates with:
- Kodosumi Tracer for real-time progress updates in the UI
- LangWatch for development tracing and debugging
- Langfuse for LLM observability (optional)

This abstraction allows agents to be observable regardless of
the execution context (development, production, testing).
"""

import functools
import logging
import os
from collections.abc import Callable
from datetime import datetime
from typing import Any, Optional, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class AgentTracer:
    """
    Unified tracer for agent observability.

    Works with both Kodosumi's Tracer for production progress updates
    and LangWatch for development tracing. Provides a consistent
    interface for:
    - Markdown progress updates
    - Span tracing
    - Tool execution capture
    - LLM call tracking

    Example:
        tracer = AgentTracer(kodosumi_tracer=tracer, langwatch_enabled=True)

        await tracer.markdown("Starting research...")

        @tracer.trace(name="category_research")
        async def research():
            pass

        await tracer.capture_tool_execution(
            tool_name="graphiti_search",
            tool_input={"query": "..."},
            tool_output=results,
            execution_time=1.5,
        )

    Attributes:
        kodosumi_tracer: Optional Kodosumi Tracer for UI updates
        langwatch_enabled: Whether LangWatch tracing is enabled
        langfuse_enabled: Whether Langfuse tracking is enabled
    """

    def __init__(
        self,
        kodosumi_tracer: Optional[Any] = None,
        langwatch_enabled: bool = True,
        langfuse_enabled: bool = False,
    ):
        """
        Initialize the unified tracer.

        Args:
            kodosumi_tracer: Optional Kodosumi Tracer instance for UI updates
            langwatch_enabled: Whether to enable LangWatch tracing
            langfuse_enabled: Whether to enable Langfuse tracking
        """
        self._kodosumi_tracer = kodosumi_tracer
        self._langwatch_enabled = langwatch_enabled and self._check_langwatch_available()
        self._langfuse_enabled = langfuse_enabled

        # Span tracking
        self._spans: list[dict[str, Any]] = []
        self._current_span: Optional[str] = None
        self._span_counter = 0

        # Initialize LangWatch if available
        self._langwatch_tracer = None
        if self._langwatch_enabled:
            self._init_langwatch()

    def _check_langwatch_available(self) -> bool:
        """Check if LangWatch is available and configured."""
        try:
            api_key = os.getenv("LANGWATCH_API_KEY")
            if not api_key:
                return False
            return True
        except Exception:
            return False

    def _init_langwatch(self) -> None:
        """Initialize LangWatch tracer."""
        try:
            from src.chat.observability.langwatch_config import langwatch_config

            langwatch_config.initialize()
            self._langwatch_tracer = langwatch_config
            logger.debug("LangWatch initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize LangWatch: {e}")
            self._langwatch_enabled = False

    async def markdown(self, content: str) -> None:
        """
        Send markdown progress update to Kodosumi UI.

        This is the primary method for sending real-time progress
        updates to users during report generation.

        Args:
            content: Markdown-formatted content to display
        """
        if self._kodosumi_tracer:
            try:
                await self._kodosumi_tracer.markdown(content)
            except Exception as e:
                logger.debug(f"Failed to send markdown to Kodosumi: {e}")
        else:
            # Log to console when not in Kodosumi context
            logger.info(f"[Progress] {content.strip()}")

    async def start_span(
        self,
        name: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Start a new tracing span.

        Spans are used to track the execution of operations with
        timing and success/failure information.

        Args:
            name: Span name (e.g., "category_research", "llm_extraction")
            metadata: Optional metadata to attach to the span

        Returns:
            Span ID for use with end_span()
        """
        self._span_counter += 1
        span_id = f"span_{name}_{self._span_counter}_{datetime.now().timestamp()}"
        self._current_span = span_id

        span_data = {
            "id": span_id,
            "name": name,
            "start_time": datetime.now(),
            "metadata": metadata or {},
            "status": "running",
        }
        self._spans.append(span_data)

        # LangWatch span
        if self._langwatch_enabled and self._langwatch_tracer:
            try:
                # Use LangWatch's trace context
                pass  # LangWatch uses decorators, not explicit spans
            except Exception as e:
                logger.debug(f"LangWatch span start failed: {e}")

        logger.debug(f"Started span: {name} ({span_id})")
        return span_id

    async def end_span(
        self,
        span_id: str,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """
        End a tracing span.

        Args:
            span_id: ID of the span to end
            success: Whether the operation was successful
            error: Optional error message if failed
        """
        for span in self._spans:
            if span["id"] == span_id:
                span["end_time"] = datetime.now()
                span["success"] = success
                span["error"] = error
                span["status"] = "completed" if success else "failed"
                span["duration"] = (
                    span["end_time"] - span["start_time"]
                ).total_seconds()

                logger.debug(
                    f"Ended span: {span['name']} "
                    f"(success={success}, duration={span['duration']:.2f}s)"
                )
                break

    def trace(
        self,
        name: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Callable[[F], F]:
        """
        Decorator for tracing async functions.

        Automatically creates spans around function execution and
        captures success/failure status.

        Args:
            name: Span name for the traced function
            metadata: Optional metadata to attach

        Returns:
            Decorated function

        Example:
            @tracer.trace(name="research_category")
            async def research_category(self, category):
                # Implementation
                pass
        """

        def decorator(func: F) -> F:
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                span_id = await self.start_span(name, metadata)
                try:
                    result = await func(*args, **kwargs)
                    await self.end_span(span_id, success=True)
                    return result
                except Exception as e:
                    await self.end_span(span_id, success=False, error=str(e))
                    raise

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                # For sync functions, just execute without async span
                return func(*args, **kwargs)

            import asyncio

            if asyncio.iscoroutinefunction(func):
                return async_wrapper  # type: ignore
            return sync_wrapper  # type: ignore

        return decorator

    async def capture_tool_execution(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_output: Any,
        execution_time: float,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """
        Capture a tool execution for observability.

        Records tool executions for debugging and performance analysis.
        Integrates with LangWatch when available.

        Args:
            tool_name: Name of the tool (e.g., "graphiti_search")
            tool_input: Input parameters to the tool
            tool_output: Output from the tool
            execution_time: Execution time in seconds
            success: Whether the execution was successful
            error: Optional error message if failed
        """
        # Send progress update
        status = "complete" if success else "failed"
        await self.markdown(
            f"  {'✓' if success else '✗'} `{tool_name}`: {status} ({execution_time:.2f}s)\n"
        )

        # Log for debugging
        logger.info(
            f"Tool execution: {tool_name}, "
            f"success={success}, time={execution_time:.2f}s"
        )

        # LangWatch capture
        if self._langwatch_enabled and self._langwatch_tracer:
            try:
                self._langwatch_tracer.capture_tool_execution(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    tool_output=tool_output if success else None,
                    execution_time=execution_time,
                    success=success,
                    error=error,
                )
            except Exception as e:
                logger.debug(f"LangWatch tool capture failed: {e}")

    async def capture_llm_call(
        self,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        execution_time: float,
        purpose: str = "general",
    ) -> None:
        """
        Capture an LLM call for cost and performance tracking.

        Args:
            model_name: Name of the model used
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            execution_time: Execution time in seconds
            purpose: Purpose of the LLM call
        """
        total_tokens = prompt_tokens + completion_tokens

        logger.info(
            f"LLM call: {model_name}, "
            f"tokens={total_tokens} (prompt={prompt_tokens}, completion={completion_tokens}), "
            f"time={execution_time:.2f}s, purpose={purpose}"
        )

        # LangWatch will automatically capture LLM calls if configured
        # No additional capture needed here

    def get_spans(self) -> list[dict[str, Any]]:
        """
        Get all recorded spans.

        Returns:
            List of span dictionaries with timing and status info
        """
        return self._spans.copy()

    def get_span_summary(self) -> dict[str, Any]:
        """
        Get a summary of all spans.

        Returns:
            Dictionary with span statistics
        """
        if not self._spans:
            return {"total_spans": 0}

        completed = [s for s in self._spans if s.get("status") == "completed"]
        failed = [s for s in self._spans if s.get("status") == "failed"]

        total_duration = sum(
            s.get("duration", 0) for s in self._spans if "duration" in s
        )

        return {
            "total_spans": len(self._spans),
            "completed": len(completed),
            "failed": len(failed),
            "total_duration_seconds": round(total_duration, 3),
        }
