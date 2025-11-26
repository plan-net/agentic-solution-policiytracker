"""
Person (Bundestag Member) Collector for German Bundestag.

Collects information about Members of the Bundestag (MdB) including their
Fraktion membership, committee assignments, electoral constituency, and
biographical information.
"""

import json
import time
from typing import Any

import structlog

from src.flows.bundestag_ingestion.collectors.base_collector import BaseCollector
from src.graphrag.political_schema_v5 import (
    BundestagPerson,
    InWahlperiode,
    MemberOfFraktion,
    RepresentsWahlkreis,
)

logger = structlog.get_logger()


class PersonCollector(BaseCollector):
    """
    Collector for German Bundestag members (MdB).

    Fetches comprehensive information about politicians including their
    parliamentary group membership, committee assignments, electoral data,
    and biographical details. Filters by Wahlperiode for current members.

    Attributes:
        endpoint: "person"
        entity_type: "BundestagPerson"
    """

    @property
    def endpoint(self) -> str:
        """API endpoint for person data."""
        return "person"

    @property
    def entity_type(self) -> str:
        """Entity type produced by this collector."""
        return "BundestagPerson"

    async def collect_and_transform(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Collect person data and transform into entities and edges.

        Process:
        1. Fetch person data from API with optional Wahlperiode filter
        2. Extract Fraktion, Partei, and Wahlkreis information
        3. Create BundestagPerson entities
        4. Create edges to BundestagFraktion, Wahlperiode, and Wahlkreis

        Args:
            inputs: Dictionary containing:
                - filters: API filter parameters
                - limit: Maximum number of persons to fetch
                - wahlperiode: Filter for specific electoral period (optional)
                - current_only: Only fetch current MdBs (default: True)

        Returns:
            Statistics dictionary with collection metrics
        """
        start_time = time.time()

        # Parse inputs
        filters = inputs.get("filters", {})
        limit = inputs.get("limit")
        wahlperiode = inputs.get("wahlperiode")
        current_only = inputs.get("current_only", True)

        errors = []

        try:
            logger.info(
                "Starting Person collection",
                filters=filters,
                limit=limit,
                wahlperiode=wahlperiode,
                current_only=current_only,
            )

            # Add Wahlperiode filter if specified
            if wahlperiode:
                filters["f.wahlperiode"] = wahlperiode

            # Collect persons with pagination
            items, duration = await self._collect_with_timing(filters, limit)

            logger.info("Collected persons", items_count=len(items), duration=duration)

            # Filter for current members if requested
            if current_only:
                items = await self._filter_current_members(items)
                logger.info("Filtered to current members", current_count=len(items))

            # Extract detailed information
            items = await self._extract_fraktion_info(items)
            items = await self._extract_committee_info(items)

            # Transform to entities
            entities = await self._transform_to_entities(items)

            # Transform to edges
            edges = await self._transform_to_edges(items, entities)

            # Save to Neo4j
            save_result = await self.save_to_neo4j(entities, edges)

            # Calculate total duration
            total_duration = self._measure_duration(start_time)

            # Return statistics
            return self._create_statistics(
                entities_created=save_result.get("entities_saved", len(entities)),
                edges_created=save_result.get("edges_saved", len(edges)),
                duration=total_duration,
                items_collected=len(items),
                errors=errors,
            )

        except Exception as e:
            error_msg = f"Person collection failed: {str(e)}"
            logger.error(error_msg, error=str(e))
            errors.append(error_msg)

            return self._create_statistics(
                entities_created=0,
                edges_created=0,
                duration=self._measure_duration(start_time),
                items_collected=0,
                errors=errors,
            )

    async def _filter_current_members(self, persons: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Filter to only include current Bundestag members.

        Checks if person has active membership in current Wahlperiode.

        Args:
            persons: List of person items from API

        Returns:
            Filtered list of current members
        """
        current_members = []

        for person in persons:
            try:
                # Check if person has current Wahlperiode membership
                wahlperioden = person.get("wahlperiode", [])

                if isinstance(wahlperioden, list):
                    # Consider current if any Wahlperiode has no end date
                    has_current = any(
                        wp.get("bis") is None or wp.get("bis") == "" for wp in wahlperioden
                    )

                    if has_current:
                        current_members.append(person)
                elif wahlperioden:
                    # Simple case: any wahlperiode value means current
                    current_members.append(person)

            except Exception as e:
                logger.error("Error filtering person", person_id=person.get("id"), error=str(e))
                continue

        return current_members

    async def _extract_fraktion_info(self, persons: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Extract Fraktion (parliamentary group) information for each person.

        Extracts current and historical Fraktion memberships.

        Args:
            persons: List of person items

        Returns:
            Enhanced persons with fraktion_info field
        """
        logger.info("Extracting Fraktion information", count=len(persons))

        for person in persons:
            try:
                # Extract Fraktion from API data
                # The structure may vary, handle different formats
                fraktion_data = person.get("fraktion")

                if isinstance(fraktion_data, list) and fraktion_data:
                    # Get most recent (current) Fraktion
                    current_fraktion = fraktion_data[0]
                    # Handle both dict and string formats
                    if isinstance(current_fraktion, dict):
                        person["current_fraktion"] = current_fraktion.get("fraktion", "")
                    elif isinstance(current_fraktion, str):
                        person["current_fraktion"] = current_fraktion
                    else:
                        person["current_fraktion"] = None
                elif isinstance(fraktion_data, str):
                    person["current_fraktion"] = fraktion_data
                else:
                    person["current_fraktion"] = None

                # Store all Fraktion memberships for edge creation (only dicts)
                if isinstance(fraktion_data, list):
                    person["fraktion_history"] = [f for f in fraktion_data if isinstance(f, dict)]
                else:
                    person["fraktion_history"] = []

                # Extract Partei (party affiliation)
                partei_data = person.get("partei")
                if isinstance(partei_data, str):
                    person["current_partei"] = partei_data
                elif isinstance(partei_data, list) and partei_data:
                    first_partei = partei_data[0]
                    # Handle both dict and string formats
                    if isinstance(first_partei, dict):
                        person["current_partei"] = first_partei.get("partei", "")
                    elif isinstance(first_partei, str):
                        person["current_partei"] = first_partei
                    else:
                        person["current_partei"] = None
                else:
                    person["current_partei"] = None

            except Exception as e:
                logger.error(
                    "Failed to extract Fraktion info", person_id=person.get("id"), error=str(e)
                )
                person["current_fraktion"] = None
                person["fraktion_history"] = []
                person["current_partei"] = None
                continue

        return persons

    async def _extract_committee_info(self, persons: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Extract committee (Ausschuss) membership information.

        Parses committee assignments with roles and dates.

        Args:
            persons: List of person items

        Returns:
            Enhanced persons with ausschuss_mitgliedschaften field
        """
        logger.info("Extracting committee information", count=len(persons))

        for person in persons:
            try:
                # Extract committee memberships
                ausschuesse = person.get("ausschuss", [])

                if isinstance(ausschuesse, list):
                    parsed_ausschuesse = []

                    for ausschuss in ausschuesse:
                        parsed_ausschuss = {
                            "ausschuss": ausschuss.get("ausschuss_name", ausschuss.get("name", "")),
                            "rolle": ausschuss.get("rolle", "Mitglied"),
                            "von": ausschuss.get("von"),
                            "bis": ausschuss.get("bis"),
                        }
                        parsed_ausschuesse.append(parsed_ausschuss)

                    # Store as JSON string for entity field
                    person["ausschuss_mitgliedschaften"] = json.dumps(
                        parsed_ausschuesse, ensure_ascii=False
                    )

                    logger.debug(
                        "Parsed committee memberships",
                        person_id=person.get("id"),
                        committee_count=len(parsed_ausschuesse),
                    )
                else:
                    person["ausschuss_mitgliedschaften"] = None

            except Exception as e:
                logger.error(
                    "Failed to extract committee info", person_id=person.get("id"), error=str(e)
                )
                person["ausschuss_mitgliedschaften"] = None
                continue

        return persons

    async def _transform_to_entities(self, items: list[dict[str, Any]]) -> list[BundestagPerson]:
        """
        Transform person items into BundestagPerson entities.

        Args:
            items: List of raw person items from API

        Returns:
            List of BundestagPerson entity objects
        """
        # Person API format requires direct entity creation
        # The generic entity_builder doesn't recognize Person API structure
        return await self._create_entities_directly(items)

    async def _create_entities_directly(self, items: list[dict[str, Any]]) -> list[BundestagPerson]:
        """
        Create BundestagPerson entities directly from API items.

        Fallback method when no entity_builder is configured.

        Args:
            items: List of raw person items from API

        Returns:
            List of BundestagPerson entity objects
        """
        entities = []

        for item in items:
            try:
                # Extract personal information
                vorname = item.get("vorname", "")
                nachname = item.get("nachname", "")
                person_name = f"{vorname} {nachname}".strip()

                # Extract Wahlperioden
                wahlperioden_data = item.get("wahlperiode", [])
                if isinstance(wahlperioden_data, list):
                    # API returns list of integers [16, 18, 19, 20, 21] not dicts
                    wahlperioden_nummern = [
                        wp
                        if isinstance(wp, int)
                        else wp.get("nummer")
                        if isinstance(wp, dict)
                        else None
                        for wp in wahlperioden_data
                    ]
                    wahlperioden_nummern = [wp for wp in wahlperioden_nummern if wp is not None]
                else:
                    wahlperioden_nummern = []

                # Create entity
                entity = BundestagPerson(
                    person_name=person_name,
                    person_id=str(item.get("id", "")),
                    fraktion=item.get("current_fraktion"),
                    partei=item.get("current_partei"),
                    wahlperioden=json.dumps(wahlperioden_nummern, ensure_ascii=False)
                    if wahlperioden_nummern
                    else None,
                    ausschuss_mitgliedschaften=item.get("ausschuss_mitgliedschaften"),
                    titel=item.get("titel"),
                    beruf=item.get("beruf"),
                    geburtsdatum=item.get("geburtsdatum"),
                    geburtsort=item.get("geburtsort"),
                    wahlkreis=item.get("wahlkreis", {}).get("name")
                    if isinstance(item.get("wahlkreis"), dict)
                    else None,
                    landesliste=item.get("landesliste"),
                    website=item.get("homepage"),
                    foto_url=item.get("foto_url"),
                    aktualisiert=item.get("aktualisiert"),
                )

                entities.append(entity)

            except Exception as e:
                logger.error(
                    "Failed to create BundestagPerson entity", item_id=item.get("id"), error=str(e)
                )
                continue

        logger.info(
            "Created BundestagPerson entities", input_count=len(items), output_count=len(entities)
        )

        return entities

    async def _transform_to_edges(
        self, items: list[dict[str, Any]], entities: list[BundestagPerson]
    ) -> list[Any]:
        """
        Create relationship edges for BundestagPerson entities.

        Creates:
        - MEMBER_OF_FRAKTION: Link to parliamentary group
        - IN_WAHLPERIODE: Links to electoral periods served
        - REPRESENTS_WAHLKREIS: Link to electoral constituency (if directly elected)

        Args:
            items: Raw person items from API
            entities: Transformed BundestagPerson entities

        Returns:
            List of edge objects
        """
        if self.edge_builder:
            return await super()._transform_to_edges(items, entities)

        # Create edges directly
        edges = []

        for item, entity in zip(items, entities):
            try:
                # Create MEMBER_OF_FRAKTION edges for Fraktion history
                fraktion_history = item.get("fraktion_history", [])
                for fraktion_membership in fraktion_history:
                    fraktion_edge = MemberOfFraktion(
                        joined_date=fraktion_membership.get("von"),
                        left_date=fraktion_membership.get("bis"),
                        role="Mitglied",  # Default role, could be enhanced
                    )
                    edges.append(fraktion_edge)

                # Create IN_WAHLPERIODE edges for each Wahlperiode served
                wahlperioden = item.get("wahlperiode", [])
                if isinstance(wahlperioden, list):
                    for wp in wahlperioden:
                        wp_edge = InWahlperiode(
                            entity_type="BundestagPerson",
                            active_from=wp.get("von"),
                            active_until=wp.get("bis"),
                        )
                        edges.append(wp_edge)

                # Create REPRESENTS_WAHLKREIS edge if directly elected
                wahlkreis_data = item.get("wahlkreis")
                if wahlkreis_data and isinstance(wahlkreis_data, dict):
                    wahlkreis_edge = RepresentsWahlkreis(
                        wahlkreis_nummer=str(wahlkreis_data.get("nummer", "")),
                        wahlkreis_name=wahlkreis_data.get("name", ""),
                        wahlperiode=wahlkreis_data.get("wahlperiode", 0),
                        elected_directly=True,  # Assume true if wahlkreis exists
                        vote_percentage=wahlkreis_data.get("vote_percentage"),
                    )
                    edges.append(wahlkreis_edge)

            except Exception as e:
                logger.error(
                    "Failed to create edges for person", item_id=item.get("id"), error=str(e)
                )
                continue

        logger.info("Created edges for BundestagPerson entities", total_edges=len(edges))

        return edges
