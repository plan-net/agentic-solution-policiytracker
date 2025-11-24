"""FastAPI application for graph visualization with Ray Serve deployment."""

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from neo4j import AsyncGraphDatabase, AsyncDriver
from ray import serve

from src.graph_viz import __version__
from src.graph_viz.context_tracker import ChatContextTracker
from src.graph_viz.models import (
    ChatContextRequest,
    ChatContextResponse,
    GraphEdge,
    GraphNode,
    HealthResponse,
    SchemaQuery,
    SchemaQueryResponse,
    TextToCypherRequest,
    TextToCypherResponse,
)
from src.graph_viz.schema_queries import get_all_queries, get_query_by_name
from src.graph_viz.text_to_cypher import TextToCypherService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances (initialized in lifespan)
neo4j_driver: AsyncDriver | None = None
text_to_cypher_service: TextToCypherService | None = None
context_tracker: ChatContextTracker | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    global neo4j_driver, text_to_cypher_service, context_tracker

    # Startup: Initialize services
    logger.info("Starting Graph Visualization Service...")

    # Load configuration from environment
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password123")
    neo4j_database = os.getenv("NEO4J_DATABASE", "politicalmonitoring")
    openai_api_key = os.getenv("OPENAI_API_KEY", "")

    # Initialize Neo4j driver
    try:
        neo4j_driver = AsyncGraphDatabase.driver(
            neo4j_uri, auth=(neo4j_user, neo4j_password)
        )
        await neo4j_driver.verify_connectivity()
        logger.info("Neo4j connection established")
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        neo4j_driver = None

    # Initialize Text-to-Cypher service
    if openai_api_key:
        try:
            text_to_cypher_service = TextToCypherService(
                neo4j_uri=neo4j_uri,
                neo4j_user=neo4j_user,
                neo4j_password=neo4j_password,
                openai_api_key=openai_api_key,
                neo4j_database=neo4j_database,
            )
            logger.info("Text-to-Cypher service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Text-to-Cypher service: {e}")
            text_to_cypher_service = None
    else:
        logger.warning("OPENAI_API_KEY not set, Text-to-Cypher will be unavailable")

    # Initialize context tracker
    if neo4j_driver:
        context_tracker = ChatContextTracker(neo4j_driver, ttl_minutes=5)
        logger.info("Context tracker initialized")

    logger.info(f"Graph Visualization Service v{__version__} ready!")

    yield  # Application runs here

    # Shutdown: Clean up resources
    logger.info("Shutting down Graph Visualization Service...")
    if neo4j_driver:
        await neo4j_driver.close()
        logger.info("Neo4j connection closed")


# Create FastAPI app
app = FastAPI(
    title="Graph Visualization API",
    description="Neo4j knowledge graph visualization with text-to-Cypher",
    version=__version__,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/graph/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    neo4j_connected = neo4j_driver is not None
    llm_available = text_to_cypher_service is not None

    # Test Neo4j connectivity
    if neo4j_connected:
        try:
            await neo4j_driver.verify_connectivity()
        except Exception:
            neo4j_connected = False

    status = "healthy" if (neo4j_connected and llm_available) else "degraded"

    return HealthResponse(
        status=status,
        neo4j_connected=neo4j_connected,
        llm_available=llm_available,
        version=__version__,
    )


@app.get("/api/graph/schema-queries", response_model=list[SchemaQuery])
async def get_schema_queries():
    """Get list of all predefined schema queries."""
    return get_all_queries()


@app.get("/api/graph/schema-query/{query_name}", response_model=SchemaQueryResponse)
async def execute_schema_query(query_name: str):
    """Execute a predefined schema query."""
    if not neo4j_driver:
        raise HTTPException(status_code=503, detail="Neo4j not connected")

    # Get query definition
    query = get_query_by_name(query_name)
    if not query:
        raise HTTPException(status_code=404, detail=f"Query '{query_name}' not found")

    # Execute query
    start_time = time.time()
    nodes, edges = await _execute_cypher_query(query.cypher)
    execution_time = time.time() - start_time

    return SchemaQueryResponse(
        query_info=query,
        nodes=nodes,
        links=edges,
        execution_time=execution_time,
        stats={
            "nodes_returned": len(nodes),
            "relationships_returned": len(edges),
        },
    )


@app.post("/api/graph/text-to-cypher", response_model=TextToCypherResponse)
async def text_to_cypher(request: TextToCypherRequest):
    """Convert natural language to Cypher and execute."""
    if not text_to_cypher_service:
        raise HTTPException(status_code=503, detail="Text-to-Cypher service unavailable")

    if not neo4j_driver:
        raise HTTPException(status_code=503, detail="Neo4j not connected")

    # Convert and execute
    start_time = time.time()
    cypher, nodes, edges, error = await text_to_cypher_service.convert_and_execute(
        text=request.text, limit=request.limit, driver=neo4j_driver
    )
    execution_time = time.time() - start_time

    return TextToCypherResponse(
        cypher=cypher,
        nodes=nodes,
        links=edges,
        execution_time=execution_time,
        error=error,
    )


@app.post("/api/graph/chat-context", response_model=ChatContextResponse)
async def get_chat_context(request: ChatContextRequest):
    """Get graph context from a chat session."""
    if not context_tracker:
        raise HTTPException(status_code=503, detail="Context tracker unavailable")

    # Get context graph
    nodes, edges, metadata = await context_tracker.get_context_graph(
        session_id=request.session_id, query_text=request.query
    )

    # Check for errors in metadata
    if "error" in metadata:
        raise HTTPException(status_code=404, detail=metadata["error"])

    return ChatContextResponse(nodes=nodes, links=edges, metadata=metadata)


async def _execute_cypher_query(cypher: str) -> tuple[list[GraphNode], list[GraphEdge]]:
    """Execute a Cypher query and convert results to graph format."""
    nodes = []
    edges = []
    node_map = {}

    try:
        async with neo4j_driver.session() as session:
            result = await session.run(cypher)
            records = await result.data()

            for record in records:
                # Process each value in the record
                for value in record.values():
                    # Handle nodes
                    if hasattr(value, "element_id") and hasattr(value, "labels"):
                        node_id = value.element_id
                        if node_id not in node_map:
                            node_data = dict(value.items())
                            node = GraphNode(
                                id=node_id,
                                name=node_data.get("name", node_id[:8]),
                                type=list(value.labels)[0] if value.labels else "Entity",
                                properties=node_data,
                                val=1,
                            )
                            nodes.append(node)
                            node_map[node_id] = node

                    # Handle relationships
                    elif hasattr(value, "start_node") and hasattr(value, "end_node"):
                        source_id = value.start_node.element_id
                        target_id = value.end_node.element_id

                        # Ensure source node exists
                        if source_id not in node_map:
                            source_data = dict(value.start_node.items())
                            source_node = GraphNode(
                                id=source_id,
                                name=source_data.get("name", source_id[:8]),
                                type=list(value.start_node.labels)[0]
                                if value.start_node.labels
                                else "Entity",
                                properties=source_data,
                                val=1,
                            )
                            nodes.append(source_node)
                            node_map[source_id] = source_node

                        # Ensure target node exists
                        if target_id not in node_map:
                            target_data = dict(value.end_node.items())
                            target_node = GraphNode(
                                id=target_id,
                                name=target_data.get("name", target_id[:8]),
                                type=list(value.end_node.labels)[0]
                                if value.end_node.labels
                                else "Entity",
                                properties=target_data,
                                val=1,
                            )
                            nodes.append(target_node)
                            node_map[target_id] = target_node

                        # Create edge
                        edge = GraphEdge(
                            source=source_id,
                            target=target_id,
                            type=value.type,
                            value=1.0,
                            properties=dict(value.items()),
                        )
                        edges.append(edge)

    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")

    return nodes, edges


# Ray Serve deployment
@serve.deployment(
    name="graph-viz-server",
    num_replicas=1,
    ray_actor_options={"num_cpus": 1, "memory": 2000000000},
    autoscaling_config={"min_replicas": 1, "max_replicas": 2},
)
@serve.ingress(app)
class GraphVizServer:
    """Ray Serve deployment for graph visualization API."""

    pass


# Create deployment binding
graph_viz_app = GraphVizServer.bind()
