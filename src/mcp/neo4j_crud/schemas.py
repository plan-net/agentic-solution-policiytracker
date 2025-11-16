"""Pydantic schemas for Neo4j CRUD MCP Server."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CreateNodeRequest(BaseModel):
    """Request to create a new node."""

    entity_type: str = Field(..., description="Entity type (e.g., 'BundestagPerson', 'Vorgang')")
    properties: Dict[str, Any] = Field(..., description="Node properties as key-value pairs")


class UpdateNodeRequest(BaseModel):
    """Request to update an existing node."""

    entity_type: str = Field(..., description="Entity type")
    node_id: str = Field(..., description="Unique identifier value for the node")
    properties: Dict[str, Any] = Field(..., description="Properties to update")


class DeleteNodeRequest(BaseModel):
    """Request to delete (soft delete) a node."""

    entity_type: str = Field(..., description="Entity type")
    node_id: str = Field(..., description="Unique identifier value for the node")
    hard_delete: bool = Field(default=False, description="If True, actually delete. If False, set active=false")


class CreateRelationshipRequest(BaseModel):
    """Request to create a relationship between two nodes."""

    from_entity_type: str = Field(..., description="Source entity type")
    from_node_id: str = Field(..., description="Source node ID")
    to_entity_type: str = Field(..., description="Target entity type")
    to_node_id: str = Field(..., description="Target node ID")
    relationship_type: str = Field(..., description="Relationship type (e.g., 'MEMBER_OF', 'BELONGS_TO')")
    properties: Optional[Dict[str, Any]] = Field(default=None, description="Relationship properties")


class UpdateRelationshipRequest(BaseModel):
    """Request to update a relationship."""

    from_entity_type: str = Field(..., description="Source entity type")
    from_node_id: str = Field(..., description="Source node ID")
    to_entity_type: str = Field(..., description="Target entity type")
    to_node_id: str = Field(..., description="Target node ID")
    relationship_type: str = Field(..., description="Relationship type")
    properties: Dict[str, Any] = Field(..., description="Properties to update")


class QueryNodesRequest(BaseModel):
    """Request to query nodes with filters."""

    entity_type: str = Field(..., description="Entity type to query")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Property filters")
    limit: int = Field(default=100, description="Maximum number of results")
    skip: int = Field(default=0, description="Number of results to skip (for pagination)")


class OperationResponse(BaseModel):
    """Generic response for CRUD operations."""

    success: bool = Field(..., description="Whether operation was successful")
    message: str = Field(..., description="Human-readable message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Operation result data")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class QueryNodesResponse(BaseModel):
    """Response for query_nodes operation."""

    success: bool = Field(..., description="Whether query was successful")
    nodes: List[Dict[str, Any]] = Field(..., description="List of matching nodes")
    total_count: int = Field(..., description="Total number of nodes (before limit/skip)")
    returned_count: int = Field(..., description="Number of nodes returned")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status: 'healthy' or 'unhealthy'")
    neo4j_connected: bool = Field(..., description="Whether Neo4j connection is working")
    message: str = Field(default="", description="Additional status information")
