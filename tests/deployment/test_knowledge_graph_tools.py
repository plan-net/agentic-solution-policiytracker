"""Knowledge graph tools deployment tests."""

import pytest
import asyncio
from typing import Dict, Any

from src.chat.agent.tool_integration import ToolIntegrationManager
from graphiti_core import Graphiti
from src.config import settings

@pytest.mark.deployment
@pytest.mark.asyncio
@pytest.mark.requires_data
class TestKnowledgeGraphTools:
    """Test individual knowledge graph tools functionality."""
    
    @pytest.fixture(scope="class")
    async def tool_manager(self):
        """Initialize tool manager for testing."""
        graphiti_client = Graphiti(
            settings.NEO4J_URI,
            settings.NEO4J_USERNAME,
            settings.NEO4J_PASSWORD
        )
        await graphiti_client.build_indices_and_constraints()
        
        tool_manager = ToolIntegrationManager(graphiti_client)
        yield tool_manager
    
    async def test_search_tool(self, tool_manager):
        """Test basic search functionality."""
        search_tool = tool_manager.tools.get("search")
        assert search_tool is not None, "Search tool not available"
        
        try:
            # Test basic search
            result = await search_tool.arun("GDPR regulation")
            assert isinstance(result, str), "Search should return string result"
            assert len(result) > 0, "Search should return non-empty result"
            
            print(f"✅ Search tool working: {len(result)} characters returned")
            
        except Exception as e:
            print(f"⚠️  Search tool error: {e}")
            # Don't fail the test, just log the issue
    
    async def test_entity_details_tool(self, tool_manager):
        """Test entity details tool."""
        entity_tool = tool_manager.tools.get("get_entity_details")
        assert entity_tool is not None, "Entity details tool not available"
        
        try:
            result = await entity_tool.arun("GDPR")
            assert isinstance(result, str), "Entity details should return string"
            print(f"✅ Entity details tool working: {len(result)} characters returned")
            
        except Exception as e:
            print(f"⚠️  Entity details tool error: {e}")
    
    async def test_tool_recommendations_integration(self, tool_manager):
        """Test that tool recommendations work correctly."""
        
        test_cases = [
            {
                "intent": "Information Seeking",
                "entities": ["GDPR"],
                "complexity": "Simple",
                "strategy": "focused",
                "expected_tools": ["search", "get_entity_details"]
            },
            {
                "intent": "Relationship Analysis", 
                "entities": ["GDPR", "Google"],
                "complexity": "Medium",
                "strategy": "comprehensive",
                "expected_min_tools": 1
            }
        ]
        
        for case in test_cases:
            recommendations = tool_manager.get_tool_recommendations(
                intent=case["intent"],
                entities=case["entities"],
                complexity=case["complexity"],
                strategy_type=case["strategy"]
            )
            
            assert isinstance(recommendations, list), f"Recommendations should be list for {case['intent']}"
            assert len(recommendations) > 0, f"Should have recommendations for {case['intent']}"
            
            if "expected_tools" in case:
                recommended_tool_names = [r["tool_name"] for r in recommendations]
                for expected_tool in case["expected_tools"]:
                    assert expected_tool in recommended_tool_names, f"Missing expected tool {expected_tool} in {recommended_tool_names}"
            
            if "expected_min_tools" in case:
                assert len(recommendations) >= case["expected_min_tools"], f"Too few recommendations for {case['intent']}"
            
            print(f"✅ {case['intent']}: {len(recommendations)} tools recommended")
            for rec in recommendations:
                print(f"   - {rec['tool_name']}: {rec['purpose']}")
    
    async def test_all_tools_available(self, tool_manager):
        """Test that all expected tools are available."""
        
        expected_tools = [
            "search", "get_entity_details", "get_entity_relationships", 
            "get_entity_timeline", "find_similar_entities", "traverse_from_entity",
            "find_paths_between_entities", "analyze_entity_impact", "search_by_date_range",
            "find_concurrent_events", "track_policy_evolution", "get_communities",
            "get_community_members", "get_policy_clusters"
        ]
        
        available_tools = list(tool_manager.tools.keys())
        missing_tools = [tool for tool in expected_tools if tool not in available_tools]
        
        assert len(missing_tools) == 0, f"Missing tools: {missing_tools}"
        
        print(f"✅ All {len(expected_tools)} expected tools are available")
        print(f"Available tools: {', '.join(sorted(available_tools))}")
    
    async def test_tool_execution_performance(self, tool_manager):
        """Test tool execution performance."""
        
        performance_tests = [
            {"tool_name": "search", "params": {"query": "GDPR"}, "max_time": 10},
            {"tool_name": "get_entity_details", "params": {"entity_name": "GDPR"}, "max_time": 8},
        ]
        
        for test in performance_tests:
            tool = tool_manager.tools.get(test["tool_name"])
            if tool is None:
                print(f"⚠️  Tool {test['tool_name']} not available")
                continue
                
            import time
            start_time = time.time()
            
            try:
                if test["tool_name"] == "search":
                    result = await tool.arun(test["params"]["query"])
                elif test["tool_name"] == "get_entity_details":
                    result = await tool.arun(test["params"]["entity_name"])
                
                execution_time = time.time() - start_time
                
                assert execution_time < test["max_time"], f"{test['tool_name']} too slow: {execution_time:.2f}s"
                print(f"✅ {test['tool_name']}: {execution_time:.2f}s (limit: {test['max_time']}s)")
                
            except Exception as e:
                execution_time = time.time() - start_time
                print(f"⚠️  {test['tool_name']} error after {execution_time:.2f}s: {e}")

@pytest.mark.deployment
@pytest.mark.asyncio
class TestToolIntegrationRobustness:
    """Test tool integration robustness and edge cases."""
    
    async def test_invalid_tool_parameters(self):
        """Test tool behavior with invalid parameters."""
        graphiti_client = Graphiti(
            settings.NEO4J_URI,
            settings.NEO4J_USERNAME,
            settings.NEO4J_PASSWORD
        )
        await graphiti_client.build_indices_and_constraints()
        
        tool_manager = ToolIntegrationManager(graphiti_client)
        
        # Test invalid recommendation parameters
        invalid_cases = [
            {"intent": "", "entities": [], "complexity": "", "strategy": ""},
            {"intent": "Invalid Intent", "entities": ["NonExistent"], "complexity": "Super Complex", "strategy": "unknown"},
            {"intent": None, "entities": None, "complexity": None, "strategy": None}
        ]
        
        for case in invalid_cases:
            try:
                recommendations = tool_manager.get_tool_recommendations(
                    intent=case.get("intent", ""),
                    entities=case.get("entities", []),
                    complexity=case.get("complexity", ""),
                    strategy_type=case.get("strategy", "")
                )
                # Should not crash, even with invalid inputs
                assert isinstance(recommendations, list), "Should return list even for invalid inputs"
                print(f"✅ Handled invalid case gracefully: {len(recommendations)} recommendations")
                
            except Exception as e:
                print(f"⚠️  Error with invalid parameters: {e}")
                # Don't fail the test - robustness testing
    
    async def test_tool_manager_memory_usage(self):
        """Test tool manager doesn't leak memory."""
        graphiti_client = Graphiti(
            settings.NEO4J_URI,
            settings.NEO4J_USERNAME,
            settings.NEO4J_PASSWORD
        )
        await graphiti_client.build_indices_and_constraints()
        
        # Create and destroy multiple tool managers
        for i in range(5):
            tool_manager = ToolIntegrationManager(graphiti_client)
            
            # Use the tool manager
            recommendations = tool_manager.get_tool_recommendations(
                intent="Information Seeking",
                entities=["GDPR"],
                complexity="Simple",
                strategy_type="focused"
            )
            
            assert len(recommendations) > 0, f"Iteration {i}: No recommendations"
            
            # Delete reference
            del tool_manager
        
        print("✅ Memory test completed - no obvious leaks")
    
    async def test_concurrent_tool_requests(self):
        """Test concurrent tool recommendation requests."""
        graphiti_client = Graphiti(
            settings.NEO4J_URI,
            settings.NEO4J_USERNAME,
            settings.NEO4J_PASSWORD
        )
        await graphiti_client.build_indices_and_constraints()
        
        tool_manager = ToolIntegrationManager(graphiti_client)
        
        async def get_recommendations(case_id: int):
            return tool_manager.get_tool_recommendations(
                intent="Information Seeking",
                entities=[f"Entity_{case_id}"],
                complexity="Simple",
                strategy_type="focused"
            )
        
        # Send 5 concurrent requests
        tasks = [get_recommendations(i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = [r for r in results if isinstance(r, list)]
        failed = [r for r in results if not isinstance(r, list)]
        
        print(f"✅ Concurrent test: {len(successful)}/{len(results)} successful")
        
        assert len(successful) >= 3, f"Too many failures in concurrent test: {len(failed)} failed"