"""Enhanced tool integration system for multi-agent orchestrator."""

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any, Optional

from graphiti_core import Graphiti

from ..tools.community import CommunityMembersTool, GetCommunitiesTool, PolicyClustersTool
from ..tools.entity import (
    EntityDetailsTool,
    EntityRelationshipsTool,
    EntityTimelineTool,
    SimilarEntitesTool,
)
from ..tools.search import GraphitiSearchTool
from ..tools.temporal import ConcurrentEventsTool, DateRangeSearchTool, PolicyEvolutionTool
from ..tools.traverse import FindPathsTool, ImpactAnalysisTool, TraverseFromEntityTool

logger = logging.getLogger(__name__)


class ToolIntegrationManager:
    """Manages knowledge graph tool integration with intelligent selection."""

    def __init__(self, graphiti_client: Graphiti):
        self.client = graphiti_client
        self.tools = {}
        self.tool_performance = {}
        self.tool_usage_patterns = {}
        self._initialize_tools()

    def _initialize_tools(self) -> None:
        """Initialize all available knowledge graph tools."""
        try:
            # Core search tools
            self.tools["search"] = GraphitiSearchTool(self.client)

            # Entity-focused tools
            self.tools["get_entity_details"] = EntityDetailsTool(self.client)
            self.tools["get_entity_relationships"] = EntityRelationshipsTool(self.client)
            self.tools["get_entity_timeline"] = EntityTimelineTool(self.client)
            self.tools["find_similar_entities"] = SimilarEntitesTool(self.client)

            # Graph traversal tools
            self.tools["traverse_from_entity"] = TraverseFromEntityTool(self.client)
            self.tools["find_paths_between_entities"] = FindPathsTool(self.client)
            self.tools["analyze_entity_impact"] = ImpactAnalysisTool(self.client)

            # Temporal analysis tools
            self.tools["search_by_date_range"] = DateRangeSearchTool(self.client)
            self.tools["find_concurrent_events"] = ConcurrentEventsTool(self.client)
            self.tools["track_policy_evolution"] = PolicyEvolutionTool(self.client)

            # Community and clustering tools
            self.tools["get_communities"] = GetCommunitiesTool(self.client)
            self.tools["get_community_members"] = CommunityMembersTool(self.client)
            self.tools["get_policy_clusters"] = PolicyClustersTool(self.client)

            logger.info(f"Initialized {len(self.tools)} knowledge graph tools")

        except ImportError as e:
            logger.warning(f"Some tools could not be imported: {e}")
            # Initialize basic tools that should always be available
            self.tools["search"] = GraphitiSearchTool(self.client)
            self.tools["get_entity_details"] = EntityDetailsTool(self.client)

    def get_tool_recommendations(
        self, intent: str, entities: list[str], complexity: str, strategy_type: str
    ) -> list[dict[str, Any]]:
        """Get intelligent tool recommendations based on query analysis."""

        recommendations = []

        # Normalize inputs for case-insensitive matching
        intent_lower = intent.lower()
        complexity_lower = complexity.lower()
        strategy_lower = strategy_type.lower()

        # Intent-based tool selection
        if intent_lower == "information seeking" or intent_lower == "information_seeking":
            if strategy_lower == "focused":
                recommendations.extend(
                    [
                        {
                            "tool_name": "search",
                            "parameters": {
                                "query": " ".join(entities[:2]),
                                "limit": 5,
                                "search_type": "comprehensive",
                            },
                            "purpose": "Find general information about key entities",
                            "priority": "high",
                            "estimated_time": 3.0,
                        }
                    ]
                )

                if entities:
                    recommendations.append(
                        {
                            "tool_name": "get_entity_details",
                            "parameters": {"entity_name": entities[0]},
                            "purpose": "Get comprehensive details about the primary entity",
                            "priority": "high",
                            "estimated_time": 2.0,
                        }
                    )

            elif strategy_lower == "comprehensive":
                recommendations.extend(
                    [
                        {
                            "tool_name": "search",
                            "parameters": {
                                "query": " ".join(entities),
                                "limit": 10,
                                "search_type": "comprehensive",
                            },
                            "purpose": "Comprehensive search across all mentioned entities",
                            "priority": "high",
                            "estimated_time": 4.0,
                        },
                        {
                            "tool_name": "get_entity_relationships",
                            "parameters": {"entity_name": entities[0], "max_relationships": 15},
                            "purpose": "Explore relationships to understand context",
                            "priority": "medium",
                            "estimated_time": 3.0,
                        },
                        {
                            "tool_name": "find_similar_entities",
                            "parameters": {"entity_name": entities[0], "max_similar": 8},
                            "purpose": "Find related entities for broader context",
                            "priority": "medium",
                            "estimated_time": 2.5,
                        },
                    ]
                )

        elif intent_lower == "relationship_analysis" or intent_lower == "relationship analysis":
            if len(entities) >= 2:
                recommendations.extend(
                    [
                        {
                            "tool_name": "find_paths_between_entities",
                            "parameters": {
                                "start_entity": entities[0],
                                "end_entity": entities[1],
                                "max_hops": 3,
                            },
                            "purpose": "Find connection paths between entities",
                            "priority": "high",
                            "estimated_time": 4.0,
                        },
                        {
                            "tool_name": "search",
                            "parameters": {
                                "query": f"{entities[0]} {entities[1]}",
                                "search_type": "relationship_focused",
                            },
                            "purpose": "Search for relationship-specific information",
                            "priority": "high",
                            "estimated_time": 3.0,
                        },
                    ]
                )
            else:
                recommendations.append(
                    {
                        "tool_name": "get_entity_relationships",
                        "parameters": {"entity_name": entities[0], "max_relationships": 20},
                        "purpose": "Explore all relationships for the entity",
                        "priority": "high",
                        "estimated_time": 3.5,
                    }
                )

        elif intent_lower == "temporal_analysis" or intent_lower == "temporal analysis":
            recommendations.extend(
                [
                    {
                        "tool_name": "get_entity_timeline",
                        "parameters": {"entity_name": entities[0], "days_back": 365},
                        "purpose": "Analyze temporal evolution of the entity",
                        "priority": "high",
                        "estimated_time": 4.0,
                    },
                    {
                        "tool_name": "search_by_date_range",
                        "parameters": {"query": " ".join(entities), "days_back": 180},
                        "purpose": "Find recent developments",
                        "priority": "medium",
                        "estimated_time": 3.0,
                    },
                ]
            )

            if "policy" in " ".join(entities).lower():
                recommendations.append(
                    {
                        "tool_name": "track_policy_evolution",
                        "parameters": {"policy_name": entities[0]},
                        "purpose": "Track how the policy has evolved over time",
                        "priority": "high",
                        "estimated_time": 5.0,
                    }
                )

        elif intent_lower == "impact_analysis" or intent_lower == "impact analysis":
            recommendations.extend(
                [
                    {
                        "tool_name": "analyze_entity_impact",
                        "parameters": {"entity_name": entities[0], "max_hops": 2},
                        "purpose": "Analyze the broader impact network",
                        "priority": "high",
                        "estimated_time": 4.5,
                    },
                    {
                        "tool_name": "get_communities",
                        "parameters": {"entity_name": entities[0]},
                        "purpose": "Find communities and clusters affected",
                        "priority": "medium",
                        "estimated_time": 3.0,
                    },
                ]
            )

        # Complexity adjustments
        if complexity_lower == "simple":
            # Limit to top 2 recommendations for simple queries
            recommendations = recommendations[:2]
        elif complexity_lower == "complex":
            # Add more comprehensive tools for complex queries
            if intent_lower in [
                "information_seeking",
                "information seeking",
                "relationship_analysis",
                "relationship analysis",
            ]:
                recommendations.append(
                    {
                        "tool_name": "get_policy_clusters",
                        "parameters": {"entity_name": entities[0] if entities else ""},
                        "purpose": "Identify related policy clusters",
                        "priority": "low",
                        "estimated_time": 2.0,
                    }
                )

        # Sort by priority and estimated success rate
        priority_order = {"high": 3, "medium": 2, "low": 1}
        recommendations.sort(
            key=lambda x: (
                priority_order.get(x["priority"], 0),
                -x["estimated_time"],  # Prefer faster tools for tie-breaking
            ),
            reverse=True,
        )

        return recommendations

    async def execute_tool_sequence(
        self, tool_sequence: list[dict[str, Any]], progress_callback: Optional[Callable] = None
    ) -> list[dict[str, Any]]:
        """Execute a sequence of tools with intelligent error handling."""

        results = []

        for i, tool_config in enumerate(tool_sequence):
            tool_name = tool_config["tool_name"]
            parameters = tool_config["parameters"]

            if progress_callback:
                await progress_callback(
                    {
                        "tool_execution": f"Executing {tool_name}...",
                        "progress": f"{i+1}/{len(tool_sequence)}",
                        "tool_name": tool_name,
                        "purpose": tool_config.get("purpose", ""),
                    }
                )

            start_time = datetime.now()

            try:
                if tool_name in self.tools:
                    tool = self.tools[tool_name]

                    # Execute tool
                    if hasattr(tool, "_arun"):
                        result = await tool._arun(**parameters)
                    else:
                        # Fallback to sync execution in thread pool
                        loop = asyncio.get_event_loop()
                        result = await loop.run_in_executor(None, lambda: tool._run(**parameters))

                    execution_time = (datetime.now() - start_time).total_seconds()

                    # Structure the result
                    structured_result = {
                        "tool_name": tool_name,
                        "success": True,
                        "execution_time": execution_time,
                        "parameters_used": parameters,
                        "raw_output": result,
                        "insights": self._extract_insights_from_result(result, tool_name),
                        "entities_found": self._extract_entities_from_result(result),
                        "relationships_discovered": self._extract_relationships_from_result(result),
                        "source_citations": self._extract_sources_from_result(result),
                        "temporal_aspects": self._extract_temporal_info(result),
                        "quality_score": self._assess_result_quality(result, tool_name),
                        "purpose": tool_config.get("purpose", ""),
                        "error": None,
                    }

                    results.append(structured_result)

                    # Update tool performance
                    self._update_tool_performance(tool_name, True, execution_time, None)

                    if progress_callback:
                        await progress_callback(
                            {
                                "tool_execution": f"Completed {tool_name}: ✓",
                                "tool_name": tool_name,
                                "success": True,
                                "execution_time": execution_time,
                            }
                        )

                else:
                    # Tool not available
                    error_msg = f"Tool {tool_name} not available"
                    results.append(
                        {
                            "tool_name": tool_name,
                            "success": False,
                            "execution_time": 0.0,
                            "parameters_used": parameters,
                            "raw_output": {},
                            "insights": [],
                            "entities_found": [],
                            "relationships_discovered": [],
                            "source_citations": [],
                            "temporal_aspects": [],
                            "quality_score": 0.0,
                            "purpose": tool_config.get("purpose", ""),
                            "error": error_msg,
                        }
                    )

                    self._update_tool_performance(tool_name, False, 0.0, error_msg)

            except Exception as e:
                execution_time = (datetime.now() - start_time).total_seconds()
                error_msg = str(e)

                results.append(
                    {
                        "tool_name": tool_name,
                        "success": False,
                        "execution_time": execution_time,
                        "parameters_used": parameters,
                        "raw_output": {},
                        "insights": [f"Tool execution failed: {error_msg}"],
                        "entities_found": [],
                        "relationships_discovered": [],
                        "source_citations": [],
                        "temporal_aspects": [],
                        "quality_score": 0.0,
                        "purpose": tool_config.get("purpose", ""),
                        "error": error_msg,
                    }
                )

                self._update_tool_performance(tool_name, False, execution_time, error_msg)

                if progress_callback:
                    await progress_callback(
                        {
                            "tool_execution": f"Failed {tool_name}: ✗",
                            "tool_name": tool_name,
                            "success": False,
                            "error": error_msg,
                        }
                    )

                # Continue with other tools unless it's a critical failure
                logger.error(f"Tool {tool_name} failed: {error_msg}")

        return results

    def _extract_insights_from_result(self, result: Any, tool_name: str) -> list[str]:
        """Extract key insights from tool result."""
        insights = []

        if isinstance(result, dict):
            # Handle different result structures based on tool type
            if "nodes" in result:
                insights.append(f"Found {len(result['nodes'])} relevant entities")
            if "edges" in result:
                insights.append(f"Discovered {len(result['edges'])} relationships")
            if "summary" in result:
                insights.append(result["summary"])
        elif isinstance(result, str) and result:
            # Extract first sentence as insight
            sentences = result.split(".")
            if sentences:
                insights.append(sentences[0].strip())

        return insights[:3]  # Limit to top 3 insights

    def _extract_entities_from_result(self, result: Any) -> list[dict[str, str]]:
        """Extract entities from tool result."""
        entities = []

        if isinstance(result, dict) and "nodes" in result:
            for node in result["nodes"][:10]:  # Limit to 10 entities
                if isinstance(node, dict):
                    entities.append(
                        {
                            "name": node.get("name", "Unknown"),
                            "type": node.get("type", "Entity"),
                            "relevance": "high",
                        }
                    )

        return entities

    def _extract_relationships_from_result(self, result: Any) -> list[dict[str, str]]:
        """Extract relationships from tool result."""
        relationships = []

        if isinstance(result, dict) and "edges" in result:
            for edge in result["edges"][:10]:  # Limit to 10 relationships
                if isinstance(edge, dict):
                    relationships.append(
                        {
                            "source": edge.get("source", "Unknown"),
                            "target": edge.get("target", "Unknown"),
                            "relationship": edge.get("relationship", "RELATED_TO"),
                        }
                    )

        return relationships

    def _extract_sources_from_result(self, result: Any) -> list[str]:
        """Extract source citations from tool result."""
        sources = []

        if isinstance(result, dict):
            if "sources" in result:
                sources.extend(result["sources"])
            elif "episodes" in result:
                # Extract episode sources
                for episode in result["episodes"][:5]:
                    if isinstance(episode, dict) and "source" in episode:
                        sources.append(episode["source"])

        return list(set(sources))  # Remove duplicates

    def _extract_temporal_info(self, result: Any) -> list[str]:
        """Extract temporal information from tool result."""
        temporal_info = []

        if isinstance(result, dict):
            if "timeline" in result:
                temporal_info.append("Timeline data available")
            if "date_range" in result:
                temporal_info.append(f"Date range: {result['date_range']}")

        return temporal_info

    def _assess_result_quality(self, result: Any, tool_name: str) -> float:
        """Assess the quality of tool result."""
        if not result:
            return 0.0

        quality_score = 0.5  # Base score

        if isinstance(result, dict):
            # Check for rich content
            if result.get("nodes"):
                quality_score += 0.2
            if result.get("edges"):
                quality_score += 0.2
            if result.get("summary"):
                quality_score += 0.1
        elif isinstance(result, str) and len(result) > 50:
            quality_score += 0.3

        return min(1.0, quality_score)

    def _update_tool_performance(
        self, tool_name: str, success: bool, execution_time: float, error: Optional[str]
    ) -> None:
        """Update tool performance metrics."""
        if tool_name not in self.tool_performance:
            self.tool_performance[tool_name] = {
                "total_executions": 0,
                "successes": 0,
                "avg_execution_time": 0.0,
                "recent_errors": [],
            }

        perf = self.tool_performance[tool_name]
        perf["total_executions"] += 1

        if success:
            perf["successes"] += 1
        else:
            if error:
                perf["recent_errors"].append(error)
                # Keep only last 5 errors
                perf["recent_errors"] = perf["recent_errors"][-5:]

        # Update average execution time
        total_time = perf["avg_execution_time"] * (perf["total_executions"] - 1)
        perf["avg_execution_time"] = (total_time + execution_time) / perf["total_executions"]

    def get_available_tools(self) -> dict[str, str]:
        """Get list of available tools with descriptions."""
        return {name: tool.description for name, tool in self.tools.items()}

    def get_tool_performance_summary(self) -> dict[str, dict[str, Any]]:
        """Get performance summary for all tools."""
        summary = {}
        for tool_name, perf in self.tool_performance.items():
            success_rate = perf["successes"] / max(1, perf["total_executions"])
            summary[tool_name] = {
                "success_rate": success_rate,
                "avg_execution_time": perf["avg_execution_time"],
                "total_executions": perf["total_executions"],
                "reliability": "high"
                if success_rate > 0.9
                else "medium"
                if success_rate > 0.7
                else "low",
            }
        return summary
