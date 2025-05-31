#!/usr/bin/env python3
"""
Simple test to see what data is actually available in the knowledge graph.
This will help identify if the issue is with data availability or tool execution.
"""

import asyncio
import os
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


async def test_data_availability():
    """Test what data is actually available in the knowledge graph."""
    print("🔍 Testing Knowledge Graph Data Availability...")
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
    
    # 2. Test basic search functionality
    print("\n2. Testing basic search functionality...")
    test_queries = [
        "EU AI Act",
        "Digital Services Act", 
        "Apple",
        "GDPR",
        "Meta",
        "regulation",
        "policy",
        "European",
        "",  # Empty query to see anything
        "act",
        "law",
        "data"
    ]
    
    print("-" * 40)
    
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        try:
            # Use the simple search method first
            results = await client.search(query)
            
            if results:
                print(f"📊 Found {len(results)} results:")
                for i, result in enumerate(results[:2], 1):  # Show first 2
                    print(f"  {i}. Type: {type(result).__name__}")
                    print(f"     Content: {str(result)[:200]}...")
            else:
                print("📊 No results found")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # 3. Test with _search method (more advanced)
    print("\n\n3. Testing advanced _search method...")
    print("-" * 40)
    
    try:
        advanced_results = await client._search("EU AI Act")
        print(f"📊 Advanced search results type: {type(advanced_results)}")
        
        if hasattr(advanced_results, 'nodes'):
            print(f"📊 Nodes found: {len(advanced_results.nodes) if advanced_results.nodes else 0}")
            if advanced_results.nodes:
                for i, node in enumerate(advanced_results.nodes[:2], 1):
                    print(f"  Node {i}: {type(node).__name__} - {str(node)[:150]}...")
        
        if hasattr(advanced_results, 'edges'):
            print(f"📊 Edges found: {len(advanced_results.edges) if advanced_results.edges else 0}")
            if advanced_results.edges:
                for i, edge in enumerate(advanced_results.edges[:2], 1):
                    print(f"  Edge {i}: {type(edge).__name__} - {str(edge)[:150]}...")
        
        if hasattr(advanced_results, 'episodes'):
            print(f"📊 Episodes found: {len(advanced_results.episodes) if advanced_results.episodes else 0}")
            
    except Exception as e:
        print(f"❌ Advanced search error: {e}")
    
    # 4. Check if there's any data at all
    print("\n\n4. Checking for any data in the graph...")
    print("-" * 40)
    
    try:
        # Try to get some stats about the graph
        # This is a workaround since we don't have direct access to graph stats
        broad_search = await client.search("")
        print(f"📊 Broad search returned: {len(broad_search)} items")
        
        if broad_search:
            print("📊 Sample data found:")
            for i, item in enumerate(broad_search[:3], 1):
                print(f"  {i}. {type(item).__name__}: {str(item)[:200]}...")
        else:
            print("⚠️  WARNING: No data found in knowledge graph!")
            print("   This suggests the graph may be empty or there's a connection issue.")
        
    except Exception as e:
        print(f"❌ Broad search error: {e}")
    
    # 5. Test direct Neo4j query if possible
    print("\n\n5. Testing direct Neo4j connection...")
    print("-" * 40)
    
    try:
        # Try to access the underlying Neo4j driver if available
        if hasattr(client, 'driver') or hasattr(client, '_driver'):
            print("✓ Neo4j driver found in client")
            # Could try direct Cypher queries here if needed
        else:
            print("ℹ️  No direct Neo4j driver access available")
            
    except Exception as e:
        print(f"❌ Driver check error: {e}")
    
    await client.close()
    print("\n✓ Test completed!")
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print("- If no results were found for basic queries like 'EU AI Act',")
    print("  the knowledge graph may be empty or not properly populated.")
    print("- If results were found but are unrelated to political content,")
    print("  there may be data ingestion issues.")
    print("- Check the data ingestion pipeline and document processing.")


if __name__ == "__main__":
    asyncio.run(test_data_availability())