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
            "track_policy_evolution"
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
