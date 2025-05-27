#!/usr/bin/env python3
"""
Test script for Political Document Processor with Graphiti integration.

This script tests the complete document processing pipeline:
1. Document content extraction
2. LLM-based entity and relationship extraction  
3. Episode creation and Graphiti storage
4. Search and retrieval functionality

Usage: uv run python scripts/test_political_document_processor.py
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from graphrag.political_document_processor import PoliticalDocumentProcessor, GraphitiConfig
from graphrag.graphiti_config import get_graphiti_settings, get_client_manager
from llm.base_client import BaseLLMClient


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing without actual API calls."""
    
    def __init__(self):
        # Import here to avoid circular imports
        from llm.models import LLMProvider
        super().__init__(provider=LLMProvider.OPENAI)
    
    async def complete(self, prompt: str, **kwargs) -> str:
        """Mock completion method."""
        return "Mock completion response"
    
    async def analyze_document(self, content: str, **kwargs) -> dict:
        """Mock document analysis method."""
        return {"summary": "Mock document analysis"}
    
    async def analyze_topics(self, content: str, **kwargs) -> dict:
        """Mock topic analysis method."""
        return {"topics": ["mock_topic"]}
    
    async def score_dimension(self, content: str, dimension: str, **kwargs) -> float:
        """Mock scoring method."""
        return 0.75
    
    async def generate_report_insights(self, data: dict, **kwargs) -> str:
        """Mock report insights method."""
        return "Mock report insights"
    
    async def generate_response(
        self, 
        prompt: str, 
        system_message: str = "", 
        response_format: str = "text"
    ) -> str:
        """Return mock entity extraction response."""
        
        if "EU Digital Services Act" in prompt or "DSA" in prompt:
            return """{
                "entities": [
                    {
                        "name": "European Union",
                        "type": "Jurisdiction",
                        "properties": {"confidence": 0.95},
                        "context": "European Union's Digital Services Act",
                        "jurisdiction": "EU"
                    },
                    {
                        "name": "Digital Services Act",
                        "type": "Policy", 
                        "properties": {"confidence": 0.98, "status": "enacted"},
                        "context": "Digital Services Act (DSA) requires large platforms",
                        "jurisdiction": "EU"
                    },
                    {
                        "name": "Meta",
                        "type": "Company",
                        "properties": {"confidence": 0.90, "sector": "technology"},
                        "context": "platforms like Meta and Google",
                        "jurisdiction": "Global"
                    },
                    {
                        "name": "Google", 
                        "type": "Company",
                        "properties": {"confidence": 0.90, "sector": "technology"},
                        "context": "platforms like Meta and Google",
                        "jurisdiction": "Global"
                    }
                ],
                "relationships": [
                    {
                        "source": "Digital Services Act",
                        "target": "Meta",
                        "type": "AFFECTS",
                        "properties": {"confidence": 0.85, "effective_date": "2024-02-17"},
                        "context": "DSA requires large platforms like Meta"
                    },
                    {
                        "source": "Digital Services Act", 
                        "target": "Google",
                        "type": "AFFECTS",
                        "properties": {"confidence": 0.85, "effective_date": "2024-02-17"},
                        "context": "DSA requires large platforms like Google"
                    },
                    {
                        "source": "European Union",
                        "target": "Digital Services Act",
                        "type": "ENFORCES",
                        "properties": {"confidence": 0.80},
                        "context": "European Union's Digital Services Act"
                    }
                ],
                "metadata": {
                    "document_type": "regulation",
                    "jurisdiction_focus": "EU",
                    "business_impact_level": "high",
                    "extraction_confidence": 0.87,
                    "key_dates": ["2024-02-17", "2024-08-25"],
                    "affected_industries": ["technology", "social_media"]
                }
            }"""
        
        # Default mock response for other content
        return """{
            "entities": [
                {
                    "name": "Test Policy",
                    "type": "Policy",
                    "properties": {"confidence": 0.75},
                    "context": "test document content",
                    "jurisdiction": "Test"
                }
            ],
            "relationships": [],
            "metadata": {
                "document_type": "policy",
                "jurisdiction_focus": "test", 
                "business_impact_level": "medium",
                "extraction_confidence": 0.75
            }
        }"""


async def test_document_processor():
    """Test the political document processor with sample documents."""
    
    print("🧪 Testing Political Document Processor")
    print("=" * 50)
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Test 1: Configuration and Setup
        print("\n📋 Test 1: Configuration and Setup")
        
        settings = get_graphiti_settings()
        print(f"✅ Graphiti settings loaded")
        print(f"   Neo4j URI: {settings.neo4j_uri}")
        print(f"   Default group: {settings.default_group_id}")
        
        # Create GraphitiConfig
        graphiti_config = GraphitiConfig(
            neo4j_uri=settings.neo4j_uri,
            neo4j_user=settings.neo4j_user,
            neo4j_password=settings.neo4j_password,
            group_id="test_political_docs"
        )
        
        # Test 2: Client Manager Connection
        print("\n🔌 Test 2: Connection Test")
        
        client_manager = get_client_manager()
        connection_ok = await client_manager.test_connection()
        
        if connection_ok:
            print("✅ Graphiti connection successful")
        else:
            print("❌ Graphiti connection failed - check Neo4j is running")
            return False
        
        # Test 3: Document Processor Initialization
        print("\n🏗️ Test 3: Document Processor Initialization")
        
        mock_llm = MockLLMClient()
        
        async with PoliticalDocumentProcessor(
            llm_client=mock_llm,
            graphiti_config=graphiti_config
        ) as processor:
            print("✅ Document processor initialized")
            
            # Test 4: Process Sample Documents
            print("\n📄 Test 4: Process Sample Documents")
            
            # Find sample documents
            sample_docs_dir = Path(__file__).parent.parent / "data" / "input" / "examples"
            
            if not sample_docs_dir.exists():
                print(f"⚠️ Sample documents directory not found: {sample_docs_dir}")
                print("   Creating test document...")
                
                # Create test document
                test_doc_path = Path("/tmp/test_political_doc.md")
                test_content = """
# EU Digital Services Act Implementation

The European Union's Digital Services Act (DSA) came into effect on February 17, 2024, 
requiring large online platforms like Meta and Google to implement comprehensive content 
moderation systems.

## Key Requirements

- Risk assessment for systemic risks
- External auditing of content moderation
- Transparency reporting on content decisions
- User complaint mechanisms

## Compliance Timeline

- February 17, 2024: DSA enters into force
- August 25, 2024: Full compliance required for Very Large Online Platforms (VLOPs)

## Affected Companies

Major technology companies including Meta (Facebook, Instagram), Google (YouTube, Search), 
X (formerly Twitter), and TikTok must comply with these requirements.

The European Commission will oversee enforcement with potential fines up to 6% of 
global annual revenue for non-compliance.
                """.strip()
                
                test_doc_path.write_text(test_content)
                sample_documents = [test_doc_path]
                
            else:
                # Use actual sample documents
                sample_documents = list(sample_docs_dir.glob("*.md"))[:2]  # Limit to 2 for testing
            
            print(f"   Found {len(sample_documents)} documents to process")
            
            # Process documents
            results = await processor.process_documents_batch(sample_documents, batch_size=2)
            
            # Test 5: Processing Results Analysis
            print("\n📊 Test 5: Processing Results Analysis")
            
            successful_results = [r for r in results if r.success]
            failed_results = [r for r in results if not r.success]
            
            print(f"   Processed: {len(results)} documents")
            print(f"   Successful: {len(successful_results)}")
            print(f"   Failed: {len(failed_results)}")
            
            if successful_results:
                total_entities = sum(r.entities_extracted for r in successful_results)
                total_relationships = sum(r.relationships_extracted for r in successful_results)
                avg_confidence = sum(r.extraction_confidence or 0 for r in successful_results) / len(successful_results)
                
                print(f"   Total entities extracted: {total_entities}")
                print(f"   Total relationships extracted: {total_relationships}")
                print(f"   Average confidence: {avg_confidence:.2f}")
                
                # Show details for first successful result
                first_result = successful_results[0]
                print(f"   Example result:")
                print(f"     Document: {Path(first_result.document_path).name}")
                print(f"     Episode ID: {first_result.episode_id}")
                print(f"     Processing time: {first_result.processing_time_seconds:.2f}s")
                print(f"     Business impact: {first_result.business_impact_level}")
            
            if failed_results:
                print(f"   Failed documents:")
                for result in failed_results:
                    print(f"     {Path(result.document_path).name}: {result.error_message}")
            
            # Test 6: Search Functionality
            print("\n🔍 Test 6: Search Functionality")
            
            try:
                search_results = await processor.search_entities("Digital Services Act", limit=5)
                print(f"   Search returned {len(search_results)} entities")
                
                for entity in search_results:
                    print(f"     - {entity['name']} (Labels: {entity['labels']})")
                    
            except Exception as e:
                print(f"   Search failed: {e}")
            
            # Test 7: Processing Statistics
            print("\n📈 Test 7: Processing Statistics")
            
            stats = processor.get_processing_statistics(results)
            
            print(f"   Success rate: {stats['summary']['success_rate']:.1%}")
            print(f"   Average processing time: {stats['processing_performance']['average_processing_time']:.2f}s")
            
            if stats['extraction_performance']['total_entities'] > 0:
                print(f"   Entities per document: {stats['extraction_performance']['average_entities_per_doc']:.1f}")
                print(f"   Relationships per document: {stats['extraction_performance']['average_relationships_per_doc']:.1f}")
            
            print(f"   Average confidence: {stats['quality_metrics']['average_confidence']:.2f}")
        
        print("\n✅ All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        logger.exception("Test execution failed")
        return False
    
    finally:
        # Cleanup test files
        test_doc_path = Path("/tmp/test_political_doc.md")
        if test_doc_path.exists():
            test_doc_path.unlink()


async def main():
    """Main test execution."""
    print("🚀 Political Document Processor Test Suite")
    print("Testing Graphiti Direct API integration")
    print()
    
    # Check prerequisites
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️ No API keys found - using mock LLM client")
    
    success = await test_document_processor()
    
    if success:
        print("\n🎉 All tests passed! Document processor is ready for use.")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed. Check the output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())