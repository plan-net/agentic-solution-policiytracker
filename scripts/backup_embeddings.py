"""
Backup embeddings to JSON before re-embedding with ada-002.

This script exports existing embeddings to a timestamped JSON file
for safety and rollback capability.

Usage:
    # Backup all embeddings
    python scripts/backup_embeddings.py

    # Backup entities only
    python scripts/backup_embeddings.py --entities

    # Backup relationships only
    python scripts/backup_embeddings.py --relationships

    # Backup episodic nodes only
    python scripts/backup_embeddings.py --episodic

    # Custom output directory
    python scripts/backup_embeddings.py --output-dir /path/to/backups
"""

import argparse
import asyncio
import json
import gzip
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from neo4j import AsyncGraphDatabase
from src.config import settings


async def backup_entities(session, limit: Optional[int] = None) -> List[Dict]:
    """Backup entity embeddings."""
    print("\n📦 Backing up entity embeddings...")

    query = """
    MATCH (e:Entity)
    WHERE e.name_embedding IS NOT NULL
    RETURN e.uuid as uuid,
           e.name as name,
           e.name_embedding as embedding,
           e.embedding_model as model
    ORDER BY e.uuid
    """

    if limit:
        query += f"\nLIMIT {limit}"

    result = await session.run(query)
    records = await result.data()

    print(f"  ✓ Backed up {len(records):,} entity embeddings")
    return records


async def backup_relationships(session, limit: Optional[int] = None) -> List[Dict]:
    """Backup relationship embeddings."""
    print("\n📦 Backing up relationship embeddings...")

    query = """
    MATCH ()-[r:RELATES_TO]->()
    WHERE r.fact_embedding IS NOT NULL
    RETURN id(r) as rel_id,
           r.fact as fact,
           r.fact_embedding as embedding,
           r.embedding_model as model
    ORDER BY id(r)
    """

    if limit:
        query += f"\nLIMIT {limit}"

    result = await session.run(query)
    records = await result.data()

    print(f"  ✓ Backed up {len(records):,} relationship embeddings")
    return records


async def backup_episodic(session, limit: Optional[int] = None) -> List[Dict]:
    """Backup episodic node embeddings."""
    print("\n📦 Backing up episodic node embeddings...")

    query = """
    MATCH (ep:Episodic)
    WHERE ep.content_embedding IS NOT NULL
    RETURN ep.uuid as uuid,
           ep.content as content,
           ep.content_embedding as embedding,
           ep.embedding_model as model
    ORDER BY ep.uuid
    """

    if limit:
        query += f"\nLIMIT {limit}"

    result = await session.run(query)
    records = await result.data()

    print(f"  ✓ Backed up {len(records):,} episodic node embeddings")
    return records


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Backup embeddings to JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument("--entities", action="store_true", help="Backup entities")
    parser.add_argument("--relationships", action="store_true", help="Backup relationships")
    parser.add_argument("--episodic", action="store_true", help="Backup episodic nodes")
    parser.add_argument("--limit", type=int, help="Limit number of items per type (for testing)")
    parser.add_argument("--output-dir", type=str, default="backups", help="Output directory (default: backups)")
    parser.add_argument("--compress", action="store_true", help="Compress output with gzip")

    args = parser.parse_args()

    # Default to all if none specified
    if not (args.entities or args.relationships or args.episodic):
        args.entities = args.relationships = args.episodic = True

    print("=" * 80)
    print("EMBEDDING BACKUP")
    print("=" * 80)
    print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Database: {settings.NEO4J_DATABASE}")

    if args.limit:
        print(f"⚠️  LIMIT: {args.limit} items per type (testing mode)")

    print("\nBacking up:")
    if args.entities:
        print("  ✓ Entities")
    if args.relationships:
        print("  ✓ Relationships")
    if args.episodic:
        print("  ✓ Episodic nodes")

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_embeddings_{timestamp}.json"
    if args.compress:
        filename += ".gz"

    output_path = output_dir / filename

    # Connect to Neo4j
    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
    )

    backup_data = {
        "timestamp": datetime.now().isoformat(),
        "database": settings.NEO4J_DATABASE,
        "entities": [],
        "relationships": [],
        "episodic": []
    }

    try:
        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            # Backup each type
            if args.entities:
                backup_data["entities"] = await backup_entities(session, args.limit)

            if args.relationships:
                backup_data["relationships"] = await backup_relationships(session, args.limit)

            if args.episodic:
                backup_data["episodic"] = await backup_episodic(session, args.limit)

        # Write to file (streaming to avoid memory issues)
        print(f"\n💾 Writing backup to {output_path}...")

        # Force compression for large backups to save memory
        if not args.compress and (len(backup_data['entities']) + len(backup_data['relationships']) + len(backup_data['episodic'])) > 10000:
            print("  (Automatically using compression for large backup)")
            if not output_path.suffix == '.gz':
                output_path = Path(str(output_path) + '.gz')
            args.compress = True

        if args.compress:
            with gzip.open(output_path, 'wt', encoding='utf-8') as f:
                # Write incrementally to reduce memory usage
                f.write('{\n')
                f.write(f'  "timestamp": "{backup_data["timestamp"]}",\n')
                f.write(f'  "database": "{backup_data["database"]}",\n')
                f.write('  "entities": ')
                json.dump(backup_data['entities'], f)
                f.write(',\n  "relationships": ')
                json.dump(backup_data['relationships'], f)
                f.write(',\n  "episodic": ')
                json.dump(backup_data['episodic'], f)
                f.write('\n}')
        else:
            with open(output_path, 'w', encoding='utf-8') as f:
                # Write incrementally to reduce memory usage
                f.write('{\n')
                f.write(f'  "timestamp": "{backup_data["timestamp"]}",\n')
                f.write(f'  "database": "{backup_data["database"]}",\n')
                f.write('  "entities": ')
                json.dump(backup_data['entities'], f)
                f.write(',\n  "relationships": ')
                json.dump(backup_data['relationships'], f)
                f.write(',\n  "episodic": ')
                json.dump(backup_data['episodic'], f)
                f.write('\n}')

        # Print summary
        file_size_mb = output_path.stat().st_size / (1024 * 1024)

        print("\n" + "=" * 80)
        print("BACKUP COMPLETE")
        print("=" * 80)
        print(f"\nBackup file: {output_path}")
        print(f"File size: {file_size_mb:.2f} MB")
        print(f"\nItems backed up:")
        print(f"  Entities: {len(backup_data['entities']):,}")
        print(f"  Relationships: {len(backup_data['relationships']):,}")
        print(f"  Episodic: {len(backup_data['episodic']):,}")
        print(f"  Total: {len(backup_data['entities']) + len(backup_data['relationships']) + len(backup_data['episodic']):,}")
        print("\n✅ Backup successful!")
        print("=" * 80)

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
