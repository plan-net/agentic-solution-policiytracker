"""
Pydantic schemas for API request/response models
"""
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field


# ===== Base Schemas =====

class CostSummary(BaseModel):
    """Summary of costs for a period."""
    total_cost_usd: float = Field(..., description="Total cost in USD")
    total_requests: int = Field(..., description="Total number of requests")
    total_tokens: int = Field(..., description="Total tokens used")
    avg_latency_ms: float = Field(..., description="Average latency in milliseconds")
    error_count: int = Field(default=0, description="Number of failed requests")


class CostSummaryResponse(BaseModel):
    """Response for cost summary endpoint."""
    period_start: datetime
    period_end: datetime
    summary: CostSummary
    by_provider: List["ProviderCostBreakdown"] = []
    by_model: List["ModelCostBreakdown"] = []


# ===== Agent Schemas =====

class AgentCostBreakdown(BaseModel):
    """Cost breakdown for a specific agent."""
    agent_type: Optional[str] = Field(None, description="chat_agent, kodosumi_flow, or etl_processor")
    agent_name: Optional[str] = None
    flow_name: Optional[str] = None
    chat_agent_name: Optional[str] = None
    total_cost_usd: float = 0.0
    request_count: int = 0
    total_tokens: int = 0
    avg_latency_ms: float = 0.0
    error_count: int = 0


class AgentCostResponse(BaseModel):
    """Response for agent cost breakdown endpoint."""
    period_start: datetime
    period_end: datetime
    total_cost_usd: float
    agents: List[AgentCostBreakdown]


# ===== Provider/Model Schemas =====

class ProviderCostBreakdown(BaseModel):
    """Cost breakdown by provider."""
    provider: str
    total_cost_usd: float
    request_count: int
    total_tokens: int


class ModelCostBreakdown(BaseModel):
    """Cost breakdown by model."""
    provider: str
    model: str
    total_cost_usd: float
    request_count: int
    prompt_tokens: int = 0
    completion_tokens: int = 0
    avg_cost_per_request: float = 0.0


class ModelCostResponse(BaseModel):
    """Response for model cost breakdown endpoint."""
    period_start: datetime
    period_end: datetime
    total_cost_usd: float
    models: List[ModelCostBreakdown]


# ===== Trend Schemas =====

class TrendDataPoint(BaseModel):
    """Single data point in a cost trend."""
    bucket: datetime
    cost_usd: float
    request_count: int
    total_tokens: int
    avg_latency_ms: float = 0.0
    error_count: int = 0


class TrendResponse(BaseModel):
    """Response for cost trends endpoint."""
    granularity: str = Field(..., description="hourly or daily")
    period_start: datetime
    period_end: datetime
    data_points: List[TrendDataPoint]


# ===== Session Schemas =====

class SessionRequest(BaseModel):
    """Single request in a session."""
    timestamp: datetime
    provider: str
    model: str
    agent_name: Optional[str] = None
    tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    status_code: int = 200


class SessionCostResponse(BaseModel):
    """Response for session cost details endpoint."""
    session_id: str
    total_cost_usd: float
    total_requests: int
    total_tokens: int
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    requests: List[SessionRequest]


# ===== Budget Schemas =====

class BudgetThreshold(BaseModel):
    """Budget threshold configuration."""
    threshold_type: str = Field(..., description="daily, weekly, or monthly")
    threshold_usd: float = Field(..., gt=0)
    scope: Optional[str] = Field(None, description="Optional agent_type or agent_name filter")


class BudgetCheckRequest(BaseModel):
    """Request for budget check endpoint."""
    thresholds: List[BudgetThreshold]


class BudgetStatus(BaseModel):
    """Status of a single budget threshold."""
    threshold_type: str
    threshold_usd: float
    current_spend_usd: float
    remaining_usd: float
    percentage_used: float
    is_exceeded: bool
    scope: Optional[str] = None


class BudgetCheckResponse(BaseModel):
    """Response for budget check endpoint."""
    checked_at: datetime
    statuses: List[BudgetStatus]
    alerts: List[str] = Field(default_factory=list)


# ===== Health Schema =====

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    service: str = "cost-analytics"
    database: str = "unknown"
    version: str = "0.2.0"


# Forward references
CostSummaryResponse.model_rebuild()
