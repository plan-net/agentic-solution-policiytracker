#!/usr/bin/env python3
"""Test GraphRAG with Langfuse prompt integration."""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import settings
from src.graphrag.knowledge_builder import PoliticalKnowledgeBuilder


async def test_graphrag_langfuse_integration():
    """Test the complete GraphRAG + Langfuse workflow."""

    print("=== Testing GraphRAG with Langfuse Integration ===\n")

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
            print("1. Testing basic GraphRAG search...")
            search_query = "AI regulation and data privacy"
            search_results = await builder.search_documents(search_query, top_k=3)
            print(f"   Found {len(search_results)} basic search results")

            # Test graph traversal search
            print("\n2. Testing graph traversal search...")
            graph_results = await builder.search_with_graph_traversal(search_query, top_k=3)
            print(f"   Graph traversal results: {graph_results.get('total_results', 0)} items")
            print(
                f"   Political entities found: {graph_results.get('political_entities_found', 0)}"
            )
            print(f"   Regulations found: {graph_results.get('regulations_found', 0)}")

            # Mock company context for testing
            company_context = {
                "terms": ["technology", "AI", "data protection", "privacy"],
                "industries": ["technology", "software", "AI"],
                "markets": ["US", "EU", "global"],
                "themes": ["regulatory compliance", "data privacy", "AI governance"],
                "strategic_focus": "AI regulation compliance and business impact",
            }

            # Test entity analysis with Langfuse
            print("\n3. Testing GraphRAG entity analysis with Langfuse prompts...")
            entity_analysis = await builder.analyze_entities_with_langfuse(
                query_results=search_results,
                company_context=company_context,
                query_topic=search_query,
            )
            print(f"   Entity analysis type: {entity_analysis.get('analysis_type')}")
            print(f"   Entities analyzed: {entity_analysis.get('entities_analyzed', 0)}")
            print(f"   Relationships analyzed: {entity_analysis.get('relationships_analyzed', 0)}")

            if "error" in entity_analysis:
                print(f"   Error in entity analysis: {entity_analysis['error']}")
            else:
                print(f"   Confidence: {entity_analysis.get('confidence', 'N/A')}")

                # Show key actors if available
                key_actors = entity_analysis.get("key_actors", [])
                if key_actors:
                    print(f"   Key actors found: {len(key_actors)}")
                    for actor in key_actors[:2]:  # Show first 2
                        print(
                            f"     - {actor.get('name', 'Unknown')}: {actor.get('type', 'Unknown type')}"
                        )

            # Test relationship insights with Langfuse
            print("\n4. Testing GraphRAG relationship insights with Langfuse prompts...")
            relationship_insights = await builder.generate_relationship_insights(
                graph_traversal_results=graph_results,
                company_context=company_context,
                time_horizon="6-12 months",
            )
            print(f"   Relationship insights type: {relationship_insights.get('analysis_type')}")
            print(f"   Time horizon: {relationship_insights.get('time_horizon')}")

            network_metrics = relationship_insights.get("network_metrics", {})
            if network_metrics:
                print(f"   Total relationships: {network_metrics.get('total_relationships', 0)}")
                print(f"   Entity types: {network_metrics.get('entity_types', 0)}")
                print(
                    f"   Relationship types: {len(network_metrics.get('relationship_types', []))}"
                )

            if "error" in relationship_insights:
                print(f"   Error in relationship insights: {relationship_insights['error']}")
            else:
                print(f"   Confidence: {relationship_insights.get('confidence', 'N/A')}")

                # Show strategic recommendations if available
                recommendations = relationship_insights.get("strategic_recommendations", [])
                if recommendations:
                    print(f"   Strategic recommendations: {len(recommendations)}")
                    for rec in recommendations[:2]:  # Show first 2
                        print(
                            f"     - {rec.get('priority', 'Unknown')}: {rec.get('description', 'No description')}"
                        )

            # Mock traditional analysis results for comparison
            traditional_results = {
                "method": "keyword_scoring",
                "confidence": 0.75,
                "key_findings": [
                    "AI regulation mentions increase",
                    "Data privacy concerns prominent",
                    "Compliance requirements expanding",
                ],
                "sentiment": "neutral",
                "urgency": "medium",
            }

            # Test comparative analysis
            print("\n5. Testing comparative analysis with Langfuse prompts...")
            comparison = await builder.compare_with_traditional_analysis(
                traditional_results=traditional_results,
                graphrag_entity_analysis=entity_analysis,
                graphrag_relationship_insights=relationship_insights,
                analysis_topic=search_query,
                company_context=company_context,
            )
            print(f"   Comparison analysis type: {comparison.get('analysis_type')}")
            print(f"   Traditional method: {comparison.get('traditional_method')}")
            print(f"   GraphRAG methods: {comparison.get('graphrag_methods', [])}")

            if "error" in comparison:
                print(f"   Error in comparison: {comparison['error']}")
            else:
                print(f"   Confidence: {comparison.get('confidence', 'N/A')}")

                # Show unique GraphRAG insights if available
                unique_insights = comparison.get("unique_graphrag_insights", [])
                if unique_insights:
                    print(f"   Unique GraphRAG insights: {len(unique_insights)}")
                    for insight in unique_insights[:2]:  # Show first 2
                        print(
                            f"     - {insight.get('insight_type', 'Unknown')}: {insight.get('strategic_value', 'Unknown value')}"
                        )

            # Get graph statistics
            print("\n6. Graph statistics:")
            stats = await builder.get_graph_stats()
            for key, value in stats.items():
                print(f"   {key.capitalize()}: {value}")

            print("\n=== GraphRAG + Langfuse Integration Test Complete ===")

            # Save test results to file
            test_results = {
                "search_query": search_query,
                "basic_search_count": len(search_results),
                "graph_search_results": graph_results.get("total_results", 0),
                "entity_analysis": entity_analysis,
                "relationship_insights": relationship_insights,
                "comparative_analysis": comparison,
                "graph_stats": stats,
            }

            output_file = project_root / "data" / "output" / "graphrag_langfuse_test_results.json"
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(test_results, f, indent=2, ensure_ascii=False)

            print(f"\nTest results saved to: {output_file}")

    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback

        traceback.print_exc()


def main():
    """Run the test."""
    asyncio.run(test_graphrag_langfuse_integration())


if __name__ == "__main__":
    main()
