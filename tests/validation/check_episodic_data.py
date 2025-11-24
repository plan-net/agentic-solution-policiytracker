"""Check Episodic node structure in Neo4j."""
import asyncio
import os
from graphiti_core import Graphiti

async def check_episodic():
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password123")
    
    client = Graphiti(neo4j_uri, neo4j_user, neo4j_password)
    
    # Query for Episodic nodes directly
    query = """
        MATCH (e:Episodic)
        RETURN e.uuid AS uuid, e.name AS name, properties(e) AS props
        LIMIT 5
    """
    
    async with client.driver.session() as session:
        result = await session.run(query)
        records = await result.data()
        
        print("Sample Episodic Nodes:")
        print("=" * 80)
        for i, record in enumerate(records, 1):
            print(f"\n{i}. UUID: {record['uuid']}")
            print(f"   Name: {record['name']}")
            print(f"   Properties: {record['props'].keys()}")
            # Print first 200 chars of name if it's a path
            if record['name'] and len(record['name']) > 80:
                print(f"   Full Name: {record['name'][:200]}...")
            print()
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(check_episodic())
