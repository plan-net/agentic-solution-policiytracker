"""
Configuration settings for the Cost Analytics API
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql+asyncpg://timescale:timescale_secure_password@timescaledb:5432/llm_costs"

    # Application
    app_name: str = "Cost Analytics API"
    app_version: str = "0.2.0"
    debug: bool = False
    log_level: str = "INFO"

    # API
    api_prefix: str = "/api"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
