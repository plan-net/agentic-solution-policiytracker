from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobRequest(BaseModel):
    job_name: str = Field(..., min_length=1, max_length=100, description="Name of the analysis job")
    input_folder: str = Field(default="./data/input", description="Path to input documents folder")
    context_file: str = Field(
        default="./data/context/client.yaml", description="Path to context file"
    )
    priority_threshold: float = Field(
        default=70.0, ge=0, le=100, description="Minimum priority score"
    )
    include_low_confidence: bool = Field(
        default=False, description="Include low confidence results"
    )
    clustering_enabled: bool = Field(default=True, description="Enable topic clustering")

    @field_validator("input_folder", "context_file")
    @classmethod
    def validate_paths(cls, v: str) -> str:
        if ".." in v or "~" in v:
            raise ValueError("Path traversal not allowed")
        return v


class Job(BaseModel):
    id: str = Field(
        ..., pattern=r"^job_\d{8}_\d{6}_[A-Za-z0-9]{6}$", description="Unique job identifier"
    )
    request: JobRequest
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result_file: Optional[str] = None
    metrics: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=True)


class JobInfo(BaseModel):
    id: str
    job_name: str
    status: JobStatus
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(use_enum_values=True)
