"""
Factory for creating policy collectors.

Supports multi-collector mode similar to news factory, allowing
policy collection from multiple sources (Exa, DPA) simultaneously.
"""

from __future__ import annotations

import os
from typing import Union

import structlog

from .dpa_news import DPANewsCollector
from .exa_direct import ExaDirectCollector

logger = structlog.get_logger()


def create_policy_collector(
    collector_type: str = None,
    api_key: str = None,
) -> Union[DPANewsCollector, ExaDirectCollector]:
    """
    Create a policy collector based on configuration.

    Args:
        collector_type: Type of collector ("exa_direct" or "dpa").
                       If None, uses POLICY_COLLECTOR environment variable.
        api_key: Optional API key to use (overrides environment variable)

    Returns:
        Configured policy collector instance

    Raises:
        ValueError: If collector type is unsupported or API keys are missing
    """
    # Determine collector type
    if collector_type is None:
        collector_type = os.getenv("POLICY_COLLECTOR", "exa_direct").lower()

    collector_type = collector_type.lower()

    # Create collector based on type
    if collector_type == "exa_direct":
        try:
            collector = ExaDirectCollector(api_key=api_key)
            logger.info("Created Exa.ai policy collector (direct HTTP)")
            return collector
        except ValueError as e:
            logger.error(f"Failed to create Exa direct collector: {e}")
            raise ValueError(f"Exa direct collector configuration error: {e}")

    elif collector_type == "dpa":
        try:
            collector = DPANewsCollector(api_key=api_key)
            logger.info("Created DPA policy collector")
            return collector
        except ValueError as e:
            logger.error(f"Failed to create DPA collector: {e}")
            raise ValueError(f"DPA collector configuration error: {e}")

    else:
        raise ValueError(
            f"Unsupported policy collector type: {collector_type}. "
            f"Supported types: 'exa_direct', 'dpa'"
        )


def get_available_policy_collectors() -> list[str]:
    """
    Get list of available policy collectors based on configured API keys.

    Returns:
        List of available collector names
    """
    available = []

    # Check Exa
    if os.getenv("EXA_API_KEY"):
        available.append("exa_direct")

    # Check DPA
    if os.getenv("DPA_API_KEY"):
        available.append("dpa")

    return available


def validate_policy_collector_config(collector_type: str = None) -> bool:
    """
    Validate that the specified policy collector can be created.

    Args:
        collector_type: Type of collector to validate

    Returns:
        True if collector can be created, False otherwise
    """
    try:
        create_policy_collector(collector_type)
        return True
    except ValueError:
        return False


def get_enabled_policy_collectors() -> list[str]:
    """
    Get list of policy collectors to run based on configuration.

    Supports multi-collector mode via POLICY_COLLECTORS env var (comma-separated).
    Falls back to single POLICY_COLLECTOR for backwards compatibility.
    Falls back to EXA_API_KEY detection for ultimate backwards compatibility.

    Returns:
        List of collector names to run in order
    """
    # Check for multi-collector config
    collectors_str = os.getenv("POLICY_COLLECTORS", "")
    if collectors_str:
        requested = [c.strip().lower() for c in collectors_str.split(",") if c.strip()]
    else:
        # Fall back to single collector
        single = os.getenv("POLICY_COLLECTOR", "")
        if single:
            requested = [single.lower()]
        elif os.getenv("EXA_API_KEY"):
            # Ultimate backwards compatibility: if EXA_API_KEY exists, use exa_direct
            requested = ["exa_direct"]
        else:
            requested = []

    # Filter to only available collectors (have API keys)
    available = get_available_policy_collectors()
    enabled = [c for c in requested if c in available]

    if not enabled:
        logger.warning(
            f"No policy collectors available from requested: {requested}. "
            f"Available: {available}"
        )
        # Fall back to first available
        if available:
            enabled = [available[0]]
            logger.info(f"Falling back to first available policy collector: {enabled[0]}")

    logger.info(f"Enabled policy collectors: {enabled}")
    return enabled
