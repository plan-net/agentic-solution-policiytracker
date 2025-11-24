"""Configuration for CRUD Subagent."""
import os
from dataclasses import dataclass


@dataclass
class CRUDSubagentConfig:
    """Configuration for CRUD Subagent."""

    mcp_url: str
    num_replicas: int
    timeout_seconds: float
    max_retries: int
    retry_delay_seconds: float

    @classmethod
    def from_env(cls) -> "CRUDSubagentConfig":
        """Load configuration from environment variables."""
        return cls(
            mcp_url=os.getenv("NEO4J_CRUD_MCP_URL", "http://localhost:8002"),
            num_replicas=int(os.getenv("CRUD_SUBAGENT_REPLICAS", "10")),
            timeout_seconds=float(os.getenv("CRUD_SUBAGENT_TIMEOUT", "30.0")),
            max_retries=int(os.getenv("CRUD_SUBAGENT_MAX_RETRIES", "3")),
            retry_delay_seconds=float(os.getenv("CRUD_SUBAGENT_RETRY_DELAY", "1.0")),
        )
