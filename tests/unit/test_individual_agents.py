"""Unit tests for individual agent implementations."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.language_models import BaseLLM

from src.chat.agent.agents import (
    QueryUnderstandingAgent,
    ResponseSynthesisAgent,
    ToolExecutionAgent,
    ToolPlanningAgent,
)
from src.chat.agent.base import AgentRole
from tests.fixtures.agent_test_data import AgentTestHelpers


class TestQueryUnderstandingAgent:
    """Test suite for Query Understanding Agent."""

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM for testing."""
        llm = AsyncMock(spec=BaseLLM)
        # Mock a realistic query analysis response
        response_mock = MagicMock()
        response_mock.content = """
        {
            "intent": "information_seeking",
            "confidence": 0.95,
            "complexity": "simple",
            "primary_entity": "EU AI Act",
            "secondary_entities": ["European Union", "artificial intelligence"],
            "key_relationships": ["AUTHORED_BY", "REGULATES"],
            "temporal_scope": "current",
            "analysis_strategy": "focused",
            "search_priorities": [
                {
                    "entity": "EU AI Act",
                    "priority": "high",
                    "reasoning": "Primary subject of query"
                }
            ],
            "expected_information_types": ["regulatory_framework", "policy_details"],
            "memory_insights": {
                "user_pattern_match": "information_seeking",
                "preference_alignment": "high_detail",
                "context_relevance": "new_topic"
            }
        }
        """
        llm.ainvoke.return_value = response_mock
        return llm

    @pytest.fixture
    def query_agent(self, mock_llm):
        """Create Query Understanding Agent with mock LLM."""
        return QueryUnderstandingAgent(llm=mock_llm)

    @pytest.mark.asyncio
    async def test_query_agent_initialization(self, query_agent):
        """Test Query Understanding Agent initialization."""
        assert query_agent.agent_role == AgentRole.QUERY_UNDERSTANDING
        assert query_agent.name == "QueryUnderstanding"
        assert query_agent.llm is not None
        assert query_agent.output_parser is not None

    @pytest.mark.asyncio
    async def test_successful_query_analysis(self, query_agent, sample_multi_agent_states):
        """Test successful query analysis process."""
        initial_state = sample_multi_agent_states["initial_state"]

        with patch.object(query_agent, "stream_thinking") as mock_stream:
            result = await query_agent.process(initial_state)

        # Verify successful result
        assert result.success
        assert result.next_agent == "tool_planning"
        assert "confidence" in result.message

        # Verify state updates
        updated_state = result.updated_state
        assert updated_state.query_analysis is not None
        assert updated_state.current_agent == "tool_planning"
        assert "query_understanding" in updated_state.agent_sequence

        # Verify analysis structure
        analysis = updated_state.query_analysis
        AgentTestHelpers.assert_valid_query_analysis(analysis)

        # Verify streaming calls
        assert mock_stream.call_count >= 2

    @pytest.mark.asyncio
    async def test_query_analysis_with_memory_integration(
        self, query_agent, sample_multi_agent_states
    ):
        """Test query analysis with memory context integration."""
        initial_state = sample_multi_agent_states["initial_state"]

        with patch.object(query_agent, "_get_memory_context") as mock_memory:
            mock_memory.return_value = {
                "user_preferences": {"detail_level": "high"},
                "learned_patterns": {"common_intent": "enforcement_tracking"},
                "tool_performance": {"search": {"success_rate": 0.94}},
            }

            result = await query_agent.process(initial_state)

        # Verify memory was consulted
        mock_memory.assert_called_once_with(initial_state.session_id)

        # Verify successful processing
        assert result.success
        assert result.updated_state.query_analysis is not None

    @pytest.mark.asyncio
    async def test_query_analysis_error_handling(self, query_agent, sample_multi_agent_states):
        """Test error handling in query analysis."""
        initial_state = sample_multi_agent_states["initial_state"]

        # Mock LLM to raise exception
        query_agent.llm.ainvoke.side_effect = Exception("LLM service unavailable")

        with patch.object(query_agent, "stream_custom") as mock_error:
            result = await query_agent.process(initial_state)

        # Verify error handling
        assert not result.success
        assert result.next_agent is None
        assert "failed" in result.message.lower()

        # Verify error streaming
        mock_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_analysis_output_parsing(self, query_agent, sample_multi_agent_states):
        """Test output parsing for query analysis."""
        initial_state = sample_multi_agent_states["initial_state"]

        result = await query_agent.process(initial_state)

        # Verify the output was parsed correctly
        analysis = result.updated_state.query_analysis

        assert analysis["intent"] == "information_seeking"
        assert analysis["confidence"] == 0.95
        assert analysis["complexity"] == "simple"
        assert analysis["primary_entity"] == "EU AI Act"
        assert len(analysis["secondary_entities"]) == 2
        assert len(analysis["search_priorities"]) == 1


class TestToolPlanningAgent:
    """Test suite for Tool Planning Agent."""

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM for testing."""
        llm = AsyncMock(spec=BaseLLM)
        response_mock = MagicMock()
        response_mock.content = """
        {
            "strategy_type": "focused",
            "estimated_execution_time": 25.0,
            "tool_sequence": [
                {
                    "step": 1,
                    "tool_name": "entity_lookup",
                    "parameters": {"entity_name": "EU AI Act"},
                    "purpose": "Get comprehensive information about the primary entity",
                    "expected_insights": "Regulatory framework details",
                    "estimated_time": 5.0,
                    "dependency": null
                },
                {
                    "step": 2,
                    "tool_name": "search",
                    "parameters": {"query": "EU AI Act implementation", "limit": 10},
                    "purpose": "Find implementation details",
                    "expected_insights": "Implementation requirements",
                    "estimated_time": 10.0,
                    "dependency": "step_1"
                }
            ],
            "success_criteria": {
                "primary": "Complete overview of EU AI Act",
                "secondary": "Implementation context",
                "minimum_threshold": "Basic regulation description"
            },
            "backup_strategies": [
                {
                    "trigger_condition": "entity_lookup fails",
                    "alternative_tools": ["search"],
                    "modified_approach": "Use search to establish context"
                }
            ],
            "optimization_notes": {
                "parallel_opportunities": "none for this simple sequence",
                "performance_priorities": "accuracy over speed",
                "user_preference_alignment": "high detail preference"
            }
        }
        """
        llm.ainvoke.return_value = response_mock
        return llm

    @pytest.fixture
    def planning_agent(self, mock_llm):
        """Create Tool Planning Agent with mock LLM."""
        return ToolPlanningAgent(llm=mock_llm)

    @pytest.mark.asyncio
    async def test_planning_agent_initialization(self, planning_agent):
        """Test Tool Planning Agent initialization."""
        assert planning_agent.agent_role == AgentRole.TOOL_PLANNING
        assert planning_agent.name == "ToolPlanning"
        assert planning_agent.llm is not None
        assert planning_agent.output_parser is not None

    @pytest.mark.asyncio
    async def test_successful_tool_planning(self, planning_agent, sample_multi_agent_states):
        """Test successful tool planning process."""
        # Use state after query analysis
        state_with_analysis = sample_multi_agent_states["query_analyzed_state"]

        with patch.object(planning_agent, "stream_thinking") as mock_stream:
            result = await planning_agent.process(state_with_analysis)

        # Verify successful result
        assert result.success
        assert result.next_agent == "tool_execution"
        assert "execution plan ready" in result.message.lower()

        # Verify state updates
        updated_state = result.updated_state
        assert updated_state.tool_plan is not None
        assert updated_state.current_agent == "tool_execution"
        assert "tool_planning" in updated_state.agent_sequence

        # Verify plan structure
        plan = updated_state.tool_plan
        AgentTestHelpers.assert_valid_tool_plan(plan)

        # Verify streaming calls
        assert mock_stream.call_count >= 2

    @pytest.mark.asyncio
    async def test_planning_without_query_analysis(self, planning_agent, sample_multi_agent_states):
        """Test planning fails gracefully without query analysis."""
        initial_state = sample_multi_agent_states["initial_state"]  # No query analysis

        result = await planning_agent.process(initial_state)

        # Verify failure
        assert not result.success
        assert result.next_agent is None
        assert "no query analysis" in result.message.lower()

    @pytest.mark.asyncio
    async def test_planning_with_memory_integration(
        self, planning_agent, sample_multi_agent_states
    ):
        """Test planning with memory context integration."""
        state_with_analysis = sample_multi_agent_states["query_analyzed_state"]

        with patch.object(planning_agent, "_get_memory_context") as mock_memory:
            mock_memory.return_value = {
                "tool_performance_history": {"search": {"success_rate": 0.94}},
                "successful_strategies": {"information_seeking": "focused"},
            }

            result = await planning_agent.process(state_with_analysis)

        # Verify memory was consulted
        mock_memory.assert_called_once_with(state_with_analysis.session_id)

        # Verify successful processing
        assert result.success
        assert result.updated_state.tool_plan is not None


class TestToolExecutionAgent:
    """Test suite for Tool Execution Agent."""

    @pytest.fixture
    def mock_tools(self):
        """Mock tools for testing."""

        async def mock_entity_lookup(entity_name: str):
            return {
                "entity": {"name": entity_name, "type": "Policy"},
                "success": True,
                "details": f"Information about {entity_name}",
            }

        async def mock_search(query: str, limit: int = 10):
            return {
                "results": [{"title": f"Result for {query}", "content": "Sample content"}],
                "total_results": 1,
                "success": True,
            }

        return {"entity_lookup": mock_entity_lookup, "search": mock_search}

    @pytest.fixture
    def execution_agent(self, mock_tools):
        """Create Tool Execution Agent with mock tools."""
        return ToolExecutionAgent(tools=mock_tools)

    @pytest.mark.asyncio
    async def test_execution_agent_initialization(self, execution_agent, mock_tools):
        """Test Tool Execution Agent initialization."""
        assert execution_agent.agent_role == AgentRole.TOOL_EXECUTION
        assert execution_agent.name == "ToolExecution"
        assert execution_agent.tools == mock_tools

    @pytest.mark.asyncio
    async def test_successful_tool_execution(self, execution_agent, sample_multi_agent_states):
        """Test successful tool execution process."""
        # Use state after planning
        state_with_plan = sample_multi_agent_states["planning_complete_state"]

        with patch.object(execution_agent, "stream_thinking") as mock_stream, patch.object(
            execution_agent, "stream_custom"
        ) as mock_tool_stream:
            result = await execution_agent.process(state_with_plan)

        # Verify successful result
        assert result.success
        assert result.next_agent == "response_synthesis"
        assert "executed" in result.message.lower()

        # Verify state updates
        updated_state = result.updated_state
        assert updated_state.tool_results is not None
        assert len(updated_state.tool_results) > 0
        assert updated_state.executed_tools is not None
        assert updated_state.current_agent == "response_synthesis"
        assert "tool_execution" in updated_state.agent_sequence
        assert updated_state.execution_metadata is not None

        # Verify tool results structure
        for result_data in updated_state.tool_results:
            AgentTestHelpers.assert_valid_tool_result(result_data)

        # Verify streaming calls
        assert mock_stream.call_count >= 2
        assert mock_tool_stream.call_count >= 2

    @pytest.mark.asyncio
    async def test_execution_without_tool_plan(self, execution_agent, sample_multi_agent_states):
        """Test execution fails gracefully without tool plan."""
        initial_state = sample_multi_agent_states["initial_state"]  # No tool plan

        result = await execution_agent.process(initial_state)

        # Verify failure
        assert not result.success
        assert result.next_agent is None
        assert "no tool plan" in result.message.lower()

    @pytest.mark.asyncio
    async def test_execution_with_missing_tool(self, execution_agent, sample_multi_agent_states):
        """Test execution handles missing tools gracefully."""
        state_with_plan = sample_multi_agent_states["planning_complete_state"]

        # Modify plan to include non-existent tool
        modified_state = state_with_plan.copy()
        modified_state.tool_plan["tool_sequence"] = [
            {
                "step": 1,
                "tool_name": "nonexistent_tool",
                "parameters": {"param": "value"},
                "purpose": "Test missing tool",
                "estimated_time": 5,
            }
        ]

        with patch.object(execution_agent, "stream_custom") as mock_error:
            result = await execution_agent.process(modified_state)

        # Should still succeed but with failed tool results
        assert result.success  # Overall success even with failed tools
        assert len(result.updated_state.tool_results) == 1
        assert not result.updated_state.tool_results[0]["success"]
        assert "not available" in result.updated_state.tool_results[0]["error"]

    @pytest.mark.asyncio
    async def test_execution_result_processing(self, execution_agent, sample_multi_agent_states):
        """Test that tool results are properly processed and structured."""
        state_with_plan = sample_multi_agent_states["planning_complete_state"]

        result = await execution_agent.process(state_with_plan)

        # Verify result structure
        tool_results = result.updated_state.tool_results
        assert len(tool_results) > 0

        for tool_result in tool_results:
            assert "tool_name" in tool_result
            assert "success" in tool_result
            assert "execution_time" in tool_result
            assert "insights" in tool_result
            assert "quality_score" in tool_result
            assert isinstance(tool_result["quality_score"], (int, float))
            assert 0.0 <= tool_result["quality_score"] <= 1.0


class TestResponseSynthesisAgent:
    """Test suite for Response Synthesis Agent."""

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM for testing."""
        llm = AsyncMock(spec=BaseLLM)
        response_mock = MagicMock()
        response_mock.content = """
        {
            "response_text": "# EU AI Act Overview\\n\\nThe EU AI Act is a comprehensive regulation that addresses artificial intelligence system risks through a risk-based approach.\\n\\n## Key Findings:\\n- Comprehensive regulatory framework for AI systems\\n- Risk-based classification system\\n- Enforced by European Commission\\n\\n## Implementation Details:\\n- Entered into force: August 1, 2024\\n- Phased implementation approach\\n\\n**Confidence:** High (95%) based on comprehensive regulatory documentation",
            "confidence_level": 0.95,
            "information_completeness": "high",
            "source_count": 2,
            "key_insights_count": 5,
            "response_metadata": {
                "word_count": 150,
                "citation_count": 2,
                "jurisdictions_covered": ["EU"],
                "temporal_scope": "2024",
                "complexity_level": "simple"
            },
            "follow_up_suggestions": [
                {
                    "question": "What specific requirements does the AI Act impose on high-risk AI systems?",
                    "reasoning": "Would provide more detailed implementation guidance"
                }
            ],
            "synthesis_notes": {
                "information_quality": "high",
                "coverage_assessment": "comprehensive for introductory query",
                "user_satisfaction_prediction": "high"
            }
        }
        """
        llm.ainvoke.return_value = response_mock
        return llm

    @pytest.fixture
    def synthesis_agent(self, mock_llm):
        """Create Response Synthesis Agent with mock LLM."""
        return ResponseSynthesisAgent(llm=mock_llm)

    @pytest.mark.asyncio
    async def test_synthesis_agent_initialization(self, synthesis_agent):
        """Test Response Synthesis Agent initialization."""
        assert synthesis_agent.agent_role == AgentRole.RESPONSE_SYNTHESIS
        assert synthesis_agent.name == "ResponseSynthesis"
        assert synthesis_agent.llm is not None
        assert synthesis_agent.output_parser is not None

    @pytest.mark.asyncio
    async def test_successful_response_synthesis(self, synthesis_agent, sample_multi_agent_states):
        """Test successful response synthesis process."""
        # Use state after execution
        state_with_results = sample_multi_agent_states["execution_complete_state"]

        with patch.object(synthesis_agent, "stream_thinking") as mock_stream:
            result = await synthesis_agent.process(state_with_results)

        # Verify successful result
        assert result.success
        assert result.next_agent is None  # End of workflow
        assert "confidence" in result.message

        # Verify state updates
        updated_state = result.updated_state
        assert updated_state.synthesis_complete
        assert updated_state.final_response is not None
        assert len(updated_state.final_response) > 100
        assert updated_state.response_metadata is not None
        assert "response_synthesis" in updated_state.agent_sequence

        # Verify response structure
        assert "# EU AI Act Overview" in updated_state.final_response
        assert "## Key Findings:" in updated_state.final_response
        assert "Confidence:" in updated_state.final_response

        # Verify streaming calls
        assert mock_stream.call_count >= 2

    @pytest.mark.asyncio
    async def test_synthesis_without_tool_results(self, synthesis_agent, sample_multi_agent_states):
        """Test synthesis fails gracefully without tool results."""
        initial_state = sample_multi_agent_states["initial_state"]  # No tool results

        result = await synthesis_agent.process(initial_state)

        # Verify failure
        assert not result.success
        assert result.next_agent is None
        assert "no tool results" in result.message.lower()

    @pytest.mark.asyncio
    async def test_synthesis_context_preparation(self, synthesis_agent, sample_multi_agent_states):
        """Test that synthesis context is properly prepared."""
        state_with_results = sample_multi_agent_states["execution_complete_state"]

        # Test context preparation method
        context = synthesis_agent._prepare_synthesis_context(state_with_results)

        assert "Query Analysis:" in context
        assert "Tool Results:" in context
        assert "Execution Metadata:" in context
        assert len(context) > 100

    @pytest.mark.asyncio
    async def test_synthesis_with_memory_integration(
        self, synthesis_agent, sample_multi_agent_states
    ):
        """Test synthesis with memory context integration."""
        state_with_results = sample_multi_agent_states["execution_complete_state"]

        with patch.object(synthesis_agent, "_get_memory_context") as mock_memory:
            mock_memory.return_value = {
                "user_preferences": {"citation_style": "academic"},
                "response_patterns": {"preferred_length": "comprehensive"},
            }

            result = await synthesis_agent.process(state_with_results)

        # Verify memory was consulted
        mock_memory.assert_called_once_with(state_with_results.session_id)

        # Verify successful processing
        assert result.success
        assert result.updated_state.final_response is not None

    @pytest.mark.asyncio
    async def test_synthesis_error_handling(self, synthesis_agent, sample_multi_agent_states):
        """Test error handling in response synthesis."""
        state_with_results = sample_multi_agent_states["execution_complete_state"]

        # Mock LLM to raise exception
        synthesis_agent.llm.ainvoke.side_effect = Exception("LLM synthesis failed")

        with patch.object(synthesis_agent, "stream_custom") as mock_error:
            result = await synthesis_agent.process(state_with_results)

        # Verify error handling
        assert not result.success
        assert result.next_agent is None
        assert "failed" in result.message.lower()

        # Verify error streaming
        mock_error.assert_called_once()


class TestAgentIntegration:
    """Integration tests for agent interactions."""

    @pytest.mark.asyncio
    async def test_agent_state_progression(self, sample_multi_agent_states, sample_queries):
        """Test that agents properly progress state through workflow."""
        # Mock all components
        mock_llm = AsyncMock(spec=BaseLLM)
        mock_tools = {"entity_lookup": AsyncMock(), "search": AsyncMock()}

        # Mock realistic responses
        query_response = MagicMock()
        query_response.content = '{"intent": "information_seeking", "confidence": 0.95, "complexity": "simple", "primary_entity": "EU AI Act", "secondary_entities": [], "key_relationships": [], "temporal_scope": "current", "analysis_strategy": "focused", "search_priorities": [], "expected_information_types": [], "memory_insights": {}}'

        plan_response = MagicMock()
        plan_response.content = '{"strategy_type": "focused", "estimated_execution_time": 20.0, "tool_sequence": [{"step": 1, "tool_name": "entity_lookup", "parameters": {"entity_name": "EU AI Act"}, "purpose": "test", "estimated_time": 5.0, "dependency": null}], "success_criteria": {"primary": "test"}, "backup_strategies": [], "optimization_notes": {}}'

        synthesis_response = MagicMock()
        synthesis_response.content = '{"response_text": "Test response", "confidence_level": 0.9, "information_completeness": "high", "source_count": 1, "key_insights_count": 3, "response_metadata": {}, "follow_up_suggestions": [], "synthesis_notes": {}}'

        mock_llm.ainvoke.side_effect = [query_response, plan_response, synthesis_response]
        mock_tools["entity_lookup"].return_value = {"success": True, "data": "test"}

        # Initialize agents
        query_agent = QueryUnderstandingAgent(llm=mock_llm)
        planning_agent = ToolPlanningAgent(llm=mock_llm)
        execution_agent = ToolExecutionAgent(tools=mock_tools)
        synthesis_agent = ResponseSynthesisAgent(llm=mock_llm)

        # Start with initial state
        current_state = sample_multi_agent_states["initial_state"]

        # Step 1: Query Understanding
        with patch.object(query_agent, "stream_thinking"):
            result1 = await query_agent.process(current_state)

        assert result1.success
        assert result1.next_agent == "tool_planning"
        current_state = result1.updated_state

        # Step 2: Tool Planning
        with patch.object(planning_agent, "stream_thinking"):
            result2 = await planning_agent.process(current_state)

        assert result2.success
        assert result2.next_agent == "tool_execution"
        current_state = result2.updated_state

        # Step 3: Tool Execution
        with patch.object(execution_agent, "stream_thinking"), patch.object(
            execution_agent, "stream_custom"
        ):
            result3 = await execution_agent.process(current_state)

        assert result3.success
        assert result3.next_agent == "response_synthesis"
        current_state = result3.updated_state

        # Step 4: Response Synthesis
        with patch.object(synthesis_agent, "stream_thinking"):
            result4 = await synthesis_agent.process(current_state)

        assert result4.success
        assert result4.next_agent is None  # End of workflow
        final_state = result4.updated_state

        # Verify complete workflow
        assert len(final_state.agent_sequence) == 4
        assert final_state.synthesis_complete
        assert final_state.final_response is not None
        assert final_state.query_analysis is not None
        assert final_state.tool_plan is not None
        assert final_state.tool_results is not None

    @pytest.mark.asyncio
    async def test_agent_error_propagation(self, sample_multi_agent_states):
        """Test that agent errors are properly handled and don't crash workflow."""
        # Mock failing LLM
        mock_llm = AsyncMock(spec=BaseLLM)
        mock_llm.ainvoke.side_effect = Exception("LLM service down")

        query_agent = QueryUnderstandingAgent(llm=mock_llm)
        initial_state = sample_multi_agent_states["initial_state"]

        # Process should handle error gracefully
        with patch.object(query_agent, "stream_custom"):
            result = await query_agent.process(initial_state)

        assert not result.success
        assert result.next_agent is None
        assert "failed" in result.message.lower()

        # State should remain unchanged on error
        assert result.updated_state == initial_state


if __name__ == "__main__":
    pytest.main([__file__])
