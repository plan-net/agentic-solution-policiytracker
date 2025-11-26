#!/usr/bin/env python3
"""
Phase 2 Migration Script - Build EntityRegistry from Existing Entities

This script scans existing Neo4j Entity nodes and populates the Phase 2
EntityRegistry with CanonicalEntity and EntityAlias nodes.

Process:
1. Scan all existing Entity nodes in the graph
2. Group entities by normalized names (case-insensitive)
3. Detect similar entities using Levenshtein distance (threshold: 0.85)
4. Create CanonicalEntity nodes for unique entities
5. Create EntityAlias nodes for variations
6. Optionally consolidate duplicate entities

Usage:
    # Dry run (no changes)
    python scripts/migrate_to_phase2.py --dry-run

    # Execute migration
    python scripts/migrate_to_phase2.py

    # Execute with duplicate consolidation
    python scripts/migrate_to_phase2.py --consolidate

    # Rollback migration
    python scripts/migrate_to_phase2.py --rollback
"""

import argparse
import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple

import structlog
from neo4j import GraphDatabase

# Add project root to path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.flows.data_ingestion.entity_registry import EntityRegistry

logger = structlog.get_logger()

# Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "politicalmonitoring.v3")


class Phase2Migrator:
    """Migrate existing Neo4j entities to Phase 2 EntityRegistry."""

    def __init__(self, dry_run: bool = False, consolidate: bool = False):
        self.dry_run = dry_run
        self.consolidate = consolidate
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.registry = EntityRegistry(
            neo4j_uri=NEO4J_URI,
            neo4j_user=NEO4J_USER,
            neo4j_password=NEO4J_PASSWORD,
            database=NEO4J_DATABASE,
        )

        self.stats = {
            "total_entities_scanned": 0,
            "canonical_entities_created": 0,
            "aliases_created": 0,
            "duplicates_consolidated": 0,
            "errors": [],
        }

    async def migrate(self):
        """Execute Phase 2 migration."""
        logger.info(
            "Starting Phase 2 migration",
            dry_run=self.dry_run,
            consolidate=self.consolidate,
        )

        try:
            # Step 1: Initialize EntityRegistry schema
            logger.info("Step 1: Initializing EntityRegistry schema")
            if not self.dry_run:
                await self.registry.initialize_schema()
                logger.info("✅ EntityRegistry schema initialized")
            else:
                logger.info("✅ (DRY RUN) Would initialize EntityRegistry schema")

            # Step 2: Scan existing entities
            logger.info("Step 2: Scanning existing Entity nodes")
            entities = await self._scan_existing_entities()
            self.stats["total_entities_scanned"] = len(entities)
            logger.info(f"Found {len(entities)} existing Entity nodes")

            # Step 3: Group entities by normalized names
            logger.info("Step 3: Grouping entities by normalized names")
            entity_groups = self._group_entities_by_normalized_name(entities)
            logger.info(f"Grouped into {len(entity_groups)} unique normalized names")

            # Step 4: Detect similar entity groups using fuzzy matching
            logger.info("Step 4: Detecting similar entity groups")
            canonical_groups = await self._detect_similar_groups(entity_groups)
            logger.info(f"Detected {len(canonical_groups)} canonical entity groups")

            # Step 5: Create CanonicalEntity and EntityAlias nodes
            logger.info("Step 5: Creating CanonicalEntity and EntityAlias nodes")
            await self._create_registry_entries(canonical_groups)

            # Step 6: Optionally consolidate duplicate entities
            if self.consolidate:
                logger.info("Step 6: Consolidating duplicate entities")
                await self._consolidate_duplicates(canonical_groups)
            else:
                logger.info("Step 6: Skipped consolidation (use --consolidate to enable)")

            # Step 7: Validate migration
            logger.info("Step 7: Validating migration")
            await self._validate_migration()

            # Print final summary
            self._print_summary()

        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            raise
        finally:
            self.driver.close()
            if self.registry:
                self.registry.close()

    async def _scan_existing_entities(self) -> List[Dict]:
        """Scan all existing Entity nodes in the graph."""
        query = """
        MATCH (e:Entity)
        RETURN e.uuid AS uuid, e.name AS name, labels(e) AS labels,
               e.created_at AS created_at
        ORDER BY e.name
        """

        entities = []
        with self.driver.session(database=NEO4J_DATABASE) as session:
            result = session.run(query)
            for record in result:
                # Get entity type from labels (exclude "Entity" base label)
                labels = [label for label in record["labels"] if label != "Entity"]
                entity_type = labels[0] if labels else "Entity"

                entities.append(
                    {
                        "uuid": record["uuid"],
                        "name": record["name"],
                        "entity_type": entity_type,
                        "created_at": record.get("created_at"),
                    }
                )

        return entities

    def _group_entities_by_normalized_name(self, entities: List[Dict]) -> Dict[str, List[Dict]]:
        """Group entities by normalized (lowercase) names."""
        groups = {}
        for entity in entities:
            normalized_name = entity["name"].lower().strip()
            if normalized_name not in groups:
                groups[normalized_name] = []
            groups[normalized_name].append(entity)

        return groups

    async def _detect_similar_groups(
        self, entity_groups: Dict[str, List[Dict]]
    ) -> List[Dict]:
        """Detect similar entity groups using fuzzy matching."""
        canonical_groups = []
        processed_groups = set()

        # Sort groups by size (largest first) to prioritize common entities
        sorted_groups = sorted(
            entity_groups.items(), key=lambda x: len(x[1]), reverse=True
        )

        for normalized_name, entities in sorted_groups:
            if normalized_name in processed_groups:
                continue

            # Find similar groups using Levenshtein distance
            similar_groups = [normalized_name]
            for other_name, _ in sorted_groups:
                if other_name == normalized_name or other_name in processed_groups:
                    continue

                # Use EntityRegistry's find_similar_entities method
                similarity = await self._calculate_similarity(normalized_name, other_name)
                if similarity >= 0.85:
                    similar_groups.append(other_name)
                    processed_groups.add(other_name)

            # Mark current group as processed
            processed_groups.add(normalized_name)

            # Create canonical group with all similar variations
            canonical_name = entities[0]["name"]  # Use most common variation
            entity_type = entities[0]["entity_type"]

            # Collect all entities from similar groups
            all_entities = []
            for group_name in similar_groups:
                all_entities.extend(entity_groups[group_name])

            canonical_groups.append(
                {
                    "canonical_name": canonical_name,
                    "entity_type": entity_type,
                    "variations": similar_groups,
                    "entities": all_entities,
                    "entity_count": len(all_entities),
                }
            )

        return canonical_groups

    async def _calculate_similarity(self, name1: str, name2: str) -> float:
        """Calculate Levenshtein similarity between two names."""
        # Use simple Levenshtein distance calculation
        # (In production, would use apoc.text.levenshteinSimilarity)
        import Levenshtein

        return Levenshtein.ratio(name1, name2)

    async def _create_registry_entries(self, canonical_groups: List[Dict]):
        """Create CanonicalEntity and EntityAlias nodes."""
        for group in canonical_groups:
            canonical_name = group["canonical_name"]
            entity_type = group["entity_type"]
            entities = group["entities"]

            # Create CanonicalEntity (use first entity's UUID)
            canonical_uuid = entities[0]["uuid"]

            if not self.dry_run:
                success = await self.registry.register_canonical_entity(
                    name=canonical_name,
                    entity_type=entity_type,
                    entity_uuid=canonical_uuid,
                    metadata={
                        "source": "phase2_migration",
                        "migration_date": datetime.now().isoformat(),
                        "entity_count": group["entity_count"],
                    },
                )

                if success:
                    self.stats["canonical_entities_created"] += 1
                else:
                    self.stats["errors"].append(
                        f"Failed to create canonical entity: {canonical_name}"
                    )

                # Create aliases for all variations (except canonical name itself)
                for entity in entities:
                    if entity["name"].lower() != canonical_name.lower():
                        alias_success = await self.registry.add_alias(
                            canonical_uuid=canonical_uuid,
                            alias=entity["name"],
                            confidence=0.95,
                            source="phase2_migration",
                        )

                        if alias_success:
                            self.stats["aliases_created"] += 1
                        else:
                            self.stats["errors"].append(
                                f"Failed to create alias: {entity['name']} → {canonical_name}"
                            )
            else:
                logger.info(
                    f"(DRY RUN) Would create canonical entity: {canonical_name} ({entity_type}) with {group['entity_count']} variations"
                )
                self.stats["canonical_entities_created"] += 1
                self.stats["aliases_created"] += group["entity_count"] - 1

    async def _consolidate_duplicates(self, canonical_groups: List[Dict]):
        """Consolidate duplicate entities by merging into canonical entities."""
        if self.dry_run:
            logger.info("(DRY RUN) Would consolidate duplicate entities")
            return

        for group in canonical_groups:
            if len(group["entities"]) <= 1:
                continue  # No duplicates to consolidate

            canonical_uuid = group["entities"][0]["uuid"]
            duplicate_uuids = [e["uuid"] for e in group["entities"][1:]]

            # Merge duplicate entities into canonical entity
            consolidation_query = """
            MATCH (canonical:Entity {uuid: $canonical_uuid})
            MATCH (duplicate:Entity)
            WHERE duplicate.uuid IN $duplicate_uuids

            // Transfer all relationships from duplicate to canonical
            MATCH (duplicate)-[r]->(target)
            WHERE NOT (canonical)-[:TYPE(r)]->(target)
            CREATE (canonical)-[new_r:TYPE(r)]->(target)
            SET new_r = properties(r)

            MATCH (source)-[r]->(duplicate)
            WHERE NOT (source)-[:TYPE(r)]->(canonical)
            CREATE (source)-[new_r:TYPE(r)]->(canonical)
            SET new_r = properties(r)

            // Delete duplicate entities
            DETACH DELETE duplicate

            RETURN count(duplicate) AS consolidated_count
            """

            try:
                with self.driver.session(database=NEO4J_DATABASE) as session:
                    result = session.run(
                        consolidation_query,
                        canonical_uuid=canonical_uuid,
                        duplicate_uuids=duplicate_uuids,
                    )
                    record = result.single()
                    if record:
                        consolidated_count = record["consolidated_count"]
                        self.stats["duplicates_consolidated"] += consolidated_count
                        logger.info(
                            f"Consolidated {consolidated_count} duplicates into {group['canonical_name']}"
                        )
            except Exception as e:
                self.stats["errors"].append(
                    f"Failed to consolidate duplicates for {group['canonical_name']}: {e}"
                )

    async def _validate_migration(self):
        """Validate the migration was successful."""
        # Get registry stats
        registry_stats = await self.registry.get_registry_stats()

        logger.info(
            "Migration validation",
            canonical_entities=registry_stats["canonical_entity_count"],
            aliases=registry_stats["alias_count"],
            avg_aliases_per_entity=registry_stats["avg_aliases_per_entity"],
        )

        # Verify counts match expectations
        if not self.dry_run:
            expected_canonicals = self.stats["canonical_entities_created"]
            actual_canonicals = registry_stats["canonical_entity_count"]

            if expected_canonicals != actual_canonicals:
                logger.warning(
                    f"⚠️ Mismatch in canonical entity count: expected {expected_canonicals}, got {actual_canonicals}"
                )
            else:
                logger.info("✅ Canonical entity count validated")

    def _print_summary(self):
        """Print migration summary."""
        print("\n" + "=" * 80)
        print("PHASE 2 MIGRATION SUMMARY")
        print("=" * 80)

        if self.dry_run:
            print("\n⚠️  DRY RUN MODE - No changes were made")

        print(f"\n📊 Entity Statistics:")
        print(f"   Total entities scanned:        {self.stats['total_entities_scanned']}")
        print(f"   Canonical entities created:    {self.stats['canonical_entities_created']}")
        print(f"   Aliases created:               {self.stats['aliases_created']}")

        if self.consolidate:
            print(f"   Duplicates consolidated:       {self.stats['duplicates_consolidated']}")

        if self.stats["errors"]:
            print(f"\n❌ Errors: {len(self.stats['errors'])}")
            for error in self.stats["errors"][:10]:  # Show first 10 errors
                print(f"   - {error}")
            if len(self.stats["errors"]) > 10:
                print(f"   ... and {len(self.stats['errors']) - 10} more errors")
        else:
            print("\n✅ No errors encountered")

        # Calculate reduction
        if self.stats["total_entities_scanned"] > 0:
            reduction = (
                1 - self.stats["canonical_entities_created"] / self.stats["total_entities_scanned"]
            ) * 100
            print(f"\n📉 Duplicate Reduction: {reduction:.1f}%")

        print("\n" + "=" * 80)

    async def rollback(self):
        """Rollback Phase 2 migration by removing all CanonicalEntity and EntityAlias nodes."""
        logger.warning("⚠️ ROLLBACK: Removing all Phase 2 EntityRegistry nodes")

        if self.dry_run:
            logger.info("(DRY RUN) Would remove all CanonicalEntity and EntityAlias nodes")
            return

        rollback_query = """
        MATCH (ce:CanonicalEntity)
        OPTIONAL MATCH (ea:EntityAlias)-[:ALIAS_OF]->(ce)
        DETACH DELETE ce, ea
        RETURN count(ce) AS canonical_count, count(ea) AS alias_count
        """

        try:
            with self.driver.session(database=NEO4J_DATABASE) as session:
                result = session.run(rollback_query)
                record = result.single()
                if record:
                    logger.info(
                        f"✅ Rollback complete: removed {record['canonical_count']} canonical entities and {record['alias_count']} aliases"
                    )
        except Exception as e:
            logger.error(f"Rollback failed: {e}", exc_info=True)
            raise


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Phase 2 Migration Script")
    parser.add_argument("--dry-run", action="store_true", help="Run without making changes")
    parser.add_argument(
        "--consolidate", action="store_true", help="Consolidate duplicate entities"
    )
    parser.add_argument("--rollback", action="store_true", help="Rollback Phase 2 migration")

    args = parser.parse_args()

    migrator = Phase2Migrator(dry_run=args.dry_run, consolidate=args.consolidate)

    if args.rollback:
        await migrator.rollback()
    else:
        await migrator.migrate()


if __name__ == "__main__":
    asyncio.run(main())
