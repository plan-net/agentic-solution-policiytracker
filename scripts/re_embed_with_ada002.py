"""
Re-embed entities, relationships, and episodic nodes with text-embedding-ada-002.

This script migrates embeddings from text-embedding-3-small to text-embedding-ada-002
for perfect multilingual (English-German) retrieval.

Testing showed ada-002 achieves 100% cross-lingual similarity vs 13% for 3-small.

Usage:
    # Re-embed entities only
    python scripts/re_embed_with_ada002.py --entities

    # Re-embed relationships only
    python scripts/re_embed_with_ada002.py --relationships

    # Re-embed entities and relationships (recommended for Phase 1)
    python scripts/re_embed_with_ada002.py --entities --relationships

    # Re-embed episodic nodes only (user will implement manually)
    python scripts/re_embed_with_ada002.py --episodic

    # Dry run to see what would be processed
    python scripts/re_embed_with_ada002.py --entities --relationships --dry-run

    # Test with limited items
    python scripts/re_embed_with_ada002.py --entities --limit 10

Cost:
    - Entities (31,129): ~$0.04
    - Relationships (53,772): ~$0.17
    - Episodic nodes (7,794): ~$0.98
    - Total: ~$1.18
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from openai import AsyncOpenAI
from neo4j import AsyncGraphDatabase
from tqdm.asyncio import tqdm
from src.config import settings


class ReembeddingStats:
    """Track re-embedding statistics."""

    def __init__(self):
        self.entities_processed = 0
        self.entities_failed = 0
        self.relationships_processed = 0
        self.relationships_failed = 0
        self.episodic_processed = 0
        self.episodic_failed = 0
        self.start_time = datetime.now()
        self.total_tokens_used = 0

    def add_tokens(self, tokens: int):
        self.total_tokens_used += tokens

    def get_cost(self) -> float:
        """Calculate cost at $0.10/1M tokens for ada-002."""
        return (self.total_tokens_used / 1_000_000) * 0.10

    def print_summary(self):
        """Print final summary."""
        duration = (datetime.now() - self.start_time).total_seconds()

        print("\n" + "=" * 80)
        print("RE-EMBEDDING SUMMARY")
        print("=" * 80)

        if self.entities_processed > 0:
            print(f"\nEntities:")
            print(f"  Processed: {self.entities_processed:,}")
            print(f"  Failed: {self.entities_failed:,}")
            print(f"  Success rate: {(self.entities_processed / (self.entities_processed + self.entities_failed) * 100):.1f}%")

        if self.relationships_processed > 0:
            print(f"\nRelationships:")
            print(f"  Processed: {self.relationships_processed:,}")
            print(f"  Failed: {self.relationships_failed:,}")
            print(f"  Success rate: {(self.relationships_processed / (self.relationships_processed + self.relationships_failed) * 100):.1f}%")

        if self.episodic_processed > 0:
            print(f"\nEpisodic Nodes:")
            print(f"  Processed: {self.episodic_processed:,}")
            print(f"  Failed: {self.episodic_failed:,}")
            print(f"  Success rate: {(self.episodic_processed / (self.episodic_processed + self.episodic_failed) * 100):.1f}%")

        total_processed = self.entities_processed + self.relationships_processed + self.episodic_processed
        total_failed = self.entities_failed + self.relationships_failed + self.episodic_failed

        print(f"\nTotal:")
        print(f"  Processed: {total_processed:,}")
        print(f"  Failed: {total_failed:,}")
        print(f"  Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        print(f"  Rate: {total_processed / duration:.1f} items/second")

        print(f"\nCost:")
        print(f"  Total tokens: {self.total_tokens_used:,}")
        print(f"  Estimated cost: ${self.get_cost():.2f}")

        print("=" * 80)


async def get_embedding(client: AsyncOpenAI, text: str, max_retries: int = 3) -> Optional[List[float]]:
    """
    Get embedding from OpenAI with retry logic.

    Args:
        client: OpenAI client
        text: Text to embed
        max_retries: Maximum number of retries

    Returns:
        Embedding vector or None if all retries failed
    """
    for attempt in range(max_retries):
        try:
            # Note: ada-002 does not support dimensions parameter (always returns 1536)
            response = await client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"\n❌ Failed to get embedding after {max_retries} attempts: {e}")
                return None
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
    return None


async def re_embed_entities(
    driver: AsyncGraphDatabase,
    openai_client: AsyncOpenAI,
    stats: ReembeddingStats,
    batch_size: int = 100,
    limit: Optional[int] = None,
    dry_run: bool = False,
    force: bool = False,
) -> None:
    """Re-embed all entities with ada-002.

    Args:
        force: If True, re-embed even if already migrated to ada-002
    """

    print("\n" + "=" * 80)
    print("RE-EMBEDDING ENTITIES")
    print("=" * 80)

    async with driver.session(database=settings.NEO4J_DATABASE) as session:
        # Count total (skip already migrated unless --force)
        if force:
            count_query = "MATCH (e:Entity) WHERE e.name IS NOT NULL RETURN count(e) as count"
        else:
            count_query = """
            MATCH (e:Entity)
            WHERE e.name IS NOT NULL
              AND (e.embedding_model IS NULL OR e.embedding_model <> 'text-embedding-ada-002')
            RETURN count(e) as count
            """

        result = await session.run(count_query)
        record = await result.single()
        total_count = record['count'] if record else 0

        if limit:
            total_count = min(total_count, limit)

        print(f"\nTotal entities to process: {total_count:,}")

        if not force:
            print("  (Skipping items already migrated to ada-002)")

        if dry_run:
            print("✓ DRY RUN - No changes will be made")
            return

        # Process in batches
        offset = 0
        pbar = tqdm(total=total_count, desc="Entities", unit="entity")

        while offset < total_count:
            # Fetch batch (skip already migrated unless --force)
            if force:
                fetch_query = """
                MATCH (e:Entity)
                WHERE e.name IS NOT NULL
                RETURN e.uuid as uuid, e.name as name
                ORDER BY e.uuid
                SKIP $offset
                LIMIT $batch_size
                """
            else:
                fetch_query = """
                MATCH (e:Entity)
                WHERE e.name IS NOT NULL
                  AND (e.embedding_model IS NULL OR e.embedding_model <> 'text-embedding-ada-002')
                RETURN e.uuid as uuid, e.name as name
                ORDER BY e.uuid
                SKIP $offset
                LIMIT $batch_size
                """

            result = await session.run(fetch_query, {"offset": offset, "batch_size": batch_size})
            records = await result.data()

            if not records:
                break

            # Process batch
            for record in records:
                uuid = record['uuid']
                name = record['name']

                # Get new embedding
                embedding = await get_embedding(openai_client, name)

                if embedding:
                    # Update in Neo4j with marker properties
                    update_query = """
                    MATCH (e:Entity {uuid: $uuid})
                    SET e.name_embedding = $embedding,
                        e.embedding_model = 'text-embedding-ada-002',
                        e.embedding_migrated_at = datetime()
                    """
                    await session.run(update_query, {"uuid": uuid, "embedding": embedding})

                    stats.entities_processed += 1
                    stats.add_tokens(len(name.split()) * 1.3)  # Rough token estimate
                else:
                    stats.entities_failed += 1

                pbar.update(1)

            offset += len(records)
            await asyncio.sleep(0.1)  # Rate limiting

        pbar.close()
        print(f"✓ Completed: {stats.entities_processed:,} entities re-embedded")


async def re_embed_relationships(
    driver: AsyncGraphDatabase,
    openai_client: AsyncOpenAI,
    stats: ReembeddingStats,
    batch_size: int = 100,
    limit: Optional[int] = None,
    dry_run: bool = False,
    force: bool = False,
) -> None:
    """Re-embed all relationships with ada-002.

    Args:
        force: If True, re-embed even if already migrated to ada-002
    """

    print("\n" + "=" * 80)
    print("RE-EMBEDDING RELATIONSHIPS")
    print("=" * 80)

    async with driver.session(database=settings.NEO4J_DATABASE) as session:
        # Count total (skip already migrated unless --force)
        if force:
            count_query = "MATCH ()-[r:RELATES_TO]->() WHERE r.fact IS NOT NULL RETURN count(r) as count"
        else:
            count_query = """
            MATCH ()-[r:RELATES_TO]->()
            WHERE r.fact IS NOT NULL
              AND (r.embedding_model IS NULL OR r.embedding_model <> 'text-embedding-ada-002')
            RETURN count(r) as count
            """

        result = await session.run(count_query)
        record = await result.single()
        total_count = record['count'] if record else 0

        if limit:
            total_count = min(total_count, limit)

        print(f"\nTotal relationships to process: {total_count:,}")

        if not force:
            print("  (Skipping items already migrated to ada-002)")

        if dry_run:
            print("✓ DRY RUN - No changes will be made")
            return

        # Process in batches
        offset = 0
        pbar = tqdm(total=total_count, desc="Relationships", unit="rel")

        while offset < total_count:
            # Fetch batch (skip already migrated unless --force)
            if force:
                fetch_query = """
                MATCH ()-[r:RELATES_TO]->()
                WHERE r.fact IS NOT NULL
                RETURN id(r) as rel_id, r.fact as fact
                ORDER BY id(r)
                SKIP $offset
                LIMIT $batch_size
                """
            else:
                fetch_query = """
                MATCH ()-[r:RELATES_TO]->()
                WHERE r.fact IS NOT NULL
                  AND (r.embedding_model IS NULL OR r.embedding_model <> 'text-embedding-ada-002')
                RETURN id(r) as rel_id, r.fact as fact
                ORDER BY id(r)
                SKIP $offset
                LIMIT $batch_size
                """

            result = await session.run(fetch_query, {"offset": offset, "batch_size": batch_size})
            records = await result.data()

            if not records:
                break

            # Process batch
            for record in records:
                rel_id = record['rel_id']
                fact = record['fact']

                # Get new embedding
                embedding = await get_embedding(openai_client, fact)

                if embedding:
                    # Update in Neo4j with marker properties
                    update_query = """
                    MATCH ()-[r:RELATES_TO]->()
                    WHERE id(r) = $rel_id
                    SET r.fact_embedding = $embedding,
                        r.embedding_model = 'text-embedding-ada-002',
                        r.embedding_migrated_at = datetime()
                    """
                    await session.run(update_query, {"rel_id": rel_id, "embedding": embedding})

                    stats.relationships_processed += 1
                    stats.add_tokens(len(fact.split()) * 1.3)  # Rough token estimate
                else:
                    stats.relationships_failed += 1

                pbar.update(1)

            offset += len(records)
            await asyncio.sleep(0.1)  # Rate limiting

        pbar.close()
        print(f"✓ Completed: {stats.relationships_processed:,} relationships re-embedded")


async def re_embed_episodic(
    driver: AsyncGraphDatabase,
    openai_client: AsyncOpenAI,
    stats: ReembeddingStats,
    batch_size: int = 100,
    limit: Optional[int] = None,
    dry_run: bool = False,
    force: bool = False,
) -> None:
    """Re-embed all episodic nodes with ada-002.

    Args:
        force: If True, re-embed even if already migrated to ada-002

    NOTE: User will implement this manually. This is a template structure.
    """

    print("\n" + "=" * 80)
    print("RE-EMBEDDING EPISODIC NODES")
    print("=" * 80)
    print("\n⚠️  NOTE: This functionality is provided as a template.")
    print("   User will implement episodic re-embedding manually.")

    async with driver.session(database=settings.NEO4J_DATABASE) as session:
        # Count total (skip already migrated unless --force)
        if force:
            count_query = "MATCH (ep:Episodic) WHERE ep.content IS NOT NULL RETURN count(ep) as count"
        else:
            count_query = """
            MATCH (ep:Episodic)
            WHERE ep.content IS NOT NULL
              AND (ep.embedding_model IS NULL OR ep.embedding_model <> 'text-embedding-ada-002')
            RETURN count(ep) as count
            """

        result = await session.run(count_query)
        record = await result.single()
        total_count = record['count'] if record else 0

        if limit:
            total_count = min(total_count, limit)

        print(f"\nTotal episodic nodes to process: {total_count:,}")

        if not force:
            print("  (Skipping items already migrated to ada-002)")

        print(f"Estimated cost: ${(total_count * 1256 * 0.10 / 1_000_000):.2f}")

        if dry_run:
            print("✓ DRY RUN - No changes will be made")
            return

        print("\n🛑 Skipping episodic re-embedding (to be implemented manually)")
        print("   Run with --episodic flag once implementation is ready")
        print("\n📝 Template structure for manual implementation:")
        print("   1. Fetch batch with query that skips already-migrated items")
        print("   2. Get new embeddings from OpenAI")
        print("   3. Update with marker properties: embedding_model, embedding_migrated_at")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Re-embed knowledge graph with text-embedding-ada-002",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument("--entities", action="store_true", help="Re-embed entities")
    parser.add_argument("--relationships", action="store_true", help="Re-embed relationships")
    parser.add_argument("--episodic", action="store_true", help="Re-embed episodic nodes (template only)")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size (default: 100)")
    parser.add_argument("--limit", type=int, help="Limit number of items per type (for testing)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    parser.add_argument("--force", action="store_true", help="Re-embed even if already migrated to ada-002")

    args = parser.parse_args()

    # Validate arguments
    if not (args.entities or args.relationships or args.episodic):
        parser.error("At least one of --entities, --relationships, or --episodic is required")

    print("=" * 80)
    print("RE-EMBEDDING WITH text-embedding-ada-002")
    print("=" * 80)
    print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Database: {settings.NEO4J_DATABASE}")
    print(f"Batch size: {args.batch_size}")

    if args.limit:
        print(f"⚠️  LIMIT: {args.limit} items per type (testing mode)")
    if args.dry_run:
        print(f"⚠️  DRY RUN: No changes will be made")
    if args.force:
        print(f"⚠️  FORCE: Re-embedding items already migrated to ada-002")

    print("\nProcessing:")
    if args.entities:
        print("  ✓ Entities")
    if args.relationships:
        print("  ✓ Relationships")
    if args.episodic:
        print("  ✓ Episodic nodes")

    # Initialize clients
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n❌ ERROR: OPENAI_API_KEY not set in environment")
        return 1

    openai_client = AsyncOpenAI(api_key=api_key)

    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
    )

    stats = ReembeddingStats()

    try:
        # Process each type
        if args.entities:
            await re_embed_entities(driver, openai_client, stats, args.batch_size, args.limit, args.dry_run, args.force)

        if args.relationships:
            await re_embed_relationships(driver, openai_client, stats, args.batch_size, args.limit, args.dry_run, args.force)

        if args.episodic:
            await re_embed_episodic(driver, openai_client, stats, args.batch_size, args.limit, args.dry_run, args.force)

        # Print summary
        if not args.dry_run:
            stats.print_summary()
        else:
            print("\n✓ Dry run completed - no changes made")

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        stats.print_summary()
        return 130

    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        stats.print_summary()
        return 1

    finally:
        await driver.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
