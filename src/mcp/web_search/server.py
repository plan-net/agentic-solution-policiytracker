"""
Web Search MCP Server.

FastAPI server with SSE transport for Claude Agent integration.
Provides web search via Exa.ai and DPA news search.
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

from .exa_client import ExaSearchClient
from .dpa_client import DPANewsClient

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
exa_client: ExaSearchClient = None
dpa_client: DPANewsClient = None
mcp_server = Server("web-search")


# =============================================================================
# Pydantic Models
# =============================================================================

class HealthResponse(BaseModel):
    status: str
    server: str
    exa_configured: bool
    dpa_configured: bool


# =============================================================================
# MCP Server Tools
# =============================================================================

@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools for web search."""
    return [
        Tool(
            name="web_search",
            description="Search the web for information using Exa.ai. Returns web pages with content relevant to the query.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'EU AI Act implementation', 'GDPR compliance')"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Number of results to return (default: 10, max: 50)",
                        "default": 10
                    },
                    "include_domains": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Only include results from these domains (e.g., ['europa.eu', 'gov.uk'])"
                    },
                    "exclude_domains": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Exclude results from these domains"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="search_news",
            description="Search for recent news articles using Exa.ai. Best for finding current events and breaking news.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "News search query"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Number of results to return (default: 10)",
                        "default": 10
                    },
                    "days_back": {
                        "type": "integer",
                        "description": "How many days back to search (default: 7)",
                        "default": 7
                    },
                    "include_domains": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Only include results from these news sources"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="search_dpa_news",
            description="Search German Press Agency (DPA) news feed. Best for German-language news and official press releases.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (German or English)"
                    },
                    "max_items": {
                        "type": "integer",
                        "description": "Maximum number of articles (default: 10)",
                        "default": 10
                    },
                    "days_back": {
                        "type": "integer",
                        "description": "How many days back to search (default: 7)",
                        "default": 7
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_article_content",
            description="Fetch the full content of articles by their URLs. Use this to get complete text when search results only show previews.",
            inputSchema={
                "type": "object",
                "properties": {
                    "urls": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of URLs to fetch content for (max 10)"
                    }
                },
                "required": ["urls"]
            }
        ),
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle MCP tool calls for web search."""
    try:
        logger.info(f"Tool called: {name} with args: {arguments}")

        if name == "web_search":
            return await handle_web_search(arguments)
        elif name == "search_news":
            return await handle_search_news(arguments)
        elif name == "search_dpa_news":
            return await handle_search_dpa_news(arguments)
        elif name == "get_article_content":
            return await handle_get_article_content(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        logger.error(f"Tool error: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_web_search(args: dict[str, Any]) -> list[TextContent]:
    """Handle web_search tool."""
    query = args["query"]
    num_results = min(args.get("num_results", 10), 50)
    include_domains = args.get("include_domains")
    exclude_domains = args.get("exclude_domains")

    results = await exa_client.web_search(
        query=query,
        num_results=num_results,
        include_domains=include_domains,
        exclude_domains=exclude_domains,
    )

    if not results:
        return [TextContent(type="text", text=f"No web results found for: {query}")]

    output = [f"## Web Search Results for: {query}", ""]

    for i, result in enumerate(results, 1):
        output.append(f"### {i}. {result.get('title', 'Untitled')}")
        output.append(f"- **URL**: {result.get('url', 'N/A')}")
        output.append(f"- **Source**: {result.get('source', 'Unknown')}")
        if result.get('published_date'):
            output.append(f"- **Date**: {result['published_date']}")
        if result.get('content_preview'):
            output.append(f"\n{result['content_preview']}")
        output.append("")

    return [TextContent(type="text", text="\n".join(output))]


async def handle_search_news(args: dict[str, Any]) -> list[TextContent]:
    """Handle search_news tool."""
    query = args["query"]
    num_results = min(args.get("num_results", 10), 50)
    days_back = args.get("days_back", 7)
    include_domains = args.get("include_domains")

    results = await exa_client.search_news(
        query=query,
        num_results=num_results,
        days_back=days_back,
        include_domains=include_domains,
    )

    if not results:
        return [TextContent(type="text", text=f"No news found for: {query}")]

    output = [f"## News Results for: {query} (last {days_back} days)", ""]

    for i, result in enumerate(results, 1):
        output.append(f"### {i}. {result.get('title', 'Untitled')}")
        output.append(f"- **URL**: {result.get('url', 'N/A')}")
        output.append(f"- **Source**: {result.get('source', 'Unknown')}")
        if result.get('published_date'):
            output.append(f"- **Date**: {result['published_date']}")
        if result.get('author'):
            output.append(f"- **Author**: {result['author']}")
        if result.get('content_preview'):
            output.append(f"\n{result['content_preview']}")
        output.append("")

    return [TextContent(type="text", text="\n".join(output))]


async def handle_search_dpa_news(args: dict[str, Any]) -> list[TextContent]:
    """Handle search_dpa_news tool."""
    if not dpa_client.is_available():
        return [TextContent(type="text", text="DPA News search is not configured. Please set DPA_API_KEY environment variable.")]

    query = args["query"]
    max_items = min(args.get("max_items", 10), 20)
    days_back = args.get("days_back", 7)

    results = await dpa_client.search_news(
        query=query,
        max_items=max_items,
        days_back=days_back,
    )

    if not results:
        return [TextContent(type="text", text=f"No DPA news found for: {query}")]

    output = [f"## DPA News Results for: {query} (last {days_back} days)", ""]

    for i, result in enumerate(results, 1):
        output.append(f"### {i}. {result.get('title', 'Untitled')}")
        output.append(f"- **URL**: {result.get('url', 'N/A')}")
        output.append(f"- **Source**: DPA")
        if result.get('published_date'):
            output.append(f"- **Date**: {result['published_date']}")
        if result.get('language'):
            output.append(f"- **Language**: {result['language']}")
        if result.get('content_preview'):
            output.append(f"\n{result['content_preview']}")
        output.append("")

    return [TextContent(type="text", text="\n".join(output))]


async def handle_get_article_content(args: dict[str, Any]) -> list[TextContent]:
    """Handle get_article_content tool."""
    urls = args["urls"]

    if not urls:
        return [TextContent(type="text", text="No URLs provided")]

    results = await exa_client.get_contents(urls[:10])

    if not results:
        return [TextContent(type="text", text="Could not fetch content for the provided URLs")]

    output = ["## Article Contents", ""]

    for i, result in enumerate(results, 1):
        output.append(f"### {i}. {result.get('title', 'Untitled')}")
        output.append(f"**URL**: {result.get('url', 'N/A')}")
        output.append("")
        content = result.get('content', '')
        # Truncate very long content
        if len(content) > 3000:
            content = content[:3000] + "\n\n... (content truncated)"
        output.append(content)
        output.append("")
        output.append("---")
        output.append("")

    return [TextContent(type="text", text="\n".join(output))]


# =============================================================================
# FastAPI Application
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    global exa_client, dpa_client

    logger.info("Starting Web Search MCP Server...")

    # Initialize clients
    try:
        exa_client = ExaSearchClient()
        logger.info("Exa.ai client initialized")
    except ValueError as e:
        logger.warning(f"Exa.ai client not initialized: {e}")
        exa_client = None

    try:
        dpa_client = DPANewsClient()
        logger.info(f"DPA client initialized (configured: {dpa_client.is_available()})")
    except Exception as e:
        logger.warning(f"DPA client not initialized: {e}")
        dpa_client = None

    logger.info("Web Search MCP Server started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Web Search MCP Server...")
    if exa_client:
        await exa_client.close()
    if dpa_client:
        await dpa_client.close()
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Web Search MCP Server",
    description="MCP server for web search via Exa.ai and DPA news",
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

# SSE Transport
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


# Mount SSE endpoints
app.add_api_route("/sse", handle_sse, methods=["GET"])
app.add_api_route("/messages/", handle_messages, methods=["POST"])


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        server="web-search",
        exa_configured=exa_client is not None,
        dpa_configured=dpa_client is not None and dpa_client.is_available()
    )


@app.get("/")
async def info():
    """Server info endpoint."""
    return JSONResponse({
        "name": "web-search",
        "version": "1.0.0",
        "description": "MCP server for web search via Exa.ai and DPA news",
        "endpoints": {
            "sse": "/sse",
            "health": "/health",
            "info": "/"
        },
        "tools": [
            "web_search",
            "search_news",
            "search_dpa_news",
            "get_article_content"
        ],
        "clients": {
            "exa": exa_client is not None,
            "dpa": dpa_client is not None and dpa_client.is_available()
        }
    })


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("MCP_PORT", "8005"))
    host = os.getenv("MCP_HOST", "0.0.0.0")

    print("=" * 60)
    print("  Web Search MCP Server")
    print("=" * 60)
    print(f"\n  Server URL: http://{host}:{port}")
    print(f"  SSE Endpoint: http://{host}:{port}/sse")
    print(f"  Health Check: http://{host}:{port}/health")
    print("=" * 60 + "\n")

    uvicorn.run(app, host=host, port=port, log_level="info")
