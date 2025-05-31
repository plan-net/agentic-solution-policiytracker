"""Unit tests for multi-agent prompt system."""

import tempfile
from pathlib import Path

import pytest

from src.chat.agent.prompt_loader import (
    MultiAgentPromptLoader,
    build_agent_context,
    multi_agent_prompt_loader,
)


class TestMultiAgentPromptLoader:
    """Test MultiAgentPromptLoader functionality."""

    @pytest.fixture
    def temp_prompt_dir(self):
        """Create temporary directory with test prompt files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            prompt_dir = Path(temp_dir) / "prompts" / "chat" / "agents"
            prompt_dir.mkdir(parents=True)

            # Create test prompt files
            self._create_test_prompts(prompt_dir)

            yield prompt_dir

    def _create_test_prompts(self, prompt_dir: Path):
        """Create test prompt files."""
        # Simple prompt without conditionals
        simple_prompt = """---
name: test_simple
version: 1
---

# Simple Agent

You are a test agent analyzing: {{user_query}}

Your task is to process this query with confidence: {{confidence}}
"""

        # Prompt with conditionals
        conditional_prompt = """---
name: test_conditional
version: 1
---

# Conditional Agent

{{#if user_preferences}}
**User Preferences**: {{user_preferences.detail_level}}
{{/if}}

Query: {{user_query}}

{{#if previous_results}}
Previous results available: {{previous_results.count}}
{{/if}}

{{#if memory_data}}
Memory context: {{memory_data}}
{{/if}}
"""

        # Complex prompt with nested variables
        complex_prompt = """---
name: test_complex
version: 1
---

# Complex Agent

## Query Analysis
Query: {{user_query}}
Intent: {{analysis.intent}}
Entities: {{analysis.entities}}

## Context
{{#if user_preferences}}
Detail Level: {{user_preferences.detail_level}}
Format: {{user_preferences.format}}
{{/if}}

## Previous Results
{{#if tool_results}}
Found {{tool_results.length}} results:
{{tool_results}}
{{/if}}
"""

        # Write test prompt files
        (prompt_dir / "simple.md").write_text(simple_prompt)
        (prompt_dir / "conditional.md").write_text(conditional_prompt)
        (prompt_dir / "complex.md").write_text(complex_prompt)

    @pytest.fixture
    def loader_with_temp_dir(self, temp_prompt_dir):
        """Create loader with temporary prompt directory."""
        loader = MultiAgentPromptLoader()
        loader.agents_prompt_dir = temp_prompt_dir
        return loader

    @pytest.mark.asyncio
    async def test_load_simple_prompt(self, loader_with_temp_dir):
        """Test loading a simple prompt without variables."""
        context = {"user_query": "What is the EU AI Act?", "confidence": 0.9}

        rendered = await loader_with_temp_dir.get_agent_prompt("simple", context)

        assert "You are a test agent analyzing: What is the EU AI Act?" in rendered
        assert "with confidence: 0.9" in rendered
        assert "{{" not in rendered  # No unprocessed template variables

    @pytest.mark.asyncio
    async def test_conditional_blocks_true(self, loader_with_temp_dir):
        """Test conditional blocks when condition is true."""
        context = {
            "user_query": "Test query",
            "user_preferences": {"detail_level": "high", "format": "detailed"},
            "previous_results": {"count": 5},
        }

        rendered = await loader_with_temp_dir.get_agent_prompt("conditional", context)

        assert "**User Preferences**: high" in rendered
        assert "Previous results available: 5" in rendered

    @pytest.mark.asyncio
    async def test_conditional_blocks_false(self, loader_with_temp_dir):
        """Test conditional blocks when condition is false."""
        context = {
            "user_query": "Test query"
            # No user_preferences or previous_results
        }

        rendered = await loader_with_temp_dir.get_agent_prompt("conditional", context)

        assert "**User Preferences**" not in rendered
        assert "Previous results available" not in rendered
        assert "Query: Test query" in rendered

    @pytest.mark.asyncio
    async def test_nested_variable_access(self, loader_with_temp_dir):
        """Test nested variable access with dot notation."""
        context = {
            "user_query": "Complex query",
            "analysis": {
                "intent": "information_seeking",
                "entities": ["EU", "AI Act", "regulation"],
            },
            "user_preferences": {"detail_level": "medium", "format": "structured"},
        }

        rendered = await loader_with_temp_dir.get_agent_prompt("complex", context)

        assert "Intent: information_seeking" in rendered
        assert "Entities: EU, AI Act, regulation" in rendered
        assert "Detail Level: medium" in rendered
        assert "Format: structured" in rendered

    @pytest.mark.asyncio
    async def test_missing_variable_handling(self, loader_with_temp_dir):
        """Test handling of missing variables."""
        context = {
            "user_query": "Test query"
            # Missing other expected variables
        }

        rendered = await loader_with_temp_dir.get_agent_prompt("complex", context)

        # Should handle missing variables gracefully
        assert "Query: Test query" in rendered
        assert "[analysis.intent]" in rendered  # Placeholder for missing variable
        assert "{{" not in rendered  # No raw template syntax

    @pytest.mark.asyncio
    async def test_array_formatting(self, loader_with_temp_dir):
        """Test array variable formatting."""
        context = {
            "user_query": "Test query",
            "analysis": {"entities": ["entity1", "entity2", "entity3"]},
        }

        rendered = await loader_with_temp_dir.get_agent_prompt("complex", context)

        assert "Entities: entity1, entity2, entity3" in rendered

    @pytest.mark.asyncio
    async def test_json_object_formatting(self, loader_with_temp_dir):
        """Test JSON object formatting."""
        context = {
            "user_query": "Test query",
            "tool_results": {
                "results": [
                    {"tool": "search", "success": True},
                    {"tool": "lookup", "success": False},
                ],
                "length": 2,
            },
        }

        rendered = await loader_with_temp_dir.get_agent_prompt("complex", context)

        # Should format complex objects as JSON
        assert "Found 2 results:" in rendered
        assert '"tool": "search"' in rendered

    def test_get_available_agents(self, loader_with_temp_dir):
        """Test getting list of available agent prompts."""
        agents = loader_with_temp_dir.get_available_agents()

        assert "simple" in agents
        assert "conditional" in agents
        assert "complex" in agents
        assert len(agents) == 3

    @pytest.mark.asyncio
    async def test_prompt_caching(self, loader_with_temp_dir):
        """Test that prompts are cached after first load."""
        context = {"user_query": "Test query", "confidence": 0.8}

        # First load
        rendered1 = await loader_with_temp_dir.get_agent_prompt("simple", context)

        # Should be cached now
        assert "agent_simple" in loader_with_temp_dir.cache

        # Second load should use cache
        rendered2 = await loader_with_temp_dir.get_agent_prompt("simple", context)

        assert rendered1 == rendered2

    def test_clear_cache(self, loader_with_temp_dir):
        """Test cache clearing."""
        loader_with_temp_dir.cache["test"] = "value"

        loader_with_temp_dir.clear_cache()

        assert len(loader_with_temp_dir.cache) == 0

    @pytest.mark.asyncio
    async def test_file_not_found_error(self, loader_with_temp_dir):
        """Test error handling for missing prompt files."""
        context = {"user_query": "Test query"}

        with pytest.raises(FileNotFoundError):
            await loader_with_temp_dir.get_agent_prompt("nonexistent", context)


class TestBuildAgentContext:
    """Test build_agent_context helper function."""

    def test_basic_context_building(self):
        """Test basic context building with minimal data."""
        context = build_agent_context(
            user_query="What is GDPR?", session_state={"original_query": "What is GDPR?"}
        )

        assert context["user_query"] == "What is GDPR?"
        assert context["original_query"] == "What is GDPR?"

    def test_context_with_session_state(self):
        """Test context building with rich session state."""
        session_state = {
            "original_query": "What is GDPR?",
            "query_analysis": {"intent": "information_seeking", "complexity": "medium"},
            "tool_plan": {"strategy": "comprehensive", "tools": ["search", "lookup"]},
            "tool_results": [{"tool": "search", "success": True}],
            "executed_tools": ["search"],
            "execution_metadata": {"total_time": 15.5},
        }

        context = build_agent_context(user_query="What is GDPR?", session_state=session_state)

        assert context["query_analysis"]["intent"] == "information_seeking"
        assert context["tool_plan"]["strategy"] == "comprehensive"
        assert len(context["tool_results"]) == 1
        assert context["executed_tools"] == ["search"]
        assert context["execution_metadata"]["total_time"] == 15.5

    def test_context_with_memory_data(self):
        """Test context building with memory data."""
        memory_data = {
            "user_preferences": {"detail_level": "high", "citation_style": "academic"},
            "conversation_history": ["Previous query about AI"],
            "learned_patterns": {"common_intent": "compliance_research"},
            "tool_performance_history": {"search": {"success_rate": 0.95}},
        }

        context = build_agent_context(
            user_query="What is GDPR?", session_state={}, memory_data=memory_data
        )

        assert context["user_preferences"]["detail_level"] == "high"
        assert context["conversation_history"] == ["Previous query about AI"]
        assert context["learned_patterns"]["common_intent"] == "compliance_research"
        assert context["tool_performance_history"]["search"]["success_rate"] == 0.95

    def test_context_with_previous_results(self):
        """Test context building with previous agent results."""
        previous_results = {
            "agent_output": "Analysis complete",
            "confidence": 0.9,
            "entities_found": ["GDPR", "EU", "privacy"],
        }

        context = build_agent_context(
            user_query="What is GDPR?", session_state={}, previous_results=previous_results
        )

        assert context["agent_output"] == "Analysis complete"
        assert context["confidence"] == 0.9
        assert context["entities_found"] == ["GDPR", "EU", "privacy"]


class TestPromptTemplateVariableSubstitution:
    """Test specific template variable substitution scenarios."""

    def test_boolean_values(self):
        """Test boolean value formatting."""
        loader = MultiAgentPromptLoader()

        result = loader._format_value(True)
        assert result == "true"

        result = loader._format_value(False)
        assert result == "false"

    def test_none_values(self):
        """Test None value handling."""
        loader = MultiAgentPromptLoader()

        result = loader._format_value(None)
        assert result == ""

    def test_empty_list_values(self):
        """Test empty list formatting."""
        loader = MultiAgentPromptLoader()

        result = loader._format_value([])
        assert result == ""

    def test_list_values(self):
        """Test list value formatting."""
        loader = MultiAgentPromptLoader()

        result = loader._format_value(["item1", "item2", "item3"])
        assert result == "item1, item2, item3"

    def test_dict_values(self):
        """Test dictionary value formatting."""
        loader = MultiAgentPromptLoader()

        test_dict = {"key": "value", "number": 42}
        result = loader._format_value(test_dict)

        # Should be valid JSON
        import json

        parsed = json.loads(result)
        assert parsed["key"] == "value"
        assert parsed["number"] == 42

    def test_nested_value_access(self):
        """Test nested property access."""
        loader = MultiAgentPromptLoader()

        context = {"user": {"preferences": {"detail_level": "high", "format": "detailed"}}}

        result = loader._get_nested_value("user.preferences.detail_level", context)
        assert result == "high"

        result = loader._get_nested_value("user.preferences.format", context)
        assert result == "detailed"

        # Test missing nested property
        result = loader._get_nested_value("user.missing.property", context)
        assert result == ""

    def test_condition_evaluation(self):
        """Test condition evaluation logic."""
        loader = MultiAgentPromptLoader()

        context = {
            "has_data": True,
            "empty_list": [],
            "filled_list": ["item1", "item2"],
            "empty_string": "",
            "filled_string": "content",
            "user": {"preferences": {"detail_level": "high"}},
        }

        # Test simple boolean
        assert loader._evaluate_condition("has_data", context) is True

        # Test empty vs filled collections
        assert loader._evaluate_condition("empty_list", context) is False
        assert loader._evaluate_condition("filled_list", context) is True

        # Test empty vs filled strings
        assert loader._evaluate_condition("empty_string", context) is False
        assert loader._evaluate_condition("filled_string", context) is True

        # Test nested property access
        assert loader._evaluate_condition("user.preferences.detail_level", context) is True
        assert loader._evaluate_condition("user.preferences.missing", context) is False

        # Test missing top-level property
        assert loader._evaluate_condition("missing_property", context) is False


class TestIntegrationWithExistingPrompts:
    """Integration tests with actual agent prompt files."""

    @pytest.mark.asyncio
    async def test_load_actual_agent_prompts(self):
        """Test loading actual agent prompt files."""
        loader = multi_agent_prompt_loader

        available_agents = loader.get_available_agents()

        # Should find our created agent prompts
        expected_agents = [
            "query_understanding",
            "tool_planning",
            "tool_execution",
            "response_synthesis",
        ]

        for agent in expected_agents:
            if agent in available_agents:  # Only test if file exists
                context = {
                    "user_query": "What is the EU AI Act?",
                    "query_analysis": {"intent": "information_seeking", "complexity": "medium"},
                }

                try:
                    rendered = await loader.get_agent_prompt(agent, context)

                    # Basic checks
                    assert isinstance(rendered, str)
                    assert len(rendered) > 0
                    # Query might appear in different forms depending on agent
                    assert (
                        "What is the EU AI Act?" in rendered
                        or "information_seeking" in rendered
                        or "medium" in rendered
                    )  # Check for query or analysis content
                    assert "{{" not in rendered  # No unprocessed template variables
                except FileNotFoundError:
                    # Skip if agent prompt file doesn't exist
                    pytest.skip(f"Agent prompt file {agent}.md not found")

    @pytest.mark.asyncio
    async def test_query_understanding_prompt_rendering(self):
        """Test specific rendering of query understanding prompt."""
        loader = multi_agent_prompt_loader

        available_agents = loader.get_available_agents()
        if "query_understanding" not in available_agents:
            pytest.skip("query_understanding prompt not available")

        context = {
            "user_query": "What enforcement actions has the EU taken against tech companies?",
            "user_preferences": {"detail_level": "high", "response_format": "detailed"},
            "conversation_history": ["Previous question about GDPR compliance"],
            "learned_patterns": {"common_intent": "enforcement_tracking"},
        }

        rendered = await loader.get_agent_prompt("query_understanding", context)

        # Check that context is properly integrated
        assert "What enforcement actions has the EU taken against tech companies?" in rendered
        assert "high" in rendered  # User preference should be included
        assert "Previous question about GDPR compliance" in rendered
        assert "enforcement_tracking" in rendered


if __name__ == "__main__":
    pytest.main([__file__])
