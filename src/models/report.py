from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, Field, ConfigDict

from .scoring import PriorityLevel, ScoringResult


class TopicCluster(BaseModel):
    topic_name: str
    topic_description: str
    document_count: int = Field(..., ge=0)
    average_score: float = Field(..., ge=0, le=100)
    documents: List[ScoringResult]
    key_themes: List[str] = Field(default_factory=list)


class PriorityQueue(BaseModel):
    priority_level: PriorityLevel
    document_count: int = Field(..., ge=0)
    documents: List[ScoringResult]

    model_config = ConfigDict(use_enum_values=True)


class ReportSummary(BaseModel):
    total_documents_analyzed: int = Field(..., ge=0)
    high_priority_count: int = Field(..., ge=0)
    key_findings: List[str] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    processing_time_minutes: float = Field(..., ge=0)
    confidence_overview: Dict[str, int] = Field(default_factory=dict)


class ReportData(BaseModel):
    job_id: str
    job_name: str
    generation_timestamp: datetime
    summary: ReportSummary
    priority_queues: List[PriorityQueue]
    topic_clusters: List[TopicCluster]
    all_results: List[ScoringResult]
    failed_documents: List[Dict[str, str]] = Field(default_factory=list)
    context_file_used: str
    parameters_used: Dict[str, Any] = Field(default_factory=dict)
    performance_metrics: Dict[str, float] = Field(default_factory=dict)
