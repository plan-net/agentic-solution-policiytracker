"""Check existing chat sessions in Neo4j."""
import asyncio
from neo4j import AsyncGraphDatabase
import json

async def check_sessions():
    driver = AsyncGraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "password123")
    )
    
    async with driver.session(database="politicalmonitoring") as session:
        # Get all chat sessions
        result = await session.run("""
            MATCH (s:ChatSession)
            RETURN s.session_id as session_id, 
                   s.entity_uuids as entity_uuids,
                   s.tools_used_json as tools_used,
                   s.created_at as created_at
            ORDER BY s.created_at DESC
            LIMIT 10
        """)
        
        records = await result.data()
        
        print(f"Found {len(records)} chat sessions:\n")
        
        for r in records:
            print(f"Session ID: {r['session_id']}")
            print(f"  Entities: {len(r['entity_uuids']) if r['entity_uuids'] else 0}")
            print(f"  Created: {r['created_at']}")
            
            if r['tools_used']:
                try:
                    tools = json.loads(r['tools_used'])
                    print(f"  Tools: {len(tools)}")
                    for tool in tools[:3]:  # Show first 3
                        print(f"    - {tool.get('tool_name', 'unknown')}")
                except:
                    print(f"  Tools: (parse error)")
            else:
                print(f"  Tools: None")
            print()
    
    await driver.close()

asyncio.run(check_sessions())
