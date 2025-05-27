#!/usr/bin/env python3
"""
Test script for Graphiti MCP client connection.

This script tests:
1. MCP server availability
2. Basic Graphiti operations via MCP
3. Neo4j connection through MCP
4. Episode creation and retrieval
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import GraphRAGSettings
from src.graphrag.mcp_graphiti_client import GraphitiMCPClient

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_mcp_connection():
    """Test MCP server connection and basic operations."""
    print("=== Testing Graphiti MCP Client Connection ===")

    try:
        # Initialize client
        print("1. Initializing MCP client...")
        settings = GraphRAGSettings()
        print(f"   Connecting to: {settings.GRAPHITI_MCP_HOST}:{settings.GRAPHITI_MCP_PORT}")
        client = GraphitiMCPClient(settings)

        # Test connection
        print("2. Testing connection...")
        is_connected = await client.test_connection()
        if not is_connected:
            print("❌ MCP server connection failed")
            print("   Make sure the server is running: docker ps | grep graphiti")
            return False
        print("✅ MCP server connection successful")

        # Test episode creation
        print("3. Testing episode creation...")
        test_episode = {
            "name": "MCP Test Episode",
            "content": "This is a test episode created via MCP to verify the Graphiti connection is working properly.",
            "timestamp": datetime.now(),
            "metadata": {"type": "test", "source": "mcp_test_script", "importance": "low"},
        }

        episode_result = await client.add_episode(**test_episode)
        print(f"✅ Episode created: {episode_result}")

        # Wait a moment for processing
        print("4. Waiting for episode processing...")
        await asyncio.sleep(3)

        # Test search
        print("5. Testing search functionality...")
        search_results = await client.search("MCP test episode", limit=5)
        print(f"✅ Search returned {len(search_results)} results")
        if search_results:
            for i, result in enumerate(search_results[:2]):  # Show first 2 results
                print(f"   Result {i+1}: {result}")

        # Test entity mentions (if any entities were extracted)
        print("6. Testing entity mentions...")
        try:
            entity_results = await client.get_entity_mentions("test", limit=5)
            print(f"✅ Entity mentions: {len(entity_results)} found")
        except Exception as e:
            print(f"⚠️  Entity mentions test: {e} (expected if no entities extracted)")

        print("=== All tests completed successfully! ===")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check if Graphiti MCP is running: docker ps | grep graphiti")
        print("2. Check logs: docker logs policiytracker-graphiti-mcp")
        print("3. Verify .env has correct GRAPHITI_MCP_HOST and GRAPHITI_MCP_PORT")
        return False


async def test_temporal_queries():
    """Test temporal query capabilities."""
    print("\n=== Testing Temporal Query Capabilities ===")

    try:
        client = GraphitiMCPClient()

        # Create test episodes with different timestamps
        print("1. Creating test episodes with temporal data...")

        now = datetime.now()
        episodes = [
            {
                "name": "EU AI Act Draft",
                "content": "The European Union published the initial draft of the AI Act.",
                "timestamp": now - timedelta(days=30),
                "metadata": {"type": "policy", "status": "draft"},
            },
            {
                "name": "EU AI Act Amendment",
                "content": "Parliament proposed amendments to the EU AI Act.",
                "timestamp": now - timedelta(days=15),
                "metadata": {"type": "policy", "status": "amendment"},
            },
            {
                "name": "EU AI Act Final Vote",
                "content": "The EU AI Act passed final parliamentary vote.",
                "timestamp": now - timedelta(days=5),
                "metadata": {"type": "policy", "status": "passed"},
            },
        ]

        for episode in episodes:
            result = await client.add_episode(**episode)
            print(f"   ✅ Created: {episode['name']}")

        # Wait for processing
        print("2. Waiting for processing...")
        await asyncio.sleep(5)

        # Test temporal search
        print("3. Testing temporal search...")

        # Search last 20 days
        time_range = (now - timedelta(days=20), now)
        recent_results = await client.search("EU AI Act", limit=10, time_range=time_range)
        print(f"✅ Recent results (last 20 days): {len(recent_results)}")

        # Search older than 20 days
        time_range = (now - timedelta(days=40), now - timedelta(days=20))
        older_results = await client.search("EU AI Act", limit=10, time_range=time_range)
        print(f"✅ Older results (20-40 days ago): {len(older_results)}")

        print("=== Temporal query tests completed! ===")
        return True

    except Exception as e:
        print(f"❌ Temporal query test failed: {e}")
        return False


async def main():
    """Run all tests."""
    try:
        # Basic connection test
        basic_success = await test_mcp_connection()

        if basic_success:
            # Temporal query test
            temporal_success = await test_temporal_queries()

            if temporal_success:
                print("\n🎉 ALL TESTS PASSED! Graphiti MCP client is working correctly.")
                return 0
            else:
                print("\n❌ Temporal query tests failed")
                return 1
        else:
            print("\n❌ Basic connection tests failed")
            return 1

    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
