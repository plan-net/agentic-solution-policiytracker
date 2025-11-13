"""
Vorgangsposition Collector for German Bundestag procedural data.

Collects detailed procedural steps/positions within legislative processes from the
Bundestag DIP API. Handles large dataset (604k+ records) with batch processing.
"""

import time
from typing import Any, Dict, List, Optional

import structlog

from src.flows.bundestag_ingestion.collectors.base_collector import BaseCollector

logger = structlog.get_logger()


class VorgangspositionCollector(BaseCollector):
    """
    Collector for Vorgangsposition entities.

    Vorgangspositionen track individual stages and actions within a Vorgang,
    such as committee referrals, readings, amendments, and votes.

    This collector implements batch processing to handle the large dataset
    efficiently (604k+ records).

    Attributes:
        endpoint: "vorgangsposition" - DIP API endpoint
        entity_type: "Vorgangsposition" - Schema entity type
        batch_size: Number of items to process in each batch (default: 100)
    """

    @property
    def endpoint(self) -> str:
        """API endpoint for Vorgangsposition data."""
        return "vorgangsposition"

    @property
    def entity_type(self) -> str:
        """Entity type for Vorgangsposition."""
        return "Vorgangsposition"

    def __init__(
        self,
        api_client,
        entity_builder: Optional[Any] = None,
        edge_builder: Optional[Any] = None,
        batch_size: int = 100
    ):
        """
        Initialize the Vorgangsposition collector.

        Args:
            api_client: BundestagAPIClient instance for API requests
            entity_builder: Builder for creating Vorgangsposition entities
            edge_builder: Builder for creating edges (PART_OF_VORGANG)
            batch_size: Number of items to process in each batch
        """
        super().__init__(api_client, entity_builder, edge_builder)
        self.batch_size = batch_size

        logger.info(
            "Initialized VorgangspositionCollector",
            batch_size=self.batch_size
        )

    async def collect_and_transform(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect Vorgangsposition data and transform into entities and edges.

        Implements batch processing for efficient handling of large datasets.
        Can filter by related vorgang_id if provided in inputs.

        Args:
            inputs: Collection parameters with optional keys:
                - vorgang_id: Filter by parent Vorgang ID
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
                "batches_processed": int,
                "errors": List[str]
            }
        """
        start_time = time.time()
        errors = []
        entities_created = 0
        edges_created = 0
        batches_processed = 0

        try:
            # Parse inputs
            filters = inputs.get("filters", {})
            limit = inputs.get("limit")
            vorgang_id = inputs.get("vorgang_id")

            # Add vorgang_id filter if provided
            if vorgang_id:
                filters["f.vorgang_id"] = vorgang_id
                logger.info(
                    "Filtering by vorgang_id",
                    vorgang_id=vorgang_id
                )

            logger.info(
                "Starting Vorgangsposition collection",
                filters=filters,
                limit=limit,
                batch_size=self.batch_size
            )

            # Fetch data with pagination
            items, fetch_duration = await self._collect_with_timing(filters, limit)

            logger.info(
                "Completed data collection",
                items_collected=len(items),
                fetch_duration=fetch_duration
            )

            # Process in batches for large datasets
            total_items = len(items)
            for batch_start in range(0, total_items, self.batch_size):
                batch_end = min(batch_start + self.batch_size, total_items)
                batch = items[batch_start:batch_end]
                batches_processed += 1

                logger.info(
                    "Processing batch",
                    batch_number=batches_processed,
                    batch_start=batch_start,
                    batch_end=batch_end,
                    total_items=total_items
                )

                try:
                    # Transform batch to entities
                    batch_entities = await self._transform_to_entities(batch)
                    entities_created += len(batch_entities)

                    # Transform batch to edges
                    batch_edges = await self._transform_to_edges(batch, batch_entities)
                    edges_created += len(batch_edges)

                    logger.info(
                        "Batch processed successfully",
                        batch_number=batches_processed,
                        entities_in_batch=len(batch_entities),
                        edges_in_batch=len(batch_edges)
                    )

                except Exception as e:
                    error_msg = f"Error processing batch {batches_processed}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    # Continue with next batch

            duration = self._measure_duration(start_time)

            stats = self._create_statistics(
                entities_created=entities_created,
                edges_created=edges_created,
                duration=duration,
                items_collected=len(items),
                errors=errors
            )

            # Add batch processing info
            stats["batches_processed"] = batches_processed

            logger.info(
                "Vorgangsposition collection complete",
                **stats
            )

            return stats

        except Exception as e:
            error_msg = f"Fatal error in Vorgangsposition collection: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

            duration = self._measure_duration(start_time)
            return self._create_statistics(
                entities_created=entities_created,
                edges_created=edges_created,
                duration=duration,
                items_collected=0,
                errors=errors
            )

    async def collect_by_vorgang(
        self,
        vorgang_id: str,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Collect all Vorgangspositionen for a specific Vorgang.

        Convenience method for collecting positions related to a single procedure.

        Args:
            vorgang_id: The Vorgang ID to collect positions for
            limit: Maximum number of positions to collect

        Returns:
            Collection statistics dictionary
        """
        logger.info(
            "Collecting Vorgangspositionen by Vorgang",
            vorgang_id=vorgang_id,
            limit=limit
        )

        inputs = {
            "vorgang_id": vorgang_id,
            "limit": limit
        }

        return await self.collect_and_transform(inputs)

    async def collect_by_wahlperiode(
        self,
        wahlperiode: str,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Collect all Vorgangspositionen for a legislative period.

        Args:
            wahlperiode: Electoral period number (e.g., "20" for 20th period)
            limit: Maximum number of positions to collect

        Returns:
            Collection statistics dictionary
        """
        logger.info(
            "Collecting Vorgangspositionen by Wahlperiode",
            wahlperiode=wahlperiode,
            limit=limit
        )

        inputs = {
            "filters": {"f.wahlperiode": wahlperiode},
            "limit": limit
        }

        return await self.collect_and_transform(inputs)

    async def get_collection_statistics(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get statistics about available Vorgangspositionen without collecting them.

        Useful for understanding dataset size before collection.

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

        logger.info(
            "Getting Vorgangsposition statistics",
            filters=filters
        )

        try:
            # Create pagination helper
            pagination_helper = PaginationHelper(
                api_client=self.api_client,
                max_items=None
            )

            # Get count without retrieving items
            total_count = await pagination_helper.count_items(self.endpoint, filters)

            stats = {
                "total_count": total_count,
                "endpoint": self.endpoint,
                "filters_applied": filters,
                "estimated_batches": (total_count + self.batch_size - 1) // self.batch_size
            }

            logger.info(
                "Retrieved Vorgangsposition statistics",
                **stats
            )

            return stats

        except Exception as e:
            logger.error(
                "Error getting Vorgangsposition statistics",
                error=str(e)
            )
            return {
                "total_count": 0,
                "endpoint": self.endpoint,
                "filters_applied": filters,
                "error": str(e)
            }
