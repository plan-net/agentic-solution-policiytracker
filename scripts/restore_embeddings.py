"""
Restore embeddings from JSON backup.

This script restores embeddings from a backup file created by backup_embeddings.py.
Use this for rollback if the re-embedding process encounters issues.

Usage:
    # Restore all embeddings from backup
    python scripts/restore_embeddings.py backup_embeddings_20260117_120000.json

    # Restore entities only
    python scripts/restore_embeddings.py backup_embeddings_20260117_120000.json --entities

    # Restore relationships only
    python scripts/restore_embeddings.py backup_embeddings_20260117_120000.json --relationships

    # Restore episodic nodes only
    python scripts/restore_embeddings.py backup_embeddings_20260117_120000.json --episodic

    # Dry run (preview what would be restored)
    python scripts/restore_embeddings.py backup_embeddings_20260117_120000.json --dry-run

    # Limit number of items (for testing)
    python scripts/restore_embeddings.py backup_embeddings_20260117_120000.json --limit 10
"""

import argparse
import asyncio
import json
import gzip
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from neo4j import AsyncGraphDatabase
from tqdm.asyncio import tqdm
from src.config import settings


async def restore_entities(session, entities: List[Dict], limit: int = None, dry_run: bool = False) -> int:
    """Restore entity embeddings from backup."""
    print("\n📦 Restoring entity embeddings...")

    if limit:
        entities = entities[:limit]

    if dry_run:
        print(f"  Would restore {len(entities):,} entities")
        return 0

    restored = 0
    pbar = tqdm(total=len(entities), desc="Entities", unit="entity")

    for entity in entities:
        uuid = entity['uuid']
        embedding = entity['embedding']
        original_model = entity.get('model')  # May be None for old embeddings

        # Restore embedding and remove migration markers
        query = """
        MATCH (e:Entity {uuid: $uuid})
        SET e.name_embedding = $embedding
        REMOVE e.embedding_model, e.embedding_migrated_at
        """

        # If original model was specified, restore it
        if original_model:
            query = """
            MATCH (e:Entity {uuid: $uuid})
            SET e.name_embedding = $embedding,
                e.embedding_model = $original_model
            REMOVE e.embedding_migrated_at
            """

        await session.run(query, {
            "uuid": uuid,
            "embedding": embedding,
            "original_model": original_model
        })

        restored += 1
        pbar.update(1)

    pbar.close()
    print(f"  ✓ Restored {restored:,} entity embeddings")
    return restored


async def restore_relationships(session, relationships: List[Dict], limit: int = None, dry_run: bool = False) -> int:
    """Restore relationship embeddings from backup."""
    print("\n📦 Restoring relationship embeddings...")

    if limit:
        relationships = relationships[:limit]

    if dry_run:
        print(f"  Would restore {len(relationships):,} relationships")
        return 0

    restored = 0
    pbar = tqdm(total=len(relationships), desc="Relationships", unit="rel")

    for rel in relationships:
        rel_id = rel['rel_id']
        embedding = rel['embedding']
        original_model = rel.get('model')  # May be None for old embeddings

        # Restore embedding and remove migration markers
        query = """
        MATCH ()-[r:RELATES_TO]->()
        WHERE id(r) = $rel_id
        SET r.fact_embedding = $embedding
        REMOVE r.embedding_model, r.embedding_migrated_at
        """

        # If original model was specified, restore it
        if original_model:
            query = """
            MATCH ()-[r:RELATES_TO]->()
            WHERE id(r) = $rel_id
            SET r.fact_embedding = $embedding,
                r.embedding_model = $original_model
            REMOVE r.embedding_migrated_at
            """

        await session.run(query, {
            "rel_id": rel_id,
            "embedding": embedding,
            "original_model": original_model
        })

        restored += 1
        pbar.update(1)

    pbar.close()
    print(f"  ✓ Restored {restored:,} relationship embeddings")
    return restored


async def restore_episodic(session, episodic: List[Dict], limit: int = None, dry_run: bool = False) -> int:
    """Restore episodic node embeddings from backup."""
    print("\n📦 Restoring episodic node embeddings...")

    if limit:
        episodic = episodic[:limit]

    if dry_run:
        print(f"  Would restore {len(episodic):,} episodic nodes")
        return 0

    restored = 0
    pbar = tqdm(total=len(episodic), desc="Episodic", unit="node")

    for ep in episodic:
        uuid = ep['uuid']
        embedding = ep['embedding']
        original_model = ep.get('model')  # May be None for old embeddings

        # Restore embedding and remove migration markers
        query = """
        MATCH (ep:Episodic {uuid: $uuid})
        SET ep.content_embedding = $embedding
        REMOVE ep.embedding_model, ep.embedding_migrated_at
        """

        # If original model was specified, restore it
        if original_model:
            query = """
            MATCH (ep:Episodic {uuid: $uuid})
            SET ep.content_embedding = $embedding,
                ep.embedding_model = $original_model
            REMOVE ep.embedding_migrated_at
            """

        await session.run(query, {
            "uuid": uuid,
            "embedding": embedding,
            "original_model": original_model
        })

        restored += 1
        pbar.update(1)

    pbar.close()
    print(f"  ✓ Restored {restored:,} episodic node embeddings")
    return restored


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Restore embeddings from JSON backup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument("backup_file", type=str, help="Path to backup JSON file (supports .gz)")
    parser.add_argument("--entities", action="store_true", help="Restore entities only")
    parser.add_argument("--relationships", action="store_true", help="Restore relationships only")
    parser.add_argument("--episodic", action="store_true", help="Restore episodic nodes only")
    parser.add_argument("--limit", type=int, help="Limit number of items per type (for testing)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")

    args = parser.parse_args()

    # Default to all if none specified
    if not (args.entities or args.relationships or args.episodic):
        args.entities = args.relationships = args.episodic = True

    print("=" * 80)
    print("RESTORE EMBEDDINGS FROM BACKUP")
    print("=" * 80)
    print(f"\nBackup file: {args.backup_file}")
    print(f"Database: {settings.NEO4J_DATABASE}")

    if args.limit:
        print(f"⚠️  LIMIT: {args.limit} items per type (testing mode)")
    if args.dry_run:
        print(f"⚠️  DRY RUN: No changes will be made")

    print("\nRestoring:")
    if args.entities:
        print("  ✓ Entities")
    if args.relationships:
        print("  ✓ Relationships")
    if args.episodic:
        print("  ✓ Episodic nodes")

    # Load backup file
    backup_path = Path(args.backup_file)
    if not backup_path.exists():
        print(f"\n❌ ERROR: Backup file not found: {args.backup_file}")
        return 1

    print(f"\n📂 Loading backup file...")

    try:
        if backup_path.suffix == '.gz':
            with gzip.open(backup_path, 'rt', encoding='utf-8') as f:
                backup_data = json.load(f)
        else:
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
    except Exception as e:
        print(f"\n❌ ERROR: Failed to load backup file: {e}")
        return 1

    print(f"  ✓ Loaded backup from {backup_data['timestamp']}")
    print(f"  Entities: {len(backup_data['entities']):,}")
    print(f"  Relationships: {len(backup_data['relationships']):,}")
    print(f"  Episodic: {len(backup_data['episodic']):,}")

    # Connect to Neo4j
    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
    )

    total_restored = 0

    try:
        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            # Restore each type
            if args.entities and backup_data['entities']:
                restored = await restore_entities(session, backup_data['entities'], args.limit, args.dry_run)
                total_restored += restored

            if args.relationships and backup_data['relationships']:
                restored = await restore_relationships(session, backup_data['relationships'], args.limit, args.dry_run)
                total_restored += restored

            if args.episodic and backup_data['episodic']:
                restored = await restore_episodic(session, backup_data['episodic'], args.limit, args.dry_run)
                total_restored += restored

        # Print summary
        print("\n" + "=" * 80)
        print("RESTORE COMPLETE")
        print("=" * 80)

        if args.dry_run:
            print("\n✓ Dry run completed - no changes made")
        else:
            print(f"\n✅ Successfully restored {total_restored:,} embeddings")
            print("\n⚠️  Note: Migration marker properties (embedding_model, embedding_migrated_at)")
            print("   have been removed. Items are restored to pre-migration state.")

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
