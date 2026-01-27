"""Configuration for BundestagPerson Manager."""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Find project root (where .env is located)
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
load_dotenv(_PROJECT_ROOT / ".env")


@dataclass
class ManagerConfig:
    """Configuration for BundestagPerson Manager."""

    # Data sources
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    neo4j_database: str
    dip_api_key: Optional[str]

    # CRUD Subagent
    crud_mcp_url: str
    crud_num_replicas: int

    # Sync behavior
    max_concurrent_operations: int
    batch_size: int
    check_interval_hours: int

    @classmethod
    def from_env(cls) -> "ManagerConfig":
        """Load configuration from environment variables."""
        return cls(
            # Neo4j
            neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
            neo4j_password=os.getenv("NEO4J_PASSWORD", "password123"),
            neo4j_database=os.getenv("NEO4J_DATABASE", "politicalmonitoring.v3"),
            # DIP API
            dip_api_key=os.getenv("BUNDESTAG_DIP_API_KEY"),
            # CRUD Subagent
            crud_mcp_url=os.getenv("NEO4J_CRUD_MCP_URL", "http://localhost:8002"),
            crud_num_replicas=int(os.getenv("CRUD_SUBAGENT_REPLICAS", "10")),
            # Sync behavior
            max_concurrent_operations=int(os.getenv("MANAGER_MAX_CONCURRENT_OPS", "100")),
            batch_size=int(os.getenv("MANAGER_BATCH_SIZE", "50")),
            check_interval_hours=int(os.getenv("MANAGER_CHECK_INTERVAL_HOURS", "6")),
        )
