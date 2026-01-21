"""
Bundestag DIP API MCP Server.

FastAPI server with SSE transport for Claude Agent integration.
Provides direct access to German Bundestag parliamentary data.
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

from .client import BundestagDIPClient

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
dip_client: BundestagDIPClient = None
mcp_server = Server("bundestag-dip")


# =============================================================================
# Pydantic Models
# =============================================================================

class HealthResponse(BaseModel):
    status: str
    server: str
    api_base_url: str


# =============================================================================
# MCP Server Tools
# =============================================================================

@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools for Bundestag DIP API."""
    return [
        Tool(
            name="search_bundestag_legislation",
            description="Search for legislative procedures (Vorgänge) in the German Bundestag. Returns bills, motions, and other parliamentary procedures with their current status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'Klimaschutz', 'Digitalisierung', 'AI Act')"
                    },
                    "wahlperiode": {
                        "type": "integer",
                        "description": "Electoral period (e.g., 20 for current period). Defaults to current period.",
                        "default": 20
                    },
                    "vorgangstyp": {
                        "type": "string",
                        "description": "Type of procedure (e.g., 'Gesetzgebung', 'Antrag', 'Kleine Anfrage')",
                        "enum": ["Gesetzgebung", "Antrag", "Kleine Anfrage", "Große Anfrage", "Entschließungsantrag"]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10, max: 50)",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_bundestag_vorgang",
            description="Get detailed information about a specific legislative procedure (Vorgang) by its ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "vorgang_id": {
                        "type": "string",
                        "description": "The Vorgang ID (e.g., '287654')"
                    }
                },
                "required": ["vorgang_id"]
            }
        ),
        Tool(
            name="search_bundestag_documents",
            description="Search for parliamentary documents (Drucksachen) including bills, reports, and official papers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for document content or title"
                    },
                    "dokumentart": {
                        "type": "string",
                        "description": "Document type (e.g., 'Gesetzentwurf', 'Beschlussempfehlung', 'Bericht')"
                    },
                    "wahlperiode": {
                        "type": "integer",
                        "description": "Electoral period",
                        "default": 20
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_bundestag_drucksache",
            description="Get detailed information about a specific parliamentary document (Drucksache) by its number.",
            inputSchema={
                "type": "object",
                "properties": {
                    "drucksache_nummer": {
                        "type": "string",
                        "description": "The Drucksache number (e.g., '20/1234')"
                    }
                },
                "required": ["drucksache_nummer"]
            }
        ),
        Tool(
            name="search_bundestag_persons",
            description="Search for members of the German Bundestag (MPs) and their information.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the person to search for"
                    },
                    "fraktion": {
                        "type": "string",
                        "description": "Parliamentary group (e.g., 'SPD', 'CDU/CSU', 'BÜNDNIS 90/DIE GRÜNEN')"
                    },
                    "wahlperiode": {
                        "type": "integer",
                        "description": "Electoral period",
                        "default": 20
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 10
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_bundestag_person",
            description="Get detailed information about a specific Bundestag member by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "person_id": {
                        "type": "string",
                        "description": "The person ID from the DIP system"
                    }
                },
                "required": ["person_id"]
            }
        ),
        Tool(
            name="search_bundestag_activities",
            description="Search for parliamentary activities including speeches, votes, and other actions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for activities"
                    },
                    "aktivitaetsart": {
                        "type": "string",
                        "description": "Type of activity (e.g., 'Rede', 'Abstimmung')"
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD format)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD format)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 10
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_bundestag_plenarprotokoll",
            description="Get plenary protocol (transcript of parliamentary session) by date or session number.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sitzungsnummer": {
                        "type": "string",
                        "description": "Session number (e.g., '20/123')"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date of the session (YYYY-MM-DD format)"
                    }
                },
                "required": []
            }
        ),
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle MCP tool calls for Bundestag DIP API."""
    try:
        logger.info(f"Tool called: {name} with args: {arguments}")

        if name == "search_bundestag_legislation":
            return await handle_search_legislation(arguments)
        elif name == "get_bundestag_vorgang":
            return await handle_get_vorgang(arguments["vorgang_id"])
        elif name == "search_bundestag_documents":
            return await handle_search_documents(arguments)
        elif name == "get_bundestag_drucksache":
            return await handle_get_drucksache(arguments["drucksache_nummer"])
        elif name == "search_bundestag_persons":
            return await handle_search_persons(arguments)
        elif name == "get_bundestag_person":
            return await handle_get_person(arguments["person_id"])
        elif name == "search_bundestag_activities":
            return await handle_search_activities(arguments)
        elif name == "get_bundestag_plenarprotokoll":
            return await handle_get_plenarprotokoll(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        logger.error(f"Tool error: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_search_legislation(args: dict[str, Any]) -> list[TextContent]:
    """Search for legislative procedures (Vorgänge)."""
    query = args["query"]
    wahlperiode = args.get("wahlperiode", 20)
    vorgangstyp = args.get("vorgangstyp")
    limit = min(args.get("limit", 10), 50)

    results = await dip_client.search_vorgaenge(
        query=query,
        wahlperiode=wahlperiode,
        vorgangstyp=vorgangstyp,
        limit=limit
    )

    if not results:
        return [TextContent(type="text", text=f"No legislative procedures found for: {query}")]

    output = [f"## Legislative Procedures for: {query}", ""]

    for i, vorgang in enumerate(results, 1):
        output.append(f"### {i}. {vorgang.get('titel', 'Untitled')}")
        output.append(f"- **ID**: {vorgang.get('id', 'N/A')}")
        output.append(f"- **Type**: {vorgang.get('vorgangstyp', 'N/A')}")
        output.append(f"- **Status**: {vorgang.get('beratungsstand', 'N/A')}")
        output.append(f"- **Initiative**: {', '.join(vorgang.get('initiative', []))}")
        output.append(f"- **Date**: {vorgang.get('datum', 'N/A')}")
        if vorgang.get('abstract'):
            abstract = vorgang['abstract'][:300] + "..." if len(vorgang.get('abstract', '')) > 300 else vorgang.get('abstract', '')
            output.append(f"- **Abstract**: {abstract}")
        output.append("")

    return [TextContent(type="text", text="\n".join(output))]


async def handle_get_vorgang(vorgang_id: str) -> list[TextContent]:
    """Get detailed information about a specific Vorgang."""
    vorgang = await dip_client.get_vorgang(vorgang_id)

    if not vorgang:
        return [TextContent(type="text", text=f"Vorgang not found: {vorgang_id}")]

    output = [
        f"## {vorgang.get('titel', 'Untitled')}",
        "",
        f"- **ID**: {vorgang.get('id', 'N/A')}",
        f"- **Type**: {vorgang.get('vorgangstyp', 'N/A')}",
        f"- **Status**: {vorgang.get('beratungsstand', 'N/A')}",
        f"- **Electoral Period**: {vorgang.get('wahlperiode', 'N/A')}",
        f"- **Initiative**: {', '.join(vorgang.get('initiative', []))}",
        f"- **Subject Areas**: {', '.join(vorgang.get('sachgebiet', []))}",
        f"- **Date**: {vorgang.get('datum', 'N/A')}",
        f"- **Last Updated**: {vorgang.get('aktualisiert', 'N/A')}",
    ]

    if vorgang.get('abstract'):
        output.append("")
        output.append("### Abstract")
        output.append(vorgang['abstract'])

    if vorgang.get('schlagwort'):
        output.append("")
        output.append(f"**Keywords**: {', '.join(vorgang['schlagwort'])}")

    return [TextContent(type="text", text="\n".join(output))]


async def handle_search_documents(args: dict[str, Any]) -> list[TextContent]:
    """Search for parliamentary documents (Drucksachen)."""
    query = args["query"]
    dokumentart = args.get("dokumentart")
    wahlperiode = args.get("wahlperiode", 20)
    limit = min(args.get("limit", 10), 50)

    results = await dip_client.search_drucksachen(
        query=query,
        dokumentart=dokumentart,
        wahlperiode=wahlperiode,
        limit=limit
    )

    if not results:
        return [TextContent(type="text", text=f"No documents found for: {query}")]

    output = [f"## Parliamentary Documents for: {query}", ""]

    for i, doc in enumerate(results, 1):
        output.append(f"### {i}. {doc.get('titel', 'Untitled')}")
        output.append(f"- **Number**: {doc.get('drucksache', 'N/A')}")
        output.append(f"- **Type**: {doc.get('dokumentart', 'N/A')}")
        output.append(f"- **Date**: {doc.get('datum', 'N/A')}")
        if doc.get('autoren'):
            output.append(f"- **Authors**: {', '.join(doc['autoren'])}")
        output.append("")

    return [TextContent(type="text", text="\n".join(output))]


async def handle_get_drucksache(drucksache_nummer: str) -> list[TextContent]:
    """Get detailed information about a specific Drucksache."""
    doc = await dip_client.get_drucksache(drucksache_nummer)

    if not doc:
        return [TextContent(type="text", text=f"Drucksache not found: {drucksache_nummer}")]

    output = [
        f"## {doc.get('titel', 'Untitled')}",
        "",
        f"- **Number**: {doc.get('drucksache', 'N/A')}",
        f"- **Type**: {doc.get('dokumentart', 'N/A')}",
        f"- **Date**: {doc.get('datum', 'N/A')}",
        f"- **Electoral Period**: {doc.get('wahlperiode', 'N/A')}",
    ]

    if doc.get('autoren'):
        output.append(f"- **Authors**: {', '.join(doc['autoren'])}")

    if doc.get('pdf_url'):
        output.append(f"- **PDF**: {doc['pdf_url']}")

    return [TextContent(type="text", text="\n".join(output))]


async def handle_search_persons(args: dict[str, Any]) -> list[TextContent]:
    """Search for Bundestag members."""
    name = args.get("name")
    fraktion = args.get("fraktion")
    wahlperiode = args.get("wahlperiode", 20)
    limit = min(args.get("limit", 10), 50)

    results = await dip_client.search_persons(
        name=name,
        fraktion=fraktion,
        wahlperiode=wahlperiode,
        limit=limit
    )

    if not results:
        query_desc = name or fraktion or "current period"
        return [TextContent(type="text", text=f"No persons found for: {query_desc}")]

    output = ["## Bundestag Members", ""]

    for i, person in enumerate(results, 1):
        output.append(f"### {i}. {person.get('vorname', '')} {person.get('nachname', '')}")
        output.append(f"- **ID**: {person.get('id', 'N/A')}")
        if person.get('fraktion'):
            output.append(f"- **Parliamentary Group**: {person['fraktion']}")
        if person.get('funktion'):
            output.append(f"- **Function**: {person['funktion']}")
        if person.get('wahlkreis'):
            output.append(f"- **Constituency**: {person['wahlkreis']}")
        output.append("")

    return [TextContent(type="text", text="\n".join(output))]


async def handle_get_person(person_id: str) -> list[TextContent]:
    """Get detailed information about a Bundestag member."""
    person = await dip_client.get_person(person_id)

    if not person:
        return [TextContent(type="text", text=f"Person not found: {person_id}")]

    output = [
        f"## {person.get('vorname', '')} {person.get('nachname', '')}",
        "",
        f"- **ID**: {person.get('id', 'N/A')}",
    ]

    if person.get('fraktion'):
        output.append(f"- **Parliamentary Group**: {person['fraktion']}")
    if person.get('funktion'):
        output.append(f"- **Function**: {person['funktion']}")
    if person.get('wahlkreis'):
        output.append(f"- **Constituency**: {person['wahlkreis']}")
    if person.get('beruf'):
        output.append(f"- **Profession**: {person['beruf']}")
    if person.get('geburtsdatum'):
        output.append(f"- **Birth Date**: {person['geburtsdatum']}")

    return [TextContent(type="text", text="\n".join(output))]


async def handle_search_activities(args: dict[str, Any]) -> list[TextContent]:
    """Search for parliamentary activities."""
    query = args.get("query")
    aktivitaetsart = args.get("aktivitaetsart")
    date_from = args.get("date_from")
    date_to = args.get("date_to")
    limit = min(args.get("limit", 10), 50)

    results = await dip_client.search_aktivitaeten(
        query=query,
        aktivitaetsart=aktivitaetsart,
        date_from=date_from,
        date_to=date_to,
        limit=limit
    )

    if not results:
        return [TextContent(type="text", text="No activities found for the specified criteria")]

    output = ["## Parliamentary Activities", ""]

    for i, activity in enumerate(results, 1):
        output.append(f"### {i}. {activity.get('titel', 'Untitled')}")
        output.append(f"- **Type**: {activity.get('aktivitaetsart', 'N/A')}")
        output.append(f"- **Date**: {activity.get('datum', 'N/A')}")
        if activity.get('person'):
            output.append(f"- **Person**: {activity['person']}")
        output.append("")

    return [TextContent(type="text", text="\n".join(output))]


async def handle_get_plenarprotokoll(args: dict[str, Any]) -> list[TextContent]:
    """Get plenary protocol."""
    sitzungsnummer = args.get("sitzungsnummer")
    date = args.get("date")

    protocol = await dip_client.get_plenarprotokoll(
        sitzungsnummer=sitzungsnummer,
        date=date
    )

    if not protocol:
        return [TextContent(type="text", text="Plenary protocol not found")]

    output = [
        "## Plenary Protocol",
        "",
        f"- **Session**: {protocol.get('sitzungsnummer', 'N/A')}",
        f"- **Date**: {protocol.get('datum', 'N/A')}",
    ]

    if protocol.get('pdf_url'):
        output.append(f"- **PDF**: {protocol['pdf_url']}")

    if protocol.get('tagesordnung'):
        output.append("")
        output.append("### Agenda Items")
        for item in protocol['tagesordnung'][:10]:
            output.append(f"- {item}")

    return [TextContent(type="text", text="\n".join(output))]


# =============================================================================
# FastAPI Application
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    global dip_client

    logger.info("Starting Bundestag DIP MCP Server...")

    # Initialize DIP client
    api_key = os.getenv("BUNDESTAG_DIP_API_KEY")
    dip_client = BundestagDIPClient(api_key=api_key)

    logger.info("Bundestag DIP MCP Server started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Bundestag DIP MCP Server...")
    await dip_client.close()
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Bundestag DIP MCP Server",
    description="MCP server for querying German Bundestag Document and Information System (DIP) API",
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
        server="bundestag-dip",
        api_base_url=dip_client.base_url if dip_client else "not initialized"
    )


@app.get("/")
async def info():
    """Server info endpoint."""
    return JSONResponse({
        "name": "bundestag-dip",
        "version": "1.0.0",
        "description": "MCP server for German Bundestag DIP API",
        "endpoints": {
            "sse": "/sse",
            "health": "/health",
            "info": "/"
        },
        "tools": [
            "search_bundestag_legislation",
            "get_bundestag_vorgang",
            "search_bundestag_documents",
            "get_bundestag_drucksache",
            "search_bundestag_persons",
            "get_bundestag_person",
            "search_bundestag_activities",
            "get_bundestag_plenarprotokoll"
        ]
    })


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("MCP_PORT", "8004"))
    host = os.getenv("MCP_HOST", "0.0.0.0")

    print("=" * 60)
    print("  Bundestag DIP MCP Server")
    print("=" * 60)
    print(f"\n  Server URL: http://{host}:{port}")
    print(f"  SSE Endpoint: http://{host}:{port}/sse")
    print(f"  Health Check: http://{host}:{port}/health")
    print("=" * 60 + "\n")

    uvicorn.run(app, host=host, port=port, log_level="info")
