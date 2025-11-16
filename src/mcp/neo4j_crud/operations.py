"""Neo4j CRUD operations using Neo4jUpsertManager."""

import logging
from typing import Any, Dict, List, Optional

from neo4j import Driver, GraphDatabase

# Import the existing upsert manager
from src.flows.bundestag_common.neo4j_upsert import Neo4jUpsertManager

logger = logging.getLogger(__name__)


class Neo4jCRUDOperations:
    """CRUD operations for Neo4j using existing infrastructure."""

    def __init__(self, driver: Driver, database: str):
        """
        Initialize CRUD operations.

        Args:
            driver: Neo4j driver instance
            database: Database name
        """
        self.driver = driver
        self.database = database
        self.upsert_manager = Neo4jUpsertManager(driver, database)
        logger.info(f"Initialized Neo4jCRUDOperations for database: {database}")

    def create_node(self, entity_type: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new node.

        Args:
            entity_type: Entity label (e.g., 'BundestagPerson')
            properties: Node properties

        Returns:
            Dict with success status and node details
        """
        logger.info(f"Creating node: {entity_type}")

        try:
            # Use existing upsert manager (MERGE operation)
            success = self.upsert_manager.upsert_entity(entity_type, properties)

            if success:
                # Get the ID field for this entity type
                id_field = self.upsert_manager.ENTITY_ID_FIELDS.get(entity_type)
                node_id = properties.get(id_field) if id_field else None

                return {
                    "success": True,
                    "message": f"Node created successfully",
                    "data": {"entity_type": entity_type, "node_id": node_id}
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to create node",
                    "error": "Upsert operation returned False"
                }

        except Exception as e:
            logger.error(f"Error creating node: {e}")
            return {
                "success": False,
                "message": f"Error creating node: {str(e)}",
                "error": str(e)
            }

    def update_node(
        self, entity_type: str, node_id: str, properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing node's properties.

        Args:
            entity_type: Entity label
            node_id: Unique identifier value
            properties: Properties to update

        Returns:
            Dict with success status
        """
        logger.info(f"Updating node: {entity_type} {node_id}")

        try:
            # Get the ID field for this entity type
            id_field = self.upsert_manager.ENTITY_ID_FIELDS.get(entity_type)
            if not id_field:
                return {
                    "success": False,
                    "message": f"Unknown entity type: {entity_type}",
                    "error": f"Entity type {entity_type} not in ENTITY_ID_FIELDS"
                }

            # Add the ID to properties (needed for upsert)
            full_properties = {id_field: node_id, **properties}

            # Use upsert (will update if exists, create if not)
            success = self.upsert_manager.upsert_entity(entity_type, full_properties)

            if success:
                return {
                    "success": True,
                    "message": f"Node updated successfully",
                    "data": {"entity_type": entity_type, "node_id": node_id}
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to update node",
                    "error": "Upsert operation returned False"
                }

        except Exception as e:
            logger.error(f"Error updating node: {e}")
            return {
                "success": False,
                "message": f"Error updating node: {str(e)}",
                "error": str(e)
            }

    def delete_node(
        self, entity_type: str, node_id: str, hard_delete: bool = False
    ) -> Dict[str, Any]:
        """
        Delete a node (soft delete by default).

        Args:
            entity_type: Entity label
            node_id: Unique identifier value
            hard_delete: If True, actually delete. If False, set active=false

        Returns:
            Dict with success status
        """
        logger.info(f"Deleting node: {entity_type} {node_id} (hard={hard_delete})")

        try:
            # Get the ID field
            id_field = self.upsert_manager.ENTITY_ID_FIELDS.get(entity_type)
            if not id_field:
                return {
                    "success": False,
                    "message": f"Unknown entity type: {entity_type}",
                    "error": f"Entity type {entity_type} not in ENTITY_ID_FIELDS"
                }

            with self.driver.session(database=self.database) as session:
                if hard_delete:
                    # Actually delete the node
                    query = f"""
                    MATCH (n:{entity_type} {{{id_field}: $node_id}})
                    DELETE n
                    RETURN count(n) as deleted_count
                    """
                else:
                    # Soft delete: set active=false
                    query = f"""
                    MATCH (n:{entity_type} {{{id_field}: $node_id}})
                    SET n.active = false
                    RETURN count(n) as updated_count
                    """

                result = session.run(query, node_id=node_id)
                record = result.single()

                if record:
                    count_key = "deleted_count" if hard_delete else "updated_count"
                    count = record[count_key]

                    if count > 0:
                        return {
                            "success": True,
                            "message": f"Node {'deleted' if hard_delete else 'deactivated'} successfully",
                            "data": {"entity_type": entity_type, "node_id": node_id}
                        }
                    else:
                        return {
                            "success": False,
                            "message": f"Node not found",
                            "error": f"No node found with {id_field}={node_id}"
                        }
                else:
                    return {
                        "success": False,
                        "message": f"Delete operation failed",
                        "error": "Query returned no result"
                    }

        except Exception as e:
            logger.error(f"Error deleting node: {e}")
            return {
                "success": False,
                "message": f"Error deleting node: {str(e)}",
                "error": str(e)
            }

    def create_relationship(
        self,
        from_entity_type: str,
        from_node_id: str,
        to_entity_type: str,
        to_node_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a relationship between two nodes.

        Args:
            from_entity_type: Source entity type
            from_node_id: Source node ID
            to_entity_type: Target entity type
            to_node_id: Target node ID
            relationship_type: Relationship type (e.g., 'MEMBER_OF')
            properties: Relationship properties

        Returns:
            Dict with success status
        """
        logger.info(f"Creating relationship: {from_entity_type}→{relationship_type}→{to_entity_type}")

        try:
            # Get ID fields
            from_id_field = self.upsert_manager.ENTITY_ID_FIELDS.get(from_entity_type)
            to_id_field = self.upsert_manager.ENTITY_ID_FIELDS.get(to_entity_type)

            if not from_id_field or not to_id_field:
                return {
                    "success": False,
                    "message": f"Unknown entity type",
                    "error": f"Entity types not in ENTITY_ID_FIELDS"
                }

            with self.driver.session(database=self.database) as session:
                # Build properties clause
                props_clause = ""
                if properties:
                    props_clause = "{" + ", ".join(f"{k}: ${k}" for k in properties.keys()) + "}"

                query = f"""
                MATCH (from:{from_entity_type} {{{from_id_field}: $from_id}})
                MATCH (to:{to_entity_type} {{{to_id_field}: $to_id}})
                MERGE (from)-[r:{relationship_type} {props_clause}]->(to)
                RETURN r
                """

                params = {
                    "from_id": from_node_id,
                    "to_id": to_node_id,
                    **(properties or {})
                }

                result = session.run(query, params)

                if result.single():
                    return {
                        "success": True,
                        "message": f"Relationship created successfully",
                        "data": {
                            "from_entity": from_entity_type,
                            "to_entity": to_entity_type,
                            "relationship_type": relationship_type
                        }
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Failed to create relationship",
                        "error": "One or both nodes not found"
                    }

        except Exception as e:
            logger.error(f"Error creating relationship: {e}")
            return {
                "success": False,
                "message": f"Error creating relationship: {str(e)}",
                "error": str(e)
            }

    def update_relationship(
        self,
        from_entity_type: str,
        from_node_id: str,
        to_entity_type: str,
        to_node_id: str,
        relationship_type: str,
        properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update relationship properties.

        Args:
            from_entity_type: Source entity type
            from_node_id: Source node ID
            to_entity_type: Target entity type
            to_node_id: Target node ID
            relationship_type: Relationship type
            properties: Properties to update

        Returns:
            Dict with success status
        """
        logger.info(f"Updating relationship: {from_entity_type}→{relationship_type}→{to_entity_type}")

        try:
            from_id_field = self.upsert_manager.ENTITY_ID_FIELDS.get(from_entity_type)
            to_id_field = self.upsert_manager.ENTITY_ID_FIELDS.get(to_entity_type)

            if not from_id_field or not to_id_field:
                return {
                    "success": False,
                    "message": f"Unknown entity type",
                    "error": f"Entity types not in ENTITY_ID_FIELDS"
                }

            with self.driver.session(database=self.database) as session:
                query = f"""
                MATCH (from:{from_entity_type} {{{from_id_field}: $from_id}})
                      -[r:{relationship_type}]->
                      (to:{to_entity_type} {{{to_id_field}: $to_id}})
                SET r += $properties
                RETURN r
                """

                params = {
                    "from_id": from_node_id,
                    "to_id": to_node_id,
                    "properties": properties
                }

                result = session.run(query, params)

                if result.single():
                    return {
                        "success": True,
                        "message": f"Relationship updated successfully",
                        "data": {"relationship_type": relationship_type}
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Relationship not found",
                        "error": "No matching relationship found"
                    }

        except Exception as e:
            logger.error(f"Error updating relationship: {e}")
            return {
                "success": False,
                "message": f"Error updating relationship: {str(e)}",
                "error": str(e)
            }

    def query_nodes(
        self,
        entity_type: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        skip: int = 0
    ) -> Dict[str, Any]:
        """
        Query nodes with filters.

        Args:
            entity_type: Entity type to query
            filters: Property filters (key-value pairs for exact match)
            limit: Maximum number of results
            skip: Number of results to skip

        Returns:
            Dict with nodes list and counts
        """
        logger.info(f"Querying nodes: {entity_type} with filters: {filters}")

        try:
            with self.driver.session(database=self.database) as session:
                # Build WHERE clause from filters
                where_clauses = []
                params = {"limit": limit, "skip": skip}

                if filters:
                    for key, value in filters.items():
                        param_name = f"filter_{key}"
                        where_clauses.append(f"n.{key} = ${param_name}")
                        params[param_name] = value

                where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

                # Count query
                count_query = f"""
                MATCH (n:{entity_type})
                {where_clause}
                RETURN count(n) as total
                """
                count_result = session.run(count_query, params)
                total_count = count_result.single()["total"]

                # Data query
                query = f"""
                MATCH (n:{entity_type})
                {where_clause}
                RETURN n
                SKIP $skip
                LIMIT $limit
                """
                result = session.run(query, params)

                # Convert nodes to dicts
                nodes = []
                for record in result:
                    node = record["n"]
                    node_dict = dict(node)  # Convert node to dict
                    nodes.append(node_dict)

                return {
                    "success": True,
                    "nodes": nodes,
                    "total_count": total_count,
                    "returned_count": len(nodes)
                }

        except Exception as e:
            logger.error(f"Error querying nodes: {e}")
            return {
                "success": False,
                "nodes": [],
                "total_count": 0,
                "returned_count": 0,
                "error": str(e)
            }

    def health_check(self) -> Dict[str, Any]:
        """
        Check Neo4j connection health.

        Returns:
            Dict with health status
        """
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run("RETURN 1 as health")
                result.single()

            return {
                "status": "healthy",
                "neo4j_connected": True,
                "message": "Neo4j connection is working"
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "neo4j_connected": False,
                "message": f"Neo4j connection failed: {str(e)}"
            }
