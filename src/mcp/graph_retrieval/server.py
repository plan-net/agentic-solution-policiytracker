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
            summary = f" - {entity['summary'][:100]}..." if entity.get('summary') and len(entity['summary']) > 100 else (f" - {entity['summary']}" if entity.get('summary') else "")
            output.append(f"- **{entity['name']}** ({entity['type']}){summary}")
        output.append("")
    
    if result['retrieved_context']['relationships']:
        output.append(f"## Relationships ({result['metadata']['total_relationships']})")
        for rel in result['retrieved_context']['relationships'][:5]:
            output.append(f"- {rel['source']} --[{rel['type']}]--> {rel['target']}")
    
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
        output.append(f"- **{rel['source']}** --[{rel['relationship']}]--> **{rel['target']}**{fact_text}")
    
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
            "graph_statistics"
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
