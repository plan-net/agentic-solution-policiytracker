"""
Logging configuration for data ingestion flow.

Configures structlog to output to stdout so Ray can capture logs.
"""

import logging
import sys

import structlog


def configure_logging(log_level: str = "INFO"):
    """Configure structlog for Ray environment."""

    # Configure standard logging to output to stderr (Ray captures this better)
    # Force reconfiguration even if already configured
    logging.root.handlers = []
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,  # Changed to stderr for better Ray capture
        level=getattr(logging, log_level.upper()),
        force=True,  # Force reconfiguration
    )

    # Configure structlog with console output
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
            # Use ConsoleRenderer for human-readable logs
            structlog.dev.ConsoleRenderer(colors=False),  # No colors in Ray logs
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


# Auto-configure when imported
configure_logging()
