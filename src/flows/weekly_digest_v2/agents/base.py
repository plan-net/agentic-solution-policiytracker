"""
Base state and types for Weekly Digest v2 three-agent architecture.

Defines the shared state TypedDict that flows through:
1. ResearchPlannerAgent - Plans research based on YAML configs
2. ToolExecutorAgent - Executes all tool calls
3. ReportSynthesizerAgent - Generates executive summary and renders report
"""

from datetime import datetime
from typing import Any, Optional, TypedDict

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """
    Structured output for individual tool execution.

    Matches src/chat/agent/agents.py ToolResult for consistency across the codebase.
    Extended with weekly digest specific fields for category tracking.
    """

    tool_name: str = Field(description="Name of the executed tool")
    success: bool = Field(description="Whether execution was successful")
    execution_time: float = Field(description="Actual execution time in seconds")
    parameters_used: dict[str, Any] = Field(description="Parameters passed to the tool")
    output: str = Field(description="Raw output or summary from tool")
    insights: list[str] = Field(description="Key insights extracted from results")
    entities_found: list[dict[str, str]] = Field(
        default_factory=list, description="Entities discovered"
    )
    relationships_discovered: list[dict[str, str]] = Field(
        default_factory=list, description="Relationships found"
    )
    source_citations: list[str] = Field(
        default_factory=list, description="Source references for information"
    )
    temporal_aspects: list[str] = Field(
        default_factory=list, description="Time-related information found"
    )
    quality_score: float = Field(
        default=0.0, description="Quality assessment of results (0.0-1.0)"
    )
    error: Optional[str] = Field(default=None, description="Error message if execution failed")

    # Weekly digest specific additions
    category: str = Field(default="", description="Which category this result belongs to")
    findings: list[dict[str, Any]] = Field(
        default_factory=list, description="Extracted findings after LLM processing"
    )


class ResearchPlanEntry(TypedDict):
    """Structure for a single category research plan."""

    display_name: str
    queries: list[str]
    search_type: str
    entity_types: list[str]
    system_prompt: str
    max_findings: int
    temporal_filter_strategy: str  # 'comprehensive', 'valid_only', 'created_only', 'changes'
    skip_llm_extraction: bool  # If true, skip LLM-based extraction and use raw results
    tool_sequence: list[dict[str, Any]]


class ExecutionMetadata(TypedDict, total=False):
    """Metadata about tool execution performance."""

    total_execution_time: float
    tools_successful: int
    tools_failed: int
    information_quality: str


class WeeklyDigestState(TypedDict, total=False):
    """
    State schema for the Weekly Digest v2 LangGraph workflow.

    This TypedDict flows through the three-agent architecture:
    - ResearchPlannerAgent: Reads YAML configs, creates research_plan
    - ToolExecutorAgent: Executes tools, populates tool_results
    - ReportSynthesizerAgent: Creates executive_summary, final_report
    """

    # === Input (from processor.py) ===
    week_input: str  # User input (KW48 or 2025-11-25)
    include_events: bool  # Whether to include events category

    # === Date Resolution (from resolve_dates node) ===
    week_start: Optional[datetime]  # Monday 00:00 of target week
    week_end: Optional[datetime]  # Sunday 23:59 of target week
    week_label: str  # Formatted label (e.g., "KW48/2025")
    week_number: int  # ISO week number
    year: int  # Year

    # Pre-resolved dates (optional, from app.py validation)
    resolved_week_start: Optional[str]
    resolved_week_end: Optional[str]
    resolved_week_label: Optional[str]
    resolved_week_number: Optional[int]
    resolved_year: Optional[int]

    # === Research Plan (from ResearchPlannerAgent) ===
    research_plan: dict[str, ResearchPlanEntry]  # {category_name: plan}

    # === Tool Results (from ToolExecutorAgent) ===
    tool_results: list[dict[str, Any]]  # List of ToolResult dicts
    executed_tools: list[str]  # Tool names executed
    execution_metadata: ExecutionMetadata

    # === Synthesis (from ReportSynthesizerAgent) ===
    findings_by_category: dict[str, list[dict[str, Any]]]  # {category: [findings]}
    summaries: dict[str, str]  # {category: summary}
    executive_summary: str
    all_entities: list[str]
    synthesis_metadata: dict[str, Any]
    graph_visualization_link: str
    final_report: str

    # === Tracking ===
    current_stage: str  # init, planning, executing, synthesizing, complete, error
    current_agent: str  # research_planner, tool_executor, report_synthesizer
    errors: list[str]
    warnings: list[str]


# Type alias for backwards compatibility
WeeklyDigestStateDict = dict[str, Any]
