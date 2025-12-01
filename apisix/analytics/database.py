"""
Database connection management for TimescaleDB
"""
import asyncpg
from typing import Optional
from contextlib import asynccontextmanager
import structlog

from config import get_settings

logger = structlog.get_logger()

# Global connection pool
_pool: Optional[asyncpg.Pool] = None


async def init_db_pool() -> asyncpg.Pool:
    """Initialize the database connection pool."""
    global _pool
    if _pool is None:
        settings = get_settings()
        # Extract connection parameters from URL
        # postgresql+asyncpg://user:password@host:port/database
        url = settings.database_url.replace("postgresql+asyncpg://", "")

        _pool = await asyncpg.create_pool(
            dsn=f"postgresql://{url}",
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
        logger.info("Database pool initialized")
    return _pool


async def close_db_pool():
    """Close the database connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database pool closed")


async def get_pool() -> asyncpg.Pool:
    """Get the database connection pool."""
    if _pool is None:
        return await init_db_pool()
    return _pool


@asynccontextmanager
async def get_connection():
    """Get a database connection from the pool."""
    pool = await get_pool()
    async with pool.acquire() as connection:
        yield connection
