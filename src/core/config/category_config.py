"""
Category Configuration Model.

Defines configuration for research categories, loaded from YAML files.
Each category specifies search queries, entity types, and LLM prompts.
"""

from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field


class SearchType(str, Enum):
    """
    Available Graphiti search types.

    Maps to the search strategies available in the chat tools:
    - COMPREHENSIVE: Cross-encoder reranking for high-quality results
    - ENTITY_FOCUSED: Node search with RRF for entity-centric queries
    - RELATIONSHIP_FOCUSED: Edge search for relationship discovery
    - EPISODE_FOCUSED: Episode mentions for document-based search
    - RRF_BALANCED: Balanced RRF search for mixed queries
    - COMMUNITY_FOCUSED: Community detection for clustering
    """

    COMPREHENSIVE = "comprehensive"
    ENTITY_FOCUSED = "entity_focused"
    RELATIONSHIP_FOCUSED = "relationship_focused"
    EPISODE_FOCUSED = "episode_focused"
    RRF_BALANCED = "rrf_balanced"
    COMMUNITY_FOCUSED = "community_focused"


class CategoryConfig(BaseModel):
    """
    Configuration for a research category.

    Each category represents a section of the report (e.g., legislative,
    personnel, compliance) and defines how to search for and process
    findings in that area.

    Loaded from YAML files like `legislative.yaml`.

    Example YAML:
        name: legislative
        display_name: "Legislative & Regulatory Updates"
        search_type: comprehensive
        search_queries:
          - "new regulation law enacted"
          - "DSA DMA compliance"
        entity_types:
          - REGULATION
          - LAW
        system_prompt: |
          You are a Legislative Research Agent...
        priority: 1
        enabled: true
        max_findings: 10

    Attributes:
        name: Internal category name (e.g., "legislative")
        display_name: Human-readable name for reports
        search_type: Graphiti search type to use
        search_queries: List of search queries for this category
        entity_types: Entity types relevant to this category
        system_prompt: System prompt for LLM finding extraction
        priority: Execution priority (1=highest)
        enabled: Whether this category is active
        max_findings: Maximum findings to return
        forward_looking_days: Days to look ahead for events category
    """

    name: str = Field(description="Internal category name (e.g., 'legislative')")
    display_name: str = Field(description="Human-readable display name")

    # Search configuration
    search_type: SearchType = Field(
        default=SearchType.COMPREHENSIVE,
        description="Graphiti search type to use",
    )
    search_queries: list[str] = Field(
        default_factory=list,
        description="List of search queries for this category",
    )
    entity_types: list[str] = Field(
        default_factory=list,
        description="Entity types relevant to this category",
    )

    # LLM configuration
    system_prompt: str = Field(
        description="System prompt for LLM finding extraction"
    )
    extraction_prompt_template: Optional[str] = Field(
        default=None,
        description="Optional custom extraction prompt template",
    )

    # Execution settings
    priority: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Execution priority (1=highest)",
    )
    enabled: bool = Field(
        default=True,
        description="Whether this category is active",
    )
    max_findings: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum findings to return",
    )

    # Category-specific settings
    forward_looking_days: int = Field(
        default=90,
        description="Days to look ahead for events/deadlines",
    )
    include_relationships: bool = Field(
        default=True,
        description="Whether to include relationship discovery",
    )

    # Temporal filtering strategy
    temporal_filter_strategy: str = Field(
        default="comprehensive",
        description="Temporal filter strategy: 'comprehensive', 'valid_only', 'created_only', or 'changes'",
    )

    # LLM extraction configuration
    skip_llm_extraction: bool = Field(
        default=True,
        description="If true, skip LLM-based filtering and use raw Graphiti results directly as findings",
    )

    # Additional metadata
    description: Optional[str] = Field(
        default=None,
        description="Description of what this category covers",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for filtering and organization",
    )

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "CategoryConfig":
        """
        Load category configuration from a YAML file.

        Args:
            yaml_path: Path to the YAML configuration file

        Returns:
            CategoryConfig instance

        Raises:
            FileNotFoundError: If the config file doesn't exist
            yaml.YAMLError: If the YAML is invalid
            ValidationError: If the config doesn't match the schema
        """
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def get_temporal_query(self, query: str, year: int) -> str:
        """
        Add temporal context to a search query.

        Args:
            query: Original search query
            year: Year to add as context

        Returns:
            Query with temporal context
        """
        return f"{query} {year}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = self.model_dump()
        data["search_type"] = self.search_type.value
        return data
