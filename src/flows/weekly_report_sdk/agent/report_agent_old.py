"""Weekly Report Agent using Claude's native tool-use capabilities.

This agent generates weekly regulatory intelligence reports by:
1. Systematically researching the knowledge graph across categories
2. Using Claude's reasoning to synthesize findings
3. Generating a structured markdown report
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Optional

from src.chat.observability.langwatch_config import langwatch_config
from src.claude_agent.mcp_client import MCPClient
from src.config import settings
from src.flows.shared.apisix_llm_client import AgentContext, create_apisix_anthropic_client

from .prompts import DEFAULT_MCP_SERVER_URL, TOOLS, get_weekly_report_system_prompt

logger = logging.getLogger(__name__)


class WeeklyReportAgent:
    """Claude-based agent for generating weekly regulatory intelligence reports.

    Uses the same MCP server as the PolicyTrackerAgent for knowledge graph access,
    with Claude's native tool-use loop for autonomous research and synthesis.
    """

    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        mcp_server_url: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        max_turns: int = 30,
    ):
        """Initialize the Weekly Report Agent.

        Args:
            anthropic_api_key: Anthropic API key (defaults to settings.ANTHROPIC_API_KEY)
            mcp_server_url: MCP server URL (defaults to DEFAULT_MCP_SERVER_URL)
            model: Claude model to use (user-selectable via UI)
            max_turns: Maximum number of conversation turns for the agentic loop
        """
        api_key = anthropic_api_key or settings.ANTHROPIC_API_KEY
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")

        # Create agent context for cost tracking
        agent_context = AgentContext(
            agent_type="kodosumi_flow",
            agent_name="weekly_report_agent",
            flow_name="weekly_report_sdk",
        )

        # Use APISIX gateway for Anthropic calls (enables cost tracking and centralized routing)
        self.client = create_apisix_anthropic_client(
            agent_context=agent_context,
            api_key=api_key,
        )
        self.mcp_client = MCPClient(mcp_server_url or DEFAULT_MCP_SERVER_URL)
        self.model = model
        self.max_turns = max_turns

        # Initialize LangWatch in manual mode - we use @langwatch_config.trace() decorator
        # to create a single trace per report generation (not per API call)
        langwatch_config.initialize(instrumentation_mode="manual")

        logger.info(f"WeeklyReportAgent initialized with model: {model} (via APISIX gateway)")

    async def _execute_tool(
        self,
        tool_name: str,
        tool_input: dict,
        tool_use_id: str = "",
        turn_number: int = 0,
        session_id: str = "",
    ) -> str:
        """Execute a tool call via the MCP server with full observability.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Tool input parameters
            tool_use_id: Claude's tool_use ID for correlation
            turn_number: Current turn in the agentic loop
            session_id: Session ID for correlation

        Returns:
            Tool result as string
        """
        start_time = time.time()
        logger.info(f"Executing tool: {tool_name} with input: {tool_input}")

        try:
            result = await self.mcp_client.call_tool(tool_name, tool_input)
            execution_time = time.time() - start_time

            # Capture tool call in session collector (synchronous)
            langwatch_config.capture_tool_call_with_response(
                tool_name=tool_name,
                tool_use_id=tool_use_id,
                tool_input=tool_input,
                tool_output=result,
                execution_time=execution_time,
                success=True,
                turn_number=turn_number,
                session_id=session_id,
            )

            logger.debug(f"Tool result: {result[:500]}...")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            # Capture failed tool call in session collector (synchronous)
            langwatch_config.capture_tool_call_with_response(
                tool_name=tool_name,
                tool_use_id=tool_use_id,
                tool_input=tool_input,
                tool_output=None,
                execution_time=execution_time,
                success=False,
                error=str(e),
                turn_number=turn_number,
                session_id=session_id,
            )
            raise

    def _update_trace_with_session_data(self, session_data: dict) -> None:
        """Update the current LangWatch trace with collected session data.

        Uses REST API directly to send traces (more reliable than OTEL SDK).
        """
        # Use REST API directly - this is the reliable method
        success = langwatch_config.send_trace_via_rest_api(session_data)
        if success:
            logger.info(f"Trace sent via REST API for session: {session_data.get('session_id')}")
        else:
            logger.warning(f"Failed to send trace via REST API for session: {session_data.get('session_id')}")

    @langwatch_config.trace(
        name="weekly_report_generation", metadata={"agent": "WeeklyReportAgent"}
    )
    async def generate_report(
        self,
        week_start: datetime,
        week_end: datetime,
        week_label: str,
        include_events: bool = True,
        tracer=None,
    ) -> dict:
        """Generate a weekly regulatory intelligence report.

        Uses Claude's agentic loop to:
        1. Research each category using knowledge graph tools
        2. Synthesize findings into structured sections
        3. Generate executive summary with cross-cutting themes

        Args:
            week_start: Start of the reporting week
            week_end: End of the reporting week
            week_label: Human-readable week label (e.g., "KW48/2025")
            include_events: Whether to include upcoming events section
            tracer: Optional Kodosumi tracer for progress updates

        Returns:
            Dict containing:
                - report_content: Generated markdown report
                - metadata: Generation metadata (model, turns, etc.)
                - tool_calls: List of tool calls made
        """
        # Format dates for the prompt
        week_start_str = week_start.strftime("%Y-%m-%d")
        week_end_str = week_end.strftime("%Y-%m-%d")

        # Get the system prompt
        system_prompt = get_weekly_report_system_prompt(
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

        messages = [{"role": "user", "content": user_message}]

        # Track tool calls for metadata
        tool_calls = []
        turns = 0

        # Generate a unique session ID for this report generation
        report_session_id = f"report_{uuid.uuid4().hex[:12]}"

        # Set thread_id for LangWatch trace grouping
        langwatch_config.set_thread_id(report_session_id)
        # Initialize session collector
        langwatch_config.set_session_query(report_session_id, user_message)

        if tracer:
            await tracer.markdown("**Starting report generation...**\n\nResearching knowledge graph...")

        # Agentic loop
        while turns < self.max_turns:
            turns += 1
            logger.info(f"Agent turn {turns}/{self.max_turns}")

            try:
                # Call Claude with tools
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=8192,
                    system=system_prompt,
                    tools=TOOLS,
                    messages=messages,
                )

                logger.debug(f"Response stop_reason: {response.stop_reason}")

                # Collect tool calls for this turn (for observability)
                tool_calls_in_turn = []
                if response.stop_reason == "tool_use":
                    for block in response.content:
                        if block.type == "tool_use":
                            tool_calls_in_turn.append({"name": block.name, "id": block.id})

                # Capture turn in session collector (synchronous)
                langwatch_config.capture_agentic_turn(
                    turn_number=turns,
                    session_id=report_session_id,
                    stop_reason=response.stop_reason,
                    tool_calls=tool_calls_in_turn,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    model=self.model,
                )

                # Check if Claude wants to use tools
                if response.stop_reason == "tool_use":
                    # Process tool calls
                    assistant_content = response.content
                    tool_results = []

                    for block in assistant_content:
                        if block.type == "tool_use":
                            tool_name = block.name
                            tool_input = block.input
                            tool_use_id = block.id

                            logger.info(f"Tool call: {tool_name}")

                            # Execute the tool via MCP with full observability context
                            try:
                                result = await self._execute_tool(
                                    tool_name=tool_name,
                                    tool_input=tool_input,
                                    tool_use_id=tool_use_id,
                                    turn_number=turns,
                                    session_id=report_session_id,
                                )
                                tool_calls.append({
                                    "tool": tool_name,
                                    "input": tool_input,
                                    "success": True,
                                })

                                if tracer:
                                    await tracer.markdown(f"  - Searched: {tool_input.get('query', tool_name)[:50]}...")

                            except Exception as e:
                                logger.error(f"Tool execution failed: {e}")
                                result = f"Error: {str(e)}"
                                tool_calls.append({
                                    "tool": tool_name,
                                    "input": tool_input,
                                    "success": False,
                                    "error": str(e),
                                })

                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": result,
                            })

                    # Add assistant message and tool results to conversation
                    messages.append({"role": "assistant", "content": assistant_content})
                    messages.append({"role": "user", "content": tool_results})

                elif response.stop_reason == "end_turn":
                    # Claude finished - extract the report
                    report_content = ""
                    for block in response.content:
                        if hasattr(block, "text"):
                            report_content += block.text

                    if tracer:
                        await tracer.markdown("\n**Report generation complete!**")

                    # Finalize session and update LangWatch trace with structured data
                    langwatch_config.set_session_response(report_session_id, report_content)
                    session_data = langwatch_config.finalize_session(report_session_id)
                    if session_data:
                        self._update_trace_with_session_data(session_data)

                    logger.info(f"Report generated successfully in {turns} turns")

                    return {
                        "report_content": report_content,
                        "metadata": {
                            "model": self.model,
                            "turns": turns,
                            "tool_calls_count": len(tool_calls),
                            "week_label": week_label,
                            "week_start": week_start_str,
                            "week_end": week_end_str,
                            "generated_at": datetime.now().isoformat(),
                            "session_id": report_session_id,
                        },
                        "tool_calls": tool_calls,
                    }

                else:
                    # Unexpected stop reason
                    logger.warning(f"Unexpected stop reason: {response.stop_reason}")
                    break

            except Exception as e:
                logger.error(f"Error in agent loop: {e}", exc_info=True)
                raise

        # Max turns reached
        logger.warning(f"Max turns ({self.max_turns}) reached without completion")

        # Try to extract partial report from last response
        partial_content = ""
        if messages and len(messages) > 1:
            last_assistant = None
            for msg in reversed(messages):
                if msg.get("role") == "assistant":
                    last_assistant = msg.get("content", [])
                    break
            if last_assistant:
                for block in last_assistant:
                    if hasattr(block, "text"):
                        partial_content += block.text

        return {
            "report_content": partial_content or "Report generation incomplete - max turns reached.",
            "metadata": {
                "model": self.model,
                "turns": turns,
                "tool_calls_count": len(tool_calls),
                "week_label": week_label,
                "week_start": week_start_str,
                "week_end": week_end_str,
                "generated_at": datetime.now().isoformat(),
                "incomplete": True,
                "session_id": report_session_id,
            },
            "tool_calls": tool_calls,
        }

    async def close(self):
        """Close the agent and cleanup resources."""
        await self.mcp_client.close()
