"""
Data Models for Weekly Regulatory Intelligence Digest v2.

Defines the state schema for LangGraph workflow and supporting data structures
for findings, report metadata, and category-specific results.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class FindingPriority(str, Enum):
    """Priority levels for findings."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Finding(BaseModel):
    """
    A single finding/insight discovered during category research.

    Represents a discrete piece of intelligence extracted from the
    knowledge graph and processed by the LLM.

    Attributes:
        title: Brief headline summarizing the finding
        content: Detailed description (2-3 sentences)
        impact: Business/compliance impact statement
        action: Recommended action for stakeholders
        category: Category this finding belongs to
        priority: Priority level (high, medium, low)
        date: Date associated with the finding (if mentioned)
        source: Source document or entity
        entities: Related entity names mentioned
        forward_looking: Whether this includes future dates/deadlines
        metadata: Additional metadata from Graphiti
    """

    title: str = Field(description="Brief title summarizing the finding")
    content: str = Field(description="Detailed description of the finding")
    impact: Optional[str] = Field(
        default=None,
        description="Business/compliance impact statement",
    )
    action: Optional[str] = Field(
        default=None,
        description="Recommended action for stakeholders",
    )
    category: str = Field(description="Category this finding belongs to")
    priority: FindingPriority = Field(
        default=FindingPriority.MEDIUM,
        description="Priority level of the finding",
    )
    date: Optional[datetime] = Field(
        default=None,
        description="Date associated with the finding",
    )
    source: Optional[str] = Field(
        default=None,
        description="Source document or entity",
    )
    entities: list[str] = Field(
        default_factory=list,
        description="Related entities mentioned",
    )
    forward_looking: bool = Field(
        default=False,
        description="Whether this includes future dates/deadlines",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata from Graphiti",
    )

    class Config:
        use_enum_values = True


class CategoryResearchResult(BaseModel):
    """
    Result from a category research agent.

    Includes execution_metadata for observability and debugging.

    Attributes:
        category: Category name (e.g., "legislative")
        findings: List of extracted findings
        summary: Brief summary of findings
        query_used: Graphiti queries used
        execution_time: Query execution time in seconds
        success: Whether research completed successfully
        error: Error message if failed
        execution_metadata: Structured execution metadata
    """

    category: str
    findings: list[Finding] = Field(default_factory=list)
    summary: str = Field(default="", description="Brief summary of findings")
    query_used: str = Field(default="", description="Graphiti query used")
    execution_time: float = Field(
        default=0.0,
        description="Query execution time in seconds",
    )
    success: bool = Field(default=True)
    error: Optional[str] = Field(default=None)
    execution_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured execution metadata for observability",
    )

    class Config:
        use_enum_values = True


class ReportMetadata(BaseModel):
    """
    Metadata for the generated weekly report.

    Captures timing, coverage, and quality metrics for the report.

    Attributes:
        week_number: ISO week number
        year: Year
        week_label: Formatted week label (e.g., 'KW48/2025')
        week_start: Monday of the week
        week_end: Sunday of the week
        generated_at: Timestamp when report was generated
        total_findings: Total findings across all categories
        categories_completed: Number of categories successfully researched
        processing_time_seconds: Total processing time
        graphiti_queries_executed: Number of Graphiti queries executed
    """

    week_number: int = Field(description="ISO week number")
    year: int = Field(description="Year")
    week_label: str = Field(description="Formatted week label")
    week_start: datetime = Field(description="Monday of the week")
    week_end: datetime = Field(description="Sunday of the week")
    generated_at: datetime = Field(default_factory=datetime.now)
    total_findings: int = Field(default=0)
    categories_completed: int = Field(default=0)
    processing_time_seconds: float = Field(default=0.0)
    graphiti_queries_executed: int = Field(default=0)


class WeeklyDigestState(BaseModel):
    """
    State schema for the Weekly Digest LangGraph workflow.

    This state is passed between nodes during workflow execution.
    Uses explicit category fields to avoid dynamic key issues.

    Attributes:
        week_input: User input (KW48 or 2025-11-25)
        week_number: Resolved ISO week number
        year: Resolved year
        week_start: Monday 00:00 of the target week
        week_end: Sunday 23:59 of the target week
        week_label: Formatted week label
        include_events: Whether to include forward-looking events
        *_findings: Findings for each category
        *_summary: Summary for each category
        executive_summary: Generated executive summary
        final_report: Final rendered report markdown
        graph_visualization_link: URL to graph visualization
        all_entities: All entities discovered across categories
        current_stage: Current workflow stage
        completed_categories: List of completed category names
        errors: List of error messages
        warnings: List of warning messages
        metadata: Report metadata
    """

    # Input
    week_input: str = Field(
        default="",
        description="User input: calendar week (KW48) or Monday date (2025-11-25)",
    )
    week_number: int = Field(default=0, description="Resolved ISO week number")
    year: int = Field(default=0, description="Resolved year")
    include_events: bool = Field(
        default=True,
        description="Whether to include forward-looking events",
    )

    # Date Resolution
    week_start: Optional[datetime] = Field(
        default=None,
        description="Monday 00:00 of the target week",
    )
    week_end: Optional[datetime] = Field(
        default=None,
        description="Sunday 23:59 of the target week",
    )
    week_label: str = Field(default="", description="Formatted week label")

    # Category Findings (explicit fields for type safety)
    legislative_findings: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Legislative & regulatory findings",
    )
    personnel_findings: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Personnel change findings",
    )
    compliance_findings: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Industry & compliance findings",
    )
    policy_findings: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Government policy findings",
    )
    events_findings: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Upcoming events & deadlines",
    )

    # Category Summaries
    legislative_summary: str = Field(default="")
    personnel_summary: str = Field(default="")
    compliance_summary: str = Field(default="")
    policy_summary: str = Field(default="")
    events_summary: str = Field(default="")

    # Synthesis
    executive_summary: str = Field(default="", description="Executive summary")
    report_sections: dict[str, str] = Field(
        default_factory=dict,
        description="Rendered markdown sections",
    )
    final_report: str = Field(default="", description="Final rendered report")

    # Graph Visualization
    graph_visualization_link: str = Field(
        default="",
        description="URL to graph visualization",
    )
    all_entities: list[str] = Field(
        default_factory=list,
        description="All entities discovered across categories",
    )

    # Execution Tracking
    current_stage: str = Field(default="init", description="Current workflow stage")
    completed_categories: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    # Metadata
    metadata: Optional[dict[str, Any]] = Field(default=None)

    class Config:
        arbitrary_types_allowed = True

    def get_findings_for_category(self, category: str) -> list[dict[str, Any]]:
        """Get findings for a specific category."""
        return getattr(self, f"{category}_findings", [])

    def get_summary_for_category(self, category: str) -> str:
        """Get summary for a specific category."""
        return getattr(self, f"{category}_summary", "")


# Type alias for LangGraph state (dict-based)
WeeklyDigestStateDict = dict[str, Any]


def state_to_dict(state: WeeklyDigestState) -> WeeklyDigestStateDict:
    """Convert Pydantic model to dict for LangGraph compatibility."""
    return state.model_dump()


def dict_to_state(data: WeeklyDigestStateDict) -> WeeklyDigestState:
    """Convert dict back to Pydantic model."""
    return WeeklyDigestState(**data)
