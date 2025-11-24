"""Test script to run the search tool with a specific query."""

import asyncio
import logging
import os
from graphiti_core import Graphiti
from src.chat.tools.search import GraphitiSearchTool

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_search_tool():
    """Test the search tool with Google regulatory query."""

    # Initialize Graphiti client
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password123")
    neo4j_database = os.getenv("NEO4J_DATABASE", "politicalmonitoring")

    logger.info(f"Connecting to Neo4j at {neo4j_uri}, database: {neo4j_database}")

    try:
        # Create Graphiti client
        client = Graphiti(neo4j_uri, neo4j_user, neo4j_password)

        # Create search tool
        search_tool = GraphitiSearchTool(graphiti_client=client)

        # Test query
        query = "Google regulatory exposure DMA DSA AI Act"

        print("=" * 80)
        print(f"TESTING SEARCH TOOL")
        print(f"Query: {query}")
        print("=" * 80)
        print()

        # Test 1: Text output with relevance scores
        print("Test 1: Text output with relevance scores (limit=5)")
        print("-" * 80)
        result = await search_tool._arun(
            query=query,
            limit=5,
            search_type="comprehensive",
            output_format="text"
        )
        print(result)
        print()

        # Test 2: Structured output with graph data
        print("\nTest 2: Structured output with graph data (limit=5)")
        print("-" * 80)
        result = await search_tool._arun(
            query=query,
            limit=5,
            search_type="comprehensive",
            output_format="structured"
        )

        import json
        print(json.dumps(result, indent=2))
        print()

        # Print graph data summary
        if "graph_data" in result:
            print(f"\nGraph Data Summary:")
            print(f"  Nodes: {len(result['graph_data']['nodes'])}")
            print(f"  Edges: {len(result['graph_data']['edges'])}")
            print()

        # Test 3: Entity-focused with structured output
        print("\nTest 3: Entity-focused search (structured)")
        print("-" * 80)
        result = await search_tool._arun(
            query=query,
            limit=3,
            search_type="entity_focused",
            output_format="structured"
        )

        # Just print summary for entity search
        print(f"Query: {result['query']}")
        print(f"Total Results: {result['total_results']}")
        print(f"Results Returned: {result['returned_results']}")
        print(f"\nTop {len(result['results'])} Entities:")
        for r in result['results']:
            score_text = f" [Score: {r['relevance_score']:.2f}]" if r['relevance_score'] else ""
            print(f"  {r['rank']}.{score_text} {r['name']} ({r['type']})")
        print()

        print("=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)

    except Exception as e:
        logger.error(f"Error during test: {e}", exc_info=True)
        raise
    finally:
        # Clean up
        if 'client' in locals():
            logger.info("Closing Graphiti client")
            await client.close()


if __name__ == "__main__":
    asyncio.run(test_search_tool())
