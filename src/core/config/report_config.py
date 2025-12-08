"""
Report Configuration Model.

Defines the master configuration for a report type, loaded from YAML files.
Supports weekly, monthly, quarterly, and topic-specific reports.
"""

from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field


class ReportConfig(BaseModel):
    """
    Master configuration for a report type.

    This configuration drives the entire report generation workflow,
    specifying categories, execution strategy, output format, and
    observability settings.

    Loaded from YAML files like `weekly_digest.yaml`.

    Example YAML:
        report_type: weekly
        version: "2.0.0"
        categories:
          - legislative.yaml
          - personnel.yaml
        category_execution: sequential
        output_format: markdown
        template_name: weekly_digest.md.j2
        default_tool_plan: comprehensive

    Attributes:
        report_type: Type of report (weekly, monthly, quarterly, topic_specific)
        version: Version string for the configuration
        input_type: How input is provided (week_selector, date_range, free_form)
        date_resolution_strategy: How to resolve dates (iso_week, calendar_month)
        categories: List of category config filenames to load
        category_execution: Execution strategy (sequential, parallel)
        output_format: Output format (markdown, pdf, email)
        template_name: Jinja2 template filename for rendering
        default_tool_plan: Default tool plan to use
        include_graph_visualization: Whether to include graph visualization link
        trace_name: Name for LangWatch trace
        max_findings_per_category: Maximum findings to include per category
        max_total_findings: Maximum total findings across all categories
        search_result_limit: Default limit for search results
        llm_timeout_seconds: Timeout for LLM calls
    """

    report_type: str = Field(
        description="Type of report (weekly, monthly, quarterly, topic_specific)"
    )
    version: str = Field(default="1.0.0", description="Configuration version")

    # Input handling
    input_type: str = Field(
        default="week_selector",
        description="Input type: week_selector, date_range, free_form",
    )
    date_resolution_strategy: str = Field(
        default="iso_week",
        description="Date resolution: iso_week, calendar_month, custom_range",
    )

    # Categories
    categories: list[str] = Field(
        description="List of category config filenames to load"
    )
    category_execution: str = Field(
        default="sequential",
        description="Execution strategy: sequential, parallel",
    )

    # Output
    output_format: str = Field(
        default="markdown",
        description="Output format: markdown, pdf, email",
    )
    template_name: str = Field(
        default="weekly_digest.md.j2",
        description="Jinja2 template filename",
    )

    # Tool planning
    default_tool_plan: str = Field(
        default="comprehensive",
        description="Default tool plan to use",
    )
    fallback_tool_plan: Optional[str] = Field(
        default="focused",
        description="Fallback tool plan if default fails",
    )

    # Visualization
    include_graph_visualization: bool = Field(
        default=True,
        description="Whether to include graph visualization link",
    )
    graph_visualization_url: str = Field(
        default="http://localhost:5173",
        description="Base URL for graph visualization service",
    )

    # Observability
    trace_name: str = Field(
        default="report_workflow",
        description="Name for LangWatch trace",
    )
    enable_langwatch: bool = Field(
        default=True,
        description="Whether to enable LangWatch tracing",
    )

    # Limits
    max_findings_per_category: int = Field(
        default=10,
        description="Maximum findings per category",
    )
    max_total_findings: int = Field(
        default=50,
        description="Maximum total findings",
    )
    search_result_limit: int = Field(
        default=20,
        description="Default search result limit",
    )
    llm_timeout_seconds: float = Field(
        default=30.0,
        description="Timeout for LLM calls",
    )

    # Additional settings
    extra_settings: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional custom settings",
    )

    @classmethod
    def load(cls, config_path: Path) -> "ReportConfig":
        """
        Load report configuration from a YAML file.

        Args:
            config_path: Path to the YAML configuration file

        Returns:
            ReportConfig instance

        Raises:
            FileNotFoundError: If the config file doesn't exist
            yaml.YAMLError: If the YAML is invalid
            ValidationError: If the config doesn't match the schema
        """
        with open(config_path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def get_category_config_path(self, category_file: str, config_dir: Path) -> Path:
        """
        Get the full path to a category config file.

        Args:
            category_file: Category config filename
            config_dir: Base directory containing config files

        Returns:
            Full path to the category config file
        """
        return config_dir / "categories" / category_file

    def get_tool_plan_path(self, plan_name: str, config_dir: Path) -> Path:
        """
        Get the full path to a tool plan config file.

        Args:
            plan_name: Tool plan name (without .yaml extension)
            config_dir: Base directory containing config files

        Returns:
            Full path to the tool plan config file
        """
        return config_dir / "tool_plans" / f"{plan_name}.yaml"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return self.model_dump()
