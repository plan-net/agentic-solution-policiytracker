from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.models.content import ProcessedContent
from src.models.job import JobRequest
from src.models.report import ReportData
from src.models.scoring import ScoringResult


class WorkflowState(BaseModel):
    """Minimal state schema for LangGraph workflow."""
    
    job_id: str = Field(..., description="Unique job identifier")
    job_request: JobRequest = Field(..., description="Original job request")
    documents: List[ProcessedContent] = Field(default_factory=list, description="Processed documents")
    scoring_results: List[ScoringResult] = Field(default_factory=list, description="Scoring results")
    report_data: Optional[ReportData] = Field(default=None, description="Report data")
    context: Dict[str, Any] = Field(default_factory=dict, description="Client context data")
    errors: List[str] = Field(default_factory=list, description="Processing errors")
    current_progress: Dict[str, Any] = Field(default_factory=dict, description="Progress tracking")
    
    # Additional workflow state
    file_paths: List[str] = Field(default_factory=list, description="Discovered file paths")
    failed_documents: List[Dict[str, str]] = Field(default_factory=list, description="Failed processing")
    report_file_path: Optional[str] = Field(default=None, description="Generated report file path")
    
    class Config:
        arbitrary_types_allowed = True