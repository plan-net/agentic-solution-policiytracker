"""DiffAnalyzer - Compare Neo4j Drucksache data with Bundestag DIP API."""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


class DrucksacheDiff:
    """Represents the difference for a single Drucksache."""

    def __init__(
        self,
        drucksache_id: str,
        diff_type: str,  # "missing", "outdated", "relationship_missing"
        neo4j_data: Optional[Dict] = None,
        dip_data: Optional[Dict] = None,
        changed_fields: Optional[Set[str]] = None,
    ):
        self.drucksache_id = drucksache_id
        self.diff_type = diff_type
        self.neo4j_data = neo4j_data or {}
        self.dip_data = dip_data or {}
        self.changed_fields = changed_fields or set()

    def __repr__(self):
        return f"DrucksacheDiff(id={self.drucksache_id}, type={self.diff_type}, fields={self.changed_fields})"


class DrucksacheDiffAnalyzer:
    """Analyzes differences between Neo4j and Bundestag DIP API Drucksache data."""

    def __init__(self, neo4j_driver, neo4j_database, dip_client):
        """Initialize DrucksacheDiffAnalyzer.

        Args:
            neo4j_driver: Neo4j driver instance
            neo4j_database: Neo4j database name
            dip_client: Bundestag DIP API client for Drucksache
        """
        self.neo4j_driver = neo4j_driver
        self.neo4j_database = neo4j_database
        self.dip_client = dip_client

        # Fields to compare
        self.DRUCKSACHE_FIELDS = [
            "dokumentnummer",
            "dokumentart",
            "titel",
            "datum",
            "wahlperiode",
            "herausgeber",
            "pdf_url",
            "autoren",
            "abstract",
            "ressort",
            "aktualisiert",
        ]

        logger.info("DrucksacheDiffAnalyzer initialized")

    async def analyze_all_drucksachen(
        self, limit: Optional[int] = None
    ) -> List[DrucksacheDiff]:
        """Analyze all Drucksachen and find differences.

        Args:
            limit: Maximum number of Drucksachen to analyze (None = all)

        Returns:
            List of DrucksacheDiff objects
        """
        logger.info(f"Starting analysis of all Drucksachen (limit={limit})")

        # 1. Get all Drucksache IDs from DIP API
        dip_drucksache_ids = await self.dip_client.get_all_drucksache_ids(limit=limit)
        logger.info(f"Found {len(dip_drucksache_ids)} Drucksachen in DIP API")

        # 2. Get all Drucksache IDs from Neo4j
        neo4j_drucksache_ids = await self._get_neo4j_drucksache_ids()
        logger.info(f"Found {len(neo4j_drucksache_ids)} Drucksachen in Neo4j")

        # 3. Find missing Drucksachen (in DIP but not in Neo4j)
        missing_ids = set(dip_drucksache_ids) - set(neo4j_drucksache_ids)
        logger.info(f"Found {len(missing_ids)} missing Drucksachen")

        # 4. Find potentially outdated Drucksachen (in both)
        existing_ids = set(dip_drucksache_ids) & set(neo4j_drucksache_ids)
        logger.info(
            f"Found {len(existing_ids)} existing Drucksachen to check for updates"
        )

        # 5. Analyze differences
        all_diffs = []

        # Add missing Drucksachen
        for drucksache_id in missing_ids:
            dip_data = await self.dip_client.get_drucksache_by_id(drucksache_id)
            all_diffs.append(
                DrucksacheDiff(
                    drucksache_id=drucksache_id,
                    diff_type="missing",
                    dip_data=dip_data,
                )
            )

        # Check existing Drucksachen for updates
        for drucksache_id in existing_ids:
            diff = await self._compare_single_drucksache(drucksache_id)
            if diff:
                all_diffs.append(diff)

        logger.info(f"Analysis complete: {len(all_diffs)} differences found")
        return all_diffs

    async def analyze_specific_drucksachen(
        self, drucksache_ids: List[str]
    ) -> List[DrucksacheDiff]:
        """Analyze specific Drucksachen.

        Args:
            drucksache_ids: List of Drucksache IDs to analyze

        Returns:
            List of DrucksacheDiff objects
        """
        logger.info(f"Analyzing {len(drucksache_ids)} specific Drucksachen")

        all_diffs = []
        for drucksache_id in drucksache_ids:
            diff = await self._compare_single_drucksache(drucksache_id)
            if diff:
                all_diffs.append(diff)

        return all_diffs

    async def _compare_single_drucksache(self, drucksache_id: str) -> Optional[DrucksacheDiff]:
        """Compare a single Drucksache between Neo4j and DIP API.

        Args:
            drucksache_id: Drucksache ID to compare

        Returns:
            DrucksacheDiff if differences found, None otherwise
        """
        # Get data from both sources
        neo4j_data = await self._get_neo4j_drucksache(drucksache_id)
        dip_data = await self.dip_client.get_drucksache_by_id(drucksache_id)

        if not neo4j_data and dip_data:
            # Drucksache missing in Neo4j
            return DrucksacheDiff(
                drucksache_id=drucksache_id, diff_type="missing", dip_data=dip_data
            )

        if not dip_data:
            # Drucksache not in DIP API (shouldn't happen, but handle it)
            logger.warning(f"Drucksache {drucksache_id} not found in DIP API")
            return None

        # Compare fields
        changed_fields = set()
        for field in self.DRUCKSACHE_FIELDS:
            neo4j_value = neo4j_data.get(field)
            dip_value = dip_data.get(field)

            # Normalize values for comparison
            if neo4j_value != dip_value:
                # Skip if both are None/empty
                if not neo4j_value and not dip_value:
                    continue
                changed_fields.add(field)

        if changed_fields:
            return DrucksacheDiff(
                drucksache_id=drucksache_id,
                diff_type="outdated",
                neo4j_data=neo4j_data,
                dip_data=dip_data,
                changed_fields=changed_fields,
            )

        return None

    async def _get_neo4j_drucksache_ids(self) -> List[str]:
        """Get all Drucksache IDs from Neo4j.

        Returns:
            List of Drucksache IDs
        """
        query = """
        MATCH (d:Drucksache)
        WHERE d.active = true
        RETURN d.drucksache_id as drucksache_id
        ORDER BY d.drucksache_id
        """

        with self.neo4j_driver.session(database=self.neo4j_database) as session:
            result = session.run(query)
            return [record["drucksache_id"] for record in result]

    async def _get_neo4j_drucksache(self, drucksache_id: str) -> Optional[Dict[str, Any]]:
        """Get Drucksache data from Neo4j.

        Args:
            drucksache_id: Drucksache ID

        Returns:
            Drucksache data dict or None
        """
        query = """
        MATCH (d:Drucksache {drucksache_id: $drucksache_id})
        WHERE d.active = true
        RETURN d
        """

        with self.neo4j_driver.session(database=self.neo4j_database) as session:
            result = session.run(query, drucksache_id=drucksache_id)
            record = result.single()
            if record:
                return dict(record["d"])
            return None

    def generate_summary(self, diffs: List[DrucksacheDiff]) -> Dict[str, Any]:
        """Generate a summary of differences.

        Args:
            diffs: List of DrucksacheDiff objects

        Returns:
            Summary dictionary
        """
        summary = {
            "total_diffs": len(diffs),
            "missing_count": len([d for d in diffs if d.diff_type == "missing"]),
            "outdated_count": len([d for d in diffs if d.diff_type == "outdated"]),
            "most_changed_fields": self._count_changed_fields(diffs),
            "timestamp": datetime.now().isoformat(),
        }

        return summary

    def _count_changed_fields(self, diffs: List[DrucksacheDiff]) -> Dict[str, int]:
        """Count which fields changed most frequently.

        Args:
            diffs: List of DrucksacheDiff objects

        Returns:
            Field name -> count mapping
        """
        field_counts = {}
        for diff in diffs:
            if diff.diff_type == "outdated":
                for field in diff.changed_fields:
                    field_counts[field] = field_counts.get(field, 0) + 1

        # Sort by count descending
        return dict(sorted(field_counts.items(), key=lambda x: x[1], reverse=True))
