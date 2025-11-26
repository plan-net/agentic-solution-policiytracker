#!/usr/bin/env python3
"""
Verify Graphiti Search Compatibility for Phase 4 Nodes.

This script checks that Wahlperiode and Fraktion nodes have:
1. :Entity label (in addition to domain label)
2. uuid property
3. name property
4. name_embedding property (1536-dim vector)
5. group_id property
6. created_at property
"""

import os
from neo4j import GraphDatabase

# Get Neo4j connection from environment
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "politicalmonitoring.v3")

print("=" * 70)
print("Graphiti Search Compatibility Verification")
print("=" * 70)
print(f"\n🔗 Connecting to Neo4j: {NEO4J_URI}")
print(f"📦 Database: {NEO4J_DATABASE}\n")

# Initialize Neo4j connection
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

try:
    with driver.session(database=NEO4J_DATABASE) as session:

        # 1. Verify Wahlperiode nodes
        print("=" * 70)
        print("1️⃣  Verifying Wahlperiode Nodes")
        print("=" * 70)

        # Count total Wahlperiode nodes
        result = session.run("MATCH (w:Wahlperiode) RETURN count(w) AS count")
        total_wahlperiode = result.single()["count"]
        print(f"\n📊 Total Wahlperiode nodes: {total_wahlperiode}")

        # Count nodes with :Entity label
        result = session.run("MATCH (w:Entity:Wahlperiode) RETURN count(w) AS count")
        entity_label_count = result.single()["count"]
        print(f"✓ Nodes with :Entity label: {entity_label_count}/{total_wahlperiode}")

        # Check required properties on sample node
        result = session.run("""
            MATCH (w:Entity:Wahlperiode)
            WHERE w.wahlperiode_nummer = 20
            RETURN
                w.uuid AS uuid,
                w.name AS name,
                size(w.name_embedding) AS embedding_dim,
                w.group_id AS group_id,
                w.created_at AS created_at,
                labels(w) AS labels
        """)
        wp20 = result.single()

        if wp20:
            print(f"\n📋 Sample Node (Wahlperiode 20):")
            print(f"   - Labels: {wp20['labels']}")
            print(f"   - UUID: {wp20['uuid']}")
            print(f"   - Name: {wp20['name']}")
            print(f"   - Embedding Dim: {wp20['embedding_dim']}")
            print(f"   - Group ID: {wp20['group_id']}")
            print(f"   - Created At: {wp20['created_at']}")

            # Validation checks
            checks_passed = 0
            checks_total = 6

            if 'Entity' in wp20['labels'] and 'Wahlperiode' in wp20['labels']:
                print(f"\n   ✅ Has both :Entity and :Wahlperiode labels")
                checks_passed += 1
            else:
                print(f"\n   ❌ Missing labels")

            if wp20['uuid']:
                print(f"   ✅ Has uuid property")
                checks_passed += 1
            else:
                print(f"   ❌ Missing uuid")

            if wp20['name']:
                print(f"   ✅ Has name property")
                checks_passed += 1
            else:
                print(f"   ❌ Missing name")

            if wp20['embedding_dim'] == 1536:
                print(f"   ✅ Has valid name_embedding (1536 dimensions)")
                checks_passed += 1
            else:
                print(f"   ❌ Invalid embedding dimension: {wp20['embedding_dim']}")

            if wp20['group_id']:
                print(f"   ✅ Has group_id property")
                checks_passed += 1
            else:
                print(f"   ❌ Missing group_id")

            if wp20['created_at']:
                print(f"   ✅ Has created_at property")
                checks_passed += 1
            else:
                print(f"   ❌ Missing created_at")

            print(f"\n   Validation: {checks_passed}/{checks_total} checks passed")

        # 2. Verify Fraktion nodes
        print("\n" + "=" * 70)
        print("2️⃣  Verifying Fraktion Nodes")
        print("=" * 70)

        # Count total Fraktion nodes
        result = session.run("MATCH (f:Fraktion) RETURN count(f) AS count")
        total_fraktion = result.single()["count"]
        print(f"\n📊 Total Fraktion nodes: {total_fraktion}")

        # Count nodes with :Entity label
        result = session.run("MATCH (f:Entity:Fraktion) RETURN count(f) AS count")
        entity_label_count = result.single()["count"]
        print(f"✓ Nodes with :Entity label: {entity_label_count}/{total_fraktion}")

        # Check required properties on sample node
        result = session.run("""
            MATCH (f:Entity:Fraktion)
            WHERE f.fraktion_id = 'spd'
            RETURN
                f.uuid AS uuid,
                f.name AS name,
                size(f.name_embedding) AS embedding_dim,
                f.group_id AS group_id,
                f.created_at AS created_at,
                labels(f) AS labels
        """)
        spd = result.single()

        if spd:
            print(f"\n📋 Sample Node (SPD):")
            print(f"   - Labels: {spd['labels']}")
            print(f"   - UUID: {spd['uuid']}")
            print(f"   - Name: {spd['name']}")
            print(f"   - Embedding Dim: {spd['embedding_dim']}")
            print(f"   - Group ID: {spd['group_id']}")
            print(f"   - Created At: {spd['created_at']}")

            # Validation checks
            checks_passed = 0
            checks_total = 6

            if 'Entity' in spd['labels'] and 'Fraktion' in spd['labels']:
                print(f"\n   ✅ Has both :Entity and :Fraktion labels")
                checks_passed += 1
            else:
                print(f"\n   ❌ Missing labels")

            if spd['uuid']:
                print(f"   ✅ Has uuid property")
                checks_passed += 1
            else:
                print(f"   ❌ Missing uuid")

            if spd['name']:
                print(f"   ✅ Has name property")
                checks_passed += 1
            else:
                print(f"   ❌ Missing name")

            if spd['embedding_dim'] == 1536:
                print(f"   ✅ Has valid name_embedding (1536 dimensions)")
                checks_passed += 1
            else:
                print(f"   ❌ Invalid embedding dimension: {spd['embedding_dim']}")

            if spd['group_id']:
                print(f"   ✅ Has group_id property")
                checks_passed += 1
            else:
                print(f"   ❌ Missing group_id")

            if spd['created_at']:
                print(f"   ✅ Has created_at property")
                checks_passed += 1
            else:
                print(f"   ❌ Missing created_at")

            print(f"\n   Validation: {checks_passed}/{checks_total} checks passed")

        # 3. Summary
        print("\n" + "=" * 70)
        print("3️⃣  Summary")
        print("=" * 70)

        all_good = True

        if entity_label_count != total_wahlperiode:
            print(f"\n❌ Not all Wahlperiode nodes have :Entity label ({entity_label_count}/{total_wahlperiode})")
            all_good = False
        else:
            print(f"\n✅ All {total_wahlperiode} Wahlperiode nodes have :Entity label")

        # Count Fraktion with Entity label
        result = session.run("MATCH (f:Entity:Fraktion) RETURN count(f) AS count")
        fraktion_entity_count = result.single()["count"]

        if fraktion_entity_count != total_fraktion:
            print(f"❌ Not all Fraktion nodes have :Entity label ({fraktion_entity_count}/{total_fraktion})")
            all_good = False
        else:
            print(f"✅ All {total_fraktion} Fraktion nodes have :Entity label")

        # Check relationships
        result = session.run("MATCH ()-[r:ACTIVE_IN]->() RETURN count(r) AS count")
        active_in_count = result.single()["count"]
        print(f"✅ {active_in_count} ACTIVE_IN relationships created")

        result = session.run("MATCH ()-[r:SUCCESSOR_OF]->() RETURN count(r) AS count")
        successor_of_count = result.single()["count"]
        print(f"✅ {successor_of_count} SUCCESSOR_OF relationships created")

        # Final verdict
        print("\n" + "=" * 70)
        if all_good and wp20 and spd and checks_passed == checks_total:
            print("✨ SUCCESS! All Phase 4 nodes are Graphiti-compatible")
        else:
            print("⚠️  WARNING: Some issues detected (see above)")
        print("=" * 70)

        print("\n🔍 Test Queries:")
        print("   Neo4j Browser: http://localhost:7474")
        print("   Query 1: MATCH (n:Entity) RETURN count(n)  -- Should return 37")
        print("   Query 2: MATCH (w:Entity:Wahlperiode) RETURN w.name, size(w.name_embedding)")
        print("   Query 3: MATCH (f:Entity:Fraktion) RETURN f.name, size(f.name_embedding)")
        print("   Query 4: MATCH (f:Entity:Fraktion)-[r:ACTIVE_IN]->(w:Entity:Wahlperiode) RETURN count(r)")
        print("\n")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

finally:
    driver.close()
