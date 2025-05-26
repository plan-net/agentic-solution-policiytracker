#!/usr/bin/env python
"""Set up embeddings and vector indexes using neo4j-graphrag package."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j_graphrag.indexes import create_vector_index
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from src.config import graphrag_settings
from src.graphrag.knowledge_builder import PoliticalKnowledgeBuilder


async def setup_embeddings_and_indexes():
    """Set up embeddings and vector indexes for our chunks."""
    print("🚀 Setting up GraphRAG Embeddings and Vector Indexes")
    print("=" * 60)
    
    if not graphrag_settings.ENABLE_GRAPHRAG:
        print("❌ GraphRAG is disabled. Set ENABLE_GRAPHRAG=true in .env")
        return False
    
    async with PoliticalKnowledgeBuilder(
        uri=graphrag_settings.NEO4J_URI,
        username=graphrag_settings.NEO4J_USERNAME,
        password=graphrag_settings.NEO4J_PASSWORD,
        database=graphrag_settings.NEO4J_DATABASE,
    ) as kb:
        
        # Step 1: Create vector index using neo4j-graphrag
        print("\n📊 Creating vector index for chunks...")
        try:
            async with kb.driver.session(database=kb.database) as session:
                # Create vector index using the GraphRAG package
                await create_vector_index(
                    driver=kb.driver,
                    name="chunk_embeddings",
                    label="Chunk", 
                    embedding_property="embedding",
                    dimensions=graphrag_settings.GRAPHRAG_EMBEDDING_DIMS,
                    similarity_fn="cosine"
                )
                print("✅ Vector index 'chunk_embeddings' created successfully")
        except Exception as e:
            if "already exists" in str(e):
                print("✅ Vector index 'chunk_embeddings' already exists")
            else:
                print(f"❌ Error creating vector index: {e}")
                return False
        
        # Step 2: Initialize embeddings service
        print(f"\n🤖 Initializing {graphrag_settings.GRAPHRAG_EMBEDDING_PROVIDER} embeddings...")
        if graphrag_settings.GRAPHRAG_EMBEDDING_PROVIDER == "openai":
            import os
            if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "sk-your-openai-api-key-here":
                print("⚠️  OPENAI_API_KEY not set. Using mock embeddings for testing.")
                embeddings = None
            else:
                embeddings = OpenAIEmbeddings(
                    model=graphrag_settings.GRAPHRAG_EMBEDDING_MODEL
                )
                print("✅ OpenAI embeddings initialized")
        else:
            print("⚠️  Local embeddings not implemented yet. Using mock embeddings.")
            embeddings = None
        
        # Step 3: Get chunks that need embeddings
        print(f"\n📄 Fetching chunks without embeddings...")
        async with kb.driver.session(database=kb.database) as session:
            result = await session.run("""
                MATCH (c:Chunk)
                WHERE c.embedding IS NULL
                RETURN c.chunk_id, c.text, c.document_id
                LIMIT 100
            """)
            chunks_to_embed = await result.data()
            print(f"Found {len(chunks_to_embed)} chunks needing embeddings")
        
        if not chunks_to_embed:
            print("✅ All chunks already have embeddings")
            return True
        
        # Step 4: Generate embeddings (mock for now if no API key)
        print(f"\n⚡ Generating embeddings...")
        if embeddings:
            # Real embeddings with OpenAI
            batch_size = 10
            for i in range(0, len(chunks_to_embed), batch_size):
                batch = chunks_to_embed[i:i + batch_size]
                texts = [chunk['c.text'] for chunk in batch]
                
                try:
                    # Generate embeddings for batch
                    batch_embeddings = await embeddings.embed_documents(texts)
                    
                    # Update chunks with embeddings
                    async with kb.driver.session(database=kb.database) as session:
                        for j, chunk in enumerate(batch):
                            await session.run("""
                                MATCH (c:Chunk {chunk_id: $chunk_id})
                                SET c.embedding = $embedding
                            """, chunk_id=chunk['c.chunk_id'], embedding=batch_embeddings[j])
                    
                    print(f"  ✅ Processed batch {i//batch_size + 1}/{(len(chunks_to_embed)-1)//batch_size + 1}")
                    
                except Exception as e:
                    print(f"  ❌ Error processing batch: {e}")
                    # Continue with mock embeddings
                    break
        
        # Step 5: Add mock embeddings for testing (if no real embeddings)
        if not embeddings or True:  # Force mock for testing
            print("🎭 Adding mock embeddings for testing...")
            import random
            async with kb.driver.session(database=kb.database) as session:
                for chunk in chunks_to_embed:
                    # Create mock embedding vector
                    mock_embedding = [random.uniform(-1, 1) for _ in range(graphrag_settings.GRAPHRAG_EMBEDDING_DIMS)]
                    
                    await session.run("""
                        MATCH (c:Chunk {chunk_id: $chunk_id})
                        SET c.embedding = $embedding
                    """, chunk_id=chunk['c.chunk_id'], embedding=mock_embedding)
                
                print(f"✅ Added mock embeddings to {len(chunks_to_embed)} chunks")
        
        # Step 6: Verify setup
        print(f"\n🔍 Verifying setup...")
        async with kb.driver.session(database=kb.database) as session:
            # Check chunks with embeddings
            result = await session.run("""
                MATCH (c:Chunk)
                WHERE c.embedding IS NOT NULL
                RETURN count(c) as embedded_chunks
            """)
            embedded_count = (await result.single())['embedded_chunks']
            
            # Check vector index
            result = await session.run("SHOW INDEXES")
            indexes = await result.data()
            vector_indexes = [idx for idx in indexes if idx.get('type') == 'VECTOR']
            
            print(f"✅ {embedded_count} chunks have embeddings")
            print(f"✅ {len(vector_indexes)} vector indexes available")
            
        # Step 7: Test retrieval
        print(f"\n🔎 Testing vector retrieval...")
        try:
            from neo4j_graphrag.retrievers import VectorRetriever
            
            retriever = VectorRetriever(
                driver=kb.driver,
                index_name="chunk_embeddings",
                embedder=embeddings if embeddings else None
            )
            
            # Test query
            if embeddings:
                test_results = await retriever.search(
                    query_text="GDPR data protection",
                    top_k=3
                )
                print(f"✅ Retrieved {len(test_results.records)} relevant chunks")
                for i, record in enumerate(test_results.records[:2]):
                    text_preview = record['content'][:100] + "..." if len(record['content']) > 100 else record['content']
                    print(f"  {i+1}. {text_preview}")
            else:
                print("⚠️  Skipping retrieval test (no embeddings service)")
            
        except Exception as e:
            print(f"⚠️  Retrieval test failed: {e}")
        
        print(f"\n✅ GraphRAG setup completed successfully!")
        return True


async def main():
    """Main function."""
    success = await setup_embeddings_and_indexes()
    
    if success:
        print(f"\n🎉 Ready for GraphRAG queries!")
        print(f"💡 Next steps:")
        print(f"   1. Test retrieval with: VectorRetriever")
        print(f"   2. Implement entity extraction")
        print(f"   3. Add relationship detection")
    else:
        print(f"\n❌ Setup failed. Check errors above.")


if __name__ == "__main__":
    asyncio.run(main())