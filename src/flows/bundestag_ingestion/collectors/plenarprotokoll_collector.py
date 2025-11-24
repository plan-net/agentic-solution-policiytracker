"""
Plenarprotokoll (Plenary Session Protocol) Collector for German Bundestag.

Collects complete plenary session transcripts including all speeches, votes,
and procedural actions. Links protocols to relevant Vorgänge (procedures) and
parses agenda items (Tagesordnungspunkte).
"""

import json
import time
from typing import Any

import structlog

from src.flows.bundestag_ingestion.collectors.base_collector import BaseCollector
from src.graphrag.political_schema_v4 import Plenarprotokoll

logger = structlog.get_logger()


class PlenarprotokollCollector(BaseCollector):
    """
    Collector for German Bundestag plenary session protocols.

    Fetches complete session transcripts with speeches, votes, and agenda items.
    Creates Plenarprotokoll entities and links to Wahlperiode and Vorgänge.

    Attributes:
        endpoint: "plenarprotokoll"
        entity_type: "Plenarprotokoll"
    """

    @property
    def endpoint(self) -> str:
        """API endpoint for plenary protocols."""
        return "plenarprotokoll"

    @property
    def entity_type(self) -> str:
        """Entity type produced by this collector."""
        return "Plenarprotokoll"

    async def collect_and_transform(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Collect plenary protocols and transform into entities and edges.

        Process:
        1. Fetch plenary protocols from API with filters
        2. Get full transcript text for each protocol
        3. Parse agenda items (Tagesordnungspunkte)
        4. Create Plenarprotokoll entities
        5. Create edges to Wahlperiode and Vorgänge

        Args:
            inputs: Dictionary containing:
                - filters: API filter parameters
                - limit: Maximum number of protocols to fetch
                - fetch_full_text: Whether to fetch complete transcripts (default: True)

        Returns:
            Statistics dictionary with collection metrics
        """
        start_time = time.time()

        # Parse inputs
        filters = inputs.get("filters", {})
        limit = inputs.get("limit")
        fetch_full_text = inputs.get("fetch_full_text", True)

        errors = []

        try:
            # Debug: Log collection start
            with open("/tmp/plenarprotokoll_save_debug.log", "a") as f:
                f.write("\n\n=== NEW COLLECTION RUN ===\n")
                f.write(f"Filters: {filters}\n")
                f.write(f"Limit: {limit}\n")

            logger.info(
                "Starting Plenarprotokoll collection",
                filters=filters,
                limit=limit,
                fetch_full_text=fetch_full_text,
            )

            # Collect protocols with pagination
            items, duration = await self._collect_with_timing(filters, limit)

            # Debug: Log what API returned
            with open("/tmp/plenarprotokoll_save_debug.log", "a") as f:
                f.write(f"API returned {len(items)} items in {duration}s\n")

            logger.info("Collected plenary protocols", items_count=len(items), duration=duration)

            # Fetch full transcripts if requested
            if fetch_full_text:
                items = await self._fetch_full_texts(items)

            # Parse agenda items for each protocol
            items = await self._parse_agenda_items(items)

            # Transform to entities
            entities = await self._transform_to_entities(items)
            logger.info(
                f"DEBUG: Transformed {len(entities)} entities, types: {[type(e).__name__ for e in entities[:3]]}"
            )

            # Transform to edges
            edges = await self._transform_to_edges(items, entities)
            logger.info(f"DEBUG: Transformed {len(edges)} edges")

            # Save to Neo4j
            logger.info(
                f"DEBUG: About to call save_to_neo4j with {len(entities)} entities and {len(edges)} edges"
            )
            logger.info(f"DEBUG: neo4j_driver is {'SET' if self.neo4j_driver else 'NOT SET'}")
            save_result = await self.save_to_neo4j(entities, edges)
            logger.info(f"DEBUG: save_to_neo4j returned: {save_result}")

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
            error_msg = f"Plenarprotokoll collection failed: {str(e)}"
            logger.error(error_msg, error=str(e))
            errors.append(error_msg)

            return self._create_statistics(
                entities_created=0,
                edges_created=0,
                duration=self._measure_duration(start_time),
                items_collected=0,
                errors=errors,
            )

    async def _fetch_full_texts(self, protocols: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Fetch complete transcript text for each protocol.

        Uses /api/v1/plenarprotokoll-text/{id} endpoint to get full session transcripts.

        Args:
            protocols: List of protocol items from API

        Returns:
            Enhanced protocol items with full_text field
        """
        logger.info("Fetching full transcripts for protocols", count=len(protocols))

        enhanced_protocols = []

        for protocol in protocols:
            try:
                protocol_id = protocol.get("id")
                if not protocol_id:
                    logger.warning(
                        "Protocol missing ID, skipping full text fetch", protocol=protocol
                    )
                    enhanced_protocols.append(protocol)
                    continue

                # Fetch full text from dedicated endpoint
                full_text_endpoint = f"plenarprotokoll-text/{protocol_id}"
                text_response = await self.api_client.get(full_text_endpoint)

                # Extract text content
                full_text = text_response.get("text", "")

                # Add full text to protocol
                protocol["full_text"] = full_text

                logger.debug(
                    "Fetched full text for protocol",
                    protocol_id=protocol_id,
                    text_length=len(full_text),
                )

                enhanced_protocols.append(protocol)

            except Exception as e:
                logger.error(
                    "Failed to fetch full text for protocol",
                    protocol_id=protocol.get("id"),
                    error=str(e),
                )
                # Include protocol without full text
                enhanced_protocols.append(protocol)
                continue

        logger.info(
            "Completed full text fetching",
            total_protocols=len(protocols),
            successful=len([p for p in enhanced_protocols if "full_text" in p]),
        )

        return enhanced_protocols

    async def _parse_agenda_items(self, protocols: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Parse Tagesordnungspunkte (agenda items) from protocols.

        Extracts agenda items with their associated Vorgänge (procedures).

        Args:
            protocols: List of protocol items

        Returns:
            Enhanced protocols with parsed tagesordnungspunkte
        """
        logger.info("Parsing agenda items for protocols", count=len(protocols))

        for protocol in protocols:
            try:
                # Check if protocol has agenda items data
                if "tagesordnungspunkt" in protocol:
                    tops = protocol.get("tagesordnungspunkt", [])

                    # Parse agenda items
                    parsed_tops = []
                    for top in tops:
                        parsed_top = {
                            "top_nummer": top.get("nummer", ""),
                            "titel": top.get("titel", ""),
                            "vorgaenge": top.get("vorgangsposition", []),
                        }
                        parsed_tops.append(parsed_top)

                    # Store as JSON string for entity field
                    protocol["tagesordnungspunkte"] = json.dumps(parsed_tops, ensure_ascii=False)

                    logger.debug(
                        "Parsed agenda items",
                        protocol_id=protocol.get("id"),
                        top_count=len(parsed_tops),
                    )
                else:
                    protocol["tagesordnungspunkte"] = None

            except Exception as e:
                logger.error(
                    "Failed to parse agenda items", protocol_id=protocol.get("id"), error=str(e)
                )
                protocol["tagesordnungspunkte"] = None
                continue

        return protocols

    async def _transform_to_entities(self, items: list[dict[str, Any]]) -> list[Plenarprotokoll]:
        """
        Transform protocol items into Plenarprotokoll entities.

        Args:
            items: List of raw protocol items from API

        Returns:
            List of Plenarprotokoll entity objects
        """
        if not self.entity_builder:
            logger.warning("No entity_builder configured, creating entities directly")
            return await self._create_entities_directly(items)

        return await super()._transform_to_entities(items)

    async def _create_entities_directly(self, items: list[dict[str, Any]]) -> list[Plenarprotokoll]:
        """
        Create Plenarprotokoll entities directly from API items.

        Fallback method when no entity_builder is configured.

        Args:
            items: List of raw protocol items from API

        Returns:
            List of Plenarprotokoll entity objects
        """
        entities = []

        # Debug: Log what we received from API
        with open("/tmp/plenarprotokoll_save_debug.log", "a") as f:
            f.write(f"\n=== _create_entities_directly called with {len(items)} items ===\n")
            if items:
                f.write(f"Sample item keys: {list(items[0].keys())}\n")
                f.write(f"Sample item: {items[0]}\n")

        for item in items:
            try:
                # Extract core fields
                wahlperiode = item.get("wahlperiode", 0)
                # Use dokumentnummer as sitzungsnummer (API doesn't return sitzungsnummer field)
                sitzungsnummer = item.get("dokumentnummer", "")
                datum = item.get("datum", "")
                herausgeber = item.get("herausgeber", "BT")

                with open("/tmp/plenarprotokoll_save_debug.log", "a") as f:
                    f.write(
                        f"Item: sitzung={sitzungsnummer}, wp={wahlperiode}, herausgeber={herausgeber}, titel={item.get('titel', 'N/A')[:50]}\n"
                    )

                # Filter out protocols without sitzungsnummer
                if not sitzungsnummer:
                    with open("/tmp/plenarprotokoll_save_debug.log", "a") as f:
                        f.write("  -> SKIPPED: No sitzungsnummer\n")
                    logger.warning(
                        "Skipping protocol without sitzungsnummer",
                        titel=item.get("titel"),
                        herausgeber=herausgeber,
                    )
                    continue

                # Create entity
                entity = Plenarprotokoll(
                    plenarprotokoll_name=item.get("titel", f"Sitzung {sitzungsnummer}"),
                    sitzungsnummer=sitzungsnummer,
                    wahlperiode=wahlperiode,
                    datum=datum,
                    herausgeber=item.get("herausgeber", "BT"),
                    pdf_url=item.get("fundstelle", {}).get("pdf_url")
                    if isinstance(item.get("fundstelle"), dict)
                    else None,
                    full_text=item.get("full_text"),
                    tagesordnungspunkte=item.get("tagesordnungspunkte"),
                    reden_anzahl=item.get("reden_anzahl"),
                    fundstelle=item.get("fundstelle", {}).get("fundstelle")
                    if isinstance(item.get("fundstelle"), dict)
                    else None,
                    aktualisiert=item.get("aktualisiert"),
                    vorgangsbezug_anzahl=item.get("vorgangsbezug_anzahl"),
                    related_vorgang_ids=json.dumps(
                        item.get("vorgangsbezug", []), ensure_ascii=False
                    )
                    if item.get("vorgangsbezug")
                    else None,
                    url=item.get("fundstelle", {}).get("dokumentnummer")
                    if isinstance(item.get("fundstelle"), dict)
                    else None,
                )

                entities.append(entity)

            except Exception as e:
                logger.error(
                    "Failed to create Plenarprotokoll entity", item_id=item.get("id"), error=str(e)
                )
                continue

        logger.info(
            "Created Plenarprotokoll entities", input_count=len(items), output_count=len(entities)
        )

        return entities

    async def _transform_to_edges(
        self, items: list[dict[str, Any]], entities: list[Plenarprotokoll]
    ) -> list[Any]:
        """
        Create relationship edges for Plenarprotokoll entities.

        Creates:
        - IN_WAHLPERIODE: Link to electoral period
        - REFERENCES_VORGANG: Links to discussed Vorgänge

        Args:
            items: Raw protocol items from API
            entities: Transformed Plenarprotokoll entities

        Returns:
            List of edge objects
        """
        if self.edge_builder:
            return await super()._transform_to_edges(items, entities)

        # Create edges directly with from_id and to_id
        edges = []

        for item, entity in zip(items, entities):
            try:
                # Create IN_WAHLPERIODE edge: Plenarprotokoll -> Wahlperiode
                # Use composite key for Plenarprotokoll as from_id
                plenarprotokoll_id = f"{entity.sitzungsnummer}_{entity.wahlperiode}"
                wahlperiode_id = str(entity.wahlperiode)

                wahlperiode_edge = {
                    "type": "IN_WAHLPERIODE",
                    "from_id": plenarprotokoll_id,
                    "to_id": wahlperiode_id,
                    "entity_type": "Plenarprotokoll",
                    "active_from": item.get("datum"),
                    "active_until": None,
                }
                edges.append(wahlperiode_edge)

                # Create REFERENCES_VORGANG edges for each related procedure
                vorgaenge = item.get("vorgangsbezug", [])
                for vorgang_ref in vorgaenge:
                    vorgang_id = vorgang_ref.get("id")
                    if vorgang_id:
                        vorgang_edge = {
                            "type": "REFERENCES_VORGANG",
                            "from_id": plenarprotokoll_id,
                            "to_id": vorgang_id,
                            "reference_type": "debated_in_plenum",
                            "context": f"Discussed in plenary session {entity.sitzungsnummer}",
                        }
                        edges.append(vorgang_edge)

            except Exception as e:
                logger.error(
                    "Failed to create edges for protocol", item_id=item.get("id"), error=str(e)
                )
                continue

        logger.info("Created edges for Plenarprotokoll entities", total_edges=len(edges))

        return edges
