from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    # Kodosumi Settings
    KODOSUMI_SERVICE_NAME: str = Field(default="political-monitoring")
    KODOSUMI_SERVICE_PORT: int = Field(default=8000)

    # Ray Settings
    RAY_ADDRESS: str = Field(default="auto")
    RAY_NUM_CPUS: int = Field(default=8)
    RAY_TASK_MAX_RETRIES: int = Field(default=3)

    # Path Settings
    DEFAULT_INPUT_FOLDER: str = Field(default="./data/input")
    DEFAULT_OUTPUT_FOLDER: str = Field(default="./data/output")
    DEFAULT_CONTEXT_FOLDER: str = Field(default="./data/context")

    # Processing Limits
    MAX_BATCH_SIZE: int = Field(default=1000)
    PROCESSING_TIMEOUT_SECONDS: int = Field(default=600)
    MAX_DOCUMENT_SIZE_MB: int = Field(default=50)

    # Scoring Settings
    CONFIDENCE_THRESHOLD: float = Field(default=0.7)
    MIN_RELEVANCE_SCORE: float = Field(default=0.0)
    MAX_RELEVANCE_SCORE: float = Field(default=100.0)

    # Dimension Weights
    DIRECT_IMPACT_WEIGHT: float = Field(default=0.40)
    INDUSTRY_RELEVANCE_WEIGHT: float = Field(default=0.25)
    GEOGRAPHIC_RELEVANCE_WEIGHT: float = Field(default=0.15)
    TEMPORAL_URGENCY_WEIGHT: float = Field(default=0.10)
    STRATEGIC_ALIGNMENT_WEIGHT: float = Field(default=0.10)

    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="json")
    ENABLE_PERFORMANCE_LOGGING: bool = Field(default=True)

    # LLM Configuration
    LLM_ENABLED: bool = Field(default=False, description="Enable LLM integration")
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    OPENAI_MODEL: str = Field(default="gpt-4", description="OpenAI model to use")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Anthropic API key")
    ANTHROPIC_MODEL: str = Field(
        default="claude-3-haiku-20240307", description="Anthropic model to use"
    )
    LLM_MAX_CONCURRENT: int = Field(default=3, description="Max concurrent LLM requests")
    LLM_TIMEOUT_SECONDS: int = Field(default=30, description="LLM request timeout")
    LLM_TEMPERATURE: float = Field(default=0.3, description="LLM temperature for creativity")
    LLM_MAX_TOKENS: int = Field(default=2000, description="Maximum tokens for LLM responses")
    LLM_FALLBACK_ENABLED: bool = Field(
        default=True, description="Enable fallback to rule-based scoring"
    )

    # Langfuse Observability
    LANGFUSE_SECRET_KEY: Optional[str] = Field(default=None, description="Langfuse secret key")
    LANGFUSE_PUBLIC_KEY: Optional[str] = Field(default=None, description="Langfuse public key")
    LANGFUSE_HOST: str = Field(
        default="https://cloud.langfuse.com", description="Langfuse host URL"
    )

    # Neo4j GraphRAG Configuration
    NEO4J_URI: str = Field(default="bolt://localhost:7687", description="Neo4j database URI")
    NEO4J_USERNAME: str = Field(default="neo4j", description="Neo4j username")
    NEO4J_PASSWORD: str = Field(default="password", description="Neo4j password")
    NEO4J_DATABASE: str = Field(default="neo4j", description="Neo4j database name")

    # Azure Storage Configuration
    USE_AZURE_STORAGE: bool = Field(
        default=False, description="Use Azure Blob Storage instead of local filesystem"
    )
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = Field(
        default=None, description="Azure Storage connection string"
    )
    AZURE_STORAGE_ACCOUNT_NAME: Optional[str] = Field(
        default=None, description="Azure Storage account name"
    )
    AZURE_STORAGE_CONTAINER_NAME: str = Field(
        default="politicalmonitoring", description="Default Azure container name"
    )

    # Azure Storage Paths (automatically managed by import script)
    AZURE_JOB_ID: Optional[str] = Field(default=None, description="Current Azure job ID")
    AZURE_INPUT_PATH: str = Field(default="input", description="Azure input blob path")
    AZURE_CONTEXT_PATH: str = Field(
        default="context/client.yaml", description="Azure context file path"
    )
    AZURE_OUTPUT_PATH: str = Field(default="output", description="Azure output blob path")

    @property
    def dimension_weights(self) -> dict[str, float]:
        return {
            "direct_impact": self.DIRECT_IMPACT_WEIGHT,
            "industry_relevance": self.INDUSTRY_RELEVANCE_WEIGHT,
            "geographic_relevance": self.GEOGRAPHIC_RELEVANCE_WEIGHT,
            "temporal_urgency": self.TEMPORAL_URGENCY_WEIGHT,
            "strategic_alignment": self.STRATEGIC_ALIGNMENT_WEIGHT,
        }

    @property
    def input_path(self) -> str:
        """Get the appropriate input path based on storage mode."""
        if self.USE_AZURE_STORAGE:
            return self.AZURE_INPUT_PATH
        return self.DEFAULT_INPUT_FOLDER

    @property
    def context_path(self) -> str:
        """Get the appropriate context path based on storage mode."""
        if self.USE_AZURE_STORAGE:
            return self.AZURE_CONTEXT_PATH
        return f"{self.DEFAULT_CONTEXT_FOLDER}/client.yaml"

    @property
    def output_path(self) -> str:
        """Get the appropriate output path based on storage mode."""
        if self.USE_AZURE_STORAGE:
            return self.AZURE_OUTPUT_PATH
        return self.DEFAULT_OUTPUT_FOLDER


class GraphRAGSettings(BaseSettings):
    """Settings for GraphRAG integration (v0.2.0)."""

    # Feature flag
    ENABLE_GRAPHRAG: bool = Field(default=False, description="Enable GraphRAG features")

    # Neo4j Configuration
    NEO4J_URI: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI")
    NEO4J_USERNAME: str = Field(default="neo4j", description="Neo4j username")
    NEO4J_PASSWORD: str = Field(default="password123", description="Neo4j password")
    NEO4J_DATABASE: str = Field(default="politicalmonitoring", description="Neo4j database name")

    # Embedding Configuration
    GRAPHRAG_EMBEDDING_PROVIDER: str = Field(
        default="openai", description="Embedding provider: openai or local"
    )
    GRAPHRAG_EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-small", description="Embedding model name"
    )
    GRAPHRAG_EMBEDDING_DIMS: int = Field(default=1536, description="Embedding dimensions")

    # Chunking Configuration
    GRAPHRAG_CHUNK_SIZE: int = Field(default=1000, description="Document chunk size")
    GRAPHRAG_CHUNK_OVERLAP: int = Field(default=200, description="Chunk overlap size")

    # Ray Data Configuration
    RAY_DATA_NUM_WORKERS: int = Field(default=4, description="Number of Ray workers")
    RAY_DATA_BATCH_SIZE: int = Field(default=100, description="Batch size for processing")

    # Retrieval Configuration
    GRAPHRAG_VECTOR_SEARCH_LIMIT: int = Field(
        default=10, description="Max results for vector search"
    )
    GRAPHRAG_TRAVERSAL_DEPTH: int = Field(default=3, description="Max graph traversal depth")
    GRAPHRAG_HYBRID_WEIGHT: float = Field(
        default=0.7, description="Weight for vector vs graph search"
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


# Global settings instances
settings = Settings()
graphrag_settings = GraphRAGSettings()
