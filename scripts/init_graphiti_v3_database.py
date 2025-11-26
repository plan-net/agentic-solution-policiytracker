"""
Initialize Graphiti indices and constraints in politicalmonitoring.v3 database.
Uses Neo4j driver directly since Graphiti doesn't expose database parameter.
"""

import os
from neo4j import GraphDatabase


def init_graphiti():
    """Initialize Graphiti indices and constraints in the new database."""

    # Get connection details from environment
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password123")
    neo4j_database = os.getenv("NEO4J_DATABASE", "politicalmonitoring.v3")

    print(f"🔧 Initializing Graphiti indices in database: {neo4j_database}")
    print(f"   URI: {neo4j_uri}")

    # Connect to Neo4j
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    # Create indices and constraints
    with driver.session(database=neo4j_database) as session:
        print("📊 Creating Graphiti indices and constraints...")

        # 1. Unique constraint on Entity.uuid
        print("   - Creating unique constraint on Entity.uuid...")
        session.run(
            "CREATE CONSTRAINT entity_uuid_unique IF NOT EXISTS "
            "FOR (e:Entity) REQUIRE e.uuid IS UNIQUE"
        )

        # 2. Index on Entity.group_id
        print("   - Creating index on Entity.group_id...")
        session.run(
            "CREATE INDEX entity_group_id_index IF NOT EXISTS "
            "FOR (e:Entity) ON (e.group_id)"
        )

        # 3. Index on Entity.name for fulltext search
        print("   - Creating index on Entity.name...")
        session.run(
            "CREATE INDEX entity_name_index IF NOT EXISTS "
            "FOR (e:Entity) ON (e.name)"
        )

        # 4. Vector index on Entity.name_embedding (for semantic search)
        print("   - Creating vector index on Entity.name_embedding...")
        session.run(
            """
            CREATE VECTOR INDEX entity_name_embedding_index IF NOT EXISTS
            FOR (e:Entity) ON (e.name_embedding)
            OPTIONS {indexConfig: {
                `vector.dimensions`: 1536,
                `vector.similarity_function`: 'cosine'
            }}
            """
        )

        # 5. Episodic node constraints
        print("   - Creating Episodic node constraints...")
        session.run(
            "CREATE CONSTRAINT episodic_uuid_unique IF NOT EXISTS "
            "FOR (ep:Episodic) REQUIRE ep.uuid IS UNIQUE"
        )

        # 6. Index on Episodic.group_id
        session.run(
            "CREATE INDEX episodic_group_id_index IF NOT EXISTS "
            "FOR (ep:Episodic) ON (ep.group_id)"
        )

        print("✅ Graphiti initialization complete!")
        print("\n📋 Created indices and constraints:")
        print("   ✓ Unique constraint on Entity.uuid")
        print("   ✓ Index on Entity.group_id")
        print("   ✓ Index on Entity.name")
        print("   ✓ Vector index on Entity.name_embedding (1536 dims, cosine)")
        print("   ✓ Unique constraint on Episodic.uuid")
        print("   ✓ Index on Episodic.group_id")
        print(f"\n🎯 Database '{neo4j_database}' is ready for Graphiti operations!")

    driver.close()
    return True


if __name__ == "__main__":
    init_graphiti()
