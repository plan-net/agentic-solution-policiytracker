import logging
import sys
from typing import Any, Dict

import structlog

from src.config import settings


def setup_logging() -> structlog.stdlib.BoundLogger:
    """Setup structured logging configuration."""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )
    
    # Configure structlog processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    
    if settings.LOG_FORMAT.lower() == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=True),
        ])
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger()


def log_performance(operation: str, duration_ms: float, **kwargs: Any) -> None:
    """Log performance metrics if enabled."""
    if settings.ENABLE_PERFORMANCE_LOGGING:
        logger = structlog.get_logger()
        logger.info(
            "Performance metric",
            operation=operation,
            duration_ms=duration_ms,
            **kwargs
        )