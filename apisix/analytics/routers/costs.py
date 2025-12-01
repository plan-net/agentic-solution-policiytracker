"""
Cost query endpoints
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query
import structlog

from models.schemas import (
    CostSummaryResponse, AgentCostResponse, ModelCostResponse,
    TrendResponse, SessionCostResponse
)
from services.cost_service import CostService

router = APIRouter(prefix="/costs", tags=["Costs"])
logger = structlog.get_logger()
cost_service = CostService()


@router.get("/summary", response_model=CostSummaryResponse)
async def get_cost_summary(
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    days: int = Query(7, ge=1, le=365, description="Number of days to look back"),
):
    """
    Get overall cost summary for a period.

    Returns total costs, request count, token usage, and breakdowns by provider and model.
    """
    summary, period_start, period_end = await cost_service.get_summary(
        start_date=start_date,
        end_date=end_date,
        days=days,
    )

    by_provider = await cost_service.get_by_provider(
        start_date=period_start,
        end_date=period_end,
    )

    models, _, _, _ = await cost_service.get_by_model(
        start_date=period_start,
        end_date=period_end,
    )

    return CostSummaryResponse(
        period_start=period_start,
        period_end=period_end,
        summary=summary,
        by_provider=by_provider,
        by_model=models[:10],  # Top 10 models
    )


@router.get("/by-agent", response_model=AgentCostResponse)
async def get_costs_by_agent(
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    days: int = Query(7, ge=1, le=365, description="Number of days to look back"),
    agent_type: Optional[str] = Query(None, description="Filter by agent type"),
    flow_name: Optional[str] = Query(None, description="Filter by flow name"),
):
    """
    Get cost breakdown by agent.

    Returns costs grouped by agent_type, agent_name, flow_name, and chat_agent_name.
    """
    agents, total_cost, period_start, period_end = await cost_service.get_by_agent(
        start_date=start_date,
        end_date=end_date,
        days=days,
        agent_type=agent_type,
        flow_name=flow_name,
    )

    return AgentCostResponse(
        period_start=period_start,
        period_end=period_end,
        total_cost_usd=total_cost,
        agents=agents,
    )


@router.get("/by-model", response_model=ModelCostResponse)
async def get_costs_by_model(
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    days: int = Query(7, ge=1, le=365, description="Number of days to look back"),
    provider: Optional[str] = Query(None, description="Filter by provider (openai, anthropic)"),
):
    """
    Get cost breakdown by LLM model.

    Returns costs grouped by provider and model.
    """
    models, total_cost, period_start, period_end = await cost_service.get_by_model(
        start_date=start_date,
        end_date=end_date,
        days=days,
        provider=provider,
    )

    return ModelCostResponse(
        period_start=period_start,
        period_end=period_end,
        total_cost_usd=total_cost,
        models=models,
    )


@router.get("/trends", response_model=TrendResponse)
async def get_cost_trends(
    granularity: str = Query("daily", description="hourly or daily"),
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    days: int = Query(7, ge=1, le=365, description="Number of days to look back"),
    agent_type: Optional[str] = Query(None, description="Filter by agent type"),
):
    """
    Get cost trends over time.

    Uses TimescaleDB continuous aggregates for efficient queries.
    """
    if granularity not in ["hourly", "daily"]:
        granularity = "daily"

    data_points, period_start, period_end = await cost_service.get_trends(
        granularity=granularity,
        start_date=start_date,
        end_date=end_date,
        days=days,
        agent_type=agent_type,
    )

    return TrendResponse(
        granularity=granularity,
        period_start=period_start,
        period_end=period_end,
        data_points=data_points,
    )


@router.get("/sessions/{session_id}", response_model=SessionCostResponse)
async def get_session_costs(session_id: str):
    """
    Get cost details for a specific session.

    Returns all requests in the session with their costs.
    """
    requests, total_cost, total_requests, total_tokens = await cost_service.get_session_costs(
        session_id=session_id
    )

    start_time = requests[0].timestamp if requests else None
    end_time = requests[-1].timestamp if requests else None

    return SessionCostResponse(
        session_id=session_id,
        total_cost_usd=total_cost,
        total_requests=total_requests,
        total_tokens=total_tokens,
        start_time=start_time,
        end_time=end_time,
        requests=requests,
    )
