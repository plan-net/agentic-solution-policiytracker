"""
Agent Mixins for Cross-Cutting Concerns.

Provides mixin classes that add common functionality to agents:
- StreamingMixin: Real-time progress updates
- ObservabilityMixin: LangWatch and metrics integration
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from src.core.observability.tracer import AgentTracer


class StreamingMixin:
    """
    Mixin for real-time progress streaming to Kodosumi UI.

    Provides methods for emitting structured progress updates during
    agent execution, including thinking updates, progress indicators,
    and agent transitions.

    Usage:
        class MyAgent(BaseReportAgent, StreamingMixin):
            async def execute(self, inputs):
                await self.stream_thinking("Analyzing input...")
                await self.stream_progress("Research", 0.5)
                await self.stream_agent_transition("research", "synthesis")
    """

    tracer: "AgentTracer"  # Must be set by the implementing class

    async def stream_thinking(
        self,
        thought: str,
        agent_name: Optional[str] = None,
    ) -> None:
        """
        Emit a thinking/reasoning update.

        Args:
            thought: The reasoning or thought to display
            agent_name: Optional agent name for attribution
        """
        prefix = f"**{agent_name}:** " if agent_name else ""
        await self.tracer.markdown(f"{prefix}{thought}\n")

    async def stream_progress(
        self,
        stage: str,
        percentage: Optional[float] = None,
        details: Optional[str] = None,
    ) -> None:
        """
        Emit a progress indicator.

        Args:
            stage: Current stage name
            percentage: Optional progress percentage (0.0-1.0)
            details: Optional additional details
        """
        progress_text = f"- **{stage}**"
        if percentage is not None:
            progress_text += f" ({percentage * 100:.0f}%)"
        if details:
            progress_text += f": {details}"
        await self.tracer.markdown(f"{progress_text}\n")

    async def stream_agent_transition(
        self,
        from_agent: str,
        to_agent: str,
        reason: Optional[str] = None,
    ) -> None:
        """
        Emit an agent transition notification.

        Args:
            from_agent: Agent we're transitioning from
            to_agent: Agent we're transitioning to
            reason: Optional reason for the transition
        """
        display_name = to_agent.replace("_", " ").title()
        await self.tracer.markdown(f"\n### {display_name}\n")
        if reason:
            await self.tracer.markdown(f"*{reason}*\n")

    async def stream_category_start(self, category: str) -> None:
        """
        Emit notification that category research is starting.

        Args:
            category: Category display name
        """
        await self.tracer.markdown(f"### Researching {category}\n")

    async def stream_findings_summary(
        self,
        category: str,
        total: int,
        high_priority: int = 0,
    ) -> None:
        """
        Emit summary of findings for a category.

        Args:
            category: Category display name
            total: Total number of findings
            high_priority: Number of high-priority findings
        """
        summary = f"**{category}:** {total} findings"
        if high_priority > 0:
            summary += f" ({high_priority} high priority)"
        await self.tracer.markdown(f"{summary}\n")

    async def stream_tool_execution(
        self,
        tool_name: str,
        status: str,
        execution_time: Optional[float] = None,
    ) -> None:
        """
        Emit tool execution status.

        Args:
            tool_name: Name of the tool being executed
            status: Status message (starting, complete, failed)
            execution_time: Optional execution time in seconds
        """
        emoji = "+" if "complete" in status.lower() else "..."
        if "fail" in status.lower():
            emoji = "x"

        text = f"  {emoji} `{tool_name}`: {status}"
        if execution_time is not None:
            text += f" ({execution_time:.2f}s)"
        await self.tracer.markdown(f"{text}\n")


class ObservabilityMixin:
    """
    Mixin for enhanced observability and metrics.

    Provides methods for capturing tool executions, LLM calls,
    and performance metrics for LangWatch integration.

    Usage:
        class MyAgent(BaseReportAgent, ObservabilityMixin):
            async def execute(self, inputs):
                with self.observe_operation("research"):
                    # Research logic
                    pass
    """

    tracer: "AgentTracer"  # Must be set by the implementing class

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

        Args:
            tool_name: Name of the tool
            tool_input: Input parameters to the tool
            tool_output: Output from the tool
            execution_time: Execution time in seconds
            success: Whether the execution was successful
            error: Optional error message if failed
        """
        await self.tracer.capture_tool_execution(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            execution_time=execution_time,
            success=success,
            error=error,
        )

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
            purpose: Purpose of the LLM call (e.g., "finding_extraction")
        """
        await self.tracer.capture_llm_call(
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            execution_time=execution_time,
            purpose=purpose,
        )

    async def start_span(
        self,
        name: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Start a new tracing span.

        Args:
            name: Span name
            metadata: Optional metadata to attach

        Returns:
            Span ID for ending the span
        """
        return await self.tracer.start_span(name, metadata)

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
            error: Optional error message
        """
        await self.tracer.end_span(span_id, success, error)
