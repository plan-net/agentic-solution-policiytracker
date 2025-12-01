#!/usr/bin/env python3
"""
Delete Phase 4 nodes from Neo4j before re-running updated scripts.

This script removes:
- 21 Wahlperiode nodes
- 16 Fraktion nodes
- 124 ACTIVE_IN relationships
- 2 SUCCESSOR_OF relationships
"""

import os
from neo4j import GraphDatabase

# Get Neo4j connection from environment
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "politicalmonitoring.v3")

print("=" * 60)
print("Phase 4 Node Deletion Script")
print("=" * 60)
print(f"\n🔗 Connecting to Neo4j: {NEO4J_URI}")
print(f"📦 Database: {NEO4J_DATABASE}\n")

# Initialize Neo4j connection
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

try:
    with driver.session(database=NEO4J_DATABASE) as session:
        # Count existing nodes before deletion
        print("📊 Counting existing Phase 4 nodes...")

        result = session.run("MATCH (w:Wahlperiode) RETURN count(w) AS count")
        wahlperiode_count = result.single()["count"]
        print(f"   - Wahlperiode nodes: {wahlperiode_count}")

        result = session.run("MATCH (f:Fraktion) RETURN count(f) AS count")
        fraktion_count = result.single()["count"]
        print(f"   - Fraktion nodes: {fraktion_count}")

        result = session.run("MATCH ()-[r:ACTIVE_IN]->() RETURN count(r) AS count")
        active_in_count = result.single()["count"]
        print(f"   - ACTIVE_IN relationships: {active_in_count}")

        result = session.run("MATCH ()-[r:SUCCESSOR_OF]->() RETURN count(r) AS count")
        successor_of_count = result.single()["count"]
        print(f"   - SUCCESSOR_OF relationships: {successor_of_count}\n")

        if wahlperiode_count == 0 and fraktion_count == 0:
            print("✅ No Phase 4 nodes found. Nothing to delete.\n")
        else:
            # Delete Wahlperiode nodes and relationships
            print("🗑️  Deleting Wahlperiode nodes and relationships...")
            result = session.run("MATCH (w:Wahlperiode) DETACH DELETE w RETURN count(w) AS deleted")
            deleted_wahlperiode = result.single()["deleted"]
            print(f"   ✅ Deleted {deleted_wahlperiode} Wahlperiode nodes\n")

            # Delete Fraktion nodes and relationships
            print("🗑️  Deleting Fraktion nodes and relationships...")
            result = session.run("MATCH (f:Fraktion) DETACH DELETE f RETURN count(f) AS deleted")
            deleted_fraktion = result.single()["deleted"]
            print(f"   ✅ Deleted {deleted_fraktion} Fraktion nodes\n")

            # Verify deletion
            print("🔍 Verifying deletion...")
            result = session.run("MATCH (w:Wahlperiode) RETURN count(w) AS count")
            remaining_wahlperiode = result.single()["count"]

            result = session.run("MATCH (f:Fraktion) RETURN count(f) AS count")
            remaining_fraktion = result.single()["count"]

            if remaining_wahlperiode == 0 and remaining_fraktion == 0:
                print("   ✅ All Phase 4 nodes successfully deleted\n")
            else:
                print(f"   ⚠️  Warning: {remaining_wahlperiode} Wahlperiode and {remaining_fraktion} Fraktion nodes still remain\n")

        print("=" * 60)
        print("✨ Phase 4 Node Deletion Complete!")
        print("=" * 60)
        print("\n📋 Next Steps:")
        print("   1. Run: uv run python src/flows/bundestag_wahlperiode/load_wahlperioden.py")
        print("   2. Run: uv run python src/flows/bundestag_fraktion/load_fraktionen.py")
        print("   3. Verify nodes in Neo4j Browser: http://localhost:7474\n")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

finally:
    driver.close()
