#!/usr/bin/env python3
"""Inspect the actual Neo4j graph schema created by SimpleKGPipeline."""

import asyncio

from dotenv import load_dotenv

from src.config import graphrag_settings
from src.graphrag.knowledge_builder import PoliticalKnowledgeBuilder

load_dotenv()


async def inspect_graph_schema():
    """Inspect what's actually in our knowledge graph."""
    kb = PoliticalKnowledgeBuilder(
        uri=graphrag_settings.NEO4J_URI,
        username=graphrag_settings.NEO4J_USERNAME,
        password=graphrag_settings.NEO4J_PASSWORD,
        database=graphrag_settings.NEO4J_DATABASE,
        openai_api_key="dummy",  # Not needed for inspection
    )

    try:

        def _inspect():
            with kb.driver.session(database=kb.database) as session:
                print("=== NODE LABELS ===")
                result = session.run("CALL db.labels() YIELD label RETURN label ORDER BY label")
                for record in result:
                    print(f"  {record['label']}")

                print("\n=== RELATIONSHIP TYPES ===")
                result = session.run(
                    "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType ORDER BY relationshipType"
                )
                for record in result:
                    print(f"  {record['relationshipType']}")

                print("\n=== SAMPLE GRAPH STRUCTURE ===")
                result = session.run(
                    """
                MATCH (n)-[r]->(m)
                RETURN labels(n)[0] as from_type, type(r) as relationship, labels(m)[0] as to_type, count(*) as count
                ORDER BY count DESC
                LIMIT 10
                """
                )
                for record in result:
                    print(
                        f"  {record['from_type']} -[{record['relationship']}]-> {record['to_type']} ({record['count']} times)"
                    )

                print("\n=== SAMPLE NODES ===")
                result = session.run(
                    "MATCH (n) RETURN labels(n)[0] as type, n.name as name LIMIT 10"
                )
                for record in result:
                    print(f"  {record['type']}: {record['name']}")

        _inspect()

    finally:
        kb.driver.close()


if __name__ == "__main__":
    asyncio.run(inspect_graph_schema())
