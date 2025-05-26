#!/usr/bin/env python
"""Test script to validate GraphRAG setup and basic functionality."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import graphrag_settings
from src.graphrag.knowledge_builder import PoliticalKnowledgeBuilder


async def test_neo4j_connection():
    """Test Neo4j connection and schema initialization."""
    print(f"🔍 Testing Neo4j connection...")
    print(f"   URI: {graphrag_settings.NEO4J_URI}")
    print(f"   Database: {graphrag_settings.NEO4J_DATABASE}")
    
    try:
        async with PoliticalKnowledgeBuilder(
            uri=graphrag_settings.NEO4J_URI,
            username=graphrag_settings.NEO4J_USERNAME,
            password=graphrag_settings.NEO4J_PASSWORD,
            database=graphrag_settings.NEO4J_DATABASE,
        ) as kb:
            print("✅ Connected to Neo4j successfully!")
            
            # Get graph statistics
            stats = await kb.get_graph_stats()
            print(f"\n📊 Graph Statistics:")
            for key, value in stats.items():
                print(f"   {key}: {value}")
            
            # Test creating a sample document
            print(f"\n🧪 Testing document creation...")
            test_doc = {
                "document_id": "test_doc_001",
                "path": "test/sample.txt",
                "title": "Test Document",
                "type": "test",
                "container": "test",
                "extracted_at": "2025-05-26T12:00:00",
                "size_bytes": 1024,
                "word_count": 150,
            }
            
            async with kb.driver.session(database=kb.database) as session:
                doc_id = await kb.create_document_node(session, test_doc)
                print(f"✅ Created test document: {doc_id}")
                
                # Create test chunks
                test_chunks = [
                    {
                        "chunk_id": "test_doc_001_chunk_0",
                        "document_id": "test_doc_001",
                        "text": "This is a test chunk for GraphRAG integration.",
                        "position": 0,
                        "chunk_index": 0,
                    },
                    {
                        "chunk_id": "test_doc_001_chunk_1",
                        "document_id": "test_doc_001",
                        "text": "This is another test chunk with more content.",
                        "position": 100,
                        "chunk_index": 1,
                    },
                ]
                
                chunks_created = await kb.create_chunk_nodes(session, test_chunks)
                print(f"✅ Created {chunks_created} test chunks")
            
            # Get updated stats
            stats = await kb.get_graph_stats()
            print(f"\n📊 Updated Graph Statistics:")
            for key, value in stats.items():
                print(f"   {key}: {value}")
                
    except Exception as e:
        print(f"❌ Failed to connect to Neo4j: {e}")
        print(f"\n💡 Make sure Neo4j is running:")
        print(f"   1. Start services: just services-up")
        print(f"   2. Check Neo4j browser: http://localhost:7474")
        print(f"   3. Verify credentials in .env file")
        return False
    
    return True


async def test_ray_data_pipeline():
    """Test Ray Data pipeline setup."""
    print(f"\n🔍 Testing Ray Data pipeline...")
    
    try:
        import ray
        from src.pipeline.document_processor import create_document_processor
        
        # Initialize Ray if not already
        if not ray.is_initialized():
            ray.init(local_mode=True)
            print("✅ Ray initialized in local mode")
        
        # Create processor
        processor = create_document_processor(
            neo4j_config={
                "uri": graphrag_settings.NEO4J_URI,
                "username": graphrag_settings.NEO4J_USERNAME,
                "password": graphrag_settings.NEO4J_PASSWORD,
            }
        )
        
        print("✅ Document processor created successfully")
        
        # Test chunking logic
        test_doc = {
            "document_id": "test_002",
            "path": "test.txt",
            "text": "This is a test document. " * 100,  # Create text with ~2400 chars
        }
        
        processor_ref = ray.get(processor)
        chunks = processor_ref._chunk_document(test_doc)
        print(f"✅ Chunking test: Created {len(chunks)} chunks from test document")
        
        ray.shutdown()
        
    except Exception as e:
        print(f"❌ Ray Data pipeline test failed: {e}")
        return False
    
    return True


async def main():
    """Run all tests."""
    print("🚀 GraphRAG Setup Test Suite")
    print("=" * 50)
    
    # Check if GraphRAG is enabled
    print(f"📋 GraphRAG Configuration:")
    print(f"   Enabled: {graphrag_settings.ENABLE_GRAPHRAG}")
    print(f"   Embedding Provider: {graphrag_settings.GRAPHRAG_EMBEDDING_PROVIDER}")
    print(f"   Chunk Size: {graphrag_settings.GRAPHRAG_CHUNK_SIZE}")
    print(f"   Chunk Overlap: {graphrag_settings.GRAPHRAG_CHUNK_OVERLAP}")
    
    if not graphrag_settings.ENABLE_GRAPHRAG:
        print(f"\n⚠️  GraphRAG is disabled. Set ENABLE_GRAPHRAG=true in .env to enable.")
    
    # Run tests
    neo4j_ok = await test_neo4j_connection()
    ray_ok = await test_ray_data_pipeline()
    
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print(f"   Neo4j Connection: {'✅ PASS' if neo4j_ok else '❌ FAIL'}")
    print(f"   Ray Data Pipeline: {'✅ PASS' if ray_ok else '❌ FAIL'}")
    
    if neo4j_ok and ray_ok:
        print("\n✅ All tests passed! GraphRAG setup is ready.")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())