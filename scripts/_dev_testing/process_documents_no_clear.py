#!/usr/bin/env python3
"""
Document Processing Script (Graph already cleared via MCP)
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


async def main():
    """Main processing function."""
    print("🏛️ Political Document Knowledge Graph Builder")
    print("Processing all documents (graph already cleared)")
    print("=" * 55)
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Step 1: Check API key
        if not os.getenv("OPENAI_API_KEY"):
            print("❌ OPENAI_API_KEY required")
            return False
        
        print("✅ OpenAI API key found")
        
        # Step 2: Find documents
        docs_dir = Path(__file__).parent.parent / "data" / "input" / "examples"
        documents = list(docs_dir.glob("*.md")) + list(docs_dir.glob("*.txt"))
        documents.sort()
        
        print(f"\n📄 Found {len(documents)} documents:")
        for i, doc in enumerate(documents, 1):
            print(f"   {i:2d}. {doc.name}")
        
        # Step 3: Setup processor
        settings = get_graphiti_settings()
        graphiti_config = GraphitiConfig(
            neo4j_uri=settings.neo4j_uri,
            neo4j_user=settings.neo4j_user,
            neo4j_password=settings.neo4j_password,
            group_id="political_monitoring_full"
        )
        
        llm_client = RealLLMClient()
        
        # Step 4: Process all documents
        print(f"\n🔄 Processing {len(documents)} documents...")
        
        async with PoliticalDocumentProcessor(
            llm_client=llm_client,
            graphiti_config=graphiti_config
        ) as processor:
            
            # Process in small batches
            results = await processor.process_documents_batch(documents, batch_size=2)
            
            # Show results
            successful = [r for r in results if r.success]
            failed = [r for r in results if not r.success]
            
            print(f"\n📊 Processing Results:")
            print(f"   Total documents: {len(results)}")
            print(f"   Successful: {len(successful)} ({len(successful)/len(results)*100:.1f}%)")
            print(f"   Failed: {len(failed)}")
            
            if successful:
                total_entities = sum(r.entities_extracted for r in successful)
                total_relationships = sum(r.relationships_extracted for r in successful)
                avg_confidence = sum(r.extraction_confidence or 0 for r in successful) / len(successful)
                total_time = sum(r.processing_time_seconds for r in successful)
                
                print(f"\n🎯 Knowledge Graph Created:")
                print(f"   Total entities: {total_entities}")
                print(f"   Total relationships: {total_relationships}")
                print(f"   Average confidence: {avg_confidence:.2f}")
                print(f"   Total processing time: {total_time:.1f}s")
                print(f"   Average per document: {total_time/len(successful):.1f}s")
                
                # Show top performing documents
                top_docs = sorted(successful, key=lambda x: x.entities_extracted, reverse=True)[:5]
                print(f"\n🏆 Top Documents by Entity Count:")
                for i, result in enumerate(top_docs, 1):
                    doc_name = Path(result.document_path).name
                    print(f"   {i}. {doc_name}: {result.entities_extracted} entities, {result.relationships_extracted} relationships")
            
            if failed:
                print(f"\n❌ Failed Documents:")
                for result in failed[:3]:  # Show first 3 failures
                    doc_name = Path(result.document_path).name
                    print(f"   • {doc_name}: {result.error_message}")
                if len(failed) > 3:
                    print(f"   ... and {len(failed) - 3} more")
        
        # Step 5: Graph exploration info
        print(f"\n🌐 Knowledge Graph Ready for Exploration:")
        print(f"   Neo4j Browser: http://localhost:7474")
        print(f"   Username: neo4j")
        print(f"   Password: password123")
        print(f"   Group ID: political_monitoring_full")
        
        print(f"\n🔍 Useful Cypher Queries:")
        print(f"   # Count all entities")
        print(f"   MATCH (n:Entity) WHERE n.group_id = 'political_monitoring_full' RETURN count(n)")
        print(f"   ")
        print(f"   # Show entity types")
        print(f"   MATCH (n:Entity) WHERE n.group_id = 'political_monitoring_full' RETURN labels(n), count(*) ORDER BY count(*) DESC")
        print(f"   ")
        print(f"   # Find policies")
        print(f"   MATCH (n:Entity) WHERE n.group_id = 'political_monitoring_full' AND any(label IN labels(n) WHERE label CONTAINS 'Policy') RETURN n.name LIMIT 10")
        print(f"   ")
        print(f"   # Show relationships")
        print(f"   MATCH (a:Entity)-[r:RELATES_TO]->(b:Entity) WHERE r.group_id = 'political_monitoring_full' RETURN a.name, r.name, b.name LIMIT 20")
        print(f"   ")
        print(f"   # Visualize subgraph")
        print(f"   MATCH (n:Entity)-[r:RELATES_TO]-(m:Entity) WHERE n.group_id = 'political_monitoring_full' RETURN n, r, m LIMIT 50")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print("\n🎉 Success! Your knowledge graph is ready to explore!")
    else:
        print("\n💥 Processing failed!")