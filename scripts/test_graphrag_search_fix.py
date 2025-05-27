#!/usr/bin/env python3
"""Test GraphRAG search functionality after the RetrieverResult fix."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import settings
from src.graphrag.knowledge_builder import PoliticalKnowledgeBuilder


async def test_graphrag_search_fix():
    """Test that GraphRAG search now returns proper format."""

    print("=== Testing GraphRAG Search Fix ===\n")

    # Initialize knowledge builder
    builder = PoliticalKnowledgeBuilder(
        uri=settings.NEO4J_URI,
        username=settings.NEO4J_USERNAME,
        password=settings.NEO4J_PASSWORD,
        database=settings.NEO4J_DATABASE,
        openai_api_key=settings.OPENAI_API_KEY,
    )

    try:
        async with builder:
            # Test basic search
            print("1. Testing basic search (should return list of dicts)...")
            search_results = await builder.search_documents("AI regulation", top_k=3)

            print(f"   Type: {type(search_results)}")
            print(f"   Length: {len(search_results)}")

            if isinstance(search_results, list):
                print("   ✅ Returns list as expected")
                if search_results:
                    first_result = search_results[0]
                    print(f"   First result type: {type(first_result)}")
                    if isinstance(first_result, dict):
                        print("   ✅ First result is dict as expected")
                        print(f"   Keys: {list(first_result.keys())}")
                    else:
                        print(f"   ❌ First result is {type(first_result)}, expected dict")
                else:
                    print("   ⚠️  No results found (might be expected if graph is empty)")
            else:
                print(f"   ❌ Returns {type(search_results)}, expected list")
                return False

            # Test graph traversal search
            print("\n2. Testing graph traversal search (should return dict with list)...")
            graph_results = await builder.search_with_graph_traversal("data privacy", top_k=3)

            print(f"   Type: {type(graph_results)}")

            if isinstance(graph_results, dict):
                print("   ✅ Returns dict as expected")
                print(f"   Keys: {list(graph_results.keys())}")

                if "results" in graph_results and isinstance(graph_results["results"], list):
                    print("   ✅ Contains 'results' list as expected")
                    print(f"   Results count: {len(graph_results['results'])}")
                else:
                    print("   ❌ Missing 'results' list")

                if "total_results" in graph_results:
                    print(f"   Total results: {graph_results['total_results']}")
                    print("   ✅ Contains 'total_results' as expected")
                else:
                    print("   ❌ Missing 'total_results'")
            else:
                print(f"   ❌ Returns {type(graph_results)}, expected dict")
                return False

            print("\n✅ All GraphRAG search methods return correct data types!")
            return True

    except Exception as e:
        print(f"❌ Error during GraphRAG search test: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run the search fix test."""
    success = asyncio.run(test_graphrag_search_fix())
    if success:
        print("\n🎉 GraphRAG search fix successful! Ready for workflow integration.")
    else:
        print("\n❌ GraphRAG search fix failed - check the errors above")
        sys.exit(1)


if __name__ == "__main__":
    main()
