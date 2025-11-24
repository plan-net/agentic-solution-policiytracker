"""DiffAnalyzer - Compare Neo4j data with Bundestag DIP API."""
import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class PersonDiff:
    """Represents the difference for a single person."""

    def __init__(
        self,
        person_id: str,
        diff_type: str,  # "missing", "outdated", "relationship_missing"
        neo4j_data: Optional[dict] = None,
        dip_data: Optional[dict] = None,
        changed_fields: Optional[set[str]] = None,
    ):
        self.person_id = person_id
        self.diff_type = diff_type
        self.neo4j_data = neo4j_data or {}
        self.dip_data = dip_data or {}
        self.changed_fields = changed_fields or set()

    def __repr__(self):
        return (
            f"PersonDiff(id={self.person_id}, type={self.diff_type}, fields={self.changed_fields})"
        )


class DiffAnalyzer:
    """Analyzes differences between Neo4j and Bundestag DIP API data."""

    def __init__(self, neo4j_driver, neo4j_database, dip_client):
        """Initialize DiffAnalyzer.

        Args:
            neo4j_driver: Neo4j driver instance
            neo4j_database: Neo4j database name
            dip_client: Bundestag DIP API client
        """
        self.neo4j_driver = neo4j_driver
        self.neo4j_database = neo4j_database
        self.dip_client = dip_client

        # Fields to compare
        self.PERSON_FIELDS = [
            "vorname",
            "nachname",
            "titel",
            "geschlecht",
            "geburtsdatum",
            "geburtsort",
            "sterbedatum",
            "fraktion",
            "land",
            "wahlkreis",
        ]

        logger.info("DiffAnalyzer initialized")

    async def analyze_all_persons(self, limit: Optional[int] = None) -> list[PersonDiff]:
        """Analyze all persons and find differences.

        Args:
            limit: Maximum number of persons to analyze (None = all)

        Returns:
            List of PersonDiff objects
        """
        logger.info(f"Starting analysis of all persons (limit={limit})")

        # 1. Get all person IDs from DIP API
        dip_person_ids = await self.dip_client.get_all_person_ids(limit=limit)
        logger.info(f"Found {len(dip_person_ids)} persons in DIP API")

        # 2. Get all person IDs from Neo4j
        neo4j_person_ids = await self._get_neo4j_person_ids()
        logger.info(f"Found {len(neo4j_person_ids)} persons in Neo4j")

        # 3. Find missing persons (in DIP but not in Neo4j)
        missing_ids = set(dip_person_ids) - set(neo4j_person_ids)
        logger.info(f"Found {len(missing_ids)} missing persons")

        # 4. Find potentially outdated persons (in both)
        existing_ids = set(dip_person_ids) & set(neo4j_person_ids)
        logger.info(f"Found {len(existing_ids)} existing persons to check for updates")

        # 5. Analyze differences
        all_diffs = []

        # Add missing persons
        for person_id in missing_ids:
            dip_data = await self.dip_client.get_person_by_id(person_id)
            all_diffs.append(
                PersonDiff(
                    person_id=person_id,
                    diff_type="missing",
                    dip_data=dip_data,
                )
            )

        # Check existing persons for updates
        for person_id in existing_ids:
            diff = await self._compare_single_person(person_id)
            if diff:
                all_diffs.append(diff)

        logger.info(f"Analysis complete: {len(all_diffs)} differences found")
        return all_diffs

    async def analyze_specific_persons(self, person_ids: list[str]) -> list[PersonDiff]:
        """Analyze specific persons.

        Args:
            person_ids: List of person IDs to analyze

        Returns:
            List of PersonDiff objects
        """
        logger.info(f"Analyzing {len(person_ids)} specific persons")

        all_diffs = []
        for person_id in person_ids:
            diff = await self._compare_single_person(person_id)
            if diff:
                all_diffs.append(diff)

        return all_diffs

    async def _compare_single_person(self, person_id: str) -> Optional[PersonDiff]:
        """Compare a single person between Neo4j and DIP API.

        Args:
            person_id: Person ID to compare

        Returns:
            PersonDiff if differences found, None otherwise
        """
        # Get data from both sources
        neo4j_data = await self._get_neo4j_person(person_id)
        dip_data = await self.dip_client.get_person_by_id(person_id)

        if not neo4j_data and dip_data:
            # Person missing in Neo4j
            return PersonDiff(person_id=person_id, diff_type="missing", dip_data=dip_data)

        if not dip_data:
            # Person not in DIP API (shouldn't happen, but handle it)
            logger.warning(f"Person {person_id} not found in DIP API")
            return None

        # Compare fields
        changed_fields = set()
        for field in self.PERSON_FIELDS:
            neo4j_value = neo4j_data.get(field)
            dip_value = dip_data.get(field)

            # Normalize values for comparison
            if neo4j_value != dip_value:
                # Skip if both are None/empty
                if not neo4j_value and not dip_value:
                    continue
                changed_fields.add(field)

        if changed_fields:
            return PersonDiff(
                person_id=person_id,
                diff_type="outdated",
                neo4j_data=neo4j_data,
                dip_data=dip_data,
                changed_fields=changed_fields,
            )

        return None

    async def _get_neo4j_person_ids(self) -> list[str]:
        """Get all person IDs from Neo4j.

        Returns:
            List of person IDs
        """
        query = """
        MATCH (p:BundestagPerson)
        WHERE p.active = true
        RETURN p.person_id as person_id
        ORDER BY p.person_id
        """

        with self.neo4j_driver.session(database=self.neo4j_database) as session:
            result = session.run(query)
            return [record["person_id"] for record in result]

    async def _get_neo4j_person(self, person_id: str) -> Optional[dict[str, Any]]:
        """Get person data from Neo4j.

        Args:
            person_id: Person ID

        Returns:
            Person data dict or None
        """
        query = """
        MATCH (p:BundestagPerson {person_id: $person_id})
        WHERE p.active = true
        RETURN p
        """

        with self.neo4j_driver.session(database=self.neo4j_database) as session:
            result = session.run(query, person_id=person_id)
            record = result.single()
            if record:
                return dict(record["p"])
            return None

    def generate_summary(self, diffs: list[PersonDiff]) -> dict[str, Any]:
        """Generate a summary of differences.

        Args:
            diffs: List of PersonDiff objects

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

    def _count_changed_fields(self, diffs: list[PersonDiff]) -> dict[str, int]:
        """Count which fields changed most frequently.

        Args:
            diffs: List of PersonDiff objects

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
