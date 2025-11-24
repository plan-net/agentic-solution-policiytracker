"""Pydantic models for graph visualization API."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    """Represents a node in the graph visualization."""

    id: str = Field(..., description="Unique identifier (UUID)")
    name: str = Field(..., description="Display name of the node")
    type: str = Field(default="Entity", description="Node type/label")
    properties: dict[str, Any] = Field(default_factory=dict, description="Node properties")
    group: Optional[int] = Field(
        default=None, description="Group ID for community detection"
    )
    val: Optional[int] = Field(
        default=1, description="Node value for sizing (react-force-graph)"
    )


class GraphEdge(BaseModel):
    """Represents an edge/relationship in the graph visualization."""

    source: str = Field(..., description="Source node ID (UUID)")
    target: str = Field(..., description="Target node ID (UUID)")
    type: str = Field(default="RELATED_TO", description="Relationship type")
    value: float = Field(default=1.0, description="Edge weight/strength")
    properties: dict[str, Any] = Field(default_factory=dict, description="Edge properties")


class GraphData(BaseModel):
    """Graph data structure for visualization."""

    nodes: list[GraphNode] = Field(default_factory=list, description="List of nodes")
    links: list[GraphEdge] = Field(
        default_factory=list, description="List of edges (called 'links' for react-force-graph)"
    )


class ChatContextRequest(BaseModel):
    """Request to get graph context from a chat query."""

    query: Optional[str] = Field(default=None, description="Chat query text")
    session_id: str = Field(..., description="Chat session ID")


class ChatContextResponse(BaseModel):
    """Response containing graph context from chat interaction."""

    nodes: list[GraphNode]
    links: list[GraphEdge]
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about the context (tools used, execution time, etc.)",
    )


class TextToCypherRequest(BaseModel):
    """Request to convert natural language to Cypher query."""

    text: str = Field(..., description="Natural language query")
    limit: int = Field(default=50, ge=1, le=200, description="Maximum number of nodes to return")


class TextToCypherResponse(BaseModel):
    """Response from text-to-Cypher conversion and execution."""

    cypher: str = Field(..., description="Generated Cypher query")
    nodes: list[GraphNode]
    links: list[GraphEdge]
    execution_time: float = Field(..., description="Query execution time in seconds")
    error: Optional[str] = Field(default=None, description="Error message if query failed")


class SchemaQuery(BaseModel):
    """Predefined schema query definition."""

    name: str = Field(..., description="Query display name")
    description: str = Field(..., description="Query description")
    cypher: str = Field(..., description="Cypher query template")
    category: str = Field(..., description="Query category (policy, organization, temporal, network)")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Query parameters"
    )


class SchemaQueryResponse(BaseModel):
    """Response from executing a schema query."""

    query_info: SchemaQuery
    nodes: list[GraphNode]
    links: list[GraphEdge]
    execution_time: float = Field(..., description="Query execution time in seconds")
    stats: dict[str, Any] = Field(
        default_factory=dict, description="Query statistics"
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    neo4j_connected: bool = Field(..., description="Neo4j connection status")
    llm_available: bool = Field(..., description="LLM service availability")
    version: str = Field(..., description="Service version")
