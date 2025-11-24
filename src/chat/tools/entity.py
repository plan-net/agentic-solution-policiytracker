"""Entity-focused tools for exploring the knowledge graph."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Union

from graphiti_core import Graphiti
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EntityDetailsInput(BaseModel):
    """Input schema for entity details tool."""

    entity_name: str = Field(description="Name of the entity to get details for")
    entity_type: Optional[str] = Field(
        default=None, description="Type of entity (Policy, Company, Politician, etc.)"
    )
    output_format: str = Field(
        default="structured",
        description="Output format: 'structured' (JSON with graph data) or 'text' (markdown)",
    )


class EntityRelationshipsInput(BaseModel):
    """Input schema for entity relationships tool."""

    entity_name: str = Field(description="Name of the entity to find relationships for")
    max_relationships: int = Field(
        default=10, description="Maximum number of relationships to return"
    )
    relationship_types: Optional[list[str]] = Field(
        default=None, description="Specific relationship types to filter for"
    )
    output_format: str = Field(
        default="structured",
        description="Output format: 'structured' (JSON with detailed data) or 'text' (markdown)",
    )
    include_bidirectional: bool = Field(
        default=True,
        description="Include both outgoing (from entity) and incoming (to entity) relationships",
    )


class EntityTimelineInput(BaseModel):
    """Input schema for entity timeline tool."""

    entity_name: str = Field(description="Name of the entity to get timeline for")
    days_back: int = Field(
        default=365, description="Number of days back to search for timeline events"
    )


class SimilarEntitiesInput(BaseModel):
    """Input schema for similar entities tool."""

    entity_name: str = Field(description="Name of the entity to find similar entities for")
    max_similar: int = Field(default=5, description="Maximum number of similar entities to return")


class EntityDetailsTool(BaseTool):
    """Tool for getting detailed information about a specific entity."""

    name: str = "get_entity_details"
    description: str = "Get comprehensive details about a specific entity (policy, company, politician, etc.) including its properties and basic context."
    args_schema: type[BaseModel] = EntityDetailsInput

    client: Graphiti = None

    def __init__(self, graphiti_client: Graphiti, **kwargs):
        super().__init__(**kwargs)
        self.client = graphiti_client

    class Config:
        arbitrary_types_allowed = True

    def _sanitize_for_serialization(self, obj):
        """Convert Neo4j types to JSON-serializable types.

        Handles DateTime, Date, Time, Duration, and other Neo4j types.
        """
        from datetime import date, datetime, time

        if obj is None:
            return None
        elif isinstance(obj, (str, int, float, bool)):
            return obj
        elif isinstance(obj, (datetime, date, time)):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: self._sanitize_for_serialization(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._sanitize_for_serialization(item) for item in obj]
        else:
            # For any other type (Neo4j DateTime, etc.), convert to string
            return str(obj)

    async def _find_entity_node(
        self, entity_name: str, entity_type: Optional[str] = None
    ) -> Optional[dict]:
        """Find entity node in Neo4j using smart matching.

        Uses Neo4j Cypher query to find entity nodes with exact or fuzzy name matching.
        Returns best match based on shortest name length (avoids false positives).

        Args:
            entity_name: Name to search for
            entity_type: Optional entity type to filter by

        Returns:
            Dict with uuid, name, labels, and properties if found, else None
        """
        try:
            # Build query with smart matching
            query = """
                MATCH (n:Entity)
                WHERE toLower(n.name) CONTAINS toLower($entity_name)
            """

            if entity_type:
                query += " AND $entity_type IN labels(n)"

            query += """
                RETURN n.uuid AS uuid, n.name AS name, labels(n) AS labels,
                       properties(n) AS properties
                ORDER BY size(n.name) ASC
                LIMIT 5
            """

            # Execute query
            async with self.client.driver.session() as session:
                result = await session.run(
                    query, {"entity_name": entity_name, "entity_type": entity_type}
                )
                records = await result.data()

                if records:
                    # Return best match (shortest name containing query)
                    best_match = records[0]
                    logger.info(
                        f"Found entity node: {best_match['name']} (UUID: {best_match['uuid']})"
                    )
                    return best_match

                logger.warning(f"No entity node found for: {entity_name}")
                return None

        except Exception as e:
            logger.error(f"Error finding entity node: {e}")
            return None

    async def _get_entity_properties(self, entity_uuid: str) -> dict:
        """Get entity properties directly from Neo4j.

        Args:
            entity_uuid: UUID of the entity node

        Returns:
            Dict with entity properties
        """
        try:
            query = """
                MATCH (n:Entity {uuid: $entity_uuid})
                RETURN n.name AS name, labels(n) AS labels, properties(n) AS properties
            """

            async with self.client.driver.session() as session:
                result = await session.run(query, {"entity_uuid": entity_uuid})
                records = await result.data()

                if records:
                    return records[0]

                return {}

        except Exception as e:
            logger.error(f"Error getting entity properties: {e}")
            return {}

    async def _get_entity_relationships_summary(
        self, entity_uuid: str, max_relationships: int = 10
    ) -> list[dict]:
        """Get summary of entity's relationships from Neo4j.

        Args:
            entity_uuid: UUID of the entity node
            max_relationships: Maximum number of relationships to return

        Returns:
            List of relationship dicts with source, target, and type
        """
        try:
            query = """
                MATCH (source:Entity {uuid: $entity_uuid})-[r]->(target:Entity)
                RETURN source.name AS source_name,
                       type(r) AS relationship_type,
                       target.name AS target_name,
                       target.uuid AS target_uuid,
                       r.fact AS fact
                LIMIT $max_relationships
            """

            async with self.client.driver.session() as session:
                result = await session.run(
                    query,
                    {"entity_uuid": entity_uuid, "max_relationships": max_relationships},
                )
                records = await result.data()

                relationships = []
                for record in records:
                    relationships.append(
                        {
                            "source": record["source_name"],
                            "target": record["target_name"],
                            "relationship_type": record["relationship_type"],
                            "fact": record.get("fact", ""),
                        }
                    )

                return relationships

        except Exception as e:
            logger.error(f"Error getting entity relationships: {e}")
            return []

    async def _extract_entity_sources(self, entity_uuid: str) -> list[dict]:
        """Extract source documents for entity from Episodic nodes.

        Args:
            entity_uuid: UUID of the entity node

        Returns:
            List of source dicts with title and url
        """
        try:
            query = """
                MATCH (entity:Entity {uuid: $entity_uuid})<-[:MENTIONS]-(ep:Episodic)
                RETURN DISTINCT ep.name AS episodic_name,
                       ep.source AS source_description
                LIMIT 20
            """

            async with self.client.driver.session() as session:
                result = await session.run(query, {"entity_uuid": entity_uuid})
                records = await result.data()

                sources = []
                for record in records:
                    episodic_name = record.get("episodic_name", "")
                    source_desc = record.get("source_description", "")

                    # Extract URL and title from episodic name (format: YYYYMMDD_source_title_hash.md)
                    if episodic_name:
                        parts = episodic_name.split("_")
                        if len(parts) >= 3:
                            date_str = parts[0] if parts[0].isdigit() else ""
                            source_name = parts[1] if len(parts) > 1 else "unknown"
                            title = " ".join(parts[2:-1]) if len(parts) > 2 else episodic_name

                            # Try to extract URL from source_description
                            url = ""
                            if source_desc and "http" in source_desc:
                                url = source_desc.split("http")[1].split()[0]
                                url = "http" + url

                            sources.append(
                                {
                                    "title": f"{source_name}: {title}" if title else source_name,
                                    "url": url if url else "",
                                    "date": date_str,
                                }
                            )

                return sources

        except Exception as e:
            logger.error(f"Error extracting entity sources: {e}")
            return []

    def _run(
        self,
        entity_name: str,
        entity_type: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute synchronously - placeholder."""
        return "Sync not implemented - use async version"

    async def _arun(
        self,
        entity_name: str,
        entity_type: Optional[str] = None,
        output_format: str = "structured",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Union[str, dict]:
        """Get detailed information about an entity using smart entity resolution."""
        try:
            logger.info(f"Getting details for entity: {entity_name}")

            # Step 1: Smart entity resolution using Neo4j
            entity_node = await self._find_entity_node(entity_name, entity_type)

            if not entity_node:
                error_msg = f"No entity found for '{entity_name}'"
                if output_format == "text":
                    return f"## Entity Not Found\n\n{error_msg}"
                else:
                    return self._sanitize_for_serialization(
                        {
                            "entity_name": entity_name,
                            "found": False,
                            "error": error_msg,
                        }
                    )

            entity_uuid = entity_node["uuid"]
            resolved_name = entity_node["name"]
            entity_labels = entity_node.get("labels", [])

            logger.info(
                f"Resolved '{entity_name}' to entity '{resolved_name}' (UUID: {entity_uuid})"
            )

            # Step 2: Get entity properties directly from Neo4j
            properties = await self._get_entity_properties(entity_uuid)

            # Step 3: Get relationships summary
            relationships = await self._get_entity_relationships_summary(
                entity_uuid, max_relationships=10
            )

            # Step 4: Extract source documents
            sources = await self._extract_entity_sources(entity_uuid)

            # Step 5: Get additional facts via Graphiti search (for context)
            search_query = f"{resolved_name} details context"
            from graphiti_core.search.search_config_recipes import EDGE_HYBRID_SEARCH_RRF

            search_results = await self.client._search(search_query, config=EDGE_HYBRID_SEARCH_RRF)

            entity_facts = []
            if hasattr(search_results, "edges") and search_results.edges:
                for edge in search_results.edges[:10]:
                    if hasattr(edge, "fact") and edge.fact:
                        # Use UUID matching instead of string matching
                        if (
                            hasattr(edge, "source_node_uuid")
                            and edge.source_node_uuid == entity_uuid
                        ):
                            entity_facts.append(edge.fact)
                        elif (
                            hasattr(edge, "target_node_uuid")
                            and edge.target_node_uuid == entity_uuid
                        ):
                            entity_facts.append(edge.fact)

            # Format response based on output_format
            if output_format == "structured":
                # Sanitize all data for JSON serialization (handles Neo4j DateTime, etc.)
                return self._sanitize_for_serialization(
                    {
                        "entity": {
                            "name": resolved_name,
                            "uuid": entity_uuid,
                            "type": entity_labels[0] if entity_labels else "Entity",
                            "labels": entity_labels,
                            "properties": properties.get("properties", {}),
                        },
                        "relationships": relationships,
                        "facts": entity_facts,
                        "sources": sources,
                        "total_relationships": len(relationships),
                        "total_facts": len(entity_facts),
                        "total_sources": len(sources),
                    }
                )
            else:
                # Text format (markdown)
                response = f"## Entity Details: {resolved_name}\n\n"
                response += f"**UUID**: {entity_uuid}\n"
                response += f"**Type**: {entity_labels[0] if entity_labels else 'Entity'}\n\n"

                if properties.get("properties"):
                    response += "**Properties:**\n"
                    for key, value in properties["properties"].items():
                        if key not in ["uuid", "name"]:
                            response += f"- {key}: {value}\n"
                    response += "\n"

                if relationships:
                    response += f"**Relationships**: {len(relationships)} connections\n"
                    for i, rel in enumerate(relationships[:5], 1):
                        response += f"{i}. {rel['source']} --[{rel['relationship_type']}]--> {rel['target']}\n"
                    if len(relationships) > 5:
                        response += f"... and {len(relationships) - 5} more relationships\n"
                    response += "\n"

                if entity_facts:
                    response += "**Key Facts:**\n"
                    for i, fact in enumerate(entity_facts[:8], 1):
                        response += f"{i}. {fact}\n"
                    if len(entity_facts) > 8:
                        response += f"... and {len(entity_facts) - 8} more facts\n"
                    response += "\n"

                if sources:
                    response += f"**Sources**: Found in {len(sources)} document(s)\n"
                    for i, source in enumerate(sources[:3], 1):
                        if source.get("url"):
                            response += f"{i}. [{source['title']}]({source['url']})\n"
                        else:
                            response += f"{i}. {source['title']}\n"
                    if len(sources) > 3:
                        response += f"... and {len(sources) - 3} more sources\n"

                logger.info(
                    f"Retrieved entity details: {len(relationships)} relationships, {len(entity_facts)} facts, {len(sources)} sources"
                )
                return response

        except Exception as e:
            logger.error(f"Error getting entity details: {e}")
            error_msg = f"Error retrieving details for {entity_name}: {str(e)}"
            if output_format == "text":
                return error_msg
            else:
                return self._sanitize_for_serialization(
                    {"entity_name": entity_name, "error": error_msg, "found": False}
                )


class EntityRelationshipsTool(BaseTool):
    """Tool for exploring relationships from a specific entity."""

    name: str = "get_entity_relationships"
    description: str = "Explore what other entities are connected to this entity and how they are related. Shows the network of relationships."
    args_schema: type[BaseModel] = EntityRelationshipsInput

    client: Graphiti = None

    def __init__(self, graphiti_client: Graphiti, **kwargs):
        super().__init__(**kwargs)
        self.client = graphiti_client

    class Config:
        arbitrary_types_allowed = True

    async def _get_entity_relationships_direct(
        self,
        entity_uuid: str,
        max_relationships: int = 10,
        relationship_types: Optional[list[str]] = None,
        include_bidirectional: bool = True,
    ) -> dict:
        """Get relationships directly from Neo4j using entity UUID.

        Args:
            entity_uuid: UUID of the entity
            max_relationships: Maximum relationships to return per direction
            relationship_types: Optional list of relationship types to filter
            include_bidirectional: Include both outgoing and incoming

        Returns:
            Dict with 'outgoing' and 'incoming' relationship lists
        """
        try:
            relationships = {"outgoing": [], "incoming": []}

            # Query outgoing relationships (from entity)
            outgoing_query = """
                MATCH (source:Entity {uuid: $entity_uuid})-[r]->(target:Entity)
                WHERE $relationship_types IS NULL OR type(r) IN $relationship_types
                RETURN source.name AS source_name,
                       source.uuid AS source_uuid,
                       type(r) AS relationship_type,
                       target.name AS target_name,
                       target.uuid AS target_uuid,
                       r.fact AS fact,
                       'outgoing' AS direction
                ORDER BY r.created_at DESC
                LIMIT $max_relationships
            """

            async with self.client.driver.session() as session:
                result = await session.run(
                    outgoing_query,
                    {
                        "entity_uuid": entity_uuid,
                        "max_relationships": max_relationships,
                        "relationship_types": relationship_types,
                    },
                )
                outgoing_records = await result.data()
                relationships["outgoing"] = outgoing_records

            # Query incoming relationships (to entity) if bidirectional
            if include_bidirectional:
                incoming_query = """
                    MATCH (source:Entity)-[r]->(target:Entity {uuid: $entity_uuid})
                    WHERE $relationship_types IS NULL OR type(r) IN $relationship_types
                    RETURN source.name AS source_name,
                           source.uuid AS source_uuid,
                           type(r) AS relationship_type,
                           target.name AS target_name,
                           target.uuid AS target_uuid,
                           r.fact AS fact,
                           'incoming' AS direction
                    ORDER BY r.created_at DESC
                    LIMIT $max_relationships
                """

                async with self.client.driver.session() as session:
                    result = await session.run(
                        incoming_query,
                        {
                            "entity_uuid": entity_uuid,
                            "max_relationships": max_relationships,
                            "relationship_types": relationship_types,
                        },
                    )
                    incoming_records = await result.data()
                    relationships["incoming"] = incoming_records

            return relationships

        except Exception as e:
            logger.error(f"Error getting direct relationships: {e}")
            return {"outgoing": [], "incoming": []}

    def _group_relationships_by_type(self, relationships: dict) -> dict:
        """Group relationships by type and count them.

        Args:
            relationships: Dict with 'outgoing' and 'incoming' lists

        Returns:
            Dict with relationship type counts
        """
        type_counts = {}

        for direction in ["outgoing", "incoming"]:
            for rel in relationships.get(direction, []):
                rel_type = rel.get("relationship_type", "UNKNOWN")
                type_counts[rel_type] = type_counts.get(rel_type, 0) + 1

        return type_counts

    def _run(
        self,
        entity_name: str,
        max_relationships: int = 10,
        relationship_types: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute synchronously - placeholder."""
        return "Sync not implemented - use async version"

    async def _arun(
        self,
        entity_name: str,
        max_relationships: int = 10,
        relationship_types: Optional[list[str]] = None,
        output_format: str = "structured",
        include_bidirectional: bool = True,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Union[str, dict]:
        """Get relationships for an entity using smart resolution and direct Neo4j queries."""
        try:
            logger.info(f"Finding relationships for entity: {entity_name}")

            # Step 1: Smart entity resolution - reuse from EntityDetailsTool
            # Find entity UUID first for accurate relationship queries
            entity_node = None
            async with self.client.driver.session() as session:
                query = """
                    MATCH (n:Entity)
                    WHERE toLower(n.name) CONTAINS toLower($entity_name)
                    RETURN n.uuid AS uuid, n.name AS name, labels(n) AS labels
                    ORDER BY size(n.name) ASC
                    LIMIT 1
                """
                result = await session.run(query, {"entity_name": entity_name})
                records = await result.data()
                if records:
                    entity_node = records[0]

            if not entity_node:
                error_msg = f"No entity found for '{entity_name}'"
                if output_format == "text":
                    return f"## Entity Not Found\n\n{error_msg}"
                else:
                    return {"entity_name": entity_name, "found": False, "error": error_msg}

            entity_uuid = entity_node["uuid"]
            resolved_name = entity_node["name"]

            logger.info(
                f"Resolved '{entity_name}' to entity '{resolved_name}' (UUID: {entity_uuid})"
            )

            # Step 2: Get relationships directly from Neo4j (bidirectional)
            relationships = await self._get_entity_relationships_direct(
                entity_uuid,
                max_relationships,
                relationship_types,
                include_bidirectional,
            )

            # Step 3: Group relationships by type
            relationship_type_counts = self._group_relationships_by_type(relationships)

            # Calculate totals
            total_outgoing = len(relationships["outgoing"])
            total_incoming = len(relationships["incoming"])
            total_relationships = total_outgoing + total_incoming

            # Step 4: Format response based on output_format
            if output_format == "structured":
                # Structured JSON output
                # Use EntityDetailsTool's sanitization method if available
                output = {
                    "entity": {
                        "name": resolved_name,
                        "uuid": entity_uuid,
                        "labels": entity_node.get("labels", []),
                    },
                    "relationships": relationships,
                    "summary": {
                        "total_relationships": total_relationships,
                        "outgoing_count": total_outgoing,
                        "incoming_count": total_incoming,
                        "relationship_types": relationship_type_counts,
                    },
                }

                # Sanitize for serialization (handle Neo4j DateTime)
                # Borrow _sanitize_for_serialization from EntityDetailsTool if needed
                try:
                    # Simple sanitization inline
                    def sanitize(obj):
                        if obj is None:
                            return None
                        elif isinstance(obj, (str, int, float, bool)):
                            return obj
                        elif isinstance(obj, dict):
                            return {k: sanitize(v) for k, v in obj.items()}
                        elif isinstance(obj, (list, tuple)):
                            return [sanitize(item) for item in obj]
                        else:
                            return str(obj)

                    return sanitize(output)
                except Exception:
                    return output

            else:
                # Text format (markdown)
                response = f"## Relationships for: {resolved_name}\n\n"
                response += f"**Total Relationships**: {total_relationships}"

                if include_bidirectional:
                    response += f" ({total_outgoing} outgoing, {total_incoming} incoming)"
                response += "\n\n"

                if relationship_type_counts:
                    response += "**Relationship Types:**\n"
                    for rel_type, count in sorted(
                        relationship_type_counts.items(), key=lambda x: x[1], reverse=True
                    ):
                        response += f"- {rel_type}: {count} connections\n"
                    response += "\n"

                # Outgoing relationships
                if relationships["outgoing"]:
                    response += f"**Outgoing Relationships** (from {resolved_name}):\n"
                    for i, rel in enumerate(relationships["outgoing"][:max_relationships], 1):
                        response += (
                            f"{i}. [{rel['relationship_type']}] "
                            f"{rel['source_name']} → {rel['target_name']}"
                        )
                        if rel.get("fact"):
                            response += f": {rel['fact'][:100]}..."
                        response += "\n"

                    if len(relationships["outgoing"]) > max_relationships:
                        response += f"... and {len(relationships['outgoing']) - max_relationships} more outgoing\n"
                    response += "\n"

                # Incoming relationships
                if include_bidirectional and relationships["incoming"]:
                    response += f"**Incoming Relationships** (to {resolved_name}):\n"
                    for i, rel in enumerate(relationships["incoming"][:max_relationships], 1):
                        response += (
                            f"{i}. [{rel['relationship_type']}] "
                            f"{rel['source_name']} → {rel['target_name']}"
                        )
                        if rel.get("fact"):
                            response += f": {rel['fact'][:100]}..."
                        response += "\n"

                    if len(relationships["incoming"]) > max_relationships:
                        response += f"... and {len(relationships['incoming']) - max_relationships} more incoming\n"

                logger.info(
                    f"Found {total_relationships} relationships for {resolved_name} "
                    f"({total_outgoing} outgoing, {total_incoming} incoming)"
                )
                return response

        except Exception as e:
            logger.error(f"Error getting entity relationships: {e}")
            error_msg = f"Error retrieving relationships for {entity_name}: {str(e)}"
            if output_format == "text":
                return error_msg
            else:
                return {"entity_name": entity_name, "error": error_msg, "found": False}


class EntityTimelineTool(BaseTool):
    """Tool for tracking how an entity has evolved over time."""

    name: str = "get_entity_timeline"
    description: str = "Track how an entity has evolved, changed, or been mentioned over time. Shows temporal progression of events."
    args_schema: type[BaseModel] = EntityTimelineInput

    client: Graphiti = None

    def __init__(self, graphiti_client: Graphiti, **kwargs):
        super().__init__(**kwargs)
        self.client = graphiti_client

    class Config:
        arbitrary_types_allowed = True

    def _run(
        self,
        entity_name: str,
        days_back: int = 365,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute synchronously - placeholder."""
        return "Sync not implemented - use async version"

    async def _arun(
        self,
        entity_name: str,
        days_back: int = 365,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Get timeline of entity evolution."""
        try:
            logger.info(f"Getting timeline for entity: {entity_name} ({days_back} days back)")

            # Calculate time range
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days_back)

            # Search for temporal mentions of the entity
            search_query = f"{entity_name} timeline history evolution changes development"

            # Use advanced search with edge-focused configuration for temporal analysis
            from graphiti_core.search.search_config_recipes import EDGE_HYBRID_SEARCH_RRF

            search_results = await self.client._search(search_query, config=EDGE_HYBRID_SEARCH_RRF)

            # Extract edges for timeline analysis
            results = []
            if hasattr(search_results, "edges") and search_results.edges:
                results.extend(search_results.edges)

            if not results:
                return f"No timeline information found for entity '{entity_name}'"

            # Try to extract temporal information from facts
            timeline_events = []

            for result in results:
                fact = result.fact
                if entity_name.lower() in fact.lower():
                    # Try to extract date/time information from the fact
                    event = {
                        "fact": fact,
                        "episodes": getattr(result, "episodes", []),
                        "timestamp": None,  # Would need episode details to get exact timestamp
                    }

                    # Look for temporal keywords in the fact
                    temporal_keywords = [
                        "announced",
                        "released",
                        "published",
                        "enacted",
                        "implemented",
                        "proposed",
                        "approved",
                    ]
                    for keyword in temporal_keywords:
                        if keyword in fact.lower():
                            event["type"] = keyword
                            break

                    timeline_events.append(event)

            # Format timeline response
            response = f"## Timeline for: {entity_name}\n\n"
            response += f"**Time Range**: Last {days_back} days\n\n"

            if timeline_events:
                response += "**Key Timeline Events:**\n"
                for i, event in enumerate(timeline_events[:10], 1):
                    event_type = event.get("type", "Event")
                    response += f"{i}. **{event_type.title()}**: {event['fact']}\n"

                if len(timeline_events) > 10:
                    response += (
                        f"\n... and {len(timeline_events) - 10} more timeline events available."
                    )
            else:
                response += f"No specific timeline events found for {entity_name} in the last {days_back} days."

            # Note about temporal precision
            response += "\n\n*Note: Timeline precision depends on document timestamps. Use temporal search tools for more precise date-based queries.*"

            logger.info(f"Found {len(timeline_events)} timeline events for {entity_name}")
            return response

        except Exception as e:
            logger.error(f"Error getting entity timeline: {e}")
            return f"Error retrieving timeline for {entity_name}: {str(e)}"


class SimilarEntitesTool(BaseTool):
    """Tool for finding entities similar to a given entity."""

    name: str = "find_similar_entities"
    description: str = "Find entities that are similar or related to the given entity based on graph structure and context."
    args_schema: type[BaseModel] = SimilarEntitiesInput

    client: Graphiti = None

    def __init__(self, graphiti_client: Graphiti, **kwargs):
        super().__init__(**kwargs)
        self.client = graphiti_client

    class Config:
        arbitrary_types_allowed = True

    def _run(
        self,
        entity_name: str,
        max_similar: int = 5,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute synchronously - placeholder."""
        return "Sync not implemented - use async version"

    async def _arun(
        self,
        entity_name: str,
        max_similar: int = 5,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Find similar entities."""
        try:
            logger.info(f"Finding similar entities to: {entity_name}")

            # Search for similar entities using context and relationships
            search_query = f"{entity_name} similar like comparable equivalent type category"

            # Use advanced search with node-focused configuration for entity similarity
            from graphiti_core.search.search_config_recipes import NODE_HYBRID_SEARCH_RRF

            search_results = await self.client._search(search_query, config=NODE_HYBRID_SEARCH_RRF)

            # Extract both nodes and edges for similarity analysis
            results = []
            if hasattr(search_results, "edges") and search_results.edges:
                results.extend(search_results.edges)
            if hasattr(search_results, "nodes") and search_results.nodes:
                results.extend(search_results.nodes)

            if not results:
                return f"No similar entities found for '{entity_name}'"

            # Extract potential similar entities from facts
            similar_entities = {}

            for result in results:
                # Handle both edges (with .fact) and nodes (with .summary)
                content = ""
                if hasattr(result, "fact") and result.fact:
                    content = result.fact
                elif hasattr(result, "summary") and result.summary:
                    content = result.summary
                elif hasattr(result, "name") and result.name:
                    # If it's a node entity, use its name as potential similar entity
                    entity_name_candidate = result.name
                    if entity_name_candidate != entity_name and len(entity_name_candidate) > 2:
                        if entity_name_candidate not in similar_entities:
                            similar_entities[entity_name_candidate] = []
                        similar_entities[entity_name_candidate].append(
                            getattr(result, "summary", f"Entity: {entity_name_candidate}")
                        )
                    continue

                if not content:
                    continue

                # Extract entity names that appear with the target entity
                # This is a simplified approach - in practice would need NER
                words = content.lower().split()

                # Look for capitalized phrases that might be entity names
                import re

                entity_patterns = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", content)

                for potential_entity in entity_patterns:
                    if potential_entity != entity_name and len(potential_entity) > 2:
                        if potential_entity not in similar_entities:
                            similar_entities[potential_entity] = []
                        similar_entities[potential_entity].append(content)

            # Rank by frequency of co-occurrence
            ranked_similar = sorted(
                similar_entities.items(), key=lambda x: len(x[1]), reverse=True
            )[:max_similar]

            # Format response
            response = f"## Similar Entities to: {entity_name}\n\n"

            if ranked_similar:
                response += "**Most Similar Entities:**\n"
                for i, (similar_entity, contexts) in enumerate(ranked_similar, 1):
                    response += f"{i}. **{similar_entity}** (appears together in {len(contexts)} context(s))\n"
                    # Show one example context
                    if contexts:
                        response += f"   Example: {contexts[0][:100]}...\n"
                response += "\n"
            else:
                response += f"No clearly similar entities identified for {entity_name}.\n\n"

            # Suggest using community detection for better similarity
            response += "*Note: For more sophisticated similarity analysis, consider using community detection tools to find entities in the same cluster.*"

            logger.info(f"Found {len(ranked_similar)} similar entities for {entity_name}")
            return response

        except Exception as e:
            logger.error(f"Error finding similar entities: {e}")
            return f"Error finding similar entities to {entity_name}: {str(e)}"
