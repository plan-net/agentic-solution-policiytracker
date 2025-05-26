from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .scoring import PriorityLevel, ScoringResult


class TopicCluster(BaseModel):
    topic_name: str
    topic_description: str
    document_count: int = Field(..., ge=0)
    average_score: float = Field(..., ge=0, le=100)
    documents: list[ScoringResult]
    key_themes: list[str] = Field(default_factory=list)


class PriorityQueue(BaseModel):
    priority_level: PriorityLevel
    document_count: int = Field(..., ge=0)
    documents: list[ScoringResult]

    model_config = ConfigDict(use_enum_values=True)


class ReportSummary(BaseModel):
    total_documents_analyzed: int = Field(..., ge=0)
    high_priority_count: int = Field(..., ge=0)
    key_findings: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    processing_time_minutes: float = Field(..., ge=0)
    confidence_overview: dict[str, int] = Field(default_factory=dict)


class ReportData(BaseModel):
    job_id: str
    job_name: str
    generation_timestamp: datetime
    summary: ReportSummary
    priority_queues: list[PriorityQueue]
    topic_clusters: list[TopicCluster]
    all_results: list[ScoringResult]
    failed_documents: list[dict[str, str]] = Field(default_factory=list)
    context_file_used: str
    parameters_used: dict[str, Any] = Field(default_factory=dict)
    performance_metrics: dict[str, float] = Field(default_factory=dict)
