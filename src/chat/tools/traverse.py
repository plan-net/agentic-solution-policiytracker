"""Graph traversal tools for exploring multi-hop relationships in the knowledge graph."""

import logging
from typing import Optional

from graphiti_core import Graphiti
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TraverseFromEntityInput(BaseModel):
    """Input schema for traversing from an entity."""

    entity_name: str = Field(description="Starting entity to traverse from")
    relationship_types: Optional[list[str]] = Field(
        default=None,
        description="[DEPRECATED] Not used - tool now finds ALL relationships and applies relevance filtering",
    )
    max_depth: int = Field(default=2, description="Maximum depth to traverse (1-3 recommended)")
    max_results: int = Field(
        default=15, description="Maximum number of most relevant results to return"
    )


class FindPathsInput(BaseModel):
    """Input schema for finding paths between entities."""

    source_entity: str = Field(description="Source entity to start from")
    target_entity: str = Field(description="Target entity to find paths to")
    max_path_length: int = Field(default=4, description="Maximum path length to search")
    max_paths: int = Field(default=5, description="Maximum number of paths to return")


class GetNeighborsInput(BaseModel):
    """Input schema for getting entity neighbors."""

    entity_name: str = Field(description="Entity to find neighbors for")
    max_depth: int = Field(default=1, description="Depth of neighbors to explore (1-2 recommended)")
    neighbor_types: Optional[list[str]] = Field(
        default=None,
        description="DEPRECATED - Parameter accepted for backwards compatibility but ignored. Tool now returns ALL neighbor types using Neo4j Cypher queries.",
    )


class ImpactAnalysisInput(BaseModel):
    """Input schema for impact analysis."""

    entity_name: str = Field(description="Entity to analyze impact for")
    impact_types: Optional[list[str]] = Field(
        default=None, description="Types of impact to focus on (e.g., ['regulatory', 'financial'])"
    )
    max_hops: int = Field(default=3, description="Maximum relationship hops to explore for impact")


class TraverseFromEntityTool(BaseTool):
    """Tool for traversing relationships from a specific entity with intelligent relevance filtering."""

    name: str = "traverse_from_entity"
    description: str = "Follow ALL relationships from an entity to explore connected entities, with intelligent relevance filtering to show the most important connections. Returns results ranked by relationship importance, path distance, and context richness."
    args_schema: type[BaseModel] = TraverseFromEntityInput

    client: Graphiti = None

    def __init__(self, graphiti_client: Graphiti, **kwargs):
        super().__init__(**kwargs)
        self.client = graphiti_client

    class Config:
        arbitrary_types_allowed = True

    async def _find_entity_node(self, entity_name: str) -> Optional[dict]:
        """Find entity node in Neo4j using smart matching.

        Uses Neo4j Cypher query to find entity nodes with exact or fuzzy name matching.
        Returns best match based on shortest name length (avoids false positives).

        Args:
            entity_name: Name to search for

        Returns:
            Dict with uuid, name, labels, and properties if found, else None
        """
        try:
            # Build query with smart matching
            query = """
                MATCH (n:Entity)
                WHERE toLower(n.name) CONTAINS toLower($entity_name)
                RETURN n.uuid AS uuid, n.name AS name, labels(n) AS labels,
                       properties(n) AS properties
                ORDER BY size(n.name) ASC
                LIMIT 5
            """

            # Execute query
            async with self.client.driver.session() as session:
                result = await session.run(query, {"entity_name": entity_name})
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
            logger.error(f"Error finding entity node: {e}", exc_info=True)
            return None

    async def _traverse_graph_cypher(
        self,
        entity_uuid: str,
        max_depth: int,
        max_results: int = 50,  # Get more results for relevance filtering
    ) -> list[dict]:
        """Execute real graph traversal using Neo4j Cypher - gets ALL relationship types.

        Args:
            entity_uuid: UUID of the starting entity
            max_depth: Maximum relationship hops to traverse (1-3 recommended)
            max_results: Maximum number of raw results to retrieve before filtering

        Returns:
            List of dicts with traversal path information
        """
        try:
            # Cypher query for multi-hop traversal - NO relationship type filter
            # This gets ALL connected entities regardless of relationship type
            query = f"""
                MATCH path = (start:Entity {{uuid: $entity_uuid}})-[*1..{max_depth}]-(connected:Entity)
                WITH path, connected, relationships(path) AS rels, length(path) AS depth
                WHERE connected.uuid <> $entity_uuid
                RETURN DISTINCT
                    connected.uuid AS target_uuid,
                    connected.name AS target_name,
                    labels(connected) AS target_types,
                    [rel IN rels | {{
                        type: type(rel),
                        source_name: startNode(rel).name,
                        target_name: endNode(rel).name,
                        fact: COALESCE(rel.fact, ''),
                        properties: properties(rel)
                    }}] AS relationship_chain,
                    depth
                ORDER BY depth ASC
                LIMIT $max_results
            """

            async with self.client.driver.session() as session:
                result = await session.run(
                    query,
                    {
                        "entity_uuid": entity_uuid,
                        "max_results": max_results,
                    },
                )
                records = await result.data()

                logger.info(
                    f"Cypher traversal found {len(records)} connected entities (all relationship types)"
                )
                return records

        except Exception as e:
            logger.error(f"Error in Cypher traversal: {e}", exc_info=True)
            return []

    def _calculate_relevance_score(self, entity_data: dict, source_entity_name: str) -> float:
        """Calculate relevance score for a traversal result.

        Scoring factors:
        - Depth: Shorter paths are more relevant (1/depth weight)
        - Fact richness: Relationships with detailed facts are more relevant
        - Relationship types: Certain relationship types are more important
        - Entity types: Certain entity types are more relevant

        Args:
            entity_data: Entity data from traversal
            source_entity_name: Name of the source entity

        Returns:
            Relevance score (higher = more relevant)
        """
        score = 0.0

        # Factor 1: Depth (inverse weight - closer is more relevant)
        depth = entity_data.get("depth", 1)
        score += 10.0 / depth  # Max 10.0 for depth 1, 5.0 for depth 2, etc.

        # Factor 2: Relationship fact richness
        rel_chain = entity_data.get("relationship_chain", [])
        for hop in rel_chain:
            fact = hop.get("fact", "")
            if fact:
                # Score based on fact length (more detail = more relevant)
                fact_score = min(len(fact) / 100.0, 3.0)  # Max 3.0 for facts >300 chars
                score += fact_score

        # Factor 3: Relationship type importance
        important_rel_types = {
            "AFFECTS": 3.0,
            "REGULATES": 3.0,
            "GOVERNS": 3.0,
            "ENFORCES": 2.5,
            "REQUIRES_COMPLIANCE": 2.5,
            "SUBJECT_TO": 2.5,
            "IMPLEMENTS": 2.0,
            "PROPOSES": 2.0,
            "INFLUENCES": 1.5,
            "RELATES_TO": 1.0,
            "REFERENCES": 1.0,
        }
        for hop in rel_chain:
            rel_type = hop.get("type", "")
            type_score = important_rel_types.get(rel_type, 0.5)  # Default 0.5 for unknown types
            score += type_score

        # Factor 4: Entity type relevance
        target_types = entity_data.get("target_types", [])
        important_entity_types = {
            "Policy": 3.0,
            "Regulation": 3.0,
            "LegislativeProposal": 2.5,
            "Politician": 2.0,
            "Organization": 2.0,
            "Company": 2.0,
            "GovernmentAgency": 2.0,
            "LegislativeBody": 1.5,
            "Committee": 1.5,
        }
        for entity_type in target_types:
            if entity_type != "Entity":  # Skip generic Entity label
                type_score = important_entity_types.get(entity_type, 1.0)
                score += type_score

        # Factor 5: Path diversity bonus
        # Bonus for paths that traverse different relationship types
        unique_rel_types = set(hop.get("type", "") for hop in rel_chain)
        if len(unique_rel_types) > 1:
            score += 1.0 * len(unique_rel_types)

        return score

    async def _extract_source_from_episode(self, episode_key: str) -> Optional[dict]:
        """Extract source information from episode UUID or name."""
        try:
            # Query Neo4j for Episodic node metadata
            query = """
                MATCH (e:Episodic)
                WHERE e.uuid = $episode_key OR e.name = $episode_key
                RETURN e.uuid AS uuid, e.name AS name, e.source AS source,
                       e.source_description AS source_description
                LIMIT 1
            """

            async with self.client.driver.session() as session:
                result = await session.run(query, {"episode_key": episode_key})
                records = await result.data()

                if records:
                    record = records[0]

                    # Parse episode name to extract source
                    if record.get("name"):
                        source_info = self._parse_episodic_name(record["name"])
                        if source_info:
                            return source_info

                    # Parse source_description as fallback
                    if record.get("source_description"):
                        desc = record["source_description"]
                        if ":" in desc:
                            filename = desc.split(":", 1)[1].strip()
                            if filename.endswith(".md"):
                                filename = filename[:-3]
                            source_info = self._parse_episodic_name(filename)
                            if source_info:
                                return source_info

            return None

        except Exception as e:
            logger.debug(f"Error extracting source from episode: {e}")
            return None

    def _parse_episodic_name(self, name: str) -> Optional[dict]:
        """Parse Episodic node name to extract source information."""
        try:
            # Expected format: political_doc_YYYYMMDD_domain_title_timestamp_chunk_N
            # Remove 'political_doc_' prefix if present
            if name.startswith("political_doc_"):
                name = name[14:]

            # Split by underscore
            parts = name.split("_")

            if len(parts) < 3:
                return None

            # First part is date (YYYYMMDD)
            date_part = parts[0] if parts[0].isdigit() and len(parts[0]) == 8 else None

            # Second part is domain (with hyphens)
            domain_part = parts[1].replace("-", ".") if len(parts) > 1 else None

            if not domain_part:
                return None

            # Collect title parts (between domain and timestamp/chunk markers)
            title_parts = []
            for i in range(2, len(parts)):
                part = parts[i]
                # Stop at timestamp (8 digits followed by 6 digits)
                if part.isdigit() and len(part) >= 8:
                    break
                # Stop at 'chunk'
                if part == "chunk":
                    break
                title_parts.append(part)

            # Build title
            title = " ".join(title_parts).replace("-", " ") if title_parts else ""

            # Construct URL
            url = f"https://{domain_part}"

            # Create display title
            if title:
                display_title = f"{domain_part}: {title[:60]}"
                if len(title) > 60:
                    display_title += "..."
            else:
                display_title = domain_part

            return {"url": url, "title": display_title, "date": date_part}

        except Exception as e:
            logger.debug(f"Could not parse Episodic name: {e}")
            return None

    def _apply_relevance_filtering(
        self, traversal_results: list[dict], source_entity_name: str, max_final_results: int = 15
    ) -> list[dict]:
        """Apply relevance scoring and filter to top results.

        Args:
            traversal_results: Raw traversal results from Cypher
            source_entity_name: Name of source entity (for context)
            max_final_results: Maximum number of results to return

        Returns:
            Top N most relevant results
        """
        if not traversal_results:
            return []

        # Calculate relevance score for each result
        scored_results = []
        for result in traversal_results:
            score = self._calculate_relevance_score(result, source_entity_name)
            scored_results.append({"data": result, "relevance_score": score})

        # Sort by relevance score (highest first)
        scored_results.sort(key=lambda x: x["relevance_score"], reverse=True)

        # Return top N results (just the data, not the scores)
        top_results = [item["data"] for item in scored_results[:max_final_results]]

        logger.info(
            f"Relevance filtering: {len(traversal_results)} raw results → {len(top_results)} most relevant results"
        )
        if top_results:
            logger.debug(
                f"Top result score: {scored_results[0]['relevance_score']:.2f}, "
                f"Lowest result score: {scored_results[min(len(scored_results)-1, max_final_results-1)]['relevance_score']:.2f}"
            )

        return top_results

    def _run(
        self,
        entity_name: str,
        relationship_types: Optional[list[str]] = None,
        max_depth: int = 2,
        max_results: int = 15,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute synchronously - placeholder."""
        return "Sync not implemented - use async version"

    async def _arun(
        self,
        entity_name: str,
        relationship_types: Optional[
            list[str]
        ] = None,  # Kept for backwards compatibility, but not used for filtering
        max_depth: int = 2,
        max_results: int = 15,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Traverse relationships from an entity using real Neo4j graph traversal with relevance filtering.

        Note: This tool now finds ALL relationship types and applies intelligent relevance scoring
        to return the most important connections. The relationship_types parameter is deprecated.
        """
        try:
            logger.info(
                f"Traversing from entity: {entity_name} (depth={max_depth}, relevance-filtered)"
            )

            # Step 1: Find entity node using smart matching
            entity_node = await self._find_entity_node(entity_name)

            if not entity_node:
                return f"❌ Entity '{entity_name}' not found in knowledge graph.\n\n**Suggestions:**\n- Try a different spelling or abbreviation\n- Use the search tool first to find exact entity names\n- Check if the entity exists in the graph"

            resolved_name = entity_node["name"]
            entity_uuid = entity_node["uuid"]

            # Step 2: Execute Cypher-based graph traversal (gets ALL relationship types)
            # Fetch more raw results for relevance filtering
            raw_max_results = max_results * 3  # Get 3x results for filtering
            traversal_results = await self._traverse_graph_cypher(
                entity_uuid=entity_uuid,
                max_depth=max_depth,
                max_results=raw_max_results,
            )

            if not traversal_results:
                response = f"## Relationship Traversal from: {resolved_name}\n\n"
                response += (
                    f"❌ No connections found within {max_depth} hops.\n\n**Suggestions:**\n"
                )
                response += "- Increase max_depth to explore further\n"
                response += "- Try exploring neighbors of related entities\n"
                response += "- Verify the entity has relationships in the graph\n"
                return response

            # Step 3: Apply relevance filtering to get top results
            filtered_results = self._apply_relevance_filtering(
                traversal_results, resolved_name, max_final_results=max_results
            )

            # Step 4: Format structured output
            response = f"## Relationship Traversal from: {resolved_name}\n\n"
            response += f"**Traversal Depth**: {max_depth} levels\n"
            response += f"**Total Entities Found**: {len(traversal_results)} (showing top {len(filtered_results)} most relevant)\n"
            response += "**Relevance Filtering**: Applied intelligent scoring based on relationship importance, path distance, and context richness\n"
            response += "\n"

            # Group by depth level (using filtered results)
            depth_groups = {}
            for result in filtered_results:
                depth = result["depth"]
                if depth not in depth_groups:
                    depth_groups[depth] = []
                depth_groups[depth].append(result)

            # Display results by depth level
            for depth in sorted(depth_groups.keys()):
                entities_at_depth = depth_groups[depth]
                response += (
                    f"### Level {depth} Connections ({len(entities_at_depth)} entities):\n\n"
                )

                for entity_data in entities_at_depth[:10]:  # Show top 10 per level
                    target_name = entity_data["target_name"]
                    target_types = entity_data.get("target_types", [])
                    rel_chain = entity_data.get("relationship_chain", [])

                    # Show entity with types
                    entity_types_str = (
                        ", ".join([t for t in target_types if t != "Entity"])
                        if target_types
                        else "Unknown"
                    )
                    response += f"**{target_name}** ({entity_types_str})\n"

                    # Show relationship chain (path from source to target)
                    if rel_chain:
                        response += "  Path: "
                        path_str = " → ".join(
                            [
                                f"{hop['source_name']} --[{hop['type']}]--> {hop['target_name']}"
                                for hop in rel_chain
                            ]
                        )
                        # Truncate if too long
                        if len(path_str) > 150:
                            path_str = path_str[:150] + "..."
                        response += f"{path_str}\n"

                        # Show fact if available
                        if rel_chain[0].get("fact"):
                            fact = rel_chain[0]["fact"]
                            if len(fact) > 100:
                                fact = fact[:100] + "..."
                            response += f"  Context: {fact}\n"

                    response += "\n"

                # Show remaining count if more exist
                if len(entities_at_depth) > 10:
                    response += (
                        f"  ... and {len(entities_at_depth) - 10} more entities at this level\n\n"
                    )

            # Add detailed summary sections (like search tool)
            response += "\n---\n\n"

            # 1. Collect unique entities found
            entities_found = {}  # uuid -> entity data
            for result in filtered_results:
                uuid = result.get("target_uuid")
                if uuid and uuid not in entities_found:
                    entities_found[uuid] = {
                        "name": result["target_name"],
                        "types": [t for t in result.get("target_types", []) if t != "Entity"],
                        "uuid": uuid,
                    }

            # 2. Collect unique relationships
            relationships_discovered = {}  # relationship_type -> count
            for result in filtered_results:
                rel_chain = result.get("relationship_chain", [])
                for hop in rel_chain:
                    rel_type = hop["type"]
                    relationships_discovered[rel_type] = (
                        relationships_discovered.get(rel_type, 0) + 1
                    )

            # 3. Extract source citations from episodes (if available)
            source_citations = []
            seen_sources = set()

            for result in filtered_results:
                rel_chain = result.get("relationship_chain", [])
                for hop in rel_chain:
                    # Try to extract source from relationship properties
                    if "properties" in hop:
                        props = hop.get("properties", {})
                        if "source" in props or "episode" in props:
                            source_key = props.get("source", props.get("episode"))
                            if source_key and source_key not in seen_sources:
                                # Parse episode/source information
                                source_info = await self._extract_source_from_episode(source_key)
                                if source_info:
                                    source_citations.append(source_info)
                                    seen_sources.add(source_key)

            # 4. Extract temporal aspects
            temporal_aspects = []
            seen_dates = set()

            for result in filtered_results:
                rel_chain = result.get("relationship_chain", [])
                for hop in rel_chain:
                    props = hop.get("properties", {})
                    # Look for date/time fields
                    for key in ["created_at", "date", "timestamp", "valid_from"]:
                        if key in props and props[key]:
                            date_val = str(props[key])
                            if date_val not in seen_dates:
                                temporal_aspects.append(
                                    {
                                        "date": date_val,
                                        "relationship": hop["type"],
                                        "context": f"{hop['source_name']} → {hop['target_name']}",
                                    }
                                )
                                seen_dates.add(date_val)

            # Format summary sections
            response += "## Summary\n\n"

            # Entities Found
            response += f"### Entities Found ({len(entities_found)})\n"
            if entities_found:
                for entity in list(entities_found.values())[:10]:  # Show top 10
                    types_str = ", ".join(entity["types"]) if entity["types"] else "Entity"
                    response += f"- **{entity['name']}** ({types_str})\n"
                if len(entities_found) > 10:
                    response += f"- ... and {len(entities_found) - 10} more entities\n"
            else:
                response += "- No entities found\n"
            response += "\n"

            # Relationships Discovered
            response += f"### Relationships Discovered ({len(relationships_discovered)} types)\n"
            if relationships_discovered:
                # Sort by count (most common first)
                sorted_rels = sorted(
                    relationships_discovered.items(), key=lambda x: x[1], reverse=True
                )
                for rel_type, count in sorted_rels[:10]:  # Show top 10
                    response += f"- **{rel_type}**: {count} occurrence{'s' if count > 1 else ''}\n"
                if len(relationships_discovered) > 10:
                    response += (
                        f"- ... and {len(relationships_discovered) - 10} more relationship types\n"
                    )
            else:
                response += "- No relationships found\n"
            response += "\n"

            # Source Citations
            response += f"### Source Citations ({len(source_citations)})\n"
            if source_citations:
                for i, source in enumerate(source_citations[:5], 1):  # Show top 5
                    response += f"{i}. {source['title']}\n"
                    if source.get("url"):
                        response += f"   URL: {source['url']}\n"
                if len(source_citations) > 5:
                    response += f"- ... and {len(source_citations) - 5} more sources\n"
            else:
                response += "- No source citations available\n"
            response += "\n"

            # Temporal Aspects
            response += f"### Temporal Aspects ({len(temporal_aspects)})\n"
            if temporal_aspects:
                # Sort by date (most recent first)
                sorted_temporal = sorted(temporal_aspects, key=lambda x: x["date"], reverse=True)
                for aspect in sorted_temporal[:5]:  # Show top 5
                    response += (
                        f"- **{aspect['date']}**: {aspect['relationship']} - {aspect['context']}\n"
                    )
                if len(temporal_aspects) > 5:
                    response += f"- ... and {len(temporal_aspects) - 5} more temporal entries\n"
            else:
                response += "- No temporal information available\n"

            logger.info(
                f"Traversal found {len(traversal_results)} total entities, filtered to {len(filtered_results)} most relevant across {len(depth_groups)} depth levels. Summary: {len(entities_found)} entities, {len(relationships_discovered)} relationship types, {len(source_citations)} sources, {len(temporal_aspects)} temporal aspects"
            )
            return response

        except Exception as e:
            logger.error(f"Error in traversal: {e}", exc_info=True)
            return f"❌ Error traversing from {entity_name}: {str(e)}\n\nPlease check logs for details."


class FindPathsTool(BaseTool):
    """Tool for finding connection paths between two entities using Neo4j shortest path algorithms."""

    name: str = "find_paths_between_entities"
    description: str = "Find actual connection paths between two entities using Neo4j graph algorithms (shortestPath, allShortestPaths). Shows complete path chains with intermediate entities, relationship types, and contextual facts. Includes summary sections with entities found, relationships discovered, source citations, and temporal aspects."
    args_schema: type[BaseModel] = FindPathsInput

    client: Graphiti = None

    def __init__(self, graphiti_client: Graphiti, **kwargs):
        super().__init__(**kwargs)
        self.client = graphiti_client

    class Config:
        arbitrary_types_allowed = True

    def _run(
        self,
        source_entity: str,
        target_entity: str,
        max_path_length: int = 4,
        max_paths: int = 5,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute synchronously - placeholder."""
        return "Sync not implemented - use async version"

    async def _find_entity_node(self, entity_name: str) -> Optional[dict]:
        """Find entity node in Neo4j using smart matching."""
        try:
            query = """
                MATCH (n:Entity)
                WHERE toLower(n.name) CONTAINS toLower($entity_name)
                RETURN n.uuid AS uuid, n.name AS name, labels(n) AS labels,
                       properties(n) AS properties
                ORDER BY size(n.name) ASC
                LIMIT 5
            """

            async with self.client.driver.session() as session:
                result = await session.run(query, {"entity_name": entity_name})
                records = await result.data()

                if records:
                    # Return best match (shortest name containing the search term)
                    best_match = records[0]
                    logger.info(
                        f"Found entity node: {best_match['name']} (UUID: {best_match['uuid']})"
                    )
                    return best_match

                logger.warning(f"No entity node found for: {entity_name}")
                return None

        except Exception as e:
            logger.error(f"Error finding entity node: {e}", exc_info=True)
            return None

    async def _find_paths_cypher(
        self,
        source_uuid: str,
        target_uuid: str,
        max_path_length: int = 4,
        max_paths: int = 5,
    ) -> list[dict]:
        """Find paths between two entities using Neo4j shortest path algorithms."""
        try:
            # Use allShortestPaths to find multiple shortest paths
            query = f"""
                MATCH path = allShortestPaths(
                    (start:Entity {{uuid: $source_uuid}})-[*..{max_path_length}]-(end:Entity {{uuid: $target_uuid}})
                )
                WITH path,
                     [node IN nodes(path) | {{
                         uuid: node.uuid,
                         name: node.name,
                         types: labels(node)
                     }}] AS path_nodes,
                     [rel IN relationships(path) | {{
                         type: type(rel),
                         source_name: startNode(rel).name,
                         target_name: endNode(rel).name,
                         fact: COALESCE(rel.fact, ''),
                         properties: properties(rel)
                     }}] AS path_relationships,
                     length(path) AS path_length
                RETURN path_nodes, path_relationships, path_length
                ORDER BY path_length ASC
                LIMIT $max_paths
            """

            params = {
                "source_uuid": source_uuid,
                "target_uuid": target_uuid,
                "max_paths": max_paths,
            }

            async with self.client.driver.session() as session:
                result = await session.run(query, params)
                records = await result.data()

            logger.info(f"Found {len(records)} paths between entities")
            return records

        except Exception as e:
            logger.error(f"Error finding paths via Cypher: {e}", exc_info=True)
            return []

    async def _extract_source_from_episode(self, episode_key: str) -> Optional[dict]:
        """Extract source information from episode UUID or name."""
        try:
            query = """
                MATCH (e:Episodic)
                WHERE e.uuid = $episode_key OR e.name = $episode_key
                RETURN e.uuid AS uuid, e.name AS name, e.source AS source,
                       e.source_description AS source_description
                LIMIT 1
            """

            async with self.client.driver.session() as session:
                result = await session.run(query, {"episode_key": episode_key})
                records = await result.data()

                if records:
                    record = records[0]

                    # Try to parse episode name first
                    if record.get("name"):
                        source_info = self._parse_episodic_name(record["name"])
                        if source_info:
                            return source_info

                    # Fallback to source_description
                    if record.get("source_description"):
                        return {"url": "", "title": record["source_description"][:80], "date": None}

        except Exception as e:
            logger.error(f"Error extracting source from episode: {e}")

        return None

    def _parse_episodic_name(self, name: str) -> Optional[dict]:
        """Parse Episodic node name to extract source information.

        Expected format: political_doc_YYYYMMDD_domain_title_timestamp_chunk_N
        Example: political_doc_20240315_europa-eu_digital-services-act_1710500000_chunk_0
        """
        try:
            # Remove political_doc_ prefix if present
            if name.startswith("political_doc_"):
                name = name[14:]  # len("political_doc_") = 14

            # Split by underscore
            parts = name.split("_")

            if len(parts) < 3:
                return None

            # Extract date (first part should be YYYYMMDD)
            date_part = parts[0] if parts[0].isdigit() and len(parts[0]) == 8 else None

            # Extract domain (second part, restore dots)
            domain_part = parts[1].replace("-", ".") if len(parts) > 1 else None

            if not domain_part:
                return None

            # Extract title (parts between domain and timestamp/chunk)
            title_parts = []
            for i in range(2, len(parts)):
                part = parts[i]

                # Stop at timestamp (long digit string) or "chunk" keyword
                if part.isdigit() and len(part) >= 8:
                    break
                if part == "chunk":
                    break

                title_parts.append(part)

            # Reconstruct title
            title = " ".join(title_parts).replace("-", " ") if title_parts else ""

            # Build URL
            url = f"https://{domain_part}"

            # Create display title
            if title:
                display_title = f"{domain_part}: {title[:60]}"
                if len(title) > 60:
                    display_title += "..."
            else:
                display_title = domain_part

            return {"url": url, "title": display_title, "date": date_part}

        except Exception as e:
            logger.error(f"Error parsing episodic name '{name}': {e}")
            return None

    async def _arun(
        self,
        source_entity: str,
        target_entity: str,
        max_path_length: int = 4,
        max_paths: int = 5,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Find paths between two entities using Neo4j shortest path algorithms."""
        try:
            logger.info(
                f"Finding paths between: {source_entity} -> {target_entity} (max_length={max_path_length})"
            )

            # Step 1: Find both entity nodes using smart Neo4j matching
            source_node = await self._find_entity_node(source_entity)
            if not source_node:
                return f"❌ Source entity '{source_entity}' not found in knowledge graph.\n\nPlease verify the entity name or try a related search."

            target_node = await self._find_entity_node(target_entity)
            if not target_node:
                return f"❌ Target entity '{target_entity}' not found in knowledge graph.\n\nPlease verify the entity name or try a related search."

            source_name = source_node["name"]
            target_name = target_node["name"]

            # Step 2: Find paths using Neo4j shortest path algorithms
            paths = await self._find_paths_cypher(
                source_uuid=source_node["uuid"],
                target_uuid=target_node["uuid"],
                max_path_length=max_path_length,
                max_paths=max_paths,
            )

            if not paths:
                return f"## Connection Paths: {source_name} ↔ {target_name}\n\n❌ No paths found within {max_path_length} hops.\n\n**Suggestions:**\n- Increase max_path_length to explore longer paths\n- Try finding paths to intermediate entities\n- Use traverse_network tool to explore each entity's connections\n- Verify both entities are in the same connected component"

            # Step 3: Format output with path chains
            response = f"## Connection Paths: {source_name} ↔ {target_name}\n\n"
            response += f"**Maximum Path Length**: {max_path_length} hop(s)\n"
            response += f"**Paths Found**: {len(paths)}\n\n"

            # Track all entities and relationships for summary
            all_entities = {}  # uuid -> {name, types}
            all_relationships = {}  # rel_type -> count
            all_sources = {}  # episode_key -> source_info
            temporal_data = []  # List of (date, rel_type, source → target)

            for idx, path_data in enumerate(paths, 1):
                path_nodes = path_data["path_nodes"]
                path_relationships = path_data["path_relationships"]
                path_length = path_data["path_length"]

                response += f"### Path {idx} ({path_length} hop{'s' if path_length != 1 else ''})\n"

                # Build path chain visualization
                path_chain = []
                for i, node in enumerate(path_nodes):
                    node_name = node["name"]
                    node_types = node.get("types", [])
                    node_type = next((t for t in node_types if t != "Entity"), "Entity")

                    # Track entity for summary
                    all_entities[node["uuid"]] = {"name": node_name, "type": node_type}

                    if i < len(path_relationships):
                        rel = path_relationships[i]
                        rel_type = rel["type"]

                        # Track relationship for summary
                        all_relationships[rel_type] = all_relationships.get(rel_type, 0) + 1

                        path_chain.append(f"{node_name} —[{rel_type}]→ ")

                        # Extract temporal data
                        if rel.get("properties"):
                            props = rel["properties"]
                            if "created_at" in props:
                                temporal_data.append(
                                    {
                                        "date": props["created_at"],
                                        "rel_type": rel_type,
                                        "source": rel["source_name"],
                                        "target": rel["target_name"],
                                    }
                                )

                            # Extract source from episode if available
                            if "episode_uuids" in props and props["episode_uuids"]:
                                episode_key = props["episode_uuids"][0]
                                if episode_key not in all_sources:
                                    source_info = await self._extract_source_from_episode(
                                        episode_key
                                    )
                                    if source_info:
                                        all_sources[episode_key] = source_info
                    else:
                        path_chain.append(node_name)

                # Display path chain
                response += "**Path Chain**: " + "".join(path_chain) + "\n\n"

                # Display relationship details
                response += "**Relationships**:\n"
                for i, rel in enumerate(path_relationships, 1):
                    rel_type = rel["type"]
                    fact = rel.get("fact", "")
                    source_name = rel.get("source_name", "")
                    target_name = rel.get("target_name", "")

                    response += f"{i}. **{rel_type}**: {source_name} → {target_name}\n"
                    if fact:
                        # Truncate long facts
                        display_fact = fact[:200] + "..." if len(fact) > 200 else fact
                        response += f"   *Context*: {display_fact}\n"

                response += "\n"

            # Step 4: Add summary sections
            response += "---\n\n## Summary\n\n"

            # Entities Found
            if all_entities:
                response += f"### Entities Found ({len(all_entities)})\n"
                for entity_data in list(all_entities.values())[:20]:
                    response += f"- **{entity_data['name']}** ({entity_data['type']})\n"
                if len(all_entities) > 20:
                    response += f"... and {len(all_entities) - 20} more entities\n"
                response += "\n"

            # Relationships Discovered
            if all_relationships:
                response += f"### Relationships Discovered ({len(all_relationships)} types)\n"
                sorted_rels = sorted(all_relationships.items(), key=lambda x: x[1], reverse=True)
                for rel_type, count in sorted_rels[:15]:
                    response += f"- **{rel_type}**: {count} occurrence(s)\n"
                if len(sorted_rels) > 15:
                    response += f"... and {len(sorted_rels) - 15} more relationship types\n"
                response += "\n"

            # Source Citations
            if all_sources:
                response += f"### Source Citations ({len(all_sources)})\n"
                for i, source_info in enumerate(list(all_sources.values())[:10], 1):
                    title = source_info.get("title", "Unknown source")
                    url = source_info.get("url", "")
                    date = source_info.get("date", "")

                    response += f"{i}. {title}\n"
                    if url:
                        response += f"   URL: {url}\n"
                    if date:
                        response += f"   Date: {date}\n"

                if len(all_sources) > 10:
                    response += f"... and {len(all_sources) - 10} more sources\n"
                response += "\n"

            # Temporal Aspects
            if temporal_data:
                response += f"### Temporal Aspects ({len(temporal_data)})\n"
                # Sort by date
                sorted_temporal = sorted(
                    temporal_data, key=lambda x: x.get("date", ""), reverse=True
                )
                for i, temp in enumerate(sorted_temporal[:10], 1):
                    date = temp.get("date", "Unknown date")
                    rel_type = temp.get("rel_type", "")
                    source = temp.get("source", "")
                    target = temp.get("target", "")

                    response += f"- **{date}**: {rel_type} - {source} → {target}\n"

                if len(sorted_temporal) > 10:
                    response += f"... and {len(sorted_temporal) - 10} more temporal relationships\n"

            logger.info(f"Found {len(paths)} paths between {source_name} and {target_name}")
            return response

        except Exception as e:
            logger.error(f"Error finding paths: {e}", exc_info=True)
            return f"❌ Error finding paths between {source_entity} and {target_entity}: {str(e)}\n\nPlease check logs for details."


class GetNeighborsTool(BaseTool):
    """Tool for getting immediate neighbors of an entity using Neo4j Cypher queries."""

    name: str = "get_entity_neighbors"
    description: str = "Get ALL entities directly connected to the given entity using Neo4j Cypher queries. Returns neighbors separated by direction (outgoing: entity → neighbors, incoming: neighbors → entity). Shows complete immediate network neighborhood with relationship details, entity types, and contextual facts. Includes summary sections with discovered entities, relationships, source citations, and temporal aspects."
    args_schema: type[BaseModel] = GetNeighborsInput

    client: Graphiti = None

    def __init__(self, graphiti_client: Graphiti, **kwargs):
        super().__init__(**kwargs)
        self.client = graphiti_client

    class Config:
        arbitrary_types_allowed = True

    async def _find_entity_node(self, entity_name: str) -> Optional[dict]:
        """Find entity node in Neo4j using smart matching.

        Uses Neo4j Cypher query to find entity nodes with exact or fuzzy name matching.
        Returns best match based on shortest name length (avoids false positives).

        Args:
            entity_name: Name to search for

        Returns:
            Dict with uuid, name, labels, and properties if found, else None
        """
        try:
            # Build query with smart matching
            query = """
                MATCH (n:Entity)
                WHERE toLower(n.name) CONTAINS toLower($entity_name)
                RETURN n.uuid AS uuid, n.name AS name, labels(n) AS labels,
                       properties(n) AS properties
                ORDER BY size(n.name) ASC
                LIMIT 5
            """

            # Execute query
            async with self.client.driver.session() as session:
                result = await session.run(query, {"entity_name": entity_name})
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
            logger.error(f"Error finding entity node: {e}", exc_info=True)
            return None

    async def _get_neighbors_cypher(
        self,
        entity_uuid: str,
        max_depth: int = 1,
        max_results: int = 50,
    ) -> dict:
        """Get neighbors using Neo4j Cypher queries - separate outgoing and incoming.

        Args:
            entity_uuid: UUID of the entity node
            max_depth: Maximum relationship hops (default 1 for immediate neighbors)
            max_results: Maximum results per direction

        Returns:
            Dict with 'outgoing' and 'incoming' neighbor lists
        """
        try:
            # Query for OUTGOING relationships (entity -> neighbors)
            outgoing_query = f"""
                MATCH path = (start:Entity {{uuid: $entity_uuid}})-[r*1..{max_depth}]->(neighbor:Entity)
                WHERE neighbor.uuid <> $entity_uuid
                WITH neighbor, relationships(path) AS rels, length(path) AS depth
                RETURN DISTINCT
                    neighbor.uuid AS neighbor_uuid,
                    neighbor.name AS neighbor_name,
                    labels(neighbor) AS neighbor_types,
                    [rel IN rels | {{
                        type: type(rel),
                        source_name: startNode(rel).name,
                        target_name: endNode(rel).name,
                        fact: COALESCE(rel.fact, ''),
                        properties: properties(rel)
                    }}] AS relationship_chain,
                    depth
                ORDER BY depth ASC, neighbor_name ASC
                LIMIT $max_results
            """

            # Query for INCOMING relationships (neighbors -> entity)
            incoming_query = f"""
                MATCH path = (neighbor:Entity)-[r*1..{max_depth}]->(start:Entity {{uuid: $entity_uuid}})
                WHERE neighbor.uuid <> $entity_uuid
                WITH neighbor, relationships(path) AS rels, length(path) AS depth
                RETURN DISTINCT
                    neighbor.uuid AS neighbor_uuid,
                    neighbor.name AS neighbor_name,
                    labels(neighbor) AS neighbor_types,
                    [rel IN rels | {{
                        type: type(rel),
                        source_name: startNode(rel).name,
                        target_name: endNode(rel).name,
                        fact: COALESCE(rel.fact, ''),
                        properties: properties(rel)
                    }}] AS relationship_chain,
                    depth
                ORDER BY depth ASC, neighbor_name ASC
                LIMIT $max_results
            """

            params = {"entity_uuid": entity_uuid, "max_results": max_results}

            # Execute both queries
            async with self.client.driver.session() as session:
                # Get outgoing neighbors
                outgoing_result = await session.run(outgoing_query, params)
                outgoing_records = await outgoing_result.data()

                # Get incoming neighbors
                incoming_result = await session.run(incoming_query, params)
                incoming_records = await incoming_result.data()

            logger.info(
                f"Found {len(outgoing_records)} outgoing and {len(incoming_records)} incoming neighbors"
            )

            return {
                "outgoing": outgoing_records,
                "incoming": incoming_records,
            }

        except Exception as e:
            logger.error(f"Error getting neighbors via Cypher: {e}", exc_info=True)
            return {"outgoing": [], "incoming": []}

    async def _extract_source_from_episode(self, episode_key: str) -> Optional[dict]:
        """Extract source information from episode UUID or name.

        Args:
            episode_key: Episode UUID or name

        Returns:
            Dict with url, title, and date if found, else None
        """
        try:
            query = """
                MATCH (e:Episodic)
                WHERE e.uuid = $episode_key OR e.name = $episode_key
                RETURN e.uuid AS uuid, e.name AS name, e.source AS source,
                       e.source_description AS source_description
                LIMIT 1
            """

            async with self.client.driver.session() as session:
                result = await session.run(query, {"episode_key": episode_key})
                records = await result.data()

                if records:
                    record = records[0]
                    if record.get("name"):
                        source_info = self._parse_episodic_name(record["name"])
                        if source_info:
                            return source_info

                    # Fallback to source_description if available
                    if record.get("source_description"):
                        return {
                            "url": "",
                            "title": record["source_description"][:80],
                            "date": None,
                        }

        except Exception as e:
            logger.error(f"Error extracting source from episode: {e}")

        return None

    def _parse_episodic_name(self, name: str) -> Optional[dict]:
        """Parse Episodic node name to extract source information.

        Expected format: political_doc_YYYYMMDD_domain_title_timestamp_chunk_N

        Args:
            name: Episode name

        Returns:
            Dict with url, title, and date if parseable, else None
        """
        try:
            # Remove prefix
            if name.startswith("political_doc_"):
                name = name[14:]  # len("political_doc_")

            # Split by underscore
            parts = name.split("_")

            if len(parts) < 3:
                return None

            # Extract date (YYYYMMDD format)
            date_part = parts[0] if parts[0].isdigit() and len(parts[0]) == 8 else None

            # Extract domain (second part)
            domain_part = parts[1].replace("-", ".") if len(parts) > 1 else None

            if not domain_part:
                return None

            # Collect title parts (everything between domain and timestamp/chunk markers)
            title_parts = []
            for i in range(2, len(parts)):
                part = parts[i]

                # Stop at timestamp (8+ digits) or "chunk" marker
                if part.isdigit() and len(part) >= 8:
                    break
                if part == "chunk":
                    break

                title_parts.append(part)

            # Build title from parts
            title = " ".join(title_parts).replace("-", " ") if title_parts else ""

            # Construct URL
            url = f"https://{domain_part}"

            # Format display title
            if title:
                display_title = f"{domain_part}: {title[:60]}"
                if len(title) > 60:
                    display_title += "..."
            else:
                display_title = domain_part

            return {"url": url, "title": display_title, "date": date_part}

        except Exception as e:
            logger.error(f"Error parsing episodic name '{name}': {e}")
            return None

    def _run(
        self,
        entity_name: str,
        max_depth: int = 1,
        neighbor_types: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute synchronously - placeholder."""
        return "Sync not implemented - use async version"

    async def _arun(
        self,
        entity_name: str,
        max_depth: int = 1,
        neighbor_types: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Get neighbors of an entity using Neo4j Cypher queries.

        Args:
            entity_name: Name of the entity to find neighbors for
            max_depth: Maximum depth for neighbor discovery (default 1 for immediate neighbors)
            neighbor_types: DEPRECATED - parameter accepted for backwards compatibility but ignored
            run_manager: Optional callback manager

        Returns:
            Formatted string with neighbor information, separated by direction (outgoing/incoming)
        """
        try:
            logger.info(f"Getting neighbors for: {entity_name} (max_depth={max_depth})")

            # Step 1: Find entity node using smart Neo4j matching
            entity_node = await self._find_entity_node(entity_name)
            if not entity_node:
                return f"❌ Entity '{entity_name}' not found in knowledge graph.\n\nPlease verify the entity name or try a related search."

            entity_uuid = entity_node["uuid"]
            resolved_name = entity_node["name"]
            logger.info(f"Resolved entity: {resolved_name} (UUID: {entity_uuid})")

            # Step 2: Get neighbors using Cypher queries (bidirectional)
            neighbors = await self._get_neighbors_cypher(
                entity_uuid=entity_uuid,
                max_depth=max_depth,
                max_results=50,  # Limit per direction
            )

            outgoing = neighbors.get("outgoing", [])
            incoming = neighbors.get("incoming", [])

            # Check if any neighbors found
            if not outgoing and not incoming:
                return f"## Neighbors of: {resolved_name}\n\n❌ No direct neighbors found.\n\n**Suggestions**:\n- Entity may be isolated in the graph\n- Try increasing max_depth\n- Check if entity has relationships in the knowledge graph"

            # Step 3: Format output with separate sections for outgoing and incoming
            response = f"## Neighbors of: {resolved_name}\n\n"
            response += f"**Search Depth**: {max_depth} hop(s)\n"
            response += f"**Total Neighbors Found**: {len(outgoing) + len(incoming)} ({len(outgoing)} outgoing, {len(incoming)} incoming)\n\n"

            # Format outgoing neighbors (entity → neighbors)
            if outgoing:
                response += f"### Outgoing Relationships ({len(outgoing)} neighbors)\n"
                response += f"*{resolved_name} influences or relates to these entities:*\n\n"

                for idx, neighbor in enumerate(outgoing[:20], 1):  # Top 20
                    neighbor_name = neighbor["neighbor_name"]
                    neighbor_types = [
                        t for t in neighbor.get("neighbor_types", []) if t != "Entity"
                    ]
                    rel_chain = neighbor.get("relationship_chain", [])

                    # Extract relationship types from chain
                    rel_types = " → ".join(hop["type"] for hop in rel_chain)

                    response += f"{idx}. **{neighbor_name}**"
                    if neighbor_types:
                        response += f" *({', '.join(neighbor_types)})*"
                    response += f"\n   - Relationship: {rel_types}\n"

                    # Show fact from relationship
                    if rel_chain and rel_chain[0].get("fact"):
                        fact = rel_chain[0]["fact"]
                        fact_preview = fact[:120] + "..." if len(fact) > 120 else fact
                        response += f"   - Context: {fact_preview}\n"

                    response += "\n"

                if len(outgoing) > 20:
                    response += f"*... and {len(outgoing) - 20} more outgoing neighbors*\n\n"
            else:
                response += "### Outgoing Relationships (0)\n*No outgoing relationships found*\n\n"

            # Format incoming neighbors (neighbors → entity)
            if incoming:
                response += f"### Incoming Relationships ({len(incoming)} neighbors)\n"
                response += f"*These entities influence or relate to {resolved_name}:*\n\n"

                for idx, neighbor in enumerate(incoming[:20], 1):  # Top 20
                    neighbor_name = neighbor["neighbor_name"]
                    neighbor_types = [
                        t for t in neighbor.get("neighbor_types", []) if t != "Entity"
                    ]
                    rel_chain = neighbor.get("relationship_chain", [])

                    # Extract relationship types from chain
                    rel_types = " → ".join(hop["type"] for hop in rel_chain)

                    response += f"{idx}. **{neighbor_name}**"
                    if neighbor_types:
                        response += f" *({', '.join(neighbor_types)})*"
                    response += f"\n   - Relationship: {rel_types}\n"

                    # Show fact from relationship
                    if rel_chain and rel_chain[0].get("fact"):
                        fact = rel_chain[0]["fact"]
                        fact_preview = fact[:120] + "..." if len(fact) > 120 else fact
                        response += f"   - Context: {fact_preview}\n"

                    response += "\n"

                if len(incoming) > 20:
                    response += f"*... and {len(incoming) - 20} more incoming neighbors*\n\n"
            else:
                response += "### Incoming Relationships (0)\n*No incoming relationships found*\n\n"

            # Step 4: Add summary sections (like Tool 6)
            response += "---\n\n"
            response += "## Summary\n\n"

            # Collect unique entities
            all_neighbors = {}
            for neighbor in outgoing + incoming:
                uuid = neighbor["neighbor_uuid"]
                if uuid not in all_neighbors:
                    all_neighbors[uuid] = {
                        "name": neighbor["neighbor_name"],
                        "types": [t for t in neighbor.get("neighbor_types", []) if t != "Entity"],
                    }

            # 1. Entities Found
            response += f"### Entities Found ({len(all_neighbors)})\n"
            for neighbor_data in sorted(all_neighbors.values(), key=lambda x: x["name"])[:20]:
                types_str = (
                    f" ({', '.join(neighbor_data['types'])})" if neighbor_data["types"] else ""
                )
                response += f"- **{neighbor_data['name']}**{types_str}\n"
            if len(all_neighbors) > 20:
                response += f"- *... and {len(all_neighbors) - 20} more*\n"
            response += "\n"

            # 2. Relationships Discovered
            relationships_count = {}
            for neighbor in outgoing + incoming:
                rel_chain = neighbor.get("relationship_chain", [])
                for hop in rel_chain:
                    rel_type = hop["type"]
                    relationships_count[rel_type] = relationships_count.get(rel_type, 0) + 1

            response += f"### Relationships Discovered ({len(relationships_count)} types)\n"
            for rel_type, count in sorted(relationships_count.items(), key=lambda x: -x[1]):
                response += f"- **{rel_type}**: {count} occurrence(s)\n"
            response += "\n"

            # 3. Source Citations
            source_citations = []
            seen_sources = set()
            for neighbor in outgoing + incoming:
                rel_chain = neighbor.get("relationship_chain", [])
                for hop in rel_chain:
                    props = hop.get("properties", {})
                    if "source" in props or "episode" in props:
                        source_key = props.get("source", props.get("episode"))
                        if source_key and source_key not in seen_sources:
                            source_info = await self._extract_source_from_episode(source_key)
                            if source_info:
                                source_citations.append(source_info)
                                seen_sources.add(source_key)

            if source_citations:
                response += f"### Source Citations ({len(source_citations)})\n"
                for idx, source in enumerate(source_citations[:10], 1):
                    response += f"{idx}. {source['title']}\n"
                    if source["url"]:
                        response += f"   URL: {source['url']}\n"
                    if source.get("date"):
                        response += f"   Date: {source['date']}\n"
                if len(source_citations) > 10:
                    response += f"*... and {len(source_citations) - 10} more sources*\n"
                response += "\n"

            # 4. Temporal Aspects
            temporal_aspects = []
            seen_dates = set()
            for neighbor in outgoing + incoming:
                rel_chain = neighbor.get("relationship_chain", [])
                for hop in rel_chain:
                    props = hop.get("properties", {})
                    for key in ["created_at", "date", "timestamp", "valid_from"]:
                        if key in props and props[key]:
                            date_val = str(props[key])
                            if date_val not in seen_dates:
                                temporal_aspects.append(
                                    {
                                        "date": date_val,
                                        "relationship": hop["type"],
                                        "context": f"{hop['source_name']} → {hop['target_name']}",
                                    }
                                )
                                seen_dates.add(date_val)

            if temporal_aspects:
                response += f"### Temporal Aspects ({len(temporal_aspects)})\n"
                # Sort by date (most recent first)
                sorted_temporal = sorted(temporal_aspects, key=lambda x: x["date"], reverse=True)
                for aspect in sorted_temporal[:10]:
                    response += (
                        f"- **{aspect['date']}**: {aspect['relationship']} - {aspect['context']}\n"
                    )
                if len(temporal_aspects) > 10:
                    response += f"*... and {len(temporal_aspects) - 10} more temporal entries*\n"
                response += "\n"

            logger.info(
                f"Found {len(outgoing)} outgoing and {len(incoming)} incoming neighbors for {resolved_name}"
            )
            return response

        except Exception as e:
            logger.error(f"Error getting neighbors: {e}", exc_info=True)
            return f"❌ Error getting neighbors for {entity_name}: {str(e)}\n\nPlease check logs for details."


class ImpactAnalysisTool(BaseTool):
    """Tool for analyzing the impact network of an entity."""

    name: str = "analyze_entity_impact"
    description: str = "Analyze what entities are impacted by or impact the given entity. Shows regulatory/policy impact networks."
    args_schema: type[BaseModel] = ImpactAnalysisInput

    client: Graphiti = None

    def __init__(self, graphiti_client: Graphiti, **kwargs):
        super().__init__(**kwargs)
        self.client = graphiti_client

    class Config:
        arbitrary_types_allowed = True

    def _run(
        self,
        entity_name: str,
        impact_types: Optional[list[str]] = None,
        max_hops: int = 3,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute synchronously - placeholder."""
        return "Sync not implemented - use async version"

    async def _arun(
        self,
        entity_name: str,
        impact_types: Optional[list[str]] = None,
        max_hops: int = 3,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Analyze impact network of an entity."""
        try:
            logger.info(f"Analyzing impact network for: {entity_name}")

            # Build impact-focused search query
            impact_keywords = [
                "affects",
                "impacts",
                "influences",
                "regulates",
                "governs",
                "requires",
                "mandates",
                "applies to",
                "enforces",
            ]

            search_query = f"{entity_name} " + " ".join(impact_keywords)
            if impact_types:
                search_query += " " + " ".join(impact_types)

            # Use advanced search for impact analysis
            from graphiti_core.search.search_config_recipes import EDGE_HYBRID_SEARCH_RRF

            search_results = await self.client._search(search_query, config=EDGE_HYBRID_SEARCH_RRF)

            # Extract edges for impact analysis
            results = []
            if hasattr(search_results, "edges") and search_results.edges:
                results.extend(search_results.edges)

            if not results:
                return f"No impact information found for entity '{entity_name}'"

            # Categorize impacts
            direct_impacts = []  # Entity directly impacts others
            indirect_impacts = []  # Entity is impacted by others
            mutual_impacts = []  # Bidirectional relationships

            for result in results:
                fact = result.fact
                fact_lower = fact.lower()
                entity_lower = entity_name.lower()

                # Determine impact direction
                if entity_lower in fact_lower:
                    # Look for directional impact keywords
                    entity_pos = fact_lower.find(entity_lower)

                    # Check what comes after the entity mention
                    after_entity = fact_lower[entity_pos + len(entity_lower) :]
                    before_entity = fact_lower[:entity_pos]

                    impact_direction = "unclear"
                    if any(
                        keyword in after_entity
                        for keyword in ["affects", "impacts", "regulates", "governs"]
                    ):
                        impact_direction = "outbound"  # Entity impacts others
                    elif any(
                        keyword in before_entity
                        for keyword in ["affects", "impacts", "regulates", "governed by"]
                    ):
                        impact_direction = "inbound"  # Entity is impacted
                    elif any(
                        keyword in fact_lower
                        for keyword in ["mutual", "bidirectional", "interconnected"]
                    ):
                        impact_direction = "mutual"

                    impact_info = {
                        "fact": fact,
                        "direction": impact_direction,
                        "relationship": getattr(result, "name", "IMPACTS"),
                        "episodes": getattr(result, "episodes", []),
                    }

                    if impact_direction == "outbound":
                        direct_impacts.append(impact_info)
                    elif impact_direction == "inbound":
                        indirect_impacts.append(impact_info)
                    elif impact_direction == "mutual":
                        mutual_impacts.append(impact_info)
                    else:
                        # Default to direct impact if unclear
                        direct_impacts.append(impact_info)

            # Format impact analysis
            response = f"## Impact Analysis: {entity_name}\n\n"

            # Summary
            total_impacts = len(direct_impacts) + len(indirect_impacts) + len(mutual_impacts)
            response += f"**Total Impact Relationships**: {total_impacts}\n\n"

            # Direct impacts (what this entity affects)
            if direct_impacts:
                response += (
                    f"### What {entity_name} Impacts ({len(direct_impacts)} relationships):\n"
                )
                for i, impact in enumerate(direct_impacts[:8], 1):
                    response += f"{i}. {impact['fact']}\n"
                if len(direct_impacts) > 8:
                    response += f"... and {len(direct_impacts) - 8} more direct impacts\n"
                response += "\n"

            # Indirect impacts (what impacts this entity)
            if indirect_impacts:
                response += (
                    f"### What Impacts {entity_name} ({len(indirect_impacts)} relationships):\n"
                )
                for i, impact in enumerate(indirect_impacts[:8], 1):
                    response += f"{i}. {impact['fact']}\n"
                if len(indirect_impacts) > 8:
                    response += f"... and {len(indirect_impacts) - 8} more indirect impacts\n"
                response += "\n"

            # Mutual impacts
            if mutual_impacts:
                response += (
                    f"### Mutual/Bidirectional Impacts ({len(mutual_impacts)} relationships):\n"
                )
                for i, impact in enumerate(mutual_impacts[:5], 1):
                    response += f"{i}. {impact['fact']}\n"
                response += "\n"

            # Impact assessment
            if total_impacts > 0:
                response += "### Impact Assessment:\n"
                if len(direct_impacts) > len(indirect_impacts):
                    response += f"- **{entity_name} is primarily an influencer** - impacts more entities than it's impacted by\n"
                elif len(indirect_impacts) > len(direct_impacts):
                    response += f"- **{entity_name} is primarily influenced** - more impacted by other entities\n"
                else:
                    response += f"- **{entity_name} has balanced influence** - roughly equal inbound and outbound impacts\n"

                response += f"- **Network centrality**: {'High' if total_impacts > 10 else 'Medium' if total_impacts > 5 else 'Low'}\n"
            else:
                response += f"No clear impact relationships found for {entity_name}."

            logger.info(f"Impact analysis found {total_impacts} total impacts")
            return response

        except Exception as e:
            logger.error(f"Error in impact analysis: {e}")
            return f"Error analyzing impact for {entity_name}: {str(e)}"
