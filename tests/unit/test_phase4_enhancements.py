"""Tests for Phase 4 enhanced streaming and memory capabilities."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.chat.agent.memory import MemoryManager
from src.chat.agent.orchestrator import MultiAgentOrchestrator
from src.chat.agent.streaming import StreamingManager, StreamingThinkingGenerator
from src.chat.agent.tool_integration import ToolIntegrationManager


class TestEnhancedStreaming:
    """Test enhanced streaming capabilities."""

    @pytest.fixture
    def streaming_manager(self):
        """Create streaming manager for testing."""
        return StreamingManager()

    @pytest.fixture
    def thinking_generator(self, streaming_manager):
        """Create thinking generator for testing."""
        return StreamingThinkingGenerator(streaming_manager)

    def test_thinking_generator_initialization(self, thinking_generator):
        """Test enhanced thinking generator initialization."""
        assert thinking_generator.user_preferences == {}
        assert thinking_generator.thinking_history == []
        assert thinking_generator.adaptive_timing == True
        assert thinking_generator.context_aware == True

    def test_user_preferences_setting(self, thinking_generator):
        """Test setting user preferences."""
        preferences = {
            "thinking_speed": "fast",
            "detail_level": "high",
            "response_format": "structured",
        }

        thinking_generator.set_user_preferences(preferences)
        assert thinking_generator.user_preferences == preferences

    def test_adaptive_delay_calculation(self, thinking_generator):
        """Test adaptive delay calculation based on complexity and user preferences."""
        # Test different complexity levels
        assert thinking_generator.get_adaptive_delay("simple", "normal") == 0.3
        assert thinking_generator.get_adaptive_delay("normal", "normal") == 0.6
        assert thinking_generator.get_adaptive_delay("complex", "normal") == 1.0

        # Test different speed preferences (use approximate equality for floating point)
        assert abs(thinking_generator.get_adaptive_delay("normal", "fast") - 0.3) < 0.001
        assert abs(thinking_generator.get_adaptive_delay("normal", "slow") - 0.9) < 0.001
        assert abs(thinking_generator.get_adaptive_delay("normal", "detailed") - 1.2) < 0.001

        # Test with adaptive timing disabled
        thinking_generator.adaptive_timing = False
        assert thinking_generator.get_adaptive_delay("complex", "detailed") == 0.5

    @pytest.mark.asyncio
    async def test_contextual_thinking_emission(self, thinking_generator):
        """Test contextual thinking emission with formatting."""
        thinking_generator.templates.QUERY_UNDERSTANDING = {
            "test_template": "Analyzing {entity} with {confidence} confidence"
        }

        with patch.object(thinking_generator.streaming_manager, "emit_thinking") as mock_emit:
            mock_emit.return_value = None

            context = {"entity": "EU AI Act", "confidence": "95%"}

            await thinking_generator.emit_contextual_thinking(
                "query_understanding", "test_template", context, "simple"
            )

            mock_emit.assert_called_once_with(
                "query_understanding", "Analyzing EU AI Act with 95% confidence"
            )

            # Check thinking history was recorded
            assert len(thinking_generator.thinking_history) == 1
            assert thinking_generator.thinking_history[0]["agent"] == "query_understanding"
            assert thinking_generator.thinking_history[0]["template_key"] == "test_template"


class TestEnhancedMemory:
    """Test enhanced memory capabilities."""

    @pytest.fixture
    def memory_manager(self):
        """Create memory manager for testing."""
        manager = MemoryManager()
        manager.store = AsyncMock()
        return manager

    @pytest.mark.asyncio
    async def test_user_conversation_pattern_analysis(self, memory_manager):
        """Test user conversation pattern analysis."""
        # Mock stored patterns
        stored_patterns = {
            "common_intents": {"information_seeking": 10, "analysis": 5},
            "preferred_detail_level": "high",
            "question_complexity_distribution": {"simple": 0.3, "medium": 0.5, "complex": 0.2},
            "feedback_patterns": {"positive": 8, "negative": 2},
        }
        memory_manager.store.aget.return_value = stored_patterns

        patterns = await memory_manager.analyze_user_conversation_patterns("test_user")

        assert patterns["common_intents"]["information_seeking"] == 10
        assert patterns["preferred_detail_level"] == "high"
        assert patterns["feedback_patterns"]["positive"] == 8

    @pytest.mark.asyncio
    async def test_conversation_pattern_updates(self, memory_manager):
        """Test updating conversation patterns."""
        # Mock existing patterns
        existing_patterns = {
            "common_intents": {"information_seeking": 5},
            "question_complexity_distribution": {"simple": 0.4, "medium": 0.6, "complex": 0.0},
            "feedback_patterns": {"positive": 3, "negative": 1},
            "interaction_time_patterns": {},
        }
        memory_manager.store.aget.return_value = existing_patterns
        memory_manager.store.aput.return_value = None

        await memory_manager.update_user_conversation_patterns(
            user_id="test_user",
            query="What is the EU AI Act?",
            intent="information_seeking",
            complexity="simple",
            satisfaction_rating=4.5,
            response_time=2.3,
        )

        # Verify store was called to save updated patterns
        memory_manager.store.aput.assert_called_once()
        call_args = memory_manager.store.aput.call_args
        assert call_args[0][0] == "user_conversation_patterns_test_user"

        updated_patterns = call_args[0][1]
        assert updated_patterns["common_intents"]["information_seeking"] == 6
        assert updated_patterns["feedback_patterns"]["positive"] == 4

    @pytest.mark.asyncio
    async def test_personalization_recommendations(self, memory_manager):
        """Test getting personalization recommendations."""
        # Mock patterns indicating satisfied user
        patterns = {
            "common_intents": {"information_seeking": 15, "analysis": 3},
            "question_complexity_distribution": {"simple": 0.6, "medium": 0.3, "complex": 0.1},
            "feedback_patterns": {"positive": 18, "negative": 2},
            "preferred_detail_level": "medium",
        }
        memory_manager.store.aget.return_value = patterns

        recommendations = await memory_manager.get_personalization_recommendations("test_user")

        assert recommendations["thinking_speed"] == "fast"  # High satisfaction ratio
        assert recommendations["response_format"] == "structured"  # Default for info seeking
        assert recommendations["detail_level"] == "medium"
        assert recommendations["complexity_comfort"] == "simple"  # Most common
        assert recommendations["satisfaction_trend"] == "improving"


class TestToolIntegration:
    """Test tool integration capabilities."""

    @pytest.fixture
    def mock_graphiti_client(self):
        """Create mock Graphiti client."""
        client = MagicMock()
        return client

    @pytest.fixture
    def tool_integration_manager(self, mock_graphiti_client):
        """Create tool integration manager with mocked tools."""
        with patch("src.chat.agent.tool_integration.GraphitiSearchTool") as mock_search_tool:
            mock_search_tool.return_value = MagicMock()
            manager = ToolIntegrationManager(mock_graphiti_client)
            return manager

    def test_tool_recommendations_information_seeking(self, tool_integration_manager):
        """Test tool recommendations for information seeking queries."""
        recommendations = tool_integration_manager.get_tool_recommendations(
            intent="information_seeking",
            entities=["EU AI Act", "European Commission"],
            complexity="simple",
            strategy_type="focused",
        )

        assert len(recommendations) >= 1
        assert recommendations[0]["priority"] == "high"

        # Should contain either search or entity details as high-priority tools
        tool_names = [r["tool_name"] for r in recommendations]
        assert "search" in tool_names or "get_entity_details" in tool_names

        # If search is present, verify the query parameter
        search_tools = [r for r in recommendations if r["tool_name"] == "search"]
        if search_tools:
            assert "EU AI Act European Commission" in search_tools[0]["parameters"]["query"]

    def test_tool_recommendations_relationship_analysis(self, tool_integration_manager):
        """Test tool recommendations for relationship analysis."""
        recommendations = tool_integration_manager.get_tool_recommendations(
            intent="relationship_analysis",
            entities=["Meta", "GDPR"],
            complexity="medium",
            strategy_type="comprehensive",
        )

        assert len(recommendations) >= 1
        # Should include relationship-focused tools
        tool_names = [r["tool_name"] for r in recommendations]
        assert (
            "find_paths_between_entities" in tool_names or "get_entity_relationships" in tool_names
        )

    def test_tool_recommendations_temporal_analysis(self, tool_integration_manager):
        """Test tool recommendations for temporal analysis."""
        recommendations = tool_integration_manager.get_tool_recommendations(
            intent="temporal_analysis",
            entities=["Digital Services Act"],
            complexity="complex",
            strategy_type="comprehensive",
        )

        assert len(recommendations) >= 1
        tool_names = [r["tool_name"] for r in recommendations]
        assert "get_entity_timeline" in tool_names

    def test_tool_recommendations_complexity_adjustment(self, tool_integration_manager):
        """Test that complexity affects number of tool recommendations."""
        simple_recs = tool_integration_manager.get_tool_recommendations(
            intent="information_seeking",
            entities=["EU AI Act"],
            complexity="simple",
            strategy_type="focused",
        )

        complex_recs = tool_integration_manager.get_tool_recommendations(
            intent="information_seeking",
            entities=["EU AI Act"],
            complexity="complex",
            strategy_type="comprehensive",
        )

        # Simple queries should have fewer recommendations
        assert len(simple_recs) <= 2
        assert len(complex_recs) >= len(simple_recs)

    @pytest.mark.asyncio
    async def test_tool_execution_sequence(self, tool_integration_manager):
        """Test executing a sequence of tools."""
        # Mock tool execution with both sync and async interfaces
        mock_tool = MagicMock()
        mock_tool._run.return_value = {"test": "result", "nodes": [{"name": "Test Entity"}]}
        mock_tool._arun = AsyncMock(
            return_value={"test": "result", "nodes": [{"name": "Test Entity"}]}
        )
        tool_integration_manager.tools["test_tool"] = mock_tool

        tool_sequence = [
            {"tool_name": "test_tool", "parameters": {"query": "test"}, "purpose": "Test execution"}
        ]

        results = await tool_integration_manager.execute_tool_sequence(tool_sequence)

        assert len(results) == 1
        assert results[0]["success"] == True
        assert results[0]["tool_name"] == "test_tool"
        assert len(results[0]["entities_found"]) == 1
        assert results[0]["entities_found"][0]["name"] == "Test Entity"

    def test_tool_performance_tracking(self, tool_integration_manager):
        """Test tool performance tracking."""
        # Simulate tool executions with higher success rate for medium reliability
        tool_integration_manager._update_tool_performance("search", True, 1.5, None)
        tool_integration_manager._update_tool_performance("search", True, 2.0, None)
        tool_integration_manager._update_tool_performance("search", True, 1.0, None)
        tool_integration_manager._update_tool_performance("search", False, 0.5, "Connection error")

        performance = tool_integration_manager.get_tool_performance_summary()

        assert "search" in performance
        search_perf = performance["search"]
        assert search_perf["total_executions"] == 4
        assert search_perf["success_rate"] == 3 / 4  # 0.75, which is in medium range
        assert search_perf["avg_execution_time"] == (1.5 + 2.0 + 1.0 + 0.5) / 4
        assert search_perf["reliability"] == "medium"  # Success rate between 0.7 and 0.9


class TestIntegratedOrchestrator:
    """Test orchestrator with Phase 4 enhancements."""

    @pytest.fixture
    def enhanced_orchestrator(self):
        """Create orchestrator with Phase 4 enhancements."""
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(content='{"test": "response"}')

        orchestrator = MultiAgentOrchestrator(llm=mock_llm, tools={})

        # Mock the tool integration manager
        orchestrator.tool_integration_manager = MagicMock()
        orchestrator.tool_integration_manager.get_tool_recommendations.return_value = [
            {
                "tool_name": "search",
                "parameters": {"query": "test", "limit": 5},
                "purpose": "Test search",
                "priority": "high",
                "estimated_time": 2.0,
            }
        ]

        return orchestrator

    @pytest.mark.asyncio
    async def test_enhanced_learning_integration(self, enhanced_orchestrator):
        """Test enhanced learning with conversation patterns."""
        from langchain_core.messages import HumanMessage

        from src.chat.agent.base import MultiAgentState

        # Mock memory manager methods
        enhanced_orchestrator.memory_manager.update_user_conversation_patterns = AsyncMock()
        enhanced_orchestrator.memory_manager.learn_from_query = AsyncMock()
        enhanced_orchestrator.memory_manager.get_personalization_recommendations = AsyncMock(
            return_value={"thinking_speed": "fast", "response_format": "structured"}
        )
        enhanced_orchestrator.memory_manager.update_tool_performance = AsyncMock()

        # Create test state
        final_state = MultiAgentState(
            original_query="Test query",
            query_analysis={
                "intent": "information_seeking",
                "complexity": "simple",
                "confidence": 0.9,
            },
            execution_metadata={"agent_execution_times": {"search": 2.0}},
            messages=[HumanMessage(content="Test")],
        )

        await enhanced_orchestrator._learn_from_interaction("test_user", "Test query", final_state)

        # Verify enhanced learning methods were called
        enhanced_orchestrator.memory_manager.update_user_conversation_patterns.assert_called_once()
        enhanced_orchestrator.memory_manager.learn_from_query.assert_called_once()
        enhanced_orchestrator.memory_manager.get_personalization_recommendations.assert_called_once()
        enhanced_orchestrator.memory_manager.update_tool_performance.assert_called_once()

    @pytest.mark.asyncio
    async def test_personalization_setup(self, enhanced_orchestrator):
        """Test personalization setup at query start."""
        # Mock personalization
        enhanced_orchestrator.memory_manager.get_personalization_recommendations = AsyncMock(
            return_value={"thinking_speed": "detailed", "response_format": "comprehensive"}
        )

        # Mock the query execution
        with patch.object(
            enhanced_orchestrator, "_learn_from_interaction"
        ) as mock_learn, patch.object(enhanced_orchestrator.graph, "astream") as mock_stream:
            mock_stream.return_value = async_generator_mock(
                [{"test_node": {"final_response": "Test response"}}]
            )

            result = await enhanced_orchestrator.process_query(
                query="Test query", user_id="test_user"
            )

            # Verify personalization was set up
            enhanced_orchestrator.memory_manager.get_personalization_recommendations.assert_called_once_with(
                "test_user"
            )
            assert (
                enhanced_orchestrator.thinking_generator.user_preferences["thinking_speed"]
                == "detailed"
            )


# Helper function for async generator mocking
async def async_generator_mock(items):
    """Create async generator for mocking."""
    for item in items:
        yield item


if __name__ == "__main__":
    pytest.main([__file__])
