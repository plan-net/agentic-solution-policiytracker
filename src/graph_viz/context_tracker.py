"""Chat context tracking for graph visualization."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from neo4j import AsyncDriver

from src.config import settings
from .models import GraphEdge, GraphNode

logger = logging.getLogger(__name__)


class ChatContextTracker:
    """Track and extract graph context from chat tool executions."""

    def __init__(self, driver: AsyncDriver, ttl_minutes: int = 5):
        """
        Initialize the context tracker.

        Args:
            driver: Neo4j async driver
            ttl_minutes: Time-to-live for cached context data in minutes
        """
        self.driver = driver
        self.ttl = timedelta(minutes=ttl_minutes)
        self.context_cache: dict[str, dict[str, Any]] = {}

    async def track_tool_execution(self, session_id: str, tool_name: str, tool_result: Any) -> None:
        """
        Track a tool execution and extract relevant graph entities/relationships.

        Args:
            session_id: Chat session ID
            tool_name: Name of the tool that was executed
            tool_result: Result data from the tool
        """
        if session_id not in self.context_cache:
            self.context_cache[session_id] = {
                "created_at": datetime.now(UTC),
                "entity_uuids": set(),
                "relationship_data": [],
                "tools_used": [],
                "query_text": None,
            }

        context = self.context_cache[session_id]

        # Track tool usage
        context["tools_used"].append(
            {"tool_name": tool_name, "timestamp": datetime.now().isoformat()}
        )

        # Extract entity UUIDs and relationship data from tool result
        if isinstance(tool_result, dict):
            self._extract_entities_from_dict(tool_result, context)
        elif isinstance(tool_result, list):
            for item in tool_result:
                if isinstance(item, dict):
                    self._extract_entities_from_dict(item, context)

        # Persist context to Neo4j for cross-service access
        logger.warning(f"About to persist context for session {session_id} to Neo4j")
        await self._persist_context_to_neo4j(session_id, context)
        logger.warning(f"Finished persisting context for session {session_id}")

    def _extract_entities_from_dict(self, data: dict, context: dict) -> None:
        """Recursively extract entity UUIDs from nested dictionary."""
        for key, value in data.items():
            # Look for UUID fields (single UUID)
            if key in ["uuid", "entity_uuid", "source_uuid", "target_uuid", "node_uuid"]:
                if isinstance(value, str):
                    context["entity_uuids"].add(value)

            # Look for UUID array fields (from parsed tool results)
            elif key == "entity_uuids" and isinstance(value, list):
                for uuid_val in value:
                    if isinstance(uuid_val, str):
                        context["entity_uuids"].add(uuid_val)

            # Look for entity objects
            elif key == "entity" and isinstance(value, dict):
                if "uuid" in value:
                    context["entity_uuids"].add(value["uuid"])

            # Look for relationship arrays
            elif key in ["relationships", "edges", "links"]:
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            self._extract_relationship_data(item, context)
                elif isinstance(value, dict):
                    # Handle {"outgoing": [...], "incoming": [...]} structure
                    for subkey, subvalue in value.items():
                        if isinstance(subvalue, list):
                            for item in subvalue:
                                if isinstance(item, dict):
                                    self._extract_relationship_data(item, context)

            # Recurse into nested dicts
            elif isinstance(value, dict):
                self._extract_entities_from_dict(value, context)

            # Recurse into lists
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        self._extract_entities_from_dict(item, context)

    def _extract_relationship_data(self, rel_data: dict, context: dict) -> None:
        """Extract relationship data for graph visualization."""
        # Extract source and target UUIDs
        if "source_uuid" in rel_data:
            context["entity_uuids"].add(rel_data["source_uuid"])
        if "target_uuid" in rel_data:
            context["entity_uuids"].add(rel_data["target_uuid"])

        # Store relationship for later graph construction
        if "source_uuid" in rel_data and "target_uuid" in rel_data:
            context["relationship_data"].append(
                {
                    "source": rel_data["source_uuid"],
                    "target": rel_data["target_uuid"],
                    "type": rel_data.get("relationship_type", "RELATED_TO"),
                    "properties": {
                        k: v
                        for k, v in rel_data.items()
                        if k not in ["source_uuid", "target_uuid", "relationship_type"]
                    },
                }
            )

    async def _persist_context_to_neo4j(self, session_id: str, context: dict) -> None:
        """Persist chat context to Neo4j for cross-service access."""
        try:
            import json

            async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                # Convert set to list for JSON serialization
                entity_uuids_list = list(context["entity_uuids"])
                # Convert tools_used to JSON string (Neo4j can't store nested maps)
                tools_used_json = json.dumps(context["tools_used"])
                # Convert messages to JSON string
                messages_json = json.dumps(context.get("messages", []))

                await session.run(
                    """
                    MERGE (s:ChatSession {session_id: $session_id})
                    SET s.created_at = datetime($created_at),
                        s.entity_uuids = $entity_uuids,
                        s.tools_used_json = $tools_used_json,
                        s.messages_json = $messages_json,
                        s.query_text = $query_text,
                        s.last_updated = datetime()
                    """,
                    session_id=session_id,
                    created_at=context["created_at"].isoformat(),
                    entity_uuids=entity_uuids_list,
                    tools_used_json=tools_used_json,
                    messages_json=messages_json,
                    query_text=context.get("query_text"),
                )
                logger.warning(
                    f"✅ SUCCESS: Persisted context for session {session_id} to Neo4j with {len(entity_uuids_list)} entities"
                )
        except Exception as e:
            logger.error(f"❌ FAILED to persist context to Neo4j: {e}", exc_info=True)

    async def store_message(self, session_id: str, role: str, content: str) -> None:
        """Store a chat message for a session.

        Args:
            session_id: Chat session ID
            role: Message role ('user' or 'assistant')
            content: Message content
        """
        # Ensure context exists
        if session_id not in self.context_cache:
            self.context_cache[session_id] = {
                "created_at": datetime.now(UTC),
                "entity_uuids": set(),
                "relationship_data": [],
                "tools_used": [],
                "query_text": None,
                "messages": [],
            }

        # Add messages list if not present
        if "messages" not in self.context_cache[session_id]:
            self.context_cache[session_id]["messages"] = []

        # Add message
        self.context_cache[session_id]["messages"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(UTC).isoformat(),
        })

        # Persist to Neo4j
        await self._persist_context_to_neo4j(session_id, self.context_cache[session_id])

    async def _load_context_from_neo4j(self, session_id: str) -> Optional[dict]:
        """Load chat context from Neo4j.

        Note: TTL is not enforced when loading from Neo4j to allow viewing
        historical session context. TTL only applies to in-memory cache.
        """
        try:
            import json

            async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                result = await session.run(
                    """
                    MATCH (s:ChatSession {session_id: $session_id})
                    RETURN s.created_at as created_at,
                           s.entity_uuids as entity_uuids,
                           s.tools_used_json as tools_used_json,
                           s.messages_json as messages_json,
                           s.query_text as query_text
                    """,
                    session_id=session_id,
                )

                record = await result.single()
                if record:
                    # Parse tools_used from JSON
                    tools_used = []
                    if record["tools_used_json"]:
                        try:
                            tools_used = json.loads(record["tools_used_json"])
                        except json.JSONDecodeError:
                            logger.warning(
                                f"Failed to parse tools_used_json for session {session_id}"
                            )

                    # Parse messages from JSON
                    messages = []
                    if record["messages_json"]:
                        try:
                            messages = json.loads(record["messages_json"])
                        except json.JSONDecodeError:
                            logger.warning(
                                f"Failed to parse messages_json for session {session_id}"
                            )

                    # Convert Neo4j datetime to Python datetime
                    created_at = record["created_at"]
                    if hasattr(created_at, "to_native"):
                        created_at = created_at.to_native()  # Neo4j datetime object
                    elif isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at)

                    # Ensure timezone-aware datetime in UTC for Pydantic serialization
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=UTC)

                    return {
                        "created_at": created_at,
                        "entity_uuids": set(record["entity_uuids"])
                        if record["entity_uuids"]
                        else set(),
                        "relationship_data": [],  # Not persisted separately
                        "tools_used": tools_used,
                        "messages": messages,
                        "query_text": record["query_text"],
                    }
                return None
        except Exception as e:
            logger.error(f"Failed to load context from Neo4j: {e}", exc_info=True)
            return None

    async def get_context_graph(
        self, session_id: str, query_text: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Get the graph context for a chat session.

        Args:
            session_id: Chat session ID
            query_text: Optional original query text

        Returns:
            Dict with nodes, links, and metadata
        """
        # Check if session exists in cache, otherwise load from Neo4j
        if session_id not in self.context_cache:
            # Try loading from Neo4j
            logger.warning(f"Context not in cache for {session_id}, loading from Neo4j")
            context = await self._load_context_from_neo4j(session_id)
            logger.warning(
                f"Loaded context from Neo4j: {context is not None}, entities: {len(context.get('entity_uuids', [])) if context else 0}"
            )
            if context:
                # Mark as loaded from Neo4j so TTL check is skipped for historical sessions
                context["_loaded_from_neo4j"] = True
                self.context_cache[session_id] = context
            else:
                return {
                    "nodes": [],
                    "links": [],
                    "metadata": {
                        "session_id": session_id,
                        "error": "No context found for this session",
                    },
                }

        context = self.context_cache[session_id]

        # Check if context is expired (only for in-memory cache, not for persisted sessions)
        # Historical sessions loaded from Neo4j should always be viewable
        is_historical = context.get("_loaded_from_neo4j", False)
        if not is_historical and datetime.now(UTC) - context["created_at"] > self.ttl:
            del self.context_cache[session_id]
            return {
                "nodes": [],
                "links": [],
                "metadata": {
                    "session_id": session_id,
                    "error": "Context expired (TTL exceeded)",
                },
            }

        # Update query text if provided
        if query_text:
            context["query_text"] = query_text

        # Build graph from tracked entities
        try:
            logger.warning(
                f"🏗️  Building graph for session {session_id} with {len(context.get('entity_uuids', []))} entity UUIDs"
            )
            nodes, links = await self._build_graph_from_context(context)
            logger.warning(f"✅ Graph built: {len(nodes)} nodes, {len(links)} links")
        except Exception as e:
            logger.error(f"❌ Error building graph from context: {e}", exc_info=True)
            return {
                "nodes": [],
                "links": [],
                "metadata": {
                    "session_id": session_id,
                    "error": f"Failed to build graph: {str(e)}",
                    "entity_uuids_count": len(context.get("entity_uuids", [])),
                },
            }

        return {
            "nodes": nodes,
            "links": links,
            "metadata": {
                "session_id": session_id,
                "query_text": context.get("query_text"),
                "tools_used": context["tools_used"],
                "entity_count": len(nodes),
                "relationship_count": len(links),
                "created_at": context["created_at"].isoformat(),
            },
        }

    async def _build_graph_from_context(
        self, context: dict
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        """Build graph nodes and edges from tracked context."""
        entity_uuids = list(context["entity_uuids"])

        if not entity_uuids:
            return [], []

        # Fetch entity details from Neo4j
        nodes = await self._fetch_entities(entity_uuids)

        # Build edges from tracked relationships (from tool results)
        links = []
        for rel_data in context["relationship_data"]:
            links.append(
                GraphEdge(
                    source=rel_data["source"],
                    target=rel_data["target"],
                    type=rel_data["type"],
                    properties=rel_data["properties"],
                )
            )

        # Also fetch relationships between entities from Neo4j
        neo4j_relationships = await self._fetch_relationships(entity_uuids)
        links.extend(neo4j_relationships)

        logger.warning(
            f"📊 Built graph: {len(nodes)} nodes, {len(links)} links ({len(neo4j_relationships)} from Neo4j)"
        )

        return nodes, links

    async def _fetch_entities(self, entity_uuids: list[str]) -> list[GraphNode]:
        """Fetch entity details from Neo4j by UUIDs."""
        nodes = []

        try:
            logger.warning(f"🔍 Fetching entities for {len(entity_uuids)} UUIDs")
            async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                # Batch fetch entities - try multiple labels since we don't know the exact label
                query = """
                    MATCH (e)
                    WHERE e.uuid IN $uuids
                    RETURN e.uuid AS uuid, e.name AS name, labels(e) AS labels, properties(e) AS props
                """
                result = await session.run(query, {"uuids": entity_uuids})
                records = await result.data()

                logger.warning(
                    f"📊 Query returned {len(records)} records for {len(entity_uuids)} UUIDs"
                )

                if len(records) == 0:
                    logger.error(
                        "❌ NO ENTITIES FOUND - UUIDs stored in ChatSession have no matching Entity nodes in Neo4j!"
                    )
                    logger.error(f"Sample UUIDs: {entity_uuids[:3]}")
                    # Let's check if ANY nodes with these UUIDs exist
                    check_query = "MATCH (n) WHERE n.uuid IN $uuids RETURN count(n) as count"
                    check_result = await session.run(check_query, {"uuids": entity_uuids[:5]})
                    check_data = await check_result.data()
                    logger.error(
                        f"Check query found {check_data[0]['count'] if check_data else 0} nodes with ANY label"
                    )

                for record in records:
                    try:
                        # Sanitize properties to convert Neo4j DateTime objects to strings
                        props = record.get("props", {})
                        logger.warning(
                            f"🔍 Raw props before sanitization: {type(props)} - {list(props.keys()) if isinstance(props, dict) else 'NOT A DICT'}"
                        )

                        # Log types of property values
                        if isinstance(props, dict):
                            for k, v in props.items():
                                logger.warning(
                                    f"  Property '{k}': type={type(v).__name__}, value={v!r}"
                                )

                        sanitized_props = self._sanitize_neo4j_properties(props)
                        logger.warning(
                            f"✅ Sanitized props: {list(sanitized_props.keys()) if isinstance(sanitized_props, dict) else 'NOT A DICT'}"
                        )

                        node = GraphNode(
                            id=record["uuid"],
                            name=record.get("name", f"Entity-{record['uuid'][:8]}"),
                            type=self._get_primary_label(record["labels"] or []),
                            properties=sanitized_props,
                        )
                        nodes.append(node)
                        logger.warning(f"✅ Found entity: {node.name} ({node.type})")
                    except Exception as node_error:
                        logger.error(
                            f"❌ Error creating GraphNode from record: {node_error}, record: {record}"
                        )

        except Exception as e:
            logger.error(f"❌ Error fetching entities from Neo4j: {e}", exc_info=True)

        logger.warning(f"📈 Returning {len(nodes)} nodes from _fetch_entities")
        return nodes

    async def _fetch_relationships(self, entity_uuids: list[str]) -> list[GraphEdge]:
        """Fetch relationships between tracked entities from Neo4j."""
        relationships = []

        if not entity_uuids:
            return relationships

        try:
            logger.warning(f"🔗 Fetching relationships between {len(entity_uuids)} entities")
            async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                # Query relationships where both source and target are in our entity list
                query = """
                    MATCH (e1)-[r]->(e2)
                    WHERE e1.uuid IN $uuids AND e2.uuid IN $uuids
                    RETURN e1.uuid AS source_uuid,
                           e2.uuid AS target_uuid,
                           type(r) AS rel_type,
                           properties(r) AS rel_props
                    LIMIT 100
                """
                result = await session.run(query, {"uuids": entity_uuids})
                records = await result.data()

                logger.warning(f"📊 Query returned {len(records)} relationships")

                for record in records:
                    try:
                        # Sanitize relationship properties
                        props = record.get("rel_props", {})
                        sanitized_props = (
                            self._sanitize_neo4j_properties(props)
                            if isinstance(props, dict)
                            else {}
                        )

                        edge = GraphEdge(
                            source=record["source_uuid"],
                            target=record["target_uuid"],
                            type=record["rel_type"],
                            properties=sanitized_props,
                        )
                        relationships.append(edge)
                    except Exception as edge_error:
                        logger.error(f"❌ Error creating GraphEdge: {edge_error}, record: {record}")

        except Exception as e:
            logger.error(f"❌ Error fetching relationships from Neo4j: {e}", exc_info=True)

        logger.warning(f"📈 Returning {len(relationships)} relationships")
        return relationships

    def _get_primary_label(self, labels: list[str]) -> str:
        """Select the most specific label, ignoring generic 'Entity' when possible.

        Args:
            labels: List of Neo4j node labels

        Returns:
            The most specific/meaningful label for display and coloring
        """
        if not labels:
            return "Unknown"

        # Priority order: specific types first (from Neo4j .grass style file)
        priority_labels = [
            # Core types
            "Policy", "Regulation", "Document", "Person", "Company",
            # Government & Political
            "GovernmentAgency", "LegislativeBody", "LegislativeProposal",
            "Politician", "PoliticalParty", "Committee", "Vote", "Jurisdiction",
            # Legal & Compliance
            "LegalFramework", "ComplianceObligation", "EnforcementAction",
            "TechnicalStandard", "ConsultationProcess",
            # Business & Industry
            "Industry", "Market", "LobbyGroup", "BusinessActivity", "Exception",
            # German Parliament (Bundestag)
            "Drucksache", "Sachgebiet", "Deskriptor", "Vorgang", "BundestagPerson",
            "Fraktion", "BundestagFraktion", "Wahlperiode", "Plenarprotokoll",
            "Vorgangsposition", "Aktivitaet", "DrucksachePage",
            # Other types
            "ChatSession", "Community", "EntityAlias", "CanonicalEntity", "Episodic",
        ]

        # Check for priority labels first
        for priority_label in priority_labels:
            if priority_label in labels:
                return priority_label

        # Filter out generic labels
        specific_labels = [label for label in labels if label not in ("Entity", "Node")]

        # Return first specific label, or first label if all are generic
        return specific_labels[0] if specific_labels else labels[0]

    def _sanitize_neo4j_properties(self, props: dict) -> dict:
        """Convert Neo4j native types (DateTime, Duration, Point, etc.) to JSON-serializable Python types."""
        sanitized = {}

        for key, value in props.items():
            # Skip internal Neo4j properties
            if key in ["uuid", "labels", "name_embedding"]:
                sanitized[key] = value
                continue

            # Handle Neo4j DateTime objects
            if hasattr(value, "isoformat"):
                # Neo4j DateTime or Python datetime - convert to ISO string
                sanitized[key] = value.isoformat()

            # Handle nested dictionaries
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_neo4j_properties(value)

            # Handle lists
            elif isinstance(value, list):
                sanitized[key] = [
                    item.isoformat()
                    if hasattr(item, "isoformat")
                    else self._sanitize_neo4j_properties(item)
                    if isinstance(item, dict)
                    else item
                    for item in value
                ]

            # Handle other types as-is
            else:
                sanitized[key] = value

        return sanitized

    def clear_expired_contexts(self) -> int:
        """Clear expired contexts from cache. Returns number of contexts cleared."""
        now = datetime.now(UTC)
        expired_sessions = [
            session_id
            for session_id, context in self.context_cache.items()
            if now - context["created_at"] > self.ttl
        ]

        for session_id in expired_sessions:
            del self.context_cache[session_id]

        return len(expired_sessions)

    def clear_session_context(self, session_id: str) -> bool:
        """Clear context for a specific session. Returns True if session was found."""
        if session_id in self.context_cache:
            del self.context_cache[session_id]
            return True
        return False
