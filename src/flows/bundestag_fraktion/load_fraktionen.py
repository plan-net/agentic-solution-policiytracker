#!/usr/bin/env python3
"""
Simple script to load Bundestag Fraktion reference data into Neo4j.

Run with: python src/flows/bundestag_fraktion/load_fraktionen.py
Or via just: just load-fraktionen
"""

import sys
import os
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from neo4j import GraphDatabase
from src.flows.bundestag_fraktion.fraktion_data import FRAKTION_REFERENCE_DATA
from src.flows.bundestag_common.neo4j_upsert import Neo4jUpsertManager


def map_fraktion_to_entity(frak_data: Dict[str, Any]) -> Dict[str, Any]:
    """Map fraktion reference data to entity structure."""

    entity = {
        "fraktion_id": frak_data["fraktion_id"],
        "fraktion_name": frak_data["fraktion_name"],
        "full_name": frak_data["full_name"],
        "abbreviation": frak_data["abbreviation"],
        "founding_date": frak_data.get("founding_date"),
        "dissolution_date": frak_data.get("dissolution_date"),
        "status": frak_data.get("status", "active"),
        "fraktion_type": frak_data.get("fraktion_type", "fraktion"),
        "party_family": frak_data.get("party_family", ""),
        "active_wahlperioden": frak_data.get("active_wahlperioden", []),
        "description": frak_data.get("description", ""),
    }

    return entity


def create_active_in_relationships(driver, database: str) -> Dict[str, int]:
    """Create ACTIVE_IN relationships between Fraktion and Wahlperiode nodes."""
    query = """
    MATCH (f:Fraktion)
    WHERE f.active_wahlperioden IS NOT NULL AND size(f.active_wahlperioden) > 0
    UNWIND f.active_wahlperioden AS wp_num
    MATCH (w:Wahlperiode {wahlperiode_nummer: wp_num})
    MERGE (f)-[:ACTIVE_IN]->(w)
    RETURN count(*) as relationships_created
    """

    try:
        with driver.session(database=database) as session:
            result = session.run(query)
            record = result.single()
            created = record["relationships_created"] if record else 0
            return {"created": created}
    except Exception as e:
        print(f"❌ Failed to create ACTIVE_IN relationships: {e}")
        return {"created": 0, "error": str(e)}


def create_member_of_relationships(driver, database: str) -> Dict[str, int]:
    """Create MEMBER_OF relationships between BundestagPerson and Fraktion nodes."""
    query = """
    MATCH (p:BundestagPerson)
    WHERE p.current_fraktion IS NOT NULL AND size(p.current_fraktion) > 0
    UNWIND p.current_fraktion AS frak_name
    MATCH (f:Fraktion {fraktion_name: frak_name})
    MERGE (p)-[r:MEMBER_OF]->(f)
    ON CREATE SET
        r.from_date = p.datum,
        r.wahlperiode = CASE WHEN size(p.wahlperioden) > 0 THEN p.wahlperioden[0] ELSE null END
    RETURN count(*) as relationships_created
    """

    try:
        with driver.session(database=database) as session:
            result = session.run(query)
            record = result.single()
            created = record["relationships_created"] if record else 0
            return {"created": created}
    except Exception as e:
        print(f"❌ Failed to create MEMBER_OF relationships: {e}")
        return {"created": 0, "error": str(e)}


def create_successor_relationships(driver, database: str) -> Dict[str, int]:
    """Create SUCCESSOR_OF relationships between historical fraktionen."""
    # Define successor relationships
    successors = [
        ("die_linke", "pds"),  # DIE LINKE succeeded PDS
        ("pds", "kpd"),  # PDS as conceptual successor to KPD (historically complex)
    ]

    created_count = 0

    try:
        with driver.session(database=database) as session:
            for successor_id, predecessor_id in successors:
                query = """
                MATCH (successor:Fraktion {fraktion_id: $successor_id})
                MATCH (predecessor:Fraktion {fraktion_id: $predecessor_id})
                MERGE (successor)-[:SUCCESSOR_OF]->(predecessor)
                RETURN count(*) as created
                """
                result = session.run(query, successor_id=successor_id, predecessor_id=predecessor_id)
                record = result.single()
                if record:
                    created_count += record["created"]

        return {"created": created_count}
    except Exception as e:
        print(f"❌ Failed to create SUCCESSOR_OF relationships: {e}")
        return {"created": 0, "error": str(e)}


def main():
    """Main execution function."""
    # Get Neo4j connection from environment or use defaults
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password123")
    neo4j_database = os.getenv("NEO4J_DATABASE", "politicamonitoring.v2")

    print("=" * 60)
    print("Bundestag Fraktion Loader")
    print("=" * 60)
    print(f"\n📊 Loading {len(FRAKTION_REFERENCE_DATA)} fraktionen...")
    print(f"🔗 Connecting to Neo4j: {neo4j_uri}")
    print(f"📦 Database: {neo4j_database}\n")

    # Initialize Neo4j connection
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))

    try:
        upsert_manager = Neo4jUpsertManager(driver=driver, database=neo4j_database)

        # Map reference data to entities
        print("⚙️  Mapping fraktionen...")
        entities = []
        for frak_data in FRAKTION_REFERENCE_DATA:
            entity = map_fraktion_to_entity(frak_data)
            entities.append(entity)

        # Count by status for summary
        status_counts = {}
        type_counts = {}
        for entity in entities:
            status = entity["status"]
            frak_type = entity["fraktion_type"]
            status_counts[status] = status_counts.get(status, 0) + 1
            type_counts[frak_type] = type_counts.get(frak_type, 0) + 1

        print(f"✅ Mapped {len(entities)} fraktionen")
        print(f"   - Active: {status_counts.get('active', 0)}")
        print(f"   - Dissolved: {status_counts.get('dissolved', 0)}")
        print(f"   - Fraktion: {type_counts.get('fraktion', 0)}")
        print(f"   - Gruppe: {type_counts.get('gruppe', 0)}")
        print(f"   - Independent: {type_counts.get('independent', 0)}\n")

        # Upsert to Neo4j
        print("💾 Upserting to Neo4j...")
        results = upsert_manager.upsert_entities_batch(
            entity_type="Fraktion",
            entities=entities,
            batch_size=25
        )

        print(f"✅ Upserted {results['successful']} fraktionen ({results['failed']} failed)\n")

        # Create ACTIVE_IN relationships
        print("🔗 Creating ACTIVE_IN relationships...")
        active_in_results = create_active_in_relationships(driver, neo4j_database)
        print(f"✅ Created {active_in_results['created']} ACTIVE_IN relationships\n")

        # Create MEMBER_OF relationships
        print("🔗 Creating MEMBER_OF relationships...")
        member_of_results = create_member_of_relationships(driver, neo4j_database)
        print(f"✅ Created {member_of_results['created']} MEMBER_OF relationships\n")

        # Create SUCCESSOR_OF relationships
        print("🔗 Creating SUCCESSOR_OF relationships...")
        successor_results = create_successor_relationships(driver, neo4j_database)
        print(f"✅ Created {successor_results['created']} SUCCESSOR_OF relationships\n")

        # Final summary
        print("=" * 60)
        print("✨ SUCCESS! Fraktion data loaded")
        print("=" * 60)
        print(f"\n📈 Summary:")
        print(f"   - Fraktion nodes: {results['successful']}")
        print(f"   - ACTIVE_IN relationships: {active_in_results['created']}")
        print(f"   - MEMBER_OF relationships: {member_of_results['created']}")
        print(f"   - SUCCESSOR_OF relationships: {successor_results['created']}")
        print(f"   - Coverage: 1949 (WP 1) to 2029 (WP 21)")
        print(f"\n🔍 View in Neo4j Browser: http://localhost:7474")
        print(f"   Query: MATCH (f:Fraktion) RETURN f ORDER BY f.founding_date")
        print(f"   Query: MATCH (p:BundestagPerson)-[r:MEMBER_OF]->(f:Fraktion) RETURN p, r, f LIMIT 100\n")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        driver.close()


if __name__ == "__main__":
    main()
