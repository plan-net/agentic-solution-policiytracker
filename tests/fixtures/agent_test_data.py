"""Test fixtures and realistic data for multi-agent system testing."""

import pytest
from typing import Dict, List, Any
from datetime import datetime, timedelta
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from src.chat.agent.base import AgentRole, MultiAgentState
from tests.mocks.knowledge_graph_tools import MockKnowledgeGraphTools
from tests.mocks.memory_components import MockMemoryManager, MockStreamingManager


class AgentTestDataFixtures:
    """Comprehensive test data fixtures for agent testing."""
    
    @staticmethod
    def get_sample_queries() -> Dict[str, Dict[str, Any]]:
        """Get sample user queries with expected analysis results."""
        return {
            "simple_information_seeking": {
                "query": "What is the EU AI Act?",
                "expected_intent": "information_seeking",
                "expected_complexity": "simple",
                "expected_entities": ["EU AI Act", "European Union"],
                "expected_strategy": "focused"
            },
            "enforcement_tracking": {
                "query": "What enforcement actions has the EU taken against Meta this year?",
                "expected_intent": "enforcement_tracking", 
                "expected_complexity": "medium",
                "expected_entities": ["Meta", "European Union", "enforcement"],
                "expected_strategy": "comprehensive"
            },
            "complex_compliance": {
                "query": "How do GDPR, DSA, and the AI Act interact for social media platforms operating in multiple jurisdictions?",
                "expected_intent": "compliance_research",
                "expected_complexity": "complex",
                "expected_entities": ["GDPR", "Digital Services Act", "EU AI Act", "social media", "jurisdiction"],
                "expected_strategy": "comprehensive"
            },
            "temporal_analysis": {
                "query": "How has EU privacy regulation evolved from GDPR to the AI Act?",
                "expected_intent": "temporal_analysis",
                "expected_complexity": "medium", 
                "expected_entities": ["GDPR", "EU AI Act", "privacy", "regulation"],
                "expected_strategy": "temporal"
            },
            "comparative_analysis": {
                "query": "Compare US and EU approaches to AI regulation",
                "expected_intent": "comparative_analysis",
                "expected_complexity": "complex",
                "expected_entities": ["United States", "European Union", "AI regulation"],
                "expected_strategy": "comprehensive"
            }
        }
    
    @staticmethod
    def get_sample_query_analyses() -> Dict[str, Dict[str, Any]]:
        """Get sample query analysis results from Query Understanding Agent."""
        return {
            "simple_analysis": {
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
                "expected_information_types": [
                    "regulatory_framework",
                    "policy_details",
                    "implementation_timeline"
                ],
                "memory_insights": {
                    "user_pattern_match": "regulatory_information_seeking",
                    "preference_alignment": "high_detail_legal_focus",
                    "context_relevance": "new_topic_exploration"
                }
            },
            "complex_analysis": {
                "intent": "compliance_research",
                "confidence": 0.88,
                "complexity": "complex",
                "primary_entity": "GDPR",
                "secondary_entities": ["Digital Services Act", "EU AI Act", "Meta", "social media platforms"],
                "key_relationships": ["REGULATES", "AFFECTS", "REQUIRES_COMPLIANCE"],
                "temporal_scope": "current",
                "analysis_strategy": "comprehensive",
                "search_priorities": [
                    {
                        "entity": "GDPR", 
                        "priority": "high",
                        "reasoning": "Foundational regulation affecting all others"
                    },
                    {
                        "entity": "Meta",
                        "priority": "high", 
                        "reasoning": "Specific company example for compliance"
                    },
                    {
                        "entity": "Digital Services Act",
                        "priority": "medium",
                        "reasoning": "Related regulation with overlapping scope"
                    }
                ],
                "expected_information_types": [
                    "compliance_requirements",
                    "regulatory_interactions", 
                    "enforcement_precedents",
                    "implementation_challenges"
                ],
                "memory_insights": {
                    "user_pattern_match": "compliance_research_pattern",
                    "preference_alignment": "detailed_multi_jurisdictional",
                    "context_relevance": "follows_previous_enforcement_questions"
                }
            }
        }
    
    @staticmethod
    def get_sample_tool_plans() -> Dict[str, Dict[str, Any]]:
        """Get sample tool execution plans from Tool Planning Agent."""
        return {
            "focused_plan": {
                "strategy_type": "focused",
                "estimated_execution_time": 25,
                "tool_sequence": [
                    {
                        "step": 1,
                        "tool_name": "entity_lookup",
                        "parameters": {"entity_name": "EU AI Act"},
                        "purpose": "Get comprehensive information about the primary entity",
                        "expected_insights": "Regulatory framework details, status, key provisions",
                        "estimated_time": 5,
                        "dependency": None
                    },
                    {
                        "step": 2,
                        "tool_name": "get_entity_neighbors",
                        "parameters": {"entity_name": "EU AI Act", "relationship_types": ["AUTHORED_BY", "ENFORCES"]},
                        "purpose": "Find related regulatory authorities and enforcement mechanisms",
                        "expected_insights": "Regulatory bodies, implementation timeline",
                        "estimated_time": 8,
                        "dependency": "step_1"
                    },
                    {
                        "step": 3,
                        "tool_name": "search",
                        "parameters": {"query": "EU AI Act implementation requirements", "limit": 10},
                        "purpose": "Find specific implementation and compliance details",
                        "expected_insights": "Practical compliance requirements, deadlines",
                        "estimated_time": 12,
                        "dependency": "step_2"
                    }
                ],
                "success_criteria": {
                    "primary": "Complete overview of EU AI Act with implementation details",
                    "secondary": "Related regulatory context and enforcement information",
                    "minimum_threshold": "Basic regulation description with key facts"
                },
                "backup_strategies": [
                    {
                        "trigger_condition": "entity_lookup fails",
                        "alternative_tools": ["search", "temporal_query"],
                        "modified_approach": "Use broader search to establish context first"
                    }
                ],
                "optimization_notes": {
                    "parallel_opportunities": "steps 2 and 3 can run in parallel after step 1",
                    "performance_priorities": "prioritize accuracy over speed for regulatory information",
                    "user_preference_alignment": "matches user preference for detailed regulatory analysis"
                }
            },
            "comprehensive_plan": {
                "strategy_type": "comprehensive",
                "estimated_execution_time": 45,
                "tool_sequence": [
                    {
                        "step": 1,
                        "tool_name": "search",
                        "parameters": {"query": "GDPR Digital Services Act AI Act compliance interaction", "limit": 15},
                        "purpose": "Establish broad regulatory landscape",
                        "expected_insights": "Overview of regulatory interactions and overlaps",
                        "estimated_time": 10,
                        "dependency": None
                    },
                    {
                        "step": 2,
                        "tool_name": "entity_lookup",
                        "parameters": {"entity_name": "Meta"},
                        "purpose": "Get detailed information about the target company",
                        "expected_insights": "Company profile, regulatory history, compliance status",
                        "estimated_time": 6,
                        "dependency": None
                    },
                    {
                        "step": 3,
                        "tool_name": "relationship_analysis",
                        "parameters": {"entity1": "GDPR", "entity2": "Meta"},
                        "purpose": "Analyze specific compliance relationship",
                        "expected_insights": "GDPR compliance requirements for Meta",
                        "estimated_time": 8,
                        "dependency": "step_2"
                    },
                    {
                        "step": 4,
                        "tool_name": "find_paths_between_entities",
                        "parameters": {"entity1": "Meta", "entity2": "EU AI Act", "max_path_length": 3},
                        "purpose": "Discover regulatory pathways and connections",
                        "expected_insights": "How AI Act affects Meta through various regulatory channels",
                        "estimated_time": 12,
                        "dependency": "step_3"
                    },
                    {
                        "step": 5,
                        "tool_name": "temporal_query",
                        "parameters": {"entity": "Meta", "time_range": ("2024-01-01", "2024-12-31")},
                        "purpose": "Track recent regulatory developments",
                        "expected_insights": "Recent enforcement actions, compliance updates",
                        "estimated_time": 9,
                        "dependency": "step_4"
                    }
                ],
                "success_criteria": {
                    "primary": "Comprehensive multi-regulation compliance analysis with specific company examples",
                    "secondary": "Temporal context and regulatory evolution understanding",
                    "minimum_threshold": "Basic understanding of how multiple regulations interact"
                },
                "backup_strategies": [
                    {
                        "trigger_condition": "relationship_analysis returns insufficient data",
                        "alternative_tools": ["traverse_from_entity", "get_communities"],
                        "modified_approach": "Use network traversal to find indirect relationships"
                    },
                    {
                        "trigger_condition": "temporal_query fails",
                        "alternative_tools": ["search_by_date_range"],
                        "modified_approach": "Use date-scoped search instead of entity-focused temporal query"
                    }
                ],
                "optimization_notes": {
                    "parallel_opportunities": "steps 1 and 2 can run in parallel, then 3-5 sequentially",
                    "performance_priorities": "balance thoroughness with execution time",
                    "user_preference_alignment": "comprehensive analysis matches user's complex query needs"
                }
            }
        }
    
    @staticmethod
    def get_sample_tool_results() -> Dict[str, List[Dict[str, Any]]]:
        """Get sample tool execution results."""
        return {
            "successful_results": [
                {
                    "tool_name": "entity_lookup",
                    "success": True,
                    "execution_time": 0.05,
                    "parameters_used": {"entity_name": "EU AI Act"},
                    "output": "Found comprehensive entity information",
                    "insights": [
                        "EU AI Act is a comprehensive regulation addressing AI system risks",
                        "Applies risk-based approach with different requirements for different AI systems",
                        "Enforced by European Commission with national competent authorities"
                    ],
                    "entities_found": [
                        {"name": "EU AI Act", "type": "Policy", "relevance": "high"},
                        {"name": "European Commission", "type": "Organization", "relevance": "high"}
                    ],
                    "relationships_discovered": [
                        {
                            "source": "European Commission",
                            "target": "EU AI Act",
                            "relationship": "AUTHORED",
                            "context": "Proposed and developed the regulation"
                        }
                    ],
                    "source_citations": [
                        "Official EU AI Act text (Regulation 2024/1689)",
                        "European Commission press release AI-2024-03"
                    ],
                    "temporal_aspects": [
                        "Entered into force: August 1, 2024",
                        "Full application: August 2, 2026"
                    ],
                    "quality_score": 0.95,
                    "error": None
                },
                {
                    "tool_name": "search",
                    "success": True,
                    "execution_time": 0.12,
                    "parameters_used": {"query": "GDPR enforcement Meta fines", "limit": 10},
                    "output": "Found multiple enforcement actions",
                    "insights": [
                        "Meta received €390M fine for GDPR violations in 2023",
                        "Issues included forced consent and data processing transparency",
                        "Irish DPA led investigation with European Data Protection Board oversight"
                    ],
                    "entities_found": [
                        {"name": "Meta", "type": "Company", "relevance": "high"},
                        {"name": "Irish DPA", "type": "Organization", "relevance": "high"},
                        {"name": "GDPR", "type": "Policy", "relevance": "high"}
                    ],
                    "relationships_discovered": [
                        {
                            "source": "Irish DPA",
                            "target": "Meta",
                            "relationship": "FINED",
                            "context": "€390M fine for GDPR violations"
                        }
                    ],
                    "source_citations": [
                        "Irish DPC decision IN-18-5-5 (January 2023)",
                        "EDPB binding decision 01/2023"
                    ],
                    "temporal_aspects": [
                        "Investigation started: May 2018",
                        "Final decision: January 4, 2023"
                    ],
                    "quality_score": 0.92,
                    "error": None
                }
            ],
            "failed_results": [
                {
                    "tool_name": "entity_lookup",
                    "success": False,
                    "execution_time": 0.03,
                    "parameters_used": {"entity_name": "Nonexistent Regulation"},
                    "output": "",
                    "insights": [],
                    "entities_found": [],
                    "relationships_discovered": [],
                    "source_citations": [],
                    "temporal_aspects": [],
                    "quality_score": 0.0,
                    "error": "Entity 'Nonexistent Regulation' not found in knowledge graph"
                }
            ]
        }
    
    @staticmethod
    def get_sample_memory_data() -> Dict[str, Dict[str, Any]]:
        """Get sample memory context data."""
        return {
            "experienced_user": {
                "user_preferences": {
                    "detail_level": "high",
                    "response_format": "structured",
                    "citation_style": "academic",
                    "preferred_jurisdictions": ["EU", "US"],
                    "notification_preferences": {
                        "enforcement_actions": True,
                        "policy_updates": True,
                        "compliance_deadlines": True
                    }
                },
                "conversation_history": [
                    HumanMessage(content="What are the latest GDPR enforcement actions?"),
                    AIMessage(content="Recent GDPR enforcement includes several significant fines..."),
                    HumanMessage(content="How does this affect social media companies specifically?"),
                    AIMessage(content="Social media companies face particular challenges under GDPR...")
                ],
                "learned_patterns": {
                    "query_patterns": [
                        {
                            "pattern": "enforcement_focus",
                            "confidence": 0.89,
                            "examples": ["enforcement", "fines", "violations", "penalties"]
                        },
                        {
                            "pattern": "cross_jurisdictional_interest",
                            "confidence": 0.82,
                            "examples": ["EU vs US", "international", "cross-border"]
                        }
                    ],
                    "entity_preferences": [
                        {"entity": "GDPR", "interest_score": 0.95},
                        {"entity": "Meta", "interest_score": 0.87},
                        {"entity": "Digital Services Act", "interest_score": 0.78}
                    ]
                },
                "tool_performance_history": {
                    "search": {"success_rate": 0.94, "avg_time": 0.12},
                    "entity_lookup": {"success_rate": 0.98, "avg_time": 0.05},
                    "relationship_analysis": {"success_rate": 0.89, "avg_time": 0.08}
                }
            },
            "new_user": {
                "user_preferences": {
                    "detail_level": "medium",
                    "response_format": "conversational",
                    "citation_style": "simple"
                },
                "conversation_history": [],
                "learned_patterns": {},
                "tool_performance_history": {}
            }
        }
    
    @staticmethod
    def get_sample_multi_agent_states() -> Dict[str, MultiAgentState]:
        """Get sample MultiAgentState instances for testing."""
        return {
            "initial_state": MultiAgentState(
                original_query="What is the EU AI Act?",
                current_agent="query_understanding",
                session_id="test_session_123",
                is_streaming=True
            ),
            "query_analyzed_state": MultiAgentState(
                original_query="What is the EU AI Act?",
                processed_query="What is the EU AI Act?",
                query_analysis={
                    "intent": "information_seeking",
                    "complexity": "simple",
                    "primary_entity": "EU AI Act",
                    "confidence": 0.95
                },
                current_agent="tool_planning",
                agent_sequence=["query_understanding"],
                session_id="test_session_123",
                is_streaming=True
            ),
            "planning_complete_state": MultiAgentState(
                original_query="What is the EU AI Act?",
                processed_query="What is the EU AI Act?",
                query_analysis={
                    "intent": "information_seeking", 
                    "complexity": "simple",
                    "primary_entity": "EU AI Act",
                    "confidence": 0.95
                },
                tool_plan={
                    "strategy_type": "focused",
                    "tool_sequence": ["entity_lookup", "search"],
                    "estimated_execution_time": 20
                },
                current_agent="tool_execution",
                agent_sequence=["query_understanding", "tool_planning"],
                session_id="test_session_123",
                is_streaming=True
            ),
            "execution_complete_state": MultiAgentState(
                original_query="What is the EU AI Act?",
                processed_query="What is the EU AI Act?",
                query_analysis={
                    "intent": "information_seeking",
                    "complexity": "simple", 
                    "primary_entity": "EU AI Act",
                    "confidence": 0.95
                },
                tool_plan={
                    "strategy_type": "focused",
                    "tool_sequence": ["entity_lookup", "search"],
                    "estimated_execution_time": 20
                },
                executed_tools=["entity_lookup", "search"],
                tool_results=[
                    {
                        "tool_name": "entity_lookup",
                        "success": True,
                        "insights": ["EU AI Act regulatory framework details"]
                    },
                    {
                        "tool_name": "search", 
                        "success": True,
                        "insights": ["Implementation requirements and timeline"]
                    }
                ],
                current_agent="response_synthesis",
                agent_sequence=["query_understanding", "tool_planning", "tool_execution"],
                session_id="test_session_123",
                is_streaming=True,
                execution_metadata={
                    "total_execution_time": 18.5,
                    "tools_successful": 2,
                    "information_quality": "high"
                }
            )
        }


# Pytest fixtures

@pytest.fixture
def sample_queries():
    """Pytest fixture for sample queries."""
    return AgentTestDataFixtures.get_sample_queries()

@pytest.fixture
def sample_query_analyses():
    """Pytest fixture for sample query analyses."""
    return AgentTestDataFixtures.get_sample_query_analyses()

@pytest.fixture
def sample_tool_plans():
    """Pytest fixture for sample tool plans."""
    return AgentTestDataFixtures.get_sample_tool_plans()

@pytest.fixture
def sample_tool_results():
    """Pytest fixture for sample tool results."""
    return AgentTestDataFixtures.get_sample_tool_results()

@pytest.fixture
def sample_memory_data():
    """Pytest fixture for sample memory data."""
    return AgentTestDataFixtures.get_sample_memory_data()

@pytest.fixture
def sample_multi_agent_states():
    """Pytest fixture for sample MultiAgentState instances."""
    return AgentTestDataFixtures.get_sample_multi_agent_states()

@pytest.fixture
def mock_kg_tools():
    """Pytest fixture for mock knowledge graph tools."""
    tools = MockKnowledgeGraphTools()
    tools.reset_call_history()
    return tools

@pytest.fixture
def mock_memory_manager():
    """Pytest fixture for mock memory manager."""
    manager = MockMemoryManager()
    manager.reset_call_history()
    return manager

@pytest.fixture
def mock_streaming_manager():
    """Pytest fixture for mock streaming manager."""
    manager = MockStreamingManager()
    manager.clear_events()
    return manager

@pytest.fixture
def mock_stream_writer():
    """Pytest fixture for mock stream writer."""
    from unittest.mock import AsyncMock
    return AsyncMock()


class AgentTestHelpers:
    """Helper methods for agent testing."""
    
    @staticmethod
    def assert_valid_query_analysis(result: Dict[str, Any]) -> None:
        """Assert that a query analysis result is valid."""
        required_fields = [
            "intent", "confidence", "complexity", "primary_entity",
            "secondary_entities", "key_relationships", "temporal_scope",
            "analysis_strategy", "search_priorities", "expected_information_types"
        ]
        
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
        
        assert isinstance(result["confidence"], (int, float))
        assert 0.0 <= result["confidence"] <= 1.0
        assert result["complexity"] in ["simple", "medium", "complex"]
        assert isinstance(result["secondary_entities"], list)
        assert isinstance(result["search_priorities"], list)
    
    @staticmethod
    def assert_valid_tool_plan(result: Dict[str, Any]) -> None:
        """Assert that a tool plan is valid."""
        required_fields = [
            "strategy_type", "estimated_execution_time", "tool_sequence",
            "success_criteria", "backup_strategies", "optimization_notes"
        ]
        
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
        
        assert result["strategy_type"] in ["focused", "comprehensive", "temporal", "network", "comparative"]
        assert isinstance(result["estimated_execution_time"], (int, float))
        assert isinstance(result["tool_sequence"], list)
        assert len(result["tool_sequence"]) > 0
        
        # Validate tool sequence structure
        for step in result["tool_sequence"]:
            assert "step" in step
            assert "tool_name" in step
            assert "parameters" in step
            assert "purpose" in step
    
    @staticmethod
    def assert_valid_tool_result(result: Dict[str, Any]) -> None:
        """Assert that a tool result is valid."""
        required_fields = [
            "tool_name", "success", "execution_time", "parameters_used",
            "output", "insights", "entities_found", "relationships_discovered",
            "source_citations", "quality_score"
        ]
        
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
        
        assert isinstance(result["success"], bool)
        assert isinstance(result["execution_time"], (int, float))
        assert isinstance(result["insights"], list)
        assert isinstance(result["entities_found"], list)
        assert isinstance(result["relationships_discovered"], list)
        assert 0.0 <= result["quality_score"] <= 1.0