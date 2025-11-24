"""
Vorgang Collector for German Bundestag legislative procedures.

Collects Vorgang (legislative procedure) data from the Bundestag DIP API,
transforms it into knowledge graph entities, and creates relationships.
"""

import time
from typing import Any, Optional

import structlog

from src.flows.bundestag_ingestion.collectors.base_collector import BaseCollector

logger = structlog.get_logger()


class VorgangCollector(BaseCollector):
    """
    Collector for Vorgang (legislative procedure) entities.

    A Vorgang represents the complete lifecycle of a legislative initiative in the
    German Bundestag, from proposal through committee work, debates, votes, and
    final outcome. This collector fetches Vorgänge from the DIP API and transforms
    them into knowledge graph entities with appropriate relationships.

    Attributes:
        endpoint: API endpoint ("vorgang")
        entity_type: Entity type ("Vorgang")
        api_client: BundestagAPIClient instance
        entity_builder: Builder for creating Vorgang entities
        edge_builder: Builder for creating relationship edges
    """

    @property
    def endpoint(self) -> str:
        """API endpoint for Vorgang collection."""
        return "vorgang"

    @property
    def entity_type(self) -> str:
        """Entity type produced by this collector."""
        return "Vorgang"

    async def collect_and_transform(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Collect Vorgang data from API and transform into entities and edges.

        Process:
        1. Parse input filters (wahlperiode, sachgebiet, datum_von/bis, limit)
        2. Fetch Vorgänge from /api/v1/vorgang with pagination
        3. For each Vorgang, create entity using entity_builder
        4. Create edge to Wahlperiode using edge_builder
        5. Return collection statistics

        Args:
            inputs: Dictionary containing:
                - filters: Dict of filter parameters (optional)
                - wahlperiode: Legislative period (optional)
                - sachgebiet: Subject area (optional)
                - datum_von: Start date ISO 8601 (optional)
                - datum_bis: End date ISO 8601 (optional)
                - limit: Maximum number of items (optional)

        Returns:
            Dictionary with collection statistics:
            {
                "entities_created": int,
                "edges_created": int,
                "duration": float,
                "items_collected": int,
                "errors": List[str]
            }
        """
        start_time = time.time()
        errors: list[str] = []

        logger.info("Starting Vorgang collection", inputs=inputs)

        try:
            # Extract filter parameters
            filters = self._extract_filters(inputs)
            limit = inputs.get("limit")

            logger.info("Collecting Vorgänge with filters", filters=filters, limit=limit)

            # Fetch Vorgänge with pagination
            vorgaenge, fetch_duration = await self._collect_with_timing(filters, limit)

            logger.info("Fetched Vorgänge", count=len(vorgaenge), duration=fetch_duration)

            # Transform to entities and edges
            entities_created = 0
            edges_created = 0

            if self.entity_builder and self.edge_builder:
                # Transform to entities
                entities = await self._transform_to_entities(vorgaenge)
                entities_created = len(entities)

                # Transform to edges
                edges = await self._transform_to_edges(vorgaenge, entities)
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
            return self._create_statistics(
                entities_created=entities_created,
                edges_created=edges_created,
                duration=duration,
                items_collected=len(vorgaenge),
                errors=errors,
            )

        except Exception as e:
            error_msg = f"Vorgang collection failed: {str(e)}"
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
            sachgebiet=inputs.get("sachgebiet"),
            limit=inputs.get("limit"),
        )

        logger.debug("Built filters from inputs", filters=filters)

        return filters

    async def _create_wahlperiode_edges(
        self, vorgang: dict[str, Any], vorgang_entity: Any
    ) -> list[Any]:
        """
        Create edges linking Vorgang to its Wahlperiode.

        Args:
            vorgang: Raw Vorgang data from API
            vorgang_entity: Created Vorgang entity

        Returns:
            List of edge objects
        """
        edges: list[Any] = []

        if not self.edge_builder:
            return edges

        # Extract Wahlperiode from Vorgang
        wahlperiode = vorgang.get("wahlperiode")

        if wahlperiode:
            try:
                # Create IN_WAHLPERIODE edge
                edge = await self.edge_builder.create_in_wahlperiode_edge(
                    vorgang_entity=vorgang_entity,
                    wahlperiode_nummer=wahlperiode,
                    active_from=vorgang.get("datum"),
                    active_until=vorgang.get("abgeschlossen_datum"),
                )

                if edge:
                    edges.append(edge)
                    logger.debug(
                        "Created Wahlperiode edge",
                        vorgang_id=vorgang.get("id"),
                        wahlperiode=wahlperiode,
                    )

            except Exception as e:
                logger.warning(
                    "Failed to create Wahlperiode edge", vorgang_id=vorgang.get("id"), error=str(e)
                )

        return edges

    async def collect_by_wahlperiode(
        self, wahlperiode: str, limit: Optional[int] = None
    ) -> dict[str, Any]:
        """
        Convenience method to collect Vorgänge for a specific legislative period.

        Args:
            wahlperiode: Legislative period number (e.g., "20")
            limit: Maximum number of Vorgänge to collect

        Returns:
            Collection statistics dictionary
        """
        logger.info("Collecting Vorgänge for Wahlperiode", wahlperiode=wahlperiode, limit=limit)

        return await self.collect_with_filters(wahlperiode=wahlperiode, limit=limit)

    async def collect_by_sachgebiet(
        self, sachgebiet: str, wahlperiode: Optional[str] = None, limit: Optional[int] = None
    ) -> dict[str, Any]:
        """
        Convenience method to collect Vorgänge for a specific subject area.

        Args:
            sachgebiet: Subject area (e.g., "Digitalisierung")
            wahlperiode: Optional legislative period to filter by
            limit: Maximum number of Vorgänge to collect

        Returns:
            Collection statistics dictionary
        """
        logger.info(
            "Collecting Vorgänge for Sachgebiet",
            sachgebiet=sachgebiet,
            wahlperiode=wahlperiode,
            limit=limit,
        )

        return await self.collect_with_filters(
            sachgebiet=sachgebiet, wahlperiode=wahlperiode, limit=limit
        )

    async def collect_recent(
        self, days_back: int = 30, wahlperiode: Optional[str] = None, limit: Optional[int] = None
    ) -> dict[str, Any]:
        """
        Convenience method to collect recent Vorgänge.

        Args:
            days_back: Number of days to look back from today
            wahlperiode: Optional legislative period to filter by
            limit: Maximum number of Vorgänge to collect

        Returns:
            Collection statistics dictionary
        """
        from datetime import datetime, timedelta

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        logger.info(
            "Collecting recent Vorgänge",
            days_back=days_back,
            date_range=(start_date.date(), end_date.date()),
            wahlperiode=wahlperiode,
            limit=limit,
        )

        return await self.collect_with_filters(
            datum_von=start_date.strftime("%Y-%m-%d"),
            datum_bis=end_date.strftime("%Y-%m-%d"),
            wahlperiode=wahlperiode,
            limit=limit,
        )
