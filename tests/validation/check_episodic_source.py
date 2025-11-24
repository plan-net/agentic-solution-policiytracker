"""Check what's in the source property of Episodic nodes."""
import asyncio
import os

from graphiti_core import Graphiti


async def check_source():
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password123")

    client = Graphiti(neo4j_uri, neo4j_user, neo4j_password)

    query = """
        MATCH (e:Episodic)
        RETURN e.source AS source, e.source_description AS source_description, e.name AS name
        LIMIT 3
    """

    async with client.driver.session() as session:
        result = await session.run(query)
        records = await result.data()

        for i, record in enumerate(records, 1):
            print(f"\n{i}. Source: '{record['source']}'")
            print(f"   Source Description: '{record['source_description']}'")
            print(f"   Name: {record['name'][:80]}...")

    await client.close()


if __name__ == "__main__":
    asyncio.run(check_source())
