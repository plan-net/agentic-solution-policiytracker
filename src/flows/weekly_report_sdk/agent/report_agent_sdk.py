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
from src.prompts.prompt_manager import prompt_manager
from src.shared.sdk_hooks import create_langwatch_hooks, create_enhanced_hooks

from .prompts import DEFAULT_MCP_SERVER_URL, get_weekly_report_system_prompt

logger = logging.getLogger(__name__)

# MCP tool names available on the server
MCP_TOOLS = [
    "search_knowledge_graph",
    "analyze_query",
    "get_entity_info",
    "find_relationships",
    "graph_statistics",
]


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
        model: str = "claude-sonnet-4-20250514",
        max_turns: int = 30,
        enable_reflection: bool = True,
    ):
        """Initialize the Weekly Report SDK Agent.

        Args:
            mcp_server_url: MCP server URL (defaults to DEFAULT_MCP_SERVER_URL)
            model: Claude model to use (user-selectable via UI)
            max_turns: Maximum number of conversation turns for the agentic loop
            enable_reflection: Enable reflection pattern with confidence scoring
        """
        self.mcp_server_url = mcp_server_url or DEFAULT_MCP_SERVER_URL
        self.model = model
        self.max_turns = max_turns
        self.enable_reflection = enable_reflection

        # Initialize LangWatch in manual mode
        langwatch_config.initialize(instrumentation_mode="manual")

        logger.info(
            f"WeeklyReportSDKAgent initialized with model: {model}, "
            f"MCP server: {self.mcp_server_url}, reflection: {enable_reflection}"
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

    async def _build_full_system_prompt(
        self, week_label: str, week_start: str, week_end: str
    ) -> str:
        """Build complete system prompt with base, planning, and reflection components.

        Args:
            week_label: Week label (e.g., "KW48/2025")
            week_start: Start date (ISO format)
            week_end: End date (ISO format)

        Returns:
            Complete system prompt combining all components
        """
        # Get base prompt
        base_prompt = await self._get_system_prompt(week_label, week_start, week_end)

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
        """Build MCP server configuration for SSE transport."""
        return {
            "knowledge_graph": {
                "type": "sse",
                "url": self.mcp_server_url,
            }
        }

    def _get_allowed_tools(self) -> list[str]:
        """Get list of allowed MCP tools in SDK format.

        SDK tool naming convention: mcp__<server_name>__<tool_name>
        """
        return [f"mcp__knowledge_graph__{tool}" for tool in MCP_TOOLS]

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

        # Generate a unique session ID for this report generation
        report_session_id = f"report_{uuid.uuid4().hex[:12]}"

        # Set thread_id for LangWatch trace grouping
        langwatch_config.set_thread_id(report_session_id)
        langwatch_config.set_session_query(report_session_id, user_message)

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
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                report_content += block.text
                            elif isinstance(block, ToolUseBlock):
                                increment_turn()
                                turn_count += 1

                                # Extract tool name from SDK format
                                tool_name = block.name
                                if tool_name.startswith("mcp__knowledge_graph__"):
                                    tool_name = tool_name.replace(
                                        "mcp__knowledge_graph__", ""
                                    )

                                tool_input = getattr(block, "input", {})
                                tool_calls.append({
                                    "tool": tool_name,
                                    "input": tool_input,
                                    "success": True,
                                })

                                if tracer:
                                    query_text = tool_input.get("query", tool_name)
                                    await tracer.markdown(
                                        f"  - Searched: {query_text[:50]}..."
                                    )

                    elif isinstance(message, ResultMessage):
                        break

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
            },
            "tool_calls": tool_calls,
        }

    async def close(self):
        """Close the agent and cleanup resources."""
        # No persistent resources in SDK-based agent
        pass
