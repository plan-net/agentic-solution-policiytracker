"""
Drucksache Collector for German Bundestag parliamentary documents.

Collects Drucksache (parliamentary document) data from the Bundestag DIP API,
fetches full text content, and transforms into knowledge graph entities.
"""

import asyncio
import time
from typing import Any, Optional

import structlog

from src.flows.bundestag_ingestion.collectors.base_collector import BaseCollector

logger = structlog.get_logger()


class DrucksacheCollector(BaseCollector):
    """
    Collector for Drucksache (parliamentary document) entities.

    A Drucksache is an official parliamentary document in the Bundestag, including
    legislative proposals (Gesetzentwürfe), motions (Anträge), committee
    recommendations (Beschlussempfehlungen), and reports (Berichte). This collector
    fetches Drucksachen from the DIP API, retrieves full text content, and transforms
    them into knowledge graph entities with appropriate relationships.

    Attributes:
        endpoint: API endpoint ("drucksache")
        entity_type: Entity type ("Drucksache")
        api_client: BundestagAPIClient instance
        entity_builder: Builder for creating Drucksache entities
        edge_builder: Builder for creating relationship edges
    """

    @property
    def endpoint(self) -> str:
        """API endpoint for Drucksache collection."""
        return "drucksache"

    @property
    def entity_type(self) -> str:
        """Entity type produced by this collector."""
        return "Drucksache"

    async def collect_and_transform(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Collect Drucksache data from API and transform into entities and edges.

        Process:
        1. Parse input filters (wahlperiode, dokumentart, datum_von/bis, limit)
        2. Fetch Drucksachen from /api/v1/drucksache with pagination
        3. For each Drucksache, fetch full text from /api/v1/drucksache-text/{id}
        4. Create entity with full_text field populated using entity_builder
        5. Create edges to Wahlperiode and related Vorgang using edge_builder
        6. Return collection statistics

        Args:
            inputs: Dictionary containing:
                - filters: Dict of filter parameters (optional)
                - wahlperiode: Legislative period (optional)
                - dokumentart: Document type (optional)
                - datum_von: Start date ISO 8601 (optional)
                - datum_bis: End date ISO 8601 (optional)
                - limit: Maximum number of items (optional)
                - fetch_full_text: Whether to fetch full text (default: True)

        Returns:
            Dictionary with collection statistics:
            {
                "entities_created": int,
                "edges_created": int,
                "duration": float,
                "items_collected": int,
                "full_text_fetched": int,
                "errors": List[str]
            }
        """
        start_time = time.time()
        errors: list[str] = []

        logger.info("Starting Drucksache collection", inputs=inputs)

        try:
            # Extract filter parameters
            filters = self._extract_filters(inputs)
            limit = inputs.get("limit")
            fetch_full_text = inputs.get("fetch_full_text", True)

            logger.info(
                "Collecting Drucksachen with filters",
                filters=filters,
                limit=limit,
                fetch_full_text=fetch_full_text,
            )

            # Fetch Drucksachen with pagination
            drucksachen, fetch_duration = await self._collect_with_timing(filters, limit)

            logger.info("Fetched Drucksachen", count=len(drucksachen), duration=fetch_duration)

            # Fetch full text for each Drucksache if enabled
            full_text_count = 0
            if fetch_full_text:
                full_text_count = await self._fetch_full_text_for_all(drucksachen, errors)

            # Transform to entities and edges
            entities_created = 0
            edges_created = 0

            if self.entity_builder and self.edge_builder:
                # Transform to entities
                entities = await self._transform_to_entities(drucksachen)
                entities_created = len(entities)

                # Transform to edges (includes Wahlperiode and Vorgang relationships)
                edges = await self._transform_to_edges(drucksachen, entities)
                edges_created = len(edges)

                logger.info(
                    "Transformation complete",
                    entities_created=entities_created,
                    edges_created=edges_created,
                )
            else:
                logger.warning(
                    "No entity_builder or edge_builder configured",
                    entities_created=0,
                    edges_created=0,
                )

            # Calculate total duration
            duration = self._measure_duration(start_time)

            # Return statistics
            stats = self._create_statistics(
                entities_created=entities_created,
                edges_created=edges_created,
                duration=duration,
                items_collected=len(drucksachen),
                errors=errors,
            )

            # Add full text statistics
            stats["full_text_fetched"] = full_text_count

            return stats

        except Exception as e:
            error_msg = f"Drucksache collection failed: {str(e)}"
            logger.error(error_msg, error=str(e), exc_info=True)
            errors.append(error_msg)

            duration = self._measure_duration(start_time)

            return self._create_statistics(
                entities_created=0,
                edges_created=0,
                duration=duration,
                items_collected=0,
                errors=errors,
            )

    def _extract_filters(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Extract and build filter parameters from inputs.

        Args:
            inputs: Raw input dictionary

        Returns:
            Filter dictionary for API request
        """
        from src.flows.bundestag_ingestion.utils.filters import FilterBuilder

        # Check if filters are pre-built
        if "filters" in inputs:
            filters: dict[str, Any] = inputs["filters"]
            return filters

        # Build filters from individual parameters
        filter_builder = FilterBuilder()  # type: ignore[no-untyped-call]

        filters = filter_builder.build_filters(
            wahlperiode=inputs.get("wahlperiode"),
            datum_von=inputs.get("datum_von"),
            datum_bis=inputs.get("datum_bis"),
            limit=inputs.get("limit"),
            dokumentart=inputs.get("dokumentart"),
        )

        logger.debug("Built filters from inputs", filters=filters)

        return filters

    async def _fetch_full_text_for_all(
        self, drucksachen: list[dict[str, Any]], errors: list[str]
    ) -> int:
        """
        Fetch full text content for all Drucksachen.

        Makes parallel requests to the drucksache-text endpoint for each document.
        Populates the "full_text" field in each Drucksache dictionary.

        Args:
            drucksachen: List of Drucksache dictionaries
            errors: List to append error messages to

        Returns:
            Number of documents with successfully fetched full text
        """
        if not drucksachen:
            return 0

        logger.info("Fetching full text for Drucksachen", count=len(drucksachen))

        # Create tasks for fetching full text
        tasks = [self._fetch_single_full_text(drucksache, errors) for drucksache in drucksachen]

        # Execute in parallel with limited concurrency
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes
        success_count = sum(1 for result in results if result is True)

        logger.info(
            "Full text fetch complete",
            total=len(drucksachen),
            successful=success_count,
            failed=len(drucksachen) - success_count,
        )

        return success_count

    async def _fetch_single_full_text(self, drucksache: dict[str, Any], errors: list[str]) -> bool:
        """
        Fetch full text for a single Drucksache.

        Args:
            drucksache: Drucksache dictionary to populate with full text
            errors: List to append error messages to

        Returns:
            True if successful, False otherwise
        """
        drucksache_id = drucksache.get("id")

        if not drucksache_id:
            logger.warning("Drucksache missing ID, cannot fetch full text")
            return False

        try:
            # Fetch full text from drucksache-text endpoint
            response = await self.api_client.get_by_id("drucksache-text", drucksache_id)

            # Extract text content
            full_text = response.get("text", "")

            if full_text:
                drucksache["full_text"] = full_text
                logger.debug(
                    "Fetched full text", drucksache_id=drucksache_id, text_length=len(full_text)
                )
                return True
            else:
                logger.warning("No full text available", drucksache_id=drucksache_id)
                drucksache["full_text"] = None
                return False

        except Exception as e:
            error_msg = f"Failed to fetch full text for Drucksache {drucksache_id}: {str(e)}"
            logger.error(error_msg, drucksache_id=drucksache_id, error=str(e))
            errors.append(error_msg)
            drucksache["full_text"] = None
            return False

    async def collect_by_wahlperiode(
        self, wahlperiode: str, limit: Optional[int] = None, fetch_full_text: bool = True
    ) -> dict[str, Any]:
        """
        Convenience method to collect Drucksachen for a specific legislative period.

        Args:
            wahlperiode: Legislative period number (e.g., "20")
            limit: Maximum number of Drucksachen to collect
            fetch_full_text: Whether to fetch full text content

        Returns:
            Collection statistics dictionary
        """
        logger.info(
            "Collecting Drucksachen for Wahlperiode",
            wahlperiode=wahlperiode,
            limit=limit,
            fetch_full_text=fetch_full_text,
        )

        return await self.collect_with_filters(
            wahlperiode=wahlperiode, limit=limit, fetch_full_text=fetch_full_text
        )

    async def collect_by_dokumentart(
        self,
        dokumentart: str,
        wahlperiode: Optional[str] = None,
        limit: Optional[int] = None,
        fetch_full_text: bool = True,
    ) -> dict[str, Any]:
        """
        Convenience method to collect Drucksachen of a specific document type.

        Args:
            dokumentart: Document type (e.g., "Gesetzentwurf", "Antrag")
            wahlperiode: Optional legislative period to filter by
            limit: Maximum number of Drucksachen to collect
            fetch_full_text: Whether to fetch full text content

        Returns:
            Collection statistics dictionary
        """
        logger.info(
            "Collecting Drucksachen by Dokumentart",
            dokumentart=dokumentart,
            wahlperiode=wahlperiode,
            limit=limit,
            fetch_full_text=fetch_full_text,
        )

        return await self.collect_with_filters(
            dokumentart=dokumentart,
            wahlperiode=wahlperiode,
            limit=limit,
            fetch_full_text=fetch_full_text,
        )

    async def collect_recent(
        self,
        days_back: int = 30,
        wahlperiode: Optional[str] = None,
        limit: Optional[int] = None,
        fetch_full_text: bool = True,
    ) -> dict[str, Any]:
        """
        Convenience method to collect recent Drucksachen.

        Args:
            days_back: Number of days to look back from today
            wahlperiode: Optional legislative period to filter by
            limit: Maximum number of Drucksachen to collect
            fetch_full_text: Whether to fetch full text content

        Returns:
            Collection statistics dictionary
        """
        from datetime import datetime, timedelta

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        logger.info(
            "Collecting recent Drucksachen",
            days_back=days_back,
            date_range=(start_date.date(), end_date.date()),
            wahlperiode=wahlperiode,
            limit=limit,
            fetch_full_text=fetch_full_text,
        )

        return await self.collect_with_filters(
            datum_von=start_date.strftime("%Y-%m-%d"),
            datum_bis=end_date.strftime("%Y-%m-%d"),
            wahlperiode=wahlperiode,
            limit=limit,
            fetch_full_text=fetch_full_text,
        )

    async def collect_for_vorgang(
        self, vorgang_id: str, fetch_full_text: bool = True
    ) -> dict[str, Any]:
        """
        Convenience method to collect all Drucksachen related to a specific Vorgang.

        Args:
            vorgang_id: ID of the Vorgang to collect Drucksachen for
            fetch_full_text: Whether to fetch full text content

        Returns:
            Collection statistics dictionary
        """
        logger.info(
            "Collecting Drucksachen for Vorgang",
            vorgang_id=vorgang_id,
            fetch_full_text=fetch_full_text,
        )

        # Fetch the Vorgang to get its Drucksache references
        try:
            vorgang_response = await self.api_client.get_by_id("vorgang", vorgang_id)
            wichtige_drucksachen = vorgang_response.get("wichtige_drucksachen", [])

            if not wichtige_drucksachen:
                logger.warning("No Drucksachen found for Vorgang", vorgang_id=vorgang_id)
                return self._create_statistics(
                    entities_created=0, edges_created=0, duration=0.0, items_collected=0, errors=[]
                )

            # Fetch each Drucksache by ID
            drucksachen = []
            errors = []

            for drucksache_nummer in wichtige_drucksachen:
                try:
                    drucksache_response = await self.api_client.get(
                        "drucksache", params={"f.drucksachenummer": drucksache_nummer}
                    )

                    documents = drucksache_response.get("documents", [])
                    if documents:
                        drucksachen.extend(documents)

                except Exception as e:
                    error_msg = f"Failed to fetch Drucksache {drucksache_nummer}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            # Process collected Drucksachen
            if drucksachen:
                return await self.collect_and_transform(
                    {
                        "drucksachen": drucksachen,
                        "fetch_full_text": fetch_full_text,
                        "vorgang_id": vorgang_id,
                    }
                )
            else:
                return self._create_statistics(
                    entities_created=0,
                    edges_created=0,
                    duration=0.0,
                    items_collected=0,
                    errors=errors,
                )

        except Exception as e:
            error_msg = f"Failed to collect Drucksachen for Vorgang {vorgang_id}: {str(e)}"
            logger.error(error_msg, error=str(e))

            return self._create_statistics(
                entities_created=0,
                edges_created=0,
                duration=0.0,
                items_collected=0,
                errors=[error_msg],
            )
