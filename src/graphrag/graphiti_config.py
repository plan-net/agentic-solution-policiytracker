"""
Graphiti Configuration and Client Management.

This module provides configuration management and client creation utilities
for Graphiti temporal knowledge graph integration.

Version: 0.2.0
"""

import os
from datetime import UTC
from typing import Optional

from graphiti_core import Graphiti
from pydantic import BaseModel, Field, validator

from src.utils.exceptions import ConfigurationError


class GraphitiSettings(BaseModel):
    """Graphiti connection and operational settings."""

    # Neo4j Connection
    neo4j_uri: str = Field(
        default_factory=lambda: os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        description="Neo4j database connection URI",
    )
    neo4j_user: str = Field(
        default_factory=lambda: os.getenv("NEO4J_USER", "neo4j"), description="Neo4j username"
    )
    neo4j_password: str = Field(
        default_factory=lambda: os.getenv("NEO4J_PASSWORD", "password123"),
        description="Neo4j password",
    )

    # Graphiti Configuration
    default_group_id: str = Field(
        default="political_docs", description="Default group ID for political document episodes"
    )

    # Processing Settings
    batch_size: int = Field(
        default=3, ge=1, le=10, description="Number of documents to process concurrently"
    )

    max_episode_size: int = Field(
        default=50000, ge=1000, description="Maximum episode content size in characters"
    )

    processing_timeout_seconds: int = Field(
        default=300, ge=60, description="Timeout for document processing operations"
    )

    # Quality Settings
    min_extraction_confidence: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for entity extraction",
    )

    enable_relationship_validation: bool = Field(
        default=True, description="Whether to validate extracted relationships"
    )

    @validator("neo4j_uri")
    def validate_neo4j_uri(cls, v):
        """Validate Neo4j URI format."""
        if not v.startswith(("bolt://", "neo4j://", "bolt+s://", "neo4j+s://")):
            raise ValueError(
                "Neo4j URI must start with bolt://, neo4j://, bolt+s://, or neo4j+s://"
            )
        return v

    @validator("neo4j_password")
    def validate_password_not_empty(cls, v):
        """Ensure password is not empty."""
        if not v or v.strip() == "":
            raise ValueError("Neo4j password cannot be empty")
        return v

    class Config:
        env_prefix = "GRAPHITI_"
        case_sensitive = False


class GraphitiClientManager:
    """
    Manager for Graphiti client lifecycle and configuration.

    Provides centralized client creation, configuration, and connection management
    for the political monitoring system.
    """

    def __init__(self, settings: Optional[GraphitiSettings] = None):
        self.settings = settings or GraphitiSettings()
        self._client: Optional[Graphiti] = None

    async def get_client(self) -> Graphiti:
        """
        Get or create Graphiti client with proper initialization.

        Returns:
            Configured and initialized Graphiti client
        """
        if self._client is None:
            await self._create_client()
        return self._client

    async def _create_client(self) -> None:
        """Create and initialize new Graphiti client."""
        try:
            # Create Graphiti client
            self._client = Graphiti(
                self.settings.neo4j_uri, self.settings.neo4j_user, self.settings.neo4j_password
            )

            # Initialize indices and constraints
            await self._client.build_indices_and_constraints()

        except Exception as e:
            raise ConfigurationError(f"Failed to create Graphiti client: {e}")

    async def close_client(self) -> None:
        """Close Graphiti client and cleanup resources."""
        if self._client:
            try:
                if hasattr(self._client, "close"):
                    await self._client.close()
            except Exception as e:
                # Log warning but don't raise exception during cleanup
                import logging

                logging.getLogger(__name__).warning(f"Error closing Graphiti client: {e}")
            finally:
                self._client = None

    async def test_connection(self) -> bool:
        """
        Test Graphiti connection and return success status.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            client = await self.get_client()

            # Try a simple operation to test the connection
            test_episode_name = f"connection_test_{int(datetime.now().timestamp())}"
            result = await client.add_episode(
                name=test_episode_name,
                episode_body="Connection test episode - can be safely deleted",
                source="text",
                source_description="Connection test",
                reference_time=datetime.now(UTC),
            )

            # Connection successful if we got a result
            return result is not None

        except Exception:
            return False

    def get_group_id(self, client_specific: Optional[str] = None) -> str:
        """
        Get appropriate group ID for episode creation.

        Args:
            client_specific: Optional client-specific group ID suffix

        Returns:
            Group ID string for episode creation
        """
        if client_specific:
            return f"client_{client_specific}"
        return self.settings.default_group_id

    async def __aenter__(self):
        """Async context manager entry."""
        return await self.get_client()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_client()


class GraphitiNamespaceManager:
    """
    Manages Graphiti namespaces for different types of political content.

    Provides structured namespace organization for:
    - Political documents by jurisdiction and type
    - Client-specific content and analysis
    - Temporal organization and cleanup
    """

    def __init__(self, base_group_id: str = "political_docs"):
        self.base_group_id = base_group_id

    def get_document_group_id(
        self,
        jurisdiction: Optional[str] = None,
        document_type: Optional[str] = None,
        client_id: Optional[str] = None,
    ) -> str:
        """
        Generate group ID for political documents.

        Args:
            jurisdiction: Geographic jurisdiction (eu, us, uk, etc.)
            document_type: Type of document (policy, regulation, enforcement, etc.)
            client_id: Optional client-specific identifier

        Returns:
            Structured group ID for namespace organization
        """
        parts = [self.base_group_id]

        if client_id:
            parts.append(f"client_{client_id}")

        if jurisdiction:
            parts.append(jurisdiction.lower())

        if document_type:
            parts.append(document_type.lower())

        return "_".join(parts)

    def get_analysis_group_id(self, client_id: str, analysis_type: str = "relevance") -> str:
        """
        Generate group ID for client analysis results.

        Args:
            client_id: Client identifier
            analysis_type: Type of analysis (relevance, impact, compliance, etc.)

        Returns:
            Group ID for analysis namespace
        """
        return f"analysis_{client_id}_{analysis_type}"

    def get_temporal_group_id(self, base_group: str, time_period: str) -> str:
        """
        Generate group ID with temporal component.

        Args:
            base_group: Base group identifier
            time_period: Time period (2024_q1, 2024_march, etc.)

        Returns:
            Temporal group ID
        """
        return f"{base_group}_{time_period}"


# Global configuration instance
_graphiti_settings: Optional[GraphitiSettings] = None
_client_manager: Optional[GraphitiClientManager] = None


def get_graphiti_settings() -> GraphitiSettings:
    """Get global Graphiti settings instance."""
    global _graphiti_settings
    if _graphiti_settings is None:
        _graphiti_settings = GraphitiSettings()
    return _graphiti_settings


def get_client_manager() -> GraphitiClientManager:
    """Get global client manager instance."""
    global _client_manager
    if _client_manager is None:
        _client_manager = GraphitiClientManager(get_graphiti_settings())
    return _client_manager


async def create_graphiti_client() -> Graphiti:
    """
    Convenience function to create and initialize Graphiti client.

    Returns:
        Initialized Graphiti client
    """
    manager = get_client_manager()
    return await manager.get_client()


def create_namespace_manager(base_group_id: Optional[str] = None) -> GraphitiNamespaceManager:
    """
    Convenience function to create namespace manager.

    Args:
        base_group_id: Optional base group ID override

    Returns:
        Configured namespace manager
    """
    settings = get_graphiti_settings()
    base_id = base_group_id or settings.default_group_id
    return GraphitiNamespaceManager(base_id)


# Import required for datetime usage in test_connection
from datetime import datetime
