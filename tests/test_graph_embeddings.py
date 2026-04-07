"""
Test script to analyze existing embeddings in your Neo4j knowledge graph.

This script checks:
1. What entities exist in both English and German
2. How similar their embeddings are
3. Whether vector search finds cross-lingual matches

Usage:
    python test_graph_embeddings.py

Prerequisites:
    - NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD environment variables
"""

import asyncio
import os
from typing import List
import numpy as np
from neo4j import AsyncGraphDatabase

from src.config import settings


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if not vec1 or not vec2:
        return 0.0

    vec1_np = np.array(vec1)
    vec2_np = np.array(vec2)

    dot_product = np.dot(vec1_np, vec2_np)
    norm1 = np.linalg.norm(vec1_np)
    norm2 = np.linalg.norm(vec2_np)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return float(dot_product / (norm1 * norm2))


async def analyze_graph_embeddings():
    """Analyze embeddings already in the Neo4j graph."""

    print("=" * 80)
    print("NEO4J GRAPH EMBEDDING ANALYSIS")
    print("=" * 80)
    print()

    # Connect to Neo4j
    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
    )

    try:
        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            # Check embedding coverage
            print("1. EMBEDDING COVERAGE")
            print("-" * 80)

            coverage_query = """
            MATCH (e:Entity)
            WITH count(e) as total,
                 count(e.name_embedding) as with_embedding
            RETURN total, with_embedding,
                   round(100.0 * with_embedding / total, 1) as coverage_pct
            """
            result = await session.run(coverage_query)
            record = await result.single()

            if record:
                total = record['total']
                with_emb = record['with_embedding']
                coverage = record['coverage_pct']

                print(f"Total entities: {total:,}")
                print(f"With embeddings: {with_emb:,}")
                print(f"Coverage: {coverage}%")

                if coverage < 80:
                    print("⚠️  WARNING: Low embedding coverage. Some entities lack embeddings.")
            else:
                print("❌ Could not retrieve coverage statistics")

            # Find sample German entities
            print("\n2. SAMPLE GERMAN ENTITIES")
            print("-" * 80)

            german_query = """
            MATCH (e:Entity)
            WHERE e.name =~ '.*[äöüßÄÖÜ].*'
               OR e.name =~ '.*gesetz.*'
               OR e.name =~ '.*Bundes.*'
            RETURN e.uuid as uuid, e.name as name, labels(e) as labels
            LIMIT 10
            """
            result = await session.run(german_query)
            records = await result.data()

            if records:
                print(f"Found {len(records)} sample German entities:")
                for r in records[:5]:
                    labels = ', '.join(r['labels'])
                    print(f"  • {r['name']} ({labels})")
            else:
                print("⚠️  No German entities found with obvious German characteristics")

            # Find sample English entities
            print("\n3. SAMPLE ENGLISH ENTITIES")
            print("-" * 80)

            english_query = """
            MATCH (e:Entity)
            WHERE e.name =~ '.*Act.*'
               OR e.name =~ '.*Commission.*'
               OR e.name =~ '.*Regulation.*'
            RETURN e.uuid as uuid, e.name as name, labels(e) as labels
            LIMIT 10
            """
            result = await session.run(english_query)
            records = await result.data()

            if records:
                print(f"Found {len(records)} sample English entities:")
                for r in records[:5]:
                    labels = ', '.join(r['labels'])
                    print(f"  • {r['name']} ({labels})")

            # Test cross-lingual similarity
            print("\n4. CROSS-LINGUAL SIMILARITY TEST")
            print("-" * 80)

            # Try to find known entity pairs
            test_pairs = [
                ("Digital Services Act", "Digitale-Dienste-Gesetz"),
                ("GDPR", "DSGVO"),
                ("European Commission", "Europäische Kommission"),
                ("Bundestag", "Federal Parliament"),
            ]

            print("Testing known translation pairs:\n")

            for en_name, de_name in test_pairs:
                # Try to find both entities
                pair_query = """
                MATCH (en:Entity), (de:Entity)
                WHERE en.name CONTAINS $en_name
                  AND de.name CONTAINS $de_name
                  AND en.name_embedding IS NOT NULL
                  AND de.name_embedding IS NOT NULL
                RETURN en.name as en_name, en.name_embedding as en_emb,
                       de.name as de_name, de.name_embedding as de_emb
                LIMIT 1
                """

                result = await session.run(pair_query, {"en_name": en_name, "de_name": de_name})
                record = await result.single()

                if record:
                    similarity = cosine_similarity(record['en_emb'], record['de_emb'])
                    status = "✓" if similarity >= 0.65 else "⚠" if similarity >= 0.45 else "✗"
                    print(f"{status} {record['en_name']:<35} ↔ {record['de_name']:<35} {similarity:.3f}")
                else:
                    print(f"✗ {en_name:<35} ↔ {de_name:<35} (Not found in graph)")

            # Test vector search behavior
            print("\n5. VECTOR SEARCH TEST")
            print("-" * 80)
            print("Testing if vector search finds cross-lingual matches...\n")

            # Find a German entity with embedding
            sample_query = """
            MATCH (e:Entity)
            WHERE e.name_embedding IS NOT NULL
              AND (e.name =~ '.*[äöüßÄÖÜ].*' OR e.name =~ '.*gesetz.*')
            RETURN e.name as name, e.name_embedding as embedding
            LIMIT 1
            """
            result = await session.run(sample_query)
            sample = await result.single()

            if sample:
                print(f"Source (German): {sample['name']}")

                # Search for similar entities using vector similarity
                vector_search_query = """
                MATCH (e:Entity)
                WHERE e.name_embedding IS NOT NULL
                WITH e, vector.similarity.cosine(e.name_embedding, $query_embedding) as similarity
                WHERE similarity > 0.3
                RETURN e.name as name, labels(e) as labels, similarity
                ORDER BY similarity DESC
                LIMIT 10
                """

                result = await session.run(vector_search_query, {"query_embedding": sample['embedding']})
                records = await result.data()

                print(f"\nTop {len(records)} similar entities:")
                for i, r in enumerate(records, 1):
                    labels = ', '.join(r['labels'])
                    print(f"  {i}. [{r['similarity']:.3f}] {r['name']} ({labels})")

                # Check if results include both German and English
                german_count = sum(1 for r in records if any(c in r['name'] for c in 'äöüßÄÖÜ'))
                english_count = len(records) - german_count

                print(f"\nLanguage distribution:")
                print(f"  German entities: {german_count}")
                print(f"  English entities: {english_count}")

                if german_count > 0 and english_count > 0:
                    print("✓ Vector search returns MIXED languages - embeddings are multilingual!")
                elif german_count == len(records):
                    print("⚠ Vector search returns ONLY German - embeddings may be language-specific")
                else:
                    print("⚠ Vector search returns ONLY English - embeddings may be language-specific")

            # Recommendation
            print("\n6. RECOMMENDATIONS")
            print("-" * 80)

            # Get overall statistics
            stats_query = """
            MATCH (e:Entity)
            WHERE e.name_embedding IS NOT NULL
            WITH e.name as name
            WITH count(name) as total,
                 sum(CASE WHEN name =~ '.*[äöüßÄÖÜ].*' THEN 1 ELSE 0 END) as german,
                 sum(CASE WHEN name =~ '.*[a-zA-Z].*' AND NOT name =~ '.*[äöüßÄÖÜ].*' THEN 1 ELSE 0 END) as english
            RETURN total, german, english
            """
            result = await session.run(stats_query)
            stats = await result.single()

            if stats:
                total = stats['total']
                german = stats['german']
                english = stats['english']

                print(f"Graph composition:")
                print(f"  Total entities with embeddings: {total:,}")
                print(f"  German entities: {german:,} ({german/total*100:.1f}%)")
                print(f"  English entities: {english:,} ({english/total*100:.1f}%)")

                if german > 0 and english > 0:
                    print("\n✓ Your graph contains BOTH languages")
                    print("→ Cross-lingual search is critical for good retrieval")
                    print("→ Proceed with embedding test (test_multilingual_embeddings.py)")
                    print("→ If embeddings are already multilingual, just add query translation")
                    print("→ If not, consider re-embedding with multilingual model")

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        await driver.close()

    print("\n" + "=" * 80)


if __name__ == "__main__":
    print("\nAnalyzing embeddings in your Neo4j knowledge graph...")
    print(f"Database: {settings.NEO4J_DATABASE}")
    print(f"URI: {settings.NEO4J_URI}\n")

    asyncio.run(analyze_graph_embeddings())
