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
        default=None, description="Types of relationships to follow (e.g., ['AFFECTS', 'GOVERNS'])"
    )
    max_depth: int = Field(default=2, description="Maximum depth to traverse (1-3 recommended)")
    max_results: int = Field(default=15, description="Maximum number of results to return")


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
        default=None, description="Types of entities to focus on as neighbors"
    )


class ImpactAnalysisInput(BaseModel):
    """Input schema for impact analysis."""

    entity_name: str = Field(description="Entity to analyze impact for")
    impact_types: Optional[list[str]] = Field(
        default=None, description="Types of impact to focus on (e.g., ['regulatory', 'financial'])"
    )
    max_hops: int = Field(default=3, description="Maximum relationship hops to explore for impact")


class TraverseFromEntityTool(BaseTool):
    """Tool for traversing relationships from a specific entity."""

    name: str = "traverse_from_entity"
    description: str = "Follow relationships from an entity to explore connected entities. Shows the network expansion from a starting point."
    args_schema: type[BaseModel] = TraverseFromEntityInput

    client: Graphiti = None

    def __init__(self, graphiti_client: Graphiti, **kwargs):
        super().__init__(**kwargs)
        self.client = graphiti_client

    class Config:
        arbitrary_types_allowed = True

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
        relationship_types: Optional[list[str]] = None,
        max_depth: int = 2,
        max_results: int = 15,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Traverse relationships from an entity."""
        try:
            logger.info(f"Traversing from entity: {entity_name} (depth={max_depth})")

            # Build search query for traversal
            search_query = f"{entity_name}"
            if relationship_types:
                search_query += " " + " ".join(relationship_types)
            search_query += " connected related network influence affects"

            # Get initial results using advanced search
            from graphiti_core.search.search_config_recipes import EDGE_HYBRID_SEARCH_RRF

            search_results = await self.client._search(search_query, config=EDGE_HYBRID_SEARCH_RRF)

            # Extract edges for traversal analysis
            results = []
            if hasattr(search_results, "edges") and search_results.edges:
                results.extend(search_results.edges)

            if not results:
                return f"No connections found for entity '{entity_name}'"

            # Track traversed entities and relationships
            traversed_entities = set()
            relationships_found = []
            current_level_entities = {entity_name.lower()}

            # Multi-level traversal simulation
            for depth in range(max_depth):
                next_level_entities = set()

                for result in results[:max_results]:
                    fact = result.fact.lower()

                    # Check if this fact involves our current level entities
                    involves_current = any(entity in fact for entity in current_level_entities)

                    if involves_current:
                        # Extract relationship info
                        rel_type = getattr(result, "name", "CONNECTED_TO")

                        # Try to extract entity names from the fact
                        # This is simplified - in practice would use NER
                        import re

                        potential_entities = re.findall(
                            r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", result.fact
                        )

                        for entity in potential_entities:
                            if entity.lower() not in traversed_entities and len(entity) > 2:
                                next_level_entities.add(entity.lower())

                                relationships_found.append(
                                    {
                                        "depth": depth + 1,
                                        "type": rel_type,
                                        "fact": result.fact,
                                        "target_entity": entity,
                                        "episodes": getattr(result, "episodes", []),
                                    }
                                )

                # Update for next iteration
                traversed_entities.update(current_level_entities)
                current_level_entities = next_level_entities

                if not next_level_entities:
                    break

            # Format traversal results
            response = f"## Relationship Traversal from: {entity_name}\n\n"
            response += f"**Traversal Depth**: {max_depth} levels\n"
            response += f"**Entities Discovered**: {len(traversed_entities)}\n\n"

            # Group by depth
            depth_groups = {}
            for rel in relationships_found:
                depth = rel["depth"]
                if depth not in depth_groups:
                    depth_groups[depth] = []
                depth_groups[depth].append(rel)

            for depth in sorted(depth_groups.keys()):
                response += f"### Level {depth} Connections:\n"
                for rel in depth_groups[depth][:5]:  # Top 5 per level
                    response += (
                        f"- **{rel['target_entity']}** [{rel['type']}]: {rel['fact'][:100]}...\n"
                    )

                if len(depth_groups[depth]) > 5:
                    response += f"  ... and {len(depth_groups[depth]) - 5} more at this level\n"
                response += "\n"

            if not relationships_found:
                response += f"No clear relationship paths found from {entity_name} within {max_depth} levels."

            logger.info(
                f"Traversal found {len(relationships_found)} relationships across {len(depth_groups)} levels"
            )
            return response

        except Exception as e:
            logger.error(f"Error in traversal: {e}")
            return f"Error traversing from {entity_name}: {str(e)}"


class FindPathsTool(BaseTool):
    """Tool for finding connection paths between two entities."""

    name: str = "find_paths_between_entities"
    description: str = "Find connection paths between two entities, showing how they are related through intermediate entities."
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

    async def _arun(
        self,
        source_entity: str,
        target_entity: str,
        max_path_length: int = 4,
        max_paths: int = 5,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Find paths between two entities."""
        try:
            logger.info(f"Finding paths between: {source_entity} -> {target_entity}")

            # Search for facts mentioning both entities
            search_query = f"{source_entity} {target_entity} connection relationship path"

            # Use advanced search for path finding
            from graphiti_core.search.search_config_recipes import EDGE_HYBRID_SEARCH_RRF

            search_results = await self.client._search(search_query, config=EDGE_HYBRID_SEARCH_RRF)

            # Extract edges for path analysis
            results = []
            if hasattr(search_results, "edges") and search_results.edges:
                results.extend(search_results.edges)

            if not results:
                return f"No connection paths found between '{source_entity}' and '{target_entity}'"

            # Look for direct connections first
            direct_connections = []
            indirect_connections = []

            for result in results:
                fact = result.fact
                fact_lower = fact.lower()

                # Check if both entities are mentioned in the same fact
                if source_entity.lower() in fact_lower and target_entity.lower() in fact_lower:
                    direct_connections.append(
                        {
                            "type": "direct",
                            "fact": fact,
                            "relationship": getattr(result, "name", "CONNECTED"),
                            "episodes": getattr(result, "episodes", []),
                        }
                    )
                elif source_entity.lower() in fact_lower or target_entity.lower() in fact_lower:
                    # Potential intermediate connection
                    indirect_connections.append(
                        {
                            "type": "indirect",
                            "fact": fact,
                            "relationship": getattr(result, "name", "RELATED"),
                            "episodes": getattr(result, "episodes", []),
                        }
                    )

            # Format path analysis
            response = f"## Connection Paths: {source_entity} ↔ {target_entity}\n\n"

            if direct_connections:
                response += "### Direct Connections:\n"
                for i, conn in enumerate(direct_connections[:max_paths], 1):
                    response += f"{i}. **{conn['relationship']}**: {conn['fact']}\n"
                response += "\n"

            if indirect_connections:
                response += "### Potential Indirect Connections:\n"
                for i, conn in enumerate(indirect_connections[:max_paths], 1):
                    response += f"{i}. Via intermediate entities: {conn['fact'][:150]}...\n"
                response += "\n"

            if not direct_connections and not indirect_connections:
                response += f"No clear connection paths found between {source_entity} and {target_entity}.\n\n"
                response += "**Suggestions:**\n"
                response += "- Try using broader entity names or acronyms\n"
                response += "- Use traversal tools to explore each entity's network separately\n"
                response += "- Look for common policy areas or regulatory frameworks\n"

            # Add path strength analysis
            if direct_connections or indirect_connections:
                total_connections = len(direct_connections) + len(indirect_connections)
                response += "**Path Analysis:**\n"
                response += f"- Direct connections: {len(direct_connections)}\n"
                response += f"- Indirect connections: {len(indirect_connections)}\n"
                response += f"- Connection strength: {'Strong' if len(direct_connections) > 2 else 'Moderate' if total_connections > 2 else 'Weak'}\n"

            logger.info(
                f"Found {len(direct_connections)} direct and {len(indirect_connections)} indirect connections"
            )
            return response

        except Exception as e:
            logger.error(f"Error finding paths: {e}")
            return f"Error finding paths between {source_entity} and {target_entity}: {str(e)}"


class GetNeighborsTool(BaseTool):
    """Tool for getting immediate neighbors of an entity."""

    name: str = "get_entity_neighbors"
    description: str = "Get entities that are directly connected to the given entity. Shows the immediate network neighborhood."
    args_schema: type[BaseModel] = GetNeighborsInput

    client: Graphiti = None

    def __init__(self, graphiti_client: Graphiti, **kwargs):
        super().__init__(**kwargs)
        self.client = graphiti_client

    class Config:
        arbitrary_types_allowed = True

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
        """Get neighbors of an entity."""
        try:
            logger.info(f"Getting neighbors for: {entity_name}")

            # Search for immediate connections
            search_query = f"{entity_name} connected related involves affects regulates"
            if neighbor_types:
                search_query += " " + " ".join(neighbor_types)

            # Use advanced search for neighbor discovery
            from graphiti_core.search.search_config_recipes import EDGE_HYBRID_SEARCH_RRF

            search_results = await self.client._search(search_query, config=EDGE_HYBRID_SEARCH_RRF)

            # Extract edges for neighbor analysis
            results = []
            if hasattr(search_results, "edges") and search_results.edges:
                results.extend(search_results.edges)

            if not results:
                return f"No neighbors found for entity '{entity_name}'"

            # Extract neighbor entities
            neighbors = {}
            relationship_types = set()

            for result in results:
                fact = result.fact
                if entity_name.lower() in fact.lower():
                    # Extract potential neighbor entities
                    import re

                    potential_neighbors = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", fact)

                    rel_type = getattr(result, "name", "CONNECTED_TO")
                    relationship_types.add(rel_type)

                    for neighbor in potential_neighbors:
                        if neighbor.lower() != entity_name.lower() and len(neighbor) > 2:
                            # Filter by neighbor types if specified
                            if neighbor_types:
                                neighbor_matches = any(
                                    ntype.lower() in fact.lower() for ntype in neighbor_types
                                )
                                if not neighbor_matches:
                                    continue

                            if neighbor not in neighbors:
                                neighbors[neighbor] = []

                            neighbors[neighbor].append(
                                {
                                    "relationship": rel_type,
                                    "fact": fact,
                                    "episodes": getattr(result, "episodes", []),
                                }
                            )

            # Format neighbors response
            response = f"## Neighbors of: {entity_name}\n\n"

            if neighbors:
                response += f"**Found {len(neighbors)} neighboring entities**\n\n"

                # Sort by number of connections
                sorted_neighbors = sorted(neighbors.items(), key=lambda x: len(x[1]), reverse=True)

                response += "### Connected Entities:\n"
                for neighbor, connections in sorted_neighbors[:15]:  # Top 15 neighbors
                    response += f"**{neighbor}** ({len(connections)} connection(s))\n"

                    # Show relationship types
                    rel_types = set(conn["relationship"] for conn in connections)
                    response += f"  Relationships: {', '.join(rel_types)}\n"

                    # Show one example fact
                    if connections:
                        example_fact = connections[0]["fact"][:100] + "..."
                        response += f"  Example: {example_fact}\n"
                    response += "\n"

                # Summary of relationship types
                response += "### Relationship Types Found:\n"
                for rel_type in sorted(relationship_types):
                    count = sum(
                        1
                        for conns in neighbors.values()
                        for conn in conns
                        if conn["relationship"] == rel_type
                    )
                    response += f"- {rel_type}: {count} connections\n"

            else:
                response += f"No clear neighboring entities found for {entity_name}."

            logger.info(
                f"Found {len(neighbors)} neighbors with {len(relationship_types)} relationship types"
            )
            return response

        except Exception as e:
            logger.error(f"Error getting neighbors: {e}")
            return f"Error getting neighbors for {entity_name}: {str(e)}"


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
