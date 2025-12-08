"""
Base Agent Classes for Report Generation.

Provides abstract base classes that define the interface for all report agents,
enabling consistent execution patterns, configuration handling, and observability
across different report types (weekly, monthly, topic-specific).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Generic, Optional, TypeVar

from pydantic import BaseModel

if TYPE_CHECKING:
    from src.core.config.category_config import CategoryConfig
    from src.core.config.report_config import ReportConfig
    from src.core.observability.tracer import AgentTracer
    from src.core.renderers.base_renderer import BaseRenderer


# Generic type for state dictionaries
TState = TypeVar("TState", bound=dict)


class ReportType(str, Enum):
    """Supported report types for the modular agent framework."""

    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    TOPIC_SPECIFIC = "topic_specific"
    CUSTOM = "custom"


@dataclass
class AgentResult:
    """
    Standardized result from any agent operation.

    Provides a consistent interface for returning results from agent
    processing steps, including success/failure status, state updates,
    and execution metadata.

    Attributes:
        success: Whether the operation completed successfully
        updated_state: The state dictionary with any updates from this operation
        data: Additional data produced by the operation
        message: Human-readable message describing the result
        execution_time: Time taken for the operation in seconds
        metadata: Additional metadata for observability and debugging
    """

    success: bool
    updated_state: dict[str, Any]
    data: dict[str, Any]
    message: str = ""
    execution_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    @classmethod
    def success_result(
        cls,
        updated_state: dict[str, Any],
        data: dict[str, Any] = None,
        message: str = "Operation completed successfully",
        execution_time: float = 0.0,
        metadata: dict[str, Any] = None,
    ) -> "AgentResult":
        """Factory method for creating a successful result."""
        return cls(
            success=True,
            updated_state=updated_state,
            data=data or {},
            message=message,
            execution_time=execution_time,
            metadata=metadata or {},
        )

    @classmethod
    def failure_result(
        cls,
        state: dict[str, Any],
        error: str,
        execution_time: float = 0.0,
        metadata: dict[str, Any] = None,
    ) -> "AgentResult":
        """Factory method for creating a failed result."""
        # Add error to state
        errors = state.get("errors", [])
        errors.append(error)
        updated = {**state, "errors": errors}

        return cls(
            success=False,
            updated_state=updated,
            data={},
            message=error,
            execution_time=execution_time,
            metadata=metadata or {},
        )


class BaseReportAgent(ABC, Generic[TState]):
    """
    Abstract base class for all report generation agents.

    Provides a consistent interface for report agents with support for:
    - Configuration-driven behavior via ReportConfig
    - Unified observability via AgentTracer
    - Category-based research patterns
    - Pluggable output rendering

    Subclasses must implement:
    - execute(): Main workflow execution
    - get_categories(): Return configured research categories
    - get_renderer(): Return the output renderer

    Example:
        class WeeklyDigestAgent(BaseReportAgent):
            async def execute(self, inputs):
                # Implementation
                pass

            def get_categories(self):
                return self._load_categories()

            def get_renderer(self):
                return MarkdownRenderer(self.template_dir)
    """

    def __init__(
        self,
        report_type: ReportType,
        config: "ReportConfig",
        tracer: "AgentTracer",
    ):
        """
        Initialize the base report agent.

        Args:
            report_type: Type of report this agent generates
            config: Configuration for the report
            tracer: Unified tracer for observability
        """
        self.report_type = report_type
        self.config = config
        self.tracer = tracer
        self._start_time: Optional[datetime] = None

    @abstractmethod
    async def execute(self, inputs: dict[str, Any]) -> AgentResult:
        """
        Execute the report generation workflow.

        This is the main entry point for report generation. Implementations
        should orchestrate the full workflow including:
        - Input validation and date resolution
        - Category research
        - Result synthesis
        - Report rendering

        Args:
            inputs: Input parameters for report generation (e.g., week number, year)

        Returns:
            AgentResult with the generated report in data["final_report"]
        """
        pass

    @abstractmethod
    def get_categories(self) -> list["CategoryConfig"]:
        """
        Return configured categories for this report type.

        Categories define the research areas for the report (e.g., legislative,
        personnel, compliance, policy, events).

        Returns:
            List of CategoryConfig objects defining research categories
        """
        pass

    @abstractmethod
    def get_renderer(self) -> "BaseRenderer":
        """
        Return the configured output renderer.

        The renderer is responsible for converting structured findings
        into the final output format (markdown, PDF, email, etc.).

        Returns:
            BaseRenderer instance for output generation
        """
        pass

    async def _start_execution(self) -> None:
        """Mark the start of execution for timing."""
        self._start_time = datetime.now()
        await self.tracer.markdown(
            f"## {self.report_type.value.title()} Report Generation\n"
            f"**Started:** {self._start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        )

    def _get_execution_time(self) -> float:
        """Calculate execution time in seconds."""
        if self._start_time is None:
            return 0.0
        return (datetime.now() - self._start_time).total_seconds()

    async def _log_completion(self, success: bool, message: str = "") -> None:
        """Log completion status."""
        status = "completed successfully" if success else "failed"
        execution_time = self._get_execution_time()
        await self.tracer.markdown(
            f"\n**Report generation {status}** in {execution_time:.2f}s\n"
        )
        if message:
            await self.tracer.markdown(f"*{message}*\n")
