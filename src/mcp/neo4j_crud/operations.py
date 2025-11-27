"""Neo4j CRUD operations using Neo4jUpsertManager."""

import logging
import os
from typing import Any, Optional

from neo4j import Driver

# Import Graphiti registration for data consistency
from src.flows.bundestag_common.graphiti_registration import GraphitiNodeRegistrar

# Import the existing upsert manager
from src.flows.bundestag_common.neo4j_upsert import Neo4jUpsertManager

logger = logging.getLogger(__name__)


class Neo4jCRUDOperations:
    """CRUD operations for Neo4j using existing infrastructure."""

    def __init__(self, driver: Driver, database: str):
        """
        Initialize CRUD operations with Graphiti registration support.

        Args:
            driver: Neo4j driver instance
            database: Database name
        """
        self.driver = driver
        self.database = database
        self.upsert_manager = Neo4jUpsertManager(driver, database)

        # Initialize Graphiti registrar for data consistency
        openai_key = os.getenv("OPENAI_API_KEY")
        enable_graphiti = os.getenv("ENABLE_GRAPHITI_REGISTRATION", "true").lower() == "true"

        if enable_graphiti and openai_key:
            try:
                self.graphiti_registrar = GraphitiNodeRegistrar(
                    neo4j_driver=driver, neo4j_database=database, openai_api_key=openai_key
                )
                logger.info("✅ Graphiti registration enabled in MCP Server")
            except Exception as e:
                logger.warning(f"⚠️ Graphiti registration failed to initialize: {e}")
                self.graphiti_registrar = None
        else:
            self.graphiti_registrar = None
            if not enable_graphiti:
                logger.info("ℹ️ Graphiti registration disabled via ENABLE_GRAPHITI_REGISTRATION")
            if not openai_key:
                logger.warning("⚠️ Graphiti registration disabled: OPENAI_API_KEY not found")

        logger.info(f"Initialized Neo4jCRUDOperations for database: {database}")

    async def create_node(self, entity_type: str, properties: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new node with mandatory Graphiti registration.

        Args:
            entity_type: Entity label (e.g., 'BundestagPerson')
            properties: Node properties

        Returns:
            Dict with success status and node details

        Raises:
            Exception if Graphiti registration fails (node will be rolled back)
        """
        logger.info(f"Creating node: {entity_type}")

        try:
            # Step 1: Create node via upsert manager
            success = self.upsert_manager.upsert_entity(entity_type, properties)

            if not success:
                return {
                    "success": False,
                    "message": "Failed to create node",
                    "error": "Upsert operation returned False",
                }

            # Get the ID field for this entity type
            id_field = self.upsert_manager.ENTITY_ID_FIELDS.get(entity_type)
            node_id = properties.get(id_field) if id_field else None

            # Step 2: Register with Graphiti (MANDATORY for data consistency)
            if self.graphiti_registrar:
                try:
                    await self._register_with_graphiti(entity_type, properties)
                    logger.info(
                        f"✅ Node created with Graphiti registration: {entity_type} {node_id}"
                    )
                except Exception as e:
                    # ROLLBACK: Delete the node we just created
                    logger.error(
                        f"❌ Graphiti registration failed, rolling back node creation: {e}"
                    )
                    self._rollback_node_creation(entity_type, properties)
                    return {
                        "success": False,
                        "message": "Operation failed: Graphiti registration error",
                        "error": f"Graphiti registration failed: {str(e)}. Node was rolled back.",
                    }

            return {
                "success": True,
                "message": "Node created successfully"
                + (" with Graphiti registration" if self.graphiti_registrar else ""),
                "data": {"entity_type": entity_type, "node_id": node_id},
            }

        except Exception as e:
            logger.error(f"Error creating node: {e}")
            return {"success": False, "message": f"Error creating node: {str(e)}", "error": str(e)}

    def update_node(
        self, entity_type: str, node_id: str, properties: dict[str, Any]
    ) -> dict[str, Any]:
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
                    "error": f"Entity type {entity_type} not in ENTITY_ID_FIELDS",
                }

            # Add the ID to properties (needed for upsert)
            full_properties = {id_field: node_id, **properties}

            # Use upsert (will update if exists, create if not)
            success = self.upsert_manager.upsert_entity(entity_type, full_properties)

            if success:
                return {
                    "success": True,
                    "message": "Node updated successfully",
                    "data": {"entity_type": entity_type, "node_id": node_id},
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to update node",
                    "error": "Upsert operation returned False",
                }

        except Exception as e:
            logger.error(f"Error updating node: {e}")
            return {"success": False, "message": f"Error updating node: {str(e)}", "error": str(e)}

    def delete_node(
        self, entity_type: str, node_id: str, hard_delete: bool = False
    ) -> dict[str, Any]:
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
                    "error": f"Entity type {entity_type} not in ENTITY_ID_FIELDS",
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
                            "data": {"entity_type": entity_type, "node_id": node_id},
                        }
                    else:
                        return {
                            "success": False,
                            "message": "Node not found",
                            "error": f"No node found with {id_field}={node_id}",
                        }
                else:
                    return {
                        "success": False,
                        "message": "Delete operation failed",
                        "error": "Query returned no result",
                    }

        except Exception as e:
            logger.error(f"Error deleting node: {e}")
            return {"success": False, "message": f"Error deleting node: {str(e)}", "error": str(e)}

    def create_relationship(
        self,
        from_entity_type: str,
        from_node_id: str,
        to_entity_type: str,
        to_node_id: str,
        relationship_type: str,
        properties: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
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
        logger.info(
            f"Creating relationship: {from_entity_type}→{relationship_type}→{to_entity_type}"
        )

        try:
            # Get ID fields
            from_id_field = self.upsert_manager.ENTITY_ID_FIELDS.get(from_entity_type)
            to_id_field = self.upsert_manager.ENTITY_ID_FIELDS.get(to_entity_type)

            if not from_id_field or not to_id_field:
                return {
                    "success": False,
                    "message": "Unknown entity type",
                    "error": "Entity types not in ENTITY_ID_FIELDS",
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

                params = {"from_id": from_node_id, "to_id": to_node_id, **(properties or {})}

                result = session.run(query, params)

                if result.single():
                    return {
                        "success": True,
                        "message": "Relationship created successfully",
                        "data": {
                            "from_entity": from_entity_type,
                            "to_entity": to_entity_type,
                            "relationship_type": relationship_type,
                        },
                    }
                else:
                    return {
                        "success": False,
                        "message": "Failed to create relationship",
                        "error": "One or both nodes not found",
                    }

        except Exception as e:
            logger.error(f"Error creating relationship: {e}")
            return {
                "success": False,
                "message": f"Error creating relationship: {str(e)}",
                "error": str(e),
            }

    def update_relationship(
        self,
        from_entity_type: str,
        from_node_id: str,
        to_entity_type: str,
        to_node_id: str,
        relationship_type: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
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
        logger.info(
            f"Updating relationship: {from_entity_type}→{relationship_type}→{to_entity_type}"
        )

        try:
            from_id_field = self.upsert_manager.ENTITY_ID_FIELDS.get(from_entity_type)
            to_id_field = self.upsert_manager.ENTITY_ID_FIELDS.get(to_entity_type)

            if not from_id_field or not to_id_field:
                return {
                    "success": False,
                    "message": "Unknown entity type",
                    "error": "Entity types not in ENTITY_ID_FIELDS",
                }

            with self.driver.session(database=self.database) as session:
                query = f"""
                MATCH (from:{from_entity_type} {{{from_id_field}: $from_id}})
                      -[r:{relationship_type}]->
                      (to:{to_entity_type} {{{to_id_field}: $to_id}})
                SET r += $properties
                RETURN r
                """

                params = {"from_id": from_node_id, "to_id": to_node_id, "properties": properties}

                result = session.run(query, params)

                if result.single():
                    return {
                        "success": True,
                        "message": "Relationship updated successfully",
                        "data": {"relationship_type": relationship_type},
                    }
                else:
                    return {
                        "success": False,
                        "message": "Relationship not found",
                        "error": "No matching relationship found",
                    }

        except Exception as e:
            logger.error(f"Error updating relationship: {e}")
            return {
                "success": False,
                "message": f"Error updating relationship: {str(e)}",
                "error": str(e),
            }

    def query_nodes(
        self,
        entity_type: str,
        filters: Optional[dict[str, Any]] = None,
        limit: int = 100,
        skip: int = 0,
    ) -> dict[str, Any]:
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
                    "returned_count": len(nodes),
                }

        except Exception as e:
            logger.error(f"Error querying nodes: {e}")
            return {
                "success": False,
                "nodes": [],
                "total_count": 0,
                "returned_count": 0,
                "error": str(e),
            }

    def health_check(self) -> dict[str, Any]:
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
                "message": "Neo4j connection is working",
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "neo4j_connected": False,
                "message": f"Neo4j connection failed: {str(e)}",
            }

    # ========================================================================
    # Graphiti Registration Helper Methods (for Data Consistency)
    # ========================================================================

    async def _register_with_graphiti(self, entity_type: str, properties: dict[str, Any]) -> None:
        """
        Register node with Graphiti metadata (mandatory for search compatibility).

        Args:
            entity_type: Entity label
            properties: Node properties

        Raises:
            Exception if registration fails
        """
        # Get entity ID
        id_field = self.upsert_manager.ENTITY_ID_FIELDS.get(entity_type)
        if not id_field:
            raise ValueError(f"Unknown entity type: {entity_type}")

        entity_id = properties.get(id_field)
        if not entity_id:
            raise ValueError(f"Missing entity ID field: {id_field}")

        # Generate entity name for embedding
        entity_name = properties.get("name") or self._generate_name(entity_type, properties)

        # Generate embedding using Graphiti's OpenAI client
        embedding = await self.graphiti_registrar.generate_embedding(entity_name)

        # Add Entity label + metadata to the node
        result = self.graphiti_registrar.add_entity_metadata(
            entity_label=entity_type,
            entity_id_field=id_field,
            entity_id_value=entity_id,
            entity_name=entity_name,
            name_embedding=embedding,
        )

        if not result.get("success"):
            raise Exception(f"Failed to add Graphiti metadata: {result.get('error')}")

        logger.debug(f"Graphiti registration successful: {entity_type} {entity_id}")

    def _generate_name(self, entity_type: str, properties: dict[str, Any]) -> str:
        """
        Generate display name for entity (for Graphiti embedding).

        Args:
            entity_type: Entity label
            properties: Node properties

        Returns:
            Human-readable entity name
        """
        if entity_type == "BundestagPerson":
            vorname = properties.get("vorname", "")
            nachname = properties.get("nachname", "")
            name = f"{vorname} {nachname}".strip()
            return name if name else f"Person {properties.get('person_id', '')}"

        elif entity_type == "Vorgang":
            return properties.get("titel") or f"Vorgang {properties.get('vorgang_id', '')}"

        elif entity_type == "Drucksache":
            nummer = properties.get("drucksache_nummer", "")
            titel = properties.get("titel", "")
            if titel:
                return f"Drucksache {nummer}: {titel}"
            return f"Drucksache {nummer}"

        elif entity_type == "Plenarprotokoll":
            wp = properties.get("wahlperiode", "")
            sitzung = properties.get("sitzungsnummer", "")
            return f"Plenarprotokoll {wp}/{sitzung}"

        elif entity_type == "Aktivitaet":
            return properties.get("titel") or f"Aktivität {properties.get('aktivitaet_id', '')}"

        else:
            # Fallback: use first available descriptive field
            for field in ["titel", "name", "bezeichnung", "title"]:
                if field in properties and properties[field]:
                    return str(properties[field])

            # Last resort: use ID field
            id_field = self.upsert_manager.ENTITY_ID_FIELDS.get(entity_type)
            if id_field and id_field in properties:
                return f"{entity_type} {properties[id_field]}"

            return f"{entity_type} (unnamed)"

    def _rollback_node_creation(self, entity_type: str, properties: dict[str, Any]) -> None:
        """
        Delete node if Graphiti registration failed (rollback for data consistency).

        Args:
            entity_type: Entity label
            properties: Node properties
        """
        try:
            id_field = self.upsert_manager.ENTITY_ID_FIELDS.get(entity_type)
            if not id_field:
                logger.error(f"Cannot rollback: unknown entity type {entity_type}")
                return

            entity_id = properties.get(id_field)
            if not entity_id:
                logger.error(f"Cannot rollback: missing {id_field} in properties")
                return

            with self.driver.session(database=self.database) as session:
                result = session.run(
                    f"MATCH (n:{entity_type} {{{id_field}: $id}}) DELETE n RETURN count(n) as deleted",
                    id=entity_id,
                )
                deleted = result.single()["deleted"]
                if deleted > 0:
                    logger.info(f"✅ Rolled back node creation: {entity_type} {entity_id}")
                else:
                    logger.warning(f"⚠️ Rollback failed: node not found {entity_type} {entity_id}")

        except Exception as rollback_error:
            logger.error(
                f"❌ Rollback failed for {entity_type} (manual cleanup required): {rollback_error}"
            )
