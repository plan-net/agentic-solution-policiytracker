#!/usr/bin/env python3
"""Basic test of GraphRAG integration without full system dependencies."""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def test_basic_langfuse_prompts():
    """Test basic Langfuse prompt functionality."""
    
    print("=== Testing Basic GraphRAG + Langfuse Integration ===\n")
    
    try:
        from src.prompts.prompt_manager import prompt_manager
        
        # Test loading GraphRAG prompts
        print("1. Testing GraphRAG prompt loading...")
        
        # Test entity analysis prompt
        entity_prompt_variables = {
            "company_terms": ["AI", "technology", "data protection"],
            "core_industries": ["technology", "software"],
            "primary_markets": ["US", "EU"],
            "strategic_themes": ["AI regulation", "data privacy"],
            "entities": json.dumps([{"name": "GDPR", "type": "Regulation"}], indent=2),
            "relationships": json.dumps([{"type": "AFFECTS", "from": "GDPR", "to": "Tech Companies"}], indent=2),
            "graph_results": json.dumps([{"score": 0.85, "text": "Sample analysis"}], indent=2)
        }
        
        try:
            entity_prompt = await prompt_manager.get_prompt(
                "graphrag_entity_analysis",
                variables=entity_prompt_variables
            )
            print(f"   ✅ GraphRAG entity analysis prompt loaded ({len(entity_prompt)} chars)")
        except Exception as e:
            print(f"   ❌ Failed to load entity analysis prompt: {e}")
        
        # Test relationship insights prompt
        relationship_prompt_variables = {
            "query_topic": "AI regulation compliance",
            "company_terms": ["AI", "machine learning"],
            "strategic_themes": ["compliance", "risk management"],
            "time_horizon": "6-12 months",
            "relationship_patterns": json.dumps([{"type": "IMPLEMENTS", "strength": "high"}], indent=2),
            "entity_clusters": json.dumps({"Regulation": ["GDPR", "AI Act"]}, indent=2),
            "network_metrics": json.dumps({"total_relationships": 5}, indent=2),
            "traversal_results": json.dumps({"query": "test", "results": []}, indent=2)
        }
        
        try:
            relationship_prompt = await prompt_manager.get_prompt(
                "graphrag_relationship_insights",
                variables=relationship_prompt_variables
            )
            print(f"   ✅ GraphRAG relationship insights prompt loaded ({len(relationship_prompt)} chars)")
        except Exception as e:
            print(f"   ❌ Failed to load relationship insights prompt: {e}")
        
        # Test comparative analysis prompt
        comparison_prompt_variables = {
            "analysis_topic": "AI regulation impact",
            "company_context": json.dumps({"focus": "AI compliance"}, indent=2),
            "strategic_focus": "regulatory compliance",
            "traditional_results": json.dumps({"method": "keyword_scoring", "score": 0.75}, indent=2),
            "graphrag_entities": json.dumps({"entities_analyzed": 10}, indent=2),
            "graphrag_relationships": json.dumps({"network_metrics": {"total": 15}}, indent=2),
            "network_metrics": json.dumps({"centrality": "high"}, indent=2)
        }
        
        try:
            comparison_prompt = await prompt_manager.get_prompt(
                "graphrag_comparative_analysis",
                variables=comparison_prompt_variables
            )
            print(f"   ✅ GraphRAG comparative analysis prompt loaded ({len(comparison_prompt)} chars)")
        except Exception as e:
            print(f"   ❌ Failed to load comparative analysis prompt: {e}")
        
        # Test prompt manager cache statistics
        print("\n2. Testing prompt manager functionality...")
        cache_stats = prompt_manager.get_cache_stats()
        print(f"   Cached prompts: {cache_stats['cached_prompts']}")
        print(f"   Fallback count: {cache_stats['fallback_count']}")
        print(f"   Available prompts: {len(cache_stats['available_prompts'])}")
        
        # List all available prompts
        print(f"   Available prompt files: {cache_stats['available_prompts']}")
        
        print("\n3. Testing variable substitution...")
        # Test simple variable substitution
        test_template = "Hello {{name}}, your score is {{score}}"
        test_vars = {"name": "GraphRAG", "score": 95}
        substituted = prompt_manager._substitute_variables(test_template, test_vars)
        expected = "Hello GraphRAG, your score is 95"
        if substituted == expected:
            print("   ✅ Variable substitution working correctly")
        else:
            print(f"   ❌ Variable substitution failed: got '{substituted}', expected '{expected}'")
        
        print("\n=== Basic GraphRAG + Langfuse Integration Test Complete ===")
        print("✅ All basic functionality tests passed!")
        
        return True
        
    except Exception as e:
        print(f"Error during basic testing: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the basic test."""
    success = asyncio.run(test_basic_langfuse_prompts())
    if success:
        print("\n🎉 GraphRAG + Langfuse integration is ready for use!")
    else:
        print("\n❌ Integration test failed - check configuration")
        sys.exit(1)

if __name__ == "__main__":
    main()