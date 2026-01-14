#!/usr/bin/env python3
"""
Backfill script for adding content embeddings to existing Episodic nodes.

This script generates embeddings for all Episodic nodes that don't have
content_embedding property, enabling semantic search over episode content.

Usage:
    # Dry run to estimate cost
    uv run python scripts/backfill_episode_embeddings.py --dry-run

    # Full backfill with default batch size
    uv run python scripts/backfill_episode_embeddings.py

    # Custom batch size
    uv run python scripts/backfill_episode_embeddings.py --batch-size 100

    # Process limited number of episodes
    uv run python scripts/backfill_episode_embeddings.py --max-episodes 1000

Estimated costs (text-embedding-3-small at $0.02/1M tokens):
    - 7,611 episodes * ~5K chars avg = ~38M chars
    - ~38M chars / 4 chars per token = ~9.5M tokens
    - Cost: ~$0.19 (one-time backfill)
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "politicalmonitoring.v3")


async def verify_indexes_exist() -> dict:
    """Check if required indexes exist on Episodic nodes."""
    from neo4j import AsyncGraphDatabase

    driver = AsyncGraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD)
    )

    indexes = {
        "vector_index": False,
        "fulltext_index": False
    }

    try:
        async with driver.session(database=NEO4J_DATABASE) as session:
            # Check for vector index
            result = await session.run("""
                SHOW INDEXES
                WHERE type = 'VECTOR'
                AND labelsOrTypes = ['Episodic']
                AND properties = ['content_embedding']
            """)
            records = await result.data()
            indexes["vector_index"] = len(records) > 0

            # Check for fulltext index
            result = await session.run("""
                SHOW INDEXES
                WHERE type = 'FULLTEXT'
                AND name = 'episodic_content_fulltext'
            """)
            records = await result.data()
            indexes["fulltext_index"] = len(records) > 0

    finally:
        await driver.close()

    return indexes


async def backfill_embeddings(
    batch_size: int = 50,
    dry_run: bool = False,
    max_episodes: int | None = None,
) -> dict:
    """
    Backfill content embeddings for existing episodes.

    Args:
        batch_size: Number of episodes to process per batch
        dry_run: If True, only report what would be done
        max_episodes: Maximum episodes to process (None for all)

    Returns:
        Statistics dict with processing results
    """
    from src.graphrag.episode_embedding_manager import EpisodeEmbeddingManager

    start_time = datetime.now()
    stats = {
        "total_processed": 0,
        "successful": 0,
        "failed": 0,
        "skipped": 0,
        "total_chars": 0,
        "estimated_tokens": 0,
        "estimated_cost_usd": 0.0,
    }

    # Initialize manager
    manager = EpisodeEmbeddingManager(
        neo4j_uri=NEO4J_URI,
        neo4j_user=NEO4J_USER,
        neo4j_password=NEO4J_PASSWORD,
        neo4j_database=NEO4J_DATABASE,
    )

    try:
        # Get initial stats
        initial_stats = await manager.get_embedding_stats()
        logger.info(f"Initial state: {initial_stats}")

        if initial_stats["episodes_without_embeddings"] == 0:
            logger.info("All episodes already have embeddings!")
            return stats

        if dry_run:
            logger.info("=" * 60)
            logger.info("DRY RUN MODE - No embeddings will be created")
            logger.info("=" * 60)

        # Process in batches
        processed = 0
        batch_num = 0

        while True:
            if max_episodes and processed >= max_episodes:
                logger.info(f"Reached max_episodes limit: {max_episodes}")
                break

            # Get batch of episodes without embeddings
            batch_limit = min(batch_size, max_episodes - processed) if max_episodes else batch_size
            episodes = await manager.get_episodes_without_embeddings(limit=batch_limit)

            if not episodes:
                logger.info("No more episodes to process")
                break

            batch_num += 1
            logger.info(f"Processing batch {batch_num} ({len(episodes)} episodes)")

            for ep in episodes:
                uuid = ep["uuid"]
                content = ep["content"] or ""
                name = ep.get("name", "")

                # Track character/token counts
                char_count = len(content)
                stats["total_chars"] += char_count
                estimated_tokens = char_count // 4  # Rough estimate
                stats["estimated_tokens"] += estimated_tokens

                if dry_run:
                    logger.debug(f"Would process: {name[:50]}... ({char_count:,} chars)")
                    stats["skipped"] += 1
                else:
                    try:
                        success = await manager.add_content_embedding(uuid, content)
                        if success:
                            stats["successful"] += 1
                            logger.debug(f"Embedded: {name[:50]}...")
                        else:
                            stats["failed"] += 1
                            logger.warning(f"Failed to embed: {uuid}")
                    except Exception as e:
                        stats["failed"] += 1
                        logger.error(f"Error embedding {uuid}: {e}")

                processed += 1
                stats["total_processed"] = processed

            # Progress update every batch
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = processed / elapsed if elapsed > 0 else 0
            logger.info(
                f"Progress: {processed:,} episodes, "
                f"{stats['successful']:,} successful, "
                f"{stats['failed']:,} failed, "
                f"{rate:.1f} eps/sec"
            )

            # Small delay between batches to avoid overwhelming the API
            if not dry_run:
                await asyncio.sleep(0.5)

        # Calculate estimated cost
        # text-embedding-3-small: $0.02 per 1M tokens
        stats["estimated_cost_usd"] = (stats["estimated_tokens"] / 1_000_000) * 0.02

        # Get final stats
        final_stats = await manager.get_embedding_stats()

        duration = (datetime.now() - start_time).total_seconds()

        # Print summary
        print("\n" + "=" * 60)
        print("BACKFILL COMPLETE")
        print("=" * 60)
        print(f"Duration: {duration:.1f} seconds")
        print(f"Total processed: {stats['total_processed']:,}")
        print(f"Successful: {stats['successful']:,}")
        print(f"Failed: {stats['failed']:,}")
        print(f"Skipped (dry-run): {stats['skipped']:,}")
        print(f"Total characters: {stats['total_chars']:,}")
        print(f"Estimated tokens: {stats['estimated_tokens']:,}")
        print(f"Estimated cost: ${stats['estimated_cost_usd']:.4f}")
        print()
        print(f"Before: {initial_stats['episodes_with_embeddings']:,}/{initial_stats['total_episodes']:,} with embeddings")
        print(f"After: {final_stats['episodes_with_embeddings']:,}/{final_stats['total_episodes']:,} with embeddings")
        print(f"Coverage: {final_stats['coverage_percentage']:.1f}%")
        print("=" * 60)

        return stats

    finally:
        await manager.close()


async def main():
    parser = argparse.ArgumentParser(
        description="Backfill content embeddings for existing Episodic nodes"
    )
    parser.add_argument(
        "--batch-size", type=int, default=50,
        help="Number of episodes to process per batch (default: 50)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Only report what would be done, don't create embeddings"
    )
    parser.add_argument(
        "--max-episodes", type=int, default=None,
        help="Maximum number of episodes to process (default: all)"
    )
    parser.add_argument(
        "--skip-index-check", action="store_true",
        help="Skip checking if required indexes exist"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Episode Embedding Backfill")
    print("=" * 60)
    print(f"Neo4j URI: {NEO4J_URI}")
    print(f"Database: {NEO4J_DATABASE}")
    print(f"Batch size: {args.batch_size}")
    print(f"Max episodes: {args.max_episodes or 'All'}")
    print(f"Dry run: {args.dry_run}")
    print("=" * 60 + "\n")

    # Verify indexes exist
    if not args.skip_index_check:
        logger.info("Checking for required indexes...")
        indexes = await verify_indexes_exist()

        if not indexes["vector_index"]:
            logger.error(
                "Vector index 'episodic_content_embedding_index' not found!\n"
                "Run: uv run python scripts/init_graphiti_v3_database.py"
            )
            if not args.dry_run:
                logger.error("Aborting: Vector index must exist before backfill")
                return

        if not indexes["fulltext_index"]:
            logger.warning(
                "Fulltext index 'episodic_content_fulltext' not found.\n"
                "Run: uv run python scripts/init_graphiti_v3_database.py\n"
                "BM25 search will fall back to keyword matching."
            )

        logger.info(f"Index status: vector={indexes['vector_index']}, fulltext={indexes['fulltext_index']}")

    # Run backfill
    await backfill_embeddings(
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        max_episodes=args.max_episodes,
    )


if __name__ == "__main__":
    asyncio.run(main())
