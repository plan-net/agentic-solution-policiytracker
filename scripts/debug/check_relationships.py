"""Check if relationships exist between tracked entities."""
import asyncio
from neo4j import AsyncGraphDatabase

async def check_rels():
    driver = AsyncGraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "password123")
    )
    
    # Get entity UUIDs from the session
    session_id = "session_6ae9cd17a1474cde"
    
    async with driver.session(database="politicalmonitoring") as session:
        # Get entity UUIDs from session
        result = await session.run("""
            MATCH (s:ChatSession {session_id: $session_id})
            RETURN s.entity_uuids as uuids
        """, {"session_id": session_id})
        
        record = await result.single()
        entity_uuids = record["uuids"] if record else []
        
        print(f"Session has {len(entity_uuids)} entity UUIDs\n")
        
        # Check if relationships exist between these entities
        rel_result = await session.run("""
            MATCH (e1)-[r]->(e2)
            WHERE e1.uuid IN $uuids AND e2.uuid IN $uuids
            RETURN type(r) as rel_type, 
                   e1.name as source_name,
                   e2.name as target_name,
                   e1.uuid as source_uuid,
                   e2.uuid as target_uuid
            LIMIT 20
        """, {"uuids": entity_uuids})
        
        rels = await rel_result.data()
        
        print(f"Found {len(rels)} relationships between tracked entities:\n")
        
        for rel in rels[:10]:
            print(f"{rel['source_name']} --[{rel['rel_type']}]--> {rel['target_name']}")
    
    await driver.close()

asyncio.run(check_rels())
