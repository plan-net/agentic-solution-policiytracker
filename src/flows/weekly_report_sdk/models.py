"""Data models for the Weekly Report SDK flow.

Extends models from weekly_digest_v2 where applicable.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ReportModel(str, Enum):
    """Available Claude models for report generation."""

    SONNET_4 = "claude-sonnet-4-20250514"
    OPUS_4 = "claude-opus-4-20250514"


class ToolCall(BaseModel):
    """Record of a tool call made during report generation."""

    tool: str
    input: dict[str, Any]
    success: bool = True
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ReportMetadata(BaseModel):
    """Metadata about the report generation process."""

    model: str
    turns: int
    tool_calls_count: int
    week_label: str
    week_start: str
    week_end: str
    generated_at: str
    incomplete: bool = False


class WeeklyReportResult(BaseModel):
    """Result of the weekly report generation."""

    report_content: str
    metadata: ReportMetadata
    tool_calls: list[ToolCall] = Field(default_factory=list)


class ReportGenerationRequest(BaseModel):
    """Request to generate a weekly report."""

    week_input: str = ""
    claude_model: ReportModel = ReportModel.SONNET_4
    include_events: bool = True

    # Pre-resolved date values (optional, computed if not provided)
    resolved_week_start: Optional[str] = None
    resolved_week_end: Optional[str] = None
    resolved_week_label: Optional[str] = None
    resolved_week_number: Optional[int] = None
    resolved_year: Optional[int] = None


class ReportGenerationResponse(BaseModel):
    """Response from report generation."""

    success: bool
    report_id: Optional[str] = None
    report_content: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[ReportMetadata] = None
