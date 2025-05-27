#!/usr/bin/env python3
"""
Test script for Approach A: Graphiti custom entity types
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from graphrag.political_document_processor import PoliticalDocumentProcessor, GraphitiConfig
from graphrag.graphiti_config import get_graphiti_settings
from llm.base_client import BaseLLMClient
from llm.models import LLMProvider


class MinimalLLMClient(BaseLLMClient):
    """Minimal LLM client since we're not using it for Approach A."""
    
    def __init__(self):
        super().__init__(provider=LLMProvider.OPENAI)
    
    async def complete(self, prompt: str, **kwargs) -> str:
        return "Not used in Approach A"
    
    async def analyze_document(self, content: str, **kwargs) -> dict:
        return {"summary": "Not used in Approach A"}
    
    async def analyze_topics(self, content: str, **kwargs) -> dict:
        return {"topics": ["Not used"]}
    
    async def score_dimension(self, content: str, dimension: str, **kwargs) -> float:
        return 0.5
    
    async def generate_report_insights(self, data: dict, **kwargs) -> str:
        return "Not used in Approach A"
    
    async def generate_response(self, prompt: str, system_message: str = "", response_format: str = "text") -> str:
        return "Not used in Approach A"


async def test_approach_a():
    """Test Approach A with custom entity types."""
    print("🧪 Testing Approach A: Graphiti Custom Entity Types")
    print("=" * 55)
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Check API key (still needed for Graphiti's internal LLM calls)
        if not os.getenv("OPENAI_API_KEY"):
            print("❌ OPENAI_API_KEY required for Graphiti's internal processing")
            return False
        
        print("✅ OpenAI API key found")
        
        # Setup processor with custom entity types
        settings = get_graphiti_settings()
        graphiti_config = GraphitiConfig(
            neo4j_uri=settings.neo4j_uri,
            neo4j_user=settings.neo4j_user,
            neo4j_password=settings.neo4j_password,
            group_id="approach_a_test"
        )
        
        llm_client = MinimalLLMClient()
        
        # Test with one document
        test_doc = Path(__file__).parent.parent / "data" / "input" / "examples" / "apple_ai_act_compliance_response_2024.md"
        
        if not test_doc.exists():
            print(f"❌ Test document not found: {test_doc}")
            return False
        
        print(f"📄 Testing with: {test_doc.name}")
        
        async with PoliticalDocumentProcessor(
            llm_client=llm_client,
            graphiti_config=graphiti_config
        ) as processor:
            print("✅ Processor initialized with custom entity types")
            
            # Process the document
            results = await processor.process_documents_batch([test_doc], batch_size=1)
            
            if not results:
                print("❌ No results returned")
                return False
            
            result = results[0]
            print(f"\n📊 Processing Result:")
            print(f"   Success: {result.success}")
            print(f"   Episode ID: {result.episode_id}")
            print(f"   Entities extracted: {result.entities_extracted}")
            print(f"   Relationships extracted: {result.relationships_extracted}")
            print(f"   Processing time: {result.processing_time_seconds:.2f}s")
            
            if not result.success:
                print(f"   Error: {result.error_message}")
                return False
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_approach_a())
    if success:
        print("\n🎉 Approach A test completed! Check Neo4j browser to see results.")
        print("Expected: Entities should have proper labels (Policy, Company, etc.)")
    else:
        print("\n💥 Approach A test failed!")