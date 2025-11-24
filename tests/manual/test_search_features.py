"""Test script to demonstrate all 3 search tool improvements."""
import asyncio
import json
import os

from graphiti_core import Graphiti

from src.chat.tools.search import GraphitiSearchTool


async def test_all_features():
    """Test all 3 new search features: relevance scores, source extraction, structured output."""

    # Get Neo4j credentials
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password123")

    print("🔧 Connecting to Neo4j...")
    client = Graphiti(neo4j_uri, neo4j_user, neo4j_password)
    tool = GraphitiSearchTool(graphiti_client=client)

    # Test query
    query = "Google regulatory exposure DMA DSA AI Act"

    # ========================================================================
    # TEST 1: Text Output - Shows Relevance Scores + Sources
    # ========================================================================
    print("\n" + "=" * 80)
    print("📝 TEST 1: Text Output Format (Relevance Scores + Sources)")
    print("=" * 80)
    print(f"Query: {query}")
    print()

    text_result = await tool._arun(
        query=query,
        limit=5,
        search_type="comprehensive",
        output_format="text",  # Default format
    )

    print(text_result)

    # ========================================================================
    # TEST 2: Structured Output - Shows Complete Graph Data
    # ========================================================================
    print("\n" + "=" * 80)
    print("📊 TEST 2: Structured Output Format (Graph Visualization Data)")
    print("=" * 80)
    print(f"Query: {query}")
    print()

    structured_result = await tool._arun(
        query=query,
        limit=5,
        search_type="comprehensive",
        output_format="structured",  # JSON format
    )

    print(json.dumps(structured_result, indent=2))

    # ========================================================================
    # TEST 3: Feature Highlights
    # ========================================================================
    print("\n" + "=" * 80)
    print("✨ FEATURE HIGHLIGHTS")
    print("=" * 80)

    if isinstance(structured_result, dict):
        # Count features
        total_results = structured_result.get("total_results", 0)
        results = structured_result.get("results", [])
        sources = structured_result.get("sources", [])
        nodes = structured_result.get("graph_data", {}).get("nodes", [])
        edges = structured_result.get("graph_data", {}).get("edges", [])

        print("\n1. 🎯 Relevance Scores:")
        print(f"   - Total results: {total_results}")
        print(f"   - Results with scores: {len([r for r in results if r.get('relevance_score')])}")
        if results:
            scores = [r.get("relevance_score", 0) for r in results if r.get("relevance_score")]
            if scores:
                print(f"   - Score range: {min(scores):.3f} to {max(scores):.3f}")
                print(
                    f"   - Example: Result #1 has score {results[0].get('relevance_score', 0):.3f}"
                )

        print("\n2. 📰 Source Extraction:")
        print(f"   - Unique sources found: {len(sources)}")
        if sources:
            print("   - Sources:")
            for source in sources[:3]:  # Show first 3
                print(f"     • {source.get('title', 'N/A')}")
                print(f"       URL: {source.get('url', 'N/A')}")

        print("\n3. 📊 Structured Output (Graph Data):")
        print(f"   - Nodes extracted: {len(nodes)}")
        print(f"   - Edges extracted: {len(edges)}")
        if nodes:
            enriched_nodes = [n for n in nodes if n.get("name") != "Unknown"]
            print(f"   - Nodes with enriched names: {len(enriched_nodes)}")
            print("   - Example nodes:")
            for node in nodes[:3]:  # Show first 3
                print(f"     • {node.get('name', 'Unknown')} ({node.get('type', 'N/A')})")

    # Close connection
    await client.close()

    print("\n" + "=" * 80)
    print("✅ All tests completed!")
    print("=" * 80)
    print("\n💡 Next Steps:")
    print("   1. Open WebUI at http://localhost:3000 to test via chat interface")
    print("   2. Ask questions like: 'What regulatory changes affect Google?'")
    print("   3. Check the response for relevance scores and sources")
    print()


if __name__ == "__main__":
    asyncio.run(test_all_features())
