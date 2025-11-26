#!/usr/bin/env python3
"""
Verify Phase 4 nodes match expected schema structure.

This script checks:
1. Wahlperiode nodes have Pydantic model fields from political_schema_v5
2. Fraktion nodes have historical reference structure
3. Relationships are intact
"""

import os
from neo4j import GraphDatabase

# Get Neo4j connection from environment
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "politicalmonitoring.v3")

print("=" * 60)
print("Phase 4 Schema Verification")
print("=" * 60)
print(f"\n🔗 Connecting to Neo4j: {NEO4J_URI}")
print(f"📦 Database: {NEO4J_DATABASE}\n")

# Initialize Neo4j connection
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

try:
    with driver.session(database=NEO4J_DATABASE) as session:
        # 1. Verify Wahlperiode count and structure
        print("1️⃣  Verifying Wahlperiode nodes...")
        result = session.run("MATCH (w:Wahlperiode) RETURN count(w) AS count")
        wahlperiode_count = result.single()["count"]
        print(f"   ✅ Found {wahlperiode_count} Wahlperiode nodes")

        # Check Pydantic model fields
        result = session.run("""
            MATCH (w:Wahlperiode)
            WHERE w.wahlperiode_nummer = 20
            RETURN w
        """)
        wp20 = result.single()["w"]

        pydantic_fields = ["von", "bis", "bundeskanzler", "koalition", "sitze_gesamt", "wahltag", "besonderheiten"]
        missing_fields = [field for field in pydantic_fields if field not in wp20]

        if missing_fields:
            print(f"   ⚠️  Missing Pydantic fields: {missing_fields}")
        else:
            print(f"   ✅ All Pydantic model fields present")

        print(f"   📋 Sample Wahlperiode 20 properties:")
        for field in ["wahlperiode_nummer", "von", "bis", "bundeskanzler", "koalition", "sitze_gesamt"]:
            if field in wp20:
                print(f"      - {field}: {wp20[field]}")

        # 2. Verify Fraktion count and structure
        print("\n2️⃣  Verifying Fraktion nodes...")
        result = session.run("MATCH (f:Fraktion) RETURN count(f) AS count")
        fraktion_count = result.single()["count"]
        print(f"   ✅ Found {fraktion_count} Fraktion nodes")

        # Check historical reference structure
        result = session.run("""
            MATCH (f:Fraktion)
            WHERE f.fraktion_id = 'spd'
            RETURN f
        """)
        spd = result.single()["f"]

        historical_fields = ["fraktion_id", "fraktion_name", "founding_date", "active_wahlperioden"]
        missing_fields = [field for field in historical_fields if field not in spd]

        if missing_fields:
            print(f"   ⚠️  Missing historical reference fields: {missing_fields}")
        else:
            print(f"   ✅ All historical reference fields present")

        print(f"   📋 Sample Fraktion (SPD) properties:")
        for field in ["fraktion_id", "fraktion_name", "founding_date", "active_wahlperioden", "color"]:
            if field in spd:
                value = spd[field]
                if field == "active_wahlperioden" and isinstance(value, list):
                    print(f"      - {field}: [{len(value)} wahlperioden: {value[:5]}...]")
                else:
                    print(f"      - {field}: {value}")

        # 3. Verify relationships
        print("\n3️⃣  Verifying relationships...")

        # ACTIVE_IN relationships
        result = session.run("MATCH ()-[r:ACTIVE_IN]->() RETURN count(r) AS count")
        active_in_count = result.single()["count"]
        print(f"   ✅ Found {active_in_count} ACTIVE_IN relationships (expected: 124)")

        # SUCCESSOR_OF relationships
        result = session.run("MATCH ()-[r:SUCCESSOR_OF]->() RETURN count(r) AS count")
        successor_of_count = result.single()["count"]
        print(f"   ✅ Found {successor_of_count} SUCCESSOR_OF relationships (expected: 2)")

        # Sample ACTIVE_IN relationship
        result = session.run("""
            MATCH (f:Fraktion {fraktion_id: 'spd'})-[r:ACTIVE_IN]->(w:Wahlperiode)
            RETURN w.wahlperiode_nummer AS wp_num
            ORDER BY wp_num
            LIMIT 5
        """)
        wp_nums = [record["wp_num"] for record in result]
        print(f"   📋 Sample: SPD ACTIVE_IN wahlperioden: {wp_nums}...")

        # 4. Verify Graphiti compatibility
        print("\n4️⃣  Verifying Graphiti compatibility...")

        # Check if Wahlperiode has both old and Pydantic fields
        result = session.run("""
            MATCH (w:Wahlperiode)
            WHERE w.wahlperiode_nummer = 20
            RETURN
                w.von IS NOT NULL AS has_von,
                w.bis IS NOT NULL AS has_bis,
                w.start_date IS NOT NULL AS has_start_date,
                w.end_date IS NOT NULL AS has_end_date
        """)
        compat = result.single()

        if compat["has_von"] and compat["has_bis"]:
            print(f"   ✅ Pydantic fields (von, bis) present")
        else:
            print(f"   ❌ Missing Pydantic fields")

        if compat["has_start_date"] and compat["has_end_date"]:
            print(f"   ✅ Compatibility fields (start_date, end_date) present")
        else:
            print(f"   ⚠️  Missing compatibility fields")

        # 5. Final validation
        print("\n5️⃣  Final validation...")
        all_good = True

        if wahlperiode_count != 21:
            print(f"   ❌ Expected 21 Wahlperiode nodes, found {wahlperiode_count}")
            all_good = False

        if fraktion_count != 16:
            print(f"   ❌ Expected 16 Fraktion nodes, found {fraktion_count}")
            all_good = False

        if active_in_count != 124:
            print(f"   ⚠️  Expected 124 ACTIVE_IN relationships, found {active_in_count}")
            all_good = False

        if successor_of_count != 2:
            print(f"   ⚠️  Expected 2 SUCCESSOR_OF relationships, found {successor_of_count}")
            all_good = False

        if missing_fields:
            print(f"   ❌ Missing required fields in schema")
            all_good = False

        if all_good:
            print(f"   ✅ All validations passed!")
        else:
            print(f"   ⚠️  Some validations failed (see above)")

        print("\n" + "=" * 60)
        if all_good:
            print("✨ SUCCESS! Phase 4 schema verified (Graphiti-Compatible)")
        else:
            print("⚠️  WARNING: Phase 4 schema has issues (see above)")
        print("=" * 60)
        print("\n📋 Summary:")
        print(f"   - Wahlperiode nodes: {wahlperiode_count} (Pydantic validated)")
        print(f"   - Fraktion nodes: {fraktion_count} (Historical reference)")
        print(f"   - ACTIVE_IN relationships: {active_in_count}")
        print(f"   - SUCCESSOR_OF relationships: {successor_of_count}")
        print(f"   - Database: {NEO4J_DATABASE}")
        print("\n🔍 View in Neo4j Browser: http://localhost:7474")
        print("   Query: MATCH (w:Wahlperiode) RETURN w ORDER BY w.wahlperiode_nummer")
        print("   Query: MATCH (f:Fraktion)-[r:ACTIVE_IN]->(w:Wahlperiode) RETURN f, r, w LIMIT 50\n")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

finally:
    driver.close()
