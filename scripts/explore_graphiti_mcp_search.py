#!/usr/bin/env python3
"""
Explore Graphiti MCP Server Search Strategies

This script demonstrates different search approaches available through the Graphiti MCP server:
1. Basic semantic search
2. Temporal search with time ranges
3. Entity-centered search
4. Fact-based search
5. Node exploration
6. Advanced search with filters
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GraphitiMCPSearchExplorer:
    """Demonstrates different search strategies using Graphiti MCP server."""
    
    def __init__(self):
        # Note: In a real implementation, you'd connect to the MCP server here
        # For demonstration, we'll show the search patterns
        self.group_id = "test_custom_entities"
    
    async def demonstrate_search_strategies(self):
        """Run through different search strategies to show capabilities."""
        
        print("🔍 Graphiti MCP Server Search Strategy Demonstration")
        print("=" * 60)
        
        # Strategy 1: Basic Semantic Search
        await self._demo_basic_semantic_search()
        
        # Strategy 2: Temporal Search
        await self._demo_temporal_search()
        
        # Strategy 3: Entity-Centered Search
        await self._demo_entity_centered_search()
        
        # Strategy 4: Fact-Based Search
        await self._demo_fact_based_search()
        
        # Strategy 5: Node Exploration
        await self._demo_node_exploration()
        
        # Strategy 6: Advanced Search with Filters
        await self._demo_advanced_search()
        
        print("\n🎯 Search Strategy Summary")
        print("-" * 30)
        self._print_search_strategy_summary()

    async def _demo_basic_semantic_search(self):
        """Demonstrate basic semantic search capabilities."""
        print("\n1️⃣  **BASIC SEMANTIC SEARCH**")
        print("-" * 40)
        
        search_queries = [
            "Apple AI Act compliance",
            "European Union artificial intelligence regulation",
            "data protection requirements",
            "governance framework Singapore",
            "compliance reporting obligations"
        ]
        
        for query in search_queries:
            print(f"\n🔎 Query: '{query}'")
            
            # MCP call would be:
            mcp_call = {
                "method": "search_memory_facts",
                "params": {
                    "query": query,
                    "group_ids": [self.group_id],
                    "max_facts": 5
                }
            }
            
            print(f"   📡 MCP Call: {json.dumps(mcp_call, indent=6)}")
            print(f"   💡 Use Case: Find facts related to '{query}' across all documents")
            print(f"   🎯 Expected Results: Top 5 most relevant facts/relationships")
    
    async def _demo_temporal_search(self):
        """Demonstrate temporal search with time ranges."""
        print("\n2️⃣  **TEMPORAL SEARCH**")
        print("-" * 40)
        
        # Time-based searches
        now = datetime.now()
        last_week = now - timedelta(days=7)
        last_month = now - timedelta(days=30)
        
        temporal_scenarios = [
            {
                "description": "Recent AI Act developments (last 7 days)",
                "query": "AI Act implementation timeline",
                "time_context": "last_week"
            },
            {
                "description": "Historical compliance requirements",
                "query": "compliance deadlines",
                "time_context": "last_month"
            },
            {
                "description": "Policy evolution over time",
                "query": "regulatory changes",
                "time_context": "historical"
            }
        ]
        
        for scenario in temporal_scenarios:
            print(f"\n📅 Scenario: {scenario['description']}")
            
            # For Graphiti MCP, temporal search is built into the query context
            mcp_call = {
                "method": "search_memory_facts",
                "params": {
                    "query": f"{scenario['query']} {scenario['time_context']}",
                    "group_ids": [self.group_id],
                    "max_facts": 10
                }
            }
            
            print(f"   📡 MCP Call: {json.dumps(mcp_call, indent=6)}")
            print(f"   💡 Use Case: Find {scenario['description'].lower()}")
            print(f"   🎯 Expected Results: Time-relevant facts with temporal context")

    async def _demo_entity_centered_search(self):
        """Demonstrate entity-centered search strategies."""
        print("\n3️⃣  **ENTITY-CENTERED SEARCH**")
        print("-" * 40)
        
        entities_of_interest = [
            {
                "entity": "Apple Inc.",
                "search_focus": "compliance obligations"
            },
            {
                "entity": "European AI Office",
                "search_focus": "regulatory authority"
            },
            {
                "entity": "Singapore Model AI Governance Framework",
                "search_focus": "policy implementation"
            }
        ]
        
        for entity_info in entities_of_interest:
            print(f"\n🎯 Entity Focus: {entity_info['entity']}")
            
            # First, find the entity
            entity_search = {
                "method": "search_memory_nodes",
                "params": {
                    "query": entity_info['entity'],
                    "group_ids": [self.group_id],
                    "max_nodes": 1
                }
            }
            
            print(f"   📡 Find Entity: {json.dumps(entity_search, indent=6)}")
            
            # Then search around that entity
            centered_search = {
                "method": "search_memory_facts",
                "params": {
                    "query": entity_info['search_focus'],
                    "group_ids": [self.group_id],
                    "center_node_uuid": "entity_uuid_from_above",  # Would be populated from first call
                    "max_facts": 8
                }
            }
            
            print(f"   📡 Centered Search: {json.dumps(centered_search, indent=6)}")
            print(f"   💡 Use Case: Find all {entity_info['search_focus']} related to {entity_info['entity']}")
            print(f"   🎯 Expected Results: Facts directly connected to this entity")

    async def _demo_fact_based_search(self):
        """Demonstrate fact-based search for specific relationships."""
        print("\n4️⃣  **FACT-BASED SEARCH**")
        print("-" * 40)
        
        fact_queries = [
            {
                "query": "COMPLIES_WITH relationships",
                "description": "Find all compliance relationships"
            },
            {
                "query": "REPORTS_TO obligations",
                "description": "Find reporting requirement chains"
            },
            {
                "query": "ESTABLISHED policies",
                "description": "Find policy establishment facts"
            },
            {
                "query": "deadline requirements",
                "description": "Find time-sensitive obligations"
            }
        ]
        
        for fact_query in fact_queries:
            print(f"\n📋 Fact Search: {fact_query['description']}")
            
            mcp_call = {
                "method": "search_memory_facts",
                "params": {
                    "query": fact_query['query'],
                    "group_ids": [self.group_id],
                    "max_facts": 15
                }
            }
            
            print(f"   📡 MCP Call: {json.dumps(mcp_call, indent=6)}")
            print(f"   💡 Use Case: {fact_query['description']}")
            print(f"   🎯 Expected Results: Specific relationship facts matching the pattern")

    async def _demo_node_exploration(self):
        """Demonstrate node exploration and discovery."""
        print("\n5️⃣  **NODE EXPLORATION**")
        print("-" * 40)
        
        exploration_strategies = [
            {
                "entity_type": "Policy",
                "description": "Explore all policy entities"
            },
            {
                "entity_type": "Company", 
                "description": "Explore all company entities"
            },
            {
                "entity_type": "GovernmentAgency",
                "description": "Explore all government agencies"
            }
        ]
        
        for strategy in exploration_strategies:
            print(f"\n🗺️  Exploration: {strategy['description']}")
            
            # Search for nodes of specific type
            node_search = {
                "method": "search_memory_nodes",
                "params": {
                    "query": strategy['entity_type'],
                    "group_ids": [self.group_id],
                    "entity": strategy['entity_type'],  # Filter by entity type
                    "max_nodes": 10
                }
            }
            
            print(f"   📡 MCP Call: {json.dumps(node_search, indent=6)}")
            print(f"   💡 Use Case: Discover all {strategy['entity_type']} entities in the graph")
            print(f"   🎯 Expected Results: List of entities with their properties and connections")

    async def _demo_advanced_search(self):
        """Demonstrate advanced search combinations."""
        print("\n6️⃣  **ADVANCED SEARCH STRATEGIES**")
        print("-" * 40)
        
        advanced_scenarios = [
            {
                "name": "Compliance Impact Analysis",
                "steps": [
                    "1. Find a specific policy (e.g., EU AI Act)",
                    "2. Search for all entities that COMPLIES_WITH this policy", 
                    "3. For each complying entity, find their compliance obligations",
                    "4. Identify potential compliance gaps or conflicts"
                ]
            },
            {
                "name": "Regulatory Authority Mapping",
                "steps": [
                    "1. Find all GovernmentAgency entities",
                    "2. For each agency, find entities that REPORTS_TO them",
                    "3. Map the regulatory hierarchy and authority chains",
                    "4. Identify overlapping jurisdictions"
                ]
            },
            {
                "name": "Policy Evolution Timeline",
                "steps": [
                    "1. Search for policy documents over time",
                    "2. Find AMENDS, SUPERSEDES, and UPDATES relationships",
                    "3. Build temporal policy evolution graph",
                    "4. Identify current vs. historical requirements"
                ]
            }
        ]
        
        for scenario in advanced_scenarios:
            print(f"\n🧠 Advanced Scenario: {scenario['name']}")
            print("   📋 Multi-step Process:")
            for step in scenario['steps']:
                print(f"      {step}")
            
            # Example MCP call sequence for first scenario
            if scenario['name'] == "Compliance Impact Analysis":
                print("\n   📡 Example MCP Call Sequence:")
                
                # Step 1: Find EU AI Act
                step1 = {
                    "method": "search_memory_nodes",
                    "params": {
                        "query": "European Union Artificial Intelligence Act",
                        "entity": "Policy",
                        "max_nodes": 1
                    }
                }
                print(f"      Step 1: {json.dumps(step1, indent=8)}")
                
                # Step 2: Find compliance relationships
                step2 = {
                    "method": "search_memory_facts", 
                    "params": {
                        "query": "COMPLIES_WITH",
                        "center_node_uuid": "eu_ai_act_uuid",
                        "max_facts": 20
                    }
                }
                print(f"      Step 2: {json.dumps(step2, indent=8)}")

    def _print_search_strategy_summary(self):
        """Print a summary of available search strategies."""
        
        strategies = {
            "Basic Semantic": {
                "best_for": "General topic exploration",
                "mcp_method": "search_memory_facts",
                "key_params": "query, max_facts"
            },
            "Temporal": {
                "best_for": "Time-based analysis",
                "mcp_method": "search_memory_facts + temporal context",
                "key_params": "query with time context"
            },
            "Entity-Centered": {
                "best_for": "Deep-dive on specific entities",
                "mcp_method": "search_memory_nodes + search_memory_facts",
                "key_params": "center_node_uuid"
            },
            "Fact-Based": {
                "best_for": "Relationship pattern discovery",
                "mcp_method": "search_memory_facts",
                "key_params": "relationship-focused queries"
            },
            "Node Exploration": {
                "best_for": "Entity type discovery",
                "mcp_method": "search_memory_nodes",
                "key_params": "entity type filters"
            },
            "Advanced Multi-Step": {
                "best_for": "Complex analytical workflows",
                "mcp_method": "Combination of above methods",
                "key_params": "Sequential calls with context"
            }
        }
        
        for strategy_name, details in strategies.items():
            print(f"\n📊 {strategy_name}:")
            print(f"   🎯 Best for: {details['best_for']}")
            print(f"   📡 MCP Method: {details['mcp_method']}")
            print(f"   🔧 Key Params: {details['key_params']}")

async def main():
    """Main demonstration function."""
    explorer = GraphitiMCPSearchExplorer()
    await explorer.demonstrate_search_strategies()
    
    print("\n" + "=" * 60)
    print("💡 **NEXT STEPS:**")
    print("   1. Start the Graphiti MCP server: docker-compose up graphiti-mcp")
    print("   2. Use Claude Code MCP integration to run these searches")
    print("   3. Combine search results for complex analytical workflows")
    print("   4. Build dashboards or reports based on search patterns")

if __name__ == "__main__":
    asyncio.run(main())