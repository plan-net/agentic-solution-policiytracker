"""
Monkey-patches for Graphiti library to handle edge cases.

This module patches Graphiti's edge/node parsing functions to handle cases where
`created_at` fields may be stored as strings instead of Neo4j DateTime objects.
This can happen due to data migration or different ingestion paths.

Apply this patch early in the application startup, BEFORE importing graphiti_core.
"""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

_patch_applied = False


def _safe_parse_datetime(value: Any) -> datetime:
    """
    Safely parse a datetime value that may be:
    - A Neo4j DateTime object (has .to_native() method)
    - A Python datetime object
    - A string in ISO format
    - A float timestamp
    """
    if value is None:
        return datetime.now()

    # Neo4j DateTime object
    if hasattr(value, "to_native"):
        return value.to_native()

    # Already a Python datetime
    if isinstance(value, datetime):
        return value

    # String (ISO format)
    if isinstance(value, str):
        try:
            # Try ISO format first
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            # Try common formats
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
            logger.warning(f"Could not parse datetime string: {value}")
            return datetime.now()

    # Float timestamp
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value)

    logger.warning(f"Unknown datetime type: {type(value)} = {value}")
    return datetime.now()


def apply_graphiti_patches():
    """
    Apply monkey-patches to Graphiti's edge/node parsing functions.

    This patches the following functions to handle string datetime values:
    - graphiti_core.edges.get_episodic_edge_from_record
    - graphiti_core.edges.get_entity_edge_from_record
    - graphiti_core.edges.get_community_edge_from_record
    - graphiti_core.nodes.get_episodic_node_from_record
    - graphiti_core.nodes.get_entity_node_from_record
    - graphiti_core.nodes.get_community_node_from_record
    """
    global _patch_applied

    if _patch_applied:
        logger.debug("Graphiti patches already applied")
        return

    try:
        import graphiti_core.edges as edges_module
        import graphiti_core.nodes as nodes_module
        from graphiti_core.edges import (
            CommunityEdge,
            EntityEdge,
            EpisodicEdge,
        )
        from graphiti_core.helpers import parse_db_date
        from graphiti_core.nodes import (
            CommunityNode,
            EntityNode,
            EpisodeType,
            EpisodicNode,
        )

        # ========== EDGE PATCHES ==========

        def patched_get_episodic_edge_from_record(record: Any) -> EpisodicEdge:
            """Patched version that handles string datetime values."""
            return EpisodicEdge(
                uuid=record["uuid"],
                group_id=record["group_id"],
                source_node_uuid=record["source_node_uuid"],
                target_node_uuid=record["target_node_uuid"],
                created_at=_safe_parse_datetime(record["created_at"]),
            )

        def patched_get_entity_edge_from_record(record: Any) -> EntityEdge:
            """Patched version that handles string datetime values."""
            edge = EntityEdge(
                uuid=record["uuid"],
                source_node_uuid=record["source_node_uuid"],
                target_node_uuid=record["target_node_uuid"],
                fact=record["fact"],
                name=record["name"],
                group_id=record["group_id"],
                episodes=record["episodes"],
                created_at=_safe_parse_datetime(record["created_at"]),
                expired_at=parse_db_date(record["expired_at"]),
                valid_at=parse_db_date(record["valid_at"]),
                invalid_at=parse_db_date(record["invalid_at"]),
                attributes=record["attributes"],
            )

            # Clean up attributes (same as original)
            edge.attributes.pop("uuid", None)
            edge.attributes.pop("source_node_uuid", None)
            edge.attributes.pop("target_node_uuid", None)
            edge.attributes.pop("fact", None)
            edge.attributes.pop("name", None)
            edge.attributes.pop("group_id", None)
            edge.attributes.pop("episodes", None)
            edge.attributes.pop("created_at", None)
            edge.attributes.pop("expired_at", None)
            edge.attributes.pop("valid_at", None)
            edge.attributes.pop("invalid_at", None)

            return edge

        def patched_get_community_edge_from_record(record: Any) -> CommunityEdge:
            """Patched version that handles string datetime values."""
            return CommunityEdge(
                uuid=record["uuid"],
                group_id=record["group_id"],
                source_node_uuid=record["source_node_uuid"],
                target_node_uuid=record["target_node_uuid"],
                created_at=_safe_parse_datetime(record["created_at"]),
            )

        # ========== NODE PATCHES ==========

        def patched_get_episodic_node_from_record(record: Any) -> EpisodicNode:
            """Patched version that handles string datetime values."""
            created_at = _safe_parse_datetime(record["created_at"])
            valid_at = _safe_parse_datetime(record["valid_at"])
            return EpisodicNode(
                content=record["content"],
                created_at=created_at.timestamp() if hasattr(created_at, "timestamp") else created_at,
                valid_at=valid_at,
                uuid=record["uuid"],
                group_id=record["group_id"],
                source=EpisodeType.from_str(record["source"]),
                name=record["name"],
                source_description=record["source_description"],
                entity_edges=record["entity_edges"],
            )

        def patched_get_entity_node_from_record(record: Any) -> EntityNode:
            """Patched version that handles string datetime values."""
            entity_node = EntityNode(
                uuid=record["uuid"],
                name=record["name"],
                group_id=record["group_id"],
                labels=record["labels"],
                created_at=_safe_parse_datetime(record["created_at"]),
                summary=record["summary"],
                attributes=record["attributes"],
            )

            entity_node.attributes.pop("uuid", None)
            entity_node.attributes.pop("name", None)
            entity_node.attributes.pop("group_id", None)
            entity_node.attributes.pop("name_embedding", None)
            entity_node.attributes.pop("summary", None)
            entity_node.attributes.pop("created_at", None)

            return entity_node

        def patched_get_community_node_from_record(record: Any) -> CommunityNode:
            """Patched version that handles string datetime values."""
            return CommunityNode(
                uuid=record["uuid"],
                name=record["name"],
                group_id=record["group_id"],
                name_embedding=record["name_embedding"],
                created_at=_safe_parse_datetime(record["created_at"]),
                summary=record["summary"],
            )

        # Apply edge patches
        edges_module.get_episodic_edge_from_record = patched_get_episodic_edge_from_record
        edges_module.get_entity_edge_from_record = patched_get_entity_edge_from_record
        edges_module.get_community_edge_from_record = patched_get_community_edge_from_record

        # Apply node patches
        nodes_module.get_episodic_node_from_record = patched_get_episodic_node_from_record
        nodes_module.get_entity_node_from_record = patched_get_entity_node_from_record
        nodes_module.get_community_node_from_record = patched_get_community_node_from_record

        _patch_applied = True
        logger.info("Successfully applied Graphiti datetime parsing patches (edges + nodes)")
        # Print to stderr to ensure visibility in Ray logs
        print("✅ Graphiti datetime patches applied successfully (edges + nodes)", flush=True)

    except Exception as e:
        logger.error(f"Failed to apply Graphiti patches: {e}", exc_info=True)
        print(f"❌ Failed to apply Graphiti patches: {e}", flush=True)
        raise
