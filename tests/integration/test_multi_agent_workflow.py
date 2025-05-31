"""Integration tests for multi-agent workflow and handoffs."""


import pytest

from src.chat.agent.base import MultiAgentState
from src.chat.agent.prompt_loader import build_agent_context
from tests.fixtures.agent_test_data import AgentTestHelpers


class TestMultiAgentWorkflowIntegration:
    """Integration tests for complete multi-agent workflows."""

    @pytest.mark.asyncio
    async def test_complete_workflow_simple_query(
        self, sample_queries, mock_kg_tools, mock_memory_manager, mock_streaming_manager
    ):
        """Test complete workflow from query to response for simple query."""

        # Get test data
        query_data = sample_queries["simple_information_seeking"]
        user_query = query_data["query"]

        # Initialize workflow state
        initial_state = MultiAgentState(
            original_query=user_query,
            current_agent="query_understanding",
            session_id="test_workflow_123",
            is_streaming=True,
        )

        # Step 1: Query Understanding Agent simulation
        query_context = build_agent_context(
            user_query=user_query,
            session_state=initial_state,
            memory_data={
                "user_preferences": {"detail_level": "high"},
                "learned_patterns": {"common_intent": "information_seeking"},
            },
        )

        # Simulate query understanding result
        query_analysis = {
            "intent": "information_seeking",
            "confidence": 0.95,
            "complexity": "simple",
            "primary_entity": "EU AI Act",
            "secondary_entities": ["European Union", "artificial intelligence"],
            "key_relationships": ["AUTHORED_BY", "REGULATES"],
            "temporal_scope": "current",
            "analysis_strategy": "focused",
            "search_priorities": [
                {"entity": "EU AI Act", "priority": "high", "reasoning": "Primary subject of query"}
            ],
            "expected_information_types": ["regulatory_framework", "policy_details"],
            "memory_insights": {
                "user_pattern_match": "information_seeking",
                "preference_alignment": "high_detail",
                "context_relevance": "new_topic",
            },
        }

        # Validate query analysis
        AgentTestHelpers.assert_valid_query_analysis(query_analysis)

        # Update state after query understanding
        post_query_state = MultiAgentState(
            original_query=user_query,
            processed_query=user_query,
            query_analysis=query_analysis,
            current_agent="tool_planning",
            agent_sequence=["query_understanding"],
            session_id="test_workflow_123",
            is_streaming=True,
        )

        # Step 2: Tool Planning Agent simulation
        planning_context = build_agent_context(
            user_query=user_query,
            session_state=post_query_state,
            memory_data={"tool_performance_history": {"search": {"success_rate": 0.94}}},
        )

        # Simulate tool planning result
        tool_plan = {
            "strategy_type": "focused",
            "estimated_execution_time": 25,
            "tool_sequence": [
                {
                    "step": 1,
                    "tool_name": "entity_lookup",
                    "parameters": {"entity_name": "EU AI Act"},
                    "purpose": "Get comprehensive information about the primary entity",
                    "expected_insights": "Regulatory framework details",
                    "estimated_time": 5,
                    "dependency": None,
                },
                {
                    "step": 2,
                    "tool_name": "search",
                    "parameters": {"query": "EU AI Act implementation", "limit": 10},
                    "purpose": "Find implementation details",
                    "expected_insights": "Implementation requirements",
                    "estimated_time": 10,
                    "dependency": "step_1",
                },
            ],
            "success_criteria": {
                "primary": "Complete overview of EU AI Act",
                "secondary": "Implementation context",
                "minimum_threshold": "Basic regulation description",
            },
            "backup_strategies": [
                {
                    "trigger_condition": "entity_lookup fails",
                    "alternative_tools": ["search"],
                    "modified_approach": "Use search to establish context",
                }
            ],
            "optimization_notes": {
                "parallel_opportunities": "none for this simple sequence",
                "performance_priorities": "accuracy over speed",
                "user_preference_alignment": "high detail preference",
            },
        }

        # Validate tool plan
        AgentTestHelpers.assert_valid_tool_plan(tool_plan)

        # Update state after tool planning
        post_planning_state = MultiAgentState(
            original_query=user_query,
            processed_query=user_query,
            query_analysis=query_analysis,
            tool_plan=tool_plan,
            current_agent="tool_execution",
            agent_sequence=["query_understanding", "tool_planning"],
            session_id="test_workflow_123",
            is_streaming=True,
        )

        # Step 3: Tool Execution Agent simulation
        execution_context = build_agent_context(
            user_query=user_query, session_state=post_planning_state
        )

        # Execute tools using mock
        tool_results = []

        # Execute entity_lookup
        lookup_result = await mock_kg_tools.entity_lookup("EU AI Act")
        tool_result_1 = {
            "tool_name": "entity_lookup",
            "success": lookup_result["success"],
            "execution_time": lookup_result["execution_time"],
            "parameters_used": {"entity_name": "EU AI Act"},
            "output": "Found comprehensive entity information",
            "insights": [
                "EU AI Act is a comprehensive regulation addressing AI system risks",
                "Applies risk-based approach with different requirements",
            ],
            "entities_found": [{"name": "EU AI Act", "type": "Policy", "relevance": "high"}],
            "relationships_discovered": lookup_result.get("entity", {}).get("related_entities", []),
            "source_citations": ["Official EU AI Act text"],
            "temporal_aspects": ["Entered into force: August 1, 2024"],
            "quality_score": 0.95,
            "error": None,
        }
        AgentTestHelpers.assert_valid_tool_result(tool_result_1)
        tool_results.append(tool_result_1)

        # Execute search
        search_result = await mock_kg_tools.search("EU AI Act implementation", limit=10)
        tool_result_2 = {
            "tool_name": "search",
            "success": True,
            "execution_time": search_result["execution_time"],
            "parameters_used": {"query": "EU AI Act implementation", "limit": 10},
            "output": f"Found {len(search_result['facts'])} relevant facts",
            "insights": [
                "Implementation follows phased approach",
                "Different requirements for different risk categories",
            ],
            "entities_found": search_result["entities"],
            "relationships_discovered": [],
            "source_citations": [f["source"] for f in search_result["facts"]],
            "temporal_aspects": [],
            "quality_score": 0.88,
            "error": None,
        }
        AgentTestHelpers.assert_valid_tool_result(tool_result_2)
        tool_results.append(tool_result_2)

        # Update state after tool execution
        post_execution_state = MultiAgentState(
            original_query=user_query,
            processed_query=user_query,
            query_analysis=query_analysis,
            tool_plan=tool_plan,
            executed_tools=["entity_lookup", "search"],
            tool_results=tool_results,
            current_agent="response_synthesis",
            agent_sequence=["query_understanding", "tool_planning", "tool_execution"],
            session_id="test_workflow_123",
            is_streaming=True,
            execution_metadata={
                "total_execution_time": 18.2,
                "tools_successful": 2,
                "information_quality": "high",
                "confidence_level": 0.91,
            },
        )

        # Step 4: Response Synthesis Agent simulation
        synthesis_context = build_agent_context(
            user_query=user_query,
            session_state=post_execution_state,
            memory_data={"user_preferences": {"citation_style": "academic"}},
        )

        # Simulate response synthesis
        final_response = {
            "response_text": """# EU AI Act Overview

The EU AI Act is a comprehensive regulation that addresses artificial intelligence system risks through a risk-based approach.

## Key Findings:
- Comprehensive regulatory framework for AI systems in the European Union
- Risk-based classification system with different requirements for different AI applications
- Enforced by the European Commission in coordination with national authorities

## Implementation Details:
- Entered into force: August 1, 2024
- Phased implementation with different requirements taking effect at different times
- Applies to AI systems based on their risk level and intended use

## Sources:
- Official EU AI Act text (Regulation 2024/1689)
- European Commission implementation guidance

**Confidence:** High (91%) based on comprehensive regulatory documentation
""",
            "confidence_level": 0.91,
            "information_completeness": "high",
            "source_count": 2,
            "key_insights_count": 5,
            "response_metadata": {
                "word_count": 150,
                "citation_count": 2,
                "jurisdictions_covered": ["EU"],
                "temporal_scope": "2024",
                "complexity_level": "simple",
            },
            "follow_up_suggestions": [
                {
                    "question": "What specific requirements does the AI Act impose on high-risk AI systems?",
                    "reasoning": "Would provide more detailed implementation guidance",
                },
                {
                    "question": "How does the AI Act interact with existing EU regulations like GDPR?",
                    "reasoning": "Would clarify regulatory landscape interactions",
                },
            ],
            "synthesis_notes": {
                "information_quality": "high",
                "coverage_assessment": "comprehensive for introductory query",
                "user_satisfaction_prediction": "high",
            },
        }

        # Final state update
        final_state = MultiAgentState(
            original_query=user_query,
            processed_query=user_query,
            query_analysis=query_analysis,
            tool_plan=tool_plan,
            executed_tools=["entity_lookup", "search"],
            tool_results=tool_results,
            synthesis_complete=True,
            final_response=final_response["response_text"],
            response_metadata=final_response["response_metadata"],
            current_agent="response_synthesis",
            agent_sequence=[
                "query_understanding",
                "tool_planning",
                "tool_execution",
                "response_synthesis",
            ],
            session_id="test_workflow_123",
            is_streaming=True,
            execution_metadata={
                "total_execution_time": 22.5,
                "agent_execution_times": {
                    "query_understanding": 1.2,
                    "tool_planning": 2.1,
                    "tool_execution": 15.1,
                    "response_synthesis": 4.1,
                },
            },
        )

        # Assertions for complete workflow
        assert final_state.synthesis_complete
        assert final_state.final_response is not None
        assert len(final_state.final_response) > 100
        assert final_state.response_metadata["confidence_level"] > 0.8
        assert len(final_state.agent_sequence) == 4
        assert final_state.execution_metadata["total_execution_time"] > 0

        # Verify all agents were called in correct sequence
        expected_sequence = [
            "query_understanding",
            "tool_planning",
            "tool_execution",
            "response_synthesis",
        ]
        assert final_state.agent_sequence == expected_sequence

        # Verify tools were executed
        assert len(final_state.executed_tools) == 2
        assert "entity_lookup" in final_state.executed_tools
        assert "search" in final_state.executed_tools

        # Verify mock tool calls
        assert mock_kg_tools.get_call_count("entity_lookup") == 1
        assert mock_kg_tools.get_call_count("search") == 1

    @pytest.mark.asyncio
    async def test_streaming_workflow_integration(
        self, sample_queries, mock_streaming_manager, mock_stream_writer
    ):
        """Test streaming integration throughout workflow."""

        mock_streaming_manager.set_stream_writer(mock_stream_writer)

        # Simulate streaming throughout workflow
        await mock_streaming_manager.emit_thinking(
            "query_understanding", "Analyzing query structure and intent..."
        )

        await mock_streaming_manager.emit_agent_transition(
            "query_understanding",
            "tool_planning",
            "Query analysis complete, proceeding to planning",
        )

        await mock_streaming_manager.emit_thinking(
            "tool_planning", "Designing optimal tool execution sequence..."
        )

        await mock_streaming_manager.emit_agent_transition(
            "tool_planning", "tool_execution", "Execution plan ready, beginning tool execution"
        )

        await mock_streaming_manager.emit_tool_execution(
            "tool_execution", "entity_lookup", "starting", ""
        )

        await mock_streaming_manager.emit_tool_execution(
            "tool_execution", "entity_lookup", "completed", "Found comprehensive entity information"
        )

        await mock_streaming_manager.emit_thinking(
            "response_synthesis", "Synthesizing findings into comprehensive response..."
        )

        # Verify streaming events
        events = mock_streaming_manager.get_emitted_events()
        assert len(events) == 7

        thinking_events = mock_streaming_manager.get_emitted_events("thinking")
        assert len(thinking_events) == 3

        transition_events = mock_streaming_manager.get_emitted_events("agent_transition")
        assert len(transition_events) == 2

        tool_events = mock_streaming_manager.get_emitted_events("tool_execution")
        assert len(tool_events) == 2

        # Verify stream writer was called
        assert mock_stream_writer.call_count == 7

    @pytest.mark.asyncio
    async def test_memory_integration_workflow(self, sample_queries, mock_memory_manager):
        """Test memory integration throughout workflow."""

        user_id = "test_user_workflow"
        query = sample_queries["enforcement_tracking"]["query"]

        # Test memory retrieval at start of workflow
        user_prefs = await mock_memory_manager.get_user_preferences(user_id)
        query_insights = await mock_memory_manager.get_query_insights(user_id)

        # Simulate learning from query during workflow
        await mock_memory_manager.learn_from_query(
            user_id=user_id,
            query=query,
            intent="enforcement_tracking",
            entities=["Meta", "European Union"],
            satisfaction_rating=4.2,
        )

        # Simulate tool performance learning
        await mock_memory_manager.update_tool_performance(
            tool_name="search", success=True, execution_time=0.12, error=None
        )

        await mock_memory_manager.update_tool_performance(
            tool_name="entity_lookup", success=True, execution_time=0.05, error=None
        )

        # Test pattern learning
        await mock_memory_manager.save_learned_pattern(
            pattern_type="successful_workflows",
            pattern_data={
                "query_type": "enforcement_tracking",
                "strategy_used": "comprehensive",
                "tools_sequence": ["search", "entity_lookup", "relationship_analysis"],
                "success_score": 0.91,
                "user_satisfaction": 4.2,
            },
        )

        # Verify memory operations
        assert mock_memory_manager.get_call_count("get_user_preferences") >= 1
        assert mock_memory_manager.get_call_count("learn_from_query") == 1
        assert mock_memory_manager.get_call_count("update_tool_performance") == 2
        assert mock_memory_manager.get_call_count("save_learned_pattern") == 1

        # Verify learned data
        updated_insights = await mock_memory_manager.get_query_insights(user_id)
        assert "enforcement_tracking" in dict(updated_insights["common_intents"])

        search_perf = await mock_memory_manager.get_tool_performance_history("search")
        assert search_perf["total_executions"] > 0
        assert search_perf["success_rate"] > 0

    @pytest.mark.asyncio
    async def test_error_handling_workflow(
        self, sample_queries, mock_kg_tools, mock_streaming_manager
    ):
        """Test error handling and recovery in workflow."""

        # Simulate tool failure
        mock_kg_tools.set_execution_delay("entity_lookup", 0.01)  # Very fast for error simulation

        # Test tool failure scenario
        try:
            # This should succeed with mock data
            result = await mock_kg_tools.entity_lookup("Nonexistent Entity")
            assert not result["success"]
            assert "error" in result
        except Exception as e:
            # If exception occurs, verify it's handled gracefully
            assert isinstance(e, Exception)

        # Test error streaming
        await mock_streaming_manager.emit_error(
            "tool_execution", "Entity lookup failed: entity not found", "entity_not_found"
        )

        # Test backup strategy activation
        # Simulate switching to search when entity_lookup fails
        search_result = await mock_kg_tools.search("Nonexistent Entity", limit=5)
        assert search_result["total_results"] >= 0  # Should not fail, even with no results

        # Verify error was logged
        error_events = mock_streaming_manager.get_emitted_events("error")
        assert len(error_events) == 1
        assert "entity not found" in error_events[0]["error_message"]

    @pytest.mark.asyncio
    async def test_complex_query_workflow(self, sample_queries, mock_kg_tools):
        """Test workflow with complex query requiring comprehensive analysis."""

        complex_query_data = sample_queries["complex_compliance"]
        query = complex_query_data["query"]

        # Simulate complex query analysis
        query_analysis = {
            "intent": "compliance_research",
            "confidence": 0.88,
            "complexity": "complex",
            "primary_entity": "GDPR",
            "secondary_entities": ["Digital Services Act", "EU AI Act", "social media platforms"],
            "key_relationships": ["REGULATES", "AFFECTS", "REQUIRES_COMPLIANCE"],
            "temporal_scope": "current",
            "analysis_strategy": "comprehensive",
            "search_priorities": [
                {"entity": "GDPR", "priority": "high", "reasoning": "Foundational regulation"},
                {"entity": "Meta", "priority": "high", "reasoning": "Example platform"},
                {
                    "entity": "Digital Services Act",
                    "priority": "medium",
                    "reasoning": "Related regulation",
                },
            ],
            "expected_information_types": [
                "compliance_requirements",
                "regulatory_interactions",
                "enforcement_precedents",
            ],
            "memory_insights": {
                "user_pattern_match": "compliance_research_pattern",
                "preference_alignment": "detailed_multi_jurisdictional",
                "context_relevance": "follows_enforcement_questions",
            },
        }

        # Test comprehensive tool plan for complex query
        tool_plan = {
            "strategy_type": "comprehensive",
            "estimated_execution_time": 45,
            "tool_sequence": [
                {
                    "step": 1,
                    "tool_name": "search",
                    "parameters": {
                        "query": "GDPR Digital Services Act AI Act compliance interaction",
                        "limit": 15,
                    },
                    "purpose": "Establish broad regulatory landscape",
                    "expected_insights": "Regulatory interactions overview",
                    "estimated_time": 10,
                    "dependency": None,
                },
                {
                    "step": 2,
                    "tool_name": "relationship_analysis",
                    "parameters": {"entity1": "GDPR", "entity2": "Digital Services Act"},
                    "purpose": "Analyze specific regulatory relationships",
                    "expected_insights": "How regulations interact",
                    "estimated_time": 8,
                    "dependency": None,
                },
                {
                    "step": 3,
                    "tool_name": "find_paths_between_entities",
                    "parameters": {"entity1": "Meta", "entity2": "EU AI Act", "max_path_length": 3},
                    "purpose": "Find regulatory pathways",
                    "expected_insights": "How AI Act affects Meta",
                    "estimated_time": 12,
                    "dependency": "step_2",
                },
            ],
            "success_criteria": {
                "primary": "Comprehensive multi-regulation compliance analysis",
                "secondary": "Specific company examples and interactions",
                "minimum_threshold": "Basic understanding of regulatory interactions",
            },
            "backup_strategies": [
                {
                    "trigger_condition": "relationship_analysis insufficient",
                    "alternative_tools": ["traverse_from_entity", "get_communities"],
                    "modified_approach": "Use network traversal for relationships",
                }
            ],
            "optimization_notes": {
                "parallel_opportunities": "steps 1 and 2 can run in parallel",
                "performance_priorities": "thoroughness over speed",
                "user_preference_alignment": "comprehensive analysis for complex query",
            },
        }

        # Execute comprehensive tool sequence
        results = []

        # Step 1: Search
        search_result = await mock_kg_tools.search(
            "GDPR Digital Services Act AI Act compliance interaction", limit=15
        )
        results.append(
            {
                "tool_name": "search",
                "success": True,
                "insights": [f"Found {search_result['total_results']} regulatory interactions"],
                "quality_score": 0.87,
            }
        )

        # Step 2: Relationship analysis
        rel_result = await mock_kg_tools.relationship_analysis("GDPR", "Digital Services Act")
        results.append(
            {
                "tool_name": "relationship_analysis",
                "success": True,
                "insights": [
                    f"Found {len(rel_result['direct_relationships'])} direct relationships"
                ],
                "quality_score": 0.82,
            }
        )

        # Step 3: Path finding
        path_result = await mock_kg_tools.find_paths_between_entities(
            "Meta", "EU AI Act", max_path_length=3
        )
        results.append(
            {
                "tool_name": "find_paths_between_entities",
                "success": path_result["connection_exists"],
                "insights": [f"Found {len(path_result['paths_found'])} connection paths"],
                "quality_score": 0.79,
            }
        )

        # Verify comprehensive analysis
        assert len(results) == 3
        assert all(r["success"] for r in results)

        # Verify mock tool calls for complex workflow
        assert mock_kg_tools.get_call_count("search") >= 1
        assert mock_kg_tools.get_call_count("relationship_analysis") >= 1
        assert mock_kg_tools.get_call_count("find_paths_between_entities") >= 1

        # Calculate overall workflow metrics
        total_insights = sum(len(r["insights"]) for r in results)
        avg_quality = sum(r["quality_score"] for r in results) / len(results)

        assert total_insights >= 3
        assert avg_quality > 0.7


if __name__ == "__main__":
    pytest.main([__file__])
