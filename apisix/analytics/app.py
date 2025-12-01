"""
Cost Analytics API - FastAPI Application
Policy Tracker v0.2.0

Provides REST endpoints for querying LLM cost data from TimescaleDB.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from config import get_settings
from database import init_db_pool, close_db_pool
from routers import health_router, costs_router, budgets_router, ingest_router

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager."""
    # Startup
    logger.info("Starting Cost Analytics API", version=settings.app_version)
    try:
        await init_db_pool()
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.error("Failed to initialize database pool", error=str(e))
        raise

    yield

    # Shutdown
    logger.info("Shutting down Cost Analytics API")
    await close_db_pool()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
## LLM Cost Analytics API

This API provides endpoints for querying LLM usage costs tracked by the APISIX gateway.

### Features:
- **Cost Summary**: Overall spending by period
- **Agent Breakdown**: Costs attributed to specific agents/flows
- **Model Breakdown**: Costs by LLM model
- **Trends**: Hourly and daily cost trends
- **Session Details**: Costs for specific sessions
- **Budget Monitoring**: Check spend against thresholds

### Data Source
All data is collected by the APISIX `llm-cost-tracker` plugin and stored in TimescaleDB.
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router)
app.include_router(costs_router, prefix=settings.api_prefix)
app.include_router(budgets_router, prefix=settings.api_prefix)
app.include_router(ingest_router, prefix=settings.api_prefix)


@app.get("/")
async def root():
    """Root endpoint - redirect to docs."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
