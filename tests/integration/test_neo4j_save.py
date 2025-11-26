#!/usr/bin/env python3
"""Quick test to verify Neo4j save works"""

from neo4j import GraphDatabase

from src.graphrag.political_schema_v5 import Plenarprotokoll

# Connect to Neo4j
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password123"))

# Create test entity (use different number)
test_entity = Plenarprotokoll(
    plenarprotokoll_name="Test Protocol 888",
    sitzungsnummer="888",
    wahlperiode=20,
    datum="2025-11-17",
    herausgeber="BT",
    pdf_url=None,
    full_text=None,
    tagesordnungspunkte=None,
    reden_anzahl=None,
    fundstelle=None,
    aktualisiert=None,
    vorgangsbezug_anzahl=None,
    related_vorgang_ids=None,
    url=None,
)

print(
    f"Created test entity: sitzungsnummer={test_entity.sitzungsnummer}, wp={test_entity.wahlperiode}"
)
print(f"Entity dict: {test_entity.model_dump()}")

# Try to save it
entity_dict = test_entity.model_dump()
sitzungsnummer_str = entity_dict.get("sitzungsnummer")
wahlperiode = entity_dict.get("wahlperiode")

# Convert to int
sitzungsnummer_int = int(sitzungsnummer_str)

# CRITICAL: Also fix in entity_dict so SET doesn't overwrite it
entity_dict["sitzungsnummer"] = sitzungsnummer_int

print(
    f"\nAttempting MERGE with sitzungsnummer={sitzungsnummer_int} (int), wahlperiode={wahlperiode}"
)
print(f"Properties sitzungsnummer type: {type(entity_dict['sitzungsnummer'])}")

with driver.session(database="politicamonitoring.v2") as session:
    query = """
    MERGE (n:Plenarprotokoll {sitzungsnummer: $sitzungsnummer, wahlperiode: $wahlperiode})
    SET n += $properties
    RETURN n
    """

    result = session.run(
        query, sitzungsnummer=sitzungsnummer_int, wahlperiode=wahlperiode, properties=entity_dict
    )
    record = result.single()

    if record:
        print(f"SUCCESS! Node created/updated: {record['n']}")
    else:
        print("FAILED! No record returned")

# Verify it exists
with driver.session(database="politicamonitoring.v2") as session:
    result = session.run(
        "MATCH (p:Plenarprotokoll {sitzungsnummer: $sitzung, wahlperiode: $wp}) RETURN p",
        sitzung=sitzungsnummer_int,
        wp=wahlperiode,
    )
    record = result.single()
    if record:
        print(f"\nVerified: Node exists in Neo4j: {record['p']}")
    else:
        print("\nWARNING: Node not found after MERGE!")

# Count total
with driver.session(database="politicamonitoring.v2") as session:
    result = session.run("MATCH (p:Plenarprotokoll) RETURN count(p) as count")
    count = result.single()["count"]
    print(f"\nTotal Plenarprotokoll nodes: {count}")

driver.close()
