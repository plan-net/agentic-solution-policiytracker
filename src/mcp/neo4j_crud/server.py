"""FastAPI MCP Server for Neo4j CRUD operations."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from neo4j import GraphDatabase

from .config import Neo4jConfig, ServerConfig
from .operations import Neo4jCRUDOperations
from .schemas import (
    CreateNodeRequest,
    CreateRelationshipRequest,
    DeleteNodeRequest,
    HealthResponse,
    OperationResponse,
    QueryNodesRequest,
    QueryNodesResponse,
    UpdateNodeRequest,
    UpdateRelationshipRequest,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global operations instance
crud_ops: Neo4jCRUDOperations = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    global crud_ops

    # Startup
    logger.info("Starting Neo4j CRUD MCP Server...")

    # Load configuration
    neo4j_config = Neo4jConfig.from_env()
    server_config = ServerConfig.from_env()

    logger.info(f"Connecting to Neo4j at {neo4j_config.uri}")

    # Initialize Neo4j driver
    driver = GraphDatabase.driver(neo4j_config.uri, auth=(neo4j_config.user, neo4j_config.password))

    # Initialize CRUD operations
    crud_ops = Neo4jCRUDOperations(driver, neo4j_config.database)

    logger.info("Neo4j CRUD MCP Server started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Neo4j CRUD MCP Server...")
    driver.close()
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Neo4j CRUD MCP Server",
    description="Generic CRUD operations for Neo4j entities via MCP protocol",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    result = crud_ops.health_check()
    return HealthResponse(**result)


@app.post("/create_node", response_model=OperationResponse)
async def create_node(request: CreateNodeRequest):
    """
    Create a new node with Graphiti registration.

    Args:
        request: CreateNodeRequest with entity_type and properties

    Returns:
        OperationResponse with success status
    """
    logger.info(f"POST /create_node: {request.entity_type}")

    # Await the async create_node method (now includes Graphiti registration)
    result = await crud_ops.create_node(
        entity_type=request.entity_type, properties=request.properties
    )

    if result["success"]:
        return OperationResponse(**result)
    else:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to create node"))


@app.post("/update_node", response_model=OperationResponse)
async def update_node(request: UpdateNodeRequest):
    """
    Update an existing node's properties.

    Args:
        request: UpdateNodeRequest with entity_type, node_id, and properties

    Returns:
        OperationResponse with success status
    """
    logger.info(f"POST /update_node: {request.entity_type} {request.node_id}")

    result = crud_ops.update_node(
        entity_type=request.entity_type, node_id=request.node_id, properties=request.properties
    )

    if result["success"]:
        return OperationResponse(**result)
    else:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to update node"))


@app.post("/delete_node", response_model=OperationResponse)
async def delete_node(request: DeleteNodeRequest):
    """
    Delete a node (soft delete by default).

    Args:
        request: DeleteNodeRequest with entity_type and node_id

    Returns:
        OperationResponse with success status
    """
    logger.info(f"POST /delete_node: {request.entity_type} {request.node_id}")

    result = crud_ops.delete_node(
        entity_type=request.entity_type, node_id=request.node_id, hard_delete=request.hard_delete
    )

    if result["success"]:
        return OperationResponse(**result)
    else:
        raise HTTPException(
            status_code=404 if "not found" in result.get("error", "").lower() else 400,
            detail=result.get("error", "Failed to delete node"),
        )


@app.post("/create_relationship", response_model=OperationResponse)
async def create_relationship(request: CreateRelationshipRequest):
    """
    Create a relationship between two nodes.

    Args:
        request: CreateRelationshipRequest with entity types, IDs, and relationship type

    Returns:
        OperationResponse with success status
    """
    logger.info(
        f"POST /create_relationship: {request.from_entity_type}→{request.relationship_type}→{request.to_entity_type}"
    )

    result = crud_ops.create_relationship(
        from_entity_type=request.from_entity_type,
        from_node_id=request.from_node_id,
        to_entity_type=request.to_entity_type,
        to_node_id=request.to_node_id,
        relationship_type=request.relationship_type,
        properties=request.properties,
    )

    if result["success"]:
        return OperationResponse(**result)
    else:
        raise HTTPException(
            status_code=404 if "not found" in result.get("error", "").lower() else 400,
            detail=result.get("error", "Failed to create relationship"),
        )


@app.post("/update_relationship", response_model=OperationResponse)
async def update_relationship(request: UpdateRelationshipRequest):
    """
    Update relationship properties.

    Args:
        request: UpdateRelationshipRequest with entity types, IDs, relationship type, and properties

    Returns:
        OperationResponse with success status
    """
    logger.info(
        f"POST /update_relationship: {request.from_entity_type}→{request.relationship_type}→{request.to_entity_type}"
    )

    result = crud_ops.update_relationship(
        from_entity_type=request.from_entity_type,
        from_node_id=request.from_node_id,
        to_entity_type=request.to_entity_type,
        to_node_id=request.to_node_id,
        relationship_type=request.relationship_type,
        properties=request.properties,
    )

    if result["success"]:
        return OperationResponse(**result)
    else:
        raise HTTPException(
            status_code=404 if "not found" in result.get("error", "").lower() else 400,
            detail=result.get("error", "Failed to update relationship"),
        )


@app.post("/query_nodes", response_model=QueryNodesResponse)
async def query_nodes(request: QueryNodesRequest):
    """
    Query nodes with filters.

    Args:
        request: QueryNodesRequest with entity_type, filters, limit, and skip

    Returns:
        QueryNodesResponse with nodes list and counts
    """
    logger.info(f"POST /query_nodes: {request.entity_type} (filters: {request.filters})")

    result = crud_ops.query_nodes(
        entity_type=request.entity_type,
        filters=request.filters,
        limit=request.limit,
        skip=request.skip,
    )

    return QueryNodesResponse(**result)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unexpected errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "Internal server error", "error": str(exc)},
    )


if __name__ == "__main__":
    import uvicorn

    server_config = ServerConfig.from_env()
    uvicorn.run(
        app,
        host=server_config.host,
        port=server_config.port,
        log_level=server_config.log_level.lower(),
    )
