"""
Policy Query Generator for ETL Pipeline

Generates targeted search queries for policy landscape collection
by parsing client context YAML and creating strategic combinations.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

logger = logging.getLogger(__name__)


class PolicyQueryGenerator:
    """Generates policy-focused search queries from client context."""

    def __init__(self, client_context_path: str = "data/context/client.yaml"):
        """Initialize with path to client context YAML."""
        self.context_path = Path(client_context_path)
        self.context_data: Dict[str, Any] = {}
        self._load_context()

    def _load_context(self) -> None:
        """Load and parse client context YAML file."""
        try:
            with open(self.context_path, encoding="utf-8") as f:
                self.context_data = yaml.safe_load(f)
            logger.info(f"Loaded client context from {self.context_path}")
        except Exception as e:
            logger.error(f"Failed to load client context: {e}")
            raise

    def generate_policy_queries(self) -> List[Dict[str, str]]:
        """
        Generate comprehensive policy search queries.

        Returns:
            List of query dictionaries with 'query', 'category', and 'description'
        """
        queries = []

        # Core markets and industries for context
        markets = self.context_data.get("primary_markets", [])
        industries = self.context_data.get("core_industries", [])

        # Generate queries for each topic pattern (limited)
        topic_patterns = self.context_data.get("topic_patterns", {})

        for category, terms in topic_patterns.items():
            category_queries = self._generate_category_queries(category, terms, markets, industries)
            # Limit queries per category to avoid API overload
            queries.extend(category_queries[:5])  # Max 5 per category

        # Add strategic theme queries (limited)
        strategic_queries = self._generate_strategic_queries(markets, industries)
        queries.extend(strategic_queries[:4])  # Max 4 strategic queries

        # Add enforcement and compliance queries (limited)
        enforcement_queries = self._generate_enforcement_queries(markets)
        queries.extend(enforcement_queries[:4])  # Max 4 enforcement queries

        logger.info(f"Generated {len(queries)} policy search queries")
        return queries

    def _generate_category_queries(
        self, category: str, terms: List[str], markets: List[str], industries: List[str]
    ) -> List[Dict[str, str]]:
        """Generate queries for a specific topic category."""
        queries = []

        # Primary markets (EU focus)
        eu_markets = ["european union", "eu", "europe"]
        primary_markets = [m for m in markets if m.lower() in eu_markets]
        if not primary_markets:
            primary_markets = markets[:3]  # Fallback to first 3 markets

        # Core industries
        core_industries = industries[:3]  # Focus on top 3 industries

        # Generate focused queries (reduced combinations)
        # Only use top 2 markets and 2 industries to limit explosion
        for market in primary_markets[:2]:  # Top 2 markets only
            for industry in core_industries[:2]:  # Top 2 industries only
                # Take only top 2 terms from each category
                for term in terms[:2]:  # Top 2 terms only
                    query_parts = [term, market, industry]
                    query = " AND ".join(f'"{part}"' for part in query_parts)

                    queries.append(
                        {
                            "query": query,
                            "category": category,
                            "description": f'{category.replace("-", " ").title()} in {industry} sector for {market}',
                        }
                    )

        # Add regulation-specific queries (only for key categories)
        if category in ["data-protection", "ecommerce-regulation"]:
            # Only add 1 upcoming query per key category
            term = terms[0] if terms else category.replace("-", " ")
            reg_query = f'"{term}" AND "new regulation" AND "2024" AND "2025"'
            queries.append(
                {
                    "query": reg_query,
                    "category": f"{category}-upcoming",
                    "description": f"Upcoming {term} regulations and changes",
                }
            )

        return queries

    def _generate_strategic_queries(
        self, markets: List[str], industries: List[str]
    ) -> List[Dict[str, str]]:
        """Generate queries for strategic themes."""
        queries = []
        strategic_themes = self.context_data.get("strategic_themes", [])

        # Focus on AI, sustainability, and data privacy as high-impact themes
        priority_themes = [
            "artificial intelligence",
            "sustainability",
            "data privacy",
            "digital transformation",
        ]

        relevant_themes = [t for t in strategic_themes if t in priority_themes]

        for theme in relevant_themes[:3]:  # Top 3 themes
            for market in markets[:2]:  # Top 2 markets
                query = f'"{theme}" AND "{market}" AND "regulation" AND "policy"'
                queries.append(
                    {
                        "query": query,
                        "category": "strategic-themes",
                        "description": f"{theme.title()} policy developments in {market}",
                    }
                )

        return queries

    def _generate_enforcement_queries(self, markets: List[str]) -> List[Dict[str, str]]:
        """Generate queries focused on enforcement and compliance actions."""
        queries = []
        impact_keywords = self.context_data.get("direct_impact_keywords", [])

        # Focus on enforcement actions
        enforcement_terms = ["enforcement action", "penalty", "investigation", "compliance audit"]

        for term in enforcement_terms:
            for market in markets[:3]:  # Top 3 markets
                query = f'"{term}" AND "{market}" AND "e-commerce" AND "platform"'
                queries.append(
                    {
                        "query": query,
                        "category": "enforcement",
                        "description": f"Enforcement actions and penalties in {market}",
                    }
                )

        return queries

    def _generate_temporal_queries(self) -> List[Dict[str, str]]:
        """Generate time-sensitive policy queries."""
        queries = []

        # Recent and upcoming regulations
        temporal_terms = [
            '"new regulation" AND "2024" AND "2025"',
            '"upcoming changes" AND "policy" AND "2025"',
            '"draft legislation" AND "consultation"',
            '"enforcement deadline" AND "compliance"',
        ]

        markets = self.context_data.get("primary_markets", [])

        for term in temporal_terms:
            for market in markets[:2]:  # Top 2 markets
                query = f'{term} AND "{market}"'
                queries.append(
                    {
                        "query": query,
                        "category": "temporal",
                        "description": f"Time-sensitive policy developments in {market}",
                    }
                )

        return queries

    def get_query_summary(self) -> Dict[str, int]:
        """Get summary of query categories and counts."""
        queries = self.generate_policy_queries()

        summary = {}
        for query in queries:
            category = query["category"]
            summary[category] = summary.get(category, 0) + 1

        return summary

    def validate_queries(self) -> Tuple[bool, List[str]]:
        """Validate generated queries for quality and completeness."""
        errors = []

        try:
            queries = self.generate_policy_queries()

            if len(queries) < 10:
                errors.append(f"Too few queries generated: {len(queries)}")

            if len(queries) > 40:
                errors.append(f"Too many queries generated: {len(queries)} (may hit API limits)")

            # Check for required categories
            categories = {q["category"] for q in queries}
            required_categories = ["data-protection", "ecommerce-regulation", "compliance"]

            for req_cat in required_categories:
                if req_cat not in categories:
                    errors.append(f"Missing required category: {req_cat}")

            # Check query format
            for i, query in enumerate(queries):
                if not query.get("query"):
                    errors.append(f"Empty query at index {i}")
                if len(query.get("query", "")) < 10:
                    errors.append(f"Query too short at index {i}: {query.get('query')}")

        except Exception as e:
            errors.append(f"Validation failed with error: {e}")

        return len(errors) == 0, errors


def main():
    """Test the policy query generator."""
    generator = PolicyQueryGenerator()

    print("=== Policy Query Generator Test ===")

    # Generate queries
    queries = generator.generate_policy_queries()

    print(f"\nGenerated {len(queries)} queries:")
    print("-" * 50)

    # Group by category
    by_category = {}
    for query in queries:
        category = query["category"]
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(query)

    # Display by category
    for category, cat_queries in by_category.items():
        print(f"\n{category.upper()} ({len(cat_queries)} queries):")
        for query in cat_queries[:3]:  # Show first 3 per category
            print(f"  • {query['query']}")
            print(f"    └─ {query['description']}")

    # Summary
    print(f"\nSummary: {generator.get_query_summary()}")

    # Validation
    is_valid, errors = generator.validate_queries()
    print(f"\nValidation: {'✅ PASSED' if is_valid else '❌ FAILED'}")
    if errors:
        for error in errors:
            print(f"  • {error}")


if __name__ == "__main__":
    main()
