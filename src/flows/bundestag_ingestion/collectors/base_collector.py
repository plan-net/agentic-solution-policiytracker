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
        # Debug logging to file (since stdout isn't captured)
        import os
        debug_file = "/tmp/plenarprotokoll_save_debug.log"
        with open(debug_file, "a") as f:
            f.write(f"\n=== save_to_neo4j CALLED at {time.time()} ===\n")
            f.write(f"Entities: {len(entities)}, Edges: {len(edges)}\n")
            f.write(f"Has driver: {self.neo4j_driver is not None}\n")
            if entities:
                f.write(f"First entity type: {type(entities[0]).__name__}\n")
                if hasattr(entities[0], 'model_dump'):
                    f.write(f"First entity: {entities[0].model_dump()}\n")

        logger.info(
            "save_to_neo4j called",
            entities_count=len(entities),
            edges_count=len(edges),
            has_driver=self.neo4j_driver is not None
        )

        if not self.neo4j_driver:
            print("=== NO NEO4J DRIVER - SKIPPING ===")
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
                        # Special handling for Plenarprotokoll (uses composite key)
                        if entity_type == 'Plenarprotokoll':
                            sitzungsnummer = entity_dict.get('sitzungsnummer')
                            wahlperiode = entity_dict.get('wahlperiode')

                            # Debug to file
                            with open("/tmp/plenarprotokoll_save_debug.log", "a") as f:
                                f.write(f"Processing Plenarprotokoll: sitzung={sitzungsnummer}, wp={wahlperiode}, herausgeber={entity_dict.get('herausgeber')}\n")

                            logger.info(
                                "Processing Plenarprotokoll entity",
                                sitzungsnummer=sitzungsnummer,
                                wahlperiode=wahlperiode,
                                entity_dict_keys=list(entity_dict.keys())
                            )

                            # Skip if sitzungsnummer is empty (can't create node without key)
                            if not sitzungsnummer or wahlperiode is None:
                                herausgeber = entity_dict.get('herausgeber', 'unknown')
                                with open("/tmp/plenarprotokoll_save_debug.log", "a") as f:
                                    f.write(f"⚠️  SKIPPED: Empty sitzungsnummer, herausgeber={herausgeber}, name={entity_dict.get('plenarprotokoll_name', 'unknown')}\n")
                                logger.warning(
                                    "Plenarprotokoll missing sitzungsnummer, skipping",
                                    sitzungsnummer=sitzungsnummer,
                                    wahlperiode=wahlperiode,
                                    herausgeber=herausgeber,
                                    name=entity_dict.get('plenarprotokoll_name')
                                )
                                continue

                            # Convert sitzungsnummer to int to match existing nodes in Neo4j
                            # (schema says str, but existing nodes use int)
                            # Handle format "20/214" by extracting the session number after the slash
                            try:
                                if '/' in str(sitzungsnummer):
                                    # Extract session number from "20/214" format
                                    sitzungsnummer_int = int(sitzungsnummer.split('/')[-1])
                                else:
                                    sitzungsnummer_int = int(sitzungsnummer)

                                with open("/tmp/plenarprotokoll_save_debug.log", "a") as f:
                                    f.write(f"Converted sitzungsnummer '{sitzungsnummer}' to int {sitzungsnummer_int}\n")

                            except (ValueError, TypeError) as e:
                                with open("/tmp/plenarprotokoll_save_debug.log", "a") as f:
                                    f.write(f"❌ Cannot convert sitzungsnummer '{sitzungsnummer}' to int: {e}\n")
                                logger.warning(
                                    "Cannot convert sitzungsnummer to int, skipping",
                                    sitzungsnummer=sitzungsnummer,
                                    error=str(e)
                                )
                                continue

                            # CRITICAL: Also convert sitzungsnummer in properties to int
                            # Otherwise SET n += $properties will overwrite it back to string!
                            entity_dict['sitzungsnummer'] = sitzungsnummer_int

                            # Use composite key for Plenarprotokoll
                            query = f"""
                            MERGE (n:{entity_type} {{sitzungsnummer: $sitzungsnummer, wahlperiode: $wahlperiode}})
                            SET n += $properties
                            RETURN n
                            """

                            logger.info(
                                "Executing Plenarprotokoll MERGE query",
                                sitzungsnummer=sitzungsnummer_int,
                                wahlperiode=wahlperiode
                            )

                            result = session.run(query, sitzungsnummer=sitzungsnummer_int, wahlperiode=wahlperiode, properties=entity_dict)
                            result_record = result.single()

                            with open("/tmp/plenarprotokoll_save_debug.log", "a") as f:
                                if result_record:
                                    entities_saved += 1
                                    f.write(f"✅ SAVED Plenarprotokoll sitzung={sitzungsnummer_int}, wp={wahlperiode}\n")
                                    logger.info(
                                        "Successfully saved Plenarprotokoll",
                                        sitzungsnummer=sitzungsnummer_int,
                                        wahlperiode=wahlperiode
                                    )
                                else:
                                    f.write(f"❌ MERGE RETURNED NOTHING for sitzung={sitzungsnummer_int}, wp={wahlperiode}\n")
                                    logger.warning(
                                        "Plenarprotokoll MERGE returned no result",
                                        sitzungsnummer=sitzungsnummer_int,
                                        wahlperiode=wahlperiode
                                    )
                            continue

                        # Standard handling for other entity types
                        unique_id = (
                            entity_dict.get('person_id') or
                            entity_dict.get('vorgang_id') or
                            entity_dict.get('drucksache_id') or
                            entity_dict.get('aktivitaet_id') or
                            entity_dict.get('id') or
                            entity_dict.get('name')
                        )

                        if not unique_id:
                            logger.warning(f"No unique identifier found for {entity_type}, skipping", entity_dict=entity_dict)
                            continue

                        # Determine the ID field name for this entity type
                        if 'person_id' in entity_dict:
                            id_field = 'person_id'
                        elif 'vorgang_id' in entity_dict:
                            id_field = 'vorgang_id'
                        elif 'drucksache_id' in entity_dict:
                            id_field = 'drucksache_id'
                        elif 'aktivitaet_id' in entity_dict:
                            id_field = 'aktivitaet_id'
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

                        # Special handling for Plenarprotokoll edges (composite key: sitzungsnummer_wahlperiode)
                        if '_' in str(from_id) and from_id.replace('_', '').replace('/', '').isdigit():
                            # Plenarprotokoll composite key format: "214_20" or "20/214_20"
                            parts = str(from_id).rsplit('_', 1)
                            if len(parts) == 2:
                                sitzung_raw = parts[0]
                                wahlperiode = parts[1]

                                # Extract session number from "20/214" format if needed
                                if '/' in sitzung_raw:
                                    sitzungsnummer = int(sitzung_raw.split('/')[-1])
                                else:
                                    sitzungsnummer = int(sitzung_raw)

                                query = f"""
                                MATCH (a:Plenarprotokoll), (b)
                                WHERE a.sitzungsnummer = $sitzungsnummer AND a.wahlperiode = $wahlperiode
                                  AND (b.person_id = $to_id OR b.vorgang_id = $to_id OR b.drucksache_id = $to_id OR b.id = $to_id OR b.name = $to_id)
                                MERGE (a)-[r:{rel_type}]->(b)
                                SET r += $properties
                                RETURN r
                                """

                                result = session.run(query, sitzungsnummer=sitzungsnummer, wahlperiode=int(wahlperiode), to_id=to_id, properties=properties)
                                if result.single():
                                    edges_saved += 1
                                continue

                        # Standard handling for other entity types
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
