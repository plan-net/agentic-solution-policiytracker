"""
Graphiti Node Registration for Bundestag Flows.

This module makes Direct Neo4j nodes searchable by Graphiti's client.search()
by adding the required :Entity label, name embeddings, and metadata.

Architecture:
- Bundestag flows create nodes directly in Neo4j (deterministic ingestion)
- GraphitiNodeRegistrar adds Graphiti-compatible metadata to those nodes
- Graphiti client.search() can then find and query these nodes

Required Graphiti Metadata:
- :Entity label (in addition to specific label like :BundestagPerson)
- uuid: Unique identifier
- name_embedding: 1536-dim vector from text-embedding-3-small
- group_id: "bundestag_direct" to distinguish from LLM-extracted entities
- created_at: Timestamp
"""

import os
import uuid as uuid_lib
from datetime import datetime
from typing import Any, Optional

import structlog
from neo4j import Driver
from openai import AsyncOpenAI

logger = structlog.get_logger()

# Graphiti constants
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
GROUP_ID = "bundestag_direct"  # Distinguishes direct ingestion from LLM extraction


class GraphitiNodeRegistrar:
    """
    Register Direct Neo4j nodes with Graphiti-compatible metadata.

    This class adds the :Entity label and required metadata to nodes created
    by deterministic Bundestag flows, making them searchable via Graphiti's
    temporal search capabilities.

    Usage:
        registrar = GraphitiNodeRegistrar(driver, database, openai_api_key)
        await registrar.register_bundestag_person(
            person_id="11004809",
            person_name="Olaf Scholz",
            properties={...}
        )
    """

    def __init__(
        self,
        neo4j_driver: Driver,
        neo4j_database: str,
        openai_api_key: str,
    ):
        """
        Initialize the registrar.

        Args:
            neo4j_driver: Neo4j driver instance
            neo4j_database: Database name (e.g., "politicalmonitoring.v3")
            openai_api_key: OpenAI API key for embeddings
        """
        self.driver = neo4j_driver
        self.database = neo4j_database

        # Route embeddings through APISIX for cost tracking
        apisix_base_url = os.getenv("APISIX_GATEWAY_URL", "http://localhost:9080/v1")
        self.openai_client = AsyncOpenAI(
            api_key=openai_api_key,
            base_url=apisix_base_url,
        )

        logger.info(
            "Initialized GraphitiNodeRegistrar",
            database=neo4j_database,
            group_id=GROUP_ID,
            embedding_model=EMBEDDING_MODEL,
            apisix_base_url=apisix_base_url,
        )

    async def generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for text using OpenAI.

        Args:
            text: Text to embed

        Returns:
            1536-dimensional embedding vector

        Raises:
            Exception: If embedding generation fails
        """
        try:
            response = await self.openai_client.embeddings.create(model=EMBEDDING_MODEL, input=text)
            embedding = response.data[0].embedding

            if len(embedding) != EMBEDDING_DIM:
                raise ValueError(f"Expected {EMBEDDING_DIM}-dim embedding, got {len(embedding)}")

            return embedding

        except Exception as e:
            logger.error("Failed to generate embedding", text=text[:50], error=str(e))
            raise

    def add_entity_metadata(
        self,
        entity_label: str,
        entity_id_field: str,
        entity_id_value: Any,
        entity_name: str,
        name_embedding: list[float],
        additional_properties: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Add Graphiti metadata to an existing node.

        This method:
        1. Adds :Entity label (in addition to existing label)
        2. Sets uuid, group_id, created_at, name_embedding
        3. Optionally updates additional properties

        Args:
            entity_label: Node label (e.g., "BundestagPerson")
            entity_id_field: Unique identifier field name (e.g., "person_id")
            entity_id_value: Value of identifier (e.g., "11004809")
            entity_name: Display name for entity (e.g., "Olaf Scholz")
            name_embedding: 1536-dim embedding vector
            additional_properties: Optional dict of extra properties to set

        Returns:
            Dict with registration results
        """
        query = f"""
        MATCH (n:{entity_label} {{{entity_id_field}: $entity_id_value}})

        // Add :Entity label if not present
        SET n:Entity

        // Add Graphiti-required metadata
        SET n.uuid = CASE WHEN n.uuid IS NULL THEN $uuid ELSE n.uuid END
        SET n.group_id = $group_id
        SET n.name = $entity_name
        SET n.name_embedding = $name_embedding
        SET n.created_at = CASE WHEN n.created_at IS NULL THEN $created_at ELSE n.created_at END

        // Add additional properties if provided
        {"SET n += $additional_properties" if additional_properties else ""}

        RETURN n.uuid as uuid, n.name as name, labels(n) as labels
        """

        params = {
            "entity_id_value": entity_id_value,
            "uuid": str(uuid_lib.uuid4()),
            "group_id": GROUP_ID,
            "entity_name": entity_name,
            "name_embedding": name_embedding,
            "created_at": datetime.utcnow().isoformat(),
        }

        if additional_properties:
            params["additional_properties"] = additional_properties

        with self.driver.session(database=self.database) as session:
            result = session.run(query, params)
            record = result.single()

            if not record:
                logger.warning(
                    "No node found to register",
                    entity_label=entity_label,
                    entity_id_field=entity_id_field,
                    entity_id_value=entity_id_value,
                )
                return {"success": False, "reason": "node_not_found"}

            logger.info(
                "Registered node with Graphiti metadata",
                entity_label=entity_label,
                entity_name=entity_name,
                uuid=record["uuid"],
                labels=record["labels"],
            )

            return {
                "success": True,
                "uuid": record["uuid"],
                "name": record["name"],
                "labels": record["labels"],
            }

    async def register_bundestag_person(
        self,
        person_id: str,
        person_name: str,
        additional_properties: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Register a BundestagPerson node with Graphiti metadata.

        Args:
            person_id: Person ID from DIP API (e.g., "11004809")
            person_name: Full name (e.g., "Olaf Scholz")
            additional_properties: Optional extra properties

        Returns:
            Registration result dict
        """
        embedding = await self.generate_embedding(person_name)

        return self.add_entity_metadata(
            entity_label="BundestagPerson",
            entity_id_field="person_id",
            entity_id_value=person_id,
            entity_name=person_name,
            name_embedding=embedding,
            additional_properties=additional_properties,
        )

    async def register_vorgang(
        self,
        vorgang_id: str,
        vorgang_name: str,
        additional_properties: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Register a Vorgang node with Graphiti metadata.

        Args:
            vorgang_id: Vorgang ID from DIP API
            vorgang_name: Vorgang title/name
            additional_properties: Optional extra properties

        Returns:
            Registration result dict
        """
        embedding = await self.generate_embedding(vorgang_name)

        return self.add_entity_metadata(
            entity_label="Vorgang",
            entity_id_field="vorgang_id",
            entity_id_value=vorgang_id,
            entity_name=vorgang_name,
            name_embedding=embedding,
            additional_properties=additional_properties,
        )

    async def register_drucksache(
        self,
        drucksache_id: str,
        drucksache_name: str,
        additional_properties: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Register a Drucksache node with Graphiti metadata.

        Args:
            drucksache_id: Drucksache ID from DIP API
            drucksache_name: Drucksache title
            additional_properties: Optional extra properties

        Returns:
            Registration result dict
        """
        embedding = await self.generate_embedding(drucksache_name)

        return self.add_entity_metadata(
            entity_label="Drucksache",
            entity_id_field="drucksache_id",
            entity_id_value=drucksache_id,
            entity_name=drucksache_name,
            name_embedding=embedding,
            additional_properties=additional_properties,
        )

    async def register_plenarprotokoll(
        self,
        sitzungsnummer: int,
        wahlperiode: int,
        plenarprotokoll_name: str,
        additional_properties: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Register a Plenarprotokoll node with Graphiti metadata.

        Note: Plenarprotokoll uses composite key (sitzungsnummer, wahlperiode).

        Args:
            sitzungsnummer: Session number (integer)
            wahlperiode: Electoral period number
            plenarprotokoll_name: Protocol name/title
            additional_properties: Optional extra properties

        Returns:
            Registration result dict
        """
        embedding = await self.generate_embedding(plenarprotokoll_name)

        # Special handling for composite key
        query = (
            """
        MATCH (n:Plenarprotokoll {sitzungsnummer: $sitzungsnummer, wahlperiode: $wahlperiode})

        // Add :Entity label if not present
        SET n:Entity

        // Add Graphiti-required metadata
        SET n.uuid = CASE WHEN n.uuid IS NULL THEN $uuid ELSE n.uuid END
        SET n.group_id = $group_id
        SET n.name = $plenarprotokoll_name
        SET n.name_embedding = $name_embedding
        SET n.created_at = CASE WHEN n.created_at IS NULL THEN $created_at ELSE n.created_at END

        // Add additional properties if provided
        """
            + ("SET n += $additional_properties" if additional_properties else "")
            + """

        RETURN n.uuid as uuid, n.name as name, labels(n) as labels
        """
        )

        params = {
            "sitzungsnummer": sitzungsnummer,
            "wahlperiode": wahlperiode,
            "uuid": str(uuid_lib.uuid4()),
            "group_id": GROUP_ID,
            "plenarprotokoll_name": plenarprotokoll_name,
            "name_embedding": embedding,
            "created_at": datetime.utcnow().isoformat(),
        }

        if additional_properties:
            params["additional_properties"] = additional_properties

        with self.driver.session(database=self.database) as session:
            result = session.run(query, params)
            record = result.single()

            if not record:
                logger.warning(
                    "No Plenarprotokoll found to register",
                    sitzungsnummer=sitzungsnummer,
                    wahlperiode=wahlperiode,
                )
                return {"success": False, "reason": "node_not_found"}

            logger.info(
                "Registered Plenarprotokoll with Graphiti metadata",
                sitzungsnummer=sitzungsnummer,
                wahlperiode=wahlperiode,
                uuid=record["uuid"],
            )

            return {
                "success": True,
                "uuid": record["uuid"],
                "name": record["name"],
                "labels": record["labels"],
            }

    async def register_aktivitaet(
        self,
        aktivitaet_id: str,
        aktivitaet_name: str,
        additional_properties: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Register an Aktivitaet node with Graphiti metadata.

        Args:
            aktivitaet_id: Aktivitaet ID from DIP API
            aktivitaet_name: Aktivitaet title/description
            additional_properties: Optional extra properties

        Returns:
            Registration result dict
        """
        embedding = await self.generate_embedding(aktivitaet_name)

        return self.add_entity_metadata(
            entity_label="Aktivitaet",
            entity_id_field="aktivitaet_id",
            entity_id_value=aktivitaet_id,
            entity_name=aktivitaet_name,
            name_embedding=embedding,
            additional_properties=additional_properties,
        )

    async def register_wahlperiode(
        self,
        wahlperiode_nummer: int,
        wahlperiode_name: str,
        additional_properties: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Register a Wahlperiode node with Graphiti metadata.

        Args:
            wahlperiode_nummer: Electoral period number (e.g., 20)
            wahlperiode_name: Display name (e.g., "Wahlperiode 20")
            additional_properties: Optional extra properties

        Returns:
            Registration result dict
        """
        embedding = await self.generate_embedding(wahlperiode_name)

        return self.add_entity_metadata(
            entity_label="Wahlperiode",
            entity_id_field="wahlperiode_nummer",
            entity_id_value=wahlperiode_nummer,
            entity_name=wahlperiode_name,
            name_embedding=embedding,
            additional_properties=additional_properties,
        )

    async def register_fraktion(
        self,
        fraktion_id: str,
        fraktion_name: str,
        additional_properties: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Register a BundestagFraktion node with Graphiti metadata.

        Args:
            fraktion_id: Fraktion ID (e.g., "fraktion_spd_20")
            fraktion_name: Fraktion name (e.g., "SPD")
            additional_properties: Optional extra properties

        Returns:
            Registration result dict
        """
        embedding = await self.generate_embedding(fraktion_name)

        return self.add_entity_metadata(
            entity_label="BundestagFraktion",
            entity_id_field="fraktion_id",
            entity_id_value=fraktion_id,
            entity_name=fraktion_name,
            name_embedding=embedding,
            additional_properties=additional_properties,
        )

    async def batch_register_nodes(
        self,
        entity_label: str,
        entity_id_field: str,
        nodes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Register multiple nodes in batch (more efficient for large datasets).

        Each node dict must contain:
        - The entity_id field value
        - A 'name' field for embedding generation

        Args:
            entity_label: Node label (e.g., "BundestagPerson")
            entity_id_field: Identifier field name
            nodes: List of node dicts with id and name

        Returns:
            Dict with success/failure counts
        """
        results = {"successful": 0, "failed": 0, "errors": []}

        for node in nodes:
            try:
                entity_id = node.get(entity_id_field)
                entity_name = node.get("name")

                if not entity_id or not entity_name:
                    logger.warning(
                        "Skipping node missing id or name",
                        entity_label=entity_label,
                        node=node,
                    )
                    results["failed"] += 1
                    continue

                embedding = await self.generate_embedding(entity_name)

                # Remove id and name from additional_properties
                additional_props = {
                    k: v for k, v in node.items() if k not in [entity_id_field, "name"]
                }

                result = self.add_entity_metadata(
                    entity_label=entity_label,
                    entity_id_field=entity_id_field,
                    entity_id_value=entity_id,
                    entity_name=entity_name,
                    name_embedding=embedding,
                    additional_properties=additional_props if additional_props else None,
                )

                if result.get("success"):
                    results["successful"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(result.get("reason", "unknown"))

            except Exception as e:
                logger.error(
                    "Failed to register node in batch",
                    entity_label=entity_label,
                    node=node,
                    error=str(e),
                )
                results["failed"] += 1
                results["errors"].append(str(e))

        logger.info(
            "Batch registration complete",
            entity_label=entity_label,
            successful=results["successful"],
            failed=results["failed"],
        )

        return results

    def close(self):
        """Close the OpenAI client connection."""
        # AsyncOpenAI doesn't require explicit closing
        pass
