"""
Setup Neo4j constraints and indexes for Bundestag entities.

Run this script once to create unique constraints and performance indexes
for all 8 Bundestag entity types.
"""

import os
from neo4j import GraphDatabase
from src.flows.bundestag_common.neo4j_upsert import Neo4jUpsertManager
import structlog

logger = structlog.get_logger()


def setup_neo4j_schema():
    """Create all constraints and indexes for Bundestag entities."""

    # Get Neo4j connection details from environment
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password123")
    neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")

    logger.info(
        "Setting up Neo4j schema",
        uri=neo4j_uri,
        database=neo4j_database
    )

    # Create driver
    driver = GraphDatabase.driver(
        neo4j_uri,
        auth=(neo4j_username, neo4j_password)
    )

    try:
        # Create upsert manager
        upsert_manager = Neo4jUpsertManager(
            driver=driver,
            database=neo4j_database
        )

        # Create constraints
        logger.info("Creating unique constraints...")
        constraint_results = upsert_manager.create_constraints()

        for entity_type, success in constraint_results.items():
            if success:
                logger.info(f"✅ Constraint created for {entity_type}")
            else:
                logger.error(f"❌ Failed to create constraint for {entity_type}")

        # Create indexes
        logger.info("Creating indexes...")
        index_results = upsert_manager.create_indexes()

        for index_name, success in index_results.items():
            if success:
                logger.info(f"✅ Index created: {index_name}")
            else:
                logger.error(f"❌ Failed to create index: {index_name}")

        # Summary
        constraints_created = sum(1 for v in constraint_results.values() if v)
        indexes_created = sum(1 for v in index_results.values() if v)

        logger.info(
            "Schema setup complete",
            constraints_created=constraints_created,
            total_constraints=len(constraint_results),
            indexes_created=indexes_created,
            total_indexes=len(index_results)
        )

        return constraint_results, index_results

    finally:
        driver.close()


if __name__ == "__main__":
    setup_neo4j_schema()
