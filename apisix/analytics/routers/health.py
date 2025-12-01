"""
Health check endpoint
"""
from fastapi import APIRouter
import structlog

from database import get_pool
from models.schemas import HealthResponse
from config import get_settings

router = APIRouter(tags=["Health"])
logger = structlog.get_logger()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service health including database connectivity."""
    settings = get_settings()
    db_status = "unknown"

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_status = "connected"
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        db_status = f"error: {str(e)}"

    return HealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        service="cost-analytics",
        database=db_status,
        version=settings.app_version,
    )
