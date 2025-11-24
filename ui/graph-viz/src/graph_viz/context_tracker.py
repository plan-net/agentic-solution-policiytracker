"""Chat context tracking for graph visualization."""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from neo4j import AsyncDriver

from src.graph_viz.models import GraphEdge, GraphNode

logger = logging.getLogger(__name__)


class ChatContextTracker:
    """Tracks and extracts graph context from chat tool executions."""

    def __init__(self, driver: AsyncDriver, ttl_minutes: int = 5):
        """
        Initialize context tracker.

        Args:
            driver: Neo4j async driver
            ttl_minutes: Time-to-live for cached contexts in minutes
        """
        self.driver = driver
        self.ttl = timedelta(minutes=ttl_minutes)
        self.context_cache: dict[str, dict[str, Any]] = {}

    async def track_tool_execution(
        self, session_id: str, tool_name: str, tool_result: Any
    ):
        """
        Track a tool execution and extract relevant entity UUIDs.

        Args:
            session_id: Chat session ID
            tool_name: Name of the tool executed
            tool_result: Result from tool execution
        """
        if session_id not in self.context_cache:
            self.context_cache[session_id] = {
                "created_at": datetime.now(),
                "entity_uuids": set(),
                "relationship_data": [],
                "tools_used": [],
                "query_text": None,
            }

        context = self.context_cache[session_id]

        # Update metadata
        context["tools_used"].append(tool_name)

        # Extract entity UUIDs from tool result (recursive extraction)
        uuids = self._extract_uuids_from_result(tool_result)
        context["entity_uuids"].update(uuids)

        logger.info(
            f"Session {session_id}: Tracked {tool_name}, found {len(uuids)} entities"
        )

    async def get_context_graph(
        self, session_id: str, query_text: Optional[str] = None
    ) -> tuple[list[GraphNode], list[GraphEdge], dict[str, Any]]:
        """
        Build graph visualization from tracked context.

        Args:
            session_id: Chat session ID
            query_text: Optional query text to store

        Returns:
            (nodes, edges, metadata)
        """
        # Check if context exists and is valid
        if session_id not in self.context_cache:
            return [], [], {"error": "Session not found"}

        context = self.context_cache[session_id]

        # Check TTL
        if datetime.now() - context["created_at"] > self.ttl:
            del self.context_cache[session_id]
            return [], [], {"error": "Session expired (TTL exceeded)"}

        # Update query text if provided
        if query_text:
            context["query_text"] = query_text

        # Fetch entities and relationships from Neo4j
        entity_uuids = list(context["entity_uuids"])

        if not entity_uuids:
            return [], [], {
                "tools_used": context["tools_used"],
                "entity_count": 0,
                "relationship_count": 0,
            }

        nodes, edges = await self._fetch_subgraph(entity_uuids)

        metadata = {
            "tools_used": context["tools_used"],
            "entity_count": len(nodes),
            "relationship_count": len(edges),
            "query_text": context.get("query_text"),
            "created_at": context["created_at"].isoformat(),
        }

        return nodes, edges, metadata

    def _extract_uuids_from_result(self, result: Any, uuids: Optional[set] = None) -> set[str]:
        """
        Recursively extract entity UUIDs from tool result.

        Looks for:
        - 'uuid', 'id', 'entity_id' keys
        - Lists of dictionaries
        - Nested structures
        """
        if uuids is None:
            uuids = set()

        if isinstance(result, dict):
            # Check for UUID fields
            for key in ["uuid", "id", "entity_id", "element_id"]:
                if key in result and isinstance(result[key], str):
                    uuids.add(result[key])

            # Recurse into nested dicts
            for value in result.values():
                self._extract_uuids_from_result(value, uuids)

        elif isinstance(result, list):
            # Recurse into lists
            for item in result:
                self._extract_uuids_from_result(item, uuids)

        return uuids

    async def _fetch_subgraph(
        self, entity_uuids: list[str]
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        """
        Fetch subgraph from Neo4j for given entity UUIDs.

        Args:
            entity_uuids: List of entity UUIDs

        Returns:
            (nodes, edges)
        """
        nodes = []
        edges = []
        node_map = {}

        try:
            # Query Neo4j for entities and their relationships
            cypher = """
                MATCH (n:Entity)
                WHERE n.uuid IN $uuids
                OPTIONAL MATCH (n)-[r]-(m:Entity)
                WHERE m.uuid IN $uuids
                RETURN n, r, m
            """

            async with self.driver.session() as session:
                result = await session.run(cypher, uuids=entity_uuids)
                records = await result.data()

                for record in records:
                    # Process source node
                    if record["n"]:
                        node_data = record["n"]
                        node_id = node_data.get("uuid", node_data.element_id)

                        if node_id not in node_map:
                            node = GraphNode(
                                id=node_id,
                                name=node_data.get("name", node_id[:8]),
                                type=list(node_data.labels)[0]
                                if node_data.labels
                                else "Entity",
                                properties=dict(node_data.items()),
                                val=1,
                            )
                            nodes.append(node)
                            node_map[node_id] = node

                    # Process target node
                    if record["m"]:
                        node_data = record["m"]
                        node_id = node_data.get("uuid", node_data.element_id)

                        if node_id not in node_map:
                            node = GraphNode(
                                id=node_id,
                                name=node_data.get("name", node_id[:8]),
                                type=list(node_data.labels)[0]
                                if node_data.labels
                                else "Entity",
                                properties=dict(node_data.items()),
                                val=1,
                            )
                            nodes.append(node)
                            node_map[node_id] = node

                    # Process relationship
                    if record["r"]:
                        rel_data = record["r"]
                        source_id = record["n"].get("uuid", record["n"].element_id)
                        target_id = record["m"].get("uuid", record["m"].element_id)

                        edge = GraphEdge(
                            source=source_id,
                            target=target_id,
                            type=rel_data.type,
                            value=1.0,
                            properties=dict(rel_data.items()),
                        )
                        edges.append(edge)

        except Exception as e:
            logger.error(f"Failed to fetch subgraph: {e}")
            raise

        return nodes, edges

    def clear_expired_contexts(self):
        """Remove expired contexts from cache."""
        now = datetime.now()
        expired_sessions = [
            session_id
            for session_id, context in self.context_cache.items()
            if now - context["created_at"] > self.ttl
        ]

        for session_id in expired_sessions:
            del self.context_cache[session_id]
            logger.info(f"Cleared expired context for session {session_id}")
