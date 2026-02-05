"""
Configuration loader for ETL pipeline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import structlog
import yaml

from .schema_helpers import (
    extract_company_terms,
    extract_exclusion_terms,
    extract_industries,
    extract_legislative_terms,
    extract_markets,
    extract_regulatory_actors,
)

logger = structlog.get_logger()


class ClientConfigLoader:
    """Loads and manages client configuration for ETL pipeline."""

    def __init__(self, config_path: str = "data/context/client.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        logger.info(f"Loaded client config from: {self.config_path}")

    def _load_config(self) -> dict[str, Any]:
        """Load client configuration from YAML file."""
        try:
            if not self.config_path.exists():
                logger.warning(f"Client config not found at {self.config_path}, using defaults")
                return self._get_default_config()

            with open(self.config_path) as f:
                config = yaml.safe_load(f)

            return config

        except Exception as e:
            logger.error(f"Failed to load client config: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> dict[str, Any]:
        """Return default configuration if file not found."""
        return {
            "company_terms": ["example_company"],
            "core_industries": ["technology"],
            "primary_markets": ["united states", "european union"],
            "secondary_markets": [],
            "strategic_themes": ["regulation", "compliance"],
            "topic_patterns": {},
            "direct_impact_keywords": ["must comply", "required to"],
            "exclusion_terms": [],
        }

    def get_company_names(self) -> list[str]:
        """Get list of company names/terms to search for.

        Uses schema_helpers to support both company_terms list and client_name fallback.
        """
        return extract_company_terms(self.config)

    def get_primary_company_name(self) -> str:
        """Get the primary company name for searches."""
        company_terms = self.get_company_names()
        return company_terms[0] if company_terms else "unknown_company"

    def get_search_queries(self) -> list[str]:
        """Generate search queries based on client configuration."""
        queries = []

        # Primary company name queries
        company_names = self.get_company_names()
        queries.extend(company_names)

        # Could extend with combinations if needed
        # For now, keeping it simple as requested

        return queries

    def get_exclusion_terms(self) -> list[str]:
        """Get terms to exclude from search results.

        Uses schema_helpers to support both flat and nested formats.
        """
        return extract_exclusion_terms(self.config)

    def get_core_industries(self) -> list[str]:
        """Get core industries, supporting both nested and flat formats.

        Returns:
            List of industry strings extracted from config
        """
        return extract_industries(self.config)

    def get_markets(self) -> tuple[list[str], list[str]]:
        """Get primary and secondary markets.

        Returns:
            Tuple of (primary_markets, secondary_markets)
        """
        return extract_markets(self.config)

    def get_regulatory_actors(self, region: Optional[str] = None) -> list[str]:
        """Get regulatory actors, optionally filtered by region.

        Args:
            region: Optional filter ("german_federal", "eu_institutions")

        Returns:
            List of regulatory actor names
        """
        return extract_regulatory_actors(self.config, region)

    def get_legislative_terms(self, language: Optional[str] = None) -> list[str]:
        """Get legislative terms, optionally filtered by language.

        Args:
            language: Optional filter ("german", "english")

        Returns:
            List of legislative term strings
        """
        return extract_legislative_terms(self.config, language)

    def should_exclude_article(self, article: dict[str, Any]) -> bool:
        """Check if an article should be excluded based on exclusion terms."""
        exclusion_terms = self.get_exclusion_terms()
        if not exclusion_terms:
            return False

        # Check title and content for exclusion terms
        text_to_check = f"{article.get('title', '')} {article.get('content', '')}".lower()

        for term in exclusion_terms:
            if term.lower() in text_to_check:
                logger.debug(f"Excluding article due to term '{term}': {article.get('title')}")
                return True

        return False
