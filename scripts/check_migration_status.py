"""
Check re-embedding migration status for entities, relationships, and episodic nodes.

This script queries Neo4j to show progress of the ada-002 migration:
- Total items
- Items migrated (with embedding_model = 'text-embedding-ada-002')
- Items pending (not yet migrated)
- Percentage complete

Usage:
    # Check all types
    python scripts/check_migration_status.py

    # Check entities only
    python scripts/check_migration_status.py --entities

    # Check relationships only
    python scripts/check_migration_status.py --relationships

    # Check episodic nodes only
    python scripts/check_migration_status.py --episodic

    # Detailed output (show oldest/newest migrations)
    python scripts/check_migration_status.py --detailed
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Dict, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from neo4j import AsyncGraphDatabase
from src.config import settings


async def check_entities_status(session, detailed: bool = False) -> Dict:
    """Check entity migration status."""

    # Count query
    query = """
    MATCH (e:Entity)
    WHERE e.name IS NOT NULL
    RETURN
      count(e) as total,
      count(CASE WHEN e.embedding_model = 'text-embedding-ada-002' THEN 1 END) as migrated,
      count(CASE WHEN e.embedding_model IS NULL OR e.embedding_model <> 'text-embedding-ada-002' THEN 1 END) as pending
    """

    result = await session.run(query)
    record = await result.single()

    stats = {
        'total': record['total'] if record else 0,
        'migrated': record['migrated'] if record else 0,
        'pending': record['pending'] if record else 0,
    }

    if detailed and stats['migrated'] > 0:
        # Get oldest and newest migrations
        detail_query = """
        MATCH (e:Entity)
        WHERE e.embedding_model = 'text-embedding-ada-002'
          AND e.embedding_migrated_at IS NOT NULL
        RETURN
          min(e.embedding_migrated_at) as oldest,
          max(e.embedding_migrated_at) as newest
        """
        result = await session.run(detail_query)
        detail = await result.single()
        if detail:
            stats['oldest_migration'] = detail['oldest']
            stats['newest_migration'] = detail['newest']

    return stats


async def check_relationships_status(session, detailed: bool = False) -> Dict:
    """Check relationship migration status."""

    # Count query
    query = """
    MATCH ()-[r:RELATES_TO]->()
    WHERE r.fact IS NOT NULL
    RETURN
      count(r) as total,
      count(CASE WHEN r.embedding_model = 'text-embedding-ada-002' THEN 1 END) as migrated,
      count(CASE WHEN r.embedding_model IS NULL OR r.embedding_model <> 'text-embedding-ada-002' THEN 1 END) as pending
    """

    result = await session.run(query)
    record = await result.single()

    stats = {
        'total': record['total'] if record else 0,
        'migrated': record['migrated'] if record else 0,
        'pending': record['pending'] if record else 0,
    }

    if detailed and stats['migrated'] > 0:
        # Get oldest and newest migrations
        detail_query = """
        MATCH ()-[r:RELATES_TO]->()
        WHERE r.embedding_model = 'text-embedding-ada-002'
          AND r.embedding_migrated_at IS NOT NULL
        RETURN
          min(r.embedding_migrated_at) as oldest,
          max(r.embedding_migrated_at) as newest
        """
        result = await session.run(detail_query)
        detail = await result.single()
        if detail:
            stats['oldest_migration'] = detail['oldest']
            stats['newest_migration'] = detail['newest']

    return stats


async def check_episodic_status(session, detailed: bool = False) -> Dict:
    """Check episodic node migration status."""

    # Count query
    query = """
    MATCH (ep:Episodic)
    WHERE ep.content IS NOT NULL
    RETURN
      count(ep) as total,
      count(CASE WHEN ep.embedding_model = 'text-embedding-ada-002' THEN 1 END) as migrated,
      count(CASE WHEN ep.embedding_model IS NULL OR ep.embedding_model <> 'text-embedding-ada-002' THEN 1 END) as pending
    """

    result = await session.run(query)
    record = await result.single()

    stats = {
        'total': record['total'] if record else 0,
        'migrated': record['migrated'] if record else 0,
        'pending': record['pending'] if record else 0,
    }

    if detailed and stats['migrated'] > 0:
        # Get oldest and newest migrations
        detail_query = """
        MATCH (ep:Episodic)
        WHERE ep.embedding_model = 'text-embedding-ada-002'
          AND ep.embedding_migrated_at IS NOT NULL
        RETURN
          min(ep.embedding_migrated_at) as oldest,
          max(ep.embedding_migrated_at) as newest
        """
        result = await session.run(detail_query)
        detail = await result.single()
        if detail:
            stats['oldest_migration'] = detail['oldest']
            stats['newest_migration'] = detail['newest']

    return stats


def print_stats(name: str, stats: Dict, detailed: bool = False):
    """Print migration statistics."""
    total = stats['total']
    migrated = stats['migrated']
    pending = stats['pending']

    if total == 0:
        print(f"\n{name}: No items found")
        return

    percentage = (migrated / total * 100) if total > 0 else 0

    print(f"\n{name}:")
    print(f"  Total:     {total:,}")
    print(f"  Migrated:  {migrated:,} ({percentage:.1f}%)")
    print(f"  Pending:   {pending:,} ({100-percentage:.1f}%)")

    # Status indicator
    if percentage == 0:
        print(f"  Status:    🔴 Not started")
    elif percentage < 100:
        print(f"  Status:    🟡 In progress")
    else:
        print(f"  Status:    🟢 Complete")

    # Detailed info
    if detailed and 'oldest_migration' in stats:
        print(f"\n  First migration:  {stats['oldest_migration']}")
        print(f"  Latest migration: {stats['newest_migration']}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check re-embedding migration status",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument("--entities", action="store_true", help="Check entities only")
    parser.add_argument("--relationships", action="store_true", help="Check relationships only")
    parser.add_argument("--episodic", action="store_true", help="Check episodic nodes only")
    parser.add_argument("--detailed", action="store_true", help="Show detailed information")

    args = parser.parse_args()

    # Default to all if none specified
    if not (args.entities or args.relationships or args.episodic):
        args.entities = args.relationships = args.episodic = True

    print("=" * 80)
    print("RE-EMBEDDING MIGRATION STATUS")
    print("=" * 80)
    print(f"\nDatabase: {settings.NEO4J_DATABASE}")
    print(f"Target model: text-embedding-ada-002")

    # Connect to Neo4j
    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
    )

    try:
        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            # Check each type
            total_items = 0
            total_migrated = 0

            if args.entities:
                stats = await check_entities_status(session, args.detailed)
                print_stats("Entities", stats, args.detailed)
                total_items += stats['total']
                total_migrated += stats['migrated']

            if args.relationships:
                stats = await check_relationships_status(session, args.detailed)
                print_stats("Relationships", stats, args.detailed)
                total_items += stats['total']
                total_migrated += stats['migrated']

            if args.episodic:
                stats = await check_episodic_status(session, args.detailed)
                print_stats("Episodic Nodes", stats, args.detailed)
                total_items += stats['total']
                total_migrated += stats['migrated']

            # Overall summary (if checking multiple types)
            if sum([args.entities, args.relationships, args.episodic]) > 1:
                overall_percentage = (total_migrated / total_items * 100) if total_items > 0 else 0

                print("\n" + "=" * 80)
                print("OVERALL SUMMARY")
                print("=" * 80)
                print(f"\nTotal items:    {total_items:,}")
                print(f"Migrated:       {total_migrated:,} ({overall_percentage:.1f}%)")
                print(f"Pending:        {total_items - total_migrated:,} ({100-overall_percentage:.1f}%)")

                if overall_percentage == 0:
                    print(f"\nStatus: 🔴 Not started")
                elif overall_percentage < 100:
                    print(f"\nStatus: 🟡 In progress ({overall_percentage:.1f}% complete)")
                else:
                    print(f"\nStatus: 🟢 Complete!")

            print("\n" + "=" * 80)

        return 0

    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        await driver.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
