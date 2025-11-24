"""
Aktivitaet Collector for German Bundestag parliamentary activities.

Collects specific parliamentary activities and actions from the Bundestag DIP API,
such as committee meetings, hearings, expert testimonies, and procedural motions.
"""

import time
from datetime import datetime
from typing import Any, Optional

import structlog

from src.flows.bundestag_ingestion.collectors.base_collector import BaseCollector

logger = structlog.get_logger()


class AktivitaetCollector(BaseCollector):
    """
    Collector for Aktivitaet entities.

    Aktivitäten represent discrete actions taken in the parliamentary process,
    such as committee meetings, hearings, expert testimonies, or procedural motions.

    Links activities to related Vorgänge and Drucksachen.

    Attributes:
        endpoint: "aktivitaet" - DIP API endpoint
        entity_type: "Aktivitaet" - Schema entity type
    """

    @property
    def endpoint(self) -> str:
        """API endpoint for Aktivitaet data."""
        return "aktivitaet"

    @property
    def entity_type(self) -> str:
        """Entity type for Aktivitaet."""
        return "Aktivitaet"

    async def collect_and_transform(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Collect Aktivitaet data and transform into entities and edges.

        Creates Aktivitaet entities and links them to related Vorgänge
        (ACTIVITY_IN_VORGANG) and Drucksachen (if applicable).

        Args:
            inputs: Collection parameters with optional keys:
                - aktivitaetsart: Filter by activity type
                - datum_von: Start date filter (ISO 8601)
                - datum_bis: End date filter (ISO 8601)
                - vorgang_id: Filter by related Vorgang ID
                - wahlperiode: Filter by legislative period
                - limit: Maximum number of items to collect
                - filters: Additional filter parameters

        Returns:
            Statistics dictionary with collection results:
            {
                "entities_created": int,
                "edges_created": int,
                "duration": float,
                "items_collected": int,
                "activities_with_vorgang": int,
                "activities_with_drucksache": int,
                "errors": List[str]
            }
        """
        start_time = time.time()
        errors = []
        entities_created = 0
        edges_created = 0
        activities_with_vorgang = 0
        activities_with_drucksache = 0

        try:
            # Parse inputs
            filters = inputs.get("filters", {})
            limit = inputs.get("limit")

            # Add specific filters from inputs
            if "aktivitaetsart" in inputs:
                filters["f.aktivitaetsart"] = inputs["aktivitaetsart"]
                logger.info("Filtering by aktivitaetsart", aktivitaetsart=inputs["aktivitaetsart"])

            if "datum_von" in inputs:
                filters["f.datum"] = f"gte:{inputs['datum_von']}"
                logger.info("Filtering by datum_von", datum_von=inputs["datum_von"])

            if "datum_bis" in inputs:
                # Combine with datum_von if present
                if "f.datum" in filters:
                    filters["f.datum"] = f"{filters['f.datum']}|lte:{inputs['datum_bis']}"
                else:
                    filters["f.datum"] = f"lte:{inputs['datum_bis']}"
                logger.info("Filtering by datum_bis", datum_bis=inputs["datum_bis"])

            if "vorgang_id" in inputs:
                filters["f.vorgang_id"] = inputs["vorgang_id"]
                logger.info("Filtering by vorgang_id", vorgang_id=inputs["vorgang_id"])

            if "wahlperiode" in inputs:
                filters["f.wahlperiode"] = inputs["wahlperiode"]
                logger.info("Filtering by wahlperiode", wahlperiode=inputs["wahlperiode"])

            logger.info("Starting Aktivitaet collection", filters=filters, limit=limit)

            # Fetch data with pagination
            items, fetch_duration = await self._collect_with_timing(filters, limit)

            logger.info(
                "Completed data collection",
                items_collected=len(items),
                fetch_duration=fetch_duration,
            )

            # Transform to entities
            entities = await self._transform_to_entities(items)
            entities_created = len(entities)

            # Transform to edges and count relationships
            edges = await self._transform_to_edges(items, entities)
            edges_created = len(edges)

            # Count relationship types for statistics
            for item in items:
                if item.get("vorgang_id"):
                    activities_with_vorgang += 1
                if item.get("drucksache_nummer"):
                    activities_with_drucksache += 1

            duration = self._measure_duration(start_time)

            stats = self._create_statistics(
                entities_created=entities_created,
                edges_created=edges_created,
                duration=duration,
                items_collected=len(items),
                errors=errors,
            )

            # Add relationship statistics
            stats["activities_with_vorgang"] = activities_with_vorgang
            stats["activities_with_drucksache"] = activities_with_drucksache

            logger.info("Aktivitaet collection complete", **stats)

            return stats

        except Exception as e:
            error_msg = f"Fatal error in Aktivitaet collection: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

            duration = self._measure_duration(start_time)
            return self._create_statistics(
                entities_created=entities_created,
                edges_created=edges_created,
                duration=duration,
                items_collected=0,
                errors=errors,
            )

    async def collect_by_activity_type(
        self, aktivitaetsart: str, limit: Optional[int] = None
    ) -> dict[str, Any]:
        """
        Collect activities filtered by activity type.

        Args:
            aktivitaetsart: Activity type to filter by
            limit: Maximum number of activities to collect

        Returns:
            Collection statistics dictionary
        """
        logger.info("Collecting Aktivitaeten by type", aktivitaetsart=aktivitaetsart, limit=limit)

        inputs = {"aktivitaetsart": aktivitaetsart, "limit": limit}

        return await self.collect_and_transform(inputs)

    async def collect_by_date_range(
        self, datum_von: str, datum_bis: str, limit: Optional[int] = None
    ) -> dict[str, Any]:
        """
        Collect activities within a date range.

        Args:
            datum_von: Start date (ISO 8601 format, e.g., "2024-01-01")
            datum_bis: End date (ISO 8601 format)
            limit: Maximum number of activities to collect

        Returns:
            Collection statistics dictionary
        """
        logger.info(
            "Collecting Aktivitaeten by date range",
            datum_von=datum_von,
            datum_bis=datum_bis,
            limit=limit,
        )

        # Validate date formats
        try:
            datetime.fromisoformat(datum_von)
            datetime.fromisoformat(datum_bis)
        except ValueError as e:
            error_msg = f"Invalid date format: {str(e)}"
            logger.error(error_msg)
            return self._create_statistics(
                entities_created=0,
                edges_created=0,
                duration=0.0,
                items_collected=0,
                errors=[error_msg],
            )

        inputs = {"datum_von": datum_von, "datum_bis": datum_bis, "limit": limit}

        return await self.collect_and_transform(inputs)

    async def collect_by_vorgang(
        self, vorgang_id: str, limit: Optional[int] = None
    ) -> dict[str, Any]:
        """
        Collect all activities related to a specific Vorgang.

        Args:
            vorgang_id: The Vorgang ID to collect activities for
            limit: Maximum number of activities to collect

        Returns:
            Collection statistics dictionary
        """
        logger.info("Collecting Aktivitaeten by Vorgang", vorgang_id=vorgang_id, limit=limit)

        inputs = {"vorgang_id": vorgang_id, "limit": limit}

        return await self.collect_and_transform(inputs)

    async def collect_recent_activities(
        self, days: int = 7, aktivitaetsart: Optional[str] = None, limit: Optional[int] = None
    ) -> dict[str, Any]:
        """
        Collect recent activities from the last N days.

        Convenience method for getting recent parliamentary activities.

        Args:
            days: Number of days to look back (default: 7)
            aktivitaetsart: Optional filter by activity type
            limit: Maximum number of activities to collect

        Returns:
            Collection statistics dictionary
        """
        from datetime import timedelta

        datum_bis = datetime.now().date().isoformat()
        datum_von = (datetime.now() - timedelta(days=days)).date().isoformat()

        logger.info(
            "Collecting recent Aktivitaeten",
            days=days,
            datum_von=datum_von,
            datum_bis=datum_bis,
            aktivitaetsart=aktivitaetsart,
            limit=limit,
        )

        inputs = {"datum_von": datum_von, "datum_bis": datum_bis, "limit": limit}

        if aktivitaetsart:
            inputs["aktivitaetsart"] = aktivitaetsart

        return await self.collect_and_transform(inputs)

    async def get_activity_types(self) -> list[str]:
        """
        Get a list of available activity types from the API.

        This can help understand what aktivitaetsart values are available.

        Returns:
            List of activity type strings
        """
        try:
            logger.info("Fetching available activity types")

            # Fetch a sample of activities to extract types
            items = await self.fetch_with_pagination(filters={}, limit=100)

            # Extract unique activity types
            activity_types = set()
            for item in items:
                if "aktivitaetsart" in item:
                    activity_types.add(item["aktivitaetsart"])

            activity_types_list = sorted(list(activity_types))

            logger.info(
                "Retrieved activity types",
                count=len(activity_types_list),
                types=activity_types_list,
            )

            return activity_types_list

        except Exception as e:
            logger.error("Error fetching activity types", error=str(e))
            return []

    async def get_collection_statistics(
        self, filters: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Get statistics about available activities without collecting them.

        Args:
            filters: Optional filter parameters

        Returns:
            Dictionary with statistics:
            {
                "total_count": int,
                "endpoint": str,
                "filters_applied": dict
            }
        """
        from src.flows.bundestag_ingestion.utils.pagination import PaginationHelper

        filters = filters or {}

        logger.info("Getting Aktivitaet statistics", filters=filters)

        try:
            # Create pagination helper
            pagination_helper = PaginationHelper(api_client=self.api_client, max_items=None)

            # Get count without retrieving items
            total_count = await pagination_helper.count_items(self.endpoint, filters)

            stats = {
                "total_count": total_count,
                "endpoint": self.endpoint,
                "filters_applied": filters,
            }

            logger.info("Retrieved Aktivitaet statistics", **stats)

            return stats

        except Exception as e:
            logger.error("Error getting Aktivitaet statistics", error=str(e))
            return {
                "total_count": 0,
                "endpoint": self.endpoint,
                "filters_applied": filters,
                "error": str(e),
            }
