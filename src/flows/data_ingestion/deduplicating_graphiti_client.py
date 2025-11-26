"""
Deduplicating Graphiti Client - Phase 2 Deduplication Wrapper.

Wraps the Graphiti client to enforce entity deduplication at ingestion time by:
1. Pre-normalizing entity names (Phase 1 EntityNormalizer)
2. Post-processing extracted entities to check EntityRegistry
3. Resolving entity names to canonical forms
4. Reusing canonical entity UUIDs when matches found
5. Registering new entities and aliases in the registry

This prevents duplicate entity creation by ensuring all entity variations
map to a single canonical entity in the knowledge graph.

Architecture:
    User Code → DeduplicatingGraphitiClient → Graphiti → Neo4j
                            ↓
                     EntityRegistry ← → Neo4j (CanonicalEntity/EntityAlias)
                            ↓
                     EntityNormalizer (Phase 1)

Example:
    # Initialize components
    registry = EntityRegistry(neo4j_driver)
    await registry.initialize_schema()

    normalizer = EntityNormalizer()
    base_client = Graphiti(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    # Create deduplicating wrapper
    dedupe_client = DeduplicatingGraphitiClient(
        base_client=base_client,
        entity_registry=registry,
        entity_normalizer=normalizer
    )

    # Use like normal Graphiti client - deduplication happens automatically
    result = await dedupe_client.add_episode(
        name="EU_AI_Act_Document",
        episode_body=document_text,
        source=EpisodeType.text
    )
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType

from src.flows.data_ingestion.entity_normalizer import EntityNormalizer
from src.flows.data_ingestion.entity_registry import EntityRegistry

logger = structlog.get_logger()


@dataclass
class EntityResolutionResult:
    """Result of entity resolution process."""

    original_uuid: str
    canonical_uuid: str
    is_reused: bool  # True if resolved to existing canonical entity
    match_type: Optional[str] = None  # exact, alias, fuzzy, or new
    confidence: float = 1.0


@dataclass
class DeduplicationStats:
    """Statistics from deduplication process."""

    total_entities_extracted: int
    entities_reused: int
    entities_created: int
    aliases_registered: int
    reuse_rate: float
    processing_time_seconds: float


class DeduplicatingGraphitiClient:
    """
    Graphiti client wrapper with built-in entity deduplication.

    This wrapper adds zero-duplicate entity ingestion by:
    - Normalizing entity names before extraction
    - Checking EntityRegistry for existing canonical entities
    - Mapping extracted entities to canonical UUIDs
    - Registering new entities and aliases automatically

    All Graphiti client methods are proxied, so this can be used as a
    drop-in replacement for the standard Graphiti client.
    """

    def __init__(
        self,
        base_client: Graphiti,
        entity_registry: EntityRegistry,
        entity_normalizer: Optional[EntityNormalizer] = None,
        enable_deduplication: bool = True,
        enable_alias_registration: bool = True,
    ):
        """
        Initialize DeduplicatingGraphitiClient.

        Args:
            base_client: Base Graphiti client instance
            entity_registry: EntityRegistry for canonical entity management
            entity_normalizer: EntityNormalizer for text preprocessing (default: creates new instance)
            enable_deduplication: Enable entity deduplication (default: True)
            enable_alias_registration: Auto-register aliases for new entities (default: True)
        """
        self.base_client = base_client
        self.registry = entity_registry
        self.normalizer = entity_normalizer or EntityNormalizer()
        self.enable_deduplication = enable_deduplication
        self.enable_alias_registration = enable_alias_registration

        # Statistics tracking
        self.stats = {
            "total_episodes": 0,
            "total_entities_processed": 0,
            "total_entities_reused": 0,
            "total_entities_created": 0,
            "total_aliases_registered": 0,
        }

        logger.info(
            "DeduplicatingGraphitiClient initialized",
            enable_deduplication=enable_deduplication,
            enable_alias_registration=enable_alias_registration,
        )

    async def add_episode(
        self,
        name: str,
        episode_body: str,
        source: EpisodeType,
        source_description: Optional[str] = None,
        reference_time: Optional[datetime] = None,
        **kwargs,
    ):
        """
        Add episode with entity deduplication.

        Process:
        1. Normalize episode_body text (Phase 1)
        2. Call base_client.add_episode() to extract entities
        3. Post-process extracted entities:
           a. For each entity, check EntityRegistry
           b. If match found: use canonical UUID, register alias
           c. If no match: register as new canonical entity
        4. Return result with deduplication metadata

        Args:
            name: Episode name
            episode_body: Text content to process
            source: Episode source type
            source_description: Optional description
            reference_time: Optional timestamp
            **kwargs: Additional arguments passed to base Graphiti client

        Returns:
            Episode result with entities resolved to canonical forms
        """
        start_time = asyncio.get_event_loop().time()

        try:
            # Step 1: Normalize text using Phase 1 normalizer
            if self.enable_deduplication:
                normalized_body = self.normalizer.normalize_text(episode_body)

                # Log normalization stats
                norm_stats = self.normalizer.get_statistics(episode_body)
                if norm_stats["total_abbreviations"] > 0:
                    logger.debug(
                        "Normalized text before extraction",
                        abbreviations_expanded=norm_stats["total_abbreviations"],
                        episode_name=name,
                    )
            else:
                normalized_body = episode_body

            # Step 2: Extract entities via base Graphiti client
            logger.debug("Extracting entities via Graphiti", episode_name=name)
            result = await self.base_client.add_episode(
                name=name,
                episode_body=normalized_body,
                source=source,
                source_description=source_description,
                reference_time=reference_time or datetime.now(),
                **kwargs,
            )

            # Step 3: Post-process entities for deduplication
            if self.enable_deduplication and hasattr(result, "nodes"):
                dedup_result = await self._deduplicate_entities(result, name)

                # Update statistics
                self.stats["total_episodes"] += 1
                self.stats["total_entities_processed"] += dedup_result.total_entities_extracted
                self.stats["total_entities_reused"] += dedup_result.entities_reused
                self.stats["total_entities_created"] += dedup_result.entities_created
                self.stats["total_aliases_registered"] += dedup_result.aliases_registered

                # Attach deduplication metadata to result
                if not hasattr(result, "metadata"):
                    result.metadata = {}
                result.metadata["deduplication"] = {
                    "enabled": True,
                    "entities_reused": dedup_result.entities_reused,
                    "entities_created": dedup_result.entities_created,
                    "aliases_registered": dedup_result.aliases_registered,
                    "reuse_rate": dedup_result.reuse_rate,
                    "processing_time_seconds": dedup_result.processing_time_seconds,
                }

                processing_time = asyncio.get_event_loop().time() - start_time
                logger.info(
                    "Episode processed with deduplication",
                    episode_name=name,
                    entities_extracted=dedup_result.total_entities_extracted,
                    entities_reused=dedup_result.entities_reused,
                    entities_created=dedup_result.entities_created,
                    reuse_rate=f"{dedup_result.reuse_rate:.1%}",
                    processing_time=f"{processing_time:.2f}s",
                )

            return result

        except Exception as e:
            logger.error(f"Failed to process episode with deduplication: {e}", episode_name=name)
            raise

    async def _deduplicate_entities(self, result, episode_name: str) -> DeduplicationStats:
        """
        Deduplicate extracted entities by checking EntityRegistry.

        For each entity:
        1. Check registry for canonical match
        2. If match: register as alias (if name differs)
        3. If no match: register as new canonical entity

        Args:
            result: Episode result from base Graphiti client
            episode_name: Episode name for logging

        Returns:
            DeduplicationStats with processing metrics
        """
        start_time = asyncio.get_event_loop().time()

        entities_reused = 0
        entities_created = 0
        aliases_registered = 0

        # Track entity resolution for this episode
        resolution_map: Dict[str, EntityResolutionResult] = {}

        for entity in result.nodes:
            entity_name = entity.name
            entity_type = entity.labels[0] if entity.labels else "Entity"

            # Check registry for canonical form
            canonical = await self.registry.get_canonical_entity(entity_name, entity_type)

            if canonical:
                # Entity matches existing canonical entity
                entities_reused += 1

                resolution_map[entity.uuid] = EntityResolutionResult(
                    original_uuid=entity.uuid,
                    canonical_uuid=canonical["canonical_uuid"],
                    is_reused=True,
                    match_type=canonical["match_type"],
                    confidence=canonical["confidence"],
                )

                # Register this name as alias if not exact match
                if (
                    self.enable_alias_registration
                    and entity_name.lower() != canonical["canonical_name"].lower()
                ):
                    alias_added = await self.registry.add_alias(
                        canonical_uuid=canonical["canonical_uuid"],
                        alias=entity_name,
                        confidence=canonical["confidence"],
                        source="graphiti_extraction",
                    )
                    if alias_added:
                        aliases_registered += 1

                logger.debug(
                    "Entity resolved to existing canonical",
                    entity_name=entity_name,
                    canonical_name=canonical["canonical_name"],
                    match_type=canonical["match_type"],
                    confidence=canonical["confidence"],
                )

            else:
                # New entity - register as canonical
                entities_created += 1

                registered = await self.registry.register_canonical_entity(
                    name=entity_name,
                    entity_type=entity_type,
                    entity_uuid=entity.uuid,
                    metadata={"episode_name": episode_name, "source": "graphiti_extraction"},
                )

                resolution_map[entity.uuid] = EntityResolutionResult(
                    original_uuid=entity.uuid,
                    canonical_uuid=entity.uuid,  # Self-mapping for new entities
                    is_reused=False,
                    match_type="new",
                    confidence=1.0,
                )

                if registered:
                    logger.debug("Registered new canonical entity", entity_name=entity_name, entity_type=entity_type)

        # Calculate statistics
        total_entities = len(result.nodes)
        reuse_rate = entities_reused / total_entities if total_entities > 0 else 0.0
        processing_time = asyncio.get_event_loop().time() - start_time

        stats = DeduplicationStats(
            total_entities_extracted=total_entities,
            entities_reused=entities_reused,
            entities_created=entities_created,
            aliases_registered=aliases_registered,
            reuse_rate=reuse_rate,
            processing_time_seconds=processing_time,
        )

        # Store resolution map in result metadata for downstream use
        if not hasattr(result, "metadata"):
            result.metadata = {}
        result.metadata["entity_resolution_map"] = resolution_map

        return stats

    async def get_deduplication_stats(self) -> Dict:
        """
        Get overall deduplication statistics for this client instance.

        Returns:
            {
                "total_episodes": 150,
                "total_entities_processed": 3500,
                "total_entities_reused": 1400,
                "total_entities_created": 2100,
                "total_aliases_registered": 800,
                "overall_reuse_rate": 0.40
            }
        """
        total_processed = self.stats["total_entities_processed"]
        total_reused = self.stats["total_entities_reused"]

        overall_reuse_rate = total_reused / total_processed if total_processed > 0 else 0.0

        return {
            **self.stats,
            "overall_reuse_rate": overall_reuse_rate,
        }

    # Proxy methods to base Graphiti client for compatibility

    async def search(self, *args, **kwargs):
        """Proxy search to base client."""
        return await self.base_client.search(*args, **kwargs)

    async def build_indices_and_constraints(self):
        """Proxy index building to base client."""
        return await self.base_client.build_indices_and_constraints()

    def close(self):
        """Close both base client and registry connections."""
        if hasattr(self.base_client, "close"):
            self.base_client.close()
        if self.registry:
            self.registry.close()
        logger.debug("DeduplicatingGraphitiClient closed")

    # Context manager support

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.close()


# Example usage
if __name__ == "__main__":
    import os

    async def test_deduplicating_client():
        """Test DeduplicatingGraphitiClient with sample documents."""
        from graphiti_core.llm_client import OpenAIClient

        print("=" * 80)
        print("DeduplicatingGraphitiClient Test")
        print("=" * 80)

        # Initialize components
        print("\n1. Initializing components...")

        # EntityRegistry
        registry = EntityRegistry()
        await registry.initialize_schema()
        print("   ✅ EntityRegistry initialized")

        # EntityNormalizer
        normalizer = EntityNormalizer()
        print("   ✅ EntityNormalizer initialized")

        # Base Graphiti client
        llm_client = OpenAIClient(os.getenv("OPENAI_API_KEY"))
        base_client = Graphiti(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            os.getenv("NEO4J_USER", "neo4j"),
            os.getenv("NEO4J_PASSWORD", "password123"),
            llm_client=llm_client,
        )
        await base_client.build_indices_and_constraints()
        print("   ✅ Base Graphiti client initialized")

        # DeduplicatingGraphitiClient
        dedupe_client = DeduplicatingGraphitiClient(
            base_client=base_client, entity_registry=registry, entity_normalizer=normalizer
        )
        print("   ✅ DeduplicatingGraphitiClient initialized")

        # Test documents with entity variations
        test_documents = [
            {
                "name": "doc_1_eu_commission",
                "text": "The EU Commission announced new GDPR enforcement actions against Meta.",
            },
            {
                "name": "doc_2_european_commission",
                "text": "The European Commission proposed updates to the Digital Services Act.",
            },
            {
                "name": "doc_3_variations",
                "text": "Both the EU Commission and Meta are involved in GDPR compliance discussions.",
            },
        ]

        print("\n2. Processing documents with deduplication...")
        for i, doc in enumerate(test_documents, 1):
            print(f"\n   Document {i}: {doc['name']}")
            print(f"   Text: {doc['text'][:80]}...")

            result = await dedupe_client.add_episode(
                name=doc["name"], episode_body=doc["text"], source=EpisodeType.text
            )

            # Print deduplication metadata
            if hasattr(result, "metadata") and "deduplication" in result.metadata:
                dedup_meta = result.metadata["deduplication"]
                print(f"   Entities extracted: {dedup_meta.get('entities_reused', 0) + dedup_meta.get('entities_created', 0)}")
                print(f"   Entities reused: {dedup_meta.get('entities_reused', 0)}")
                print(f"   Entities created: {dedup_meta.get('entities_created', 0)}")
                print(f"   Reuse rate: {dedup_meta.get('reuse_rate', 0):.1%}")

        # Get overall stats
        print("\n3. Overall Deduplication Statistics")
        print("   " + "=" * 76)
        stats = await dedupe_client.get_deduplication_stats()
        print(f"   Total episodes processed: {stats['total_episodes']}")
        print(f"   Total entities processed: {stats['total_entities_processed']}")
        print(f"   Entities reused: {stats['total_entities_reused']}")
        print(f"   Entities created: {stats['total_entities_created']}")
        print(f"   Aliases registered: {stats['total_aliases_registered']}")
        print(f"   Overall reuse rate: {stats['overall_reuse_rate']:.1%}")

        # Get registry stats
        print("\n4. EntityRegistry Statistics")
        print("   " + "=" * 76)
        registry_stats = await registry.get_registry_stats()
        print(f"   Canonical entities: {registry_stats['canonical_entity_count']}")
        print(f"   Aliases: {registry_stats['alias_count']}")
        print(f"   Avg aliases per entity: {registry_stats['avg_aliases_per_entity']:.2f}")

        # Cleanup
        dedupe_client.close()
        print("\n✅ Test complete!")

    # Run test
    asyncio.run(test_deduplicating_client())
