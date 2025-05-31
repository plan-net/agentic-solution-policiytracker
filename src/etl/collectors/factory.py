"""
Factory for creating news collectors.
"""

import os
from typing import Union

import structlog

from .apify_news import ApifyNewsCollector
from .exa_direct import ExaDirectCollector
from .exa_news import ExaNewsCollector

logger = structlog.get_logger()


def create_news_collector(
    collector_type: str = None,
) -> Union[ApifyNewsCollector, ExaNewsCollector, ExaDirectCollector]:
    """
    Create a news collector based on configuration.

    Args:
        collector_type: Type of collector ("apify", "exa", or "exa_direct").
                       If None, uses NEWS_COLLECTOR environment variable.

    Returns:
        Configured news collector instance

    Raises:
        ValueError: If collector type is unsupported or API keys are missing
    """
    # Determine collector type
    if collector_type is None:
        collector_type = os.getenv("NEWS_COLLECTOR", "exa_direct").lower()

    collector_type = collector_type.lower()

    # Create collector based on type
    if collector_type == "apify":
        try:
            collector = ApifyNewsCollector()
            logger.info("Created Apify news collector")
            return collector
        except ValueError as e:
            logger.error(f"Failed to create Apify collector: {e}")
            raise ValueError(f"Apify collector configuration error: {e}")

    elif collector_type == "exa":
        try:
            collector = ExaNewsCollector()
            logger.info("Created Exa.ai news collector (Python client)")
            return collector
        except ValueError as e:
            logger.error(f"Failed to create Exa collector: {e}")
            raise ValueError(f"Exa collector configuration error: {e}")

    elif collector_type == "exa_direct":
        try:
            collector = ExaDirectCollector()
            logger.info("Created Exa.ai news collector (direct HTTP)")
            return collector
        except ValueError as e:
            logger.error(f"Failed to create Exa direct collector: {e}")
            raise ValueError(f"Exa direct collector configuration error: {e}")

    else:
        raise ValueError(
            f"Unsupported collector type: {collector_type}. Supported types: 'apify', 'exa', 'exa_direct'"
        )


def get_available_collectors() -> list:
    """
    Get list of available collectors based on configured API keys.

    Returns:
        List of available collector names
    """
    available = []

    # Check Apify
    if os.getenv("APIFY_API_TOKEN"):
        available.append("apify")

    # Check Exa (both variants)
    if os.getenv("EXA_API_KEY"):
        available.append("exa")
        available.append("exa_direct")

    return available


def validate_collector_config(collector_type: str = None) -> bool:
    """
    Validate that the specified collector can be created.

    Args:
        collector_type: Type of collector to validate

    Returns:
        True if collector can be created, False otherwise
    """
    try:
        create_news_collector(collector_type)
        return True
    except ValueError:
        return False
