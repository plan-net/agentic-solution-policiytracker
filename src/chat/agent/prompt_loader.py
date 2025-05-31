"""Enhanced prompt loader for multi-agent system with template support."""

import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MultiAgentPromptLoader:
    """
    Enhanced prompt loader for multi-agent system with support for:
    - Handlebars-style template variables ({{variable}})
    - Conditional blocks ({{#if condition}})
    - Agent-specific prompt loading
    - Memory context integration
    """

    def __init__(self) -> None:
        self.agents_prompt_dir = Path(__file__).parent.parent.parent / "prompts" / "chat" / "agents"
        self.cache: dict[str, str] = {}

    async def get_agent_prompt(self, agent_name: str, context: dict[str, Any]) -> str:
        """
        Get agent-specific prompt with full context substitution.

        Args:
            agent_name: Agent name (query_understanding, tool_planning, etc.)
            context: Full context including memory, previous results, user preferences

        Returns:
            Rendered prompt text with all variables substituted
        """
        # Load the raw prompt template
        raw_prompt = await self._load_agent_prompt_template(agent_name)

        # Render the template with context
        rendered_prompt = self._render_template(raw_prompt, context)

        return rendered_prompt

    async def _load_agent_prompt_template(self, agent_name: str) -> str:
        """Load raw prompt template from file system."""
        cache_key = f"agent_{agent_name}"

        if cache_key in self.cache:
            return self.cache[cache_key]

        prompt_file = self.agents_prompt_dir / f"{agent_name}.md"

        if not prompt_file.exists():
            raise FileNotFoundError(f"Agent prompt not found: {prompt_file}")

        # Read and parse the prompt file
        with open(prompt_file, encoding="utf-8") as f:
            content = f.read()

        # Extract content after frontmatter
        prompt_content = self._parse_prompt_file(content)

        # Cache the raw template
        self.cache[cache_key] = prompt_content

        logger.debug(f"Loaded agent prompt template: {agent_name}")
        return prompt_content

    def _parse_prompt_file(self, content: str) -> str:
        """Parse prompt file and extract content after frontmatter."""
        parts = content.split("---", 2)

        if len(parts) >= 3:
            # Has frontmatter - return content after second ---
            return parts[2].strip()
        else:
            # No frontmatter - return entire content
            return content.strip()

    def _render_template(self, template: str, context: dict[str, Any]) -> str:
        """
        Render template with Handlebars-style syntax support.

        Supports:
        - {{variable}} - Simple variable substitution
        - {{#if condition}}...{{/if}} - Conditional blocks
        - {{#each array}}...{{/each}} - Array iteration (basic)
        """
        result = template

        # Process conditional blocks first
        result = self._process_conditionals(result, context)

        # Process simple variable substitutions
        result = self._process_variables(result, context)

        # Clean up any remaining template syntax
        result = self._cleanup_template_syntax(result)

        return result

    def _process_conditionals(self, template: str, context: dict[str, Any]) -> str:
        """Process {{#if condition}}...{{/if}} blocks."""
        # Find all conditional blocks
        conditional_pattern = r"\{\{#if\s+([^}]+)\}\}(.*?)\{\{/if\}\}"

        def replace_conditional(match: re.Match[str]) -> str:
            condition = match.group(1).strip()
            content = match.group(2)

            # Evaluate condition
            if self._evaluate_condition(condition, context):
                return content
            else:
                return ""

        return re.sub(conditional_pattern, replace_conditional, template, flags=re.DOTALL)

    def _evaluate_condition(self, condition: str, context: dict[str, Any]) -> bool:
        """Evaluate a condition string against context."""
        # Simple condition evaluation - can be enhanced
        try:
            # Handle simple existence checks
            if condition in context:
                value = context[condition]
                # Check if value is truthy
                if isinstance(value, list | dict):
                    return len(value) > 0
                elif isinstance(value, str):
                    return value.strip() != ""
                else:
                    return bool(value)

            # Handle nested property access (e.g., "user_preferences.detail_level")
            if "." in condition:
                parts = condition.split(".")
                value = context
                for part in parts:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        return False

                # Check if final value is truthy
                if isinstance(value, list | dict):
                    return len(value) > 0
                elif isinstance(value, str):
                    return value.strip() != ""
                else:
                    return bool(value)

            return False

        except Exception as e:
            logger.warning(f"Error evaluating condition '{condition}': {e}")
            return False

    def _process_variables(self, template: str, context: dict[str, Any]) -> str:
        """Process {{variable}} substitutions."""
        # Pattern to match {{variable}} or {{object.property}}
        variable_pattern = r"\{\{([^#/][^}]*)\}\}"

        def replace_variable(match: re.Match[str]) -> str:
            variable_path = match.group(1).strip()

            try:
                value = self._get_nested_value(variable_path, context)
                if value == "":  # Explicitly check for empty string from missing nested values
                    return f"[{variable_path}]"  # Placeholder for missing values
                return self._format_value(value)
            except Exception as e:
                logger.warning(f"Error substituting variable '{variable_path}': {e}")
                return f"[{variable_path}]"  # Placeholder for missing values

        return re.sub(variable_pattern, replace_variable, template)

    def _get_nested_value(self, path: str, context: dict[str, Any]) -> Any:
        """Get value from nested context using dot notation."""
        if "." not in path:
            return context.get(path, "")

        parts = path.split(".")
        value = context

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part, "")
            else:
                return ""

        return value

    def _format_value(self, value: Any) -> str:
        """Format a value for template substitution."""
        if value is None:
            return ""
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, list | tuple):
            if len(value) == 0:
                return ""
            # Format lists in a readable way
            return ", ".join(str(item) for item in value)
        elif isinstance(value, dict):
            # For complex objects, return JSON representation
            try:
                return json.dumps(value, indent=2)
            except Exception:
                return str(value)
        else:
            return str(value)

    def _cleanup_template_syntax(self, template: str) -> str:
        """Clean up any remaining template syntax."""
        # Remove any leftover handlebars syntax
        template = re.sub(r"\{\{[^}]*\}\}", "", template)

        # Clean up multiple newlines
        template = re.sub(r"\n\s*\n\s*\n", "\n\n", template)

        return template.strip()

    def get_available_agents(self) -> list[str]:
        """Get list of available agent prompt templates."""
        if not self.agents_prompt_dir.exists():
            return []

        return [f.stem for f in self.agents_prompt_dir.glob("*.md") if f.is_file()]

    def clear_cache(self) -> None:
        """Clear the prompt template cache."""
        self.cache.clear()
        logger.info("Multi-agent prompt cache cleared")


# Helper functions for building context


def build_agent_context(
    user_query: str,
    session_state: dict[str, Any],
    memory_data: dict[str, Any] | None = None,
    previous_results: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build comprehensive context for agent prompt rendering.

    Args:
        user_query: Original user query
        session_state: Current multi-agent state
        memory_data: User preferences, patterns, etc.
        previous_results: Results from previous agents

    Returns:
        Complete context dictionary for template rendering
    """
    context = {
        "user_query": user_query,
        "original_query": session_state.get("original_query", user_query),
    }

    # Add session state data
    if "query_analysis" in session_state:
        context["query_analysis"] = session_state["query_analysis"]

    if "tool_plan" in session_state:
        context["tool_plan"] = session_state["tool_plan"]

    if "tool_results" in session_state:
        context["tool_results"] = session_state["tool_results"]

    if "executed_tools" in session_state:
        context["executed_tools"] = session_state["executed_tools"]

    if "execution_metadata" in session_state:
        context["execution_metadata"] = session_state["execution_metadata"]

    # Add memory data if available
    if memory_data:
        context.update(
            {
                "user_preferences": memory_data.get("user_preferences", {}),
                "conversation_history": memory_data.get("conversation_history", []),
                "learned_patterns": memory_data.get("learned_patterns", {}),
                "tool_performance_history": memory_data.get("tool_performance_history", {}),
            }
        )

    # Add previous agent results if available
    if previous_results:
        context.update(previous_results)

    return context


# Global instance
multi_agent_prompt_loader = MultiAgentPromptLoader()
