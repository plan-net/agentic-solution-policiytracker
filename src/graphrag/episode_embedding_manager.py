"""
Episode Embedding Manager for semantic search on Episodic nodes.

This module provides functionality to generate and manage content embeddings
for Episodic nodes in the Neo4j knowledge graph, enabling semantic search
over document chunks (episodes).

Usage:
    manager = EpisodeEmbeddingManager(driver, embedder)
    await manager.add_content_embedding(episode_uuid, content)
    stats = await manager.get_embedding_stats()
"""

import logging
import os
from typing import Optional

from neo4j import AsyncGraphDatabase

logger = logging.getLogger(__name__)

# Default configuration
# Updated to text-embedding-ada-002 for better multilingual support (100% vs 13% cross-lingual similarity)
EMBEDDING_MODEL = "text-embedding-ada-002"
EMBEDDING_DIM = 1536


class EpisodeEmbeddingManager:
    """
    Manages content embeddings for Episodic nodes.

    This class handles embedding generation and storage for episode content,
    working alongside Graphiti's existing Entity embeddings to enable
    semantic search over source documents.
    """

    def __init__(
        self,
        neo4j_uri: Optional[str] = None,
        neo4j_user: Optional[str] = None,
        neo4j_password: Optional[str] = None,
        neo4j_database: Optional[str] = None,
        embedder=None,
    ):
        """
        Initialize the Episode Embedding Manager.

        Args:
            neo4j_uri: Neo4j connection URI (defaults to NEO4J_URI env var)
            neo4j_user: Neo4j username (defaults to NEO4J_USER env var)
            neo4j_password: Neo4j password (defaults to NEO4J_PASSWORD env var)
            neo4j_database: Neo4j database name (defaults to NEO4J_DATABASE env var)
            embedder: Optional Graphiti embedder instance. If not provided,
                     creates one using APISIX routing for cost tracking.
        """
        self.neo4j_uri = neo4j_uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = neo4j_user or os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = neo4j_password or os.getenv("NEO4J_PASSWORD", "password123")
        self.neo4j_database = neo4j_database or os.getenv("NEO4J_DATABASE", "politicalmonitoring.v3")

        self._driver = None
        self._embedder = embedder

    async def _get_driver(self):
        """Get or create Neo4j async driver."""
        if self._driver is None:
            self._driver = AsyncGraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )
        return self._driver

    async def _get_embedder(self):
        """Get or create embedder with APISIX routing."""
        if self._embedder is None:
            from src.flows.shared.apisix_llm_client import create_apisix_graphiti_embedder
            self._embedder = create_apisix_graphiti_embedder(
                embedding_model=EMBEDDING_MODEL
            )
        return self._embedder

    async def close(self):
        """Close the Neo4j driver connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None

    async def add_content_embedding(
        self,
        episode_uuid: str,
        content: str,
    ) -> bool:
        """
        Generate and store content embedding for an episode.

        Args:
            episode_uuid: UUID of the Episodic node
            content: Episode content text to embed

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get embedder
            embedder = await self._get_embedder()

            # Generate embedding (Graphiti embedder returns list[float])
            embedding = await embedder.create(input_data=[content])

            if not embedding or len(embedding) != EMBEDDING_DIM:
                logger.warning(
                    f"Invalid embedding for episode {episode_uuid}: "
                    f"expected {EMBEDDING_DIM} dims, got {len(embedding) if embedding else 0}"
                )
                return False

            # Store embedding in Neo4j
            driver = await self._get_driver()
            query = """
                MATCH (e:Episodic {uuid: $uuid})
                SET e.content_embedding = $embedding
                RETURN e.uuid AS uuid
            """

            async with driver.session(database=self.neo4j_database) as session:
                result = await session.run(query, uuid=episode_uuid, embedding=embedding)
                records = await result.data()

            if records:
                logger.debug(f"Added content embedding to episode {episode_uuid}")
                return True
            else:
                logger.warning(f"Episode not found: {episode_uuid}")
                return False

        except Exception as e:
            logger.error(f"Failed to add embedding to episode {episode_uuid}: {e}")
            return False

    async def get_episodes_without_embeddings(
        self,
        group_ids: Optional[list[str]] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        Find episodes that don't have content embeddings.

        Used for backfill operations.

        Args:
            group_ids: Optional filter by group IDs
            limit: Maximum episodes to return

        Returns:
            List of {uuid, content, name} dicts for episodes needing embeddings
        """
        driver = await self._get_driver()

        group_filter = ""
        params = {"limit": limit}

        if group_ids:
            group_filter = "AND e.group_id IN $group_ids"
            params["group_ids"] = group_ids

        query = f"""
            MATCH (e:Episodic)
            WHERE e.content_embedding IS NULL
            {group_filter}
            RETURN e.uuid AS uuid, e.content AS content, e.name AS name
            ORDER BY e.created_at DESC
            LIMIT $limit
        """

        async with driver.session(database=self.neo4j_database) as session:
            result = await session.run(query, **params)
            records = await result.data()

        return [
            {
                "uuid": r["uuid"],
                "content": r["content"],
                "name": r.get("name", "")
            }
            for r in records
        ]

    async def get_embedding_stats(
        self,
        group_ids: Optional[list[str]] = None
    ) -> dict:
        """
        Get statistics on episode embeddings.

        Args:
            group_ids: Optional filter by group IDs

        Returns:
            Dict with total_episodes, episodes_with_embeddings,
            episodes_without_embeddings, coverage_percentage
        """
        driver = await self._get_driver()

        group_filter = ""
        params = {}

        if group_ids:
            group_filter = "WHERE e.group_id IN $group_ids"
            params["group_ids"] = group_ids

        query = f"""
            MATCH (e:Episodic)
            {group_filter}
            RETURN
                count(e) AS total,
                count(e.content_embedding) AS with_embedding
        """

        async with driver.session(database=self.neo4j_database) as session:
            result = await session.run(query, **params)
            records = await result.data()

        if records:
            total = records[0]["total"]
            with_emb = records[0]["with_embedding"]
            return {
                "total_episodes": total,
                "episodes_with_embeddings": with_emb,
                "episodes_without_embeddings": total - with_emb,
                "coverage_percentage": round((with_emb / total * 100), 2) if total > 0 else 0
            }

        return {
            "total_episodes": 0,
            "episodes_with_embeddings": 0,
            "episodes_without_embeddings": 0,
            "coverage_percentage": 0
        }

    async def generate_query_embedding(self, query: str) -> list[float]:
        """
        Generate embedding for a search query.

        Args:
            query: Search query text

        Returns:
            List of floats representing the query embedding
        """
        embedder = await self._get_embedder()
        return await embedder.create(input_data=[query])

    async def remove_embedding(self, episode_uuid: str) -> bool:
        """
        Remove content embedding from an episode (for testing/cleanup).

        Args:
            episode_uuid: UUID of the Episodic node

        Returns:
            True if successful
        """
        driver = await self._get_driver()

        query = """
            MATCH (e:Episodic {uuid: $uuid})
            REMOVE e.content_embedding
            RETURN e.uuid AS uuid
        """

        async with driver.session(database=self.neo4j_database) as session:
            result = await session.run(query, uuid=episode_uuid)
            records = await result.data()

        return len(records) > 0
