"""Client context loader for agent operations.

Loads client business context from YAML configuration to help agents
understand the client's industry, regulatory focus areas, and markets.
This enables agents to prioritize relevance and frame responses appropriately.
"""

from __future__ import annotations

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

    # Extract core_industries using the same logic as schema_helpers
    # This handles both nested {primary, secondary} and flat list formats
    core_industries_raw = ctx.get("core_industries", [])
    if isinstance(core_industries_raw, dict):
        # Nested format: get primary industry
        client_industry = core_industries_raw.get("primary", "Unknown Industry")
    elif isinstance(core_industries_raw, list) and core_industries_raw:
        # Flat list format: get first industry
        client_industry = core_industries_raw[0]
    else:
        client_industry = "Unknown Industry"

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

    # Format markets - support both nested and flat formats
    markets_nested = ctx.get("markets", {})
    if isinstance(markets_nested, dict) and markets_nested.get("primary"):
        primary_markets = ", ".join(markets_nested.get("primary", []))
    else:
        # Fallback to flat format
        primary_markets = ", ".join(ctx.get("primary_markets", []))

    # Format key activities
    business_model = ctx.get("business_model", {})
    key_activities = "\n".join([
        f"- {activity}"
        for activity in business_model.get("key_activities", [])
    ])

    # Format exclusions - support both nested and flat formats
    exclusions_config = ctx.get("exclusions", {})
    excluded_industries = exclusions_config.get("industries", [])
    if not excluded_industries:
        # Fallback to flat format
        excluded_industries = ctx.get("exclusion_terms", [])
    exclusions = ", ".join(excluded_industries) if excluded_industries else ""

    return {
        "client_name": ctx.get("client_name", "Unknown"),
        "client_industry": client_industry,
        "client_description": business_model.get("description", ""),
        "regulatory_focus": regulatory_focus,
        "primary_markets": primary_markets,
        "key_activities": key_activities,
        "exclusions": exclusions,
        "regulatory_context": get_regulatory_context_for_agents(),
    }


def get_regulatory_context_for_agents() -> str:
    """Get formatted regulatory context for agent prompts.

    Extracts regulatory actors and legislative vocabulary from client.yaml
    to enhance agent awareness of authoritative sources and legislative stages.

    Returns:
        Formatted markdown string with regulatory actors and legislative vocabulary,
        or empty string if not configured.
    """
    ctx = load_client_context()

    if not ctx:
        return ""

    # Extract regulatory actors
    actors_config = ctx.get("regulatory_actors", {})
    german_actors = actors_config.get("german_federal", [])[:5]  # Top 5
    eu_actors = actors_config.get("eu_institutions", [])[:5]  # Top 5

    # Extract legislative terms
    terms_config = ctx.get("legislative_terms", {})
    german_terms = terms_config.get("german", [])[:5]  # Top 5
    english_terms = terms_config.get("english", [])[:5]  # Top 5

    # Build regulatory context if we have data
    if not (german_actors or eu_actors or german_terms or english_terms):
        return ""

    context_parts = []

    if german_actors or eu_actors:
        context_parts.append("**Key Regulatory Actors to Monitor:**")
        if german_actors:
            context_parts.append(f"- German Federal: {', '.join(german_actors)}")
        if eu_actors:
            context_parts.append(f"- EU Institutions: {', '.join(eu_actors)}")

    if german_terms or english_terms:
        if context_parts:
            context_parts.append("")  # Blank line
        context_parts.append("**Legislative Vocabulary:**")
        if german_terms:
            context_parts.append(f"- German: {', '.join(german_terms)}")
        if english_terms:
            context_parts.append(f"- English: {', '.join(english_terms)}")

    if context_parts:
        context_parts.append("")  # Blank line
        context_parts.append(
            "When analyzing regulatory content, prioritize documents mentioning "
            "these actors or using this legislative terminology."
        )

    return "\n".join(context_parts)


def get_client_name() -> str:
    """Get the client name from context.

    Returns:
        Client name string or "Unknown" if not configured.
    """
    ctx = load_client_context()
    return ctx.get("client_name", "Unknown")


def get_primary_markets() -> list[str]:
    """Get list of primary markets for the client.

    Supports both nested and flat formats:
    - Nested: markets.primary
    - Flat: primary_markets

    Returns:
        List of primary market names (e.g., ["germany", "european union"])
    """
    ctx = load_client_context()

    # Try nested format first
    markets_nested = ctx.get("markets", {})
    if isinstance(markets_nested, dict) and markets_nested.get("primary"):
        return markets_nested.get("primary", [])

    # Fall back to flat format
    return ctx.get("primary_markets", [])


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
