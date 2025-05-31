#!/usr/bin/env python3
"""
Test to examine the actual content of EntityEdge objects returned by Graphiti search.
This will help us understand why the chat agent might be getting the wrong answers.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import settings

# Import Graphiti directly 
try:
    from graphiti_core import Graphiti
except ImportError:
    print("❌ graphiti_core not available. Install with: uv add graphiti-core")
    sys.exit(1)


async def test_edge_content():
    """Examine the actual content of EntityEdge objects."""
    print("🔍 Testing EntityEdge Content...")
    print("=" * 60)
    
    # 1. Initialize Graphiti client
    print("1. Initializing Graphiti client...")
    client = Graphiti(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USERNAME,
        password=settings.NEO4J_PASSWORD
    )
    await client.build_indices_and_constraints()
    print("✓ Graphiti client connected")
    
    # 2. Get search results for EU AI Act
    print("\n2. Getting EU AI Act search results...")
    results = await client.search("EU AI Act")
    
    if not results:
        print("❌ No results found!")
        return
    
    print(f"📊 Found {len(results)} results")
    
    # 3. Examine the first few results in detail
    print("\n3. Examining result details...")
    print("-" * 40)
    
    for i, result in enumerate(results[:3], 1):
        print(f"\n🔍 Result {i}:")
        print(f"  Type: {type(result).__name__}")
        print(f"  UUID: {result.uuid}")
        
        # Check for fact content
        if hasattr(result, 'fact'):
            print(f"  Fact: {result.fact}")
        else:
            print("  No 'fact' attribute")
        
        # Check for name
        if hasattr(result, 'name'):
            print(f"  Name: {result.name}")
        else:
            print("  No 'name' attribute")
        
        # Check for summary
        if hasattr(result, 'summary'):
            print(f"  Summary: {result.summary}")
        else:
            print("  No 'summary' attribute")
        
        # Check for episodes
        if hasattr(result, 'episodes'):
            print(f"  Episodes: {result.episodes}")
        else:
            print("  No 'episodes' attribute")
        
        # Show all attributes
        attrs = [attr for attr in dir(result) if not attr.startswith('_')]
        print(f"  All attributes: {attrs}")
        
        # Try to get the actual content
        print(f"  Raw content preview: {str(result)[:200]}...")
    
    # 4. Try to get nodes that should contain the actual content
    print("\n\n4. Trying to get entity nodes...")
    print("-" * 40)
    
    try:
        # Get the source and target node UUIDs from the first edge
        first_edge = results[0]
        source_uuid = first_edge.source_node_uuid
        target_uuid = first_edge.target_node_uuid
        
        print(f"First edge connects: {source_uuid} -> {target_uuid}")
        
        # Try to get node content
        # This might not work directly, but let's try
        # We need to find a method to get nodes by UUID
        
    except Exception as e:
        print(f"❌ Error getting node details: {e}")
    
    # 5. Try a different search approach to get nodes
    print("\n\n5. Trying advanced search to get nodes...")
    print("-" * 40)
    
    try:
        from graphiti_core.search.search_config_recipes import COMBINED_HYBRID_SEARCH_CROSS_ENCODER
        
        advanced_results = await client._search(
            query="EU AI Act",
            config=COMBINED_HYBRID_SEARCH_CROSS_ENCODER
        )
        
        print(f"📊 Advanced search results type: {type(advanced_results)}")
        
        if hasattr(advanced_results, 'nodes') and advanced_results.nodes:
            print(f"📊 Found {len(advanced_results.nodes)} nodes:")
            for i, node in enumerate(advanced_results.nodes[:2], 1):
                print(f"\n  Node {i}:")
                print(f"    Type: {type(node).__name__}")
                if hasattr(node, 'name'):
                    print(f"    Name: {node.name}")
                if hasattr(node, 'summary'):
                    print(f"    Summary: {node.summary[:200]}...")
                attrs = [attr for attr in dir(node) if not attr.startswith('_')]
                print(f"    Attributes: {attrs}")
        
        if hasattr(advanced_results, 'edges') and advanced_results.edges:
            print(f"📊 Found {len(advanced_results.edges)} edges:")
            for i, edge in enumerate(advanced_results.edges[:2], 1):
                print(f"\n  Edge {i}:")
                print(f"    Type: {type(edge).__name__}")
                if hasattr(edge, 'fact'):
                    print(f"    Fact: {edge.fact[:200]}...")
                attrs = [attr for attr in dir(edge) if not attr.startswith('_')]
                print(f"    Attributes: {attrs}")
        
    except Exception as e:
        print(f"❌ Advanced search error: {e}")
    
    await client.close()
    print("\n✓ Test completed!")


if __name__ == "__main__":
    asyncio.run(test_edge_content())