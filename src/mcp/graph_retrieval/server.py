"""
Graph Context Retrieval MCP Server.

FastAPI server with SSE transport for Claude.ai integration.
Provides knowledge graph querying capabilities via MCP protocol.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent

from .retriever import (
    GraphContextRetriever,
    Neo4jConfig,
    QueryAnalyzer,
    ToolPlanner,
)

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
retriever: GraphContextRetriever = None
mcp_server = Server("graph-context-retrieval")


# =============================================================================
# Pydantic Models
# =============================================================================

class HealthResponse(BaseModel):
    status: str
    server: str
    neo4j_uri: str
    neo4j_database: str
    neo4j_status: str


class SearchRequest(BaseModel):
    query: str


class EntityRequest(BaseModel):
    entity_name: str
    max_results: int = 10


# =============================================================================
# MCP Server Tools
# =============================================================================

@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="search_knowledge_graph",
            description="Search the political monitoring knowledge graph for information about regulations, policies, politicians, organizations, and legislative activities.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query to search the knowledge graph"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="analyze_query",
            description="Analyze a query to understand its intent, extract entities, and determine the best retrieval strategy.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Query to analyze"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_entity_info",
            description="Get detailed information about a specific entity in the knowledge graph.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_name": {
                        "type": "string",
                        "description": "Name of the entity to look up"
                    }
                },
                "required": ["entity_name"]
            }
        ),
        Tool(
            name="find_relationships",
            description="Find relationships and connections for an entity in the knowledge graph.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_name": {
                        "type": "string",
                        "description": "Name of the entity to find relationships for"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of relationships to return",
                        "default": 10
                    }
                },
                "required": ["entity_name"]
            }
        ),
        Tool(
            name="graph_statistics",
            description="Get statistics about the knowledge graph (node counts, entity types, etc.).",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="search_documents",
            description="Search source documents (episodic nodes) in the knowledge graph using semantic similarity. Returns document chunks that are relevant to the query.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to find relevant documents"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of documents to return",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        # Temporal Analysis Tools
        Tool(
            name="search_by_date_range",
            description="Search for events, policies, or regulatory changes within a specific date range. Returns results filtered and scored by temporal relevance. Use for questions like 'What happened between [date] and [date]?'",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to find relevant content within the date range"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": 10
                    }
                },
                "required": ["query", "start_date", "end_date"]
            }
        ),
        Tool(
            name="get_entity_history",
            description="Track the historical evolution of an entity over time. Shows how an entity has changed, been mentioned, or evolved. Use for questions like 'How has [entity] changed over the past year?'",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_name": {
                        "type": "string",
                        "description": "Name of the entity to track history for"
                    },
                    "days_back": {
                        "type": "integer",
                        "description": "Number of days back to search",
                        "default": 365
                    },
                    "event_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Types of events to focus on (e.g., 'regulatory', 'enforcement', 'amendment')"
                    }
                },
                "required": ["entity_name"]
            }
        ),
        Tool(
            name="find_concurrent_events",
            description="Find events that occurred around a specific reference date. Useful for understanding what else was happening during a particular time. Use for questions like 'What else happened around [date]?'",
            inputSchema={
                "type": "object",
                "properties": {
                    "reference_date": {
                        "type": "string",
                        "description": "Reference date in YYYY-MM-DD format"
                    },
                    "window_days": {
                        "type": "integer",
                        "description": "Number of days before and after to search",
                        "default": 30
                    },
                    "event_context": {
                        "type": "string",
                        "description": "Context or theme to focus on (e.g., 'data protection', 'AI regulation')"
                    }
                },
                "required": ["reference_date"]
            }
        ),
        Tool(
            name="compare_timelines",
            description="Compare the timelines of multiple entities to see how they evolved in parallel. Use for questions like 'Compare the development of [entity1] and [entity2]'",
            inputSchema={
                "type": "object",
                "properties": {
                    "entities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of entity names to compare (2-5 entities)"
                    },
                    "time_period": {
                        "type": "integer",
                        "description": "Time period in days to compare",
                        "default": 365
                    },
                    "comparison_focus": {
                        "type": "string",
                        "description": "Specific aspect to focus comparison on"
                    }
                },
                "required": ["entities"]
            }
        ),
        Tool(
            name="track_policy_evolution",
            description="Track how a policy or regulation has evolved over time, including amendments, enforcement actions, and implementation phases. Use for questions like 'How has [policy] evolved since [date]?'",
            inputSchema={
                "type": "object",
                "properties": {
                    "policy_name": {
                        "type": "string",
                        "description": "Name of the policy to track (e.g., 'GDPR', 'AI Act', 'DSA')"
                    },
                    "evolution_period": {
                        "type": "integer",
                        "description": "Period in days to track evolution",
                        "default": 730
                    },
                    "evolution_aspects": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Aspects to track (e.g., 'amendments', 'enforcement', 'compliance')"
                    }
                },
                "required": ["policy_name"]
            }
        ),
        # =============================================================================
        # Community Detection Tools
        # =============================================================================
        Tool(
            name="get_communities",
            description="Discover communities and clusters of related entities in the knowledge graph. Shows groups of policies, organizations, or topics that are closely connected. Use for questions like 'What are the main clusters of EU regulations?' or 'Find communities of related policy areas'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic_focus": {
                        "type": "string",
                        "description": "Topic or theme to focus community search on (e.g., 'AI regulation', 'data privacy')"
                    },
                    "max_communities": {
                        "type": "integer",
                        "description": "Maximum number of communities to return",
                        "default": 5
                    },
                    "min_community_size": {
                        "type": "integer",
                        "description": "Minimum number of entities per community",
                        "default": 3
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_community_members",
            description="Get the members of a specific community or cluster. Shows entities that belong to the same thematic group. Use for questions like 'Who are the members of the data protection community?' or 'Show entities in the AI regulation cluster'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "community_topic": {
                        "type": "string",
                        "description": "Topic or theme that defines the community"
                    },
                    "max_members": {
                        "type": "integer",
                        "description": "Maximum number of community members to return",
                        "default": 10
                    },
                    "member_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Types of entities to focus on (e.g., ['Policy', 'Company', 'Organization'])"
                    }
                },
                "required": ["community_topic"]
            }
        ),
        Tool(
            name="get_policy_clusters",
            description="Identify clusters of related policies and regulations. Groups policies by theme, jurisdiction, or time period. Use for questions like 'Group EU regulations by theme' or 'Find policy clusters by jurisdiction'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "policy_area": {
                        "type": "string",
                        "description": "Policy area to focus on (e.g., 'digital', 'environmental', 'financial')"
                    },
                    "cluster_method": {
                        "type": "string",
                        "description": "Clustering method: 'thematic', 'jurisdictional', or 'temporal'",
                        "default": "thematic"
                    },
                    "max_clusters": {
                        "type": "integer",
                        "description": "Maximum number of policy clusters to return",
                        "default": 5
                    }
                },
                "required": []
            }
        ),
        # =============================================================================
        # Graph Traversal Tools
        # =============================================================================
        Tool(
            name="traverse_from_entity",
            description="Follow ALL relationships from an entity to explore connected entities, with intelligent relevance filtering to show the most important connections. Returns results ranked by relationship importance, path distance, and context richness. Use for questions like 'What entities are connected to GDPR within 2 hops?' or 'Explore the regulatory network around AI Act'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_name": {
                        "type": "string",
                        "description": "Starting entity to traverse from"
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum depth to traverse (1-3 recommended)",
                        "default": 2
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of most relevant results to return",
                        "default": 15
                    }
                },
                "required": ["entity_name"]
            }
        ),
        Tool(
            name="find_paths_between_entities",
            description="Find actual connection paths between two entities using Neo4j graph algorithms (shortestPath, allShortestPaths). Shows complete path chains with intermediate entities, relationship types, and contextual facts. Use for questions like 'How is the AI Act connected to GDPR?' or 'Find the path between European Commission and DSA'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_entity": {
                        "type": "string",
                        "description": "Source entity to start from"
                    },
                    "target_entity": {
                        "type": "string",
                        "description": "Target entity to find paths to"
                    },
                    "max_path_length": {
                        "type": "integer",
                        "description": "Maximum path length to search",
                        "default": 4
                    },
                    "max_paths": {
                        "type": "integer",
                        "description": "Maximum number of paths to return",
                        "default": 5
                    }
                },
                "required": ["source_entity", "target_entity"]
            }
        ),
        Tool(
            name="get_entity_neighbors",
            description="Get ALL entities directly connected to the given entity using Neo4j Cypher queries. Returns neighbors separated by direction (outgoing: entity → neighbors, incoming: neighbors → entity). Use for questions like 'What entities are directly related to the European Parliament?' or 'Find immediate connections to NIS2 Directive'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_name": {
                        "type": "string",
                        "description": "Entity to find neighbors for"
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Depth of neighbors to explore (1-2 recommended)",
                        "default": 1
                    }
                },
                "required": ["entity_name"]
            }
        ),
        Tool(
            name="analyze_entity_impact",
            description="Analyze what entities are impacted by or impact the given entity. Shows regulatory/policy impact networks. Use for questions like 'What is the impact network of GDPR?' or 'What entities are affected by the AI Act?'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_name": {
                        "type": "string",
                        "description": "Entity to analyze impact for"
                    },
                    "impact_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Types of impact to focus on (e.g., ['regulatory', 'financial', 'operational'])"
                    },
                    "max_hops": {
                        "type": "integer",
                        "description": "Maximum relationship hops to explore for impact",
                        "default": 3
                    }
                },
                "required": ["entity_name"]
            }
        ),
        # =============================================================================
        # Similarity Tool
        # =============================================================================
        Tool(
            name="find_similar_entities",
            description="Find entities that are similar or related to the given entity based on graph structure and context. Use for questions like 'Find regulations similar to GDPR' or 'What entities are structurally similar to the European Commission?'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_name": {
                        "type": "string",
                        "description": "Name of the entity to find similar entities for"
                    },
                    "max_similar": {
                        "type": "integer",
                        "description": "Maximum number of similar entities to return",
                        "default": 5
                    }
                },
                "required": ["entity_name"]
            }
        )
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle MCP tool calls."""
    try:
        logger.info(f"Tool called: {name} with args: {arguments}")

        if name == "search_knowledge_graph":
            return await handle_search(arguments["query"])
        elif name == "analyze_query":
            return await handle_analyze(arguments["query"])
        elif name == "get_entity_info":
            return await handle_entity_info(arguments["entity_name"])
        elif name == "find_relationships":
            return await handle_relationships(
                arguments["entity_name"],
                arguments.get("max_results", 10)
            )
        elif name == "graph_statistics":
            return await handle_statistics()
        elif name == "search_documents":
            return await handle_search_documents(
                arguments["query"],
                arguments.get("limit", 5)
            )
        # Temporal Tools
        elif name == "search_by_date_range":
            return await handle_search_by_date_range(
                arguments["query"],
                arguments["start_date"],
                arguments["end_date"],
                arguments.get("max_results", 10)
            )
        elif name == "get_entity_history":
            return await handle_get_entity_history(
                arguments["entity_name"],
                arguments.get("days_back", 365),
                arguments.get("event_types")
            )
        elif name == "find_concurrent_events":
            return await handle_find_concurrent_events(
                arguments["reference_date"],
                arguments.get("window_days", 30),
                arguments.get("event_context")
            )
        elif name == "compare_timelines":
            return await handle_compare_timelines(
                arguments["entities"],
                arguments.get("time_period", 365),
                arguments.get("comparison_focus")
            )
        elif name == "track_policy_evolution":
            return await handle_track_policy_evolution(
                arguments["policy_name"],
                arguments.get("evolution_period", 730),
                arguments.get("evolution_aspects")
            )
        # Community Detection Tools
        elif name == "get_communities":
            return await handle_get_communities(
                arguments.get("topic_focus"),
                arguments.get("max_communities", 5),
                arguments.get("min_community_size", 3)
            )
        elif name == "get_community_members":
            return await handle_get_community_members(
                arguments["community_topic"],
                arguments.get("max_members", 10),
                arguments.get("member_types")
            )
        elif name == "get_policy_clusters":
            return await handle_get_policy_clusters(
                arguments.get("policy_area"),
                arguments.get("cluster_method", "thematic"),
                arguments.get("max_clusters", 5)
            )
        # Graph Traversal Tools
        elif name == "traverse_from_entity":
            return await handle_traverse_from_entity(
                arguments["entity_name"],
                arguments.get("max_depth", 2),
                arguments.get("max_results", 15)
            )
        elif name == "find_paths_between_entities":
            return await handle_find_paths_between_entities(
                arguments["source_entity"],
                arguments["target_entity"],
                arguments.get("max_path_length", 4),
                arguments.get("max_paths", 5)
            )
        elif name == "get_entity_neighbors":
            return await handle_get_entity_neighbors(
                arguments["entity_name"],
                arguments.get("max_depth", 1)
            )
        elif name == "analyze_entity_impact":
            return await handle_analyze_entity_impact(
                arguments["entity_name"],
                arguments.get("impact_types"),
                arguments.get("max_hops", 3)
            )
        # Similarity Tool
        elif name == "find_similar_entities":
            return await handle_find_similar_entities(
                arguments["entity_name"],
                arguments.get("max_similar", 5)
            )
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        logger.error(f"Tool error: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_search(query: str) -> list[TextContent]:
    """Handle search_knowledge_graph tool."""
    logger.info(f"Searching for: {query}")
    context = await retriever.retrieve(query)
    result = retriever.to_dict(context)
    
    output = []
    output.append(f"## Query Analysis")
    output.append(f"- **Intent**: {result['query_understanding']['intent']}")
    output.append(f"- **Entities**: {', '.join(result['query_understanding']['entities_identified']) or 'None detected'}")
    output.append(f"- **Strategy**: {result['execution_summary']['strategy']}")
    output.append(f"- **Confidence**: {result['metadata']['confidence_assessment']}")
    output.append("")
    
    if result['retrieved_context']['facts']:
        output.append(f"## Facts ({result['metadata']['total_facts']})")
        for fact in result['retrieved_context']['facts'][:10]:
            content = fact['content'][:200] + "..." if len(fact['content']) > 200 else fact['content']
            output.append(f"- {content}")
        output.append("")
    
    if result['retrieved_context']['entities']:
        output.append(f"## Entities ({result['metadata']['total_entities']})")
        for entity in result['retrieved_context']['entities'][:10]:
            uuid_str = f" [UUID: {entity['uuid']}]" if entity.get('uuid') else ""
            summary = f" - {entity['summary'][:100]}..." if entity.get('summary') and len(entity['summary']) > 100 else (f" - {entity['summary']}" if entity.get('summary') else "")
            output.append(f"- **{entity['name']}** ({entity['type']}){uuid_str}{summary}")
        output.append("")
    
    if result['retrieved_context']['relationships']:
        output.append(f"## Relationships ({result['metadata']['total_relationships']})")
        for rel in result['retrieved_context']['relationships'][:5]:
            output.append(f"- {rel['source']} --[{rel['type']}]--> {rel['target']}")
        output.append("")

    # Include source documents (episodes) if available
    if result.get('sources'):
        output.append(f"## Source Documents ({len(result['sources'])})")
        for i, source in enumerate(result['sources'][:5], 1):
            name = source.get('name', 'Unknown')
            preview = source.get('content_preview', '')[:150]
            if len(source.get('content_preview', '')) > 150:
                preview += "..."
            source_desc = source.get('source_description', '')
            output.append(f"{i}. **{name}**")
            if source_desc:
                output.append(f"   Source: {source_desc}")
            if preview:
                output.append(f"   Preview: {preview}")

    return [TextContent(type="text", text="\n".join(output))]


async def handle_analyze(query: str) -> list[TextContent]:
    """Handle analyze_query tool."""
    analyzer = QueryAnalyzer()
    planner = ToolPlanner()
    
    analysis = analyzer.analyze(query)
    plan = planner.create_plan(analysis)
    
    output = [
        f"## Query Analysis",
        f"- **Original Query**: {query}",
        f"- **Intent**: {analysis.intent.value}",
        f"- **Entities**: {', '.join(analysis.entities) or 'None detected'}",
        f"- **Temporal Scope**: {analysis.temporal_scope or 'None'}",
        f"- **Complexity**: {analysis.complexity}",
        f"- **Domain Hints**: {', '.join(analysis.domain_hints) or 'None'}",
        "",
        f"## Execution Plan",
        f"- **Strategy**: {plan.strategy.value}",
        f"- **Estimated Time**: {plan.estimated_time:.1f}s",
        f"- **Tools**:"
    ]
    
    for i, tool in enumerate(plan.tools, 1):
        output.append(f"  {i}. **{tool['tool_name']}** ({tool['priority']}) - {tool['purpose']}")
    
    return [TextContent(type="text", text="\n".join(output))]


async def handle_entity_info(entity_name: str) -> list[TextContent]:
    """Handle get_entity_info tool."""
    await retriever.executor.initialize()
    result = await retriever.executor._get_entity_details({"entity_name": entity_name})
    
    if "error" in result:
        return [TextContent(type="text", text=f"Entity not found: {entity_name}")]
    
    output = [
        f"## {result.get('name', entity_name)}",
        f"- **Type**: {', '.join(result.get('labels', ['Unknown']))}",
        f"- **UUID**: {result.get('uuid', 'N/A')}",
    ]
    
    if result.get('summary'):
        output.append(f"- **Summary**: {result['summary']}")
    
    return [TextContent(type="text", text="\n".join(output))]


async def handle_relationships(entity_name: str, max_results: int) -> list[TextContent]:
    """Handle find_relationships tool."""
    await retriever.executor.initialize()
    result = await retriever.executor._get_entity_relationships({
        "entity_name": entity_name,
        "max_relationships": max_results
    })
    
    relationships = result.get("relationships", [])
    
    if not relationships:
        return [TextContent(type="text", text=f"No relationships found for: {entity_name}")]
    
    output = [f"## Relationships for {entity_name}", ""]

    for rel in relationships:
        fact_text = f"\n  > {rel['fact']}" if rel.get('fact') else ""
        source_uuid = f" [UUID: {rel['source_uuid']}]" if rel.get('source_uuid') else ""
        target_uuid = f" [UUID: {rel['target_uuid']}]" if rel.get('target_uuid') else ""
        output.append(f"- **{rel['source']}**{source_uuid} --[{rel['relationship']}]--> **{rel['target']}**{target_uuid}{fact_text}")
    
    return [TextContent(type="text", text="\n".join(output))]


async def handle_search_documents(query: str, limit: int = 5) -> list[TextContent]:
    """Handle search_documents tool - semantic search over episodic nodes."""
    logger.info(f"Searching documents for: {query}")
    await retriever.executor.initialize()

    result = await retriever.executor._search_episodes({
        "query": query,
        "limit": limit
    })

    episodes = result.get("episodes", [])

    if not episodes:
        return [TextContent(type="text", text=f"No documents found for: {query}")]

    output = [f"## Source Documents for: {query}", ""]

    for i, ep in enumerate(episodes, 1):
        name = ep.get('name', 'Unknown')
        content = ep.get('content', '')
        source_desc = ep.get('source_description', '')
        date = ep.get('valid_at', '') or ep.get('created_at', '')
        score = ep.get('score', 0)
        uuid = ep.get('uuid', '')

        output.append(f"### {i}. {name}")
        if source_desc:
            output.append(f"**Source**: {source_desc}")
        if date:
            output.append(f"**Date**: {date}")
        if score:
            output.append(f"**Relevance Score**: {score:.3f}")
        if uuid:
            output.append(f"**UUID**: {uuid}")
        output.append("")
        output.append("**Content Preview**:")
        output.append(f"> {content}")
        output.append("")

    return [TextContent(type="text", text="\n".join(output))]


async def handle_statistics() -> list[TextContent]:
    """Handle graph_statistics tool."""
    await retriever.executor.initialize()

    count_query = "MATCH (n) RETURN count(n) as total"
    type_query = """
    MATCH (n:Entity)
    RETURN DISTINCT labels(n) as labels, count(*) as count
    ORDER BY count DESC
    LIMIT 15
    """

    async with await retriever.executor._get_session() as session:
        result = await session.run(count_query)
        total = (await result.data())[0]['total']

        result = await session.run(type_query)
        types = await result.data()

    config = retriever.config
    output = [
        "## Knowledge Graph Statistics",
        f"- **Total Nodes**: {total:,}",
        f"- **Database**: {config.database}",
        "",
        "## Entity Types"
    ]

    for t in types:
        labels = ', '.join(t['labels'])
        output.append(f"- {labels}: {t['count']:,}")

    return [TextContent(type="text", text="\n".join(output))]


# =============================================================================
# Temporal Tool Handlers
# =============================================================================

def _calculate_temporal_relevance(content: str, start_year: int, end_year: int) -> float:
    """Calculate how temporally relevant content is to the date range."""
    import re
    content_lower = content.lower()

    # Look for temporal indicators
    temporal_indicators = [
        "announced", "published", "enacted", "implemented", "released",
        "updated", "changed", "effective", "deadline", "commenced"
    ]

    relevance_score = 0.0

    # Base score for temporal keywords
    for indicator in temporal_indicators:
        if indicator in content_lower:
            relevance_score += 0.2

    # Look for date patterns
    date_patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",  # YYYY-MM-DD
        r"\b\d{1,2}/\d{1,2}/\d{4}\b",  # MM/DD/YYYY or DD/MM/YYYY
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}\b",
    ]

    for pattern in date_patterns:
        if re.search(pattern, content_lower):
            relevance_score += 0.3
            break

    # Look for year mentions within range
    for year in range(start_year, end_year + 1):
        if str(year) in content:
            relevance_score += 0.3
            break

    return min(relevance_score, 1.0)


def _extract_event_info(content: str, entity_name: str) -> dict[str, Any]:
    """Extract event type and importance from content."""
    content_lower = content.lower()

    # Event type classification
    event_types = {
        "regulatory": ["regulation", "rule", "compliance", "enforcement", "fine", "penalty"],
        "policy": ["policy", "law", "act", "directive", "legislation", "amendment"],
        "business": ["merger", "acquisition", "partnership", "investment", "funding"],
        "product": ["launch", "release", "announcement", "update", "version"],
        "legal": ["lawsuit", "court", "ruling", "judgment", "settlement", "litigation"],
        "general": ["news", "report", "statement", "comment", "response"],
    }

    detected_type = "general"
    for event_type, keywords in event_types.items():
        if any(keyword in content_lower for keyword in keywords):
            detected_type = event_type
            break

    # Importance scoring
    importance_indicators = {
        "high": ["major", "significant", "important", "critical", "breakthrough", "landmark"],
        "medium": ["notable", "substantial", "considerable", "meaningful"],
        "temporal": ["announced", "released", "published", "enacted", "implemented"],
    }

    importance_score = 0.3  # Base score
    for level, indicators in importance_indicators.items():
        for indicator in indicators:
            if indicator in content_lower:
                if level == "high":
                    importance_score += 0.3
                elif level == "medium":
                    importance_score += 0.2
                elif level == "temporal":
                    importance_score += 0.1

    # Extract temporal indicators
    temporal_indicators = []
    temporal_keywords = [
        "announced", "released", "published", "enacted", "implemented",
        "updated", "changed", "effective", "deadline", "commenced"
    ]

    for keyword in temporal_keywords:
        if keyword in content_lower:
            temporal_indicators.append(keyword)

    return {
        "type": detected_type,
        "importance": min(importance_score, 1.0),
        "temporal_indicators": temporal_indicators,
    }


def _analyze_policy_evolution(content: str, policy_name: str) -> dict[str, Any]:
    """Analyze content for policy evolution indicators."""
    content_lower = content.lower()

    # Evolution phases
    phase_indicators = {
        "proposal": ["proposed", "draft", "proposal", "suggest", "recommend"],
        "amendment": ["amended", "revised", "updated", "modified", "changed"],
        "implementation": ["implemented", "enacted", "effective", "came into force"],
        "enforcement": ["enforced", "penalty", "fine", "violation", "compliance"],
        "review": ["reviewed", "evaluated", "assessed", "reconsidered"],
    }

    detected_phase = "general"
    for phase, indicators in phase_indicators.items():
        if any(indicator in content_lower for indicator in indicators):
            detected_phase = phase
            break

    # Evolution types
    evolution_types = {
        "amendment": ["amendment", "revised", "updated", "modified"],
        "expansion": ["expanded", "extended", "broadened", "increased"],
        "restriction": ["restricted", "limited", "reduced", "narrowed"],
        "clarification": ["clarified", "explained", "defined", "specified"],
        "enforcement": ["enforcement", "penalty", "fine", "sanction"],
    }

    detected_type = "general"
    for evo_type, keywords in evolution_types.items():
        if any(keyword in content_lower for keyword in keywords):
            detected_type = evo_type
            break

    # Impact level scoring
    impact_indicators = {
        "high": ["major", "significant", "substantial", "critical", "fundamental"],
        "medium": ["important", "notable", "considerable", "meaningful"],
        "procedural": ["administrative", "procedural", "technical", "minor"],
    }

    impact_level = 0.3  # Base impact
    for level, indicators in impact_indicators.items():
        for indicator in indicators:
            if indicator in content_lower:
                if level == "high":
                    impact_level += 0.4
                elif level == "medium":
                    impact_level += 0.2
                elif level == "procedural":
                    impact_level += 0.1

    # Extract stakeholders
    stakeholder_patterns = [
        "commission", "parliament", "council", "agency", "authority",
        "company", "companies", "organization", "industry", "sector"
    ]

    stakeholders = []
    for pattern in stakeholder_patterns:
        if pattern in content_lower:
            stakeholders.append(pattern)

    return {
        "phase": detected_phase,
        "evolution_type": detected_type,
        "impact_level": min(impact_level, 1.0),
        "stakeholders": stakeholders,
    }


async def handle_search_by_date_range(
    query: str,
    start_date: str,
    end_date: str,
    max_results: int = 10
) -> list[TextContent]:
    """Handle search_by_date_range tool - search within a specific date range."""
    from datetime import datetime

    logger.info(f"Searching date range {start_date} to {end_date} for: {query}")

    try:
        # Parse dates
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError as e:
        return [TextContent(type="text", text=f"Error: Invalid date format. Use YYYY-MM-DD. {e}")]

    # Build temporal search query with keywords
    temporal_keywords = ["announced", "published", "enacted", "implemented", "released", "updated", "changed"]
    temporal_query = f"{query} " + " ".join(temporal_keywords[:3])

    # Use retriever to search
    context = await retriever.retrieve(temporal_query)
    result = retriever.to_dict(context)

    # Extract facts and entities
    facts = result.get('retrieved_context', {}).get('facts', [])
    entities = result.get('retrieved_context', {}).get('entities', [])

    # Process and filter by temporal relevance
    temporal_events = []

    for fact in facts:
        content = fact.get('content', '')
        if content:
            temporal_score = _calculate_temporal_relevance(content, start_dt.year, end_dt.year)
            if temporal_score > 0:
                temporal_events.append({
                    "content": content,
                    "temporal_score": temporal_score,
                    "type": "fact"
                })

    for entity in entities:
        content = entity.get('summary', '') or entity.get('name', '')
        if content:
            temporal_score = _calculate_temporal_relevance(content, start_dt.year, end_dt.year)
            if temporal_score > 0:
                temporal_events.append({
                    "content": content,
                    "temporal_score": temporal_score,
                    "type": "entity",
                    "name": entity.get('name', '')
                })

    # Sort by temporal relevance
    temporal_events.sort(key=lambda x: x["temporal_score"], reverse=True)
    temporal_events = temporal_events[:max_results]

    # Format response
    output = [
        f"## Temporal Search: {start_date} to {end_date}",
        "",
        f"**Query**: {query}",
        f"**Period**: {(end_dt - start_dt).days} days",
        ""
    ]

    if temporal_events:
        output.append(f"**Found {len(temporal_events)} temporally relevant results:**")
        output.append("")
        for i, event in enumerate(temporal_events, 1):
            content = event['content'][:200] + "..." if len(event['content']) > 200 else event['content']
            output.append(f"{i}. **[{event['type'].title()}]** {content}")
            if event["temporal_score"] > 0.7:
                output.append(f"   *High temporal relevance ({event['temporal_score']:.2f})*")
            output.append("")
    else:
        output.append(f"No temporally relevant events found for '{query}' in the specified date range.")
        output.append("")
        output.append("**Suggestions:**")
        output.append("- Try expanding the date range")
        output.append("- Use broader search terms")
        output.append("- Search with German terms (e.g., 'Verordnung' instead of 'regulation')")

    return [TextContent(type="text", text="\n".join(output))]


async def handle_get_entity_history(
    entity_name: str,
    days_back: int = 365,
    event_types: list[str] = None
) -> list[TextContent]:
    """Handle get_entity_history tool - track entity evolution over time."""
    logger.info(f"Getting {days_back}-day history for entity: {entity_name}")

    # Build history search query
    history_keywords = ["history", "timeline", "evolution", "changes", "updates", "development"]
    if event_types:
        history_keywords.extend(event_types)

    search_query = f"{entity_name} " + " ".join(history_keywords[:4])

    # Use retriever to search
    context = await retriever.retrieve(search_query)
    result = retriever.to_dict(context)

    # Extract facts
    facts = result.get('retrieved_context', {}).get('facts', [])
    relationships = result.get('retrieved_context', {}).get('relationships', [])

    # Process historical events
    historical_events = []

    for fact in facts:
        content = fact.get('content', '')
        if content and entity_name.lower() in content.lower():
            event_info = _extract_event_info(content, entity_name)
            historical_events.append({
                "content": content,
                "event_type": event_info["type"],
                "importance": event_info["importance"],
                "temporal_indicators": event_info["temporal_indicators"],
            })

    # Sort by importance
    historical_events.sort(key=lambda x: (x["importance"], len(x["temporal_indicators"])), reverse=True)

    # Format historical timeline
    output = [
        f"## Historical Timeline: {entity_name}",
        "",
        f"**Period**: Last {days_back} days",
    ]

    if event_types:
        output.append(f"**Focus**: {', '.join(event_types)}")
    output.append(f"**Events Found**: {len(historical_events)}")
    output.append("")

    if historical_events:
        # Group by event type
        event_groups = {}
        for event in historical_events:
            event_type = event["event_type"]
            if event_type not in event_groups:
                event_groups[event_type] = []
            event_groups[event_type].append(event)

        for event_type, events in event_groups.items():
            output.append(f"### {event_type.title()} Events:")
            for i, event in enumerate(events[:5], 1):
                content = event['content'][:150] + "..." if len(event['content']) > 150 else event['content']
                output.append(f"{i}. {content}")
                if event["temporal_indicators"]:
                    output.append(f"   *Temporal markers: {', '.join(event['temporal_indicators'][:3])}*")
            output.append("")

        # Timeline summary
        output.append("### Timeline Analysis:")
        total_events = len(historical_events)
        high_importance = len([e for e in historical_events if e["importance"] > 0.7])
        output.append(f"- **Total historical events**: {total_events}")
        output.append(f"- **High-importance events**: {high_importance}")
        output.append(f"- **Event types found**: {len(event_groups)}")
    else:
        output.append(f"No clear historical timeline found for {entity_name}.")
        output.append("")
        output.append("**Suggestions:**")
        output.append("- Try using alternative entity names or acronyms")
        output.append("- Try German names (e.g., 'KI-Verordnung' for 'AI Act')")
        output.append("- Expand the time period")

    return [TextContent(type="text", text="\n".join(output))]


async def handle_find_concurrent_events(
    reference_date: str,
    window_days: int = 30,
    event_context: str = None
) -> list[TextContent]:
    """Handle find_concurrent_events tool - find events around a reference date."""
    from datetime import datetime, timedelta

    logger.info(f"Finding concurrent events around {reference_date} (±{window_days} days)")

    try:
        ref_dt = datetime.strptime(reference_date, "%Y-%m-%d")
    except ValueError as e:
        return [TextContent(type="text", text=f"Error: Invalid date format. Use YYYY-MM-DD. {e}")]

    start_dt = ref_dt - timedelta(days=window_days)
    end_dt = ref_dt + timedelta(days=window_days)

    # Build search query
    concurrent_keywords = ["announced", "released", "published", "enacted", "occurred"]
    if event_context:
        search_query = f"{event_context} " + " ".join(concurrent_keywords[:3])
    else:
        search_query = " ".join(concurrent_keywords) + " events news policy regulation"

    # Use retriever to search
    context = await retriever.retrieve(search_query)
    result = retriever.to_dict(context)

    # Extract facts
    facts = result.get('retrieved_context', {}).get('facts', [])

    # Process concurrent events
    concurrent_events = []

    for fact in facts:
        content = fact.get('content', '')
        if content:
            temporal_score = _calculate_temporal_relevance(content, ref_dt.year, ref_dt.year)
            if temporal_score > 0.3:
                # Categorize the event
                event_info = _extract_event_info(content, "")
                concurrent_events.append({
                    "content": content,
                    "category": event_info["type"],
                    "temporal_relevance": temporal_score,
                })

    # Sort by temporal relevance
    concurrent_events.sort(key=lambda x: x["temporal_relevance"], reverse=True)
    concurrent_events = concurrent_events[:15]

    # Format concurrent events analysis
    output = [
        "## Concurrent Events Analysis",
        "",
        f"**Reference Date**: {reference_date}",
        f"**Time Window**: ±{window_days} days ({start_dt.date()} to {end_dt.date()})",
    ]
    if event_context:
        output.append(f"**Context Filter**: {event_context}")
    output.append(f"**Events Found**: {len(concurrent_events)}")
    output.append("")

    if concurrent_events:
        # Group by category
        categories = {}
        for event in concurrent_events:
            category = event["category"]
            if category not in categories:
                categories[category] = []
            categories[category].append(event)

        output.append("### Concurrent Events by Category:")
        output.append("")
        for category, events in categories.items():
            output.append(f"#### {category.title()} ({len(events)} events):")
            for i, event in enumerate(events[:3], 1):
                content = event['content'][:120] + "..." if len(event['content']) > 120 else event['content']
                output.append(f"{i}. {content}")
                output.append(f"   *Temporal relevance: {event['temporal_relevance']:.2f}*")
            output.append("")

        # Timeline context
        output.append("### Timeline Context:")
        high_relevance = len([e for e in concurrent_events if e["temporal_relevance"] > 0.7])
        output.append(f"- **High temporal relevance**: {high_relevance} events")
        output.append(f"- **Event categories**: {len(categories)}")
    else:
        output.append(f"No significant concurrent events found around {reference_date}.")
        output.append("")
        output.append("**Suggestions:**")
        output.append("- Expand the time window")
        output.append("- Try different event context keywords")
        output.append("- Check for events in adjacent time periods")

    return [TextContent(type="text", text="\n".join(output))]


async def handle_compare_timelines(
    entities: list[str],
    time_period: int = 365,
    comparison_focus: str = None
) -> list[TextContent]:
    """Handle compare_timelines tool - compare multiple entity timelines."""
    logger.info(f"Comparing timelines for {len(entities)} entities over {time_period} days")

    if len(entities) < 2:
        return [TextContent(type="text", text="Error: Please provide at least 2 entities to compare.")]

    if len(entities) > 5:
        entities = entities[:5]
        logger.warning(f"Limited comparison to first 5 entities")

    # Collect timeline data for each entity
    entity_timelines = {}

    for entity_name in entities:
        # Build search query
        keywords = ["timeline", "evolution", "history", "changes"]
        if comparison_focus:
            keywords.append(comparison_focus)

        search_query = f"{entity_name} " + " ".join(keywords[:3])

        # Use retriever to search
        context = await retriever.retrieve(search_query)
        result = retriever.to_dict(context)

        # Extract facts
        facts = result.get('retrieved_context', {}).get('facts', [])

        # Process events for this entity
        entity_events = []
        for fact in facts:
            content = fact.get('content', '')
            if content and entity_name.lower() in content.lower():
                event_info = _extract_event_info(content, entity_name)
                entity_events.append({
                    "content": content[:150],
                    "event_type": event_info["type"],
                    "importance": event_info["importance"],
                })

        entity_events.sort(key=lambda x: x["importance"], reverse=True)
        entity_timelines[entity_name] = entity_events[:5]

    # Format comparison
    output = [
        "## Timeline Comparison",
        "",
        f"**Entities Compared**: {', '.join(entities)}",
        f"**Period**: {time_period} days",
    ]
    if comparison_focus:
        output.append(f"**Focus**: {comparison_focus}")
    output.append("")

    # Show each entity's timeline
    output.append("### Individual Timelines:")
    output.append("")

    for entity_name, events in entity_timelines.items():
        output.append(f"#### {entity_name}")
        if events:
            for i, event in enumerate(events[:3], 1):
                output.append(f"{i}. [{event['event_type'].title()}] {event['content']}...")
        else:
            output.append("*No significant timeline events found*")
        output.append("")

    # Comparison analysis
    output.append("### Comparison Analysis:")

    # Find common event types
    all_event_types = {}
    for entity_name, events in entity_timelines.items():
        for event in events:
            etype = event["event_type"]
            if etype not in all_event_types:
                all_event_types[etype] = []
            all_event_types[etype].append(entity_name)

    common_types = [etype for etype, ents in all_event_types.items() if len(set(ents)) > 1]
    if common_types:
        output.append(f"- **Shared event types**: {', '.join(common_types)}")

    # Activity comparison
    activity_levels = {name: len(events) for name, events in entity_timelines.items()}
    most_active = max(activity_levels, key=activity_levels.get) if activity_levels else None
    if most_active:
        output.append(f"- **Most active entity**: {most_active} ({activity_levels[most_active]} events)")

    output.append(f"- **Entities with timeline data**: {sum(1 for e in entity_timelines.values() if e)}/{len(entities)}")

    return [TextContent(type="text", text="\n".join(output))]


async def handle_track_policy_evolution(
    policy_name: str,
    evolution_period: int = 730,
    evolution_aspects: list[str] = None
) -> list[TextContent]:
    """Handle track_policy_evolution tool - track policy/regulation evolution."""
    logger.info(f"Tracking evolution of policy: {policy_name} over {evolution_period} days")

    # Build evolution search query
    evolution_keywords = ["evolution", "amendment", "update", "revision", "change", "modification", "implementation"]
    if evolution_aspects:
        evolution_keywords.extend(evolution_aspects)

    search_query = f"{policy_name} " + " ".join(evolution_keywords[:5])

    # Use retriever to search
    context = await retriever.retrieve(search_query)
    result = retriever.to_dict(context)

    # Extract facts
    facts = result.get('retrieved_context', {}).get('facts', [])

    # Process evolution timeline
    evolution_events = []

    for fact in facts:
        content = fact.get('content', '')
        if content and policy_name.lower() in content.lower():
            evolution_info = _analyze_policy_evolution(content, policy_name)
            evolution_events.append({
                "content": content,
                "phase": evolution_info["phase"],
                "impact_level": evolution_info["impact_level"],
                "evolution_type": evolution_info["evolution_type"],
                "stakeholders": evolution_info["stakeholders"],
            })

    # Sort by impact level
    evolution_events.sort(key=lambda x: (x["impact_level"], x["phase"] == "implementation"), reverse=True)

    # Format policy evolution analysis
    output = [
        f"## Policy Evolution Analysis: {policy_name}",
        "",
        f"**Evolution Period**: {evolution_period} days (~{evolution_period // 365} years)",
    ]
    if evolution_aspects:
        output.append(f"**Focus Areas**: {', '.join(evolution_aspects)}")
    output.append(f"**Evolution Events**: {len(evolution_events)}")
    output.append("")

    if evolution_events:
        # Group by evolution phase
        phases = {}
        for event in evolution_events:
            phase = event["phase"]
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(event)

        # Order phases logically
        phase_order = ["proposal", "amendment", "implementation", "enforcement", "review", "general"]
        ordered_phases = {phase: phases.get(phase, []) for phase in phase_order if phase in phases}

        output.append("### Evolution Timeline by Phase:")
        output.append("")

        for phase, events in ordered_phases.items():
            output.append(f"#### {phase.title()} Phase ({len(events)} events):")
            for i, event in enumerate(events[:4], 1):
                content = event['content'][:120] + "..." if len(event['content']) > 120 else event['content']
                output.append(f"{i}. **{event['evolution_type'].title()}**: {content}")
                if event["stakeholders"]:
                    output.append(f"   *Stakeholders: {', '.join(event['stakeholders'][:3])}*")
                output.append(f"   *Impact level: {event['impact_level']:.2f}*")
            output.append("")

        # Evolution summary
        output.append("### Evolution Summary:")
        high_impact = len([e for e in evolution_events if e["impact_level"] > 0.7])
        evolution_types = set(e["evolution_type"] for e in evolution_events)
        all_stakeholders = set()
        for event in evolution_events:
            all_stakeholders.update(event["stakeholders"])

        output.append(f"- **High-impact changes**: {high_impact}")
        output.append(f"- **Evolution phases**: {len(ordered_phases)}")
        output.append(f"- **Change types**: {', '.join(evolution_types)}")
        if all_stakeholders:
            output.append(f"- **Key stakeholders**: {', '.join(list(all_stakeholders)[:5])}")
    else:
        output.append(f"No clear evolution timeline found for {policy_name}.")
        output.append("")
        output.append("**Suggestions:**")
        output.append("- Try alternative policy names or abbreviations")
        output.append("- Use German names (e.g., 'KI-Verordnung', 'DSGVO', 'NIS2-Richtlinie')")
        output.append("- Expand the evolution period")
        output.append("- Focus on specific evolution aspects")

    return [TextContent(type="text", text="\n".join(output))]


# =============================================================================
# Community Detection Tool Handlers
# =============================================================================

def _extract_entities_from_content(content: str) -> list[str]:
    """Extract potential entities from content using simple patterns."""
    import re

    # Extract capitalized phrases (potential entity names)
    entity_patterns = re.findall(r"\b[A-Z][a-zA-Z\s&.-]{2,30}(?:[A-Z][a-zA-Z]{2,}|\b)", content)

    # Filter and clean entities
    entities = []
    for entity in entity_patterns:
        entity = entity.strip()
        if len(entity) > 2 and len(entity) < 50:
            # Remove common non-entity words
            if not any(
                word in entity.lower() for word in ["the", "and", "or", "but", "this", "that"]
            ):
                entities.append(entity)

    # Remove duplicates while preserving order
    seen = set()
    unique_entities = []
    for entity in entities:
        if entity not in seen:
            seen.add(entity)
            unique_entities.append(entity)

    return unique_entities[:20]


def _calculate_community_cohesion(
    members: list[str], cooccurrence_matrix: dict[str, dict[str, int]]
) -> float:
    """Calculate how tightly connected community members are."""
    if len(members) < 2:
        return 0.0

    total_possible_connections = len(members) * (len(members) - 1)
    actual_connections = 0
    connection_strength = 0

    for member1 in members:
        for member2 in members:
            if member1 != member2 and member1 in cooccurrence_matrix:
                if member2 in cooccurrence_matrix[member1]:
                    actual_connections += 1
                    connection_strength += cooccurrence_matrix[member1][member2]

    # Calculate cohesion as combination of connection ratio and strength
    connection_ratio = (
        actual_connections / total_possible_connections if total_possible_connections > 0 else 0
    )
    avg_strength = connection_strength / actual_connections if actual_connections > 0 else 0

    # Normalize strength (assuming max reasonable co-occurrence is 10)
    normalized_strength = min(avg_strength / 10.0, 1.0)

    return (connection_ratio + normalized_strength) / 2


def _determine_community_theme(
    members: list[str], contexts: dict[str, list[str]], topic_focus: str = None
) -> str:
    """Determine the main theme of a community."""
    # Collect all contexts for community members
    all_contexts = []
    for member in members:
        if member in contexts:
            all_contexts.extend(contexts[member])

    # Extract common themes
    combined_text = " ".join(all_contexts).lower()

    # Predefined themes for political/regulatory content
    theme_keywords = {
        "ai_regulation": ["artificial intelligence", "ai", "machine learning", "algorithm"],
        "data_privacy": ["privacy", "data protection", "gdpr", "personal data"],
        "digital_services": ["digital", "platform", "online", "internet", "digital services"],
        "financial_regulation": ["financial", "banking", "payment", "fintech", "money"],
        "competition": ["competition", "antitrust", "monopoly", "market", "dominant"],
        "cybersecurity": ["cyber", "security", "breach", "attack", "protection"],
        "environmental": ["environment", "climate", "carbon", "sustainability", "green"],
        "trade": ["trade", "import", "export", "tariff", "commerce"],
        "general_policy": ["policy", "regulation", "law", "rule", "governance"],
    }

    # Score themes based on keyword frequency
    theme_scores = {}
    for theme, keywords in theme_keywords.items():
        score = sum(combined_text.count(keyword) for keyword in keywords)
        if score > 0:
            theme_scores[theme] = score

    # Use topic focus if provided and relevant
    if topic_focus and any(
        focus_word in combined_text for focus_word in topic_focus.lower().split()
    ):
        return topic_focus.lower().replace(" ", "_")

    # Return highest scoring theme
    if theme_scores:
        return max(theme_scores.items(), key=lambda x: x[1])[0]

    return "general"


def _detect_communities(
    results: list[Any], topic_focus: str = None, min_size: int = 3
) -> list[dict[str, Any]]:
    """Detect communities from search results using co-occurrence analysis."""
    # Extract entities and their co-occurrences
    entity_cooccurrence = {}
    entity_contexts = {}

    for result in results:
        content = ""
        if hasattr(result, "fact") and result.fact:
            content = result.fact
        elif hasattr(result, "summary") and result.summary:
            content = result.summary

        if content:
            # Extract entities from content (simplified NER)
            entities = _extract_entities_from_content(content)

            # Record co-occurrences
            for i, entity1 in enumerate(entities):
                if entity1 not in entity_contexts:
                    entity_contexts[entity1] = []
                entity_contexts[entity1].append(content)

                if entity1 not in entity_cooccurrence:
                    entity_cooccurrence[entity1] = {}

                for j, entity2 in enumerate(entities):
                    if i != j:
                        if entity2 not in entity_cooccurrence[entity1]:
                            entity_cooccurrence[entity1][entity2] = 0
                        entity_cooccurrence[entity1][entity2] += 1

    # Build communities using co-occurrence strength
    communities = []
    processed_entities = set()

    for entity, cooccurrences in entity_cooccurrence.items():
        if entity in processed_entities:
            continue

        # Find strongly connected entities
        community_members = [entity]
        community_connections = []

        # Sort by co-occurrence strength
        sorted_cooccurrences = sorted(cooccurrences.items(), key=lambda x: x[1], reverse=True)

        for related_entity, strength in sorted_cooccurrences[:10]:  # Top 10 related
            if (
                related_entity not in processed_entities and strength >= 2
            ):  # Minimum co-occurrence
                community_members.append(related_entity)
                community_connections.append(f"{entity}-{related_entity}")

        # Only keep communities above minimum size
        if len(community_members) >= min_size:
            # Calculate community cohesion
            cohesion = _calculate_community_cohesion(
                community_members, entity_cooccurrence
            )

            # Determine community theme
            theme = _determine_community_theme(
                community_members, entity_contexts, topic_focus
            )

            communities.append(
                {
                    "theme": theme,
                    "members": community_members,
                    "connections": community_connections,
                    "cohesion": cohesion,
                }
            )

            # Mark entities as processed
            processed_entities.update(community_members)

    # Sort by cohesion
    communities.sort(key=lambda x: x["cohesion"], reverse=True)

    return communities


async def handle_get_communities(
    topic_focus: str = None,
    max_communities: int = 5,
    min_community_size: int = 3
) -> list[TextContent]:
    """Handle get_communities tool - discover entity communities/clusters."""
    from graphiti_core.search.search_config_recipes import COMMUNITY_HYBRID_SEARCH_RRF

    logger.info(f"Discovering communities (focus: {topic_focus}, max: {max_communities})")

    try:
        # Build community search query
        if topic_focus:
            search_query = (
                f"{topic_focus} communities groups clusters networks related connected"
            )
        else:
            search_query = (
                "communities groups clusters networks related connected policy organization"
            )

        # Use community-focused search configuration via retriever
        await retriever.executor.initialize()
        graphiti_client = retriever.executor.graphiti_client

        search_results = await graphiti_client._search(
            query=search_query, config=COMMUNITY_HYBRID_SEARCH_RRF
        )

        # Extract results
        results = []
        if hasattr(search_results, "edges") and search_results.edges:
            results.extend(search_results.edges)
        if hasattr(search_results, "nodes") and search_results.nodes:
            results.extend(search_results.nodes)

        if not results:
            return [TextContent(type="text", text=f"No communities found for topic: {topic_focus or 'general'}")]

        # Detect communities through co-occurrence analysis
        communities = _detect_communities(results, topic_focus, min_community_size)

        # Limit to max communities
        communities = communities[:max_communities]

        # Format community analysis
        output = ["## Community Detection Analysis", ""]
        if topic_focus:
            output.append(f"**Topic Focus**: {topic_focus}")
        output.append(f"**Communities Found**: {len(communities)}")
        output.append(f"**Minimum Community Size**: {min_community_size} entities")
        output.append("")

        if communities:
            output.append("### Discovered Communities:")
            output.append("")
            for i, community in enumerate(communities, 1):
                output.append(f"#### Community {i}: {community['theme'].title()}")
                output.append(f"**Size**: {len(community['members'])} entities")
                output.append(f"**Cohesion**: {community['cohesion']:.2f}")
                output.append(f"**Key Members**: {', '.join(community['members'][:5])}")
                if len(community["members"]) > 5:
                    output.append(f" (and {len(community['members']) - 5} more)")

                if community["connections"]:
                    output.append(f"**Main Connections**: {', '.join(community['connections'][:3])}")
                output.append("")

            # Community insights
            output.append("### Community Insights:")
            total_entities = sum(len(c["members"]) for c in communities)
            avg_size = total_entities / len(communities) if communities else 0
            high_cohesion = len([c for c in communities if c["cohesion"] > 0.7])

            output.append(f"- **Average community size**: {avg_size:.1f} entities")
            output.append(f"- **High-cohesion communities**: {high_cohesion}")
            output.append(f"- **Network density**: {'High' if high_cohesion > len(communities)/2 else 'Medium' if high_cohesion > 0 else 'Low'}")
        else:
            output.append("No clear communities detected for the given criteria.")
            output.append("")
            output.append("**Suggestions:**")
            output.append("- Try broader topic focus")
            output.append("- Reduce minimum community size")
            output.append("- Use more general search terms")

        logger.info(f"Detected {len(communities)} communities")
        return [TextContent(type="text", text="\n".join(output))]

    except Exception as e:
        logger.error(f"Error detecting communities: {e}")
        return [TextContent(type="text", text=f"Error detecting communities: {str(e)}")]


def _calculate_member_relevance(entity: str, content: str, community_topic: str) -> float:
    """Calculate how relevant an entity is to the community topic."""
    content_lower = content.lower()
    entity_lower = entity.lower()
    topic_lower = community_topic.lower()

    relevance_score = 0.0

    # Base score for entity mention
    relevance_score += 0.3

    # Score for topic keywords in same context
    topic_words = topic_lower.split()
    for word in topic_words:
        if word in content_lower:
            relevance_score += 0.2

    # Score for co-occurrence strength
    entity_pos = content_lower.find(entity_lower)
    if entity_pos != -1:
        # Check proximity to topic keywords
        for word in topic_words:
            word_pos = content_lower.find(word)
            if word_pos != -1:
                distance = abs(entity_pos - word_pos)
                if distance < 100:  # Close proximity
                    relevance_score += 0.2

    # Score for relationship indicators
    relationship_words = ["related", "connected", "involved", "part of", "member", "associated"]
    for rel_word in relationship_words:
        if rel_word in content_lower:
            relevance_score += 0.1

    return min(relevance_score, 1.0)


def _classify_member_type(entity: str, content: str) -> str:
    """Classify the type of community member."""
    entity_lower = entity.lower()
    content_lower = content.lower()

    # Classification keywords
    type_keywords = {
        "policy": ["act", "law", "regulation", "directive", "policy", "rule"],
        "company": ["company", "corporation", "inc", "ltd", "gmbh", "ag", "firm"],
        "organization": ["organization", "agency", "authority", "commission", "committee"],
        "politician": ["minister", "commissioner", "president", "director", "ceo", "official"],
        "jurisdiction": ["union", "country", "state", "nation", "jurisdiction", "territory"],
        "technology": ["platform", "system", "technology", "service", "software", "app"],
    }

    # Check entity name
    for entity_type, keywords in type_keywords.items():
        if any(keyword in entity_lower for keyword in keywords):
            return entity_type

    # Check context
    for entity_type, keywords in type_keywords.items():
        if any(keyword in content_lower for keyword in keywords):
            return entity_type

    return "entity"


def _extract_member_connections(entity: str, content: str) -> list[str]:
    """Extract other entities connected to this member."""
    import re

    entities = re.findall(r"\b[A-Z][a-zA-Z\s&.-]{2,30}(?:[A-Z][a-zA-Z]{2,}|\b)", content)
    connections = []

    for other_entity in entities:
        other_entity = other_entity.strip()
        if (
            other_entity != entity
            and len(other_entity) > 2
            and len(other_entity) < 50
            and not any(word in other_entity.lower() for word in ["the", "and", "or", "but"])
        ):
            connections.append(other_entity)

    return list(set(connections))[:5]


def _extract_community_members(
    results: list[Any], community_topic: str, member_types: list[str] = None
) -> list[dict[str, Any]]:
    """Extract and score community members from search results."""
    members = []
    processed_names = set()

    for result in results:
        content = ""
        if hasattr(result, "fact") and result.fact:
            content = result.fact
        elif hasattr(result, "summary") and result.summary:
            content = result.summary

        if content:
            # Extract potential member entities
            entities = _extract_entities_from_content(content)

            for entity in entities:
                if entity not in processed_names:
                    # Score relevance to community topic
                    relevance = _calculate_member_relevance(
                        entity, content, community_topic
                    )

                    if relevance > 0.3:  # Minimum relevance threshold
                        # Determine member type
                        member_type = _classify_member_type(entity, content)

                        # Filter by member types if specified
                        if member_types and member_type not in [
                            mt.lower() for mt in member_types
                        ]:
                            continue

                        # Extract connections
                        connections = _extract_member_connections(entity, content)

                        members.append(
                            {
                                "name": entity,
                                "type": member_type,
                                "relevance": relevance,
                                "context": content,
                                "connections": connections,
                            }
                        )

                        processed_names.add(entity)

    # Sort by relevance
    members.sort(key=lambda x: x["relevance"], reverse=True)

    return members


async def handle_get_community_members(
    community_topic: str,
    max_members: int = 10,
    member_types: list[str] = None
) -> list[TextContent]:
    """Handle get_community_members tool - get members of a community."""
    from graphiti_core.search.search_config_recipes import COMBINED_HYBRID_SEARCH_RRF

    logger.info(f"Getting community members for: {community_topic}")

    try:
        # Build community member search query
        search_query = (
            f"{community_topic} members organizations companies policies entities related"
        )
        if member_types:
            search_query += " " + " ".join(member_types)

        # Use comprehensive search for community members
        await retriever.executor.initialize()
        graphiti_client = retriever.executor.graphiti_client

        search_results = await graphiti_client._search(
            query=search_query, config=COMBINED_HYBRID_SEARCH_RRF
        )

        # Extract results
        results = []
        if hasattr(search_results, "edges") and search_results.edges:
            results.extend(search_results.edges)
        if hasattr(search_results, "nodes") and search_results.nodes:
            results.extend(search_results.nodes)

        if not results:
            return [TextContent(type="text", text=f"No community members found for topic: {community_topic}")]

        # Extract and categorize community members
        members = _extract_community_members(results, community_topic, member_types)

        # Limit to max members
        members = members[:max_members]

        # Format community members analysis
        output = [f"## Community Members: {community_topic.title()}", ""]
        if member_types:
            output.append(f"**Member Types Filter**: {', '.join(member_types)}")
        output.append(f"**Members Found**: {len(members)}")
        output.append("")

        if members:
            # Group by member type
            member_groups = {}
            for member in members:
                member_type = member["type"]
                if member_type not in member_groups:
                    member_groups[member_type] = []
                member_groups[member_type].append(member)

            output.append("### Community Members by Type:")
            output.append("")
            for member_type, type_members in member_groups.items():
                output.append(f"#### {member_type.title()} ({len(type_members)} members):")
                for i, member in enumerate(type_members, 1):
                    output.append(f"{i}. **{member['name']}**")
                    output.append(f"   Relevance: {member['relevance']:.2f}")
                    context_preview = member['context'][:100] + "..." if len(member['context']) > 100 else member['context']
                    output.append(f"   Context: {context_preview}")
                    if member["connections"]:
                        output.append(f"   Connected to: {', '.join(member['connections'][:3])}")
                    output.append("")

            # Community analysis
            output.append("### Community Analysis:")
            total_relevance = sum(m["relevance"] for m in members)
            avg_relevance = total_relevance / len(members) if members else 0
            high_relevance = len([m for m in members if m["relevance"] > 0.7])

            output.append(f"- **Member types**: {len(member_groups)}")
            output.append(f"- **Average relevance**: {avg_relevance:.2f}")
            output.append(f"- **High-relevance members**: {high_relevance}")
            output.append(f"- **Community cohesion**: {'Strong' if high_relevance > len(members)/2 else 'Moderate' if high_relevance > 0 else 'Weak'}")
        else:
            output.append(f"No clear community members found for {community_topic}.")
            output.append("")
            output.append("**Suggestions:**")
            output.append("- Try broader topic terms")
            output.append("- Remove member type filters")
            output.append("- Use alternative topic names")

        logger.info(f"Found {len(members)} community members")
        return [TextContent(type="text", text="\n".join(output))]

    except Exception as e:
        logger.error(f"Error getting community members: {e}")
        return [TextContent(type="text", text=f"Error getting community members for {community_topic}: {str(e)}")]


def _extract_policies_from_content(content: str, policy_area: str = None) -> list[dict[str, Any]]:
    """Extract policy information from content."""
    import re

    policies = []

    # Look for policy patterns
    policy_patterns = [
        r"([A-Z][a-zA-Z\s]+(?:Act|Regulation|Directive|Law|Policy|Rule))",
        r"((?:EU|European|US|American|UK|British)\s+[A-Z][a-zA-Z\s]+(?:Act|Regulation|Directive))",
        r"([A-Z][A-Z]{2,}\s*(?:Act|Regulation|Directive))",  # Acronyms
    ]

    for pattern in policy_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            policy_name = match.strip()
            if len(policy_name) > 5 and len(policy_name) < 100:
                # Extract additional information
                jurisdiction = _extract_jurisdiction(content, policy_name)
                theme = _extract_policy_theme(content, policy_name, policy_area)

                policies.append(
                    {
                        "name": policy_name,
                        "content": content,
                        "jurisdiction": jurisdiction,
                        "theme": theme,
                        "context": content[:200] + "..." if len(content) > 200 else content,
                    }
                )

    return policies


def _extract_jurisdiction(content: str, policy_name: str) -> str:
    """Extract jurisdiction for a policy."""
    content_lower = content.lower()

    jurisdictions = {
        "EU": ["european union", "eu", "europe", "european"],
        "US": ["united states", "us", "america", "american", "federal"],
        "UK": ["united kingdom", "uk", "britain", "british"],
        "Germany": ["germany", "german", "deutschland"],
        "France": ["france", "french"],
        "International": ["international", "global", "worldwide"],
    }

    for jurisdiction, keywords in jurisdictions.items():
        if any(keyword in content_lower for keyword in keywords):
            return jurisdiction

    return "Unknown"


def _extract_policy_theme(content: str, policy_name: str, policy_area: str = None) -> str:
    """Extract theme for a policy."""
    content_lower = content.lower()
    policy_lower = policy_name.lower()

    themes = {
        "data_privacy": ["privacy", "data protection", "gdpr", "personal data"],
        "ai_regulation": ["artificial intelligence", "ai", "machine learning", "algorithm"],
        "digital_services": ["digital", "platform", "online", "internet"],
        "competition": ["competition", "antitrust", "monopoly", "market"],
        "financial": ["financial", "banking", "payment", "money"],
        "environmental": ["environment", "climate", "carbon", "green"],
        "cybersecurity": ["cyber", "security", "breach", "protection"],
        "trade": ["trade", "import", "export", "commerce"],
    }

    # Use policy area as primary theme if provided
    if policy_area:
        return policy_area.lower().replace(" ", "_")

    # Score themes
    theme_scores = {}
    for theme, keywords in themes.items():
        score = sum(
            content_lower.count(keyword) + policy_lower.count(keyword) for keyword in keywords
        )
        if score > 0:
            theme_scores[theme] = score

    if theme_scores:
        return max(theme_scores.items(), key=lambda x: x[1])[0]

    return "general"


def _calculate_policy_cohesion(policies: list[dict[str, Any]], cluster_type: str) -> float:
    """Calculate cohesion within a policy cluster."""
    if len(policies) < 2:
        return 0.0

    # Calculate based on shared characteristics
    if cluster_type == "theme":
        # All policies share the same theme
        return 0.8 + (0.2 * min(len(policies) / 10, 1))  # Bonus for larger clusters
    elif cluster_type == "jurisdiction":
        # Check theme diversity within jurisdiction
        themes = set(p["theme"] for p in policies)
        diversity_penalty = len(themes) / len(policies)
        return max(0.6 - diversity_penalty, 0.3)
    elif cluster_type == "temporal":
        # Check theme and jurisdiction diversity within time period
        themes = set(p["theme"] for p in policies)
        jurisdictions = set(p["jurisdiction"] for p in policies)
        diversity_score = (len(themes) + len(jurisdictions)) / (2 * len(policies))
        return max(0.7 - diversity_score, 0.3)

    return 0.5


def _extract_cluster_relationships(policies: list[dict[str, Any]]) -> list[str]:
    """Extract common relationships within a policy cluster."""
    # Extract common terms that might indicate relationships
    all_content = " ".join(p["content"] for p in policies).lower()

    relationship_terms = [
        "implements", "amends", "supersedes", "complements", "enforces",
        "requires", "mandates", "prohibits", "regulates", "governs",
    ]

    found_relationships = []
    for term in relationship_terms:
        if term in all_content:
            found_relationships.append(term)

    return found_relationships


def _cluster_policies(
    results: list[Any], cluster_method: str, policy_area: str = None
) -> list[dict[str, Any]]:
    """Cluster policies based on the specified method."""
    import re

    # Extract policies from results
    policies = []
    for result in results:
        content = ""
        if hasattr(result, "fact") and result.fact:
            content = result.fact
        elif hasattr(result, "summary") and result.summary:
            content = result.summary

        if content:
            extracted_policies = _extract_policies_from_content(content, policy_area)
            policies.extend(extracted_policies)

    # Remove duplicates
    unique_policies = []
    seen_names = set()
    for policy in policies:
        if policy["name"] not in seen_names:
            unique_policies.append(policy)
            seen_names.add(policy["name"])

    policies = unique_policies

    if not policies:
        return []

    # Apply clustering method
    if cluster_method == "thematic":
        # Cluster by theme
        theme_clusters = {}
        for policy in policies:
            theme = policy["theme"]
            if theme not in theme_clusters:
                theme_clusters[theme] = []
            theme_clusters[theme].append(policy)

        clusters = []
        for theme, theme_policies in theme_clusters.items():
            if len(theme_policies) >= 2:  # Minimum cluster size
                cohesion = _calculate_policy_cohesion(theme_policies, "theme")
                relationships = _extract_cluster_relationships(theme_policies)

                clusters.append({
                    "name": theme.replace("_", " "),
                    "theme": theme,
                    "policies": theme_policies,
                    "cohesion": cohesion,
                    "relationships": relationships,
                })

        return sorted(clusters, key=lambda x: x["cohesion"], reverse=True)

    elif cluster_method == "jurisdictional":
        # Cluster by jurisdiction
        jurisdiction_clusters = {}
        for policy in policies:
            jurisdiction = policy["jurisdiction"]
            if jurisdiction not in jurisdiction_clusters:
                jurisdiction_clusters[jurisdiction] = []
            jurisdiction_clusters[jurisdiction].append(policy)

        clusters = []
        for jurisdiction, juris_policies in jurisdiction_clusters.items():
            if len(juris_policies) >= 2:
                cohesion = _calculate_policy_cohesion(juris_policies, "jurisdiction")
                relationships = _extract_cluster_relationships(juris_policies)

                clusters.append({
                    "name": jurisdiction,
                    "theme": "jurisdictional",
                    "policies": juris_policies,
                    "cohesion": cohesion,
                    "relationships": relationships,
                })

        return sorted(clusters, key=lambda x: x["cohesion"], reverse=True)

    elif cluster_method == "temporal":
        # Cluster by temporal periods
        temporal_clusters = {}
        for policy in policies:
            years = re.findall(r"\b(20\d{2})\b", policy["content"])
            if years:
                decade = f"{years[0][:3]}0s"
                if decade not in temporal_clusters:
                    temporal_clusters[decade] = []
                temporal_clusters[decade].append(policy)
            else:
                if "unknown" not in temporal_clusters:
                    temporal_clusters["unknown"] = []
                temporal_clusters["unknown"].append(policy)

        clusters = []
        for period, period_policies in temporal_clusters.items():
            if len(period_policies) >= 2:
                cohesion = _calculate_policy_cohesion(period_policies, "temporal")
                relationships = _extract_cluster_relationships(period_policies)

                clusters.append({
                    "name": period,
                    "theme": "temporal",
                    "policies": period_policies,
                    "cohesion": cohesion,
                    "relationships": relationships,
                })

        return sorted(clusters, key=lambda x: x["cohesion"], reverse=True)

    # Default to thematic
    return _cluster_policies(results, "thematic", policy_area)


async def handle_get_policy_clusters(
    policy_area: str = None,
    cluster_method: str = "thematic",
    max_clusters: int = 5
) -> list[TextContent]:
    """Handle get_policy_clusters tool - identify policy clusters."""
    from graphiti_core.search.search_config_recipes import NODE_HYBRID_SEARCH_RRF

    logger.info(f"Identifying policy clusters (area: {policy_area}, method: {cluster_method})")

    try:
        # Build policy search query
        if policy_area:
            search_query = f"{policy_area} policy regulation law directive act legislation"
        else:
            search_query = "policy regulation law directive act legislation rules"

        # Use node search for better policy entity detection
        await retriever.executor.initialize()
        graphiti_client = retriever.executor.graphiti_client

        search_results = await graphiti_client._search(
            query=search_query, config=NODE_HYBRID_SEARCH_RRF
        )

        # Extract results
        results = []
        if hasattr(search_results, "edges") and search_results.edges:
            results.extend(search_results.edges)
        if hasattr(search_results, "nodes") and search_results.nodes:
            results.extend(search_results.nodes)

        if not results:
            return [TextContent(type="text", text=f"No policies found for area: {policy_area or 'general'}")]

        # Extract and cluster policies
        policy_clusters = _cluster_policies(results, cluster_method, policy_area)

        # Limit to max clusters
        policy_clusters = policy_clusters[:max_clusters]

        # Format policy clusters analysis
        output = ["## Policy Clusters Analysis", ""]
        if policy_area:
            output.append(f"**Policy Area**: {policy_area}")
        output.append(f"**Clustering Method**: {cluster_method}")
        output.append(f"**Clusters Found**: {len(policy_clusters)}")
        output.append("")

        if policy_clusters:
            output.append("### Policy Clusters:")
            output.append("")
            for i, cluster in enumerate(policy_clusters, 1):
                output.append(f"#### Cluster {i}: {cluster['name'].title()}")
                output.append(f"**Theme**: {cluster['theme']}")
                output.append(f"**Policies**: {len(cluster['policies'])}")
                output.append(f"**Cohesion**: {cluster['cohesion']:.2f}")

                output.append("**Key Policies**:")
                for j, policy in enumerate(cluster["policies"][:5], 1):
                    output.append(f"  {j}. {policy['name']}")
                    if policy["jurisdiction"]:
                        output.append(f"     Jurisdiction: {policy['jurisdiction']}")

                if len(cluster["policies"]) > 5:
                    output.append(f"  ... and {len(cluster['policies']) - 5} more policies")

                if cluster["relationships"]:
                    output.append(f"**Common Relationships**: {', '.join(cluster['relationships'][:3])}")
                output.append("")

            # Cluster insights
            output.append("### Cluster Insights:")
            total_policies = sum(len(c["policies"]) for c in policy_clusters)
            avg_cluster_size = total_policies / len(policy_clusters) if policy_clusters else 0
            high_cohesion = len([c for c in policy_clusters if c["cohesion"] > 0.7])

            output.append(f"- **Total policies clustered**: {total_policies}")
            output.append(f"- **Average cluster size**: {avg_cluster_size:.1f} policies")
            output.append(f"- **High-cohesion clusters**: {high_cohesion}")
            output.append(f"- **Policy landscape complexity**: {'High' if len(policy_clusters) > 3 else 'Medium' if len(policy_clusters) > 1 else 'Low'}")
        else:
            output.append("No clear policy clusters found.")
            output.append("")
            output.append("**Suggestions:**")
            output.append("- Try broader policy area terms")
            output.append("- Use different clustering method")
            output.append("- Expand search to include related terms")

        logger.info(f"Found {len(policy_clusters)} policy clusters")
        return [TextContent(type="text", text="\n".join(output))]

    except Exception as e:
        logger.error(f"Error clustering policies: {e}")
        return [TextContent(type="text", text=f"Error clustering policies: {str(e)}")]


# =============================================================================
# Graph Traversal Tool Handlers
# =============================================================================

async def _find_entity_node(entity_name: str) -> dict | None:
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

        await retriever.executor.initialize()
        async with await retriever.executor._get_session() as session:
            result = await session.run(query, {"entity_name": entity_name})
            records = await result.data()

            if records:
                best_match = records[0]
                logger.info(f"Found entity node: {best_match['name']} (UUID: {best_match['uuid']})")
                return best_match

            logger.warning(f"No entity node found for: {entity_name}")
            return None

    except Exception as e:
        logger.error(f"Error finding entity node: {e}", exc_info=True)
        return None


def _calculate_relevance_score(entity_data: dict, source_entity_name: str) -> float:
    """Calculate relevance score for a traversal result."""
    score = 0.0

    # Factor 1: Depth (inverse weight - closer is more relevant)
    depth = entity_data.get("depth", 1)
    score += 10.0 / depth

    # Factor 2: Relationship fact richness
    rel_chain = entity_data.get("relationship_chain", [])
    for hop in rel_chain:
        fact = hop.get("fact", "")
        if fact:
            fact_score = min(len(fact) / 100.0, 3.0)
            score += fact_score

    # Factor 3: Relationship type importance
    important_rel_types = {
        "AFFECTS": 3.0, "REGULATES": 3.0, "GOVERNS": 3.0,
        "ENFORCES": 2.5, "REQUIRES_COMPLIANCE": 2.5, "SUBJECT_TO": 2.5,
        "IMPLEMENTS": 2.0, "PROPOSES": 2.0, "INFLUENCES": 1.5,
        "RELATES_TO": 1.0, "REFERENCES": 1.0,
    }
    for hop in rel_chain:
        rel_type = hop.get("type", "")
        type_score = important_rel_types.get(rel_type, 0.5)
        score += type_score

    # Factor 4: Entity type relevance
    target_types = entity_data.get("target_types", [])
    important_entity_types = {
        "Policy": 3.0, "Regulation": 3.0, "LegislativeProposal": 2.5,
        "Politician": 2.0, "Organization": 2.0, "Company": 2.0,
        "GovernmentAgency": 2.0, "LegislativeBody": 1.5, "Committee": 1.5,
    }
    for entity_type in target_types:
        if entity_type != "Entity":
            type_score = important_entity_types.get(entity_type, 1.0)
            score += type_score

    # Factor 5: Path diversity bonus
    unique_rel_types = set(hop.get("type", "") for hop in rel_chain)
    if len(unique_rel_types) > 1:
        score += 1.0 * len(unique_rel_types)

    return score


async def handle_traverse_from_entity(
    entity_name: str,
    max_depth: int = 2,
    max_results: int = 15
) -> list[TextContent]:
    """Handle traverse_from_entity tool - multi-hop graph traversal with relevance filtering."""
    logger.info(f"Traversing from entity: {entity_name} (depth={max_depth})")

    try:
        # Step 1: Find entity node
        entity_node = await _find_entity_node(entity_name)

        if not entity_node:
            return [TextContent(type="text", text=f"❌ Entity '{entity_name}' not found in knowledge graph.\n\n**Suggestions:**\n- Try a different spelling or abbreviation\n- Use the search tool first to find exact entity names\n- Check if the entity exists in the graph")]

        resolved_name = entity_node["name"]
        entity_uuid = entity_node["uuid"]

        # Step 2: Execute Cypher-based graph traversal
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

        await retriever.executor.initialize()
        async with await retriever.executor._get_session() as session:
            result = await session.run(
                query,
                {"entity_uuid": entity_uuid, "max_results": max_results * 3}
            )
            traversal_results = await result.data()

        if not traversal_results:
            return [TextContent(type="text", text=f"## Relationship Traversal from: {resolved_name}\n\n❌ No connections found within {max_depth} hops.\n\n**Suggestions:**\n- Increase max_depth to explore further\n- Try exploring neighbors of related entities\n- Verify the entity has relationships in the graph")]

        # Step 3: Apply relevance filtering
        scored_results = []
        for result in traversal_results:
            score = _calculate_relevance_score(result, resolved_name)
            scored_results.append({"data": result, "relevance_score": score})

        scored_results.sort(key=lambda x: x["relevance_score"], reverse=True)
        filtered_results = [item["data"] for item in scored_results[:max_results]]

        # Step 4: Format output
        output = [
            f"## Relationship Traversal from: {resolved_name}",
            "",
            f"**Traversal Depth**: {max_depth} levels",
            f"**Total Entities Found**: {len(traversal_results)} (showing top {len(filtered_results)} most relevant)",
            "**Relevance Filtering**: Applied intelligent scoring based on relationship importance, path distance, and context richness",
            ""
        ]

        # Group by depth level
        depth_groups = {}
        for result in filtered_results:
            depth = result["depth"]
            if depth not in depth_groups:
                depth_groups[depth] = []
            depth_groups[depth].append(result)

        # Display results by depth level
        for depth in sorted(depth_groups.keys()):
            entities_at_depth = depth_groups[depth]
            output.append(f"### Level {depth} Connections ({len(entities_at_depth)} entities):")
            output.append("")

            for entity_data in entities_at_depth[:10]:
                target_name = entity_data["target_name"]
                target_types = entity_data.get("target_types", [])
                rel_chain = entity_data.get("relationship_chain", [])

                entity_types_str = (
                    ", ".join([t for t in target_types if t != "Entity"])
                    if target_types else "Unknown"
                )
                output.append(f"**{target_name}** ({entity_types_str})")

                if rel_chain:
                    path_str = " → ".join(
                        [f"{hop['source_name']} --[{hop['type']}]--> {hop['target_name']}"
                         for hop in rel_chain]
                    )
                    if len(path_str) > 150:
                        path_str = path_str[:150] + "..."
                    output.append(f"  Path: {path_str}")

                    if rel_chain[0].get("fact"):
                        fact = rel_chain[0]["fact"]
                        if len(fact) > 100:
                            fact = fact[:100] + "..."
                        output.append(f"  Context: {fact}")

                output.append("")

            if len(entities_at_depth) > 10:
                output.append(f"  ... and {len(entities_at_depth) - 10} more entities at this level")
                output.append("")

        # Add summary
        output.append("---")
        output.append("")
        output.append("## Summary")
        output.append("")

        # Entities found
        entities_found = {}
        for result in filtered_results:
            uuid = result.get("target_uuid")
            if uuid and uuid not in entities_found:
                entities_found[uuid] = {
                    "name": result["target_name"],
                    "types": [t for t in result.get("target_types", []) if t != "Entity"],
                }

        output.append(f"### Entities Found ({len(entities_found)})")
        for entity in list(entities_found.values())[:10]:
            types_str = ", ".join(entity["types"]) if entity["types"] else "Entity"
            output.append(f"- **{entity['name']}** ({types_str})")
        if len(entities_found) > 10:
            output.append(f"- ... and {len(entities_found) - 10} more entities")
        output.append("")

        # Relationships discovered
        relationships_discovered = {}
        for result in filtered_results:
            rel_chain = result.get("relationship_chain", [])
            for hop in rel_chain:
                rel_type = hop["type"]
                relationships_discovered[rel_type] = relationships_discovered.get(rel_type, 0) + 1

        output.append(f"### Relationships Discovered ({len(relationships_discovered)} types)")
        sorted_rels = sorted(relationships_discovered.items(), key=lambda x: x[1], reverse=True)
        for rel_type, count in sorted_rels[:10]:
            output.append(f"- **{rel_type}**: {count} occurrence{'s' if count > 1 else ''}")

        logger.info(f"Traversal found {len(traversal_results)} total entities, filtered to {len(filtered_results)} most relevant")
        return [TextContent(type="text", text="\n".join(output))]

    except Exception as e:
        logger.error(f"Error in traversal: {e}", exc_info=True)
        return [TextContent(type="text", text=f"❌ Error traversing from {entity_name}: {str(e)}\n\nPlease check logs for details.")]


async def handle_find_paths_between_entities(
    source_entity: str,
    target_entity: str,
    max_path_length: int = 4,
    max_paths: int = 5
) -> list[TextContent]:
    """Handle find_paths_between_entities tool - find connection paths."""
    logger.info(f"Finding paths between: {source_entity} -> {target_entity}")

    try:
        # Step 1: Find both entity nodes
        source_node = await _find_entity_node(source_entity)
        if not source_node:
            return [TextContent(type="text", text=f"❌ Source entity '{source_entity}' not found in knowledge graph.\n\nPlease verify the entity name or try a related search.")]

        target_node = await _find_entity_node(target_entity)
        if not target_node:
            return [TextContent(type="text", text=f"❌ Target entity '{target_entity}' not found in knowledge graph.\n\nPlease verify the entity name or try a related search.")]

        source_name = source_node["name"]
        target_name = target_node["name"]

        # Step 2: Find paths using Neo4j shortest path algorithms
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

        await retriever.executor.initialize()
        async with await retriever.executor._get_session() as session:
            result = await session.run(
                query,
                {
                    "source_uuid": source_node["uuid"],
                    "target_uuid": target_node["uuid"],
                    "max_paths": max_paths
                }
            )
            paths = await result.data()

        if not paths:
            return [TextContent(type="text", text=f"## Connection Paths: {source_name} ↔ {target_name}\n\n❌ No paths found within {max_path_length} hops.\n\n**Suggestions:**\n- Increase max_path_length to explore longer paths\n- Try finding paths to intermediate entities\n- Use traverse_from_entity tool to explore each entity's connections\n- Verify both entities are in the same connected component")]

        # Step 3: Format output
        output = [
            f"## Connection Paths: {source_name} ↔ {target_name}",
            "",
            f"**Maximum Path Length**: {max_path_length} hop(s)",
            f"**Paths Found**: {len(paths)}",
            ""
        ]

        all_entities = {}
        all_relationships = {}

        for idx, path_data in enumerate(paths, 1):
            path_nodes = path_data["path_nodes"]
            path_relationships = path_data["path_relationships"]
            path_length = path_data["path_length"]

            output.append(f"### Path {idx} ({path_length} hop{'s' if path_length != 1 else ''})")

            # Build path chain visualization
            path_chain = []
            for i, node in enumerate(path_nodes):
                node_name = node["name"]
                node_types = node.get("types", [])
                node_type = next((t for t in node_types if t != "Entity"), "Entity")

                all_entities[node["uuid"]] = {"name": node_name, "type": node_type}

                if i < len(path_relationships):
                    rel = path_relationships[i]
                    rel_type = rel["type"]
                    all_relationships[rel_type] = all_relationships.get(rel_type, 0) + 1
                    path_chain.append(f"{node_name} —[{rel_type}]→ ")
                else:
                    path_chain.append(node_name)

            output.append("**Path Chain**: " + "".join(path_chain))
            output.append("")

            # Display relationship details
            output.append("**Relationships**:")
            for i, rel in enumerate(path_relationships, 1):
                rel_type = rel["type"]
                fact = rel.get("fact", "")
                source_name = rel.get("source_name", "")
                target_name = rel.get("target_name", "")

                output.append(f"{i}. **{rel_type}**: {source_name} → {target_name}")
                if fact:
                    display_fact = fact[:200] + "..." if len(fact) > 200 else fact
                    output.append(f"   *Context*: {display_fact}")

            output.append("")

        # Add summary
        output.append("---")
        output.append("")
        output.append("## Summary")
        output.append("")

        if all_entities:
            output.append(f"### Entities Found ({len(all_entities)})")
            for entity_data in list(all_entities.values())[:20]:
                output.append(f"- **{entity_data['name']}** ({entity_data['type']})")
            output.append("")

        if all_relationships:
            output.append(f"### Relationships Discovered ({len(all_relationships)} types)")
            sorted_rels = sorted(all_relationships.items(), key=lambda x: x[1], reverse=True)
            for rel_type, count in sorted_rels[:15]:
                output.append(f"- **{rel_type}**: {count} occurrence(s)")

        logger.info(f"Found {len(paths)} paths between {source_name} and {target_name}")
        return [TextContent(type="text", text="\n".join(output))]

    except Exception as e:
        logger.error(f"Error finding paths: {e}", exc_info=True)
        return [TextContent(type="text", text=f"❌ Error finding paths between {source_entity} and {target_entity}: {str(e)}\n\nPlease check logs for details.")]


async def handle_get_entity_neighbors(
    entity_name: str,
    max_depth: int = 1
) -> list[TextContent]:
    """Handle get_entity_neighbors tool - get directly connected entities."""
    logger.info(f"Getting neighbors for: {entity_name} (max_depth={max_depth})")

    try:
        # Step 1: Find entity node
        entity_node = await _find_entity_node(entity_name)
        if not entity_node:
            return [TextContent(type="text", text=f"❌ Entity '{entity_name}' not found in knowledge graph.\n\nPlease verify the entity name or try a related search.")]

        entity_uuid = entity_node["uuid"]
        resolved_name = entity_node["name"]

        # Step 2: Get neighbors using Cypher queries (bidirectional)
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
            LIMIT 50
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
            LIMIT 50
        """

        await retriever.executor.initialize()
        async with await retriever.executor._get_session() as session:
            outgoing_result = await session.run(outgoing_query, {"entity_uuid": entity_uuid})
            outgoing = await outgoing_result.data()

            incoming_result = await session.run(incoming_query, {"entity_uuid": entity_uuid})
            incoming = await incoming_result.data()

        if not outgoing and not incoming:
            return [TextContent(type="text", text=f"## Neighbors of: {resolved_name}\n\n❌ No direct neighbors found.\n\n**Suggestions**:\n- Entity may be isolated in the graph\n- Try increasing max_depth\n- Check if entity has relationships in the knowledge graph")]

        # Step 3: Format output
        output = [
            f"## Neighbors of: {resolved_name}",
            "",
            f"**Search Depth**: {max_depth} hop(s)",
            f"**Total Neighbors Found**: {len(outgoing) + len(incoming)} ({len(outgoing)} outgoing, {len(incoming)} incoming)",
            ""
        ]

        # Format outgoing neighbors
        if outgoing:
            output.append(f"### Outgoing Relationships ({len(outgoing)} neighbors)")
            output.append(f"*{resolved_name} influences or relates to these entities:*")
            output.append("")

            for idx, neighbor in enumerate(outgoing[:20], 1):
                neighbor_name = neighbor["neighbor_name"]
                neighbor_types = [t for t in neighbor.get("neighbor_types", []) if t != "Entity"]
                rel_chain = neighbor.get("relationship_chain", [])

                rel_types = " → ".join(hop["type"] for hop in rel_chain)

                output.append(f"{idx}. **{neighbor_name}**")
                if neighbor_types:
                    output.append(f"   *({', '.join(neighbor_types)})*")
                output.append(f"   - Relationship: {rel_types}")

                if rel_chain and rel_chain[0].get("fact"):
                    fact = rel_chain[0]["fact"]
                    fact_preview = fact[:120] + "..." if len(fact) > 120 else fact
                    output.append(f"   - Context: {fact_preview}")

                output.append("")

            if len(outgoing) > 20:
                output.append(f"*... and {len(outgoing) - 20} more outgoing neighbors*")
                output.append("")
        else:
            output.append("### Outgoing Relationships (0)")
            output.append("*No outgoing relationships found*")
            output.append("")

        # Format incoming neighbors
        if incoming:
            output.append(f"### Incoming Relationships ({len(incoming)} neighbors)")
            output.append(f"*These entities influence or relate to {resolved_name}:*")
            output.append("")

            for idx, neighbor in enumerate(incoming[:20], 1):
                neighbor_name = neighbor["neighbor_name"]
                neighbor_types = [t for t in neighbor.get("neighbor_types", []) if t != "Entity"]
                rel_chain = neighbor.get("relationship_chain", [])

                rel_types = " → ".join(hop["type"] for hop in rel_chain)

                output.append(f"{idx}. **{neighbor_name}**")
                if neighbor_types:
                    output.append(f"   *({', '.join(neighbor_types)})*")
                output.append(f"   - Relationship: {rel_types}")

                if rel_chain and rel_chain[0].get("fact"):
                    fact = rel_chain[0]["fact"]
                    fact_preview = fact[:120] + "..." if len(fact) > 120 else fact
                    output.append(f"   - Context: {fact_preview}")

                output.append("")

            if len(incoming) > 20:
                output.append(f"*... and {len(incoming) - 20} more incoming neighbors*")
                output.append("")
        else:
            output.append("### Incoming Relationships (0)")
            output.append("*No incoming relationships found*")
            output.append("")

        # Add summary
        output.append("---")
        output.append("")
        output.append("## Summary")
        output.append("")

        # Collect unique entities
        all_neighbors = {}
        for neighbor in outgoing + incoming:
            uuid = neighbor["neighbor_uuid"]
            if uuid not in all_neighbors:
                all_neighbors[uuid] = {
                    "name": neighbor["neighbor_name"],
                    "types": [t for t in neighbor.get("neighbor_types", []) if t != "Entity"],
                }

        output.append(f"### Entities Found ({len(all_neighbors)})")
        for neighbor_data in sorted(all_neighbors.values(), key=lambda x: x["name"])[:20]:
            types_str = f" ({', '.join(neighbor_data['types'])})" if neighbor_data["types"] else ""
            output.append(f"- **{neighbor_data['name']}**{types_str}")
        if len(all_neighbors) > 20:
            output.append(f"- *... and {len(all_neighbors) - 20} more*")
        output.append("")

        # Relationships discovered
        relationships_count = {}
        for neighbor in outgoing + incoming:
            rel_chain = neighbor.get("relationship_chain", [])
            for hop in rel_chain:
                rel_type = hop["type"]
                relationships_count[rel_type] = relationships_count.get(rel_type, 0) + 1

        output.append(f"### Relationships Discovered ({len(relationships_count)} types)")
        for rel_type, count in sorted(relationships_count.items(), key=lambda x: -x[1]):
            output.append(f"- **{rel_type}**: {count} occurrence(s)")

        logger.info(f"Found {len(outgoing)} outgoing and {len(incoming)} incoming neighbors for {resolved_name}")
        return [TextContent(type="text", text="\n".join(output))]

    except Exception as e:
        logger.error(f"Error getting neighbors: {e}", exc_info=True)
        return [TextContent(type="text", text=f"❌ Error getting neighbors for {entity_name}: {str(e)}\n\nPlease check logs for details.")]


async def handle_analyze_entity_impact(
    entity_name: str,
    impact_types: list[str] = None,
    max_hops: int = 3
) -> list[TextContent]:
    """Handle analyze_entity_impact tool - analyze impact network."""
    from graphiti_core.search.search_config_recipes import EDGE_HYBRID_SEARCH_RRF

    logger.info(f"Analyzing impact network for: {entity_name}")

    try:
        # Build impact-focused search query
        impact_keywords = [
            "affects", "impacts", "influences", "regulates", "governs",
            "requires", "mandates", "applies to", "enforces",
        ]

        search_query = f"{entity_name} " + " ".join(impact_keywords)
        if impact_types:
            search_query += " " + " ".join(impact_types)

        # Use advanced search for impact analysis
        await retriever.executor.initialize()
        graphiti_client = retriever.executor.graphiti_client

        search_results = await graphiti_client._search(search_query, config=EDGE_HYBRID_SEARCH_RRF)

        # Extract edges for impact analysis
        results = []
        if hasattr(search_results, "edges") and search_results.edges:
            results.extend(search_results.edges)

        if not results:
            return [TextContent(type="text", text=f"No impact information found for entity '{entity_name}'")]

        # Categorize impacts
        direct_impacts = []
        indirect_impacts = []
        mutual_impacts = []

        for result in results:
            fact = result.fact
            fact_lower = fact.lower()
            entity_lower = entity_name.lower()

            if entity_lower in fact_lower:
                entity_pos = fact_lower.find(entity_lower)
                after_entity = fact_lower[entity_pos + len(entity_lower):]
                before_entity = fact_lower[:entity_pos]

                impact_direction = "unclear"
                if any(keyword in after_entity for keyword in ["affects", "impacts", "regulates", "governs"]):
                    impact_direction = "outbound"
                elif any(keyword in before_entity for keyword in ["affects", "impacts", "regulates", "governed by"]):
                    impact_direction = "inbound"
                elif any(keyword in fact_lower for keyword in ["mutual", "bidirectional", "interconnected"]):
                    impact_direction = "mutual"

                impact_info = {
                    "fact": fact,
                    "direction": impact_direction,
                    "relationship": getattr(result, "name", "IMPACTS"),
                }

                if impact_direction == "outbound":
                    direct_impacts.append(impact_info)
                elif impact_direction == "inbound":
                    indirect_impacts.append(impact_info)
                elif impact_direction == "mutual":
                    mutual_impacts.append(impact_info)
                else:
                    direct_impacts.append(impact_info)

        # Format impact analysis
        output = [f"## Impact Analysis: {entity_name}", ""]

        total_impacts = len(direct_impacts) + len(indirect_impacts) + len(mutual_impacts)
        output.append(f"**Total Impact Relationships**: {total_impacts}")
        output.append("")

        if direct_impacts:
            output.append(f"### What {entity_name} Impacts ({len(direct_impacts)} relationships):")
            for i, impact in enumerate(direct_impacts[:8], 1):
                output.append(f"{i}. {impact['fact']}")
            if len(direct_impacts) > 8:
                output.append(f"... and {len(direct_impacts) - 8} more direct impacts")
            output.append("")

        if indirect_impacts:
            output.append(f"### What Impacts {entity_name} ({len(indirect_impacts)} relationships):")
            for i, impact in enumerate(indirect_impacts[:8], 1):
                output.append(f"{i}. {impact['fact']}")
            if len(indirect_impacts) > 8:
                output.append(f"... and {len(indirect_impacts) - 8} more indirect impacts")
            output.append("")

        if mutual_impacts:
            output.append(f"### Mutual/Bidirectional Impacts ({len(mutual_impacts)} relationships):")
            for i, impact in enumerate(mutual_impacts[:5], 1):
                output.append(f"{i}. {impact['fact']}")
            output.append("")

        if total_impacts > 0:
            output.append("### Impact Assessment:")
            if len(direct_impacts) > len(indirect_impacts):
                output.append(f"- **{entity_name} is primarily an influencer** - impacts more entities than it's impacted by")
            elif len(indirect_impacts) > len(direct_impacts):
                output.append(f"- **{entity_name} is primarily influenced** - more impacted by other entities")
            else:
                output.append(f"- **{entity_name} has balanced influence** - roughly equal inbound and outbound impacts")

            output.append(f"- **Network centrality**: {'High' if total_impacts > 10 else 'Medium' if total_impacts > 5 else 'Low'}")
        else:
            output.append(f"No clear impact relationships found for {entity_name}.")

        logger.info(f"Impact analysis found {total_impacts} total impacts")
        return [TextContent(type="text", text="\n".join(output))]

    except Exception as e:
        logger.error(f"Error in impact analysis: {e}")
        return [TextContent(type="text", text=f"Error analyzing impact for {entity_name}: {str(e)}")]


# =============================================================================
# Similarity Tool Handler
# =============================================================================

async def handle_find_similar_entities(
    entity_name: str,
    max_similar: int = 5
) -> list[TextContent]:
    """Handle find_similar_entities tool - find similar entities."""
    from graphiti_core.search.search_config_recipes import NODE_HYBRID_SEARCH_RRF
    import re

    logger.info(f"Finding similar entities to: {entity_name}")

    try:
        # Search for similar entities using context and relationships
        search_query = f"{entity_name} similar like comparable equivalent type category"

        # Use node-focused search for entity similarity
        await retriever.executor.initialize()
        graphiti_client = retriever.executor.graphiti_client

        search_results = await graphiti_client._search(search_query, config=NODE_HYBRID_SEARCH_RRF)

        # Extract both nodes and edges
        results = []
        if hasattr(search_results, "edges") and search_results.edges:
            results.extend(search_results.edges)
        if hasattr(search_results, "nodes") and search_results.nodes:
            results.extend(search_results.nodes)

        if not results:
            return [TextContent(type="text", text=f"No similar entities found for '{entity_name}'")]

        # Extract potential similar entities from facts
        similar_entities = {}

        for result in results:
            content = ""
            if hasattr(result, "fact") and result.fact:
                content = result.fact
            elif hasattr(result, "summary") and result.summary:
                content = result.summary
            elif hasattr(result, "name") and result.name:
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

            # Look for capitalized phrases that might be entity names
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
        output = [f"## Similar Entities to: {entity_name}", ""]

        if ranked_similar:
            output.append("**Most Similar Entities:**")
            for i, (similar_entity, contexts) in enumerate(ranked_similar, 1):
                output.append(f"{i}. **{similar_entity}** (appears together in {len(contexts)} context(s))")
                if contexts:
                    context_preview = contexts[0][:100] + "..." if len(contexts[0]) > 100 else contexts[0]
                    output.append(f"   Example: {context_preview}")
            output.append("")
        else:
            output.append(f"No clearly similar entities identified for {entity_name}.")
            output.append("")

        output.append("*Note: For more sophisticated similarity analysis, consider using community detection tools to find entities in the same cluster.*")

        logger.info(f"Found {len(ranked_similar)} similar entities for {entity_name}")
        return [TextContent(type="text", text="\n".join(output))]

    except Exception as e:
        logger.error(f"Error finding similar entities: {e}")
        return [TextContent(type="text", text=f"Error finding similar entities to {entity_name}: {str(e)}")]


# =============================================================================
# FastAPI Application
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    global retriever
    
    logger.info("Starting Graph Context Retrieval MCP Server...")
    
    # Load configuration from environment
    config = Neo4jConfig(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        user=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "password123"),
        database=os.getenv("NEO4J_DATABASE", "politicalmonitoring.v3"),
    )
    
    logger.info(f"Connecting to Neo4j at {config.uri}, database: {config.database}")
    
    # Initialize retriever
    retriever = GraphContextRetriever(config)
    await retriever.executor.initialize()
    
    logger.info("Graph Context Retrieval MCP Server started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Graph Context Retrieval MCP Server...")
    await retriever.close()
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Graph Context Retrieval MCP Server",
    description="MCP server for querying Neo4j/Graphiti knowledge graphs with intelligent context retrieval",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SSE Transport - handles both GET (SSE stream) and POST (messages)
sse = SseServerTransport("/messages/")


async def handle_sse(request: Request):
    """Handle SSE connections for MCP."""
    logger.info(f"SSE connection from: {request.client}")
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp_server.run(
            streams[0], streams[1], mcp_server.create_initialization_options()
        )


async def handle_messages(request: Request):
    """Handle POST messages for MCP."""
    await sse.handle_post_message(request.scope, request.receive, request._send)


# Mount SSE endpoint for GET connections
app.add_api_route("/sse", handle_sse, methods=["GET"])
# Mount messages endpoint for POST (the SseServerTransport sends clients here)
app.add_api_route("/messages/", handle_messages, methods=["POST"])


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    config = retriever.config if retriever else Neo4jConfig()
    
    try:
        if retriever:
            await retriever.executor.initialize()
        neo4j_status = "connected"
    except Exception as e:
        neo4j_status = f"error: {str(e)}"
    
    return HealthResponse(
        status="healthy",
        server="graph-context-retrieval",
        neo4j_uri=config.uri,
        neo4j_database=config.database,
        neo4j_status=neo4j_status
    )


@app.get("/")
async def info():
    """Server info endpoint."""
    config = retriever.config if retriever else Neo4jConfig()
    
    return JSONResponse({
        "name": "graph-context-retrieval",
        "version": "1.0.0",
        "description": "MCP server for querying Neo4j/Graphiti knowledge graphs",
        "endpoints": {
            "sse": "/sse",
            "health": "/health",
            "info": "/"
        },
        "tools": [
            # Base tools
            "search_knowledge_graph",
            "analyze_query",
            "get_entity_info",
            "find_relationships",
            "graph_statistics",
            "search_documents",
            # Temporal tools
            "search_by_date_range",
            "get_entity_history",
            "find_concurrent_events",
            "compare_timelines",
            "track_policy_evolution",
            # Community tools
            "get_communities",
            "get_community_members",
            "get_policy_clusters",
            # Traversal tools
            "traverse_from_entity",
            "find_paths_between_entities",
            "get_entity_neighbors",
            "analyze_entity_impact",
            # Similarity tool
            "find_similar_entities"
        ],
        "config": {
            "neo4j_uri": config.uri,
            "neo4j_database": config.database
        }
    })


# REST API endpoints (optional, for direct HTTP access)

@app.post("/api/search")
async def api_search(request: SearchRequest):
    """REST API endpoint for searching."""
    context = await retriever.retrieve(request.query)
    return retriever.to_dict(context)


@app.post("/api/entity")
async def api_entity(request: EntityRequest):
    """REST API endpoint for entity info."""
    await retriever.executor.initialize()
    return await retriever.executor._get_entity_details({"entity_name": request.entity_name})


@app.post("/api/relationships")
async def api_relationships(request: EntityRequest):
    """REST API endpoint for relationships."""
    await retriever.executor.initialize()
    return await retriever.executor._get_entity_relationships({
        "entity_name": request.entity_name,
        "max_relationships": request.max_results
    })


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("MCP_PORT", "8003"))
    host = os.getenv("MCP_HOST", "0.0.0.0")
    
    print("=" * 60)
    print("  Graph Context Retrieval MCP Server")
    print("=" * 60)
    print(f"\n  Server URL: http://{host}:{port}")
    print(f"  SSE Endpoint: http://{host}:{port}/sse")
    print(f"  Health Check: http://{host}:{port}/health")
    print(f"\n  Neo4j URI: {os.getenv('NEO4J_URI', 'bolt://localhost:7687')}")
    print(f"  Neo4j Database: {os.getenv('NEO4J_DATABASE', 'politicalmonitoring.v3')}")
    print("=" * 60 + "\n")
    
    uvicorn.run(app, host=host, port=port, log_level="info")
