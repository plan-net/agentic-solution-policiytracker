"""CRUD Subagent - Ray actor for parallel Neo4j CRUD operations."""
import logging
from typing import Any, Dict, List, Union

import ray

from .config import CRUDSubagentConfig
from .mcp_client import MCPClient
from .schemas import (
    CreateNodeOperation,
    CreateRelationshipOperation,
    CRUDOperation,
    DeleteNodeOperation,
    OperationResult,
    QueryNodesOperation,
    UpdateNodeOperation,
    UpdateRelationshipOperation,
)

logger = logging.getLogger(__name__)


@ray.remote
class CRUDSubagentActor:
    """Ray actor for executing CRUD operations via MCP.

    This actor wraps the MCP client and provides parallel execution capabilities.
    Multiple instances can run concurrently to achieve high throughput.
    """

    def __init__(self, config: CRUDSubagentConfig):
        """Initialize CRUD subagent actor.

        Args:
            config: Configuration for subagent
        """
        self.config = config
        self.mcp_client = MCPClient(config)
        self.operations_executed = 0
        self.operations_succeeded = 0
        self.operations_failed = 0

        logger.info(f"CRUDSubagentActor initialized with MCP URL: {config.mcp_url}")

    async def execute_operation(
        self, operation: Union[Dict[str, Any], CRUDOperation]
    ) -> OperationResult:
        """Execute a single CRUD operation.

        Args:
            operation: Operation specification (dict or CRUDOperation)

        Returns:
            OperationResult with execution status
        """
        # Convert dict to operation object if needed
        if isinstance(operation, dict):
            operation = self._dict_to_operation(operation)

        self.operations_executed += 1

        try:
            # Route to appropriate MCP client method
            if isinstance(operation, CreateNodeOperation):
                result = await self.mcp_client.create_node(
                    operation.entity_type, operation.properties
                )

            elif isinstance(operation, UpdateNodeOperation):
                result = await self.mcp_client.update_node(
                    operation.entity_type, operation.node_id, operation.properties
                )

            elif isinstance(operation, DeleteNodeOperation):
                result = await self.mcp_client.delete_node(
                    operation.entity_type, operation.node_id, operation.hard_delete
                )

            elif isinstance(operation, CreateRelationshipOperation):
                result = await self.mcp_client.create_relationship(
                    operation.from_entity_type,
                    operation.from_node_id,
                    operation.to_entity_type,
                    operation.to_node_id,
                    operation.relationship_type,
                    operation.properties,
                )

            elif isinstance(operation, UpdateRelationshipOperation):
                result = await self.mcp_client.update_relationship(
                    operation.from_entity_type,
                    operation.from_node_id,
                    operation.to_entity_type,
                    operation.to_node_id,
                    operation.relationship_type,
                    operation.properties,
                )

            elif isinstance(operation, QueryNodesOperation):
                result = await self.mcp_client.query_nodes(
                    operation.entity_type,
                    operation.filters,
                    operation.limit,
                    operation.skip,
                )

            else:
                result = OperationResult(
                    success=False,
                    operation="unknown",
                    message=f"Unknown operation type: {type(operation)}",
                    error="Invalid operation type",
                    execution_time_ms=0,
                )

            # Update statistics
            if result.success:
                self.operations_succeeded += 1
            else:
                self.operations_failed += 1

            return result

        except Exception as e:
            self.operations_failed += 1
            logger.error(f"Error executing operation: {e}")
            return OperationResult(
                success=False,
                operation=getattr(operation, "operation", "unknown"),
                entity_type=getattr(operation, "entity_type", None),
                message=f"Exception during execution: {str(e)}",
                error=str(e),
                execution_time_ms=0,
            )

    def get_statistics(self) -> Dict[str, int]:
        """Get execution statistics for this actor.

        Returns:
            Statistics dictionary
        """
        return {
            "operations_executed": self.operations_executed,
            "operations_succeeded": self.operations_succeeded,
            "operations_failed": self.operations_failed,
            "success_rate": (
                self.operations_succeeded / self.operations_executed * 100
                if self.operations_executed > 0
                else 0.0
            ),
        }

    def _dict_to_operation(self, op_dict: Dict[str, Any]) -> CRUDOperation:
        """Convert dict to operation object.

        Args:
            op_dict: Operation dictionary

        Returns:
            CRUDOperation subclass instance
        """
        operation_type = op_dict.get("operation")

        if operation_type == "create_node":
            return CreateNodeOperation(**op_dict)
        elif operation_type == "update_node":
            return UpdateNodeOperation(**op_dict)
        elif operation_type == "delete_node":
            return DeleteNodeOperation(**op_dict)
        elif operation_type == "create_relationship":
            return CreateRelationshipOperation(**op_dict)
        elif operation_type == "update_relationship":
            return UpdateRelationshipOperation(**op_dict)
        elif operation_type == "query_nodes":
            return QueryNodesOperation(**op_dict)
        else:
            raise ValueError(f"Unknown operation type: {operation_type}")


class CRUDSubagent:
    """Manager for CRUD subagent actor pool.

    Handles actor lifecycle and distributes operations across multiple actors
    for parallel execution.
    """

    def __init__(
        self, config: CRUDSubagentConfig = None, mcp_url: str = None, num_replicas: int = None
    ):
        """Initialize CRUD subagent manager.

        Args:
            config: Full configuration (optional)
            mcp_url: MCP server URL (overrides config)
            num_replicas: Number of actor replicas (overrides config)
        """
        # Load config
        if config is None:
            config = CRUDSubagentConfig.from_env()

        # Override with provided values
        if mcp_url:
            config.mcp_url = mcp_url
        if num_replicas:
            config.num_replicas = num_replicas

        self.config = config
        self.actors: List[ray.ObjectRef] = []

        logger.info(
            f"CRUDSubagent initialized with {config.num_replicas} replicas"
        )

    def start(self):
        """Start the actor pool."""
        if self.actors:
            logger.warning("Actor pool already started")
            return

        logger.info(f"Starting {self.config.num_replicas} CRUD subagent actors...")

        for i in range(self.config.num_replicas):
            actor = CRUDSubagentActor.remote(self.config)
            self.actors.append(actor)

        logger.info(f"Started {len(self.actors)} CRUD subagent actors")

    def stop(self):
        """Stop the actor pool."""
        logger.info("Stopping CRUD subagent actors...")
        for actor in self.actors:
            ray.kill(actor)
        self.actors = []
        logger.info("All actors stopped")

    async def execute_operation(
        self, operation: Union[Dict[str, Any], CRUDOperation]
    ) -> OperationResult:
        """Execute a single operation using any available actor.

        Args:
            operation: Operation to execute

        Returns:
            OperationResult
        """
        if not self.actors:
            self.start()

        # Use first actor (round-robin can be added if needed)
        actor = self.actors[0]
        result = await actor.execute_operation.remote(operation)
        return result

    async def execute_parallel(
        self, operations: List[Union[Dict[str, Any], CRUDOperation]]
    ) -> List[OperationResult]:
        """Execute multiple operations in parallel across actor pool.

        This is the key method that enables 10-20x speedup through parallelization.

        Args:
            operations: List of operations to execute

        Returns:
            List of OperationResults in same order as input
        """
        if not self.actors:
            self.start()

        if not operations:
            return []

        logger.info(
            f"Executing {len(operations)} operations in parallel across {len(self.actors)} actors"
        )

        # Distribute operations across actors using round-robin
        actor_assignments = []
        for i, operation in enumerate(operations):
            actor_idx = i % len(self.actors)
            actor = self.actors[actor_idx]
            actor_assignments.append(actor.execute_operation.remote(operation))

        # Wait for all operations to complete using Ray's async API
        results = ray.get(actor_assignments)

        # Log summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_time = sum(r.execution_time_ms for r in results)
        avg_time = total_time / len(results) if results else 0

        logger.info(
            f"Parallel execution complete: {successful} succeeded, {failed} failed, "
            f"avg time: {avg_time:.2f}ms"
        )

        return results

    async def execute_batch(
        self,
        operations: List[Union[Dict[str, Any], CRUDOperation]],
        batch_size: int = None,
    ) -> List[OperationResult]:
        """Execute operations in batches.

        Useful for very large operation sets to avoid overwhelming the system.

        Args:
            operations: List of operations
            batch_size: Operations per batch (defaults to num_replicas * 10)

        Returns:
            List of all OperationResults
        """
        if not self.actors:
            self.start()

        if batch_size is None:
            batch_size = len(self.actors) * 10

        all_results = []
        total_batches = (len(operations) + batch_size - 1) // batch_size

        logger.info(
            f"Executing {len(operations)} operations in {total_batches} batches of {batch_size}"
        )

        for batch_idx in range(0, len(operations), batch_size):
            batch = operations[batch_idx : batch_idx + batch_size]
            batch_num = (batch_idx // batch_size) + 1

            logger.info(
                f"Processing batch {batch_num}/{total_batches} ({len(batch)} operations)"
            )

            batch_results = await self.execute_parallel(batch)
            all_results.extend(batch_results)

        return all_results

    async def get_pool_statistics(self) -> Dict[str, Any]:
        """Get statistics from all actors in the pool.

        Returns:
            Aggregated statistics
        """
        if not self.actors:
            return {
                "total_actors": 0,
                "total_operations": 0,
                "total_succeeded": 0,
                "total_failed": 0,
                "overall_success_rate": 0.0,
            }

        # Get statistics from each actor
        stats_refs = [actor.get_statistics.remote() for actor in self.actors]
        actor_stats = ray.get(stats_refs)

        # Aggregate
        total_ops = sum(s["operations_executed"] for s in actor_stats)
        total_succeeded = sum(s["operations_succeeded"] for s in actor_stats)
        total_failed = sum(s["operations_failed"] for s in actor_stats)

        return {
            "total_actors": len(self.actors),
            "total_operations": total_ops,
            "total_succeeded": total_succeeded,
            "total_failed": total_failed,
            "overall_success_rate": (
                total_succeeded / total_ops * 100 if total_ops > 0 else 0.0
            ),
            "per_actor_stats": actor_stats,
        }


# Add missing import
import asyncio
