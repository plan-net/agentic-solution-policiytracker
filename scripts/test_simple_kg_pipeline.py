#!/usr/bin/env python3
"""Test the SimpleKGPipeline with political documents."""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from src.config import settings, graphrag_settings
from src.graphrag.knowledge_builder import PoliticalKnowledgeBuilder

# Load environment variables
load_dotenv()

def log_info(message, **kwargs):
    """Simple logging function."""
    print(f"INFO: {message}", kwargs if kwargs else "")


async def main():
    """Test SimpleKGPipeline with our political documents."""
    try:
        # Get OpenAI API key from environment
        openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if not openai_api_key:
            print("ERROR: OPENAI_API_KEY environment variable not set")
            return
        
        # Initialize knowledge builder with GraphRAG settings (all OpenAI)
        kb = PoliticalKnowledgeBuilder(
            uri=graphrag_settings.NEO4J_URI,
            username=graphrag_settings.NEO4J_USERNAME,
            password=graphrag_settings.NEO4J_PASSWORD,
            database=graphrag_settings.NEO4J_DATABASE,
            openai_api_key=openai_api_key,
            embedding_model="text-embedding-3-small",  # OpenAI embeddings
            llm_model="gpt-4o-mini",  # OpenAI LLM
        )
        
        log_info("Testing SimpleKGPipeline with political documents")
        
        async with kb:
            # Clear existing data first
            log_info("Clearing existing graph data...")
            await kb.clear_graph()
            
            # Get test documents
            data_dir = Path("data/input/examples")
            document_paths = []
            
            if data_dir.exists():
                for file_path in data_dir.glob("*.txt"):
                    document_paths.append(str(file_path))
                    log_info(f"Found document: {file_path.name}")
                
                for file_path in data_dir.glob("*.md"):
                    document_paths.append(str(file_path))
                    log_info(f"Found document: {file_path.name}")
            
            if not document_paths:
                print("ERROR: No test documents found in data/input/examples/")
                return
                
            log_info(f"Processing {len(document_paths)} documents with SimpleKGPipeline...")
            
            # Process documents using SimpleKGPipeline
            results = await kb.process_documents(document_paths)  # Process all documents
            
            log_info("Processing results:")
            log_info(f"Documents processed: {results['processed_documents']}")
            log_info(f"Successful: {results['successful']}")
            log_info(f"Failed: {results['failed']}")
            
            # Show any errors
            for result in results['results']:
                if result['status'] == 'error':
                    print(f"ERROR: Failed to process {result['document_path']}: {result['error']}")
            
            # Get graph statistics
            stats = results['graph_stats']
            log_info("Knowledge graph statistics:")
            for key, value in stats.items():
                log_info(f"  {key}: {value}")
            
            # Test search functionality if we have data
            if stats['chunks'] > 0:
                log_info("\nTesting search functionality...")
                search_results = await kb.search_documents(
                    query="GDPR privacy data protection",
                    top_k=3
                )
                
                # Handle RetrieverResult format properly
                if hasattr(search_results, 'items') and search_results.items:
                    log_info(f"Found {len(search_results.items)} search results:")
                    for i, result_item in enumerate(search_results.items, 1):
                        # Extract text from the result content
                        import json
                        try:
                            content_data = json.loads(result_item.content)
                            text_preview = content_data.get('text', '')[:200] + "..."
                            score = result_item.metadata.get('score', 'N/A')
                            log_info(f"Result {i} (Score: {score}):")
                            log_info(f"  Preview: {text_preview}")
                        except:
                            log_info(f"Result {i}: {result_item.content[:200]}...")
                else:
                    log_info(f"No search results found or unexpected format")
            
            log_info("SimpleKGPipeline test completed successfully!")
            
    except Exception as e:
        print(f"ERROR: SimpleKGPipeline test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())