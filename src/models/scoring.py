from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field, field_validator, computed_field


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PriorityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class DimensionScore(BaseModel):
    dimension_name: str
    score: float = Field(..., ge=0, le=100, description="Score between 0-100")
    weight: float = Field(..., ge=0, le=1, description="Weight between 0-1")
    justification: str
    evidence_snippets: List[str] = Field(default_factory=list, max_items=3)


class ScoringResult(BaseModel):
    document_id: str
    master_score: float = Field(..., ge=0, le=100, description="Overall score 0-100")
    dimension_scores: Dict[str, DimensionScore]
    confidence_score: float = Field(..., ge=0, le=1, description="Confidence 0-1")
    topic_clusters: List[str] = Field(default_factory=list, max_items=5)
    scoring_timestamp: datetime
    processing_time_ms: float = Field(..., ge=0)
    overall_justification: str
    key_factors: List[str] = Field(default_factory=list)

    @computed_field
    @property
    def confidence_level(self) -> ConfidenceLevel:
        """Auto-calculate confidence level from confidence score."""
        if self.confidence_score >= 0.8:
            return ConfidenceLevel.HIGH
        elif self.confidence_score >= 0.6:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    @computed_field
    @property
    def priority_level(self) -> PriorityLevel:
        """Auto-calculate priority level from master score."""
        if self.master_score >= 90:
            return PriorityLevel.CRITICAL
        elif self.master_score >= 75:
            return PriorityLevel.HIGH
        elif self.master_score >= 50:
            return PriorityLevel.MEDIUM
        elif self.master_score >= 25:
            return PriorityLevel.LOW
        else:
            return PriorityLevel.INFORMATIONAL

    class Config:
        use_enum_values = True


class BatchScoringResults(BaseModel):
    job_id: str
    total_documents: int = Field(..., ge=0)
    scored_documents: int = Field(..., ge=0)
    failed_documents: int = Field(..., ge=0)
    results: List[ScoringResult]
    average_score: float = Field(..., ge=0, le=100)
    score_distribution: Dict[str, int] = Field(default_factory=dict)
    topic_distribution: Dict[str, int] = Field(default_factory=dict)
    total_processing_time_seconds: float = Field(..., ge=0)
    average_processing_time_ms: float = Field(..., ge=0)
