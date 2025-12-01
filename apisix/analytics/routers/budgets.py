"""
Budget checking endpoints
"""
from datetime import datetime
from fastapi import APIRouter
import structlog

from models.schemas import BudgetCheckRequest, BudgetCheckResponse
from services.cost_service import CostService

router = APIRouter(prefix="/budgets", tags=["Budgets"])
logger = structlog.get_logger()
cost_service = CostService()


@router.post("/check", response_model=BudgetCheckResponse)
async def check_budgets(request: BudgetCheckRequest):
    """
    Check current spend against budget thresholds.

    Returns the status of each threshold and any alerts for exceeded budgets.
    """
    statuses = []
    alerts = []

    for threshold in request.thresholds:
        status = await cost_service.check_budget(
            threshold_type=threshold.threshold_type,
            threshold_usd=threshold.threshold_usd,
            scope=threshold.scope,
        )
        statuses.append(status)

        # Generate alerts for exceeded or near-exceeded budgets
        if status.is_exceeded:
            scope_str = f" for {status.scope}" if status.scope else ""
            alerts.append(
                f"EXCEEDED: {status.threshold_type} budget{scope_str} exceeded "
                f"(${status.current_spend_usd:.2f} / ${status.threshold_usd:.2f})"
            )
        elif status.percentage_used >= 80:
            scope_str = f" for {status.scope}" if status.scope else ""
            alerts.append(
                f"WARNING: {status.threshold_type} budget{scope_str} at "
                f"{status.percentage_used:.1f}% "
                f"(${status.current_spend_usd:.2f} / ${status.threshold_usd:.2f})"
            )

    return BudgetCheckResponse(
        checked_at=datetime.now(),
        statuses=statuses,
        alerts=alerts,
    )
