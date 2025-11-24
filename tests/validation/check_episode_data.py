"""Check episode data structure in Neo4j."""
import asyncio
import os
from graphiti_core import Graphiti

async def check_episodes():
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password123")
    
    client = Graphiti(neo4j_uri, neo4j_user, neo4j_password)
    
    # Query for episodes directly
    query = """
        MATCH (e:Episode)
        RETURN e.uuid AS uuid, e.name AS name
        LIMIT 5
    """
    
    async with client.driver.session() as session:
        result = await session.run(query)
        records = await result.data()
        
        print("Sample Episodes:")
        for record in records:
            print(f"  UUID: {record['uuid']}")
            print(f"  Name: {record['name']}")
            print()
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(check_episodes())
