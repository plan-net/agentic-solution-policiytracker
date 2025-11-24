"""DiffAnalyzer - Compare Neo4j Plenarprotokoll data with Bundestag DIP API."""
import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class PlenarprotokollDiff:
    """Represents the difference for a single Plenarprotokoll."""

    def __init__(
        self,
        plenarprotokoll_id: str,
        diff_type: str,  # "missing", "outdated", "relationship_missing"
        neo4j_data: Optional[dict] = None,
        dip_data: Optional[dict] = None,
        changed_fields: Optional[set[str]] = None,
    ):
        self.plenarprotokoll_id = plenarprotokoll_id
        self.diff_type = diff_type
        self.neo4j_data = neo4j_data or {}
        self.dip_data = dip_data or {}
        self.changed_fields = changed_fields or set()

    def __repr__(self):
        return f"PlenarprotokollDiff(id={self.plenarprotokoll_id}, type={self.diff_type}, fields={self.changed_fields})"


class PlenarprotokollDiffAnalyzer:
    """Analyzes differences between Neo4j and Bundestag DIP API Plenarprotokoll data."""

    def __init__(self, neo4j_driver, neo4j_database, dip_client):
        """Initialize PlenarprotokollDiffAnalyzer.

        Args:
            neo4j_driver: Neo4j driver instance
            neo4j_database: Neo4j database name
            dip_client: Bundestag DIP API client for Plenarprotokoll
        """
        self.neo4j_driver = neo4j_driver
        self.neo4j_database = neo4j_database
        self.dip_client = dip_client

        # Fields to compare
        self.PLENARPROTOKOLL_FIELDS = [
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

        logger.info("PlenarprotokollDiffAnalyzer initialized")

    async def analyze_all_plenarprotokolle(
        self, limit: Optional[int] = None
    ) -> list[PlenarprotokollDiff]:
        """Analyze all Plenarprotokolln and find differences.

        Args:
            limit: Maximum number of Plenarprotokolln to analyze (None = all)

        Returns:
            List of PlenarprotokollDiff objects
        """
        logger.info(f"Starting analysis of all Plenarprotokolln (limit={limit})")

        # 1. Get all Plenarprotokoll IDs from DIP API
        dip_plenarprotokoll_ids = await self.dip_client.get_all_plenarprotokoll_ids(limit=limit)
        logger.info(f"Found {len(dip_plenarprotokoll_ids)} Plenarprotokolln in DIP API")

        # 2. Get all Plenarprotokoll IDs from Neo4j
        neo4j_plenarprotokoll_ids = await self._get_neo4j_plenarprotokoll_ids()
        logger.info(f"Found {len(neo4j_plenarprotokoll_ids)} Plenarprotokolln in Neo4j")

        # 3. Find missing Plenarprotokolln (in DIP but not in Neo4j)
        missing_ids = set(dip_plenarprotokoll_ids) - set(neo4j_plenarprotokoll_ids)
        logger.info(f"Found {len(missing_ids)} missing Plenarprotokolln")

        # 4. Find potentially outdated Plenarprotokolln (in both)
        existing_ids = set(dip_plenarprotokoll_ids) & set(neo4j_plenarprotokoll_ids)
        logger.info(f"Found {len(existing_ids)} existing Plenarprotokolln to check for updates")

        # 5. Analyze differences
        all_diffs = []

        # Add missing Plenarprotokolln
        for plenarprotokoll_id in missing_ids:
            dip_data = await self.dip_client.get_plenarprotokoll_by_id(plenarprotokoll_id)
            all_diffs.append(
                PlenarprotokollDiff(
                    plenarprotokoll_id=plenarprotokoll_id,
                    diff_type="missing",
                    dip_data=dip_data,
                )
            )

        # Check existing Plenarprotokolln for updates
        for plenarprotokoll_id in existing_ids:
            diff = await self._compare_single_plenarprotokoll(plenarprotokoll_id)
            if diff:
                all_diffs.append(diff)

        logger.info(f"Analysis complete: {len(all_diffs)} differences found")
        return all_diffs

    async def analyze_specific_plenarprotokolle(
        self, plenarprotokoll_ids: list[str]
    ) -> list[PlenarprotokollDiff]:
        """Analyze specific Plenarprotokolln.

        Args:
            plenarprotokoll_ids: List of Plenarprotokoll IDs to analyze

        Returns:
            List of PlenarprotokollDiff objects
        """
        logger.info(f"Analyzing {len(plenarprotokoll_ids)} specific Plenarprotokolln")

        all_diffs = []
        for plenarprotokoll_id in plenarprotokoll_ids:
            diff = await self._compare_single_plenarprotokoll(plenarprotokoll_id)
            if diff:
                all_diffs.append(diff)

        return all_diffs

    async def _compare_single_plenarprotokoll(
        self, plenarprotokoll_id: str
    ) -> Optional[PlenarprotokollDiff]:
        """Compare a single Plenarprotokoll between Neo4j and DIP API.

        Args:
            plenarprotokoll_id: Plenarprotokoll ID to compare

        Returns:
            PlenarprotokollDiff if differences found, None otherwise
        """
        # Get data from both sources
        neo4j_data = await self._get_neo4j_plenarprotokoll(plenarprotokoll_id)
        dip_data = await self.dip_client.get_plenarprotokoll_by_id(plenarprotokoll_id)

        if not neo4j_data and dip_data:
            # Plenarprotokoll missing in Neo4j
            return PlenarprotokollDiff(
                plenarprotokoll_id=plenarprotokoll_id, diff_type="missing", dip_data=dip_data
            )

        if not dip_data:
            # Plenarprotokoll not in DIP API (shouldn't happen, but handle it)
            logger.warning(f"Plenarprotokoll {plenarprotokoll_id} not found in DIP API")
            return None

        # Compare fields
        changed_fields = set()
        for field in self.PLENARPROTOKOLL_FIELDS:
            neo4j_value = neo4j_data.get(field)
            dip_value = dip_data.get(field)

            # Normalize values for comparison
            if neo4j_value != dip_value:
                # Skip if both are None/empty
                if not neo4j_value and not dip_value:
                    continue
                changed_fields.add(field)

        if changed_fields:
            return PlenarprotokollDiff(
                plenarprotokoll_id=plenarprotokoll_id,
                diff_type="outdated",
                neo4j_data=neo4j_data,
                dip_data=dip_data,
                changed_fields=changed_fields,
            )

        return None

    async def _get_neo4j_plenarprotokoll_ids(self) -> list[str]:
        """Get all Plenarprotokoll IDs from Neo4j.

        Returns:
            List of Plenarprotokoll IDs
        """
        query = """
        MATCH (d:Plenarprotokoll)
        WHERE d.active = true
        RETURN d.plenarprotokoll_id as plenarprotokoll_id
        ORDER BY d.plenarprotokoll_id
        """

        with self.neo4j_driver.session(database=self.neo4j_database) as session:
            result = session.run(query)
            return [record["plenarprotokoll_id"] for record in result]

    async def _get_neo4j_plenarprotokoll(self, plenarprotokoll_id: str) -> Optional[dict[str, Any]]:
        """Get Plenarprotokoll data from Neo4j.

        Args:
            plenarprotokoll_id: Plenarprotokoll ID

        Returns:
            Plenarprotokoll data dict or None
        """
        query = """
        MATCH (d:Plenarprotokoll {plenarprotokoll_id: $plenarprotokoll_id})
        WHERE d.active = true
        RETURN d
        """

        with self.neo4j_driver.session(database=self.neo4j_database) as session:
            result = session.run(query, plenarprotokoll_id=plenarprotokoll_id)
            record = result.single()
            if record:
                return dict(record["d"])
            return None

    def generate_summary(self, diffs: list[PlenarprotokollDiff]) -> dict[str, Any]:
        """Generate a summary of differences.

        Args:
            diffs: List of PlenarprotokollDiff objects

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

    def _count_changed_fields(self, diffs: list[PlenarprotokollDiff]) -> dict[str, int]:
        """Count which fields changed most frequently.

        Args:
            diffs: List of PlenarprotokollDiff objects

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
