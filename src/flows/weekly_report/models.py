"""
Data models for Weekly Regulatory Intelligence Digest.

Defines the state schema for LangGraph workflow and supporting data structures
for findings, report metadata, and category-specific results.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ReportCategory(str, Enum):
    """Categories for the weekly report sections."""

    LEGISLATIVE = "legislative"
    PERSONNEL = "personnel"
    COMPLIANCE = "compliance"
    POLICY = "policy"
    EVENTS = "events"


class FindingPriority(str, Enum):
    """Priority levels for findings."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Finding(BaseModel):
    """A single finding/insight discovered during category research."""

    title: str = Field(description="Brief title summarizing the finding")
    content: str = Field(description="Detailed description of the finding")
    category: ReportCategory = Field(description="Category this finding belongs to")
    priority: FindingPriority = Field(
        default=FindingPriority.MEDIUM, description="Priority level of the finding"
    )
    date: Optional[datetime] = Field(
        default=None, description="Date associated with the finding"
    )
    source: Optional[str] = Field(
        default=None, description="Source document or entity"
    )
    entities: list[str] = Field(
        default_factory=list, description="Related entities mentioned"
    )
    forward_looking: bool = Field(
        default=False, description="Whether this includes future dates/deadlines"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata from Graphiti"
    )

    class Config:
        use_enum_values = True


class CategoryResearchResult(BaseModel):
    """Result from a category research agent."""

    category: ReportCategory
    findings: list[Finding] = Field(default_factory=list)
    summary: str = Field(default="", description="Brief summary of findings")
    query_used: str = Field(default="", description="Graphiti query used")
    execution_time: float = Field(default=0.0, description="Query execution time in seconds")
    success: bool = Field(default=True)
    error: Optional[str] = Field(default=None)

    class Config:
        use_enum_values = True


class ReportMetadata(BaseModel):
    """Metadata for the generated weekly report."""

    week_number: int = Field(description="ISO week number")
    year: int = Field(description="Year")
    week_label: str = Field(description="Formatted week label (e.g., 'KW48/2025')")
    week_start: datetime = Field(description="Monday of the week")
    week_end: datetime = Field(description="Sunday of the week")
    generated_at: datetime = Field(default_factory=datetime.now)
    total_findings: int = Field(default=0)
    categories_completed: int = Field(default=0)
    processing_time_seconds: float = Field(default=0.0)
    graphiti_queries_executed: int = Field(default=0)


class WeeklyReportState(BaseModel):
    """
    State schema for the Weekly Report LangGraph workflow.

    This state is passed between agents during the workflow execution.
    """

    # Input
    week_input: str = Field(
        description="User input: calendar week (KW48) or Monday date (2025-11-25)"
    )

    # Date Resolution
    week_start: Optional[datetime] = Field(
        default=None, description="Monday 00:00 of the target week"
    )
    week_end: Optional[datetime] = Field(
        default=None, description="Sunday 23:59 of the target week"
    )
    week_label: str = Field(default="", description="Formatted week label")
    week_number: int = Field(default=0, description="ISO week number")
    year: int = Field(default=0, description="Year of the week")

    # Category Research Results
    legislative_findings: list[Finding] = Field(
        default_factory=list, description="Legislative & regulatory findings"
    )
    personnel_findings: list[Finding] = Field(
        default_factory=list, description="Personnel change findings"
    )
    compliance_findings: list[Finding] = Field(
        default_factory=list, description="Industry & compliance findings"
    )
    policy_findings: list[Finding] = Field(
        default_factory=list, description="Government policy findings"
    )
    events_findings: list[Finding] = Field(
        default_factory=list, description="Upcoming events & deadlines"
    )

    # Category Summaries
    legislative_summary: str = Field(default="")
    personnel_summary: str = Field(default="")
    compliance_summary: str = Field(default="")
    policy_summary: str = Field(default="")
    events_summary: str = Field(default="")

    # Synthesis
    report_sections: dict[str, str] = Field(
        default_factory=dict, description="Rendered markdown sections"
    )
    executive_summary: str = Field(default="", description="Executive summary")

    # Output
    final_report: str = Field(default="", description="Final rendered report")
    metadata: Optional[ReportMetadata] = Field(default=None)

    # Execution Tracking
    current_stage: str = Field(default="init", description="Current workflow stage")
    completed_categories: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True


# Type alias for LangGraph state (dict-based)
WeeklyReportStateDict = dict[str, Any]


def state_to_dict(state: WeeklyReportState) -> WeeklyReportStateDict:
    """Convert Pydantic model to dict for LangGraph compatibility."""
    return state.model_dump()


def dict_to_state(data: WeeklyReportStateDict) -> WeeklyReportState:
    """Convert dict back to Pydantic model."""
    return WeeklyReportState(**data)
