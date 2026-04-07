"""Quick test to verify resume-safe re-embedding works."""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from neo4j import AsyncGraphDatabase
from src.config import settings

async def check_entities():
    """Check entity migration status."""
    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
    )
    
    try:
        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            # Check total entities
            query = """
            MATCH (e:Entity)
            WHERE e.name IS NOT NULL
            RETURN count(e) as total,
                   count(CASE WHEN e.embedding_model = 'text-embedding-ada-002' THEN 1 END) as migrated
            """
            result = await session.run(query)
            record = await result.single()
            
            print(f"Total entities: {record['total']:,}")
            print(f"Migrated to ada-002: {record['migrated']:,}")
            print(f"Pending: {record['total'] - record['migrated']:,}")
            
            if record['migrated'] > 0:
                # Show sample migrated entity
                sample_query = """
                MATCH (e:Entity)
                WHERE e.embedding_model = 'text-embedding-ada-002'
                RETURN e.uuid, e.name, e.embedding_model, e.embedding_migrated_at
                LIMIT 1
                """
                result = await session.run(sample_query)
                sample = await result.single()
                if sample:
                    print(f"\nSample migrated entity:")
                    print(f"  UUID: {sample['e.uuid']}")
                    print(f"  Name: {sample['e.name']}")
                    print(f"  Model: {sample['e.embedding_model']}")
                    print(f"  Migrated at: {sample['e.embedding_migrated_at']}")
    
    finally:
        await driver.close()

if __name__ == "__main__":
    asyncio.run(check_entities())
