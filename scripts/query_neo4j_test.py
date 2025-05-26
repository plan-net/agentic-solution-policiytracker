#!/usr/bin/env python
"""Quick script to test Neo4j queries and verify our data."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import graphrag_settings
from src.graphrag.knowledge_builder import PoliticalKnowledgeBuilder


async def run_test_queries():
    """Run some test queries to verify our data."""
    print("🔍 Testing Neo4j Queries")
    print("=" * 40)
    
    async with PoliticalKnowledgeBuilder(
        uri=graphrag_settings.NEO4J_URI,
        username=graphrag_settings.NEO4J_USERNAME,
        password=graphrag_settings.NEO4J_PASSWORD,
        database=graphrag_settings.NEO4J_DATABASE,
    ) as kb:
        
        # Query 1: List all documents
        print("\n📄 Documents in Graph:")
        async with kb.driver.session(database=kb.database) as session:
            result = await session.run("""
                MATCH (d:Document) 
                RETURN d.title, d.type, d.word_count, d.size_bytes
                ORDER BY d.word_count DESC
            """)
            documents = await result.data()
            for doc in documents:
                print(f"  • {doc['d.title']} ({doc['d.type']}) - {doc['d.word_count']:,} words")
        
        # Query 2: Chunk statistics
        print(f"\n📊 Chunk Statistics:")
        async with kb.driver.session(database=kb.database) as session:
            result = await session.run("""
                MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)
                RETURN d.title, count(c) as chunk_count, 
                       avg(length(c.text)) as avg_chunk_size
                ORDER BY chunk_count DESC
            """)
            chunk_stats = await result.data()
            for stat in chunk_stats:
                print(f"  • {stat['d.title']}: {stat['chunk_count']} chunks (avg {stat['avg_chunk_size']:.0f} chars)")
        
        # Query 3: Find documents with keywords
        print(f"\n🔎 Documents mentioning 'GDPR':")
        async with kb.driver.session(database=kb.database) as session:
            result = await session.run("""
                MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)
                WHERE toLower(c.text) CONTAINS 'gdpr'
                RETURN DISTINCT d.title, count(c) as mentions
                ORDER BY mentions DESC
            """)
            gdpr_docs = await result.data()
            for doc in gdpr_docs:
                print(f"  • {doc['d.title']}: {doc['mentions']} chunks")
        
        # Query 4: Find documents mentioning AI
        print(f"\n🤖 Documents mentioning 'AI' or 'artificial intelligence':")
        async with kb.driver.session(database=kb.database) as session:
            result = await session.run("""
                MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)
                WHERE toLower(c.text) CONTAINS 'artificial intelligence' 
                   OR toLower(c.text) CONTAINS ' ai '
                   OR toLower(c.text) CONTAINS 'ai act'
                RETURN DISTINCT d.title, count(c) as mentions
                ORDER BY mentions DESC
            """)
            ai_docs = await result.data()
            for doc in ai_docs:
                print(f"  • {doc['d.title']}: {doc['mentions']} chunks")
        
        # Query 5: Sample chunk content
        print(f"\n📝 Sample Chunk Content:")
        async with kb.driver.session(database=kb.database) as session:
            result = await session.run("""
                MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)
                WHERE d.title CONTAINS 'AI Act'
                RETURN c.text
                LIMIT 1
            """)
            sample = await result.single()
            if sample:
                text = sample['c.text'][:200] + "..." if len(sample['c.text']) > 200 else sample['c.text']
                print(f"  {text}")
        
        # Final stats
        stats = await kb.get_graph_stats()
        print(f"\n📈 Overall Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(run_test_queries())