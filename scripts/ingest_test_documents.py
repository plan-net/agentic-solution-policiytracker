#!/usr/bin/env python
"""Script to ingest test documents into the Neo4j knowledge graph."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import graphrag_settings
from src.graphrag.knowledge_builder import PoliticalKnowledgeBuilder
from src.processors.document_reader import DocumentReader


async def ingest_test_documents():
    """Ingest all test documents from data/input/examples into Neo4j."""
    print("🚀 Starting test document ingestion...")
    
    if not graphrag_settings.ENABLE_GRAPHRAG:
        print("❌ GraphRAG is disabled. Set ENABLE_GRAPHRAG=true in .env")
        return False
    
    # Initialize components
    document_reader = DocumentReader()
    
    async with PoliticalKnowledgeBuilder(
        uri=graphrag_settings.NEO4J_URI,
        username=graphrag_settings.NEO4J_USERNAME,
        password=graphrag_settings.NEO4J_PASSWORD,
        database=graphrag_settings.NEO4J_DATABASE,
    ) as kb:
        
        # Get list of test documents
        examples_path = Path("data/input/examples")
        if not examples_path.exists():
            print(f"❌ Examples directory not found: {examples_path}")
            return False
            
        document_files = list(examples_path.glob("*"))
        print(f"📁 Found {len(document_files)} documents to process")
        
        processed_documents = []
        processed_chunks = []
        
        # Process each document
        for doc_path in document_files:
            if doc_path.is_file():
                print(f"\n📄 Processing: {doc_path.name}")
                
                try:
                    # Read document content (returns tuple: text, metadata)
                    text, metadata = await document_reader.read_document(str(doc_path))
                    
                    if not text:
                        print(f"⚠️  No content extracted from {doc_path.name}")
                        continue
                    
                    # Generate document ID from path and content
                    import hashlib
                    doc_id = hashlib.sha256(f"{doc_path.name}_{text[:100]}".encode()).hexdigest()[:16]
                    
                    # Create document metadata
                    doc_data = {
                        "document_id": doc_id,
                        "path": str(doc_path),
                        "title": doc_path.stem.replace('_', ' ').title(),  # Create title from filename
                        "type": doc_path.suffix[1:] if doc_path.suffix else "unknown",
                        "container": "examples",
                        "extracted_at": metadata.extraction_metadata.get("timestamp", "2024-05-26T12:00:00"),
                        "size_bytes": len(text.encode()),
                        "word_count": len(text.split()),
                    }
                    
                    processed_documents.append(doc_data)
                    
                    # Create chunks (simple chunking for now)
                    chunk_size = graphrag_settings.GRAPHRAG_CHUNK_SIZE
                    chunk_overlap = graphrag_settings.GRAPHRAG_CHUNK_OVERLAP
                    
                    chunks = []
                    for i in range(0, len(text), chunk_size - chunk_overlap):
                        chunk_text = text[i:i + chunk_size]
                        if len(chunk_text) < 50:  # Skip very small chunks
                            continue
                            
                        chunk_data = {
                            "chunk_id": f"{doc_id}_chunk_{len(chunks)}",
                            "document_id": doc_id,
                            "text": chunk_text,
                            "position": i,
                            "chunk_index": len(chunks),
                        }
                        chunks.append(chunk_data)
                    
                    processed_chunks.extend(chunks)
                    print(f"✅ Created {len(chunks)} chunks for {doc_path.name}")
                    
                except Exception as e:
                    print(f"❌ Error processing {doc_path.name}: {e}")
                    continue
        
        # Ingest into Neo4j
        if processed_documents:
            print(f"\n🗄️  Ingesting {len(processed_documents)} documents and {len(processed_chunks)} chunks into Neo4j...")
            
            try:
                await kb.process_document_batch(processed_documents, processed_chunks)
                print("✅ Successfully ingested all documents!")
                
                # Show updated statistics
                stats = await kb.get_graph_stats()
                print(f"\n📊 Updated Graph Statistics:")
                for key, value in stats.items():
                    print(f"   {key}: {value}")
                    
            except Exception as e:
                print(f"❌ Error ingesting documents: {e}")
                return False
        else:
            print("❌ No documents were successfully processed")
            return False
    
    return True


async def show_sample_queries():
    """Show some sample Cypher queries to explore the data."""
    print("\n🔍 Sample Cypher Queries to Explore Your Data:")
    print("=" * 60)
    
    queries = [
        ("List all documents", "MATCH (d:Document) RETURN d.title, d.type, d.word_count ORDER BY d.word_count DESC"),
        ("Show document chunks", "MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk) RETURN d.title, count(c) as chunks ORDER BY chunks DESC"),
        ("Find largest chunks", "MATCH (c:Chunk) RETURN c.chunk_id, length(c.text) as size ORDER BY size DESC LIMIT 5"),
        ("Document statistics", "MATCH (d:Document) RETURN d.type, count(*) as count, avg(d.word_count) as avg_words ORDER BY count DESC"),
    ]
    
    for name, query in queries:
        print(f"\n-- {name}")
        print(f"   {query}")
    
    print(f"\n💡 Access Neo4j Browser at: http://localhost:7474")
    print(f"   Username: neo4j, Password: password123")


async def main():
    """Main function."""
    print("📚 Test Document Ingestion Script")
    print("=" * 50)
    
    success = await ingest_test_documents()
    
    if success:
        await show_sample_queries()
        print("\n✅ Document ingestion completed successfully!")
    else:
        print("\n❌ Document ingestion failed. Check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())