#!/usr/bin/env python3
"""
Test actual tool execution to see what data is returned from the knowledge graph.
This will help identify if the issue is with data retrieval or answer synthesis.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from chat.agent.nodes import _create_tools_map, initialize_nodes
from graphrag.mcp_graphiti_client import MCPGraphitiClient
from config import settings
from langchain_openai import ChatOpenAI


async def test_tool_execution():
    """Test actual tool execution with real queries."""
    print("🔍 Testing Tool Execution...")
    print("=" * 60)
    
    # 1. Initialize Graphiti client
    print("1. Initializing Graphiti client...")
    client = MCPGraphitiClient(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USERNAME,
        password=settings.NEO4J_PASSWORD
    )
    await client.connect()
    print("✓ Graphiti client connected")
    
    # 2. Initialize nodes and create tools
    print("\n2. Initializing nodes and creating tools...")
    llm = ChatOpenAI(model="gpt-4", api_key=os.getenv("OPENAI_API_KEY"))
    initialize_nodes(llm, client, os.getenv("OPENAI_API_KEY"))
    
    tools_map = _create_tools_map()
    print(f"✓ Created {len(tools_map)} tools")
    
    # Get the search tool
    search_tool = tools_map.get("search")
    if not search_tool:
        print("❌ No search tool found!")
        return
    
    print(f"✓ Found search tool: {search_tool.name}")
    print(f"✓ Search tool client: {search_tool.client}")
    
    # 3. Test queries that should return different results
    test_queries = [
        "EU AI Act",
        "Digital Services Act", 
        "Apple compliance",
        "GDPR enforcement",
        "climate change renewable energy"  # This shouldn't match our political data
    ]
    
    print("\n3. Testing queries...")
    print("-" * 40)
    
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        try:
            # Execute the tool
            result = await search_tool._arun(query=query, limit=5)
            
            print(f"📊 Result type: {type(result)}")
            print(f"📊 Result length: {len(str(result))}")
            
            # Show first 500 characters
            result_preview = str(result)[:500]
            print(f"📊 Result preview:\n{result_preview}")
            
            if len(str(result)) > 500:
                print("... (truncated)")
                
        except Exception as e:
            print(f"❌ Error executing query '{query}': {e}")
    
    # 4. Test direct Graphiti search
    print("\n\n4. Testing direct Graphiti search...")
    print("-" * 40)
    
    try:
        direct_results = await client.search("EU AI Act", limit=5)
        print(f"📊 Direct search returned: {len(direct_results)} results")
        for i, result in enumerate(direct_results[:3]):  # Show first 3
            print(f"  {i+1}. {result}")
    except Exception as e:
        print(f"❌ Direct search error: {e}")
    
    # 5. Check what's actually in the knowledge graph
    print("\n\n5. Checking knowledge graph contents...")
    print("-" * 40)
    
    try:
        # Try a very broad search to see what's there
        all_results = await client.search("", limit=10)  # Empty query to get anything
        print(f"📊 Broad search returned: {len(all_results)} results")
        for i, result in enumerate(all_results[:5]):  # Show first 5
            print(f"  {i+1}. {result}")
    except Exception as e:
        print(f"❌ Broad search error: {e}")
    
    # 6. Check graph statistics
    print("\n\n6. Checking graph statistics...")
    print("-" * 40)
    
    try:
        stats = await client.get_graph_stats()
        print(f"📊 Graph stats: {stats}")
    except Exception as e:
        print(f"❌ Stats error: {e}")
    
    await client.close()
    print("\n✓ Test completed!")


if __name__ == "__main__":
    asyncio.run(test_tool_execution())