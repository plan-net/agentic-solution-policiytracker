"""Weekly Report Agent using Claude Agent SDK.

This agent generates weekly regulatory intelligence reports by:
1. Systematically researching the knowledge graph across categories
2. Using the SDK's automatic agentic loop for tool execution
3. Generating a structured markdown report

Key differences from original WeeklyReportAgent:
- Uses ClaudeSDKClient instead of AsyncAnthropic
- Native MCP support via mcp_servers config
- Automatic agentic loop (no manual while loop)
- Hooks for observability instead of inline capture

Advanced agentic patterns:
- Reflection pattern with confidence scoring
- Planning strategy for multi-step research
- External prompt management via PromptManager
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    HookMatcher,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ResultMessage,
)

from src.chat.observability.langwatch_config import langwatch_config
from src.chat.observability.observability_provider import observability_provider
from src.chat.observability.langfuse_config import (
    is_initialized as langfuse_is_initialized,
    get_langfuse_client,
)
from src.prompts.prompt_manager import prompt_manager
from src.shared.sdk_hooks import create_langwatch_hooks, create_enhanced_hooks
from src.shared.client_context import get_client_context_for_prompt
from src.shared.sdk_cost_tracker import sdk_cost_tracker, SDKCostRecord
from src.claude_agent.query_decomposition import QueryDecomposer

from .prompts import (
    DEFAULT_MCP_SERVER_URL,
    DEFAULT_BUNDESTAG_MCP_URL,
    DEFAULT_WEB_SEARCH_MCP_URL,
    KNOWLEDGE_GRAPH_TOOLS,
    BUNDESTAG_DIP_TOOLS,
    WEB_SEARCH_TOOLS,
    get_weekly_report_system_prompt,
)

logger = logging.getLogger(__name__)


class WeeklyReportSDKAgent:
    """Claude-based agent for generating weekly regulatory intelligence reports.

    Uses the Claude Agent SDK for automatic agentic loop management and
    native MCP support.

    Key features:
    - Automatic tool execution via SDK
    - Native MCP support (SSE transport)
    - LangWatch observability via enhanced hooks
    - Progress tracking via tracer integration
    - Reflection pattern with confidence scoring
    - External prompt management via PromptManager
    """

    def __init__(
        self,
        mcp_server_url: Optional[str] = None,
        bundestag_mcp_url: Optional[str] = None,
        web_search_mcp_url: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        max_turns: int = 50,  # Increased from 30 for complex report generation
        enable_reflection: bool = True,
        enable_bundestag: bool = True,
        enable_web_search: bool = True,
    ):
        """Initialize the Weekly Report SDK Agent.

        Args:
            mcp_server_url: Knowledge Graph MCP server URL (defaults to DEFAULT_MCP_SERVER_URL)
            bundestag_mcp_url: Bundestag DIP MCP server URL (defaults to DEFAULT_BUNDESTAG_MCP_URL)
            web_search_mcp_url: Web Search MCP server URL (defaults to DEFAULT_WEB_SEARCH_MCP_URL)
            model: Claude model to use (user-selectable via UI)
            max_turns: Maximum number of conversation turns for the agentic loop
            enable_reflection: Enable reflection pattern with confidence scoring
            enable_bundestag: Enable Bundestag DIP API tools
            enable_web_search: Enable web search tools (Exa.ai, DPA)
        """
        self.mcp_server_url = mcp_server_url or DEFAULT_MCP_SERVER_URL
        self.bundestag_mcp_url = bundestag_mcp_url or DEFAULT_BUNDESTAG_MCP_URL
        self.web_search_mcp_url = web_search_mcp_url or DEFAULT_WEB_SEARCH_MCP_URL
        self.model = model
        self.max_turns = max_turns
        self.enable_reflection = enable_reflection
        self.enable_bundestag = enable_bundestag
        self.enable_web_search = enable_web_search

        # Query decomposer for handling complex report generation tasks
        self._query_decomposer = QueryDecomposer(complexity_threshold=max_turns)

        # Initialize observability (handles LangWatch, LangFuse, or both based on OBSERVABILITY_PROVIDER)
        observability_provider.initialize(instrumentation_mode="manual")

        logger.info(
            f"WeeklyReportSDKAgent initialized with model: {model}, "
            f"MCP servers: knowledge_graph={self.mcp_server_url}, "
            f"bundestag={'enabled' if enable_bundestag else 'disabled'}, "
            f"web_search={'enabled' if enable_web_search else 'disabled'}, "
            f"reflection: {enable_reflection}"
        )

    async def _get_system_prompt(
        self, week_label: str, week_start: str, week_end: str
    ) -> str:
        """Load and render system prompt with variables.

        Tries PromptManager first, falls back to inline function.

        Args:
            week_label: Week label (e.g., "KW48/2025")
            week_start: Start date (ISO format)
            week_end: End date (ISO format)

        Returns:
            Rendered system prompt with week-specific information
        """
        try:
            base_prompt = await prompt_manager.get_prompt(
                "sdk_agents/weekly_report_system",
                variables={
                    "week_label": week_label,
                    "week_start": week_start,
                    "week_end": week_end,
                }
            )
            logger.debug("Loaded weekly report system prompt from PromptManager")
            return base_prompt
        except Exception as e:
            logger.warning(f"Failed to load prompt from PromptManager: {e}, using fallback")
            return get_weekly_report_system_prompt(week_label, week_start, week_end)

    async def _get_planning_prompt(self) -> str:
        """Load the planning strategy prompt for multi-step research.

        Returns:
            Planning strategy prompt or empty string if unavailable
        """
        try:
            return await prompt_manager.get_prompt("sdk_agents/weekly_report_planning")
        except Exception as e:
            logger.warning(f"Failed to load planning prompt: {e}")
            return ""

    async def _get_tool_selection_prompt(self) -> str:
        """Load the tool selection/reflection strategy prompt.

        Returns:
            Tool selection strategy prompt or empty string if unavailable
        """
        try:
            return await prompt_manager.get_prompt("sdk_agents/tool_selection_strategy")
        except Exception as e:
            logger.warning(f"Failed to load tool selection prompt: {e}")
            return ""

    async def _get_client_context_prompt(self) -> str:
        """Load client context prompt with business understanding.

        Loads the client context from data/context/client.yaml and injects
        it into the prompt template for business-aware analysis.

        Returns:
            Client context prompt or empty string if unavailable
        """
        try:
            client_vars = get_client_context_for_prompt()
            return await prompt_manager.get_prompt(
                "sdk_agents/client_context",
                variables=client_vars
            )
        except Exception as e:
            logger.warning(f"Failed to load client context prompt: {e}")
            return ""

    async def _build_full_system_prompt(
        self, week_label: str, week_start: str, week_end: str
    ) -> str:
        """Build complete system prompt with client context, planning, and reflection.

        Args:
            week_label: Week label (e.g., "KW48/2025")
            week_start: Start date (ISO format)
            week_end: End date (ISO format)

        Returns:
            Complete system prompt combining all components:
            1. Base system prompt with week info
            2. Client context (business understanding and regulatory focus)
            3. Planning strategy for multi-step research
            4. Tool selection/reflection strategy (if enabled)
        """
        # Get base prompt
        base_prompt = await self._get_system_prompt(week_label, week_start, week_end)

        # Add client context (business understanding)
        client_context_prompt = await self._get_client_context_prompt()
        if client_context_prompt:
            base_prompt = f"{base_prompt}\n\n{client_context_prompt}"

        # Add planning strategy
        planning_prompt = await self._get_planning_prompt()
        if planning_prompt:
            base_prompt = f"{base_prompt}\n\n{planning_prompt}"

        # Add tool selection/reflection strategy if enabled
        if self.enable_reflection:
            tool_prompt = await self._get_tool_selection_prompt()
            if tool_prompt:
                base_prompt = f"{base_prompt}\n\n{tool_prompt}"

        return base_prompt

    def _build_mcp_config(self) -> dict:
        """Build MCP server configuration for SSE transport.

        Configures connections to all enabled MCP servers:
        - knowledge_graph: Neo4j/Graphiti knowledge graph (always enabled)
        - bundestag_dip: German Bundestag DIP API (optional)
        - web_search: Exa.ai and DPA news search (optional)
        """
        config = {
            "knowledge_graph": {
                "type": "sse",
                "url": self.mcp_server_url,
            }
        }

        if self.enable_bundestag:
            config["bundestag_dip"] = {
                "type": "sse",
                "url": self.bundestag_mcp_url,
            }

        if self.enable_web_search:
            config["web_search"] = {
                "type": "sse",
                "url": self.web_search_mcp_url,
            }

        return config

    def _get_allowed_tools(self) -> list[str]:
        """Get list of allowed MCP tools in SDK format.

        SDK tool naming convention: mcp__<server_name>__<tool_name>

        Returns tools from all enabled MCP servers.
        """
        # Knowledge graph tools (always enabled)
        tools = [f"mcp__knowledge_graph__{t}" for t in KNOWLEDGE_GRAPH_TOOLS]

        # Bundestag DIP tools (optional)
        if self.enable_bundestag:
            tools.extend([f"mcp__bundestag_dip__{t}" for t in BUNDESTAG_DIP_TOOLS])

        # Web search tools (optional)
        if self.enable_web_search:
            tools.extend([f"mcp__web_search__{t}" for t in WEB_SEARCH_TOOLS])

        return tools

    @langwatch_config.trace(
        name="weekly_report_sdk_generation",
        metadata={"agent": "WeeklyReportSDKAgent"},
    )
    async def generate_report(
        self,
        week_start: datetime,
        week_end: datetime,
        week_label: str,
        include_events: bool = True,
        tracer=None,
    ) -> dict[str, Any]:
        """Generate a weekly regulatory intelligence report.

        Uses the SDK's automatic agentic loop to:
        1. Research each category using knowledge graph tools
        2. Synthesize findings into structured sections
        3. Generate executive summary with cross-cutting themes

        Features:
        - Reflection pattern: Validates tool results and computes confidence
        - Planning strategy: Multi-step research with category-based execution
        - External prompts: Loads prompts from PromptManager

        Args:
            week_start: Start of the reporting week
            week_end: End of the reporting week
            week_label: Human-readable week label (e.g., "KW48/2025")
            include_events: Whether to include upcoming events section
            tracer: Optional Kodosumi tracer for progress updates

        Returns:
            Dict containing:
                - report_content: Generated markdown report
                - metadata: Generation metadata (model, turns, confidence, etc.)
                - tool_calls: List of tool calls made
        """
        # Format dates for the prompt
        week_start_str = week_start.strftime("%Y-%m-%d")
        week_end_str = week_end.strftime("%Y-%m-%d")

        # Get the full system prompt (base + planning + reflection)
        system_prompt = await self._build_full_system_prompt(
            week_label=week_label,
            week_start=week_start_str,
            week_end=week_end_str,
        )

        # Initial user message
        user_message = f"""Generate a comprehensive Weekly Regulatory Intelligence Digest for {week_label}.

Please research each category thoroughly using the available tools, then synthesize your findings
into a well-structured report following the output format specified in your instructions.

{"Include upcoming events and deadlines in the next 30-90 days." if include_events else "Skip the upcoming events section."}

Begin by searching for legislative and regulatory updates, then proceed through each category."""

        # Analyze task complexity
        complexity_analysis = self._query_decomposer.analyze_complexity(user_message)
        logger.info(
            f"Report generation complexity: {complexity_analysis.complexity.value}, "
            f"estimated_turns: {complexity_analysis.estimated_turns}"
        )

        # Generate a unique session ID for this report generation
        report_session_id = f"report_{uuid.uuid4().hex[:12]}"

        # Set thread_id for LangWatch trace grouping
        langwatch_config.set_thread_id(report_session_id)
        langwatch_config.set_session_query(report_session_id, user_message)

        # Create LangFuse trace context (if enabled)
        langfuse_trace = None
        if langfuse_is_initialized():
            langfuse = get_langfuse_client()
            if langfuse:
                try:
                    langfuse_trace = langfuse.start_as_current_span(
                        name="weekly_report_generation",
                        input={"user_message": user_message, "session_id": report_session_id},
                        metadata={
                            "agent": "WeeklyReportSDKAgent",
                            "model": self.model,
                            "week_label": week_label,
                        },
                    )
                    langfuse_trace.__enter__()
                    langfuse.update_current_trace(
                        tags=["weekly-report", "sdk-agent"],
                        metadata={"session_id": report_session_id},
                    )
                except Exception as e:
                    logger.debug(f"Failed to create LangFuse trace: {e}")

        # Track tool calls for metadata
        tool_calls: list[dict[str, Any]] = []
        turn_count = 0

        if tracer:
            await tracer.markdown(
                "**Starting report generation...**\n\nResearching knowledge graph..."
            )

        # Create hooks - use enhanced hooks if reflection is enabled
        if self.enable_reflection:
            pre_hook, post_hook, increment_turn, get_reflection = await create_enhanced_hooks(
                session_id=report_session_id,
                langwatch_config=langwatch_config,
                enable_reflection=True,
                enable_retry=True,
            )
        else:
            pre_hook, post_hook, increment_turn = await create_langwatch_hooks(
                session_id=report_session_id,
                langwatch_config=langwatch_config,
            )
            get_reflection = lambda: {"total_tools": 0, "avg_confidence": 1.0, "low_confidence_tools": [], "turns": 0}

        # Build SDK options with hooks
        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            mcp_servers=self._build_mcp_config(),
            allowed_tools=self._get_allowed_tools(),
            model=self.model,
            max_turns=self.max_turns,
            hooks={
                "PreToolUse": [HookMatcher(hooks=[pre_hook])],
                "PostToolUse": [HookMatcher(hooks=[post_hook])],
            },
        )

        report_content = ""

        try:
            async with ClaudeSDKClient(options=options) as client:
                await client.query(user_message)

                async for message in client.receive_response():
                    if isinstance(message, AssistantMessage):
                        # DEBUG: Log AssistantMessage for reconciliation
                        block_types = [type(b).__name__ for b in message.content]
                        text_len = sum(len(b.text) for b in message.content if isinstance(b, TextBlock))
                        tool_uses = [b.name for b in message.content if isinstance(b, ToolUseBlock)]
                        logger.info(
                            f"[Session {report_session_id}] AssistantMessage: "
                            f"model={message.model}, "
                            f"blocks={block_types}, "
                            f"text_length={text_len}, "
                            f"tool_uses={tool_uses}, "
                            f"parent_tool_use_id={message.parent_tool_use_id}, "
                            f"error={message.error}"
                        )

                        for block in message.content:
                            if isinstance(block, TextBlock):
                                report_content += block.text
                            elif isinstance(block, ToolUseBlock):
                                increment_turn()
                                turn_count += 1

                                # Extract tool name from SDK format (handles all 3 servers)
                                tool_name = block.name
                                source = "unknown"
                                for prefix, src in [
                                    ("mcp__knowledge_graph__", "knowledge_graph"),
                                    ("mcp__bundestag_dip__", "bundestag_dip"),
                                    ("mcp__web_search__", "web_search"),
                                ]:
                                    if tool_name.startswith(prefix):
                                        tool_name = tool_name.replace(prefix, "")
                                        source = src
                                        break

                                tool_input = getattr(block, "input", {})
                                tool_calls.append({
                                    "tool": tool_name,
                                    "source": source,
                                    "input": tool_input,
                                    "success": True,
                                })

                                if tracer:
                                    query_text = tool_input.get("query", tool_name)
                                    source_label = {
                                        "knowledge_graph": "KG",
                                        "bundestag_dip": "Bundestag",
                                        "web_search": "Web",
                                    }.get(source, source)
                                    await tracer.markdown(
                                        f"  - [{source_label}] {query_text[:50]}..."
                                    )

                    elif isinstance(message, ResultMessage):
                        stop_reason = getattr(message, "subtype", "end_turn")
                        logger.info(f"[Session {report_session_id}] Received ResultMessage: stop_reason={stop_reason}")

                        # Check if we have content before breaking
                        if not report_content:
                            logger.warning(f"[Session {report_session_id}] ResultMessage received but no report content accumulated")

                        # Capture cost metrics
                        usage = getattr(message, "usage", None)
                        total_cost = getattr(message, "total_cost_usd", None)
                        duration_ms = getattr(message, "duration_ms", 0)
                        num_turns_sdk = getattr(message, "num_turns", 0)

                        # DEBUG: Log COMPLETE raw ResultMessage for analysis
                        logger.info(
                            f"[Session {report_session_id}] RAW ResultMessage: "
                            f"subtype={message.subtype}, "
                            f"duration_ms={message.duration_ms}, "
                            f"duration_api_ms={message.duration_api_ms}, "
                            f"is_error={message.is_error}, "
                            f"num_turns={message.num_turns}, "
                            f"session_id={message.session_id}, "
                            f"total_cost_usd={message.total_cost_usd}, "
                            f"usage={message.usage}, "
                            f"result={message.result[:100] if message.result else None}..., "
                            f"structured_output={message.structured_output}"
                        )

                        # DEBUG: Log extracted values for comparison with LangFuse
                        logger.info(
                            f"[Session {report_session_id}] SDK ResultMessage cost data: "
                            f"total_cost_usd={total_cost}, "
                            f"usage={usage}, "
                            f"sdk_num_turns={num_turns_sdk}, "
                            f"our_turn_count={turn_count}, "
                            f"duration_ms={duration_ms}"
                        )

                        # Capture final metrics
                        langwatch_config.capture_agentic_turn(
                            session_id=report_session_id,
                            turn=turn_count,
                            tool_name="report_generation_complete",
                            tool_input={"status": "complete"},
                            tool_output=f"Report generated: {len(report_content)} characters",
                            reflection={
                                "stop_reason": stop_reason,
                                "has_content": bool(report_content),
                            }
                        )

                        # Record cost to TimescaleDB (unified tracking with APISIX)
                        if total_cost is not None or usage:
                            # Extract all token types from SDK usage
                            prompt_tokens = usage.get("input_tokens", 0) if usage else 0
                            completion_tokens = usage.get("output_tokens", 0) if usage else 0
                            cache_creation = usage.get("cache_creation_input_tokens", 0) if usage else 0
                            cache_read = usage.get("cache_read_input_tokens", 0) if usage else 0

                            # Extract server tool usage (web search @ $0.01/search, web fetch free)
                            server_tool_use = usage.get("server_tool_use", {}) if usage else {}
                            web_searches = server_tool_use.get("web_search_requests", 0)
                            web_fetches = server_tool_use.get("web_fetch_requests", 0)

                            # Total tokens includes all input types (cached + non-cached) + output
                            total_tokens = prompt_tokens + completion_tokens + cache_creation + cache_read

                            await sdk_cost_tracker.record_cost(SDKCostRecord(
                                provider="anthropic",
                                model=self.model,
                                agent_type="kodosumi_flow",
                                agent_name="WeeklyReportSDKAgent",
                                session_id=report_session_id,
                                prompt_tokens=prompt_tokens,  # Non-cached input only
                                completion_tokens=completion_tokens,
                                total_tokens=total_tokens,  # All tokens combined
                                cost_usd=total_cost or 0.0,
                                latency_ms=duration_ms,
                                flow_name="weekly_report",
                                cache_creation_tokens=cache_creation,
                                cache_read_tokens=cache_read,
                                web_search_requests=web_searches,
                                web_fetch_requests=web_fetches,
                            ))

                        # Handle different stop reasons
                        if stop_reason == "timeout":
                            logger.error(f"[Session {report_session_id}] Agent execution timed out")
                            report_content += "\n\n[Note: Report generation timed out]"

                        # Break on valid stop conditions
                        if stop_reason in ["end_turn", "max_turns", "timeout", "error_max_turns"]:
                            break
                        else:
                            logger.warning(f"[Session {report_session_id}] Unknown stop_reason: {stop_reason}, breaking anyway")
                            break

            # Validate response - ensure we have content
            if not report_content:
                error_msg = (
                    f"No report content generated after {turn_count} turns. "
                    f"Tools executed but produced no output."
                )
                logger.error(f"[Session {report_session_id}] {error_msg}")
                report_content = (
                    f"# Weekly Regulatory Intelligence Digest - {week_label}\n\n"
                    f"**Generation Status**: Error\n\n"
                    f"I apologize, but I encountered an issue generating the report. "
                    f"The research tools executed successfully ({turn_count} turns, {len(tool_calls)} tool calls), "
                    f"but I was unable to produce the final report content. "
                    f"Please try running the report again or contact support if this persists."
                )

            logger.info(f"[Session {report_session_id}] Report content generated: {len(report_content)} characters, {turn_count} turns")

            if tracer:
                await tracer.markdown("\n**Report generation complete!**")

        except Exception as e:
            logger.error(f"Error in SDK report generation: {e}", exc_info=True)
            if tracer:
                await tracer.markdown(f"\n**Error**: {str(e)}")

            # Return partial report or error message
            if not report_content:
                report_content = f"Error generating report: {str(e)}"

        # Finalize LangWatch session
        langwatch_config.set_session_response(report_session_id, report_content)
        session_data = langwatch_config.finalize_session(report_session_id)
        if session_data:
            success = langwatch_config.send_trace_via_rest_api(session_data)
            if success:
                logger.info(f"Trace sent for report session: {report_session_id}")

        # Finalize LangFuse trace (if enabled)
        if langfuse_trace:
            try:
                langfuse = get_langfuse_client()
                if langfuse:
                    langfuse.update_current_span(
                        output=report_content[:5000] if report_content else "",
                        metadata={"turns": turn_count, "tool_calls": len(tool_calls)},
                    )
                langfuse_trace.__exit__(None, None, None)
                langfuse.flush()
                logger.debug(f"LangFuse trace completed for report session: {report_session_id}")
            except Exception as e:
                logger.debug(f"Failed to finalize LangFuse trace: {e}")

        # Get reflection summary
        reflection_summary = get_reflection()

        logger.info(
            f"Report generated successfully in {turn_count} turns "
            f"with {len(tool_calls)} tool calls, "
            f"confidence: {reflection_summary.get('avg_confidence', 1.0):.2f}"
        )

        return {
            "report_content": report_content,
            "metadata": {
                "model": self.model,
                "turns": turn_count,
                "tool_calls_count": len(tool_calls),
                "week_label": week_label,
                "week_start": week_start_str,
                "week_end": week_end_str,
                "generated_at": datetime.now().isoformat(),
                "session_id": report_session_id,
                "reflection": reflection_summary,
                "avg_confidence": reflection_summary.get("avg_confidence", 1.0),
                "validation_passed": reflection_summary.get("avg_confidence", 1.0) > 0.7,
                "task_complexity": {
                    "level": complexity_analysis.complexity.value,
                    "estimated_turns": complexity_analysis.estimated_turns,
                    "actual_turns": turn_count,
                },
            },
            "tool_calls": tool_calls,
        }

    async def close(self):
        """Close the agent and cleanup resources."""
        # No persistent resources in SDK-based agent
        pass
