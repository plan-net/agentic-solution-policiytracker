"""SyncPlanner - Convert Aktivitaet diffs into CRUD operations and batch them."""
import logging
from typing import Any, Dict, List

from .diff_analyzer import AktivitaetDiff

logger = logging.getLogger(__name__)


class SyncPlan:
    """Represents a complete sync plan with batched operations."""

    def __init__(
        self,
        operations: List[Dict[str, Any]],
        batches: List[List[Dict[str, Any]]],
        summary: Dict[str, Any],
    ):
        self.operations = operations
        self.batches = batches
        self.summary = summary

    def __repr__(self):
        return f"SyncPlan(operations={len(self.operations)}, batches={len(self.batches)})"


class AktivitaetSyncPlanner:
    """Plans CRUD operations based on detected Aktivitaet differences."""

    def __init__(self, batch_size: int = 50, max_concurrent: int = 100):
        """Initialize AktivitaetSyncPlanner.

        Args:
            batch_size: Number of operations per batch
            max_concurrent: Maximum concurrent operations
        """
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        logger.info(
            f"AktivitaetSyncPlanner initialized (batch_size={batch_size}, max_concurrent={max_concurrent})"
        )

    def create_sync_plan(self, diffs: List[AktivitaetDiff]) -> SyncPlan:
        """Create a complete sync plan from differences.

        Args:
            diffs: List of AktivitaetDiff objects

        Returns:
            SyncPlan with batched operations
        """
        logger.info(f"Creating sync plan for {len(diffs)} differences")

        # Convert diffs to CRUD operations
        operations = []
        for diff in diffs:
            ops = self._diff_to_operations(diff)
            operations.extend(ops)

        logger.info(f"Generated {len(operations)} CRUD operations")

        # Batch operations
        batches = self._batch_operations(operations)
        logger.info(f"Created {len(batches)} batches")

        # Create summary
        summary = self._create_summary(diffs, operations, batches)

        return SyncPlan(operations=operations, batches=batches, summary=summary)

    def _diff_to_operations(self, diff: AktivitaetDiff) -> List[Dict[str, Any]]:
        """Convert a AktivitaetDiff into CRUD operations.

        Args:
            diff: AktivitaetDiff object

        Returns:
            List of operation dictionaries
        """
        operations = []

        if diff.diff_type == "missing":
            # Aktivitaet doesn't exist in Neo4j - create it
            # Ensure 'aktivitaet_nummer' is present (required by ENTITY_ID_FIELDS)
            properties = {**diff.dip_data, "active": True}
            # The DIP client should already have aktivitaet_nummer, but double-check
            if "aktivitaet_nummer" not in properties and "id" in properties:
                properties["aktivitaet_nummer"] = properties["id"]

            operations.append(
                {
                    "operation": "create_node",
                    "entity_type": "Aktivitaet",
                    "properties": properties,
                    "reason": "missing_in_neo4j",
                    "aktivitaet_id": diff.aktivitaet_id,
                }
            )

        elif diff.diff_type == "outdated":
            # Aktivitaet exists but has outdated fields - update it
            # Only update changed fields
            update_properties = {
                field: diff.dip_data.get(field) for field in diff.changed_fields
            }
            operations.append(
                {
                    "operation": "update_node",
                    "entity_type": "Aktivitaet",
                    "node_id": diff.aktivitaet_id,
                    "properties": update_properties,
                    "reason": "outdated_fields",
                    "aktivitaet_id": diff.aktivitaet_id,
                    "changed_fields": list(diff.changed_fields),
                }
            )

        return operations

    def _batch_operations(
        self, operations: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """Batch operations for parallel execution.

        Args:
            operations: List of all operations

        Returns:
            List of batches (each batch is a list of operations)
        """
        if not operations:
            return []

        # Limit total operations to max_concurrent
        limited_operations = operations[: self.max_concurrent]

        if len(operations) > self.max_concurrent:
            logger.warning(
                f"Limiting operations from {len(operations)} to {self.max_concurrent}"
            )

        # Create batches
        batches = []
        for i in range(0, len(limited_operations), self.batch_size):
            batch = limited_operations[i : i + self.batch_size]
            batches.append(batch)

        return batches

    def _create_summary(
        self,
        diffs: List[AktivitaetDiff],
        operations: List[Dict[str, Any]],
        batches: List[List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """Create summary of the sync plan.

        Args:
            diffs: Original differences
            operations: Generated operations
            batches: Batched operations

        Returns:
            Summary dictionary
        """
        operation_types = {}
        for op in operations:
            op_type = op["operation"]
            operation_types[op_type] = operation_types.get(op_type, 0) + 1

        return {
            "total_diffs": len(diffs),
            "total_operations": len(operations),
            "total_batches": len(batches),
            "batch_size": self.batch_size,
            "operation_types": operation_types,
            "estimated_execution_time_seconds": self._estimate_execution_time(
                len(operations), len(batches)
            ),
        }

    def _estimate_execution_time(
        self, num_operations: int, num_batches: int
    ) -> float:
        """Estimate execution time based on operation count.

        Args:
            num_operations: Total number of operations
            num_batches: Number of batches

        Returns:
            Estimated time in seconds
        """
        # Assumptions:
        # - Average operation takes 50ms
        # - Batches run sequentially (parallel within batch)
        # - Each batch has batch_size operations
        # - With 10 actors, we can do 10 operations in parallel

        avg_op_time_ms = 50
        parallelization_factor = 10  # 10 actors

        # Time per batch (operations run in parallel)
        ops_per_batch = min(self.batch_size, parallelization_factor)
        time_per_batch_ms = avg_op_time_ms * (self.batch_size / ops_per_batch)

        # Total time (batches run sequentially)
        total_time_ms = time_per_batch_ms * num_batches

        return total_time_ms / 1000  # Convert to seconds
