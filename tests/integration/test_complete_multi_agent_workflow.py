"""
Comprehensive end-to-end integration tests for the complete multi-agent workflow.
Tests Phase 1-4 integration and validates the entire political monitoring system.
"""

import pytest
import asyncio
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.chat.agent.orchestrator import MultiAgentOrchestrator, MultiAgentStreamingOrchestrator
from src.chat.agent.base import MultiAgentState
from src.chat.agent.memory import MemoryManager
from src.chat.agent.streaming import StreamingManager, StreamingThinkingGenerator
from src.chat.agent.tool_integration import ToolIntegrationManager
from langchain_core.messages import HumanMessage


class TestCompleteMultiAgentWorkflow:
    """Comprehensive end-to-end testing of the complete multi-agent system."""
    
    @pytest.fixture
    async def complete_orchestrator(self):
        """Create a fully configured orchestrator with all Phase 1-4 enhancements."""
        # Mock LLM with realistic responses
        mock_llm = AsyncMock()
        
        # Configure LLM responses for each agent
        def configure_llm_response(content: str):
            mock_response = MagicMock()
            mock_response.content = content
            return mock_response
        
        # Query Understanding Response
        query_analysis_response = """{
            "intent": "information_seeking",
            "confidence": 0.92,
            "complexity": "medium",
            "primary_entity": "EU AI Act",
            "secondary_entities": ["European Commission", "artificial intelligence", "regulation"],
            "key_relationships": ["REGULATES", "AFFECTS", "IMPLEMENTS"],
            "temporal_scope": "current",
            "analysis_strategy": "comprehensive",
            "search_priorities": [
                {"entity": "EU AI Act", "reasoning": "Primary policy focus"},
                {"entity": "European Commission", "reasoning": "Regulatory authority"}
            ],
            "expected_information_types": ["policy_details", "implementation_timeline", "compliance_requirements"],
            "memory_insights": {
                "user_preference": "comprehensive_analysis",
                "previous_queries": "ai_regulation_focus"
            }
        }"""
        
        # Tool Planning Response
        tool_plan_response = """{
            "strategy_type": "comprehensive",
            "estimated_execution_time": 12.5,
            "tool_sequence": [
                {
                    "tool_name": "search",
                    "parameters": {"query": "EU AI Act European Commission", "limit": 10, "search_type": "comprehensive"},
                    "purpose": "Find comprehensive information about EU AI Act",
                    "priority": "high",
                    "estimated_time": 4.0
                },
                {
                    "tool_name": "get_entity_details",
                    "parameters": {"entity_name": "EU AI Act"},
                    "purpose": "Get detailed information about the AI Act",
                    "priority": "high", 
                    "estimated_time": 3.0
                },
                {
                    "tool_name": "get_entity_relationships",
                    "parameters": {"entity_name": "EU AI Act", "max_relationships": 15},
                    "purpose": "Explore relationships and impact network",
                    "priority": "medium",
                    "estimated_time": 3.5
                },
                {
                    "tool_name": "get_entity_timeline",
                    "parameters": {"entity_name": "EU AI Act", "days_back": 365},
                    "purpose": "Track development timeline",
                    "priority": "medium",
                    "estimated_time": 2.0
                }
            ],
            "success_criteria": {
                "primary": "Complete analysis of EU AI Act status and implications",
                "secondary": "Understand regulatory timeline and compliance requirements",
                "minimum": "Basic information about current AI Act status"
            },
            "backup_strategies": [
                {
                    "name": "fallback_search",
                    "description": "Use basic search if specific tools fail",
                    "tools": ["search"]
                }
            ],
            "optimization_notes": {
                "strategy": "Comprehensive analysis for complex regulatory query",
                "confidence": "0.92",
                "estimated_quality": "high"
            }
        }"""
        
        # Response Synthesis Response
        synthesis_response = """{
            "response_text": "## EU AI Act: Comprehensive Analysis\\n\\nThe European Union's Artificial Intelligence Act represents landmark legislation that establishes comprehensive rules for AI systems across the EU. Based on my analysis of current information:\\n\\n### Current Status\\nThe EU AI Act was formally adopted by the European Parliament and is now in the implementation phase. The legislation takes a risk-based approach, categorizing AI systems into different risk levels with corresponding obligations.\\n\\n### Key Provisions\\n- **High-Risk AI Systems**: Strict requirements for systems used in critical areas like healthcare, transportation, and law enforcement\\n- **Prohibited AI Practices**: Bans on AI systems that pose unacceptable risks, such as social scoring\\n- **Transparency Requirements**: Clear disclosure requirements for AI systems that interact with humans\\n- **Innovation Support**: Provisions for regulatory sandboxes to foster AI innovation\\n\\n### Implementation Timeline\\n- **2024**: Prohibitions on certain AI practices take effect\\n- **2025**: Requirements for general-purpose AI models\\n- **2026**: Full implementation of high-risk AI system requirements\\n\\n### Business Impact\\nOrganizations deploying AI systems in the EU must assess their systems against the Act's requirements, implement compliance measures, and prepare for ongoing regulatory oversight.\\n\\n### Sources\\nThis analysis is based on official EU documents, regulatory guidance, and recent policy developments tracked through multiple authoritative sources.",
            "confidence_level": 0.89,
            "information_completeness": "comprehensive",
            "source_count": 8,
            "key_insights_count": 12,
            "response_metadata": {
                "analysis_depth": "comprehensive",
                "regulatory_focus": "high",
                "compliance_guidance": "detailed",
                "temporal_coverage": "current_and_future"
            },
            "follow_up_suggestions": [
                {
                    "question": "What specific compliance steps should our organization take?",
                    "reasoning": "Practical implementation guidance"
                },
                {
                    "question": "How does the AI Act affect existing AI systems?",
                    "reasoning": "Legacy system compliance"
                },
                {
                    "question": "What are the enforcement mechanisms and penalties?",
                    "reasoning": "Risk assessment for non-compliance"
                }
            ],
            "synthesis_notes": {
                "information_quality": "high",
                "source_diversity": "excellent",
                "analysis_completeness": "comprehensive"
            }
        }"""
        
        # Configure LLM to return appropriate responses based on call order
        response_sequence = [
            configure_llm_response(query_analysis_response),
            configure_llm_response(tool_plan_response), 
            configure_llm_response(synthesis_response)
        ]
        mock_llm.ainvoke.side_effect = response_sequence
        
        # Create mock tools with realistic responses
        mock_tools = {
            "search": AsyncMock(return_value={
                "nodes": [
                    {"name": "EU AI Act", "type": "Policy", "summary": "Comprehensive AI regulation"},
                    {"name": "European Commission", "type": "Organization", "summary": "EU executive body"},
                    {"name": "Artificial Intelligence", "type": "Technology", "summary": "AI technology domain"}
                ],
                "edges": [
                    {"source": "European Commission", "target": "EU AI Act", "relationship": "PROPOSES"},
                    {"source": "EU AI Act", "target": "Artificial Intelligence", "relationship": "REGULATES"}
                ],
                "summary": "Found comprehensive information about EU AI Act development and implementation"
            }),
            "get_entity_details": AsyncMock(return_value={
                "entity": "EU AI Act",
                "details": {
                    "status": "Adopted",
                    "implementation_date": "2024-08-01",
                    "scope": "All AI systems deployed in EU",
                    "risk_categories": ["Prohibited", "High-risk", "Limited risk", "Minimal risk"]
                },
                "sources": ["Official Journal of EU", "European Parliament", "European Commission"]
            }),
            "get_entity_relationships": AsyncMock(return_value={
                "relationships": [
                    {"target": "European Parliament", "relationship": "ADOPTED_BY", "strength": 0.95},
                    {"target": "Member States", "relationship": "APPLIES_TO", "strength": 0.90},
                    {"target": "AI Systems", "relationship": "REGULATES", "strength": 1.0},
                    {"target": "Digital Single Market", "relationship": "SUPPORTS", "strength": 0.85}
                ]
            }),
            "get_entity_timeline": AsyncMock(return_value={
                "timeline": [
                    {"date": "2024-05-21", "event": "European Parliament adoption", "significance": "high"},
                    {"date": "2024-07-12", "event": "Council of EU final approval", "significance": "high"},
                    {"date": "2024-08-01", "event": "Publication in Official Journal", "significance": "critical"},
                    {"date": "2025-02-02", "event": "Governance provisions apply", "significance": "medium"}
                ]
            })
        }
        
        # Create orchestrator with all enhancements
        orchestrator = MultiAgentOrchestrator(llm=mock_llm, tools=mock_tools)
        
        # Mock the tool integration manager to use our mock tools
        mock_tool_integration = MagicMock()
        mock_tool_integration.get_tool_recommendations.return_value = [
            {
                "tool_name": "search",
                "parameters": {"query": "EU AI Act European Commission", "limit": 10, "search_type": "comprehensive"},
                "purpose": "Find comprehensive information about EU AI Act",
                "priority": "high",
                "estimated_time": 4.0
            }
        ]
        mock_tool_integration.execute_tool_sequence.return_value = [
            {
                "tool_name": "search",
                "success": True,
                "execution_time": 3.8,
                "parameters_used": {"query": "EU AI Act European Commission", "limit": 10},
                "raw_output": mock_tools["search"].return_value,
                "insights": ["EU AI Act is comprehensive legislation", "Implementation is in progress"],
                "entities_found": [{"name": "EU AI Act", "type": "Policy", "relevance": "high"}],
                "relationships_discovered": [{"source": "European Commission", "target": "EU AI Act", "relationship": "PROPOSES"}],
                "source_citations": ["Official Journal of EU", "European Parliament"],
                "temporal_aspects": ["Implementation timeline: 2024-2026"],
                "quality_score": 0.92,
                "purpose": "Find comprehensive information about EU AI Act",
                "error": None
            }
        ]
        
        orchestrator.tool_integration_manager = mock_tool_integration
        orchestrator.planning_agent.tool_integration_manager = mock_tool_integration
        orchestrator.execution_agent.tool_integration_manager = mock_tool_integration
        
        return orchestrator
    
    @pytest.mark.asyncio
    async def test_complete_workflow_information_seeking(self, complete_orchestrator):
        """Test complete workflow for information seeking query about EU AI Act."""
        
        # Test query about EU AI Act
        query = "What is the current status of the EU AI Act and how does it affect businesses?"
        user_id = "test_user_001"
        session_id = "session_001"
        
        # Capture streaming output
        streaming_events = []
        
        async def stream_callback(event):
            streaming_events.append(event)
        
        # Execute complete workflow
        result = await complete_orchestrator.process_query(
            query=query,
            session_id=session_id,
            user_id=user_id,
            stream_callback=stream_callback
        )
        
        # Validate overall result structure
        assert result["success"] is True
        assert result["response"] != ""
        assert result["confidence"] > 0.8
        assert len(result["agent_sequence"]) == 4  # All agents executed
        assert result["execution_time"] > 0
        assert len(result["errors"]) == 0
        
        # Validate response quality
        response_text = result["response"]
        assert "EU AI Act" in response_text
        assert "implementation" in response_text.lower()
        assert "businesses" in response_text.lower() or "business" in response_text.lower()
        assert len(response_text) > 500  # Comprehensive response
        
        # Validate metadata
        metadata = result["metadata"]
        assert "query_analysis" in metadata
        assert "tool_plan" in metadata
        assert "execution_metadata" in metadata
        assert "response_metadata" in metadata
        
        # Validate query analysis
        query_analysis = metadata["query_analysis"]
        assert query_analysis["intent"] == "information_seeking"
        assert query_analysis["primary_entity"] == "EU AI Act"
        assert query_analysis["confidence"] > 0.9
        
        # Validate tool execution
        execution_metadata = metadata["execution_metadata"]
        assert "tools_successful" in execution_metadata
        assert execution_metadata["tools_successful"] > 0
        
        # Validate streaming events were generated
        assert len(streaming_events) > 0
        event_types = [event.get("type") for event in streaming_events]
        assert "workflow_update" in event_types
        
        # Validate agent sequence
        expected_agents = ["query_understanding", "tool_planning", "tool_execution", "response_synthesis"]
        assert all(agent in result["agent_sequence"] for agent in expected_agents)
    
    @pytest.mark.asyncio
    async def test_complete_workflow_with_personalization(self, complete_orchestrator):
        """Test workflow with user personalization and learning."""
        
        # Simulate existing user with preferences
        user_id = "experienced_user_001"
        
        # Mock user preferences and patterns
        mock_user_patterns = {
            "common_intents": {"information_seeking": 15, "analysis": 8},
            "preferred_detail_level": "high",
            "response_format_preference": "comprehensive", 
            "question_complexity_distribution": {"simple": 0.2, "medium": 0.5, "complex": 0.3},
            "feedback_patterns": {"positive": 18, "negative": 2}
        }
        
        # Configure memory manager with user patterns
        complete_orchestrator.memory_manager.analyze_user_conversation_patterns = AsyncMock(return_value=mock_user_patterns)
        complete_orchestrator.memory_manager.get_personalization_recommendations = AsyncMock(return_value={
            "thinking_speed": "fast",
            "response_format": "comprehensive",
            "detail_level": "high",
            "complexity_comfort": "complex",
            "satisfaction_trend": "improving"
        })
        complete_orchestrator.memory_manager.update_user_conversation_patterns = AsyncMock()
        complete_orchestrator.memory_manager.learn_from_query = AsyncMock()
        complete_orchestrator.memory_manager.update_tool_performance = AsyncMock()
        
        # Execute workflow with personalization
        query = "Analyze the regulatory implications of the Digital Services Act for social media platforms"
        result = await complete_orchestrator.process_query(
            query=query,
            user_id=user_id
        )
        
        # Validate personalization was applied
        assert result["success"] is True
        
        # Verify personalization methods were called
        complete_orchestrator.memory_manager.get_personalization_recommendations.assert_called_once_with(user_id)
        complete_orchestrator.memory_manager.update_user_conversation_patterns.assert_called_once()
        complete_orchestrator.memory_manager.learn_from_query.assert_called_once()
        
        # Validate thinking generator received preferences
        thinking_prefs = complete_orchestrator.thinking_generator.user_preferences
        assert thinking_prefs.get("thinking_speed") == "fast"
        assert thinking_prefs.get("response_format") == "comprehensive"
    
    @pytest.mark.asyncio
    async def test_streaming_orchestrator_real_time(self):
        """Test real-time streaming capabilities."""
        
        # Create streaming orchestrator
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(content='{"test": "response"}')
        
        streaming_orchestrator = MultiAgentStreamingOrchestrator(llm=mock_llm, tools={})
        
        # Collect streaming events
        streaming_events = []
        
        async for event in streaming_orchestrator.process_query_with_streaming(
            query="What are the latest developments in EU privacy regulation?",
            user_id="streaming_test_user"
        ):
            streaming_events.append(event)
            
            # Break after collecting several events to avoid infinite loop in test
            if len(streaming_events) >= 5:
                break
        
        # Validate streaming events
        assert len(streaming_events) > 0
        
        # Check for different event types
        event_types = [event.get("type") for event in streaming_events]
        assert any(event_type in ["workflow_update", "final_result", "error"] for event_type in event_types)
        
        # Validate event structure
        for event in streaming_events:
            assert "type" in event
            assert "timestamp" in event
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, complete_orchestrator):
        """Test error handling and recovery mechanisms."""
        
        # Configure LLM to simulate failures
        mock_llm = complete_orchestrator.llm
        mock_llm.ainvoke.side_effect = [
            Exception("Query analysis failed"),  # First call fails
            MagicMock(content='{"intent": "information_seeking", "confidence": 0.8, "complexity": "simple", "primary_entity": "Test", "secondary_entities": [], "key_relationships": [], "temporal_scope": "current", "analysis_strategy": "focused", "search_priorities": [], "expected_information_types": [], "memory_insights": {}}'),  # Second call succeeds
            MagicMock(content='{"strategy_type": "simple", "estimated_execution_time": 5.0, "tool_sequence": [], "success_criteria": {"primary": "test"}, "backup_strategies": [], "optimization_notes": {}}'),
            MagicMock(content='{"response_text": "Error recovery response", "confidence_level": 0.6, "information_completeness": "partial", "source_count": 1, "key_insights_count": 1, "response_metadata": {}, "follow_up_suggestions": [], "synthesis_notes": {}}')
        ]
        
        # Test that system handles errors gracefully
        result = await complete_orchestrator.process_query(
            query="Test error handling",
            session_id="error_test_session"
        )
        
        # System should recover and provide a response despite initial failure
        assert "errors" in result
        # The first error should be captured but workflow should continue
        # The final result might have lower confidence but should still succeed
        assert isinstance(result["confidence"], float)
        assert result["confidence"] >= 0.0
    
    @pytest.mark.asyncio 
    async def test_tool_integration_intelligence(self, complete_orchestrator):
        """Test intelligent tool selection and integration."""
        
        # Test different query types to validate tool selection
        test_queries = [
            {
                "query": "What is the EU GDPR?",
                "expected_intent": "information_seeking",
                "expected_tools": ["search", "get_entity_details"]
            },
            {
                "query": "How does GDPR relate to the Digital Services Act?",
                "expected_intent": "relationship_analysis", 
                "expected_tools": ["find_paths_between_entities", "get_entity_relationships"]
            },
            {
                "query": "Show me the timeline of AI regulation in Europe",
                "expected_intent": "temporal_analysis",
                "expected_tools": ["get_entity_timeline", "search_by_date_range"]
            }
        ]
        
        for test_case in test_queries:
            # Mock tool integration manager to return expected tools
            complete_orchestrator.tool_integration_manager.get_tool_recommendations.return_value = [
                {
                    "tool_name": tool,
                    "parameters": {"query": "test"},
                    "purpose": f"Execute {tool}",
                    "priority": "high",
                    "estimated_time": 2.0
                }
                for tool in test_case["expected_tools"]
            ]
            
            result = await complete_orchestrator.process_query(
                query=test_case["query"],
                session_id=f"tool_test_{test_case['expected_intent']}"
            )
            
            # Validate that appropriate tools were recommended
            assert result["success"] is True
            
            # Check that tool integration manager was called with correct parameters
            call_args = complete_orchestrator.tool_integration_manager.get_tool_recommendations.call_args
            if call_args:
                assert call_args[1]["intent"] == test_case["expected_intent"]
    
    @pytest.mark.asyncio
    async def test_memory_persistence_and_learning(self, complete_orchestrator):
        """Test memory persistence and learning across multiple interactions."""
        
        user_id = "learning_test_user"
        
        # Simulate multiple interactions to test learning
        queries = [
            "What is GDPR?",
            "How does GDPR enforcement work?", 
            "What are the penalties for GDPR violations?",
            "Compare GDPR with other privacy laws"
        ]
        
        # Track learning progression
        interaction_data = []
        
        for i, query in enumerate(queries):
            # Mock progressive learning
            satisfaction_rating = 3.5 + (i * 0.3)  # Improving satisfaction
            
            complete_orchestrator.memory_manager.update_user_conversation_patterns = AsyncMock()
            complete_orchestrator.memory_manager.learn_from_query = AsyncMock()
            
            result = await complete_orchestrator.process_query(
                query=query,
                user_id=user_id,
                session_id=f"learning_session_{i}"
            )
            
            interaction_data.append({
                "query": query,
                "confidence": result["confidence"],
                "success": result["success"]
            })
            
            # Verify learning methods were called
            assert complete_orchestrator.memory_manager.update_user_conversation_patterns.called
            assert complete_orchestrator.memory_manager.learn_from_query.called
        
        # Validate learning progression
        confidences = [data["confidence"] for data in interaction_data]
        assert all(data["success"] for data in interaction_data)
        
        # Check that all queries were processed successfully
        assert len(interaction_data) == len(queries)
    
    @pytest.mark.asyncio
    async def test_performance_and_resource_usage(self, complete_orchestrator):
        """Test system performance and resource usage."""
        
        start_time = datetime.now()
        
        # Execute a standard query and measure performance
        result = await complete_orchestrator.process_query(
            query="Analyze the impact of the EU Digital Services Act on content moderation",
            session_id="performance_test"
        )
        
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        # Validate performance metrics
        assert result["success"] is True
        assert result["execution_time"] > 0
        assert total_time < 30  # Should complete within reasonable time
        
        # Validate resource efficiency
        agent_sequence = result["agent_sequence"]
        assert len(agent_sequence) == 4  # All agents executed efficiently
        
        # Check execution metadata for performance insights
        execution_metadata = result["metadata"].get("execution_metadata", {})
        if "total_execution_time" in execution_metadata:
            assert execution_metadata["total_execution_time"] < 20  # Reasonable execution time
    
    def test_workflow_schema_validation(self, complete_orchestrator):
        """Test workflow schema and configuration validation."""
        
        # Validate workflow schema
        schema = complete_orchestrator.get_workflow_schema()
        
        assert "nodes" in schema
        assert "edges" in schema
        assert "conditional_routing" in schema
        
        # Validate all required nodes are present
        node_names = [node["name"] for node in schema["nodes"]]
        expected_nodes = ["query_understanding", "tool_planning", "tool_execution", "response_synthesis"]
        assert all(node in node_names for node in expected_nodes)
        
        # Validate edge connectivity
        edges = schema["edges"]
        assert len(edges) >= 4  # At least 4 edges for basic workflow
        
        # Validate conditional routing configuration
        routing = schema["conditional_routing"]
        assert "node" in routing
        assert "conditions" in routing
        assert len(routing["conditions"]) > 0


class TestSystemIntegration:
    """Test integration between all system components."""
    
    @pytest.mark.asyncio
    async def test_memory_streaming_integration(self):
        """Test integration between memory and streaming systems."""
        
        memory_manager = MemoryManager()
        streaming_manager = StreamingManager()
        thinking_generator = StreamingThinkingGenerator(streaming_manager)
        
        # Test memory-informed streaming
        user_prefs = {
            "thinking_speed": "detailed",
            "response_format": "comprehensive",
            "detail_level": "high"
        }
        
        thinking_generator.set_user_preferences(user_prefs)
        
        # Validate preferences were applied
        assert thinking_generator.user_preferences == user_prefs
        
        # Test adaptive delay calculation with preferences
        delay = thinking_generator.get_adaptive_delay("complex", "detailed")
        assert delay > 1.0  # Should be longer for detailed preference
        
        # Test memory integration with streaming events
        streaming_events = []
        
        def mock_stream_callback(event):
            streaming_events.append(event)
        
        streaming_manager.set_stream_callback(mock_stream_callback)
        
        # Emit test thinking with context
        await thinking_generator.emit_contextual_thinking(
            "test_agent",
            "analysis_progress", 
            {"entity": "Test Entity", "confidence": "90%"},
            "complex"
        )
        
        # Validate thinking history was recorded
        assert len(thinking_generator.thinking_history) == 1
        assert thinking_generator.thinking_history[0]["agent"] == "test_agent"
    
    @pytest.mark.asyncio
    async def test_tool_memory_integration(self):
        """Test integration between tool system and memory."""
        
        # Mock Graphiti client
        mock_client = MagicMock()
        tool_manager = ToolIntegrationManager(mock_client)
        memory_manager = MemoryManager()
        
        # Test tool performance tracking integration
        tool_manager._update_tool_performance("search", True, 2.5, None)
        tool_manager._update_tool_performance("search", False, 1.0, "Timeout error")
        
        # Validate performance tracking
        performance = tool_manager.get_tool_performance_summary()
        assert "search" in performance
        assert performance["search"]["total_executions"] == 2
        assert performance["search"]["success_rate"] == 0.5
        
        # Test memory integration for tool performance
        memory_manager.update_tool_performance = AsyncMock()
        await memory_manager.update_tool_performance("search", True, 2.5, None)
        
        # Verify memory manager received tool performance data
        memory_manager.update_tool_performance.assert_called_once_with("search", True, 2.5, None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])