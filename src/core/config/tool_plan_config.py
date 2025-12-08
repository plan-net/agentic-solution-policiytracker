"""
Tool Plan Configuration Model.

Defines data-driven tool execution plans, loaded from YAML files.
Tool plans specify the sequence of tools to execute and success criteria.
"""

from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field


class ToolSpec(BaseModel):
    """
    Specification for a single tool in the execution sequence.

    Defines how to execute a tool including its name, parameters,
    and conditional execution logic.

    Attributes:
        tool_name: Name of the tool to execute
        search_type: Search type (or "from_category" to use category's type)
        limit: Maximum results to return
        parameters: Additional parameters to pass to the tool
        description: Human-readable description of this step
        conditional: Condition for execution (e.g., "has_entities")
        required: Whether this step is required for success
    """

    tool_name: str = Field(description="Name of the tool to execute")
    search_type: str = Field(
        default="from_category",
        description="Search type or 'from_category' to use category's configured type",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum results to return",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional parameters to pass to the tool",
    )
    description: str = Field(
        default="",
        description="Human-readable description of this step",
    )
    conditional: Optional[str] = Field(
        default=None,
        description="Condition for execution (e.g., 'has_entities', 'has_findings')",
    )
    required: bool = Field(
        default=False,
        description="Whether this step is required for success",
    )
    timeout_seconds: float = Field(
        default=30.0,
        description="Timeout for this tool execution",
    )

    def should_execute(self, context: dict[str, Any]) -> bool:
        """
        Check if this tool should execute based on conditions.

        Args:
            context: Current execution context with state

        Returns:
            True if the tool should execute
        """
        if self.conditional is None:
            return True

        if self.conditional == "has_entities":
            # Check if any entities were found in previous steps
            entities = context.get("entities_found", [])
            return len(entities) > 0

        if self.conditional == "has_findings":
            # Check if any findings were extracted
            findings = context.get("findings", [])
            return len(findings) > 0

        if self.conditional == "no_findings":
            # Execute only if no findings yet (fallback)
            findings = context.get("findings", [])
            return len(findings) == 0

        # Unknown condition - default to execute
        return True


class SuccessCriteria(BaseModel):
    """
    Success criteria for tool plan execution.

    Defines what constitutes success at different levels.

    Attributes:
        primary: Primary success criterion (ideal outcome)
        secondary: Secondary success criterion (acceptable outcome)
        minimum: Minimum criterion (bare minimum for non-failure)
    """

    primary: str = Field(
        default="At least 5 relevant findings per category",
        description="Primary success criterion",
    )
    secondary: str = Field(
        default="Source citations for all findings",
        description="Secondary success criterion",
    )
    minimum: str = Field(
        default="At least 1 finding",
        description="Minimum criterion for non-failure",
    )


class ToolPlanConfig(BaseModel):
    """
    Data-driven tool execution plan.

    Tool plans define the sequence of tools to execute for research,
    along with success criteria and fallback strategies. They are
    editable via YAML without code changes.

    Loaded from YAML files like `comprehensive.yaml`.

    Example YAML:
        name: comprehensive
        description: "Full coverage research strategy"
        tool_sequence:
          - tool_name: graphiti_search
            search_type: from_category
            limit: 20
          - tool_name: graphiti_search
            search_type: entity_focused
            limit: 10
            conditional: has_entities
        parallel_execution: false
        success_criteria:
          primary: "At least 5 relevant findings"
          minimum: "At least 1 finding"
        fallback_plan: focused

    Attributes:
        name: Plan name (e.g., "comprehensive", "focused")
        description: Description of this strategy
        tool_sequence: Ordered list of tool specifications
        parallel_execution: Whether tools can run in parallel
        success_criteria: Criteria for evaluating success
        fallback_plan: Name of fallback plan if this one fails
        estimated_time_seconds: Estimated execution time
        max_retries: Maximum retries on failure
    """

    name: str = Field(description="Plan name (e.g., 'comprehensive')")
    description: str = Field(
        default="",
        description="Description of this research strategy",
    )

    # Tool sequence
    tool_sequence: list[ToolSpec] = Field(
        description="Ordered list of tool specifications"
    )

    # Execution settings
    parallel_execution: bool = Field(
        default=False,
        description="Whether tools can run in parallel",
    )
    max_concurrent: int = Field(
        default=3,
        description="Maximum concurrent executions if parallel",
    )

    # Success criteria
    success_criteria: SuccessCriteria = Field(
        default_factory=SuccessCriteria,
        description="Criteria for evaluating success",
    )

    # Fallback and retry
    fallback_plan: Optional[str] = Field(
        default=None,
        description="Name of fallback plan if this one fails",
    )
    max_retries: int = Field(
        default=1,
        description="Maximum retries on failure",
    )

    # Timing
    estimated_time_seconds: float = Field(
        default=30.0,
        description="Estimated execution time",
    )
    total_timeout_seconds: float = Field(
        default=120.0,
        description="Total timeout for the entire plan",
    )

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "ToolPlanConfig":
        """
        Load tool plan configuration from a YAML file.

        Args:
            yaml_path: Path to the YAML configuration file

        Returns:
            ToolPlanConfig instance

        Raises:
            FileNotFoundError: If the config file doesn't exist
            yaml.YAMLError: If the YAML is invalid
            ValidationError: If the config doesn't match the schema
        """
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        # Convert tool_sequence dicts to ToolSpec objects
        if "tool_sequence" in data:
            data["tool_sequence"] = [
                ToolSpec(**spec) if isinstance(spec, dict) else spec
                for spec in data["tool_sequence"]
            ]

        # Convert success_criteria dict to SuccessCriteria object
        if "success_criteria" in data and isinstance(data["success_criteria"], dict):
            data["success_criteria"] = SuccessCriteria(**data["success_criteria"])

        return cls(**data)

    def get_required_tools(self) -> list[ToolSpec]:
        """Get list of required tool specifications."""
        return [spec for spec in self.tool_sequence if spec.required]

    def get_optional_tools(self) -> list[ToolSpec]:
        """Get list of optional tool specifications."""
        return [spec for spec in self.tool_sequence if not spec.required]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return self.model_dump()
