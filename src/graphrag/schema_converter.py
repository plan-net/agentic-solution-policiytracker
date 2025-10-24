"""
Schema Converter Module for Graphiti Integration.

This module provides simple getter functions to retrieve entity types, edge types,
and edge type mappings from the enhanced political schema for use with Graphiti's
add_episode() method.

Version: 1.0
Last Updated: 2025-01-09
"""

from typing import Any
from pydantic import BaseModel

from src.graphrag.political_schema_v3 import (
    ENTITY_TYPE_REGISTRY,
    EDGE_TYPE_REGISTRY,
    EDGE_TYPE_MAP,
    SCHEMA_INFO,
)


def get_entity_types() -> dict[str, type[BaseModel]]:
    """
    Get all entity types for Graphiti.

    Returns:
        Dictionary mapping entity type names to Pydantic BaseModel classes.
        This can be passed directly to Graphiti's add_episode(entity_types=...).

    Example:
        >>> entity_types = get_entity_types()
        >>> result = await graphiti_client.add_episode(
        ...     name="doc_001",
        ...     episode_body=content,
        ...     entity_types=entity_types
        ... )
    """
    return ENTITY_TYPE_REGISTRY


def get_edge_types() -> dict[str, type[BaseModel]]:
    """
    Get all edge types for Graphiti.

    Returns:
        Dictionary mapping edge type names to Pydantic BaseModel classes.
        This can be passed directly to Graphiti's add_episode(edge_types=...).

    Example:
        >>> edge_types = get_edge_types()
        >>> result = await graphiti_client.add_episode(
        ...     name="doc_001",
        ...     episode_body=content,
        ...     edge_types=edge_types
        ... )
    """
    return EDGE_TYPE_REGISTRY


def get_edge_type_map() -> dict[tuple[str, str], list[str]]:
    """
    Get edge type mapping for Graphiti.

    Returns:
        Dictionary mapping (source_entity, target_entity) tuples to lists of
        valid edge type names. This can be passed directly to Graphiti's
        add_episode(edge_type_map=...).

    Example:
        >>> edge_type_map = get_edge_type_map()
        >>> result = await graphiti_client.add_episode(
        ...     name="doc_001",
        ...     episode_body=content,
        ...     edge_type_map=edge_type_map
        ... )
    """
    return EDGE_TYPE_MAP


def get_complete_schema() -> dict[str, Any]:
    """
    Get all schema components in one call for convenience.

    Returns:
        Dictionary containing entity_types, edge_types, and edge_type_map.

    Example:
        >>> schema = get_complete_schema()
        >>> result = await graphiti_client.add_episode(
        ...     name="doc_001",
        ...     episode_body=content,
        ...     entity_types=schema["entity_types"],
        ...     edge_types=schema["edge_types"],
        ...     edge_type_map=schema["edge_type_map"]
        ... )
    """
    return {
        "entity_types": ENTITY_TYPE_REGISTRY,
        "edge_types": EDGE_TYPE_REGISTRY,
        "edge_type_map": EDGE_TYPE_MAP,
    }


def get_valid_edges_for_entity_pair(source: str, target: str) -> list[str]:
    """
    Get valid edge types for a specific source-target entity pair.

    Args:
        source: Source entity type name (e.g., "Company")
        target: Target entity type name (e.g., "Policy")

    Returns:
        List of valid edge type names for this entity pair.

    Example:
        >>> edges = get_valid_edges_for_entity_pair("Company", "Policy")
        >>> print(edges)
        ['LOBBIES_FOR', 'LOBBIES_AGAINST']
    """
    return EDGE_TYPE_MAP.get((source, target), [])


def validate_edge_pattern(source: str, edge: str, target: str) -> bool:
    """
    Check if a specific edge pattern is valid in the schema.

    Args:
        source: Source entity type name
        edge: Edge type name
        target: Target entity type name

    Returns:
        True if the pattern is valid, False otherwise.

    Example:
        >>> is_valid = validate_edge_pattern("Company", "AFFECTS", "Policy")
        >>> print(is_valid)
        False  # Policy AFFECTS Company, not the reverse

        >>> is_valid = validate_edge_pattern("Policy", "AFFECTS", "Company")
        >>> print(is_valid)
        True
    """
    valid_edges = EDGE_TYPE_MAP.get((source, target), [])
    return edge in valid_edges


def get_all_entity_names() -> list[str]:
    """
    Get a list of all entity type names.

    Returns:
        List of entity type name strings.

    Example:
        >>> entities = get_all_entity_names()
        >>> print(len(entities))
        23
    """
    return list(ENTITY_TYPE_REGISTRY.keys())


def get_all_edge_names() -> list[str]:
    """
    Get a list of all edge type names.

    Returns:
        List of edge type name strings.

    Example:
        >>> edges = get_all_edge_names()
        >>> print(len(edges))
        21
    """
    return list(EDGE_TYPE_REGISTRY.keys())


def get_schema_info() -> dict[str, Any]:
    """
    Get schema metadata and statistics.

    Returns:
        Dictionary containing schema version, counts, and description.

    Example:
        >>> info = get_schema_info()
        >>> print(info["entity_count"])
        23
        >>> print(info["edge_count"])
        21
    """
    return SCHEMA_INFO


def get_entity_type_model(entity_name: str) -> type[BaseModel] | None:
    """
    Get a specific entity type model by name.

    Args:
        entity_name: Name of the entity type (e.g., "Company", "Policy")

    Returns:
        Pydantic BaseModel class for the entity, or None if not found.

    Example:
        >>> company_model = get_entity_type_model("Company")
        >>> if company_model:
        ...     print(company_model.__doc__)
        Individual corporations and business entities
    """
    return ENTITY_TYPE_REGISTRY.get(entity_name)


def get_edge_type_model(edge_name: str) -> type[BaseModel] | None:
    """
    Get a specific edge type model by name.

    Args:
        edge_name: Name of the edge type (e.g., "AFFECTS", "INFLUENCES")

    Returns:
        Pydantic BaseModel class for the edge, or None if not found.

    Example:
        >>> affects_model = get_edge_type_model("AFFECTS")
        >>> if affects_model:
        ...     print(affects_model.__doc__)
        Direct business impact relationships
    """
    return EDGE_TYPE_REGISTRY.get(edge_name)


def get_outgoing_edges_for_entity(entity_type: str) -> dict[str, list[str]]:
    """
    Get all possible outgoing edges from a specific entity type.

    Args:
        entity_type: Source entity type name

    Returns:
        Dictionary mapping target entity types to lists of valid edge types.

    Example:
        >>> outgoing = get_outgoing_edges_for_entity("Company")
        >>> for target, edges in outgoing.items():
        ...     print(f"Company -> {target}: {edges}")
        Company -> Policy: ['LOBBIES_FOR', 'LOBBIES_AGAINST']
        Company -> Regulation: ['SUBJECT_TO', 'LOBBIES_AGAINST']
        ...
    """
    outgoing = {}
    for (source, target), edges in EDGE_TYPE_MAP.items():
        if source == entity_type:
            outgoing[target] = edges
    return outgoing


def get_incoming_edges_for_entity(entity_type: str) -> dict[str, list[str]]:
    """
    Get all possible incoming edges to a specific entity type.

    Args:
        entity_type: Target entity type name

    Returns:
        Dictionary mapping source entity types to lists of valid edge types.

    Example:
        >>> incoming = get_incoming_edges_for_entity("Company")
        >>> for source, edges in incoming.items():
        ...     print(f"{source} -> Company: {edges}")
        Policy -> Company: ['AFFECTS']
        Regulation -> Company: ['REQUIRES_COMPLIANCE']
        ...
    """
    incoming = {}
    for (source, target), edges in EDGE_TYPE_MAP.items():
        if target == entity_type:
            incoming[source] = edges
    return incoming


def print_schema_summary():
    """
    Print a human-readable summary of the schema.

    Useful for debugging and documentation purposes.
    """
    info = get_schema_info()

    print("=" * 70)
    print("POLITICAL SCHEMA SUMMARY")
    print("=" * 70)
    print(f"Version: {info['version']}")
    print(f"Last Updated: {info['last_updated']}")
    print(f"Graphiti Compatible: {info['graphiti_compatible']}")
    print()
    print(f"Entity Types: {info['entity_count']}")
    print(f"Edge Types: {info['edge_count']}")
    print(f"Edge Patterns: {info['pattern_count']}")
    print()
    print("Description:")
    print(f"  {info['description']}")
    print("=" * 70)
    print()

    print("ENTITY Name List:")
    ent_name_list = []
    for entity_name in sorted(get_all_entity_names()):
        ent_name_list.append(entity_name)
    print(', '.join(ent_name_list))
    print()

    print("ENTITY TYPES:")
    for entity_name in sorted(get_all_entity_names()):
        model = get_entity_type_model(entity_name)
        if model:
            print(f"  - {entity_name}: {model.__doc__}")
    print()


    print("EDGE List:")
    edge_name_list = []
    for edge_name in sorted(get_all_edge_names()):
        edge_name_list.append(edge_name)
    print(', '.join(edge_name_list))
    print()

    print("EDGE TYPES:")
    for edge_name in sorted(get_all_edge_names()):
        model = get_edge_type_model(edge_name)
        if model:
            print(f"  - {edge_name}: {model.__doc__}")
    print()


if __name__ == "__main__":
    # Print schema summary when run as a script
    print_schema_summary()

    # Example: Show some valid edge patterns
    print("EXAMPLE EDGE PATTERNS:")
    print("=" * 70)
    for entity in ["Company", "Policy", "Politician"]:
        outgoing = get_outgoing_edges_for_entity(entity)
        if outgoing:
            print(f"\n{entity} can connect to:")
            for target, edges in sorted(outgoing.items()):
                print(f"  → {target}: {', '.join(edges)}")

    print("=" * 70)
    print(ENTITY_TYPE_REGISTRY)
    print()
    print(EDGE_TYPE_REGISTRY)
    print()
    print(EDGE_TYPE_MAP)    

