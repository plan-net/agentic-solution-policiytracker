"""
Search for Consumer Credit Directive in the knowledge graph.

This script performs both text-based and vector similarity searches to find
all information related to the Consumer Credit Directive.

Usage:
    python scripts/search_consumer_credit.py
    python scripts/search_consumer_credit.py --detailed
    python scripts/search_consumer_credit.py --vector-only
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import List, Dict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from neo4j import AsyncGraphDatabase
from src.config import settings
from src.flows.shared.apisix_llm_client import create_apisix_graphiti_embedder


async def text_search(session) -> Dict[str, List]:
    """Perform text-based search for Consumer Credit Directive."""
    print("\n" + "=" * 80)
    print("TEXT-BASED SEARCH")
    print("=" * 80)

    results = {
        'entities': [],
        'summaries': [],
        'relationships': [],
        'episodic': []
    }

    # 1. Search entities by name
    print("\n1. Searching entity names...")
    query = """
    MATCH (e:Entity)
    WHERE toLower(e.name) CONTAINS 'consumer credit'
       OR toLower(e.name) CONTAINS 'verbraucherkreditrichtlinie'
    RETURN e.name as name, e.entity_type as type, e.summary as summary, e.uuid as uuid
    LIMIT 20
    """
    result = await session.run(query)
    results['entities'] = await result.data()
    print(f"   Found {len(results['entities'])} entity name matches")

    # 2. Search entity summaries
    print("\n2. Searching entity summaries...")
    query = """
    MATCH (e:Entity)
    WHERE toLower(e.summary) CONTAINS 'consumer credit'
       OR toLower(e.summary) CONTAINS 'verbraucherkredit'
    RETURN e.name as name, e.entity_type as type, e.summary as summary, e.uuid as uuid
    LIMIT 20
    """
    result = await session.run(query)
    results['summaries'] = await result.data()
    print(f"   Found {len(results['summaries'])} summary matches")

    # 3. Search relationship facts
    print("\n3. Searching relationship facts...")
    query = """
    MATCH (source:Entity)-[r:RELATES_TO]->(target:Entity)
    WHERE toLower(r.fact) CONTAINS 'consumer credit'
       OR toLower(r.fact) CONTAINS 'verbraucherkredit'
    RETURN source.name as source_name, target.name as target_name,
           r.fact as fact, id(r) as rel_id
    LIMIT 20
    """
    result = await session.run(query)
    results['relationships'] = await result.data()
    print(f"   Found {len(results['relationships'])} relationship matches")

    # 4. Search episodic content
    print("\n4. Searching episodic content...")
    query = """
    MATCH (ep:Episodic)
    WHERE toLower(ep.content) CONTAINS 'consumer credit directive'
       OR toLower(ep.content) CONTAINS 'verbraucherkreditrichtlinie'
    RETURN ep.uuid as uuid,
           substring(ep.content, 0, 200) + '...' as preview,
           size(ep.content) as content_length
    LIMIT 10
    """
    result = await session.run(query)
    results['episodic'] = await result.data()
    print(f"   Found {len(results['episodic'])} episodic matches")

    return results


async def vector_search(session, embedder) -> List[Dict]:
    """Perform vector similarity search for Consumer Credit Directive."""
    print("\n" + "=" * 80)
    print("VECTOR SIMILARITY SEARCH")
    print("=" * 80)

    # Generate embedding for query
    queries = [
        "Consumer Credit Directive",
        "Verbraucherkreditrichtlinie",  # German
        "EU consumer credit regulation",
        "Directive 2008/48/EC on credit agreements"
    ]

    all_results = []

    for query_text in queries:
        print(f"\n🔍 Query: '{query_text}'")

        # Get embedding
        embedding = await embedder.create([query_text])
        query_embedding = embedding[0]

        # Search entities
        cypher_query = """
        MATCH (e:Entity)
        WHERE e.name_embedding IS NOT NULL
        WITH e,
             gds.similarity.cosine(e.name_embedding, $query_embedding) as similarity
        WHERE similarity > 0.75
        RETURN e.name as name,
               e.entity_type as type,
               e.summary as summary,
               similarity
        ORDER BY similarity DESC
        LIMIT 10
        """

        result = await session.run(cypher_query, {"query_embedding": query_embedding})
        matches = await result.data()

        if matches:
            print(f"   ✓ Found {len(matches)} matches (similarity > 0.75)")
            for match in matches[:5]:  # Show top 5
                print(f"      {match['similarity']:.3f} - {match['name']}")
            all_results.extend(matches)
        else:
            print(f"   No matches found (similarity > 0.75)")

    return all_results


def print_results(text_results: Dict, vector_results: List, detailed: bool = False):
    """Print search results in a structured format."""
    print("\n" + "=" * 80)
    print("SEARCH RESULTS SUMMARY")
    print("=" * 80)

    # Text search summary
    print("\nText Search Results:")
    print(f"  • Entity name matches: {len(text_results['entities'])}")
    print(f"  • Summary matches: {len(text_results['summaries'])}")
    print(f"  • Relationship matches: {len(text_results['relationships'])}")
    print(f"  • Episodic content matches: {len(text_results['episodic'])}")

    # Vector search summary
    print(f"\nVector Search Results:")
    print(f"  • Similar entities found: {len(vector_results)}")

    # Detailed output
    if detailed:
        print("\n" + "=" * 80)
        print("DETAILED RESULTS")
        print("=" * 80)

        # Entity matches
        if text_results['entities']:
            print("\n📋 Entity Name Matches:")
            print("-" * 80)
            for entity in text_results['entities'][:10]:
                print(f"\nName: {entity['name']}")
                print(f"Type: {entity['type']}")
                if entity.get('summary'):
                    print(f"Summary: {entity['summary'][:200]}...")

        # Relationship matches
        if text_results['relationships']:
            print("\n🔗 Relationship Matches:")
            print("-" * 80)
            for rel in text_results['relationships'][:10]:
                print(f"\n{rel['source_name']} → {rel['target_name']}")
                print(f"Fact: {rel['fact'][:200]}...")

        # Episodic matches
        if text_results['episodic']:
            print("\n📄 Episodic Content Matches:")
            print("-" * 80)
            for ep in text_results['episodic'][:5]:
                print(f"\nUUID: {ep['uuid']}")
                print(f"Length: {ep['content_length']} chars")
                print(f"Preview: {ep['preview']}")

        # Vector search matches
        if vector_results:
            print("\n🎯 Vector Similarity Matches:")
            print("-" * 80)
            # Group by name to avoid duplicates
            seen = set()
            for match in vector_results:
                if match['name'] not in seen:
                    seen.add(match['name'])
                    print(f"\nSimilarity: {match['similarity']:.3f}")
                    print(f"Name: {match['name']}")
                    print(f"Type: {match['type']}")
                    if match.get('summary'):
                        print(f"Summary: {match['summary'][:200]}...")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Search for Consumer Credit Directive in knowledge graph",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument("--detailed", action="store_true", help="Show detailed results")
    parser.add_argument("--vector-only", action="store_true", help="Only perform vector search")
    parser.add_argument("--text-only", action="store_true", help="Only perform text search")

    args = parser.parse_args()

    print("=" * 80)
    print("CONSUMER CREDIT DIRECTIVE SEARCH")
    print("=" * 80)
    print(f"\nDatabase: {settings.NEO4J_DATABASE}")
    print(f"Search Terms: Consumer Credit, Verbraucherkreditrichtlinie")

    # Connect to Neo4j
    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
    )

    text_results = {'entities': [], 'summaries': [], 'relationships': [], 'episodic': []}
    vector_results = []

    try:
        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            # Text search
            if not args.vector_only:
                text_results = await text_search(session)

            # Vector search
            if not args.text_only:
                embedder = create_apisix_graphiti_embedder()
                vector_results = await vector_search(session, embedder)

        # Print results
        print_results(text_results, vector_results, args.detailed)

        # Final summary
        total_matches = (
            len(text_results['entities']) +
            len(text_results['summaries']) +
            len(text_results['relationships']) +
            len(text_results['episodic']) +
            len(set(m['name'] for m in vector_results))
        )

        print("\n" + "=" * 80)
        if total_matches > 0:
            print(f"✅ Found {total_matches} total matches for Consumer Credit Directive")
            print("\nTo see detailed results, run:")
            print("  python scripts/search_consumer_credit.py --detailed")
        else:
            print("❌ No matches found for Consumer Credit Directive")
            print("\nPossible reasons:")
            print("  • This directive may not be in the knowledge graph yet")
            print("  • Try searching with different terms (e.g., '2008/48/EC')")
            print("  • Check if the data ingestion process included this directive")
        print("=" * 80)

        return 0 if total_matches > 0 else 1

    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        await driver.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
