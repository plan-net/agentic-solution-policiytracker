"""
Phase 5 integration test for complete multi-agent system validation.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.chat.agent.orchestrator import MultiAgentOrchestrator
from src.chat.agent.production_config import DeploymentMode, ProductionConfig
from src.chat.agent.quality_assessment import ResponseQualityAssessment


class TestPhase5Integration:
    """Test Phase 5 complete integration."""

    @pytest.fixture
    def production_config(self):
        """Create production configuration for testing."""
        return ProductionConfig(DeploymentMode.DEVELOPMENT)

    @pytest.fixture
    def simple_orchestrator(self, production_config):
        """Create orchestrator with minimal mocking for integration test."""
        # Mock LLM with simple responses
        mock_llm = AsyncMock()

        # Query understanding response
        mock_llm.ainvoke.side_effect = [
            MagicMock(
                content='{"intent": "information_seeking", "confidence": 0.85, "complexity": "simple", "primary_entity": "Test Policy", "secondary_entities": ["EU", "regulation"], "key_relationships": ["REGULATES"], "temporal_scope": "current", "analysis_strategy": "focused", "search_priorities": [{"entity": "Test Policy", "reasoning": "primary focus"}], "expected_information_types": ["policy_details"], "memory_insights": {}}'
            ),
            MagicMock(
                content='{"strategy_type": "focused", "estimated_execution_time": 5.0, "tool_sequence": [{"tool_name": "search", "parameters": {"query": "Test Policy"}, "purpose": "Basic search", "priority": "high", "estimated_time": 2.0}], "success_criteria": {"primary": "Find policy information"}, "backup_strategies": [], "optimization_notes": {}}'
            ),
            MagicMock(
                content='{"response_text": "Test Policy is a comprehensive regulation that governs digital services in the European Union. The policy establishes clear requirements for platform operators and includes provisions for user safety, content moderation, and transparency reporting.", "confidence_level": 0.8, "information_completeness": "good", "source_count": 3, "key_insights_count": 5, "response_metadata": {"analysis_depth": "moderate"}, "follow_up_suggestions": [{"question": "What are the compliance requirements?", "reasoning": "Implementation guidance"}], "synthesis_notes": {"information_quality": "good"}}'
            ),
        ]

        # Mock tools
        mock_tools = {
            "search": AsyncMock(
                return_value={
                    "nodes": [{"name": "Test Policy", "type": "Policy"}],
                    "edges": [
                        {"source": "EU", "target": "Test Policy", "relationship": "PROPOSES"}
                    ],
                    "summary": "Found policy information",
                }
            )
        }

        orchestrator = MultiAgentOrchestrator(llm=mock_llm, tools=mock_tools)
        return orchestrator

    @pytest.mark.asyncio
    async def test_complete_phase5_workflow(self, simple_orchestrator, production_config):
        """Test complete Phase 5 workflow with all enhancements."""

        # Execute query with all Phase 1-5 features
        result = await simple_orchestrator.process_query(
            query="What is the Test Policy and how does it affect digital platforms?",
            session_id="phase5_test",
            user_id="integration_test_user",
        )

        # Validate basic workflow completion
        assert isinstance(result, dict)
        assert "success" in result
        assert "response" in result
        assert "confidence" in result
        assert "metadata" in result

        # Validate response content
        response = result["response"]
        assert isinstance(response, str)
        assert len(response) > 50  # Substantial response
        assert "Test Policy" in response

        # Validate metadata structure
        metadata = result["metadata"]
        assert "query_analysis" in metadata
        assert "tool_plan" in metadata
        assert "execution_metadata" in metadata
        assert "response_metadata" in metadata

        # Check if quality assessment was included
        if metadata.get("quality_metrics"):
            quality_metrics = metadata["quality_metrics"]
            assert "overall_score" in quality_metrics
            assert "dimension_scores" in quality_metrics
            assert "confidence_level" in quality_metrics

        print("✅ Phase 5 integration test passed!")
        print(f"Response length: {len(response)} characters")
        print(f"Confidence: {result['confidence']:.2f}")
        print(f"Agent sequence: {result.get('agent_sequence', [])}")

    @pytest.mark.asyncio
    async def test_quality_assessment_integration(self):
        """Test quality assessment system integration."""

        quality_assessor = ResponseQualityAssessment()

        # Test response
        response = """# EU Digital Services Act Analysis

The EU Digital Services Act (DSA) is comprehensive legislation that regulates digital platforms and services across the European Union.

## Key Provisions
- Content moderation requirements for large platforms
- Transparency obligations for algorithmic systems
- Risk assessment procedures for very large online platforms
- Enhanced user rights and remedies

## Implementation Timeline
The DSA became applicable in February 2024 for very large online platforms and will fully apply to all covered services by February 2025.

## Business Impact
Organizations operating digital services in the EU must assess their obligations under the DSA and implement appropriate compliance measures."""

        # Mock query analysis and tool results
        query_analysis = {
            "intent": "information_seeking",
            "complexity": "medium",
            "primary_entity": "EU Digital Services Act",
            "secondary_entities": ["digital platforms", "content moderation"],
            "expected_information_types": ["policy_details", "implementation_timeline"],
        }

        tool_results = [
            {
                "tool_name": "search",
                "success": True,
                "quality_score": 0.9,
                "insights": ["DSA applies to digital platforms", "Implementation is phased"],
                "source_citations": ["Official Journal of EU", "European Commission"],
            }
        ]

        execution_metadata = {"total_execution_time": 8.5, "tools_successful": 1, "tools_failed": 0}

        response_metadata = {"source_count": 2, "confidence_level": 0.85}

        # Assess quality
        quality_metrics = await quality_assessor.assess_response_quality(
            response=response,
            query="What is the EU Digital Services Act?",
            query_analysis=query_analysis,
            tool_results=tool_results,
            execution_metadata=execution_metadata,
            response_metadata=response_metadata,
        )

        # Validate quality assessment
        assert quality_metrics.overall_score > 0.6
        assert len(quality_metrics.dimension_scores) > 0
        assert quality_metrics.confidence_level > 0.5
        assert isinstance(quality_metrics.improvement_suggestions, list)
        assert isinstance(quality_metrics.quality_indicators, dict)

        print("✅ Quality assessment integration test passed!")
        print(f"Overall quality score: {quality_metrics.overall_score:.2f}")
        print(f"Assessment confidence: {quality_metrics.confidence_level:.2f}")
        print(f"Dimensions assessed: {len(quality_metrics.dimension_scores)}")

    def test_production_config_integration(self, production_config):
        """Test production configuration integration."""

        # Validate configuration structure
        assert production_config.deployment_mode == DeploymentMode.DEVELOPMENT
        assert hasattr(production_config, "resource_limits")
        assert hasattr(production_config, "quality_thresholds")
        assert hasattr(production_config, "monitoring_config")

        # Test configuration methods
        llm_config = production_config.get_llm_config()
        assert isinstance(llm_config, dict)
        assert "model" in llm_config

        memory_config = production_config.get_memory_config()
        assert isinstance(memory_config, dict)
        assert "max_conversation_tokens" in memory_config

        streaming_config = production_config.get_streaming_config()
        assert isinstance(streaming_config, dict)
        assert "enable_thinking_output" in streaming_config

        tool_config = production_config.get_tool_config()
        assert isinstance(tool_config, dict)
        assert "max_parallel_tools" in tool_config

        # Validate configuration
        validation = production_config.validate_configuration()
        assert isinstance(validation, dict)
        assert "valid" in validation
        assert "warnings" in validation
        assert "errors" in validation

        print("✅ Production config integration test passed!")
        print(f"Deployment mode: {production_config.deployment_mode.value}")
        print(f"Performance level: {production_config.performance_level.value}")
        print(f"Configuration valid: {validation['valid']}")

    @pytest.mark.asyncio
    async def test_system_component_integration(self):
        """Test integration between all system components."""

        # Test component initialization
        mock_llm = AsyncMock()
        orchestrator = MultiAgentOrchestrator(llm=mock_llm, tools={})

        # Validate all components are initialized
        assert orchestrator.memory_manager is not None
        assert orchestrator.streaming_manager is not None
        assert orchestrator.thinking_generator is not None
        assert orchestrator.quality_assessor is not None
        assert orchestrator.quality_optimizer is not None

        # Test component interactions
        assert orchestrator.thinking_generator.streaming_manager == orchestrator.streaming_manager
        assert orchestrator.quality_optimizer.assessor == orchestrator.quality_assessor

        # Test agent initialization
        assert orchestrator.query_agent is not None
        assert orchestrator.planning_agent is not None
        assert orchestrator.execution_agent is not None
        assert orchestrator.synthesis_agent is not None

        # Test workflow schema
        schema = orchestrator.get_workflow_schema()
        assert isinstance(schema, dict)
        assert "nodes" in schema
        assert "edges" in schema
        assert len(schema["nodes"]) == 4  # All agents present

        print("✅ System component integration test passed!")
        print("Components initialized: Memory, Streaming, Quality, Agents")
        print(f"Workflow nodes: {len(schema['nodes'])}")
        print(f"Workflow edges: {len(schema['edges'])}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
