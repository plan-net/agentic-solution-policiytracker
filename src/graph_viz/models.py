"""Pydantic models for graph visualization API."""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_serializer


def _sanitize_value(value: Any) -> Any:
    """Recursively sanitize values to convert Neo4j types to JSON-serializable Python types."""
    # Handle objects with isoformat() (Neo4j DateTime, Python datetime, etc.)
    if hasattr(value, "isoformat"):
        return value.isoformat()

    # Handle dictionaries
    elif isinstance(value, dict):
        return {k: _sanitize_value(v) for k, v in value.items()}

    # Handle lists
    elif isinstance(value, list):
        return [_sanitize_value(item) for item in value]

    # Return as-is for primitives
    return value


class GraphNode(BaseModel):
    """Represents a node in the graph visualization."""

    id: str = Field(..., description="Unique identifier (UUID)")
    name: str = Field(..., description="Display name of the node")
    type: str = Field(default="Entity", description="Node type/label")
    properties: dict[str, Any] = Field(default_factory=dict, description="Node properties")
    group: Optional[int] = Field(default=None, description="Group ID for community detection")

    @model_serializer
    def _serialize_model(self):
        """Custom serializer to handle Neo4j types in properties."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "properties": _sanitize_value(self.properties),
            "group": self.group,
        }


class GraphEdge(BaseModel):
    """Represents an edge/relationship in the graph visualization."""

    source: str = Field(..., description="Source node ID (UUID)")
    target: str = Field(..., description="Target node ID (UUID)")
    type: str = Field(default="RELATED_TO", description="Relationship type")
    value: float = Field(default=1.0, description="Edge weight/strength")
    properties: dict[str, Any] = Field(default_factory=dict, description="Edge properties")

    @model_serializer
    def _serialize_model(self):
        """Custom serializer to handle Neo4j types in properties."""
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "value": self.value,
            "properties": _sanitize_value(self.properties),
        }


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


class QueryParameter(BaseModel):
    """Definition of a query parameter for the UI to render appropriate input controls."""

    name: str = Field(..., description="Parameter name (used in Cypher query as $name)")
    param_type: Literal["string", "integer", "float", "boolean"] = Field(
        ..., description="Parameter data type"
    )
    default: Any = Field(..., description="Default value for the parameter")
    description: str = Field(..., description="Human-readable description for UI label")
    required: bool = Field(default=False, description="Whether the parameter is required")
    min_value: Optional[float] = Field(default=None, description="Minimum value for numeric types")
    max_value: Optional[float] = Field(default=None, description="Maximum value for numeric types")


class SchemaQuery(BaseModel):
    """Predefined schema query definition."""

    name: str = Field(..., description="Query display name")
    description: str = Field(..., description="Query description")
    cypher: str = Field(..., description="Cypher query template with $param placeholders")
    category: str = Field(
        ..., description="Query category (policy, organization, temporal, network)"
    )
    parameters: list[QueryParameter] = Field(
        default_factory=list, description="List of query parameters with their definitions"
    )


class SchemaQueryRequest(BaseModel):
    """Request to execute a schema query with parameters."""

    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Parameter values to substitute in the query"
    )


class SchemaQueryResponse(BaseModel):
    """Response from executing a schema query."""

    query_info: SchemaQuery
    nodes: list[GraphNode]
    links: list[GraphEdge]
    execution_time: float = Field(..., description="Query execution time in seconds")
    stats: dict[str, Any] = Field(default_factory=dict, description="Query statistics")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    neo4j_connected: bool = Field(..., description="Neo4j connection status")
    llm_available: bool = Field(..., description="LLM service availability")
    version: str = Field(..., description="Service version")
