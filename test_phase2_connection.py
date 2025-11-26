"""Test database connection to politicalmonitoring.v3"""
import os
from neo4j import GraphDatabase

# Get connection details from environment
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "politicalmonitoring.v3")

print(f"🔌 Testing connection to {NEO4J_DATABASE}...")

try:
    # Create driver
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    # Test connection
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run("RETURN 'Connection successful!' AS message")
        record = result.single()
        print(f"✅ {record['message']}")

        # Check CanonicalEntity node count
        result = session.run("MATCH (ce:CanonicalEntity) RETURN count(ce) AS count")
        canonical_count = result.single()["count"]
        print(f"📊 CanonicalEntity nodes: {canonical_count}")

        # Check EntityAlias node count
        result = session.run("MATCH (ea:EntityAlias) RETURN count(ea) AS count")
        alias_count = result.single()["count"]
        print(f"📊 EntityAlias nodes: {alias_count}")

        # Check Phase 2 indexes
        result = session.run("""
            SHOW INDEXES
            WHERE name STARTS WITH 'canonical_entity' OR name STARTS WITH 'entity_alias'
        """)
        indexes = list(result)
        print(f"📊 Phase 2 indexes: {len(indexes)}")
        for idx in indexes:
            print(f"  - {idx['name']}: {idx['state']}")

    driver.close()
    print("✅ Phase 3 Verification Complete!")

except Exception as e:
    print(f"❌ Connection failed: {e}")
    exit(1)
