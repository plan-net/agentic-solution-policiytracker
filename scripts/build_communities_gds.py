#!/usr/bin/env python3
"""
Build communities using Neo4j Graph Data Science (GDS) directly.

This script bypasses Graphiti's buggy build_communities() function and runs
the Leiden algorithm directly via Neo4j GDS, which handles large graphs efficiently.

Features:
- Direct GDS Leiden algorithm (no OOM issues)
- Progress logging at each step
- Creates Community nodes with member counts
- Works with 20K+ entities
- Optional LLM summarization (Graphiti-compatible)
- Optional name embeddings for semantic search
- Fallback text fields for nodes without summaries

Text Field Fallback Priority:
-----------------------------
When generating community summaries, the script uses alternative text fields
if the `summary` property is not available on Entity nodes. This is particularly
useful for German Bundestag data (Drucksache, Vorgang, etc.) which store their
descriptive text in different properties.

Priority order:
1. summary     - Standard Entity summary (from Graphiti)
2. abstract    - For Vorgang nodes (~400 chars, legislative proceeding description)
3. titel       - For Drucksache nodes (~200 chars, document title)
4. description - For Fraktion nodes (~57 chars, party description)
5. content     - For Episodic nodes (truncated to 500 chars, raw document text)
6. name        - Fallback if name > 10 chars

This ensures communities containing primarily Bundestag data can still be
summarized meaningfully, even without traditional Entity summaries.

Usage:
------
# Full run: Leiden clustering + summarization + embeddings
python scripts/build_communities_gds.py --summarize

# Just add summaries to existing communities (skip clustering)
python scripts/build_communities_gds.py --summarize-only

# Summarize specific number of communities with member limit
python scripts/build_communities_gds.py --summarize-only --max-summarize 10 --max-members 50

# Run clustering only (no LLM summarization)
python scripts/build_communities_gds.py --min-size 5

Example Output:
---------------
[12:00:11]    [1/3] Community 3141 (8073 members)
[12:00:11]       Found 30 text entries (1001 abstract, 7071 titel)
[12:00:11]       Estimated LLM calls: ~6
[12:00:11]       Generating summary...
[12:00:38]       ✓ Germany's legislative priorities during the 21st period...

The source breakdown (e.g., "1001 abstract, 7071 titel") shows where the
text content was sourced from for each community.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def log(message: str, flush: bool = True):
    """Print with timestamp and immediate flush."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", flush=flush)


# ============================================================================
# LLM SUMMARIZATION FUNCTIONS (Graphiti-compatible)
# ============================================================================

async def summarize_pair(client, summary1: str, summary2: str) -> str:
    """
    Merge two summaries into one (same pattern as Graphiti).

    Uses the exact same prompt structure as graphiti_core/prompts/summarize_nodes.py
    with additional instruction to output in English for bilingual graphs.
    """
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that combines summaries. "
                       "Always output in English, even if inputs contain German text."
        },
        {
            "role": "user",
            "content": f"""
Synthesize the information from the following two summaries into a single succinct summary.
Output the summary in English, translating any German content.

Summaries must be under 250 words.

Summaries:
{json.dumps([{"summary": summary1}, {"summary": summary2}], indent=2)}
"""
        }
    ]

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.1,
        max_tokens=500,
    )

    return response.choices[0].message.content.strip()


async def generate_community_name(client, summary: str) -> str:
    """
    Generate a one-sentence description for the community name.

    Uses the exact same prompt structure as graphiti_core/prompts/summarize_nodes.py
    with additional instruction to output in English for bilingual graphs.
    """
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that describes provided contents in a single sentence. "
                       "Always output in English."
        },
        {
            "role": "user",
            "content": f"""
Create a short one sentence description in English that explains what kind of information is summarized.

Summary:
{json.dumps(summary, indent=2)}
"""
        }
    ]

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.1,
        max_tokens=150,
    )

    return response.choices[0].message.content.strip()


async def summarize_community(client, entity_summaries: list[str]) -> str:
    """
    Hierarchical pairwise summarization until single summary remains.

    This is the same algorithm used in graphiti_core/utils/maintenance/community_operations.py
    """
    if not entity_summaries:
        return ""

    if len(entity_summaries) == 1:
        return entity_summaries[0]

    summaries = [s for s in entity_summaries if s]  # Filter out empty summaries

    if not summaries:
        return ""

    iteration = 0
    while len(summaries) > 1:
        iteration += 1

        # Handle odd count - save one for later
        odd_one_out: str | None = None
        if len(summaries) % 2 == 1:
            odd_one_out = summaries.pop()

        # Pair up and summarize in parallel
        pairs = list(zip(
            summaries[:len(summaries)//2],
            summaries[len(summaries)//2:]
        ))

        # Process pairs in parallel (with some concurrency limit)
        new_summaries = await asyncio.gather(*[
            summarize_pair(client, s1, s2) for s1, s2 in pairs
        ])

        summaries = list(new_summaries)

        # Add back the odd one
        if odd_one_out is not None:
            summaries.append(odd_one_out)

    return summaries[0]


async def embed_texts(client, texts: list[str], model: str = "text-embedding-3-small") -> list[list[float]]:
    """Generate embeddings for a list of texts."""
    if not texts:
        return []

    response = await client.embeddings.create(
        model=model,
        input=texts,
    )

    return [item.embedding for item in response.data]


# ============================================================================
# MAIN COMMUNITY DETECTION FUNCTIONS
# ============================================================================

def run_gds_community_detection(
    group_id: str | None = None,
    relationship_types: list[str] | None = None,
    min_community_size: int = 3,
    summarize: bool = False,
    summarize_only: bool = False,
    max_communities_to_summarize: int = 50,
    max_members_for_summary: int = 100,
):
    """
    Run Leiden community detection using Neo4j GDS.

    Args:
        group_id: Optional filter for specific group
        relationship_types: List of relationship types to consider (default: all)
        min_community_size: Minimum entities per community to keep
        summarize: If True, generate LLM summaries and embeddings
        summarize_only: If True, only add summaries to existing communities
        max_communities_to_summarize: Limit on communities to summarize (cost control)
        max_members_for_summary: Max entity summaries to use per community
    """
    from neo4j import GraphDatabase

    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")

    if relationship_types is None:
        relationship_types = ["RELATES_TO", "BELONGS_TO", "DOCUMENT_FOR"]

    log("=" * 60)
    log("🏘️  NEO4J GDS COMMUNITY DETECTION")
    log("=" * 60)
    log(f"Neo4j URI: {NEO4J_URI}")
    log(f"Group filter: {group_id or 'All groups'}")
    log(f"Relationship types: {relationship_types}")
    log(f"Min community size: {min_community_size}")
    log(f"Summarize: {summarize or summarize_only}")
    log("")

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        with driver.session() as session:
            # Skip clustering if summarize_only
            if not summarize_only:
                # Step 1: Check GDS version
                log("🔍 Checking Neo4j GDS...")
                result = session.run("RETURN gds.version() as version")
                gds_version = result.single()["version"]
                log(f"   ✓ GDS version: {gds_version}")

                # Step 2: Get entity count
                if group_id:
                    result = session.run(
                        "MATCH (n:Entity {group_id: $group_id}) RETURN count(n) as count",
                        group_id=group_id
                    )
                else:
                    result = session.run("MATCH (n:Entity) RETURN count(n) as count")
                entity_count = result.single()["count"]
                log(f"   ✓ Found {entity_count} entities")

                if entity_count == 0:
                    log("❌ No entities found")
                    return 1

                # Step 3: Drop existing graph projection if exists
                log("")
                log("📊 Creating graph projection...")
                try:
                    session.run("CALL gds.graph.drop('community_graph', false)")
                    log("   ✓ Dropped existing projection")
                except Exception:
                    pass  # Graph doesn't exist, that's fine

                # Step 4: Create graph projection with UNDIRECTED orientation for Leiden
                projection_query = """
                CALL gds.graph.project(
                    'community_graph',
                    'Entity',
                    {
                        RELATES_TO: {orientation: 'UNDIRECTED'},
                        BELONGS_TO: {orientation: 'UNDIRECTED'},
                        DOCUMENT_FOR: {orientation: 'UNDIRECTED'}
                    }
                )
                YIELD graphName, nodeCount, relationshipCount
                RETURN graphName, nodeCount, relationshipCount
                """

                result = session.run(projection_query)
                record = result.single()
                log(f"   ✓ Projected graph: {record['nodeCount']} nodes, {record['relationshipCount']} relationships")

                if record['nodeCount'] == 0:
                    log("❌ No nodes in projection - check your filters")
                    session.run("CALL gds.graph.drop('community_graph', false)")
                    return 1

                # Step 5: Run Leiden algorithm
                log("")
                log("🔬 Running Leiden community detection...")
                start_time = datetime.now()

                leiden_query = """
                CALL gds.leiden.stream('community_graph', {
                    maxLevels: 10,
                    gamma: 1.0,
                    theta: 0.01,
                    includeIntermediateCommunities: false
                })
                YIELD nodeId, communityId
                RETURN communityId, count(*) as size, collect(gds.util.asNode(nodeId).name) as members
                ORDER BY size DESC
                """

                result = session.run(leiden_query)
                communities = list(result)
                elapsed = (datetime.now() - start_time).total_seconds()

                log(f"   ✓ Completed in {elapsed:.1f}s")
                log(f"   ✓ Found {len(communities)} raw communities")

                # Filter by minimum size
                large_communities = [c for c in communities if c["size"] >= min_community_size]
                log(f"   ✓ {len(large_communities)} communities with {min_community_size}+ members")

                # Step 6: Clean up old Community nodes
                log("")
                log("🧹 Cleaning up old communities...")
                result = session.run("MATCH (c:Community) DETACH DELETE c RETURN count(*) as deleted")
                deleted = result.single()["deleted"]
                if deleted > 0:
                    log(f"   ✓ Deleted {deleted} old community nodes")
                else:
                    log("   ✓ No old communities to delete")

                # Step 7: Write community IDs to entities and create Community nodes
                log("")
                log("📝 Creating Community nodes...")

                # Write community assignments back to entities
                write_query = """
                CALL gds.leiden.write('community_graph', {
                    writeProperty: 'communityId',
                    maxLevels: 10,
                    gamma: 1.0,
                    theta: 0.01
                })
                YIELD communityCount, modularity
                RETURN communityCount, modularity
                """
                result = session.run(write_query)
                record = result.single()
                modularity = record['modularity']
                log(f"   ✓ Wrote community IDs to {record['communityCount']} communities")
                log(f"   ✓ Modularity score: {modularity:.4f}")

                # Create Community nodes for large communities
                create_community_query = """
                MATCH (e:Entity)
                WHERE e.communityId IS NOT NULL
                WITH e.communityId as communityId, collect(e) as members
                WHERE size(members) >= $min_size
                CREATE (c:Community {
                    uuid: randomUUID(),
                    communityId: communityId,
                    name: 'Community ' + toString(communityId),
                    member_count: size(members),
                    created_at: datetime(),
                    group_id: head(members).group_id
                })
                WITH c, members
                UNWIND members as member
                CREATE (member)-[:MEMBER_OF]->(c)
                RETURN count(DISTINCT c) as communities_created
                """
                result = session.run(create_community_query, min_size=min_community_size)
                created = result.single()["communities_created"]
                log(f"   ✓ Created {created} Community nodes")

                # Clean up graph projection
                log("")
                log("🧹 Cleaning up graph projection...")
                session.run("CALL gds.graph.drop('community_graph', false)")
                log("   ✓ Done")

            # Step 8: Generate summaries and embeddings (if requested)
            if summarize or summarize_only:
                asyncio.run(generate_community_summaries(
                    driver,
                    max_communities=max_communities_to_summarize,
                    max_members=max_members_for_summary,
                ))

            # Step 9: Create search indices
            if summarize or summarize_only:
                log("")
                log("📇 Creating search indices...")
                create_search_indices(session)

            # Final summary
            log("")
            log("📋 Community Summary:")
            log("-" * 50)

            summary_query = """
            MATCH (c:Community)<-[:MEMBER_OF]-(e:Entity)
            WITH c, collect(e.name) as members
            ORDER BY size(members) DESC
            LIMIT 15
            RETURN c.communityId as id, c.name as name, size(members) as size,
                   members[0..5] as top_members,
                   c.summary IS NOT NULL as has_summary
            """
            result = session.run(summary_query)

            for i, record in enumerate(result, 1):
                top_members = ", ".join(record["top_members"][:3])
                if len(record["top_members"]) > 3:
                    top_members += "..."
                summary_status = "✓" if record["has_summary"] else "○"
                log(f"  {i}. [{summary_status}] {record['name']} ({record['size']} members)")
                log(f"     Top: {top_members}")
                log("")

            # Final stats
            log("")
            log("=" * 60)
            log("✅ COMMUNITY DETECTION COMPLETE")
            log("=" * 60)

            # Get final counts
            result = session.run("MATCH (c:Community) RETURN count(c) as count")
            total_communities = result.single()["count"]

            result = session.run("MATCH (c:Community) WHERE c.summary IS NOT NULL RETURN count(c) as count")
            summarized = result.single()["count"]

            log(f"   Total communities: {total_communities}")
            log(f"   With summaries: {summarized}")
            log("")
            log("💡 View in Neo4j Browser: http://localhost:7474")
            log("")
            log("   Useful queries:")
            log("   MATCH (c:Community)<-[:MEMBER_OF]-(e:Entity)")
            log("   RETURN c.name, count(e) as members ORDER BY members DESC")
            log("")
            log("   // Search by name (after summarization)")
            log("   CALL db.index.fulltext.queryNodes('community_name', 'policy')")
            log("   YIELD node, score RETURN node.name, node.summary, score")

    except Exception as e:
        log(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        driver.close()

    return 0


async def generate_community_summaries(
    driver,
    max_communities: int = 50,
    max_members: int = 100,
):
    """
    Generate LLM summaries and embeddings for Community nodes.

    Uses the same hierarchical pairwise summarization as Graphiti:
    1. Collect text content from community member entities
    2. Merge pairs of summaries iteratively until one remains
    3. Generate a one-sentence community name from the final summary
    4. Create an embedding for semantic search

    Text Content Fallback:
        When Entity.summary is not available, uses alternative fields:
        - abstract: For Vorgang (legislative proceedings) - ~400 chars
        - titel: For Drucksache (documents) - ~200 chars
        - description: For Fraktion (parties) - ~57 chars
        - content: For Episodic (raw text) - truncated to 500 chars
        - name: Fallback if > 10 chars

    Args:
        driver: Neo4j driver instance
        max_communities: Maximum number of communities to summarize (cost control)
        max_members: Maximum text entries to use per community (limits LLM calls)

    Note:
        The function logs source statistics showing where text content came from,
        e.g., "Found 30 text entries (1001 abstract, 7071 titel)"
    """
    from openai import AsyncOpenAI

    log("")
    log("🤖 Generating community summaries with LLM...")
    log(f"   Max communities: {max_communities}")
    log(f"   Max members per community: {max_members}")

    # Initialize OpenAI client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        log("   ⚠️  OPENAI_API_KEY not set - skipping summarization")
        return

    # Use APISIX gateway if available, otherwise direct OpenAI
    base_url = os.getenv("APISIX_GATEWAY_URL")
    if base_url:
        base_url = f"{base_url}/v1" if not base_url.endswith("/v1") else base_url
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        log(f"   Using APISIX gateway: {base_url}")
    else:
        client = AsyncOpenAI(api_key=api_key)
        log("   Using direct OpenAI API")

    with driver.session() as session:
        # Get communities that need summarization (largest first)
        result = session.run("""
            MATCH (c:Community)<-[:MEMBER_OF]-(e:Entity)
            WHERE c.summary IS NULL
            WITH c, count(e) as member_count
            ORDER BY member_count DESC
            LIMIT $max_communities
            RETURN c.uuid as uuid, c.communityId as community_id, member_count
        """, max_communities=max_communities)

        communities_to_process = list(result)
        log(f"   Found {len(communities_to_process)} communities to summarize")

        if not communities_to_process:
            log("   ✓ All communities already have summaries")
            return

        total_llm_calls = 0

        for i, comm in enumerate(communities_to_process, 1):
            community_uuid = comm["uuid"]
            community_id = comm["community_id"]
            member_count = comm["member_count"]

            log(f"")
            log(f"   [{i}/{len(communities_to_process)}] Community {community_id} ({member_count} members)")

            # Get entity text content for this community
            # Uses fallback fields when summary is not available:
            # summary > abstract > titel > description > content (truncated) > name
            result = session.run("""
                MATCH (c:Community {uuid: $uuid})<-[:MEMBER_OF]-(e:Entity)
                WITH e,
                     CASE
                         // Priority 1: Use existing summary if available
                         WHEN e.summary IS NOT NULL AND e.summary <> '' THEN e.summary
                         // Priority 2: For Vorgang nodes, use abstract
                         WHEN e.abstract IS NOT NULL AND e.abstract <> '' THEN e.abstract
                         // Priority 3: For Drucksache/document nodes, use titel
                         WHEN e.titel IS NOT NULL AND e.titel <> '' THEN e.titel
                         // Priority 4: For Fraktion nodes, use description
                         WHEN e.description IS NOT NULL AND e.description <> '' THEN e.description
                         // Priority 5: For Episodic nodes, use truncated content
                         WHEN e.content IS NOT NULL AND e.content <> '' THEN left(e.content, 500)
                         // Priority 6: Fallback to name if nothing else
                         WHEN e.name IS NOT NULL AND size(e.name) > 10 THEN e.name
                         ELSE NULL
                     END as text_content
                WHERE text_content IS NOT NULL
                RETURN text_content as summary
                LIMIT $max_members
            """, uuid=community_uuid, max_members=max_members)

            entity_summaries = [r["summary"] for r in result if r["summary"]]

            if not entity_summaries:
                log(f"      ⚠️  No text content found (no summary/abstract/titel/content) - skipping")
                continue

            # Get statistics on where text content came from
            stats_result = session.run("""
                MATCH (c:Community {uuid: $uuid})<-[:MEMBER_OF]-(e:Entity)
                RETURN
                    sum(CASE WHEN e.summary IS NOT NULL AND e.summary <> '' THEN 1 ELSE 0 END) as from_summary,
                    sum(CASE WHEN e.summary IS NULL OR e.summary = '' THEN
                        CASE WHEN e.abstract IS NOT NULL AND e.abstract <> '' THEN 1 ELSE 0 END
                    ELSE 0 END) as from_abstract,
                    sum(CASE WHEN (e.summary IS NULL OR e.summary = '') AND (e.abstract IS NULL OR e.abstract = '') THEN
                        CASE WHEN e.titel IS NOT NULL AND e.titel <> '' THEN 1 ELSE 0 END
                    ELSE 0 END) as from_titel,
                    sum(CASE WHEN (e.summary IS NULL OR e.summary = '') AND (e.abstract IS NULL OR e.abstract = '') AND (e.titel IS NULL OR e.titel = '') THEN
                        CASE WHEN e.description IS NOT NULL AND e.description <> '' THEN 1 ELSE 0 END
                    ELSE 0 END) as from_description,
                    sum(CASE WHEN (e.summary IS NULL OR e.summary = '') AND (e.abstract IS NULL OR e.abstract = '') AND (e.titel IS NULL OR e.titel = '') AND (e.description IS NULL OR e.description = '') THEN
                        CASE WHEN e.content IS NOT NULL AND e.content <> '' THEN 1 ELSE 0 END
                    ELSE 0 END) as from_content
            """, uuid=community_uuid)
            stats = stats_result.single()

            # Build source breakdown string
            sources = []
            if stats["from_summary"] > 0:
                sources.append(f"{stats['from_summary']} summary")
            if stats["from_abstract"] > 0:
                sources.append(f"{stats['from_abstract']} abstract")
            if stats["from_titel"] > 0:
                sources.append(f"{stats['from_titel']} titel")
            if stats["from_description"] > 0:
                sources.append(f"{stats['from_description']} description")
            if stats["from_content"] > 0:
                sources.append(f"{stats['from_content']} content")

            source_info = f" ({', '.join(sources)})" if sources else ""
            log(f"      Found {len(entity_summaries)} text entries{source_info}")

            # Estimate LLM calls: log2(n) pairwise + 1 naming
            import math
            estimated_calls = int(math.log2(max(len(entity_summaries), 1))) + 2
            log(f"      Estimated LLM calls: ~{estimated_calls}")

            try:
                # Generate community summary using hierarchical pairwise summarization
                log(f"      Generating summary...")
                community_summary = await summarize_community(client, entity_summaries)

                if not community_summary:
                    log(f"      ⚠️  Empty summary generated - skipping")
                    continue

                # Generate community name (one-liner)
                log(f"      Generating name...")
                community_name = await generate_community_name(client, community_summary)

                total_llm_calls += estimated_calls

                # Generate embedding for the name
                log(f"      Generating embedding...")
                embeddings = await embed_texts(client, [community_name])
                name_embedding = embeddings[0] if embeddings else None

                # Update Community node
                session.run("""
                    MATCH (c:Community {uuid: $uuid})
                    SET c.name = $name,
                        c.summary = $summary,
                        c.name_embedding = $embedding
                """,
                    uuid=community_uuid,
                    name=community_name,
                    summary=community_summary,
                    embedding=name_embedding
                )

                log(f"      ✓ {community_name[:60]}...")

            except Exception as e:
                log(f"      ❌ Error: {e}")
                continue

        log("")
        log(f"   ✓ Summarization complete")
        log(f"   Total LLM calls: ~{total_llm_calls}")


def create_search_indices(session):
    """Create fulltext and vector indices for community search."""

    # Create fulltext index for BM25 search on community names
    try:
        session.run("""
            CREATE FULLTEXT INDEX community_name IF NOT EXISTS
            FOR (c:Community) ON EACH [c.name]
        """)
        log("   ✓ Created fulltext index: community_name")
    except Exception as e:
        if "already exists" in str(e).lower():
            log("   ✓ Fulltext index already exists: community_name")
        else:
            log(f"   ⚠️  Could not create fulltext index: {e}")

    # Create vector index for semantic similarity search
    # Note: This requires Neo4j 5.11+ with vector index support
    try:
        session.run("""
            CREATE VECTOR INDEX community_embedding IF NOT EXISTS
            FOR (c:Community) ON (c.name_embedding)
            OPTIONS {indexConfig: {
                `vector.dimensions`: 1536,
                `vector.similarity_function`: 'cosine'
            }}
        """)
        log("   ✓ Created vector index: community_embedding")
    except Exception as e:
        if "already exists" in str(e).lower():
            log("   ✓ Vector index already exists: community_embedding")
        elif "not supported" in str(e).lower() or "unknown" in str(e).lower():
            log("   ⚠️  Vector index not supported (requires Neo4j 5.11+)")
        else:
            log(f"   ⚠️  Could not create vector index: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Build communities using Neo4j GDS Leiden algorithm"
    )
    parser.add_argument(
        "--group-id",
        type=str,
        default=None,
        help="Filter to specific group_id (default: all groups)"
    )
    parser.add_argument(
        "--min-size",
        type=int,
        default=3,
        help="Minimum community size to keep (default: 3)"
    )
    parser.add_argument(
        "--relationships",
        type=str,
        default="RELATES_TO,BELONGS_TO,DOCUMENT_FOR",
        help="Comma-separated relationship types to consider"
    )
    parser.add_argument(
        "--summarize",
        action="store_true",
        help="Generate LLM summaries and embeddings for communities. "
             "Uses fallback text fields (abstract, titel, description, content) "
             "when Entity.summary is not available."
    )
    parser.add_argument(
        "--summarize-only",
        action="store_true",
        help="Only add summaries to existing communities (skip Leiden clustering). "
             "Useful for adding summaries after initial community detection."
    )
    parser.add_argument(
        "--max-summarize",
        type=int,
        default=50,
        help="Maximum number of communities to summarize for cost control (default: 50). "
             "Communities are processed largest-first."
    )
    parser.add_argument(
        "--max-members",
        type=int,
        default=100,
        help="Maximum text entries to use per community (default: 100). "
             "Uses fallback fields: summary > abstract > titel > description > content > name"
    )
    args = parser.parse_args()

    rel_types = [r.strip() for r in args.relationships.split(",")]

    exit_code = run_gds_community_detection(
        group_id=args.group_id,
        relationship_types=rel_types,
        min_community_size=args.min_size,
        summarize=args.summarize,
        summarize_only=args.summarize_only,
        max_communities_to_summarize=args.max_summarize,
        max_members_for_summary=args.max_members,
    )
    sys.exit(exit_code)
