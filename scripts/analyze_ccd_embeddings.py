"""
Analyze Consumer Credit Directive embedding similarity.

This script checks the cross-lingual semantic similarity of the actual
"Consumer Credit Directive" entity between English and German queries.

Usage:
    python scripts/analyze_ccd_embeddings.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from neo4j import AsyncGraphDatabase
from openai import AsyncOpenAI
from src.config import settings
import numpy as np


async def get_embedding(client: AsyncOpenAI, text: str):
    """Get ada-002 embedding."""
    response = await client.embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    return response.data[0].embedding


def cosine_similarity(a, b):
    """Calculate cosine similarity."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


async def main():
    print("=" * 80)
    print("ANALYZING CONSUMER CREDIT DIRECTIVE EMBEDDINGS")
    print("=" * 80)

    # Connect to OpenAI
    client = AsyncOpenAI()

    # Test queries
    queries = [
        "Consumer Credit Directive",
        "Verbraucherkreditrichtlinie",
        "Consumer credit regulations",
        "Verbraucherschutz Kredit",
        "Buy Now Pay Later directive",
        "Ratenkredite Richtlinie"
    ]

    print("\n1. Getting embeddings for test queries...")
    embeddings = {}
    for query in queries:
        embeddings[query] = await get_embedding(client, query)
        print(f"   ✓ {query}")

    # Calculate cross-lingual similarities
    print("\n2. Cross-lingual similarity matrix:")
    print("\n" + "-" * 80)
    print(f"{'Query 1':<35} | {'Query 2':<35} | Similarity")
    print("-" * 80)

    pairs = [
        ("Consumer Credit Directive", "Verbraucherkreditrichtlinie"),
        ("Consumer Credit Directive", "Verbraucherschutz Kredit"),
        ("Consumer credit regulations", "Verbraucherkreditrichtlinie"),
        ("Buy Now Pay Later directive", "Ratenkredite Richtlinie"),
    ]

    for q1, q2 in pairs:
        sim = cosine_similarity(embeddings[q1], embeddings[q2])
        status = "✅" if sim >= 0.75 else "⚠️ " if sim >= 0.65 else "❌"
        print(f"{q1:<35} | {q2:<35} | {sim:.3f} {status}")

    # Connect to Neo4j and check actual entity
    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
    )

    print("\n3. Checking actual 'Consumer Credit Directive' entity in Neo4j...")
    async with driver.session(database=settings.NEO4J_DATABASE) as session:
        query = """
        MATCH (e:Entity)
        WHERE e.name = 'Consumer Credit Directive'
        RETURN e.name as name,
               e.name_embedding as embedding,
               e.embedding_model as model,
               e.entity_type as type
        """
        result = await session.run(query)
        record = await result.single()

        if record:
            print(f"\n   ✓ Found entity: {record['name']}")
            print(f"   Model: {record['model']}")
            print(f"   Type: {record['type']}")

            stored_embedding = record['embedding']

            # Compare stored embedding with our query embeddings
            print("\n4. Comparing stored embedding with query embeddings:")
            print("\n" + "-" * 80)
            print(f"{'Query':<45} | Similarity")
            print("-" * 80)

            for query in queries:
                sim = cosine_similarity(stored_embedding, embeddings[query])
                status = "✅" if sim >= 0.90 else "✓" if sim >= 0.75 else "⚠️ "
                print(f"{query:<45} | {sim:.3f} {status}")

        else:
            print("\n   ❌ Entity not found!")

    await driver.close()

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
