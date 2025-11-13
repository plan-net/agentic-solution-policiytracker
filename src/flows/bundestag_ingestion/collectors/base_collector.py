"""
Base collector for Bundestag data ingestion.

Abstract base class for all Bundestag data collectors with common functionality.
"""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger()


class BaseCollector(ABC):
    """
    Abstract base class for Bundestag data collectors.

    Provides common infrastructure for collecting data from the Bundestag DIP API,
    transforming it into knowledge graph entities and edges, and tracking statistics.

    Attributes:
        endpoint: API endpoint for this collector (e.g., "vorgang", "drucksache")
        entity_type: Type of entity this collector produces (e.g., "Vorgang", "Drucksache")
        api_client: BundestagAPIClient instance for making API requests
        entity_builder: Builder for creating entity objects from API data
        edge_builder: Builder for creating edge objects from API data
    """

    def __init__(
        self,
        api_client,
        entity_builder: Optional[Any] = None,
        edge_builder: Optional[Any] = None,
        neo4j_driver: Optional[Any] = None,
        neo4j_database: str = "neo4j"
    ):
        """
        Initialize the base collector.

        Args:
            api_client: BundestagAPIClient instance for API requests
            entity_builder: Builder for creating entity objects (optional)
            edge_builder: Builder for creating edge objects (optional)
            neo4j_driver: Neo4j driver instance for database operations (optional)
            neo4j_database: Neo4j database name (default: "neo4j")
        """
        self.api_client = api_client
        self.entity_builder = entity_builder
        self.edge_builder = edge_builder
        self.neo4j_driver = neo4j_driver
        self.neo4j_database = neo4j_database

        logger.info(
            "Initialized collector",
            collector_type=self.__class__.__name__,
            endpoint=self.endpoint,
            entity_type=self.entity_type,
            has_neo4j=neo4j_driver is not None
        )

    @property
    @abstractmethod
    def endpoint(self) -> str:
        """
        API endpoint for this collector.

        Returns:
            Endpoint path (e.g., "vorgang", "drucksache")
        """
        pass

    @property
    @abstractmethod
    def entity_type(self) -> str:
        """
        Entity type produced by this collector.

        Returns:
            Entity type name (e.g., "Vorgang", "Drucksache")
        """
        pass

    @abstractmethod
    async def collect_and_transform(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect data from API and transform into entities and edges.

        This is the main method that subclasses must implement. It should:
        1. Parse input parameters
        2. Fetch data from the API
        3. Transform data into entities and edges
        4. Return statistics about the collection

        Args:
            inputs: Dictionary containing collection parameters

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
        pass

    async def save_to_neo4j(
        self,
        entities: List[Any],
        edges: List[Any]
    ) -> Dict[str, int]:
        """
        Save entities and edges to Neo4j database.

        Args:
            entities: List of entity objects (Pydantic models)
            edges: List of edge/relationship objects

        Returns:
            Dictionary with counts: {"entities_saved": int, "edges_saved": int}
        """
        if not self.neo4j_driver:
            logger.warning("No Neo4j driver configured, skipping persistence")
            return {"entities_saved": 0, "edges_saved": 0}

        entities_saved = 0
        edges_saved = 0

        try:
            with self.neo4j_driver.session(database=self.neo4j_database) as session:
                # Save entities
                for entity in entities:
                    try:
                        # Convert Pydantic model to dict (Pydantic v2 uses model_dump)
                        if hasattr(entity, 'model_dump'):
                            entity_dict = entity.model_dump()
                        elif hasattr(entity, 'dict'):
                            entity_dict = entity.dict()
                        else:
                            entity_dict = entity

                        # Get entity type from class name
                        entity_type = entity.__class__.__name__

                        # Find unique identifier field (try common patterns)
                        unique_id = (
                            entity_dict.get('person_id') or
                            entity_dict.get('vorgang_id') or
                            entity_dict.get('drucksache_id') or
                            entity_dict.get('id') or
                            entity_dict.get('name')
                        )

                        if not unique_id:
                            logger.warning(f"No unique identifier found for {entity_type}, skipping")
                            continue

                        # Determine the ID field name for this entity type
                        if 'person_id' in entity_dict:
                            id_field = 'person_id'
                        elif 'vorgang_id' in entity_dict:
                            id_field = 'vorgang_id'
                        elif 'drucksache_id' in entity_dict:
                            id_field = 'drucksache_id'
                        elif 'id' in entity_dict:
                            id_field = 'id'
                        else:
                            id_field = 'name'

                        # Create MERGE query to avoid duplicates
                        query = f"""
                        MERGE (n:{entity_type} {{{id_field}: $unique_id}})
                        SET n += $properties
                        RETURN n
                        """

                        result = session.run(query, unique_id=unique_id, properties=entity_dict)
                        if result.single():
                            entities_saved += 1

                    except Exception as e:
                        logger.error(f"Failed to save entity: {e}", entity_type=entity_type, entity_dict=entity_dict)

                # Save edges
                for edge in edges:
                    try:
                        # Extract edge information
                        if hasattr(edge, 'model_dump'):
                            edge_dict = edge.model_dump()
                        elif hasattr(edge, 'dict'):
                            edge_dict = edge.dict()
                        else:
                            edge_dict = edge

                        rel_type = edge_dict.get('type', 'RELATED_TO')
                        from_id = edge_dict.get('from_id')
                        to_id = edge_dict.get('to_id')
                        properties = {k: v for k, v in edge_dict.items() if k not in ['type', 'from_id', 'to_id'] and v is not None}

                        if not from_id or not to_id:
                            logger.warning(f"Edge missing from_id or to_id, skipping: {edge_dict}")
                            continue

                        # Create relationship query - match nodes by any ID field
                        query = f"""
                        MATCH (a), (b)
                        WHERE (a.person_id = $from_id OR a.vorgang_id = $from_id OR a.drucksache_id = $from_id OR a.id = $from_id OR a.name = $from_id)
                          AND (b.person_id = $to_id OR b.vorgang_id = $to_id OR b.drucksache_id = $to_id OR b.id = $to_id OR b.name = $to_id)
                        MERGE (a)-[r:{rel_type}]->(b)
                        SET r += $properties
                        RETURN r
                        """

                        result = session.run(query, from_id=from_id, to_id=to_id, properties=properties)
                        if result.single():
                            edges_saved += 1

                    except Exception as e:
                        logger.error(f"Failed to save edge: {e}", edge_type=rel_type, edge_dict=edge_dict)

            logger.info(
                "Saved to Neo4j",
                entities_saved=entities_saved,
                edges_saved=edges_saved
            )

            return {"entities_saved": entities_saved, "edges_saved": edges_saved}

        except Exception as e:
            logger.error(f"Neo4j save operation failed: {e}")
            return {"entities_saved": entities_saved, "edges_saved": edges_saved}

    async def fetch_with_pagination(
        self,
        filters: Dict[str, Any],
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch data with pagination support.

        Common method for fetching data from the API with pagination.
        Handles the pagination logic and returns all collected items.

        Args:
            filters: Filter parameters for the API request
            limit: Maximum number of items to fetch (None for unlimited)

        Returns:
            List of collected items from the API
        """
        from src.flows.bundestag_ingestion.utils.pagination import PaginationHelper

        # Create pagination helper
        pagination_helper = PaginationHelper(
            api_client=self.api_client,
            max_items=limit
        )

        logger.info(
            "Starting paginated fetch",
            endpoint=self.endpoint,
            filters=filters,
            limit=limit
        )

        # Collect all items
        items = []
        async for item in pagination_helper.paginate(self.endpoint, filters):
            items.append(item)

        logger.info(
            "Completed paginated fetch",
            endpoint=self.endpoint,
            items_collected=len(items)
        )

        return items

    def _create_statistics(
        self,
        entities_created: int,
        edges_created: int,
        duration: float,
        items_collected: int = 0,
        errors: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create standardized statistics dictionary.

        Args:
            entities_created: Number of entities created
            edges_created: Number of edges created
            duration: Total processing duration in seconds
            items_collected: Number of raw items collected from API
            errors: List of error messages (if any)

        Returns:
            Statistics dictionary
        """
        stats = {
            "entities_created": entities_created,
            "edges_created": edges_created,
            "duration": duration,
            "items_collected": items_collected,
            "collector_type": self.__class__.__name__,
            "endpoint": self.endpoint,
            "entity_type": self.entity_type,
            "errors": errors or []
        }

        logger.info(
            "Collection statistics",
            **stats
        )

        return stats

    async def _transform_to_entities(
        self,
        items: List[Dict[str, Any]]
    ) -> List[Any]:
        """
        Transform API items into entity objects.

        Args:
            items: List of raw items from the API

        Returns:
            List of entity objects
        """
        if not self.entity_builder:
            logger.warning("No entity_builder configured, skipping entity transformation")
            return []

        entities = []

        for item in items:
            try:
                entity = await self.entity_builder.build(item)
                entities.append(entity)
            except Exception as e:
                logger.error(
                    "Failed to transform item to entity",
                    item_id=item.get("id"),
                    error=str(e)
                )
                continue

        logger.info(
            "Transformed items to entities",
            input_count=len(items),
            output_count=len(entities)
        )

        return entities

    async def _transform_to_edges(
        self,
        items: List[Dict[str, Any]],
        entities: List[Any]
    ) -> List[Any]:
        """
        Transform API items into edge objects.

        Args:
            items: List of raw items from the API
            entities: List of entity objects (for relationship creation)

        Returns:
            List of edge objects
        """
        if not self.edge_builder:
            logger.warning("No edge_builder configured, skipping edge transformation")
            return []

        edges = []

        for item, entity in zip(items, entities):
            try:
                item_edges = await self.edge_builder.build(item, entity)
                edges.extend(item_edges)
            except Exception as e:
                logger.error(
                    "Failed to transform item to edges",
                    item_id=item.get("id"),
                    error=str(e)
                )
                continue

        logger.info(
            "Transformed items to edges",
            input_count=len(items),
            output_count=len(edges)
        )

        return edges

    async def collect_with_filters(
        self,
        wahlperiode: Optional[str] = None,
        datum_von: Optional[str] = None,
        datum_bis: Optional[str] = None,
        limit: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Collect data with common filter parameters.

        Convenience method that builds filters and calls collect_and_transform.

        Args:
            wahlperiode: Legislative period
            datum_von: Start date (ISO 8601)
            datum_bis: End date (ISO 8601)
            limit: Maximum number of items
            **kwargs: Additional filter parameters

        Returns:
            Collection statistics dictionary
        """
        from src.flows.bundestag_ingestion.utils.filters import FilterBuilder

        # Build filters
        filter_builder = FilterBuilder()
        filters = filter_builder.build_filters(
            wahlperiode=wahlperiode,
            datum_von=datum_von,
            datum_bis=datum_bis,
            limit=limit,
            **kwargs
        )

        # Prepare inputs
        inputs = {
            "filters": filters,
            "limit": limit
        }

        # Execute collection
        return await self.collect_and_transform(inputs)

    async def health_check(self) -> bool:
        """
        Check if the collector can successfully query the API.

        Returns:
            True if API is accessible, False otherwise
        """
        try:
            # Try fetching a single item
            from src.flows.bundestag_ingestion.utils.filters import FilterBuilder

            filter_builder = FilterBuilder()
            filters = filter_builder.build_filters(limit=1)

            items = await self.fetch_with_pagination(filters, limit=1)

            logger.info(
                "Collector health check passed",
                collector_type=self.__class__.__name__
            )
            return True

        except Exception as e:
            logger.error(
                "Collector health check failed",
                collector_type=self.__class__.__name__,
                error=str(e)
            )
            return False

    def _measure_duration(self, start_time: float) -> float:
        """
        Measure duration since start time.

        Args:
            start_time: Start time from time.time()

        Returns:
            Duration in seconds
        """
        duration = time.time() - start_time
        return round(duration, 2)

    async def _collect_with_timing(
        self,
        filters: Dict[str, Any],
        limit: Optional[int] = None
    ) -> tuple[List[Dict[str, Any]], float]:
        """
        Collect data with timing measurement.

        Args:
            filters: Filter parameters
            limit: Maximum number of items

        Returns:
            Tuple of (items, duration)
        """
        start_time = time.time()

        items = await self.fetch_with_pagination(filters, limit)

        duration = self._measure_duration(start_time)

        return items, duration
