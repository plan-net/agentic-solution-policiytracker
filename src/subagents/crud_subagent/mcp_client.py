"""HTTP client for Neo4j CRUD MCP Server."""
import asyncio
import logging
from typing import Any, Dict, Optional

import httpx

from .config import CRUDSubagentConfig
from .schemas import OperationResult

logger = logging.getLogger(__name__)


class MCPClient:
    """HTTP client for Neo4j CRUD MCP Server."""

    def __init__(self, config: CRUDSubagentConfig):
        """Initialize MCP client.

        Args:
            config: Configuration for CRUD subagent
        """
        self.config = config
        self.base_url = config.mcp_url.rstrip("/")
        self.timeout = httpx.Timeout(config.timeout_seconds)

    async def _make_request(
        self, endpoint: str, payload: Dict[str, Any], attempt: int = 1
    ) -> Dict[str, Any]:
        """Make HTTP request to MCP server with retry logic.

        Args:
            endpoint: API endpoint (e.g., "/create_node")
            payload: Request payload
            attempt: Current retry attempt

        Returns:
            Response JSON

        Raises:
            Exception: If all retries fail
        """
        url = f"{self.base_url}{endpoint}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)

                if response.status_code == 200:
                    return response.json()
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    logger.error(f"MCP request failed: {error_msg}")

                    # Retry on server errors
                    if (
                        response.status_code >= 500
                        and attempt < self.config.max_retries
                    ):
                        await asyncio.sleep(
                            self.config.retry_delay_seconds * attempt
                        )
                        return await self._make_request(
                            endpoint, payload, attempt + 1
                        )

                    raise Exception(error_msg)

        except httpx.TimeoutException:
            logger.error(f"MCP request timeout on attempt {attempt}")
            if attempt < self.config.max_retries:
                await asyncio.sleep(self.config.retry_delay_seconds * attempt)
                return await self._make_request(endpoint, payload, attempt + 1)
            raise

        except Exception as e:
            logger.error(f"MCP request error: {e}")
            if attempt < self.config.max_retries:
                await asyncio.sleep(self.config.retry_delay_seconds * attempt)
                return await self._make_request(endpoint, payload, attempt + 1)
            raise

    async def create_node(
        self, entity_type: str, properties: Dict[str, Any]
    ) -> OperationResult:
        """Create a new node.

        Args:
            entity_type: Entity type (e.g., "BundestagPerson")
            properties: Node properties

        Returns:
            OperationResult with success status
        """
        import time

        start_time = time.time()

        try:
            response = await self._make_request(
                "/create_node",
                {"entity_type": entity_type, "properties": properties},
            )

            execution_time = (time.time() - start_time) * 1000

            return OperationResult(
                success=response.get("success", False),
                operation="create_node",
                entity_type=entity_type,
                node_id=response.get("data", {}).get("node_id"),
                message=response.get("message", ""),
                data=response.get("data"),
                error=response.get("error"),
                execution_time_ms=execution_time,
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return OperationResult(
                success=False,
                operation="create_node",
                entity_type=entity_type,
                message=f"Failed to create node: {str(e)}",
                error=str(e),
                execution_time_ms=execution_time,
            )

    async def update_node(
        self, entity_type: str, node_id: str, properties: Dict[str, Any]
    ) -> OperationResult:
        """Update an existing node.

        Args:
            entity_type: Entity type
            node_id: Node identifier
            properties: Properties to update

        Returns:
            OperationResult with success status
        """
        import time

        start_time = time.time()

        try:
            response = await self._make_request(
                "/update_node",
                {
                    "entity_type": entity_type,
                    "node_id": node_id,
                    "properties": properties,
                },
            )

            execution_time = (time.time() - start_time) * 1000

            return OperationResult(
                success=response.get("success", False),
                operation="update_node",
                entity_type=entity_type,
                node_id=node_id,
                message=response.get("message", ""),
                data=response.get("data"),
                error=response.get("error"),
                execution_time_ms=execution_time,
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return OperationResult(
                success=False,
                operation="update_node",
                entity_type=entity_type,
                node_id=node_id,
                message=f"Failed to update node: {str(e)}",
                error=str(e),
                execution_time_ms=execution_time,
            )

    async def delete_node(
        self, entity_type: str, node_id: str, hard_delete: bool = False
    ) -> OperationResult:
        """Delete a node.

        Args:
            entity_type: Entity type
            node_id: Node identifier
            hard_delete: If True, permanently delete. If False, soft delete.

        Returns:
            OperationResult with success status
        """
        import time

        start_time = time.time()

        try:
            response = await self._make_request(
                "/delete_node",
                {
                    "entity_type": entity_type,
                    "node_id": node_id,
                    "hard_delete": hard_delete,
                },
            )

            execution_time = (time.time() - start_time) * 1000

            return OperationResult(
                success=response.get("success", False),
                operation="delete_node",
                entity_type=entity_type,
                node_id=node_id,
                message=response.get("message", ""),
                data=response.get("data"),
                error=response.get("error"),
                execution_time_ms=execution_time,
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return OperationResult(
                success=False,
                operation="delete_node",
                entity_type=entity_type,
                node_id=node_id,
                message=f"Failed to delete node: {str(e)}",
                error=str(e),
                execution_time_ms=execution_time,
            )

    async def create_relationship(
        self,
        from_entity_type: str,
        from_node_id: str,
        to_entity_type: str,
        to_node_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> OperationResult:
        """Create a relationship between two nodes.

        Args:
            from_entity_type: Source entity type
            from_node_id: Source node ID
            to_entity_type: Target entity type
            to_node_id: Target node ID
            relationship_type: Relationship type
            properties: Relationship properties

        Returns:
            OperationResult with success status
        """
        import time

        start_time = time.time()

        try:
            response = await self._make_request(
                "/create_relationship",
                {
                    "from_entity_type": from_entity_type,
                    "from_node_id": from_node_id,
                    "to_entity_type": to_entity_type,
                    "to_node_id": to_node_id,
                    "relationship_type": relationship_type,
                    "properties": properties or {},
                },
            )

            execution_time = (time.time() - start_time) * 1000

            return OperationResult(
                success=response.get("success", False),
                operation="create_relationship",
                entity_type=None,
                message=response.get("message", ""),
                data=response.get("data"),
                error=response.get("error"),
                execution_time_ms=execution_time,
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return OperationResult(
                success=False,
                operation="create_relationship",
                entity_type=None,
                message=f"Failed to create relationship: {str(e)}",
                error=str(e),
                execution_time_ms=execution_time,
            )

    async def update_relationship(
        self,
        from_entity_type: str,
        from_node_id: str,
        to_entity_type: str,
        to_node_id: str,
        relationship_type: str,
        properties: Dict[str, Any],
    ) -> OperationResult:
        """Update a relationship.

        Args:
            from_entity_type: Source entity type
            from_node_id: Source node ID
            to_entity_type: Target entity type
            to_node_id: Target node ID
            relationship_type: Relationship type
            properties: Properties to update

        Returns:
            OperationResult with success status
        """
        import time

        start_time = time.time()

        try:
            response = await self._make_request(
                "/update_relationship",
                {
                    "from_entity_type": from_entity_type,
                    "from_node_id": from_node_id,
                    "to_entity_type": to_entity_type,
                    "to_node_id": to_node_id,
                    "relationship_type": relationship_type,
                    "properties": properties,
                },
            )

            execution_time = (time.time() - start_time) * 1000

            return OperationResult(
                success=response.get("success", False),
                operation="update_relationship",
                entity_type=None,
                message=response.get("message", ""),
                data=response.get("data"),
                error=response.get("error"),
                execution_time_ms=execution_time,
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return OperationResult(
                success=False,
                operation="update_relationship",
                entity_type=None,
                message=f"Failed to update relationship: {str(e)}",
                error=str(e),
                execution_time_ms=execution_time,
            )

    async def query_nodes(
        self,
        entity_type: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        skip: int = 0,
    ) -> OperationResult:
        """Query nodes with filters.

        Args:
            entity_type: Entity type to query
            filters: Property filters
            limit: Maximum results
            skip: Skip count

        Returns:
            OperationResult with nodes data
        """
        import time

        start_time = time.time()

        try:
            response = await self._make_request(
                "/query_nodes",
                {
                    "entity_type": entity_type,
                    "filters": filters or {},
                    "limit": limit,
                    "skip": skip,
                },
            )

            execution_time = (time.time() - start_time) * 1000

            return OperationResult(
                success=response.get("success", False),
                operation="query_nodes",
                entity_type=entity_type,
                message=f"Found {response.get('returned_count', 0)} nodes",
                data=response,
                error=response.get("error"),
                execution_time_ms=execution_time,
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return OperationResult(
                success=False,
                operation="query_nodes",
                entity_type=entity_type,
                message=f"Failed to query nodes: {str(e)}",
                error=str(e),
                execution_time_ms=execution_time,
            )
