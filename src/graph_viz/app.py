"""FastAPI server for graph visualization with 2D/3D capabilities."""

import logging
import os
import time
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from neo4j import AsyncGraphDatabase
from ray import serve

from src.config import settings

from .context_tracker import ChatContextTracker
from .models import (
    ChatContextRequest,
    ChatContextResponse,
    GraphData,
    GraphEdge,
    GraphNode,
    HealthResponse,
    SchemaQuery,
    SchemaQueryResponse,
    TextToCypherRequest,
    TextToCypherResponse,
)
from .schema_queries import get_schema_query, list_schema_queries
from .text_to_cypher import TextToCypherService

logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Graph Visualization API",
    description="API for visualizing Neo4j knowledge graph with 2D/3D capabilities",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@serve.deployment(num_replicas=1)
@serve.ingress(app)
class GraphVizServer:
    """Ray Serve deployment for graph visualization service."""

    def __init__(self):
        self.neo4j_driver = None
        self.text_to_cypher_service = None
        self.context_tracker = None
        logger.info("GraphVizServer initialized")

    async def _get_neo4j_driver(self):
        """Lazy initialization of Neo4j driver."""
        if self.neo4j_driver is None:
            self.neo4j_driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
            )
            logger.info("Neo4j driver initialized")
        return self.neo4j_driver

    async def _get_text_to_cypher_service(self):
        """Lazy initialization of text-to-Cypher service."""
        if self.text_to_cypher_service is None:
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")

            self.text_to_cypher_service = TextToCypherService(
                neo4j_uri=settings.NEO4J_URI,
                neo4j_user=settings.NEO4J_USERNAME,
                neo4j_password=settings.NEO4J_PASSWORD,
                openai_api_key=openai_key,
            )
            logger.info("Text-to-Cypher service initialized")
        return self.text_to_cypher_service

    async def _get_context_tracker(self):
        """Lazy initialization of context tracker."""
        if self.context_tracker is None:
            driver = await self._get_neo4j_driver()
            self.context_tracker = ChatContextTracker(driver=driver, ttl_minutes=60)
            logger.info("Context tracker initialized")
        return self.context_tracker

    @app.get("/api/graph/health")
    async def health_check(self) -> HealthResponse:
        """Health check endpoint."""
        neo4j_connected = False
        llm_available = False

        try:
            driver = await self._get_neo4j_driver()
            async with driver.session(database=settings.NEO4J_DATABASE) as session:
                result = await session.run("RETURN 1")
                await result.single()
            neo4j_connected = True
        except Exception as e:
            logger.error(f"Neo4j health check failed: {e}")

        try:
            # Just check if OpenAI API key is available, don't initialize the full service
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key:
                # Service can be initialized when needed
                llm_available = True
            else:
                logger.warning("OPENAI_API_KEY not set - text-to-cypher will be unavailable")
        except Exception as e:
            logger.error(f"LLM service health check failed: {e}")

        return HealthResponse(
            status="healthy" if (neo4j_connected and llm_available) else "degraded",
            neo4j_connected=neo4j_connected,
            llm_available=llm_available,
            version="0.1.0",
        )

    @app.get("/api/graph/schema-queries")
    async def get_schema_queries(self) -> List[SchemaQuery]:
        """Get list of all available schema queries."""
        return list_schema_queries()

    @app.get("/api/graph/schema-query/{query_name}")
    async def execute_schema_query(self, query_name: str) -> SchemaQueryResponse:
        """Execute a predefined schema query."""
        query_def = get_schema_query(query_name)
        if not query_def:
            raise HTTPException(status_code=404, detail=f"Schema query '{query_name}' not found")

        start_time = time.time()

        try:
            driver = await self._get_neo4j_driver()
            nodes, links = await self._execute_cypher_query(query_def.cypher, driver)

            execution_time = time.time() - start_time

            return SchemaQueryResponse(
                query_info=query_def,
                nodes=nodes,
                links=links,
                execution_time=execution_time,
                stats={
                    "node_count": len(nodes),
                    "edge_count": len(links),
                    "query_name": query_name,
                },
            )

        except Exception as e:
            logger.error(f"Error executing schema query '{query_name}': {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/graph/text-to-cypher")
    async def text_to_cypher(self, request: TextToCypherRequest) -> TextToCypherResponse:
        """Convert natural language to Cypher and execute the query."""
        try:
            service = await self._get_text_to_cypher_service()
            driver = await self._get_neo4j_driver()

            result = await service.convert_and_execute(
                text=request.text, limit=request.limit, driver=driver
            )

            return TextToCypherResponse(**result)

        except Exception as e:
            logger.error(f"Error in text-to-Cypher: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/graph/chat-context")
    async def get_chat_context(self, request: ChatContextRequest) -> ChatContextResponse:
        """Get graph context from a chat session."""
        try:
            logger.warning(f"📥 Received chat context request for session: {request.session_id}")
            context_tracker = await self._get_context_tracker()

            context_data = await context_tracker.get_context_graph(
                session_id=request.session_id, query_text=request.query
            )

            logger.warning(f"📤 Returning context: {len(context_data['nodes'])} nodes, {len(context_data['links'])} links")

            # Check if there's an error in metadata
            if "error" in context_data.get("metadata", {}):
                logger.error(f"⚠️  Context has error: {context_data['metadata']['error']}")

            # Deep sanitize metadata to ensure no Neo4j types remain
            sanitized_metadata = self._deep_sanitize(context_data["metadata"])

            return ChatContextResponse(
                nodes=context_data["nodes"],
                links=context_data["links"],
                metadata=sanitized_metadata,
            )

        except Exception as e:
            logger.error(f"❌ Error getting chat context for session {request.session_id}: {e}", exc_info=True)
            # Return an error response instead of raising HTTPException
            return ChatContextResponse(
                nodes=[],
                links=[],
                metadata={
                    "session_id": request.session_id,
                    "error": f"Server error: {str(e)}",
                    "error_type": type(e).__name__
                },
            )

    def _deep_sanitize(self, obj):
        """Recursively sanitize any object to remove Neo4j types."""
        if hasattr(obj, 'isoformat'):
            # Neo4j DateTime or Python datetime
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: self._deep_sanitize(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._deep_sanitize(item) for item in obj]
        else:
            return obj

    async def _execute_cypher_query(
        self, cypher: str, driver
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        """Execute a Cypher query and convert results to graph format."""
        nodes_dict = {}
        links = []

        try:
            async with driver.session(database=settings.NEO4J_DATABASE) as session:
                result = await session.run(cypher)
                records = await result.data()

                for record in records:
                    for key, value in record.items():
                        # Handle nodes (dictionaries with 'labels' key and uuid)
                        if isinstance(value, dict) and "labels" in value and "uuid" in value:
                            node_id = str(value.get("uuid"))
                            if node_id not in nodes_dict:
                                # Get node properties (exclude metadata keys) and convert Neo4j types
                                node_props = {}
                                for k, v in value.items():
                                    if k not in ["labels", "uuid", "name_embedding"]:
                                        # Convert Neo4j DateTime to ISO string
                                        if hasattr(v, 'isoformat'):
                                            node_props[k] = v.isoformat()
                                        else:
                                            node_props[k] = v

                                labels = value.get("labels", [])
                                nodes_dict[node_id] = GraphNode(
                                    id=node_id,
                                    name=node_props.get("name", node_props.get("politician_name", node_props.get("company_name", f"Node-{node_id[:8]}"))),
                                    type=labels[0] if labels else "Entity",
                                    properties=node_props,
                                )

                        # Handle relationships (tuples containing (start_node, rel_type_string, end_node))
                        elif isinstance(value, tuple) and len(value) == 3:
                            start_node, rel_type, end_node = value

                            # Extract node information from tuple
                            if isinstance(start_node, dict) and "uuid" in start_node:
                                source_id = str(start_node.get("uuid"))
                                # Add start node if not already present
                                if source_id not in nodes_dict:
                                    labels = start_node.get("labels", [])
                                    node_props = {}
                                    for k, v in start_node.items():
                                        if k not in ["labels", "uuid", "name_embedding"]:
                                            # Convert Neo4j DateTime to ISO string
                                            if hasattr(v, 'isoformat'):
                                                node_props[k] = v.isoformat()
                                            else:
                                                node_props[k] = v
                                    nodes_dict[source_id] = GraphNode(
                                        id=source_id,
                                        name=node_props.get("name", node_props.get("politician_name", node_props.get("company_name", f"Node-{source_id[:8]}"))),
                                        type=labels[0] if labels else "Entity",
                                        properties=node_props,
                                    )

                            if isinstance(end_node, dict) and "uuid" in end_node:
                                target_id = str(end_node.get("uuid"))
                                # Add end node if not already present
                                if target_id not in nodes_dict:
                                    labels = end_node.get("labels", [])
                                    node_props = {}
                                    for k, v in end_node.items():
                                        if k not in ["labels", "uuid", "name_embedding"]:
                                            # Convert Neo4j DateTime to ISO string
                                            if hasattr(v, 'isoformat'):
                                                node_props[k] = v.isoformat()
                                            else:
                                                node_props[k] = v
                                    nodes_dict[target_id] = GraphNode(
                                        id=target_id,
                                        name=node_props.get("name", node_props.get("politician_name", node_props.get("company_name", f"Node-{target_id[:8]}"))),
                                        type=labels[0] if labels else "Entity",
                                        properties=node_props,
                                    )

                            # Extract relationship type (it's a string in the tuple)
                            if isinstance(rel_type, str) and source_id and target_id:
                                links.append(
                                    GraphEdge(
                                        source=source_id,
                                        target=target_id,
                                        type=rel_type,
                                        properties={},  # No properties available from tuple format
                                    )
                                )

        except Exception as e:
            logger.error(f"Error executing Cypher query: {e}")
            raise

        nodes = list(nodes_dict.values())
        return nodes, links


# Create the Ray Serve deployment
graph_viz_app = GraphVizServer.bind()


# Deployment function for standalone usage
async def deploy_graph_viz_server():
    """Deploy the graph visualization server standalone (for testing)."""
    import ray

    if not ray.is_initialized():
        ray.init()

    serve.start(detached=True, http_options={"host": "0.0.0.0", "port": 8001})
    serve.run(GraphVizServer.bind(), name="graph-viz-server", route_prefix="/graph-viz")

    logger.info("Graph visualization server deployed at http://0.0.0.0:8001/graph-viz/")


if __name__ == "__main__":
    import asyncio

    asyncio.run(deploy_graph_viz_server())
