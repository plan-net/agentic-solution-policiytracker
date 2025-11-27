"""DiffAnalyzer - Compare Neo4j Vorgang data with Bundestag DIP API."""
import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class VorgangDiff:
    """Represents the difference for a single Vorgang."""

    def __init__(
        self,
        vorgang_id: str,
        diff_type: str,  # "missing", "outdated", "relationship_missing"
        neo4j_data: Optional[dict] = None,
        dip_data: Optional[dict] = None,
        changed_fields: Optional[set[str]] = None,
    ):
        self.vorgang_id = vorgang_id
        self.diff_type = diff_type
        self.neo4j_data = neo4j_data or {}
        self.dip_data = dip_data or {}
        self.changed_fields = changed_fields or set()

    def __repr__(self):
        return f"VorgangDiff(id={self.vorgang_id}, type={self.diff_type}, fields={self.changed_fields})"


class VorgangDiffAnalyzer:
    """Analyzes differences between Neo4j and Bundestag DIP API Vorgang data."""

    def __init__(self, neo4j_driver, neo4j_database, dip_client):
        """Initialize VorgangDiffAnalyzer.

        Args:
            neo4j_driver: Neo4j driver instance
            neo4j_database: Neo4j database name
            dip_client: Bundestag DIP API client for Vorgang
        """
        self.neo4j_driver = neo4j_driver
        self.neo4j_database = neo4j_database
        self.dip_client = dip_client

        # Fields to compare
        self.VORGANG_FIELDS = [
            "titel",
            "vorgangstyp",
            "beratungsstand",
            "initiative",
            "sachgebiet",
            "wahlperiode",
            "datum",
            "aktualisiert",
            "abstract",
            "schlagwort",
        ]

        logger.info("VorgangDiffAnalyzer initialized")

    async def analyze_all_vorgaenge(
        self, limit: Optional[int] = None, wahlperiode: Optional[str] = None
    ) -> list[VorgangDiff]:
        """Analyze all Vorgänge and find differences.

        Args:
            limit: Maximum number of Vorgänge to analyze (None = all)
            wahlperiode: Filter by Wahlperiode (e.g., "21")

        Returns:
            List of VorgangDiff objects
        """
        logger.info(f"Starting analysis of all Vorgänge (limit={limit}, wahlperiode={wahlperiode})")

        # 1. Get all Vorgang IDs from DIP API
        dip_vorgang_ids = await self.dip_client.get_all_vorgang_ids(
            limit=limit, wahlperiode=wahlperiode
        )
        logger.info(f"Found {len(dip_vorgang_ids)} Vorgänge in DIP API")

        # 2. Get all Vorgang IDs from Neo4j
        neo4j_vorgang_ids = await self._get_neo4j_vorgang_ids()
        logger.info(f"Found {len(neo4j_vorgang_ids)} Vorgänge in Neo4j")

        # 3. Find missing Vorgänge (in DIP but not in Neo4j)
        missing_ids = set(dip_vorgang_ids) - set(neo4j_vorgang_ids)
        logger.info(f"Found {len(missing_ids)} missing Vorgänge")

        # 4. Find potentially outdated Vorgänge (in both)
        existing_ids = set(dip_vorgang_ids) & set(neo4j_vorgang_ids)
        logger.info(f"Found {len(existing_ids)} existing Vorgänge to check for updates")

        # 5. Analyze differences
        all_diffs = []

        # Add missing Vorgänge
        for vorgang_id in missing_ids:
            dip_data = await self.dip_client.get_vorgang_by_id(vorgang_id)
            all_diffs.append(
                VorgangDiff(
                    vorgang_id=vorgang_id,
                    diff_type="missing",
                    dip_data=dip_data,
                )
            )

        # Check existing Vorgänge for updates
        for vorgang_id in existing_ids:
            diff = await self._compare_single_vorgang(vorgang_id)
            if diff:
                all_diffs.append(diff)

        logger.info(f"Analysis complete: {len(all_diffs)} differences found")
        return all_diffs

    async def analyze_specific_vorgaenge(self, vorgang_ids: list[str]) -> list[VorgangDiff]:
        """Analyze specific Vorgänge.

        Args:
            vorgang_ids: List of Vorgang IDs to analyze

        Returns:
            List of VorgangDiff objects
        """
        logger.info(f"Analyzing {len(vorgang_ids)} specific Vorgänge")

        all_diffs = []
        for vorgang_id in vorgang_ids:
            diff = await self._compare_single_vorgang(vorgang_id)
            if diff:
                all_diffs.append(diff)

        return all_diffs

    async def _compare_single_vorgang(self, vorgang_id: str) -> Optional[VorgangDiff]:
        """Compare a single Vorgang between Neo4j and DIP API.

        Args:
            vorgang_id: Vorgang ID to compare

        Returns:
            VorgangDiff if differences found, None otherwise
        """
        # Get data from both sources
        neo4j_data = await self._get_neo4j_vorgang(vorgang_id)
        dip_data = await self.dip_client.get_vorgang_by_id(vorgang_id)

        if not neo4j_data and dip_data:
            # Vorgang missing in Neo4j
            return VorgangDiff(vorgang_id=vorgang_id, diff_type="missing", dip_data=dip_data)

        if not dip_data:
            # Vorgang not in DIP API (shouldn't happen, but handle it)
            logger.warning(f"Vorgang {vorgang_id} not found in DIP API")
            return None

        # Compare fields
        changed_fields = set()
        for field in self.VORGANG_FIELDS:
            neo4j_value = neo4j_data.get(field)
            dip_value = dip_data.get(field)

            # Normalize values for comparison
            if neo4j_value != dip_value:
                # Skip if both are None/empty
                if not neo4j_value and not dip_value:
                    continue
                changed_fields.add(field)

        if changed_fields:
            return VorgangDiff(
                vorgang_id=vorgang_id,
                diff_type="outdated",
                neo4j_data=neo4j_data,
                dip_data=dip_data,
                changed_fields=changed_fields,
            )

        return None

    async def _get_neo4j_vorgang_ids(self) -> list[str]:
        """Get all Vorgang IDs from Neo4j.

        Returns:
            List of Vorgang IDs
        """
        query = """
        MATCH (v:Vorgang)
        RETURN v.vorgang_id as vorgang_id
        ORDER BY v.vorgang_id
        """

        with self.neo4j_driver.session(database=self.neo4j_database) as session:
            result = session.run(query)
            return [record["vorgang_id"] for record in result]

    async def _get_neo4j_vorgang(self, vorgang_id: str) -> Optional[dict[str, Any]]:
        """Get Vorgang data from Neo4j.

        Args:
            vorgang_id: Vorgang ID

        Returns:
            Vorgang data dict or None
        """
        query = """
        MATCH (v:Vorgang {vorgang_id: $vorgang_id})
        RETURN v
        """

        with self.neo4j_driver.session(database=self.neo4j_database) as session:
            result = session.run(query, vorgang_id=vorgang_id)
            record = result.single()
            if record:
                return dict(record["v"])
            return None

    def generate_summary(self, diffs: list[VorgangDiff]) -> dict[str, Any]:
        """Generate a summary of differences.

        Args:
            diffs: List of VorgangDiff objects

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

    def _count_changed_fields(self, diffs: list[VorgangDiff]) -> dict[str, int]:
        """Count which fields changed most frequently.

        Args:
            diffs: List of VorgangDiff objects

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
