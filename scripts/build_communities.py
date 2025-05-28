#!/usr/bin/env python3
"""
Build communities from existing knowledge graph using Graphiti.

This script runs community detection on the existing knowledge graph
to identify document clusters and thematic groups.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flows.shared.graphiti_client import SharedGraphitiClient


async def build_communities():
    """Build communities from existing knowledge graph."""
    try:
        print("🔍 Analyzing graph structure...")
        async with SharedGraphitiClient() as client:
            communities = await client.build_communities(timeout_seconds=60)
            
            if communities:
                print(f"✅ Successfully built {len(communities)} communities!")
                print()
                for i, community in enumerate(communities[:5], 1):
                    title = getattr(community, 'title', f'Community {i}')
                    member_count = getattr(community, 'member_count', 'unknown')
                    print(f"  {i}. {title} ({member_count} members)")
                
                if len(communities) > 5:
                    print(f"  ... and {len(communities) - 5} more communities")
                    
                print()
                print("💡 View communities in Neo4j Browser: http://localhost:7474")
                print("   Query: MATCH (c:Community)<-[:MEMBER_OF]-(n) RETURN c.title, count(n) as Members")
                
            else:
                print("⚠️  No communities found or operation timed out")
                print("💡 Try with more documents or check graph connectivity")
                
    except Exception as e:
        print(f"❌ Community building failed: {e}")
        print("💡 Make sure Neo4j is running and you have processed documents first")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(build_communities())
    sys.exit(exit_code)