"""Configuration for Bundestag Aktivitaet Manager."""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ManagerConfig:
    """Configuration for BundestagAktivitaetManager."""

    # Neo4j Connection
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    neo4j_database: str

    # Bundestag DIP API
    dip_api_key: Optional[str] = None
    dip_base_url: str = "https://search.dip.bundestag.de/api/v1"

    # CRUD MCP Server
    crud_mcp_url: str = "http://localhost:8002"
    crud_num_replicas: int = 10
    crud_timeout: float = 30.0

    # Manager Settings
    max_concurrent_operations: int = 100
    batch_size: int = 50

    @classmethod
    def from_env(cls) -> "ManagerConfig":
        """Load configuration from environment variables.

        Returns:
            ManagerConfig instance
        """
        return cls(
            # Neo4j
            neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
            neo4j_password=os.getenv("NEO4J_PASSWORD", "password123"),
            neo4j_database=os.getenv("NEO4J_DATABASE", "politicamonitoring.v2"),
            # DIP API
            dip_api_key=os.getenv("BUNDESTAG_DIP_API_KEY"),
            dip_base_url=os.getenv(
                "BUNDESTAG_DIP_BASE_URL",
                "https://search.dip.bundestag.de/api/v1",
            ),
            # CRUD MCP
            crud_mcp_url=os.getenv("NEO4J_CRUD_MCP_URL", "http://localhost:8002"),
            crud_num_replicas=int(os.getenv("CRUD_SUBAGENT_REPLICAS", "10")),
            crud_timeout=float(os.getenv("CRUD_SUBAGENT_TIMEOUT", "30.0")),
            # Manager
            max_concurrent_operations=int(os.getenv("MANAGER_MAX_CONCURRENT_OPS", "100")),
            batch_size=int(os.getenv("MANAGER_BATCH_SIZE", "50")),
        )
