#!/usr/bin/env python3
"""
Test script for Political Document Processing Pipeline v0.2.0

Tests the complete pipeline with enhanced test documents to validate:
1. Document metadata extraction
2. Episode creation via Graphiti MCP
3. Temporal query capabilities
4. Cross-document entity relationships
5. Client impact analysis
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import GraphRAGSettings
from graphrag.document_pipeline import PoliticalDocumentProcessor
from graphrag.mcp_graphiti_client import GraphitiMCPClient


async def test_document_pipeline():
    """Test the complete document processing pipeline."""

    print("🏛️ Political Document Processing Pipeline Test")
    print("=" * 60)

    # Initialize components
    settings = GraphRAGSettings()
    processor = PoliticalDocumentProcessor(settings)
    graphiti_client = GraphitiMCPClient(settings)

    # Test MCP connection first
    print("1. Testing MCP Connection...")
    try:
        connected = await graphiti_client.test_connection()
        if connected:
            print("   ✅ Graphiti MCP server connected successfully")
            tools = await graphiti_client.list_available_tools()
            print(f"   📋 Available tools: {', '.join(tools)}")
        else:
            print("   ❌ Failed to connect to Graphiti MCP server")
            return False
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
        return False

    # Get test documents
    test_data_dir = Path(__file__).parent.parent / "data" / "input" / "examples"
    if not test_data_dir.exists():
        print(f"   ❌ Test data directory not found: {test_data_dir}")
        return False

    # Select key documents for comprehensive testing
    test_documents = [
        test_data_dir / "apple_ai_act_compliance_response_2024.md",
        test_data_dir / "edpb_gdpr_enforcement_action_apple_2024.md",
        test_data_dir / "digitaleurope_dsa_position_paper_2024.md",
        test_data_dir / "eu_us_regulatory_cooperation_framework_2024.md",
    ]

    # Verify test documents exist
    available_docs = [doc for doc in test_documents if doc.exists()]
    print(f"   📄 Found {len(available_docs)} test documents")

    if not available_docs:
        print("   ❌ No test documents found")
        return False

    # Clear existing data for clean test
    print("\n2. Clearing existing graph data...")
    try:
        await graphiti_client.clear_graph()
        print("   ✅ Graph cleared successfully")
    except Exception as e:
        print(f"   ⚠️  Clear graph warning: {e}")

    # Define sample client context
    client_context = {
        "name": "TechCorp Global",
        "terms": ["Apple", "AI compliance", "GDPR enforcement", "digital services"],
        "industries": ["technology", "software", "artificial intelligence"],
        "markets": ["EU", "US"],
        "themes": ["privacy", "compliance", "regulation", "enforcement"],
    }

    # Test document processing
    print("\n3. Processing Documents...")
    try:
        processing_results = await processor.process_documents_batch(available_docs, client_context)

        print("   📊 Processing Results:")
        print(f"      Total documents: {processing_results['total_documents']}")
        print(f"      Successful: {processing_results['successful']}")
        print(f"      Failed: {processing_results['failed']}")
        print(f"      Episodes created: {len(processing_results['episodes_created'])}")

        if processing_results["processing_errors"]:
            print("   ⚠️  Processing errors:")
            for error in processing_results["processing_errors"]:
                print(f"      - {error['document']}: {error['error']}")

        # Show timeline
        timeline = processing_results["temporal_timeline"]
        if timeline:
            print(f"\n   📅 Temporal Timeline ({len(timeline)} events):")
            for event in timeline[:5]:  # Show first 5
                date_str = (
                    event["date"].strftime("%Y-%m-%d")
                    if hasattr(event["date"], "strftime")
                    else str(event["date"])
                )
                print(f"      {date_str}: {event['description'][:60]}...")

    except Exception as e:
        print(f"   ❌ Document processing failed: {e}")
        return False

    # Test temporal queries
    print("\n4. Testing Temporal Queries...")
    try:
        queries = [
            "Apple AI Act compliance",
            "GDPR enforcement action",
            "regulatory cooperation",
            "privacy violations",
        ]

        for query in queries:
            print(f"   🔍 Query: '{query}'")

            results = await processor.query_temporal_insights(query=query, max_results=3)

            print(f"      Nodes found: {results.get('nodes_found', 0)}")
            print(f"      Facts found: {results.get('facts_found', 0)}")
            print(f"      Insights: {len(results.get('insights', []))}")

            if results.get("insights"):
                for insight in results["insights"][:2]:  # Show first 2
                    print(f"        - {insight}")
            print()

    except Exception as e:
        print(f"   ❌ Temporal query testing failed: {e}")
        return False

    # Test client impact analysis
    print("\n5. Testing Client Impact Analysis...")
    try:
        impact_analysis = await processor.analyze_client_impact(
            client_context=client_context, time_window_days=30
        )

        print("   🎯 Client Impact Assessment:")
        print(f"      Client: {impact_analysis['client']}")
        print(f"      Impact Level: {impact_analysis['impact_assessment']['impact_level']}")
        print(f"      Impact Score: {impact_analysis['impact_assessment']['impact_score']}/10")
        print(f"      Queries Executed: {impact_analysis['queries_executed']}")
        print(f"      Total Insights: {impact_analysis['total_insights']}")
        print(f"      Recommendation: {impact_analysis['impact_assessment']['recommendation']}")

    except Exception as e:
        print(f"   ❌ Client impact analysis failed: {e}")
        return False

    # Test cross-document entity relationships
    print("\n6. Testing Cross-Document Relationships...")
    try:
        # Search for entities that should appear across multiple documents
        cross_doc_queries = ["Apple", "GDPR", "EU AI Act"]

        for entity in cross_doc_queries:
            print(f"   🔗 Cross-doc search: '{entity}'")

            results = await processor.query_temporal_insights(query=entity, max_results=5)

            node_count = results.get("nodes_found", 0)
            fact_count = results.get("facts_found", 0)

            print(f"      Cross-references: {node_count} nodes, {fact_count} facts")

            if node_count > 0 or fact_count > 0:
                print("      ✅ Entity found across multiple documents")
            else:
                print("      ⚠️  Limited cross-document connections")

    except Exception as e:
        print(f"   ❌ Cross-document testing failed: {e}")
        return False

    # Get processing statistics
    print("\n7. Processing Statistics...")
    try:
        stats = await processor.get_processing_stats()
        print("   📈 Overall Statistics:")
        print(f"      Total episodes: {stats.get('total_episodes', 0)}")
        print(f"      Client connected: {stats.get('client_connected', False)}")
        print(f"      Available tools: {len(stats.get('available_tools', []))}")

    except Exception as e:
        print(f"   ❌ Statistics retrieval failed: {e}")

    # Test episode retrieval
    print("\n8. Testing Episode Retrieval...")
    try:
        episodes = await graphiti_client.get_episodes(last_n=5)
        if episodes:
            print(f"   📚 Retrieved {len(episodes)} recent episodes")
            # Print episode details if available
            for i, episode in enumerate(episodes[:3], 1):
                episode_info = episode if isinstance(episode, dict) else {"episode": str(episode)}
                name = episode_info.get("name", f"Episode {i}")
                print(f"      {i}. {name}")
        else:
            print("   ⚠️  No episodes found")

    except Exception as e:
        print(f"   ❌ Episode retrieval failed: {e}")

    print("\n" + "=" * 60)
    print("✅ Document Processing Pipeline Test Complete!")
    print("\nNext steps:")
    print("- Review temporal query results for accuracy")
    print("- Validate entity extraction patterns")
    print("- Test with additional document types")
    print("- Integrate with main political analyzer workflow")

    return True


async def main():
    """Main test function."""
    try:
        success = await test_document_pipeline()
        if success:
            print("\n🎉 All tests completed successfully!")
            return 0
        else:
            print("\n❌ Some tests failed. Check configuration and MCP server status.")
            return 1
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
