#!/usr/bin/env python
"""Trigger BundestagPerson Manager sync.

Usage:
    # Check sync status
    uv run python scripts/trigger_person_sync.py --status

    # Dry run (preview changes)
    uv run python scripts/trigger_person_sync.py --dry-run

    # Full sync with mock DIP API
    uv run python scripts/trigger_person_sync.py

    # Full sync with real DIP API
    uv run python scripts/trigger_person_sync.py --real-api

    # Sync specific persons
    uv run python scripts/trigger_person_sync.py --persons 11004809 11003142

    # Sync with custom configuration
    uv run python scripts/trigger_person_sync.py --actors 20 --batch-size 100
"""
import argparse
import asyncio
import logging
import sys
from datetime import datetime

import ray

from src.skills.bundestag_person_manager import BundestagPersonManager
from src.skills.bundestag_person_manager.config import ManagerConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(
        description="Trigger BundestagPerson Manager sync"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Check sync status without making changes",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them",
    )
    parser.add_argument(
        "--real-api",
        action="store_true",
        help="Use real Bundestag DIP API (requires BUNDESTAG_DIP_API_KEY)",
    )
    parser.add_argument(
        "--persons",
        nargs="+",
        help="Sync specific person IDs only",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of persons to sync (for testing)",
    )
    parser.add_argument(
        "--actors",
        type=int,
        default=10,
        help="Number of Ray actors (default: 10)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for operations (default: 50)",
    )

    args = parser.parse_args()

    # Initialize Ray if needed
    if not ray.is_initialized():
        logger.info("Initializing Ray...")
        ray.init(ignore_reinit_error=True)

    # Create config with custom settings
    config = ManagerConfig.from_env()
    config.crud_num_replicas = args.actors
    config.batch_size = args.batch_size

    # Initialize manager
    use_mock = not args.real_api
    logger.info(
        f"Initializing BundestagPersonManager (mock_api={use_mock}, actors={args.actors})"
    )
    manager = BundestagPersonManager(config=config, use_mock_dip=use_mock)

    try:
        # Status check mode
        if args.status:
            logger.info("Checking sync status...")
            status = await manager.check_sync_status()

            print("\n" + "=" * 60)
            print("📊 BundestagPerson Sync Status")
            print("=" * 60)
            print(f"Status: {status['status']}")
            print(f"Total differences: {status['total_differences']}")
            print(f"Missing persons: {status['missing_persons']}")
            print(f"Outdated persons: {status['outdated_persons']}")

            if status.get("most_changed_fields"):
                print("\nMost changed fields:")
                for field, count in list(status["most_changed_fields"].items())[:5]:
                    print(f"  - {field}: {count} changes")

            print(f"\nChecked at: {status['timestamp']}")
            print("=" * 60)
            return

        # Specific persons sync
        if args.persons:
            logger.info(f"Syncing {len(args.persons)} specific persons...")

            if args.dry_run:
                logger.info("Dry run mode enabled")

            result = await manager.sync_specific_persons(
                args.persons, dry_run=args.dry_run
            )

        # Full sync
        else:
            logger.info(
                f"Starting full sync (limit={args.limit}, dry_run={args.dry_run})"
            )

            result = await manager.sync_all_persons(
                limit=args.limit, dry_run=args.dry_run
            )

        # Display results
        print("\n" + "=" * 60)
        if args.dry_run:
            print("👀 Dry Run Results")
        else:
            print("✅ Sync Results")
        print("=" * 60)
        print(f"Success: {result.success}")
        print(f"Operations attempted: {result.operations_attempted}")
        print(f"Operations succeeded: {result.operations_succeeded}")
        print(f"Operations failed: {result.operations_failed}")
        print(f"Execution time: {result.execution_time_seconds:.2f}s")

        if result.operations_attempted > 0:
            success_rate = (
                result.operations_succeeded / result.operations_attempted * 100
            )
            print(f"Success rate: {success_rate:.1f}%")

            if result.operations_succeeded > 0:
                ops_per_second = (
                    result.operations_succeeded / result.execution_time_seconds
                )
                print(f"Throughput: {ops_per_second:.2f} operations/second")

        # Diff summary
        if result.diff_summary:
            print("\nDifferences found:")
            print(f"  Missing: {result.diff_summary.get('missing_count', 0)}")
            print(f"  Outdated: {result.diff_summary.get('outdated_count', 0)}")

            if result.diff_summary.get("most_changed_fields"):
                print("\nMost changed fields:")
                for field, count in list(
                    result.diff_summary["most_changed_fields"].items()
                )[:5]:
                    print(f"  - {field}: {count} changes")

        # Errors
        if result.errors:
            print(f"\n⚠️  {len(result.errors)} errors occurred:")
            for error in result.errors[:5]:  # Show first 5 errors
                print(f"  - {error}")
            if len(result.errors) > 5:
                print(f"  ... and {len(result.errors) - 5} more")

        print("=" * 60)

        # Exit code based on success
        if result.success:
            logger.info("Sync completed successfully")
            sys.exit(0)
        else:
            logger.error("Sync completed with failures")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Sync failed with error: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        sys.exit(1)

    finally:
        manager.close()


if __name__ == "__main__":
    asyncio.run(main())
