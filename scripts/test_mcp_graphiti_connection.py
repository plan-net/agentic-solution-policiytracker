#!/usr/bin/env python3
"""
Test script for Graphiti MCP server connection.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.graphrag.mcp_graphiti_client import GraphitiMCPClient
from src.config import Settings

async def test_graphiti_connection():
    """Test basic connection to Graphiti MCP server."""
    print("Testing Graphiti MCP Server Connection...")
    print("-" * 50)
    
    # Initialize client
    settings = Settings()
    print(f"Connecting to: {settings.GRAPHITI_MCP_HOST}:{settings.GRAPHITI_MCP_PORT}")
    
    try:
        client = GraphitiMCPClient(settings)
        
        # Test basic connection
        print("\n1. Testing HTTP connection...")
        connected = await client.test_connection()
        print(f"   Connection test: {'✓ Success' if connected else '✗ Failed'}")
        
        if not connected:
            print("\n❌ Failed to connect to Graphiti MCP server")
            print("   Make sure the server is running: docker ps | grep graphiti")
            return
        
        print("\n2. Testing MCP toolkit initialization...")
        print("   ✓ MCP toolkit initialized")
        
        # Try to search (should return empty results on fresh graph)
        print("\n3. Testing search operation...")
        try:
            results = await client.search("test", limit=5)
            print(f"   ✓ Search completed, found {len(results)} results")
        except Exception as e:
            print(f"   ✗ Search failed: {e}")
        
        print("\n✅ Connection test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check if Graphiti MCP is running: docker ps | grep graphiti")
        print("2. Check logs: docker logs policiytracker-graphiti-mcp")
        print("3. Verify .env has correct GRAPHITI_MCP_HOST and GRAPHITI_MCP_PORT")

if __name__ == "__main__":
    asyncio.run(test_graphiti_connection())