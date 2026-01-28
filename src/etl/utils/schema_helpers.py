"""Helper utilities for extracting data from client.yaml schema.

This module provides utilities to extract configuration data from client.yaml files
that may be in either the new nested format or the legacy flat list format.

The helpers ensure backward compatibility while supporting the more expressive
nested schema format introduced for principle-based regulatory monitoring.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


def extract_industries(config: Dict[str, Any]) -> List[str]:
    """
    Extract industries from either nested or flat format.

    Supports two formats:
    1. Flat format (legacy):
       core_industries: ["industry1", "industry2", "industry3"]

    2. Nested format (current):
       core_industries:
         primary: "industry1"
         secondary: ["industry2", "industry3"]

    Args:
        config: The loaded client.yaml configuration dictionary

    Returns:
        List of industry strings in flat format

    Examples:
        >>> config = {"core_industries": {"primary": "E-commerce", "secondary": ["fashion"]}}
        >>> extract_industries(config)
        ['E-commerce', 'fashion']

        >>> config = {"core_industries": ["E-commerce", "fashion"]}
        >>> extract_industries(config)
        ['E-commerce', 'fashion']
    """
    industries_raw = config.get("core_industries", [])

    # Handle nested dictionary format
    if isinstance(industries_raw, dict):
        primary = industries_raw.get("primary", "")
        secondary = industries_raw.get("secondary", [])
        # Include primary only if it's not empty
        return ([primary] if primary else []) + secondary

    # Handle flat list format (backward compatibility)
    return industries_raw if isinstance(industries_raw, list) else []


def extract_markets(config: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """
    Extract primary and secondary markets from either nested or flat format.

    Supports two formats:
    1. Flat format (legacy):
       primary_markets: ["market1", "market2"]
       secondary_markets: ["market3", "market4"]

    2. Nested format (current):
       markets:
         primary: ["market1", "market2"]
         secondary: ["market3", "market4"]

    Args:
        config: The loaded client.yaml configuration dictionary

    Returns:
        Tuple of (primary_markets, secondary_markets) as lists of strings

    Examples:
        >>> config = {"markets": {"primary": ["germany"], "secondary": ["uk"]}}
        >>> extract_markets(config)
        (['germany'], ['uk'])

        >>> config = {"primary_markets": ["germany"], "secondary_markets": ["uk"]}
        >>> extract_markets(config)
        (['germany'], ['uk'])
    """
    # Try nested format first (preferred)
    markets_data = config.get("markets", {})
    if isinstance(markets_data, dict) and markets_data:
        primary = markets_data.get("primary", [])
        secondary = markets_data.get("secondary", [])
        return (primary, secondary)

    # Fall back to flat format (legacy)
    primary = config.get("primary_markets", [])
    secondary = config.get("secondary_markets", [])
    return (primary, secondary)


def extract_company_terms(config: Dict[str, Any]) -> List[str]:
    """
    Extract company terms from config, handling both company_terms list and client_name fallback.

    Supports:
    1. Preferred: company_terms: ["term1", "term2", ...]
    2. Fallback: client_name: "single_term"

    Args:
        config: The loaded client.yaml configuration dictionary

    Returns:
        List of company term strings

    Examples:
        >>> config = {"company_terms": ["Zalando", "Zalando SE"]}
        >>> extract_company_terms(config)
        ['Zalando', 'Zalando SE']

        >>> config = {"client_name": "zalando"}
        >>> extract_company_terms(config)
        ['zalando']
    """
    # Prefer company_terms list if available
    company_terms = config.get("company_terms", [])
    if company_terms and isinstance(company_terms, list):
        return company_terms

    # Fall back to single client_name
    client_name = config.get("client_name")
    if client_name and isinstance(client_name, str):
        return [client_name]

    return []


def extract_exclusion_terms(config: Dict[str, Any]) -> List[str]:
    """
    Extract exclusion terms from config, handling both flat and nested formats.

    Supports:
    1. Flat format: exclusion_terms: ["term1", "term2"]
    2. Nested format: exclusions: {industries: ["term1", "term2"]}

    Args:
        config: The loaded client.yaml configuration dictionary

    Returns:
        List of exclusion term strings

    Examples:
        >>> config = {"exclusion_terms": ["sports", "automotive"]}
        >>> extract_exclusion_terms(config)
        ['sports', 'automotive']

        >>> config = {"exclusions": {"industries": ["sports", "automotive"]}}
        >>> extract_exclusion_terms(config)
        ['sports', 'automotive']
    """
    # Try flat format first (most common in ETL)
    exclusion_terms = config.get("exclusion_terms", [])
    if exclusion_terms and isinstance(exclusion_terms, list):
        return exclusion_terms

    # Fall back to nested format (used by some agents)
    exclusions = config.get("exclusions", {})
    if isinstance(exclusions, dict):
        industries = exclusions.get("industries", [])
        if industries and isinstance(industries, list):
            return industries

    return []


def validate_required_fields(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate that all ETL-required fields are present in the config.

    Required fields:
    - company_terms or client_name
    - core_industries
    - primary_markets (or markets.primary)
    - secondary_markets (or markets.secondary)
    - strategic_themes
    - direct_impact_keywords
    - topic_patterns
    - exclusion_terms (or exclusions.industries)

    Args:
        config: The loaded client.yaml configuration dictionary

    Returns:
        Tuple of (is_valid, list_of_missing_fields)

    Examples:
        >>> config = {
        ...     "company_terms": ["Zalando"],
        ...     "core_industries": {"primary": "E-commerce", "secondary": []},
        ...     "primary_markets": ["germany"],
        ...     "secondary_markets": ["uk"],
        ...     "strategic_themes": ["digital transformation"],
        ...     "direct_impact_keywords": ["must comply"],
        ...     "topic_patterns": {"data-protection": ["gdpr"]},
        ...     "exclusion_terms": ["sports"]
        ... }
        >>> validate_required_fields(config)
        (True, [])
    """
    missing_fields = []

    # Check company terms
    if not extract_company_terms(config):
        missing_fields.append("company_terms or client_name")

    # Check core industries
    if not extract_industries(config):
        missing_fields.append("core_industries")

    # Check markets
    primary_markets, secondary_markets = extract_markets(config)
    if not primary_markets:
        missing_fields.append("primary_markets or markets.primary")
    if not secondary_markets:
        missing_fields.append("secondary_markets or markets.secondary")

    # Check other required fields
    if not config.get("strategic_themes"):
        missing_fields.append("strategic_themes")

    if not config.get("direct_impact_keywords"):
        missing_fields.append("direct_impact_keywords")

    if not config.get("topic_patterns"):
        missing_fields.append("topic_patterns")

    if not extract_exclusion_terms(config):
        missing_fields.append("exclusion_terms or exclusions.industries")

    is_valid = len(missing_fields) == 0
    return (is_valid, missing_fields)
