#!/usr/bin/env python3
"""
Build communities from existing knowledge graph using Graphiti.

This script runs community detection on the existing knowledge graph
to identify document clusters and thematic groups.

Features:
- Pre-flight checks (Neo4j connection, entity count)
- Verbose progress logging
- Timeout protection (default 5 minutes)
- Proper error handling
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def log(message: str, flush: bool = True):
    """Print with timestamp and immediate flush."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", flush=flush)


async def check_neo4j_connection(uri: str, user: str, password: str) -> dict:
    """Pre-flight check: verify Neo4j connection and get graph stats."""
    from neo4j import AsyncGraphDatabase

    log("🔌 Checking Neo4j connection...")

    try:
        driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

        async with driver.session() as session:
            # Check connectivity
            result = await session.run("RETURN 1 as connected")
            await result.single()
            log("   ✓ Connected to Neo4j")

            # Get entity count
            result = await session.run("MATCH (n:Entity) RETURN count(n) as count")
            record = await result.single()
            entity_count = record["count"] if record else 0
            log(f"   ✓ Found {entity_count} entities")

            # Get existing community count
            result = await session.run("MATCH (c:Community) RETURN count(c) as count")
            record = await result.single()
            community_count = record["count"] if record else 0
            if community_count > 0:
                log(f"   ⚠ Found {community_count} existing communities (will be replaced)")
            else:
                log("   ✓ No existing communities")

            # Get relationship count
            result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
            record = await result.single()
            rel_count = record["count"] if record else 0
            log(f"   ✓ Found {rel_count} relationships")

        await driver.close()

        return {
            "connected": True,
            "entity_count": entity_count,
            "community_count": community_count,
            "relationship_count": rel_count,
        }

    except Exception as e:
        log(f"   ✗ Connection failed: {e}")
        return {"connected": False, "error": str(e)}


async def build_communities(timeout_seconds: int = 300, verbose: bool = True):
    """
    Build communities from existing knowledge graph.

    Args:
        timeout_seconds: Maximum time to wait for community building (default 5 min)
        verbose: Enable verbose logging
    """
    # Get Neo4j credentials
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")

    log("=" * 60)
    log("🏘️  GRAPHITI COMMUNITY BUILDER")
    log("=" * 60)
    log(f"Neo4j URI: {NEO4J_URI}")
    log(f"Timeout: {timeout_seconds}s")
    log("")

    # Pre-flight checks
    stats = await check_neo4j_connection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    if not stats.get("connected"):
        log("")
        log("❌ Cannot proceed - Neo4j connection failed")
        log("💡 Make sure Neo4j is running:")
        log("   docker compose up -d neo4j")
        return 1

    if stats.get("entity_count", 0) == 0:
        log("")
        log("❌ Cannot proceed - No entities found in graph")
        log("💡 Process some documents first to populate the knowledge graph")
        return 1

    if stats.get("entity_count", 0) < 3:
        log("")
        log(f"⚠️  Warning: Only {stats['entity_count']} entities found")
        log("   Community detection works best with more entities")

    log("")
    log("🔧 Initializing Graphiti client...")

    try:
        # Apply datetime parsing patches BEFORE importing Graphiti
        # This fixes the 'str' object has no attribute 'to_native' error
        from chat.utils.graphiti_patches import apply_graphiti_patches
        apply_graphiti_patches()
        log("   ✓ Applied datetime patches")

        from graphiti_core import Graphiti

        client = Graphiti(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        log("   ✓ Client created")

        log("📊 Building indices and constraints...")
        await client.build_indices_and_constraints()
        log("   ✓ Indices ready")

    except Exception as e:
        log(f"❌ Failed to initialize Graphiti: {e}")
        return 1

    # Build communities with timeout
    log("")
    log(f"🏗️  Building communities (timeout: {timeout_seconds}s)...")
    log("   This may take a while for large graphs...")
    log("   - Running Leiden clustering algorithm")
    log("   - Generating community summaries via LLM")
    log("   - Creating embeddings for community names")

    start_time = datetime.now()

    try:
        # Run with timeout
        result = await asyncio.wait_for(
            client.build_communities(),
            timeout=timeout_seconds
        )

        elapsed = (datetime.now() - start_time).total_seconds()

        # Handle the result - it's a tuple of (CommunityNodes, CommunityEdges)
        if isinstance(result, tuple):
            community_nodes, community_edges = result
        else:
            community_nodes = result
            community_edges = []

        log("")
        log(f"✅ Community building completed in {elapsed:.1f}s")

        if community_nodes:
            log(f"   Created {len(community_nodes)} communities")
            if community_edges:
                log(f"   Created {len(community_edges)} community edges")

            log("")
            log("📋 Communities created:")
            log("-" * 40)

            for i, community in enumerate(community_nodes[:10], 1):
                # CommunityNode has: uuid, name, group_id, name_embedding, created_at, summary
                name = getattr(community, "name", f"Community {i}")
                summary = getattr(community, "summary", "No summary")
                # Truncate long summaries
                if len(summary) > 100:
                    summary = summary[:100] + "..."
                log(f"  {i}. {name}")
                log(f"     {summary}")
                log("")

            if len(community_nodes) > 10:
                log(f"  ... and {len(community_nodes) - 10} more communities")

        else:
            log("")
            log("⚠️  No communities were created")
            log("   Possible reasons:")
            log("   - Not enough connected entities")
            log("   - Entities are too isolated (no relationships)")
            log("   - Graph structure doesn't form natural clusters")

    except asyncio.TimeoutError:
        elapsed = (datetime.now() - start_time).total_seconds()
        log("")
        log(f"⏱️  Community building timed out after {elapsed:.1f}s")
        log("💡 Try increasing the timeout or reducing graph size")
        await client.close()
        return 1

    except Exception as e:
        log("")
        log(f"❌ Community building failed: {e}")
        import traceback
        if verbose:
            log("")
            log("Traceback:")
            traceback.print_exc()
        await client.close()
        return 1

    # Cleanup
    log("")
    log("🧹 Closing connection...")
    await client.close()
    log("   ✓ Done")

    # Final instructions
    log("")
    log("=" * 60)
    log("💡 View communities in Neo4j Browser: http://localhost:7474")
    log("")
    log("   Useful queries:")
    log("   MATCH (c:Community) RETURN c.name, c.summary")
    log("")
    log("   MATCH (c:Community)<-[:MEMBER_OF]-(e:Entity)")
    log("   RETURN c.name, count(e) as members ORDER BY members DESC")
    log("")
    log("   MATCH (e:Entity)-[:MEMBER_OF]->(c:Community)")
    log("   WHERE c.name CONTAINS 'AI'")
    log("   RETURN e.name, c.name")
    log("=" * 60)

    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Build communities from Graphiti knowledge graph"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout in seconds (default: 300 = 5 minutes)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output verbosity"
    )
    args = parser.parse_args()

    exit_code = asyncio.run(
        build_communities(
            timeout_seconds=args.timeout,
            verbose=not args.quiet
        )
    )
    sys.exit(exit_code)
