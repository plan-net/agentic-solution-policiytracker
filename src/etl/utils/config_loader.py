"""
Configuration loader for ETL pipeline.
"""

from pathlib import Path
from typing import Dict, Any, List
import yaml
import structlog

logger = structlog.get_logger()


class ClientConfigLoader:
    """Loads and manages client configuration for ETL pipeline."""

    def __init__(self, config_path: str = "data/context/client.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        logger.info(f"Loaded client config from: {self.config_path}")

    def _load_config(self) -> Dict[str, Any]:
        """Load client configuration from YAML file."""
        try:
            if not self.config_path.exists():
                logger.warning(f"Client config not found at {self.config_path}, using defaults")
                return self._get_default_config()

            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)

            return config

        except Exception as e:
            logger.error(f"Failed to load client config: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
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

    def get_company_names(self) -> List[str]:
        """Get list of company names/terms to search for."""
        return self.config.get("company_terms", [])

    def get_primary_company_name(self) -> str:
        """Get the primary company name for searches."""
        company_terms = self.get_company_names()
        return company_terms[0] if company_terms else "unknown_company"

    def get_search_queries(self) -> List[str]:
        """Generate search queries based on client configuration."""
        queries = []

        # Primary company name queries
        company_names = self.get_company_names()
        queries.extend(company_names)

        # Could extend with combinations if needed
        # For now, keeping it simple as requested

        return queries

    def get_exclusion_terms(self) -> List[str]:
        """Get terms to exclude from search results."""
        return self.config.get("exclusion_terms", [])

    def should_exclude_article(self, article: Dict[str, Any]) -> bool:
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
