"""
Test multilingual search for Consumer Credit Directive.

This script tests whether searching in English vs German yields the same results
after ada-002 migration. This validates the cross-lingual semantic understanding
of the embedding model.

Usage:
    python scripts/test_multilingual_search_ccd.py
    python scripts/test_multilingual_search_ccd.py --top-k 20
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from neo4j import AsyncGraphDatabase
from src.config import settings
from src.flows.shared.apisix_llm_client import create_apisix_graphiti_embedder
import numpy as np


async def vector_search_entities(
    session,
    embedder,
    query_text: str,
    similarity_threshold: float = 0.70,
    top_k: int = 10
) -> List[Dict]:
    """Perform vector similarity search on entities."""
    # Get embedding
    embedding = await embedder.create([query_text])
    query_embedding = embedding[0]

    # Search entities
    cypher_query = """
    MATCH (e:Entity)
    WHERE e.name_embedding IS NOT NULL
    WITH e,
         gds.similarity.cosine(e.name_embedding, $query_embedding) as similarity
    WHERE similarity >= $threshold
    RETURN e.uuid as uuid,
           e.name as name,
           e.entity_type as type,
           e.summary as summary,
           similarity
    ORDER BY similarity DESC
    LIMIT $top_k
    """

    result = await session.run(cypher_query, {
        "query_embedding": query_embedding,
        "threshold": similarity_threshold,
        "top_k": top_k
    })
    matches = await result.data()
    return matches


async def vector_search_relationships(
    session,
    embedder,
    query_text: str,
    similarity_threshold: float = 0.70,
    top_k: int = 10
) -> List[Dict]:
    """Perform vector similarity search on relationships."""
    # Get embedding
    embedding = await embedder.create([query_text])
    query_embedding = embedding[0]

    # Search relationships
    cypher_query = """
    MATCH (source:Entity)-[r:RELATES_TO]->(target:Entity)
    WHERE r.fact_embedding IS NOT NULL
    WITH r, source, target,
         gds.similarity.cosine(r.fact_embedding, $query_embedding) as similarity
    WHERE similarity >= $threshold
    RETURN id(r) as rel_id,
           source.name as source_name,
           target.name as target_name,
           r.fact as fact,
           similarity
    ORDER BY similarity DESC
    LIMIT $top_k
    """

    result = await session.run(cypher_query, {
        "query_embedding": query_embedding,
        "threshold": similarity_threshold,
        "top_k": top_k
    })
    matches = await result.data()
    return matches


async def vector_search_episodic(
    session,
    embedder,
    query_text: str,
    similarity_threshold: float = 0.70,
    top_k: int = 10
) -> List[Dict]:
    """Perform vector similarity search on episodic content."""
    # Get embedding
    embedding = await embedder.create([query_text])
    query_embedding = embedding[0]

    # Search episodic nodes
    cypher_query = """
    MATCH (ep:Episodic)
    WHERE ep.content_embedding IS NOT NULL
    WITH ep,
         gds.similarity.cosine(ep.content_embedding, $query_embedding) as similarity
    WHERE similarity >= $threshold
    RETURN ep.uuid as uuid,
           substring(ep.content, 0, 200) + '...' as preview,
           similarity
    ORDER BY similarity DESC
    LIMIT $top_k
    """

    result = await session.run(cypher_query, {
        "query_embedding": query_embedding,
        "threshold": similarity_threshold,
        "top_k": top_k
    })
    matches = await result.data()
    return matches


def calculate_overlap(list1: List[Dict], list2: List[Dict], key: str = 'uuid') -> Tuple[float, List, List, List]:
    """Calculate overlap between two result lists."""
    set1 = set(item[key] for item in list1)
    set2 = set(item[key] for item in list2)

    intersection = set1 & set2
    only_in_1 = set1 - set2
    only_in_2 = set2 - set1

    # Calculate Jaccard similarity (intersection over union)
    union = set1 | set2
    overlap_percentage = len(intersection) / len(union) * 100 if union else 0

    return overlap_percentage, list(intersection), list(only_in_1), list(only_in_2)


def print_comparison_table(
    english_results: List[Dict],
    german_results: List[Dict],
    query_type: str,
    key: str = 'uuid'
):
    """Print comparison table of English vs German results."""
    print(f"\n{'=' * 80}")
    print(f"{query_type.upper()} RESULTS COMPARISON")
    print(f"{'=' * 80}")

    overlap, common, only_english, only_german = calculate_overlap(english_results, german_results, key)

    print(f"\nEnglish query results: {len(english_results)}")
    print(f"German query results:  {len(german_results)}")
    print(f"Common results:        {len(common)}")
    print(f"Overlap:               {overlap:.1f}%")

    if len(common) > 0:
        print(f"\n✅ COMMON RESULTS ({len(common)}):")
        print("-" * 80)
        # Show top 5 common results with similarity scores
        common_set = set(common)
        for i, item in enumerate(english_results):
            if item[key] in common_set and i < 5:
                # Find matching German result
                german_match = next((g for g in german_results if g[key] == item[key]), None)
                if german_match:
                    print(f"\n{i+1}. {item.get('name', item.get('fact', 'N/A'))[:60]}")
                    print(f"   English similarity: {item['similarity']:.3f}")
                    print(f"   German similarity:  {german_match['similarity']:.3f}")

    if only_english:
        print(f"\n⚠️  ONLY IN ENGLISH RESULTS ({len(only_english)}):")
        print("-" * 80)
        for item in english_results[:3]:
            if item[key] in only_english:
                print(f"  • {item.get('name', item.get('fact', 'N/A'))[:60]} (sim: {item['similarity']:.3f})")

    if only_german:
        print(f"\n⚠️  ONLY IN GERMAN RESULTS ({len(only_german)}):")
        print("-" * 80)
        for item in german_results[:3]:
            if item[key] in only_german:
                print(f"  • {item.get('name', item.get('fact', 'N/A'))[:60]} (sim: {item['similarity']:.3f})")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test multilingual search for Consumer Credit Directive",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument("--top-k", type=int, default=10, help="Number of top results to retrieve (default: 10)")
    parser.add_argument("--threshold", type=float, default=0.70, help="Similarity threshold (default: 0.70)")
    parser.add_argument("--entities-only", action="store_true", help="Only test entity search")
    parser.add_argument("--relationships-only", action="store_true", help="Only test relationship search")
    parser.add_argument("--episodic-only", action="store_true", help="Only test episodic search")

    args = parser.parse_args()

    print("=" * 80)
    print("MULTILINGUAL SEARCH TEST - CONSUMER CREDIT DIRECTIVE")
    print("=" * 80)
    print(f"\nDatabase: {settings.NEO4J_DATABASE}")
    print(f"Embedding Model: text-embedding-ada-002")
    print(f"Top-K: {args.top_k}")
    print(f"Similarity Threshold: {args.threshold}")

    # Test queries
    english_query = "Consumer Credit Directive"
    german_query = "Verbraucherkreditrichtlinie"

    print(f"\n📝 Test Queries:")
    print(f"  English: '{english_query}'")
    print(f"  German:  '{german_query}'")

    # Connect to Neo4j
    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
    )

    # Initialize embedder
    embedder = create_apisix_graphiti_embedder()

    results = {
        'entities': {'overlap': 0, 'english_count': 0, 'german_count': 0},
        'relationships': {'overlap': 0, 'english_count': 0, 'german_count': 0},
        'episodic': {'overlap': 0, 'english_count': 0, 'german_count': 0}
    }

    try:
        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            # Test entities
            if not args.relationships_only and not args.episodic_only:
                print("\n" + "=" * 80)
                print("1. TESTING ENTITY SEARCH")
                print("=" * 80)

                print(f"\n🔍 Searching entities with English query...")
                english_entities = await vector_search_entities(
                    session, embedder, english_query, args.threshold, args.top_k
                )

                print(f"🔍 Searching entities with German query...")
                german_entities = await vector_search_entities(
                    session, embedder, german_query, args.threshold, args.top_k
                )

                print_comparison_table(english_entities, german_entities, "Entity", 'uuid')

                overlap, _, _, _ = calculate_overlap(english_entities, german_entities, 'uuid')
                results['entities'] = {
                    'overlap': overlap,
                    'english_count': len(english_entities),
                    'german_count': len(german_entities)
                }

            # Test relationships
            if not args.entities_only and not args.episodic_only:
                print("\n" + "=" * 80)
                print("2. TESTING RELATIONSHIP SEARCH")
                print("=" * 80)

                print(f"\n🔍 Searching relationships with English query...")
                english_rels = await vector_search_relationships(
                    session, embedder, english_query, args.threshold, args.top_k
                )

                print(f"🔍 Searching relationships with German query...")
                german_rels = await vector_search_relationships(
                    session, embedder, german_query, args.threshold, args.top_k
                )

                print_comparison_table(english_rels, german_rels, "Relationship", 'rel_id')

                overlap, _, _, _ = calculate_overlap(english_rels, german_rels, 'rel_id')
                results['relationships'] = {
                    'overlap': overlap,
                    'english_count': len(english_rels),
                    'german_count': len(german_rels)
                }

            # Test episodic
            if not args.entities_only and not args.relationships_only:
                print("\n" + "=" * 80)
                print("3. TESTING EPISODIC CONTENT SEARCH")
                print("=" * 80)

                print(f"\n🔍 Searching episodic content with English query...")
                english_eps = await vector_search_episodic(
                    session, embedder, english_query, args.threshold, args.top_k
                )

                print(f"🔍 Searching episodic content with German query...")
                german_eps = await vector_search_episodic(
                    session, embedder, german_query, args.threshold, args.top_k
                )

                print_comparison_table(english_eps, german_eps, "Episodic Content", 'uuid')

                overlap, _, _, _ = calculate_overlap(english_eps, german_eps, 'uuid')
                results['episodic'] = {
                    'overlap': overlap,
                    'english_count': len(english_eps),
                    'german_count': len(german_eps)
                }

        # Final summary
        print("\n" + "=" * 80)
        print("MULTILINGUAL SEARCH TEST SUMMARY")
        print("=" * 80)

        if not args.relationships_only and not args.episodic_only:
            print(f"\n📋 Entity Search:")
            print(f"  English results: {results['entities']['english_count']}")
            print(f"  German results:  {results['entities']['german_count']}")
            print(f"  Overlap:         {results['entities']['overlap']:.1f}%")

        if not args.entities_only and not args.episodic_only:
            print(f"\n🔗 Relationship Search:")
            print(f"  English results: {results['relationships']['english_count']}")
            print(f"  German results:  {results['relationships']['german_count']}")
            print(f"  Overlap:         {results['relationships']['overlap']:.1f}%")

        if not args.entities_only and not args.relationships_only:
            print(f"\n📄 Episodic Content Search:")
            print(f"  English results: {results['episodic']['english_count']}")
            print(f"  German results:  {results['episodic']['german_count']}")
            print(f"  Overlap:         {results['episodic']['overlap']:.1f}%")

        # Calculate average overlap
        tested = []
        if not args.relationships_only and not args.episodic_only:
            tested.append(results['entities']['overlap'])
        if not args.entities_only and not args.episodic_only:
            tested.append(results['relationships']['overlap'])
        if not args.entities_only and not args.relationships_only:
            tested.append(results['episodic']['overlap'])

        avg_overlap = np.mean(tested) if tested else 0

        print(f"\n📊 Average Overlap: {avg_overlap:.1f}%")

        print("\n" + "=" * 80)
        if avg_overlap >= 85:
            print("✅ EXCELLENT - High cross-lingual consistency (≥85%)")
            print("\nada-002 is providing strong multilingual semantic understanding.")
            print("English and German queries retrieve very similar results.")
        elif avg_overlap >= 70:
            print("✓ GOOD - Reasonable cross-lingual consistency (≥70%)")
            print("\nada-002 is working well for multilingual search.")
            print("Some differences are expected due to language-specific nuances.")
        elif avg_overlap >= 50:
            print("⚠️  MODERATE - Some cross-lingual differences (≥50%)")
            print("\nada-002 shows partial multilingual understanding.")
            print("Consider investigating why some results differ.")
        else:
            print("❌ LOW - Significant cross-lingual differences (<50%)")
            print("\nMultilingual performance may need investigation.")
            print("Check if embeddings are properly migrated to ada-002.")
        print("=" * 80)

        return 0 if avg_overlap >= 70 else 1

    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        await driver.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
