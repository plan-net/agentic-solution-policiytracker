"""Data schemas for CRUD Subagent operations."""
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class CRUDOperation(BaseModel):
    """Base class for CRUD operations."""

    operation: Literal[
        "create_node",
        "update_node",
        "delete_node",
        "create_relationship",
        "update_relationship",
        "query_nodes",
    ]
    entity_type: Optional[str] = Field(None, description="Entity type")


class CreateNodeOperation(CRUDOperation):
    """Create a new node."""

    operation: Literal["create_node"] = "create_node"
    entity_type: str
    properties: dict[str, Any]


class UpdateNodeOperation(CRUDOperation):
    """Update an existing node."""

    operation: Literal["update_node"] = "update_node"
    entity_type: str
    node_id: str
    properties: dict[str, Any]


class DeleteNodeOperation(CRUDOperation):
    """Delete a node."""

    operation: Literal["delete_node"] = "delete_node"
    entity_type: str
    node_id: str
    hard_delete: bool = False


class CreateRelationshipOperation(CRUDOperation):
    """Create a relationship between two nodes."""

    operation: Literal["create_relationship"] = "create_relationship"
    from_entity_type: str
    from_node_id: str
    to_entity_type: str
    to_node_id: str
    relationship_type: str
    properties: Optional[dict[str, Any]] = None


class UpdateRelationshipOperation(CRUDOperation):
    """Update a relationship."""

    operation: Literal["update_relationship"] = "update_relationship"
    from_entity_type: str
    from_node_id: str
    to_entity_type: str
    to_node_id: str
    relationship_type: str
    properties: dict[str, Any]


class QueryNodesOperation(CRUDOperation):
    """Query nodes with filters."""

    operation: Literal["query_nodes"] = "query_nodes"
    entity_type: str
    filters: Optional[dict[str, Any]] = None
    limit: int = 100
    skip: int = 0


class OperationResult(BaseModel):
    """Result of a CRUD operation."""

    success: bool
    operation: str
    entity_type: Optional[str] = None
    node_id: Optional[str] = None
    message: str
    data: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: float
