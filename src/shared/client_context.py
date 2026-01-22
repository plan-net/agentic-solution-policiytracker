"""Client context loader for agent operations.

Loads client business context from YAML configuration to help agents
understand the client's industry, regulatory focus areas, and markets.
This enables agents to prioritize relevance and frame responses appropriately.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Cache for loaded context (module-level singleton)
_client_context_cache: dict[str, Any] | None = None


def load_client_context(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load client context from YAML configuration file.

    Args:
        config_path: Optional path to client config file.
                    Defaults to data/context/client.yaml

    Returns:
        Dictionary containing full client context configuration.

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is malformed
    """
    global _client_context_cache

    if _client_context_cache is not None:
        return _client_context_cache

    if config_path is None:
        # Default path relative to this file: src/shared -> src -> project root -> data/context
        config_path = Path(__file__).parent.parent.parent / "data" / "context" / "client.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        logger.warning(f"Client context file not found: {config_path}")
        return {}

    with open(config_path) as f:
        _client_context_cache = yaml.safe_load(f)

    logger.info(f"Loaded client context for: {_client_context_cache.get('client_name', 'unknown')}")
    return _client_context_cache


def get_client_context_for_prompt() -> dict[str, str]:
    """Get client context formatted for prompt template variable substitution.

    Returns a dictionary with string values suitable for {{variable}} replacement
    in prompt templates.

    Returns:
        Dictionary with keys:
        - client_name: Client company name
        - client_industry: Primary industry
        - client_description: Business model description
        - regulatory_focus: Formatted list of high-relevance regulatory areas
        - primary_markets: Comma-separated list of primary markets
        - key_activities: Formatted list of key business activities
        - exclusions: Industries/areas to exclude from analysis
    """
    ctx = load_client_context()

    if not ctx:
        return {
            "client_name": "Unknown Client",
            "client_industry": "Unknown Industry",
            "client_description": "",
            "regulatory_focus": "",
            "primary_markets": "",
            "key_activities": "",
            "exclusions": "",
        }

    # Format high-relevance regulatory areas
    high_relevance = ctx.get("regulatory_relevance", {}).get("high_relevance", [])
    regulatory_focus = "\n".join([
        f"- **{area['area']}**: {area['why']}"
        for area in high_relevance
    ])

    # Format medium-relevance areas (shorter format)
    medium_relevance = ctx.get("regulatory_relevance", {}).get("medium_relevance", [])
    medium_areas = "\n".join([
        f"- {area['area']}"
        for area in medium_relevance
    ])
    if medium_areas:
        regulatory_focus += f"\n\nAlso monitor:\n{medium_areas}"

    # Format markets
    markets = ctx.get("markets", {})
    primary_markets = ", ".join(markets.get("primary", []))

    # Format key activities
    business_model = ctx.get("business_model", {})
    key_activities = "\n".join([
        f"- {activity}"
        for activity in business_model.get("key_activities", [])
    ])

    # Format exclusions
    exclusions_config = ctx.get("exclusions", {})
    excluded_industries = exclusions_config.get("industries", [])
    exclusions = ", ".join(excluded_industries) if excluded_industries else ""

    return {
        "client_name": ctx.get("client_name", "Unknown"),
        "client_industry": ctx.get("industry", {}).get("primary", "Unknown Industry"),
        "client_description": business_model.get("description", ""),
        "regulatory_focus": regulatory_focus,
        "primary_markets": primary_markets,
        "key_activities": key_activities,
        "exclusions": exclusions,
    }


def get_client_name() -> str:
    """Get the client name from context.

    Returns:
        Client name string or "Unknown" if not configured.
    """
    ctx = load_client_context()
    return ctx.get("client_name", "Unknown")


def get_primary_markets() -> list[str]:
    """Get list of primary markets for the client.

    Returns:
        List of primary market names (e.g., ["germany", "european union"])
    """
    ctx = load_client_context()
    return ctx.get("markets", {}).get("primary", [])


def is_relevant_industry(industry: str) -> bool:
    """Check if an industry is relevant (not excluded) for the client.

    Args:
        industry: Industry name to check

    Returns:
        True if the industry is relevant, False if excluded
    """
    ctx = load_client_context()
    exclusions = ctx.get("exclusions", {}).get("industries", [])
    return industry.lower() not in [ex.lower() for ex in exclusions]


def clear_cache() -> None:
    """Clear the cached client context.

    Useful for testing or when the config file changes.
    """
    global _client_context_cache
    _client_context_cache = None
    logger.debug("Client context cache cleared")
