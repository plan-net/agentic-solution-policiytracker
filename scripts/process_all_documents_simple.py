#!/usr/bin/env python3
"""
Simple Full Document Processing Script

This script processes all documents using the working test approach but with real OpenAI API.
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
from llm.models import LLMProvider


class RealLLMClient(BaseLLMClient):
    """Real LLM client using the existing LangChain service."""
    
    def __init__(self):
        super().__init__(provider=LLMProvider.OPENAI)
    
    async def complete(self, prompt: str, **kwargs) -> str:
        return "Not implemented for document processor"
    
    async def analyze_document(self, content: str, **kwargs) -> dict:
        return {"summary": "Not implemented for document processor"}
    
    async def analyze_topics(self, content: str, **kwargs) -> dict:
        return {"topics": ["Not implemented"]}
    
    async def score_dimension(self, content: str, dimension: str, **kwargs) -> float:
        return 0.5
    
    async def generate_report_insights(self, data: dict, **kwargs) -> str:
        return "Not implemented for document processor"
    
    async def generate_response(
        self, 
        prompt: str, 
        system_message: str = "", 
        response_format: str = "text"
    ) -> str:
        """Generate response using real LLM."""
        try:
            from src.llm.langchain_service import LangChainService
            
            service = LangChainService()
            
            if response_format == "json":
                response = await service.generate_structured_response(
                    prompt=prompt,
                    system_message=system_message
                )
            else:
                response = await service.generate_response(
                    prompt=prompt,
                    system_message=system_message
                )
            
            return response
            
        except Exception as e:
            print(f"LLM generation failed: {e}")
            # Return a basic fallback response
            return '{"entities": [], "relationships": [], "metadata": {"extraction_confidence": 0.1}}'


async def clear_graph_simple():
    """Clear the graph using the working approach."""
    try:
        print("🗑️ Clearing Neo4j graph...")
        
        # Use the working approach from the test script
        client_manager = get_client_manager()
        success = await client_manager.clear_graph()
        
        if success:
            print("✅ Graph cleared successfully")
        else:
            print("⚠️ Graph clear returned false but continuing...")
        
        return True  # Continue even if clear has issues
        
    except Exception as e:
        print(f"❌ Failed to clear graph: {e}")
        print("⚠️ Continuing anyway...")
        return True  # Continue even if clear fails


async def main():
    """Main processing function."""
    print("🏛️ Political Document Knowledge Graph Builder")
    print("Processing all documents with real LLM")
    print("=" * 50)
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Step 1: Clear graph
        success = await clear_graph_simple()
        if not success:
            return False
        
        # Step 2: Check API key
        if not os.getenv("OPENAI_API_KEY"):
            print("❌ OPENAI_API_KEY required")
            return False
        
        print("✅ OpenAI API key found")
        
        # Step 3: Find documents
        docs_dir = Path(__file__).parent.parent / "data" / "input" / "examples"
        documents = list(docs_dir.glob("*.md")) + list(docs_dir.glob("*.txt"))
        documents.sort()
        
        print(f"\n📄 Found {len(documents)} documents:")
        for i, doc in enumerate(documents, 1):
            print(f"   {i:2d}. {doc.name}")
        
        # Step 4: Setup processor
        settings = get_graphiti_settings()
        graphiti_config = GraphitiConfig(
            neo4j_uri=settings.neo4j_uri,
            neo4j_user=settings.neo4j_user,
            neo4j_password=settings.neo4j_password,
            group_id="political_monitoring_full"
        )
        
        llm_client = RealLLMClient()
        
        # Step 5: Process all documents
        print(f"\n🔄 Processing documents...")
        
        async with PoliticalDocumentProcessor(
            llm_client=llm_client,
            graphiti_config=graphiti_config
        ) as processor:
            
            # Process in small batches
            results = await processor.process_documents_batch(documents, batch_size=2)
            
            # Show results
            successful = [r for r in results if r.success]
            failed = [r for r in results if not r.success]
            
            print(f"\n📊 Results:")
            print(f"   Total: {len(results)}")
            print(f"   Successful: {len(successful)} ({len(successful)/len(results)*100:.1f}%)")
            print(f"   Failed: {len(failed)}")
            
            if successful:
                total_entities = sum(r.entities_extracted for r in successful)
                total_relationships = sum(r.relationships_extracted for r in successful)
                
                print(f"\n🎯 Extractions:")
                print(f"   Entities: {total_entities}")
                print(f"   Relationships: {total_relationships}")
                
                # Show top documents
                top_docs = sorted(successful, key=lambda x: x.entities_extracted, reverse=True)[:3]
                print(f"\n🏆 Top Documents:")
                for i, result in enumerate(top_docs, 1):
                    doc_name = Path(result.document_path).name
                    print(f"   {i}. {doc_name}: {result.entities_extracted} entities")
            
            if failed:
                print(f"\n❌ Failed Documents:")
                for result in failed[:3]:  # Show first 3 failures
                    doc_name = Path(result.document_path).name
                    print(f"   • {doc_name}: {result.error_message}")
                if len(failed) > 3:
                    print(f"   ... and {len(failed) - 3} more")
        
        # Step 6: Graph exploration
        print(f"\n🌐 Graph ready for exploration:")
        print(f"   Neo4j Browser: http://localhost:7474")
        print(f"   Group ID: political_monitoring_full")
        print(f"\n🔍 Sample queries:")
        print(f"   MATCH (n:Entity) WHERE n.group_id = 'political_monitoring_full' RETURN count(n)")
        print(f"   MATCH (n:Entity) WHERE n.group_id = 'political_monitoring_full' RETURN n.name, labels(n) LIMIT 20")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Processing failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print("\n🎉 Success!")
    else:
        print("\n💥 Failed!")