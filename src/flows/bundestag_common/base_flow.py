"""
Base flow class for all Bundestag data ingestion flows.

Provides common functionality for API fetching, entity creation, and Neo4j upserting.
Each specific endpoint flow (person, vorgang, etc.) inherits from this base.
"""

import os
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

import structlog
from kodosumi import core
from kodosumi.core import Tracer
from neo4j import GraphDatabase

from src.flows.bundestag_common.api_client import BundestagAPIClient
from src.flows.bundestag_common.graphiti_registration import GraphitiNodeRegistrar
from src.flows.bundestag_common.neo4j_upsert import Neo4jUpsertManager
from src.flows.bundestag_common.pagination import PaginationHelper

logger = structlog.get_logger()


class BaseBundestagFlow(ABC):
    """
    Base class for deterministic Bundestag data ingestion flows.

    Each flow is responsible for:
    1. Fetching data from a specific API endpoint
    2. Mapping API data to entity objects (deterministic, no auto-detection)
    3. Upserting entities to Neo4j with automatic deduplication
    4. [Optional] Registering entities with Graphiti for hybrid search

    Subclasses must implement:
    - endpoint property: API endpoint name
    - entity_type property: Neo4j label
    - entity_id_field property: Primary key field name
    - map_api_to_entity(): Convert API data to entity dict
    - get_entity_name(): Extract entity name for Graphiti
    """

    def __init__(
        self,
        api_key: str,
        api_url: str,
        neo4j_uri: str,
        neo4j_username: str,
        neo4j_password: str,
        neo4j_database: str = "neo4j",
        enable_graphiti_registration: bool = False,
        openai_api_key: Optional[str] = None,
    ):
        """
        Initialize base flow.

        Args:
            api_key: Bundestag DIP API key
            api_url: API base URL
            neo4j_uri: Neo4j connection URI
            neo4j_username: Neo4j username
            neo4j_password: Neo4j password
            neo4j_database: Neo4j database name
            enable_graphiti_registration: Enable automatic Graphiti registration
            openai_api_key: OpenAI API key (required if enable_graphiti_registration=True)
        """
        # Initialize API client
        self.api_client = BundestagAPIClient(api_key=api_key, base_url=api_url)

        # Initialize Neo4j driver
        self.neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
        self.neo4j_database = neo4j_database

        # Initialize upsert manager
        self.upsert_manager = Neo4jUpsertManager(driver=self.neo4j_driver, database=neo4j_database)

        # Initialize Graphiti registrar (optional)
        self.enable_graphiti_registration = enable_graphiti_registration
        self.graphiti_registrar: Optional[GraphitiNodeRegistrar] = None

        if enable_graphiti_registration:
            if not openai_api_key:
                openai_api_key = os.getenv("OPENAI_API_KEY")

            if not openai_api_key:
                raise ValueError(
                    "openai_api_key is required when enable_graphiti_registration=True"
                )

            self.graphiti_registrar = GraphitiNodeRegistrar(
                neo4j_driver=self.neo4j_driver,
                neo4j_database=neo4j_database,
                openai_api_key=openai_api_key,
            )

            logger.info(
                "Graphiti registration enabled",
                endpoint=self.endpoint,
                entity_type=self.entity_type,
            )

        logger.info(
            "Initialized BaseBundestagFlow",
            endpoint=self.endpoint,
            entity_type=self.entity_type,
            database=neo4j_database,
            graphiti_enabled=enable_graphiti_registration,
        )

    @property
    @abstractmethod
    def endpoint(self) -> str:
        """API endpoint name (e.g., 'person', 'vorgang')."""
        pass

    @property
    @abstractmethod
    def entity_type(self) -> str:
        """Neo4j entity label (e.g., 'BundestagPerson', 'Vorgang')."""
        pass

    @property
    @abstractmethod
    def entity_id_field(self) -> str:
        """
        Primary key field name for this entity type.

        Examples:
        - "person_id" for BundestagPerson
        - "vorgang_id" for Vorgang
        - "drucksache_id" for Drucksache
        """
        pass

    @abstractmethod
    def map_api_to_entity(self, api_data: dict[str, Any]) -> dict[str, Any]:
        """
        Map API response data to entity properties dict.

        This is the key method that makes each flow deterministic.
        No auto-detection - explicit field mapping only.

        Args:
            api_data: Raw API response item

        Returns:
            Entity properties dict ready for Neo4j
        """
        pass

    @abstractmethod
    def get_entity_name(self, entity: dict[str, Any]) -> str:
        """
        Extract entity name for Graphiti registration.

        This name is used for:
        1. Generating embeddings
        2. Semantic search via Graphiti

        Args:
            entity: Entity properties dict

        Returns:
            Human-readable entity name

        Examples:
        - For BundestagPerson: "Olaf Scholz"
        - For Vorgang: "Gesetz zur Änderung des Grundgesetzes"
        - For Drucksache: "Drucksache 20/1234"
        """
        pass

    async def process(self, inputs: dict[str, Any], tracer: Tracer) -> core.response.Markdown:
        """
        Main processing method called by Kodosumi.

        Args:
            inputs: Form inputs from user
            tracer: Kodosumi tracer for progress updates

        Returns:
            Markdown report of execution
        """
        start_time = time.time()
        await tracer.markdown(f"# {inputs.get('job_name', 'Bundestag Data Ingestion')}\n")
        await tracer.markdown(f"**Endpoint:** {self.endpoint}\n")
        await tracer.markdown(f"**Entity Type:** {self.entity_type}\n")
        await tracer.markdown(f"**Start Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Extract parameters
        wahlperiode = inputs.get("wahlperiode")
        max_items = inputs.get("max_items", 100)
        start_date = inputs.get("start_date")
        end_date = inputs.get("end_date")
        aktivitaetsart = inputs.get("aktivitaetsart")  # For Aktivitaet endpoint

        # Build filters
        filters = {}
        if wahlperiode and wahlperiode != "all":
            filters["f.wahlperiode"] = wahlperiode
        if start_date:
            filters["f.datum_von"] = start_date
        if end_date:
            filters["f.datum_bis"] = end_date
        if aktivitaetsart and aktivitaetsart != "Alle":
            filters["f.aktivitaetsart"] = aktivitaetsart

        await tracer.markdown(f"**Filters:** {filters}\n")
        await tracer.markdown(
            f"**Max Items:** {'All (no limit)' if max_items is None else max_items}\n\n"
        )

        # Stage 1: Fetch data from API
        await tracer.markdown("## Stage 1: Fetching Data from API\n")
        items = await self.fetch_data(filters, max_items, tracer)

        await tracer.markdown(f"✅ Fetched **{len(items)}** items from API\n\n")

        # Stage 2: Map to entities
        await tracer.markdown("## Stage 2: Mapping to Entities\n")
        entities = await self.map_to_entities(items, tracer)

        await tracer.markdown(f"✅ Mapped **{len(entities)}** entities\n\n")

        # Stage 3: Upsert to Neo4j
        await tracer.markdown("## Stage 3: Upserting to Neo4j\n")
        upsert_results = await self.upsert_entities(entities, tracer)

        await tracer.markdown(
            f"✅ Upserted **{upsert_results['successful']}** entities "
            f"({upsert_results['failed']} failed)\n\n"
        )

        # Stage 4: Register with Graphiti (optional)
        graphiti_results = {"registered": 0, "failed": 0}
        if self.enable_graphiti_registration and upsert_results["successful"] > 0:
            await tracer.markdown("## Stage 4: Registering with Graphiti\n")
            graphiti_results = await self.register_entities_with_graphiti(entities, tracer)

            await tracer.markdown(
                f"✅ Registered **{graphiti_results['registered']}** entities with Graphiti "
                f"({graphiti_results['failed']} failed)\n\n"
            )

        # Generate report
        duration = time.time() - start_time
        await tracer.markdown(f"**Duration:** {duration:.1f} seconds\n")
        await tracer.markdown(f"**End Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        report = self.generate_report(
            items_fetched=len(items),
            entities_created=len(entities),
            upsert_results=upsert_results,
            graphiti_results=graphiti_results,
            duration=duration,
            inputs=inputs,
        )

        return core.response.Markdown(report)

    async def fetch_data(
        self, filters: dict[str, Any], max_items: Optional[int], tracer: Tracer
    ) -> list[dict[str, Any]]:
        """
        Fetch data from API with pagination.

        Args:
            filters: API filter parameters
            max_items: Maximum items to fetch
            tracer: Progress tracer

        Returns:
            List of raw API items
        """
        await tracer.markdown(f"Fetching from endpoint: **{self.endpoint}**...\n")

        pagination_helper = PaginationHelper(api_client=self.api_client, max_items=max_items)

        items = []
        async for item in pagination_helper.paginate(self.endpoint, filters):
            items.append(item)

            # Progress update every 100 items
            if len(items) % 100 == 0:
                await tracer.markdown(f"- Fetched {len(items)} items...\n")

        logger.info("Completed API fetch", endpoint=self.endpoint, items_count=len(items))

        return items

    async def map_to_entities(
        self, items: list[dict[str, Any]], tracer: Tracer
    ) -> list[dict[str, Any]]:
        """
        Map API items to entity dicts.

        Args:
            items: Raw API items
            tracer: Progress tracer

        Returns:
            List of entity property dicts
        """
        entities = []
        errors = 0

        for i, item in enumerate(items):
            try:
                entity = self.map_api_to_entity(item)
                entities.append(entity)

                # Progress update every 100 items
                if (i + 1) % 100 == 0:
                    await tracer.markdown(f"- Mapped {i + 1} entities...\n")

            except Exception as e:
                logger.error(
                    "Failed to map item to entity",
                    endpoint=self.endpoint,
                    item_id=item.get("id"),
                    error=str(e),
                )
                errors += 1

        if errors > 0:
            await tracer.markdown(f"⚠️ {errors} items failed to map\n")

        logger.info(
            "Completed entity mapping",
            endpoint=self.endpoint,
            total=len(items),
            successful=len(entities),
            failed=errors,
        )

        return entities

    async def upsert_entities(
        self, entities: list[dict[str, Any]], tracer: Tracer
    ) -> dict[str, int]:
        """
        Upsert entities to Neo4j in batches.

        Args:
            entities: Entity property dicts
            tracer: Progress tracer

        Returns:
            Upsert results with counts
        """
        await tracer.markdown(f"Upserting **{len(entities)}** entities to Neo4j...\n")

        results = self.upsert_manager.upsert_entities_batch(
            entity_type=self.entity_type, entities=entities, batch_size=100
        )

        logger.info(
            "Completed Neo4j upsert",
            endpoint=self.endpoint,
            entity_type=self.entity_type,
            results=results,
        )

        return results

    async def register_entities_with_graphiti(
        self, entities: list[dict[str, Any]], tracer: Tracer
    ) -> dict[str, int]:
        """
        Register entities with Graphiti for hybrid search.

        Adds :Entity label, embeddings, and metadata to make Direct Neo4j
        nodes searchable via Graphiti's client.search().

        Args:
            entities: Entity property dicts
            tracer: Progress tracer

        Returns:
            Registration results with counts
        """
        if not self.graphiti_registrar:
            logger.warning("Graphiti registrar not initialized")
            return {"registered": 0, "failed": 0}

        await tracer.markdown(f"Registering **{len(entities)}** entities with Graphiti...\n")

        registered = 0
        failed = 0

        for i, entity in enumerate(entities):
            try:
                # Extract entity ID
                entity_id = entity.get(self.entity_id_field)
                if not entity_id:
                    logger.warning(
                        "Entity missing ID field",
                        entity_type=self.entity_type,
                        id_field=self.entity_id_field,
                    )
                    failed += 1
                    continue

                # Get entity name for embedding
                entity_name = self.get_entity_name(entity)

                # Register based on entity type
                result = await self._register_single_entity(
                    entity_id=entity_id,
                    entity_name=entity_name,
                    entity_dict=entity,
                )

                if result.get("success"):
                    registered += 1
                else:
                    failed += 1

                # Progress update every 50 entities
                if (i + 1) % 50 == 0:
                    await tracer.markdown(f"- Registered {i + 1}/{len(entities)} entities...\n")

            except Exception as e:
                logger.error(
                    "Failed to register entity with Graphiti",
                    entity_type=self.entity_type,
                    entity=entity,
                    error=str(e),
                )
                failed += 1

        logger.info(
            "Completed Graphiti registration",
            endpoint=self.endpoint,
            entity_type=self.entity_type,
            registered=registered,
            failed=failed,
        )

        return {"registered": registered, "failed": failed}

    async def _register_single_entity(
        self, entity_id: Any, entity_name: str, entity_dict: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Register a single entity with Graphiti using appropriate method.

        Subclasses can override this to handle special cases (e.g., composite keys).

        Args:
            entity_id: Entity identifier
            entity_name: Entity display name
            entity_dict: Full entity properties

        Returns:
            Registration result
        """
        # Default implementation uses add_entity_metadata directly
        embedding = await self.graphiti_registrar.generate_embedding(entity_name)

        return self.graphiti_registrar.add_entity_metadata(
            entity_label=self.entity_type,
            entity_id_field=self.entity_id_field,
            entity_id_value=entity_id,
            entity_name=entity_name,
            name_embedding=embedding,
        )

    def generate_report(
        self,
        items_fetched: int,
        entities_created: int,
        upsert_results: dict[str, int],
        graphiti_results: dict[str, int],
        duration: float,
        inputs: dict[str, Any],
    ) -> str:
        """
        Generate execution summary report.

        Args:
            items_fetched: Number of items from API
            entities_created: Number of entities mapped
            upsert_results: Neo4j upsert results
            graphiti_results: Graphiti registration results
            duration: Total execution time
            inputs: Original form inputs

        Returns:
            Markdown report
        """
        # Build Graphiti section if enabled
        graphiti_section = ""
        if self.enable_graphiti_registration and graphiti_results["registered"] > 0:
            graphiti_section = f"""
## Graphiti Registration

| Result | Count |
|--------|-------|
| Registered with Graphiti | {graphiti_results['registered']} |
| Failed Registration | {graphiti_results['failed']} |

✅ Entities are now searchable via Graphiti `client.search()`
"""

        report = f"""# {inputs.get('job_name', 'Bundestag Data Ingestion')} - Report

## Summary

**Endpoint:** {self.endpoint}
**Entity Type:** {self.entity_type}
**Execution Time:** {duration:.1f} seconds
**Graphiti Registration:** {'Enabled' if self.enable_graphiti_registration else 'Disabled'}

## Results

| Stage | Count |
|-------|-------|
| Items Fetched from API | {items_fetched} |
| Entities Mapped | {entities_created} |
| Successfully Upserted | {upsert_results['successful']} |
| Failed Upsert | {upsert_results['failed']} |
{graphiti_section}
## Neo4j Statistics

**Total {self.entity_type} in database:** {self.upsert_manager.get_entity_count(self.entity_type)}

## Parameters

- **Wahlperiode:** {inputs.get('wahlperiode', 'all')}
- **Max Items:** {'All (no limit)' if inputs.get('max_items') is None else inputs.get('max_items', 'unlimited')}
- **Date Range:** {inputs.get('start_date', 'none')} to {inputs.get('end_date', 'none')}

---

✅ Data ingestion complete!

Access your data at: http://localhost:7474
"""

        return report

    def cleanup(self):
        """Clean up resources."""
        if hasattr(self, "neo4j_driver") and self.neo4j_driver:
            self.neo4j_driver.close()

    def __del__(self):
        """Ensure cleanup on deletion."""
        self.cleanup()
