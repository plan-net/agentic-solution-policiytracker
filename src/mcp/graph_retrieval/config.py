"""Configuration for Graph Context Retrieval MCP Server."""

import os
from dataclasses import dataclass


@dataclass
class Neo4jConfig:
    """Neo4j connection configuration."""
    uri: str
    user: str
    password: str
    database: str

    @classmethod
    def from_env(cls) -> "Neo4jConfig":
        """Load configuration from environment variables."""
        return cls(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            user=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password123"),
            database=os.getenv("NEO4J_DATABASE", "politicalmonitoring.v3"),
        )


@dataclass
class ServerConfig:
    """Server configuration."""
    host: str
    port: int
    log_level: str

    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Load configuration from environment variables."""
        return cls(
            host=os.getenv("MCP_HOST", "0.0.0.0"),
            port=int(os.getenv("MCP_PORT", "8003")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
