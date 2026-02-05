"""BundestagDrucksache Manager - Main orchestration for intelligent Neo4j sync."""
import logging
from datetime import datetime
from typing import Any, Optional

import ray
from neo4j import GraphDatabase

from src.subagents.crud_subagent import CRUDSubagent

from .config import ManagerConfig
from .diff_analyzer import DrucksacheDiffAnalyzer
from .dip_client import BundestagDrucksacheDIPClient, MockBundestagDrucksacheDIPClient
from .sync_planner import DrucksacheSyncPlanner, SyncPlan

logger = logging.getLogger(__name__)


class SyncResult:
    """Result of a sync operation."""

    def __init__(
        self,
        success: bool,
        operations_attempted: int,
        operations_succeeded: int,
        operations_failed: int,
        execution_time_seconds: float,
        diff_summary: dict[str, Any],
        errors: list[str] = None,
    ):
        self.success = success
        self.operations_attempted = operations_attempted
        self.operations_succeeded = operations_succeeded
        self.operations_failed = operations_failed
        self.execution_time_seconds = execution_time_seconds
        self.diff_summary = diff_summary
        self.errors = errors or []

    def __repr__(self):
        return (
            f"SyncResult(success={self.success}, "
            f"attempted={self.operations_attempted}, "
            f"succeeded={self.operations_succeeded}, "
            f"failed={self.operations_failed})"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "operations_attempted": self.operations_attempted,
            "operations_succeeded": self.operations_succeeded,
            "operations_failed": self.operations_failed,
            "success_rate": (
                self.operations_succeeded / self.operations_attempted * 100
                if self.operations_attempted > 0
                else 0.0
            ),
            "execution_time_seconds": self.execution_time_seconds,
            "diff_summary": self.diff_summary,
            "errors": self.errors,
        }


class BundestagDrucksacheManager:
    """Manager for intelligent BundestagDrucksache data synchronization.

    This is the main entry point for the Manager Skill. It orchestrates:
    1. Analyzing differences between Neo4j and Bundestag DIP API
    2. Planning CRUD operations
    3. Executing operations in parallel via CRUD Subagent
    """

    def __init__(self, config: ManagerConfig = None, use_mock_dip: bool = False):
        """Initialize BundestagDrucksache Manager.

        Args:
            config: Manager configuration (loads from env if None)
            use_mock_dip: Use mock DIP client instead of real API
        """
        # Load config
        if config is None:
            config = ManagerConfig.from_env()
        self.config = config

        # Initialize Neo4j driver
        self.neo4j_driver = GraphDatabase.driver(
            config.neo4j_uri,
            auth=(config.neo4j_user, config.neo4j_password),
        )

        # Initialize DIP client
        if use_mock_dip:
            self.dip_client = MockBundestagDrucksacheDIPClient()
            logger.info("Using mock DIP client for Drucksache")
        else:
            self.dip_client = BundestagDrucksacheDIPClient(api_key=config.dip_api_key)
            logger.info("Using real DIP client for Drucksache")

        # Initialize components
        self.diff_analyzer = DrucksacheDiffAnalyzer(
            self.neo4j_driver, config.neo4j_database, self.dip_client
        )
        self.sync_planner = DrucksacheSyncPlanner(
            batch_size=config.batch_size,
            max_concurrent=config.max_concurrent_operations,
        )
        self.crud_subagent = CRUDSubagent(
            mcp_url=config.crud_mcp_url, num_replicas=config.crud_num_replicas
        )

        # Initialize Ray if needed
        if not ray.is_initialized():
            ray.init(ignore_reinit_error=True)
            logger.info("Ray initialized")

        logger.info("BundestagDrucksacheManager initialized")

    async def sync_all_drucksachen(
        self,
        limit: Optional[int] = None,
        wahlperiode: Optional[str] = None,
        dry_run: bool = False,
    ) -> SyncResult:
        """Synchronize all Drucksachen from Bundestag DIP API to Neo4j.

        This is the main method for full data synchronization.

        Args:
            limit: Maximum number of Drucksachen to sync (None = all)
            wahlperiode: Filter by Wahlperiode (e.g., "20", "21")
            dry_run: If True, analyze differences but don't execute operations

        Returns:
            SyncResult with execution details
        """
        logger.info(
            f"Starting full Drucksache sync (limit={limit}, wahlperiode={wahlperiode}, dry_run={dry_run})"
        )
        start_time = datetime.now()

        try:
            # Step 1: Analyze differences
            logger.info("Step 1: Analyzing differences...")
            diffs = await self.diff_analyzer.analyze_all_drucksachen(
                limit=limit, wahlperiode=wahlperiode
            )
            diff_summary = self.diff_analyzer.generate_summary(diffs)

            logger.info(f"Analysis complete: {diff_summary['total_diffs']} differences found")
            logger.info(f"  - Missing: {diff_summary['missing_count']}")
            logger.info(f"  - Outdated: {diff_summary['outdated_count']}")

            if not diffs:
                logger.info("No differences found - database is up to date")
                return SyncResult(
                    success=True,
                    operations_attempted=0,
                    operations_succeeded=0,
                    operations_failed=0,
                    execution_time_seconds=(datetime.now() - start_time).total_seconds(),
                    diff_summary=diff_summary,
                )

            # Step 2: Create sync plan
            logger.info("Step 2: Creating sync plan...")
            sync_plan = self.sync_planner.create_sync_plan(diffs)

            logger.info(
                f"Sync plan created: {len(sync_plan.operations)} operations in {len(sync_plan.batches)} batches"
            )
            logger.info(
                f"Estimated execution time: {sync_plan.summary['estimated_execution_time_seconds']:.2f}s"
            )

            if dry_run:
                logger.info("Dry run mode - skipping execution")
                return SyncResult(
                    success=True,
                    operations_attempted=len(sync_plan.operations),
                    operations_succeeded=0,
                    operations_failed=0,
                    execution_time_seconds=(datetime.now() - start_time).total_seconds(),
                    diff_summary=diff_summary,
                )

            # Step 3: Execute operations in parallel
            logger.info("Step 3: Executing operations...")
            execution_result = await self._execute_sync_plan(sync_plan)

            # Calculate total execution time
            total_time = (datetime.now() - start_time).total_seconds()

            logger.info(
                f"Sync complete in {total_time:.2f}s: "
                f"{execution_result['succeeded']} succeeded, "
                f"{execution_result['failed']} failed"
            )

            return SyncResult(
                success=execution_result["failed"] == 0,
                operations_attempted=len(sync_plan.operations),
                operations_succeeded=execution_result["succeeded"],
                operations_failed=execution_result["failed"],
                execution_time_seconds=total_time,
                diff_summary=diff_summary,
                errors=execution_result.get("errors", []),
            )

        except Exception as e:
            logger.error(f"Error during Drucksache sync: {e}", exc_info=True)
            total_time = (datetime.now() - start_time).total_seconds()
            return SyncResult(
                success=False,
                operations_attempted=0,
                operations_succeeded=0,
                operations_failed=0,
                execution_time_seconds=total_time,
                diff_summary={},
                errors=[str(e)],
            )

    async def sync_specific_drucksachen(
        self, drucksache_ids: list[str], dry_run: bool = False
    ) -> SyncResult:
        """Synchronize specific Drucksachen.

        Args:
            drucksache_ids: List of Drucksache IDs to sync
            dry_run: If True, analyze differences but don't execute operations

        Returns:
            SyncResult with execution details
        """
        logger.info(
            f"Starting sync for {len(drucksache_ids)} specific Drucksachen (dry_run={dry_run})"
        )
        start_time = datetime.now()

        try:
            # Analyze specific Drucksachen
            diffs = await self.diff_analyzer.analyze_specific_drucksachen(drucksache_ids)
            diff_summary = self.diff_analyzer.generate_summary(diffs)

            if not diffs:
                logger.info("No differences found for specified Drucksachen")
                return SyncResult(
                    success=True,
                    operations_attempted=0,
                    operations_succeeded=0,
                    operations_failed=0,
                    execution_time_seconds=(datetime.now() - start_time).total_seconds(),
                    diff_summary=diff_summary,
                )

            # Create sync plan
            sync_plan = self.sync_planner.create_sync_plan(diffs)

            if dry_run:
                logger.info("Dry run mode - skipping execution")
                return SyncResult(
                    success=True,
                    operations_attempted=len(sync_plan.operations),
                    operations_succeeded=0,
                    operations_failed=0,
                    execution_time_seconds=(datetime.now() - start_time).total_seconds(),
                    diff_summary=diff_summary,
                )

            # Execute operations
            execution_result = await self._execute_sync_plan(sync_plan)

            total_time = (datetime.now() - start_time).total_seconds()

            return SyncResult(
                success=execution_result["failed"] == 0,
                operations_attempted=len(sync_plan.operations),
                operations_succeeded=execution_result["succeeded"],
                operations_failed=execution_result["failed"],
                execution_time_seconds=total_time,
                diff_summary=diff_summary,
                errors=execution_result.get("errors", []),
            )

        except Exception as e:
            logger.error(f"Error during Drucksache sync: {e}", exc_info=True)
            total_time = (datetime.now() - start_time).total_seconds()
            return SyncResult(
                success=False,
                operations_attempted=0,
                operations_succeeded=0,
                operations_failed=0,
                execution_time_seconds=total_time,
                diff_summary={},
                errors=[str(e)],
            )

    async def _execute_sync_plan(self, sync_plan: SyncPlan) -> dict[str, Any]:
        """Execute a sync plan using CRUD subagent.

        Args:
            sync_plan: SyncPlan to execute

        Returns:
            Execution result dictionary
        """
        # Start CRUD subagent pool
        self.crud_subagent.start()

        try:
            # Execute all operations in batches
            all_results = await self.crud_subagent.execute_batch(
                sync_plan.operations, batch_size=self.config.batch_size
            )

            # Analyze results
            succeeded = sum(1 for r in all_results if r.success)
            failed = len(all_results) - succeeded
            errors = [r.error for r in all_results if not r.success and r.error]

            return {
                "succeeded": succeeded,
                "failed": failed,
                "errors": errors,
                "results": all_results,
            }

        finally:
            # Keep subagent running for future operations
            # Don't stop it here to allow reuse
            pass

    async def check_sync_status(self) -> dict[str, Any]:
        """Check current sync status without making changes.

        Returns:
            Status dictionary with difference counts
        """
        logger.info("Checking Drucksache sync status...")

        diffs = await self.diff_analyzer.analyze_all_drucksachen(limit=100)
        summary = self.diff_analyzer.generate_summary(diffs)

        return {
            "status": "out_of_sync" if diffs else "up_to_date",
            "total_differences": summary["total_diffs"],
            "missing_drucksachen": summary["missing_count"],
            "outdated_drucksachen": summary["outdated_count"],
            "most_changed_fields": summary["most_changed_fields"],
            "timestamp": summary["timestamp"],
        }

    def close(self):
        """Clean up resources."""
        logger.info("Closing BundestagDrucksacheManager...")

        # Stop CRUD subagent
        self.crud_subagent.stop()

        # Close Neo4j driver
        self.neo4j_driver.close()

        logger.info("BundestagDrucksacheManager closed")
