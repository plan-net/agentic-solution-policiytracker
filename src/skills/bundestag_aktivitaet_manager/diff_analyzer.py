"""DiffAnalyzer - Compare Neo4j Aktivitaet data with Bundestag DIP API."""
import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AktivitaetDiff:
    """Represents the difference for a single Aktivitaet."""

    def __init__(
        self,
        aktivitaet_id: str,
        diff_type: str,  # "missing", "outdated", "relationship_missing"
        neo4j_data: Optional[dict] = None,
        dip_data: Optional[dict] = None,
        changed_fields: Optional[set[str]] = None,
    ):
        self.aktivitaet_id = aktivitaet_id
        self.diff_type = diff_type
        self.neo4j_data = neo4j_data or {}
        self.dip_data = dip_data or {}
        self.changed_fields = changed_fields or set()

    def __repr__(self):
        return f"AktivitaetDiff(id={self.aktivitaet_id}, type={self.diff_type}, fields={self.changed_fields})"


class AktivitaetDiffAnalyzer:
    """Analyzes differences between Neo4j and Bundestag DIP API Aktivitaet data."""

    def __init__(self, neo4j_driver, neo4j_database, dip_client):
        """Initialize AktivitaetDiffAnalyzer.

        Args:
            neo4j_driver: Neo4j driver instance
            neo4j_database: Neo4j database name
            dip_client: Bundestag DIP API client for Aktivitaet
        """
        self.neo4j_driver = neo4j_driver
        self.neo4j_database = neo4j_database
        self.dip_client = dip_client

        # Fields to compare
        self.AKTIVITAET_FIELDS = [
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

        logger.info("AktivitaetDiffAnalyzer initialized")

    async def analyze_all_aktivitaeten(self, limit: Optional[int] = None) -> list[AktivitaetDiff]:
        """Analyze all Aktivitaetn and find differences.

        Args:
            limit: Maximum number of Aktivitaetn to analyze (None = all)

        Returns:
            List of AktivitaetDiff objects
        """
        logger.info(f"Starting analysis of all Aktivitaetn (limit={limit})")

        # 1. Get all Aktivitaet IDs from DIP API
        dip_aktivitaet_ids = await self.dip_client.get_all_aktivitaet_ids(limit=limit)
        logger.info(f"Found {len(dip_aktivitaet_ids)} Aktivitaetn in DIP API")

        # 2. Get all Aktivitaet IDs from Neo4j
        neo4j_aktivitaet_ids = await self._get_neo4j_aktivitaet_ids()
        logger.info(f"Found {len(neo4j_aktivitaet_ids)} Aktivitaetn in Neo4j")

        # 3. Find missing Aktivitaetn (in DIP but not in Neo4j)
        missing_ids = set(dip_aktivitaet_ids) - set(neo4j_aktivitaet_ids)
        logger.info(f"Found {len(missing_ids)} missing Aktivitaetn")

        # 4. Find potentially outdated Aktivitaetn (in both)
        existing_ids = set(dip_aktivitaet_ids) & set(neo4j_aktivitaet_ids)
        logger.info(f"Found {len(existing_ids)} existing Aktivitaetn to check for updates")

        # 5. Analyze differences
        all_diffs = []

        # Add missing Aktivitaetn
        for aktivitaet_id in missing_ids:
            dip_data = await self.dip_client.get_aktivitaet_by_id(aktivitaet_id)
            all_diffs.append(
                AktivitaetDiff(
                    aktivitaet_id=aktivitaet_id,
                    diff_type="missing",
                    dip_data=dip_data,
                )
            )

        # Check existing Aktivitaetn for updates
        for aktivitaet_id in existing_ids:
            diff = await self._compare_single_aktivitaet(aktivitaet_id)
            if diff:
                all_diffs.append(diff)

        logger.info(f"Analysis complete: {len(all_diffs)} differences found")
        return all_diffs

    async def analyze_specific_aktivitaeten(
        self, aktivitaet_ids: list[str]
    ) -> list[AktivitaetDiff]:
        """Analyze specific Aktivitaetn.

        Args:
            aktivitaet_ids: List of Aktivitaet IDs to analyze

        Returns:
            List of AktivitaetDiff objects
        """
        logger.info(f"Analyzing {len(aktivitaet_ids)} specific Aktivitaetn")

        all_diffs = []
        for aktivitaet_id in aktivitaet_ids:
            diff = await self._compare_single_aktivitaet(aktivitaet_id)
            if diff:
                all_diffs.append(diff)

        return all_diffs

    async def _compare_single_aktivitaet(self, aktivitaet_id: str) -> Optional[AktivitaetDiff]:
        """Compare a single Aktivitaet between Neo4j and DIP API.

        Args:
            aktivitaet_id: Aktivitaet ID to compare

        Returns:
            AktivitaetDiff if differences found, None otherwise
        """
        # Get data from both sources
        neo4j_data = await self._get_neo4j_aktivitaet(aktivitaet_id)
        dip_data = await self.dip_client.get_aktivitaet_by_id(aktivitaet_id)

        if not neo4j_data and dip_data:
            # Aktivitaet missing in Neo4j
            return AktivitaetDiff(
                aktivitaet_id=aktivitaet_id, diff_type="missing", dip_data=dip_data
            )

        if not dip_data:
            # Aktivitaet not in DIP API (shouldn't happen, but handle it)
            logger.warning(f"Aktivitaet {aktivitaet_id} not found in DIP API")
            return None

        # Compare fields
        changed_fields = set()
        for field in self.AKTIVITAET_FIELDS:
            neo4j_value = neo4j_data.get(field)
            dip_value = dip_data.get(field)

            # Normalize values for comparison
            if neo4j_value != dip_value:
                # Skip if both are None/empty
                if not neo4j_value and not dip_value:
                    continue
                changed_fields.add(field)

        if changed_fields:
            return AktivitaetDiff(
                aktivitaet_id=aktivitaet_id,
                diff_type="outdated",
                neo4j_data=neo4j_data,
                dip_data=dip_data,
                changed_fields=changed_fields,
            )

        return None

    async def _get_neo4j_aktivitaet_ids(self) -> list[str]:
        """Get all Aktivitaet IDs from Neo4j.

        Returns:
            List of Aktivitaet IDs
        """
        query = """
        MATCH (d:Aktivitaet)
        WHERE d.active = true
        RETURN d.aktivitaet_id as aktivitaet_id
        ORDER BY d.aktivitaet_id
        """

        with self.neo4j_driver.session(database=self.neo4j_database) as session:
            result = session.run(query)
            return [record["aktivitaet_id"] for record in result]

    async def _get_neo4j_aktivitaet(self, aktivitaet_id: str) -> Optional[dict[str, Any]]:
        """Get Aktivitaet data from Neo4j.

        Args:
            aktivitaet_id: Aktivitaet ID

        Returns:
            Aktivitaet data dict or None
        """
        query = """
        MATCH (d:Aktivitaet {aktivitaet_id: $aktivitaet_id})
        WHERE d.active = true
        RETURN d
        """

        with self.neo4j_driver.session(database=self.neo4j_database) as session:
            result = session.run(query, aktivitaet_id=aktivitaet_id)
            record = result.single()
            if record:
                return dict(record["d"])
            return None

    def generate_summary(self, diffs: list[AktivitaetDiff]) -> dict[str, Any]:
        """Generate a summary of differences.

        Args:
            diffs: List of AktivitaetDiff objects

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

    def _count_changed_fields(self, diffs: list[AktivitaetDiff]) -> dict[str, int]:
        """Count which fields changed most frequently.

        Args:
            diffs: List of AktivitaetDiff objects

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
