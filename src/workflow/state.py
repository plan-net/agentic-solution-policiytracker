from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.models.content import ProcessedContent
from src.models.job import JobRequest
from src.models.report import ReportData
from src.models.scoring import ScoringResult


class WorkflowState(BaseModel):
    """Minimal state schema for LangGraph workflow."""

    job_id: str = Field(..., description="Unique job identifier")
    job_request: JobRequest = Field(..., description="Original job request")
    use_azure: bool = Field(
        default=False, description="Runtime storage mode: True for Azure, False for local"
    )
    documents: list[ProcessedContent] = Field(
        default_factory=list, description="Processed documents"
    )
    scoring_results: list[ScoringResult] = Field(
        default_factory=list, description="Scoring results"
    )
    report_data: Optional[ReportData] = Field(default=None, description="Report data")
    context: dict[str, Any] = Field(default_factory=dict, description="Client context data")
    errors: list[str] = Field(default_factory=list, description="Processing errors")
    current_progress: dict[str, Any] = Field(default_factory=dict, description="Progress tracking")

    # Additional workflow state
    file_paths: list[str] = Field(default_factory=list, description="Discovered file paths")
    failed_documents: list[dict[str, str]] = Field(
        default_factory=list, description="Failed processing"
    )
    report_file_path: Optional[str] = Field(default=None, description="Generated report file path")

    model_config = ConfigDict(arbitrary_types_allowed=True)
