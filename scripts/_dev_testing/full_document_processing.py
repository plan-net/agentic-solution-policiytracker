#!/usr/bin/env python3
"""
Full Document Processing Script

This script:
1. Clears the existing Neo4j graph
2. Processes all documents in data/input/examples/
3. Creates a comprehensive political knowledge graph
4. Provides detailed processing statistics

Usage: uv run python scripts/full_document_processing.py
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


class OpenAILLMClient(BaseLLMClient):
    """OpenAI LLM client for production document processing."""
    
    def __init__(self):
        super().__init__(provider=LLMProvider.OPENAI)
    
    async def complete(self, prompt: str, **kwargs) -> str:
        """Complete method - not used in document processor."""
        return "Not implemented for document processor"
    
    async def analyze_document(self, content: str, **kwargs) -> dict:
        """Document analysis method - not used in document processor."""
        return {"summary": "Not implemented for document processor"}
    
    async def analyze_topics(self, content: str, **kwargs) -> dict:
        """Topic analysis method - not used in document processor."""
        return {"topics": ["Not implemented"]}
    
    async def score_dimension(self, content: str, dimension: str, **kwargs) -> float:
        """Scoring method - not used in document processor."""
        return 0.5
    
    async def generate_report_insights(self, data: dict, **kwargs) -> str:
        """Report insights method - not used in document processor."""
        return "Not implemented for document processor"
    
    async def generate_response(
        self, 
        prompt: str, 
        system_message: str = "", 
        response_format: str = "text"
    ) -> str:
        """Generate response using OpenAI API - this is the main method used."""
        # This would normally call the actual OpenAI API
        # For now, we'll use the existing langchain integration
        try:
            from src.llm.langchain_service import LangChainService
            
            service = LangChainService()
            
            if response_format == "json":
                # For JSON responses, use structured output
                response = await service.generate_structured_response(
                    prompt=prompt,
                    system_message=system_message
                )
            else:
                # For text responses
                response = await service.generate_response(
                    prompt=prompt,
                    system_message=system_message
                )
            
            return response
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            # Return a basic fallback response
            return '{"entities": [], "relationships": [], "metadata": {"extraction_confidence": 0.1}}'


async def clear_neo4j_graph():
    """Clear the existing Neo4j graph data."""
    try:
        print("🗑️ Clearing existing Neo4j graph data...")
        
        # Get client manager and clear graph
        client_manager = get_client_manager()
        
        # Test connection first
        connection_ok = await client_manager.test_connection()
        if not connection_ok:
            print("❌ Cannot connect to Neo4j - please ensure it's running")
            return False
        
        # Clear the graph
        await client_manager.clear_graph()
        print("✅ Graph cleared successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to clear graph: {e}")
        return False


async def process_all_documents():
    """Process all documents in the examples directory."""
    
    print("🚀 Full Document Processing Pipeline")
    print("Processing all political documents to create knowledge graph")
    print("=" * 60)
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    try:
        # Step 1: Clear existing graph
        print("\n📋 Step 1: Graph Preparation")
        
        clear_success = await clear_neo4j_graph()
        if not clear_success:
            return False
        
        # Step 2: Configuration
        print("\n⚙️ Step 2: Configuration Setup")
        
        settings = get_graphiti_settings()
        print(f"✅ Neo4j URI: {settings.neo4j_uri}")
        print(f"✅ Default group: {settings.default_group_id}")
        
        # Create GraphitiConfig for production processing
        graphiti_config = GraphitiConfig(
            neo4j_uri=settings.neo4j_uri,
            neo4j_user=settings.neo4j_user,
            neo4j_password=settings.neo4j_password,
            group_id="political_monitoring_full"  # Use descriptive group ID
        )
        
        # Step 3: LLM Client Setup
        print("\n🤖 Step 3: LLM Client Setup")
        
        # Check for API keys
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            print("❌ OPENAI_API_KEY not found in environment")
            print("   Please set your OpenAI API key to process documents")
            return False
        
        print("✅ OpenAI API key found")
        llm_client = OpenAILLMClient()
        
        # Step 4: Document Discovery
        print("\n📄 Step 4: Document Discovery")
        
        documents_dir = Path(__file__).parent.parent / "data" / "input" / "examples"
        
        if not documents_dir.exists():
            print(f"❌ Documents directory not found: {documents_dir}")
            return False
        
        # Find all supported document files
        document_files = []
        supported_extensions = [".md", ".txt", ".pdf", ".docx"]
        
        for ext in supported_extensions:
            document_files.extend(documents_dir.glob(f"*{ext}"))
        
        document_files.sort()  # Process in alphabetical order
        
        print(f"✅ Found {len(document_files)} documents to process:")
        for i, doc_file in enumerate(document_files, 1):
            print(f"   {i:2d}. {doc_file.name}")
        
        # Step 5: Document Processing
        print("\n🔄 Step 5: Document Processing")
        
        async with PoliticalDocumentProcessor(
            llm_client=llm_client,
            graphiti_config=graphiti_config
        ) as processor:
            print("✅ Document processor initialized")
            
            # Process all documents in smaller batches to avoid overwhelming the system
            print(f"\n📊 Processing {len(document_files)} documents...")
            
            # Use smaller batch size for production processing
            batch_size = 2  # Process 2 documents at a time
            results = await processor.process_documents_batch(document_files, batch_size=batch_size)
            
            # Step 6: Results Analysis
            print("\n📈 Step 6: Results Analysis")
            
            successful_results = [r for r in results if r.success]
            failed_results = [r for r in results if not r.success]
            
            print(f"📊 Processing Summary:")
            print(f"   Total documents: {len(results)}")
            print(f"   Successful: {len(successful_results)} ({len(successful_results)/len(results)*100:.1f}%)")
            print(f"   Failed: {len(failed_results)}")
            
            if successful_results:
                total_entities = sum(r.entities_extracted for r in successful_results)
                total_relationships = sum(r.relationships_extracted for r in successful_results)
                avg_confidence = sum(r.extraction_confidence or 0 for r in successful_results) / len(successful_results)
                total_time = sum(r.processing_time_seconds for r in successful_results)
                
                print(f"\n🎯 Extraction Results:")
                print(f"   Total entities: {total_entities}")
                print(f"   Total relationships: {total_relationships}")
                print(f"   Average confidence: {avg_confidence:.2f}")
                print(f"   Total processing time: {total_time:.1f}s")
                print(f"   Average time per doc: {total_time/len(successful_results):.1f}s")
                
                # Show top performers
                print(f"\n🏆 Top Performing Documents:")
                top_docs = sorted(successful_results, key=lambda x: x.entities_extracted, reverse=True)[:3]
                for i, result in enumerate(top_docs, 1):
                    doc_name = Path(result.document_path).name
                    print(f"   {i}. {doc_name}: {result.entities_extracted} entities, {result.relationships_extracted} relationships")
            
            if failed_results:
                print(f"\n❌ Failed Documents:")
                for result in failed_results:
                    doc_name = Path(result.document_path).name
                    print(f"   • {doc_name}: {result.error_message}")
            
            # Step 7: Graph Statistics
            print("\n🕷️ Step 7: Knowledge Graph Statistics")
            
            try:
                # Search for entities to get graph stats
                search_results = await processor.search_entities("", limit=100)  # Get many entities
                print(f"✅ Knowledge graph created with {len(search_results)} searchable entities")
                
                # Show some example entities
                if search_results:
                    print(f"\n🔍 Sample Entities in Graph:")
                    for i, entity in enumerate(search_results[:5], 1):
                        print(f"   {i}. {entity['name']} (Labels: {', '.join(entity['labels'])})")
                
            except Exception as e:
                print(f"⚠️ Could not retrieve graph statistics: {e}")
            
            # Step 8: Next Steps
            print("\n🎯 Step 8: Next Steps")
            print("✅ Processing complete! You can now explore the knowledge graph:")
            print(f"   • Neo4j Browser: http://localhost:7474")
            print(f"   • Username: neo4j")
            print(f"   • Database: neo4j")
            print(f"   • Group ID: {graphiti_config.group_id}")
            
            print(f"\n🔍 Useful Cypher queries to explore the graph:")
            print(f"   # Count all entities")
            print(f"   MATCH (n:Entity) WHERE n.group_id = '{graphiti_config.group_id}' RETURN count(n)")
            print(f"   ")
            print(f"   # Show entity types distribution")
            print(f"   MATCH (n:Entity) WHERE n.group_id = '{graphiti_config.group_id}' RETURN labels(n), count(*) ORDER BY count(*) DESC")
            print(f"   ")
            print(f"   # Find all policies")
            print(f"   MATCH (n:Entity) WHERE n.group_id = '{graphiti_config.group_id}' AND any(label IN labels(n) WHERE label CONTAINS 'Policy') RETURN n.name, n.summary LIMIT 10")
            print(f"   ")
            print(f"   # Show relationships")
            print(f"   MATCH (a:Entity)-[r:RELATES_TO]->(b:Entity) WHERE r.group_id = '{graphiti_config.group_id}' RETURN a.name, r.name, b.name LIMIT 10")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Processing failed with error: {e}")
        logger.exception("Full processing failed")
        return False


async def main():
    """Main execution function."""
    print("🏛️ Political Document Knowledge Graph Builder")
    print("Creating comprehensive graph from all regulatory documents")
    print()
    
    success = await process_all_documents()
    
    if success:
        print("\n🎉 Success! Knowledge graph created and ready for exploration.")
        sys.exit(0)
    else:
        print("\n💥 Processing failed. Check the output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())