#!/usr/bin/env python3
"""
Simple script to load Bundestag Wahlperiode reference data into Neo4j.

Run with: python src/flows/bundestag_wahlperiode/load_wahlperioden.py
Or via just: just load-wahlperioden
"""

import os
import sys
from datetime import datetime
from typing import Any, Optional

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from neo4j import GraphDatabase

from src.flows.bundestag_common.neo4j_upsert import Neo4jUpsertManager
from src.flows.bundestag_wahlperiode.wahlperiode_data import WAHLPERIODE_REFERENCE_DATA


def map_wahlperiode_to_entity(wp_data: dict[str, Any]) -> dict[str, Any]:
    """Map wahlperiode reference data to entity structure."""
    nummer = wp_data["wahlperiode_nummer"]
    election_date = wp_data.get("election_date")
    start_date = wp_data.get("start_date")
    end_date = wp_data.get("end_date")

    # Compute duration if dates available
    duration_days = None
    if start_date and end_date:
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
        duration_days = (end_dt - start_dt).days

    # Determine status
    status = compute_status(start_date, end_date)

    entity = {
        "wahlperiode_nummer": nummer,
        "wahlperiode_name": f"{nummer}. Wahlperiode",
        "election_date": election_date,
        "start_date": start_date,
        "end_date": end_date,
        "duration_days": duration_days,
        "is_snap_election": wp_data.get("is_snap_election", False),
        "status": status,
    }

    return entity


def compute_status(start_date: Optional[str], end_date: Optional[str]) -> str:
    """Compute wahlperiode status based on dates."""
    if not start_date:
        return "future"

    now = datetime.now()
    start_dt = datetime.fromisoformat(start_date)

    if start_dt > now:
        return "future"

    if not end_date:
        return "current"

    end_dt = datetime.fromisoformat(end_date)

    if end_dt < now:
        return "completed"
    else:
        return "current"


def create_served_in_relationships(driver, database: str) -> dict[str, int]:
    """Create SERVED_IN relationships between BundestagPerson and Wahlperiode nodes."""
    query = """
    MATCH (p:BundestagPerson)
    WHERE p.wahlperioden IS NOT NULL AND size(p.wahlperioden) > 0
    UNWIND p.wahlperioden AS wp_num
    MATCH (w:Wahlperiode {wahlperiode_nummer: wp_num})
    MERGE (p)-[:SERVED_IN]->(w)
    RETURN count(*) as relationships_created
    """

    try:
        with driver.session(database=database) as session:
            result = session.run(query)
            record = result.single()
            created = record["relationships_created"] if record else 0
            return {"created": created}
    except Exception as e:
        print(f"❌ Failed to create relationships: {e}")
        return {"created": 0, "error": str(e)}


def main():
    """Main execution function."""
    # Get Neo4j connection from environment or use defaults
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password123")
    neo4j_database = os.getenv("NEO4J_DATABASE", "politicamonitoring.v2")

    print("=" * 60)
    print("Bundestag Wahlperiode Loader")
    print("=" * 60)
    print(f"\n📊 Loading {len(WAHLPERIODE_REFERENCE_DATA)} wahlperioden...")
    print(f"🔗 Connecting to Neo4j: {neo4j_uri}")
    print(f"📦 Database: {neo4j_database}\n")

    # Initialize Neo4j connection
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))

    try:
        upsert_manager = Neo4jUpsertManager(driver=driver, database=neo4j_database)

        # Map reference data to entities
        print("⚙️  Mapping wahlperioden...")
        entities = []
        for wp_data in WAHLPERIODE_REFERENCE_DATA:
            entity = map_wahlperiode_to_entity(wp_data)
            entities.append(entity)

        # Count by status for summary
        status_counts = {}
        for entity in entities:
            status = entity["status"]
            status_counts[status] = status_counts.get(status, 0) + 1

        snap_elections = sum(1 for e in entities if e.get("is_snap_election", False))

        print(f"✅ Mapped {len(entities)} wahlperioden")
        print(f"   - Completed: {status_counts.get('completed', 0)}")
        print(f"   - Current: {status_counts.get('current', 0)}")
        print(f"   - Future: {status_counts.get('future', 0)}")
        print(f"   - Snap Elections: {snap_elections}\n")

        # Upsert to Neo4j
        print("💾 Upserting to Neo4j...")
        results = upsert_manager.upsert_entities_batch(
            entity_type="Wahlperiode", entities=entities, batch_size=25
        )

        print(f"✅ Upserted {results['successful']} wahlperioden ({results['failed']} failed)\n")

        # Create relationships
        print("🔗 Creating SERVED_IN relationships...")
        relationship_results = create_served_in_relationships(driver, neo4j_database)

        print(f"✅ Created {relationship_results['created']} SERVED_IN relationships\n")

        # Final summary
        print("=" * 60)
        print("✨ SUCCESS! Wahlperiode data loaded")
        print("=" * 60)
        print("\n📈 Summary:")
        print(f"   - Wahlperiode nodes: {results['successful']}")
        print(f"   - SERVED_IN relationships: {relationship_results['created']}")
        print("   - Coverage: 1949 (WP 1) to 2029 (WP 21)")
        print("\n🔍 View in Neo4j Browser: http://localhost:7474")
        print("   Query: MATCH (w:Wahlperiode) RETURN w ORDER BY w.wahlperiode_nummer\n")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        driver.close()


if __name__ == "__main__":
    main()
