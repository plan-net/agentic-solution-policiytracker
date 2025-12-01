"""Debug script to investigate Graphiti search result structure."""

import asyncio
import logging
import os
from graphiti_core import Graphiti

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def debug_search_internals():
    """Investigate search result structure to fix known issues."""
    
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password123")
    
    client = Graphiti(neo4j_uri, neo4j_user, neo4j_password)
    
    print("=" * 80)
    print("DEBUGGING SEARCH RESULT INTERNALS")
    print("=" * 80)
    print()
    
    query = "EU AI Act"
    print(f"Query: {query}\n")
    
    # Get search results
    from graphiti_core.search.search_config_recipes import COMBINED_HYBRID_SEARCH_CROSS_ENCODER
    search_results = await client._search(query=query, config=COMBINED_HYBRID_SEARCH_CROSS_ENCODER)
    
    print("=" * 80)
    print("1. INVESTIGATING RELEVANCE SCORES")
    print("=" * 80)
    
    if hasattr(search_results, "edges") and search_results.edges:
        edge = search_results.edges[0]
        print(f"\nFirst Edge Attributes:")
        print(f"  Type: {type(edge)}")
        print(f"  Available attributes: {dir(edge)}")
        
        # Check for score attributes
        score_attrs = ["score", "similarity", "distance", "relevance", "rank", "weight"]
        print(f"\n  Checking score attributes:")
        for attr in score_attrs:
            if hasattr(edge, attr):
                val = getattr(edge, attr)
                print(f"    {attr}: {val} (type: {type(val)})")
            else:
                print(f"    {attr}: NOT FOUND")
    
    print("\n" + "=" * 80)
    print("2. INVESTIGATING EPISODE DATA FOR SOURCE EXTRACTION")
    print("=" * 80)
    
    if hasattr(search_results, "edges") and search_results.edges:
        edge = search_results.edges[0]
        
        print(f"\n  Edge episodes attribute:")
        if hasattr(edge, "episodes"):
            print(f"    episodes: {edge.episodes}")
            print(f"    episodes type: {type(edge.episodes)}")
            
            if edge.episodes:
                print(f"\n  Fetching episode data for first episode...")
                episode_uuids = [str(ep) for ep in edge.episodes[:1]]
                try:
                    episode_data = await client.get_nodes_and_edges_by_episode(episode_uuids)
                    print(f"    Episode data type: {type(episode_data)}")
                    print(f"    Episode data attributes: {dir(episode_data)}")
                    
                    if hasattr(episode_data, "nodes"):
                        print(f"\n    Episode nodes count: {len(episode_data.nodes)}")
                        if episode_data.nodes:
                            node = episode_data.nodes[0]
                            print(f"    First node attributes: {dir(node)}")
                            
                            # Check for episode_body
                            if hasattr(node, "episode_body"):
                                body = node.episode_body
                                print(f"\n    ✅ episode_body exists!")
                                print(f"    Length: {len(body) if body else 0}")
                                if body:
                                    print(f"    Preview: {body[:200]}...")
                            else:
                                print(f"\n    ❌ episode_body NOT FOUND")
                                
                except Exception as e:
                    print(f"    Error fetching episode: {e}")
        else:
            print(f"    ❌ episodes attribute NOT FOUND")
        
        # Check episode_name
        print(f"\n  Edge episode_name attribute:")
        if hasattr(edge, "episode_name"):
            print(f"    episode_name: {edge.episode_name}")
        else:
            print(f"    ❌ episode_name NOT FOUND")
    
    print("\n" + "=" * 80)
    print("3. INVESTIGATING NODE DATA FOR NAME ENRICHMENT")
    print("=" * 80)
    
    if hasattr(search_results, "edges") and search_results.edges:
        edge = search_results.edges[0]
        
        print(f"\n  Edge node UUID attributes:")
        if hasattr(edge, "source_node_uuid"):
            print(f"    source_node_uuid: {edge.source_node_uuid}")
        else:
            print(f"    ❌ source_node_uuid NOT FOUND")
            
        if hasattr(edge, "target_node_uuid"):
            print(f"    target_node_uuid: {edge.target_node_uuid}")
        else:
            print(f"    ❌ target_node_uuid NOT FOUND")
        
        # Try to fetch node data by UUID
        if hasattr(edge, "source_node_uuid") and edge.source_node_uuid:
            print(f"\n  Attempting to fetch node by UUID...")
            try:
                # Check if client has a method to get node by UUID
                node_methods = [m for m in dir(client) if "node" in m.lower() and not m.startswith("_")]
                print(f"    Available node methods: {node_methods}")
                
                # Try get_node method if it exists
                if hasattr(client, "get_node"):
                    node = await client.get_node(str(edge.source_node_uuid))
                    print(f"\n    ✅ get_node() works!")
                    print(f"    Node type: {type(node)}")
                    print(f"    Node attributes: {dir(node)}")
                    if hasattr(node, "name"):
                        print(f"    Node name: {node.name}")
                else:
                    print(f"\n    ❌ get_node() method not found")
                    
            except Exception as e:
                print(f"    Error fetching node: {e}")
    
    await client.close()
    
    print("\n" + "=" * 80)
    print("DEBUG COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(debug_search_internals())
