"""
Neo4j MERGE-based upsert operations for Bundestag entities.

Provides deterministic entity creation/update using Neo4j MERGE operations
with automatic deduplication via constraints.
"""

from typing import Any, Dict, List, Optional
import structlog
from neo4j import GraphDatabase, Driver

logger = structlog.get_logger()


class Neo4jUpsertManager:
    """
    Manager for upserting Bundestag entities to Neo4j with automatic deduplication.

    Uses MERGE operations to ensure entities are created if they don't exist
    or updated if they do, based on unique constraints.
    """

    # Define unique ID fields for each entity type
    ENTITY_ID_FIELDS = {
        "BundestagPerson": "person_id",
        "Vorgang": "vorgang_id",
        "Drucksache": "drucksache_nummer",
        "DrucksachePage": "page_id",
        "Plenarprotokoll": "plenarprotokoll_id",
        "Vorgangsposition": "vorgangsposition_id",
        "Aktivitaet": "aktivitaet_id",
        "Wahlperiode": "wahlperiode_nummer",
        "Fraktion": "fraktion_id",
        "Deskriptor": "deskriptor_id",
        "Sachgebiet": "sachgebiet_name",
    }

    def __init__(self, driver: Driver, database: str = "neo4j"):
        """
        Initialize Neo4j upsert manager.

        Args:
            driver: Neo4j driver instance
            database: Database name (default: "neo4j")
        """
        self.driver = driver
        self.database = database

        logger.info(
            "Initialized Neo4jUpsertManager",
            database=database
        )

    def upsert_entity(
        self,
        entity_type: str,
        entity_data: Dict[str, Any]
    ) -> bool:
        """
        Upsert a single entity using MERGE operation.

        Args:
            entity_type: Neo4j label (e.g., "BundestagPerson")
            entity_data: Entity properties as dict

        Returns:
            True if successful, False otherwise
        """
        print(f"[NEO4J_UPSERT] Starting upsert for entity_type={entity_type}")
        try:
            # Get the unique ID field for this entity type
            id_field = self.ENTITY_ID_FIELDS.get(entity_type)
            if not id_field:
                error_msg = f"Unknown entity type: {entity_type}"
                print(f"[NEO4J_UPSERT] ERROR: {error_msg}")
                logger.error(error_msg)
                return False

            # Extract unique ID value
            unique_id = entity_data.get(id_field)
            if not unique_id:
                error_msg = f"Missing required field {id_field} for entity_type={entity_type}"
                print(f"[NEO4J_UPSERT] ERROR: {error_msg}")
                logger.error(error_msg, entity_type=entity_type)
                return False

            print(f"[NEO4J_UPSERT] Entity {entity_type} with {id_field}={unique_id}")

            # Build MERGE query
            query = f"""
            MERGE (n:{entity_type} {{{id_field}: $unique_id}})
            SET n += $properties
            RETURN n
            """

            print(f"[NEO4J_UPSERT] Executing MERGE query...")
            with self.driver.session(database=self.database) as session:
                result = session.run(
                    query,
                    unique_id=unique_id,
                    properties=entity_data
                )

                if result.single():
                    print(f"[NEO4J_UPSERT] SUCCESS: Upserted {entity_type} {unique_id}")
                    logger.debug(
                        "Upserted entity",
                        entity_type=entity_type,
                        id_field=id_field,
                        unique_id=unique_id
                    )
                    return True
                else:
                    error_msg = f"MERGE returned no result for {entity_type}"
                    print(f"[NEO4J_UPSERT] WARNING: {error_msg}")
                    logger.warning(error_msg, entity_type=entity_type)
                    return False

        except Exception as e:
            error_msg = f"Failed to upsert entity {entity_type}: {str(e)}"
            print(f"[NEO4J_UPSERT] EXCEPTION: {error_msg}")
            import traceback
            print(f"[NEO4J_UPSERT] Traceback: {traceback.format_exc()}")
            logger.error(
                f"Failed to upsert entity",
                entity_type=entity_type,
                error=str(e)
            )
            return False

    def upsert_entities_batch(
        self,
        entity_type: str,
        entities: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> Dict[str, int]:
        """
        Upsert multiple entities in batches.

        Args:
            entity_type: Neo4j label
            entities: List of entity data dicts
            batch_size: Number of entities per batch transaction

        Returns:
            Dict with counts: {"total": int, "successful": int, "failed": int}
        """
        # Write debug to file since stdout isn't captured
        import os
        debug_file = "/tmp/neo4j_upsert_debug.log"
        with open(debug_file, "a") as f:
            f.write(f"\n[NEO4J_BATCH] METHOD CALLED: entity_type={entity_type}\n")
            f.write(f"[NEO4J_BATCH] entities parameter type: {type(entities)}\n")
            f.write(f"[NEO4J_BATCH] entities has __len__: {hasattr(entities, '__len__')}\n")
            try:
                f.write(f"[NEO4J_BATCH] len(entities): {len(entities)}\n")
            except Exception as e:
                f.write(f"[NEO4J_BATCH] ERROR calling len(entities): {e}\n")
            f.flush()

        total = len(entities)
        successful = 0
        failed = 0

        with open(debug_file, "a") as f:
            f.write(f"[NEO4J_BATCH] total={total}, batch_size={batch_size}\n")
            f.flush()

        print(f"[NEO4J_BATCH] Starting batch upsert: entity_type={entity_type}, total={total}, batch_size={batch_size}")
        logger.info(
            "Starting batch upsert",
            entity_type=entity_type,
            total=total,
            batch_size=batch_size
        )

        # Debug: About to start for loop
        with open(debug_file, "a") as f:
            f.write(f"[NEO4J_BATCH] About to start for loop, total={total}, batch_size={batch_size}\n")
            f.write(f"[NEO4J_BATCH] range(0, {total}, {batch_size}) will produce: {list(range(0, total, batch_size))}\n")
            f.flush()

        # Process in batches
        for i in range(0, total, batch_size):
            with open(debug_file, "a") as f:
                f.write(f"[NEO4J_BATCH] ENTERED for loop iteration, i={i}\n")
                f.write(f"[NEO4J_BATCH] entities type: {type(entities)}, len: {len(entities) if hasattr(entities, '__len__') else 'N/A'}\n")
                f.flush()

            batch = entities[i:i + batch_size]

            with open(debug_file, "a") as f:
                f.write(f"[NEO4J_BATCH] Created batch slice, batch type: {type(batch)}, len: {len(batch) if hasattr(batch, '__len__') else 'N/A'}\n")
                f.write(f"[NEO4J_BATCH] About to print batch info...\n")
                f.flush()

            try:
                print(f"[NEO4J_BATCH] Processing batch {i // batch_size + 1}, size={len(batch)}")
                with open(debug_file, "a") as f:
                    f.write(f"[NEO4J_BATCH] Print succeeded\n")
                    f.flush()
            except Exception as e:
                with open(debug_file, "a") as f:
                    f.write(f"[NEO4J_BATCH] EXCEPTION during print: {e}\n")
                    f.write(f"[NEO4J_BATCH] Exception type: {type(e)}\n")
                    f.flush()
                raise

            try:
                print(f"[NEO4J_BATCH] Opening Neo4j session to database={self.database}")
                with self.driver.session(database=self.database) as session:
                    # Use transaction for batch
                    print(f"[NEO4J_BATCH] Starting transaction")
                    with session.begin_transaction() as tx:
                        for j, entity_data in enumerate(batch):
                            try:
                                id_field = self.ENTITY_ID_FIELDS.get(entity_type)
                                unique_id = entity_data.get(id_field)

                                if not unique_id:
                                    print(f"[NEO4J_BATCH] ERROR: Missing {id_field} for entity {j}")
                                    failed += 1
                                    continue

                                print(f"[NEO4J_BATCH] Upserting entity {j+1}/{len(batch)}: {id_field}={unique_id}")

                                query = f"""
                                MERGE (n:{entity_type} {{{id_field}: $unique_id}})
                                SET n += $properties
                                RETURN n
                                """

                                result = tx.run(
                                    query,
                                    unique_id=unique_id,
                                    properties=entity_data
                                )

                                if result.single():
                                    successful += 1
                                    print(f"[NEO4J_BATCH] SUCCESS: Entity {unique_id} upserted")
                                else:
                                    failed += 1
                                    print(f"[NEO4J_BATCH] WARNING: No result for {unique_id}")

                            except Exception as e:
                                error_msg = f"Failed to upsert entity in batch: {e}"
                                print(f"[NEO4J_BATCH] EXCEPTION in entity: {error_msg}")
                                import traceback
                                print(f"[NEO4J_BATCH] Traceback: {traceback.format_exc()}")
                                logger.error(error_msg)
                                failed += 1

                        print(f"[NEO4J_BATCH] Committing transaction")
                        tx.commit()
                        print(f"[NEO4J_BATCH] Transaction committed successfully")

                print(f"[NEO4J_BATCH] Completed batch {i // batch_size + 1}: successful={successful}, failed={failed}")
                logger.info(
                    f"Completed batch {i // batch_size + 1}",
                    batch_entities=len(batch),
                    successful=successful,
                    failed=failed
                )

            except Exception as e:
                error_msg = f"Batch transaction failed: {e}"
                print(f"[NEO4J_BATCH] EXCEPTION in batch: {error_msg}")
                import traceback
                print(f"[NEO4J_BATCH] Traceback: {traceback.format_exc()}")

                with open(debug_file, "a") as f:
                    f.write(f"[NEO4J_BATCH] BATCH EXCEPTION: {error_msg}\n")
                    f.write(f"[NEO4J_BATCH] Exception type: {type(e).__name__}\n")
                    f.write(f"[NEO4J_BATCH] Full traceback:\n{traceback.format_exc()}\n")
                    f.flush()

                logger.error(error_msg)
                failed += len(batch)

        print(f"[NEO4J_BATCH] Batch upsert complete: total={total}, successful={successful}, failed={failed}")
        logger.info(
            "Batch upsert complete",
            entity_type=entity_type,
            total=total,
            successful=successful,
            failed=failed
        )

        return {
            "total": total,
            "successful": successful,
            "failed": failed
        }

    def create_constraints(self) -> Dict[str, bool]:
        """
        Create unique constraints for all Bundestag entity types.

        Should be run once during setup.

        Returns:
            Dict mapping entity type to success status
        """
        results = {}

        with self.driver.session(database=self.database) as session:
            for entity_type, id_field in self.ENTITY_ID_FIELDS.items():
                try:
                    constraint_name = f"{entity_type.lower()}_{id_field}_unique"

                    query = f"""
                    CREATE CONSTRAINT {constraint_name} IF NOT EXISTS
                    FOR (n:{entity_type})
                    REQUIRE n.{id_field} IS UNIQUE
                    """

                    session.run(query)
                    results[entity_type] = True

                    logger.info(
                        "Created constraint",
                        entity_type=entity_type,
                        constraint_name=constraint_name
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to create constraint for {entity_type}: {e}"
                    )
                    results[entity_type] = False

        return results

    def create_indexes(self) -> Dict[str, bool]:
        """
        Create indexes for commonly queried fields.

        Returns:
            Dict mapping index name to success status
        """
        indexes = [
            ("BundestagPerson", "person_name"),
            ("BundestagPerson", "fraktion"),
            ("BundestagPerson", "funktion"),  # NEW: Index for role type (MdB, etc.)
            ("BundestagPerson", "typ"),  # NEW: Index for entity type
            ("BundestagPerson", "ressort"),  # NEW: Index for ministry assignments
            ("BundestagPerson", "datum"),  # NEW: Index for snapshot date
            ("Vorgang", "wahlperiode"),
            ("Vorgang", "vorgangstyp"),
            ("Drucksache", "wahlperiode"),
            ("Drucksache", "dokumentart"),
            ("Plenarprotokoll", "wahlperiode"),
            ("Plenarprotokoll", "datum"),
            ("Wahlperiode", "wahlperiode_nummer"),
            ("Fraktion", "fraktion_id"),
            ("Fraktion", "fraktion_name"),
            ("Fraktion", "status"),
            ("Fraktion", "party_family"),
            ("Vorgang", "vorgang_id"),
            ("Vorgang", "wahlperiode"),
            ("Vorgang", "vorgangstyp"),
            ("Vorgang", "beratungsstand"),
            ("Vorgang", "datum"),
            ("Deskriptor", "deskriptor_id"),
            ("Deskriptor", "name"),
            ("Deskriptor", "typ"),
            ("Sachgebiet", "sachgebiet_name"),
            # Aktivitaet indexes (Flow 5f)
            ("Aktivitaet", "aktivitaetsart"),
            ("Aktivitaet", "person_id"),
            ("Aktivitaet", "wahlperiode"),
            ("Aktivitaet", "datum"),
            ("Aktivitaet", "dokumentart"),
        ]

        results = {}

        with self.driver.session(database=self.database) as session:
            for entity_type, field_name in indexes:
                try:
                    index_name = f"{entity_type.lower()}_{field_name}_idx"

                    query = f"""
                    CREATE INDEX {index_name} IF NOT EXISTS
                    FOR (n:{entity_type})
                    ON (n.{field_name})
                    """

                    session.run(query)
                    results[index_name] = True

                    logger.info(
                        "Created index",
                        entity_type=entity_type,
                        field_name=field_name,
                        index_name=index_name
                    )

                except Exception as e:
                    logger.error(f"Failed to create index {index_name}: {e}")
                    results[index_name] = False

        return results

    def get_entity_count(self, entity_type: str) -> int:
        """
        Get count of entities of a specific type.

        Args:
            entity_type: Neo4j label

        Returns:
            Count of entities
        """
        try:
            with self.driver.session(database=self.database) as session:
                query = f"MATCH (n:{entity_type}) RETURN count(n) as count"
                result = session.run(query)
                return result.single()["count"]
        except Exception as e:
            logger.error(f"Failed to get entity count: {e}")
            return 0
