"""
Verify that ada-002 re-embedding provides proper multilingual retrieval.

This script tests cross-lingual similarity on re-embedded entities to confirm
that the migration from text-embedding-3-small to ada-002 is working correctly.

Usage:
    python scripts/verify_ada002_migration.py
    python scripts/verify_ada002_migration.py --detailed
    python scripts/verify_ada002_migration.py --sample-size 50
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from neo4j import AsyncGraphDatabase
from openai import AsyncOpenAI
from src.config import settings


# Critical test cases (English-German pairs)
TEST_CASES = [
    # Cognates (should be >0.75)
    ("European Parliament", "Europäisches Parlament", 0.75),
    ("European Commission", "Europäische Kommission", 0.75),
    ("data protection", "Datenschutz", 0.75),

    # Queries (should be >0.70)
    ("penalties for GDPR violations", "Strafen für DSGVO-Verstöße", 0.70),
    ("artificial intelligence regulation", "Regulierung künstlicher Intelligenz", 0.70),

    # Acronyms (should be >0.65)
    ("GDPR", "DSGVO", 0.65),
    ("DSA", "Digitale-Dienste-Gesetz", 0.65),

    # Regulations (should be >0.70)
    ("Digital Services Act", "Digitale-Dienste-Gesetz", 0.70),
    ("General Data Protection Regulation", "Datenschutz-Grundverordnung", 0.70),

    # Specialized terms (should be >0.60)
    ("AI Act", "KI-Verordnung", 0.60),
    ("algorithmic transparency", "algorithmische Transparenz", 0.60),
    ("platform liability", "Plattformhaftung", 0.60),
]


async def get_embedding(client: AsyncOpenAI, text: str) -> List[float]:
    """Get ada-002 embedding for text."""
    response = await client.embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    return response.data[0].embedding


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    a_array = np.array(a)
    b_array = np.array(b)
    return float(np.dot(a_array, b_array) / (np.linalg.norm(a_array) * np.linalg.norm(b_array)))


async def check_migration_status(session) -> Dict[str, int]:
    """Check how many entities have been migrated."""
    query = """
    MATCH (e:Entity)
    WHERE e.name IS NOT NULL
    RETURN
      count(e) as total,
      count(CASE WHEN e.embedding_model = 'text-embedding-ada-002' THEN 1 END) as migrated,
      count(CASE WHEN e.embedding_model IS NULL OR e.embedding_model <> 'text-embedding-ada-002' THEN 1 END) as pending
    """

    result = await session.run(query)
    record = await result.single()

    return {
        'total': record['total'] if record else 0,
        'migrated': record['migrated'] if record else 0,
        'pending': record['pending'] if record else 0,
    }


async def sample_migrated_entities(session, limit: int = 20) -> List[Tuple[str, List[float]]]:
    """Get sample of migrated entities with their embeddings."""
    query = """
    MATCH (e:Entity)
    WHERE e.embedding_model = 'text-embedding-ada-002'
      AND e.name_embedding IS NOT NULL
    RETURN e.name as name, e.name_embedding as embedding
    LIMIT $limit
    """

    result = await session.run(query, {"limit": limit})
    records = await result.data()

    return [(r['name'], r['embedding']) for r in records]


async def test_cross_lingual_similarity(client: AsyncOpenAI) -> Dict:
    """Test cross-lingual similarity on critical test cases."""
    print("\n" + "=" * 80)
    print("CROSS-LINGUAL SIMILARITY TEST")
    print("=" * 80)
    print(f"\nTesting {len(TEST_CASES)} English-German pairs with ada-002...\n")

    results = []
    passed = 0
    failed = 0

    for english, german, threshold in TEST_CASES:
        # Get embeddings
        en_embedding = await get_embedding(client, english)
        de_embedding = await get_embedding(client, german)

        # Calculate similarity
        similarity = cosine_similarity(en_embedding, de_embedding)

        # Check if passed
        is_pass = similarity >= threshold
        status = "✓ PASS" if is_pass else "✗ FAIL"

        if is_pass:
            passed += 1
        else:
            failed += 1

        results.append({
            'english': english,
            'german': german,
            'threshold': threshold,
            'similarity': similarity,
            'passed': is_pass
        })

        print(f"{status:8} | {similarity:.3f} >= {threshold:.2f} | {english[:30]:30} ↔ {german[:30]:30}")

    print("\n" + "-" * 80)
    print(f"Results: {passed}/{len(TEST_CASES)} passed ({passed/len(TEST_CASES)*100:.1f}%)")
    print(f"Average similarity: {np.mean([r['similarity'] for r in results]):.3f}")
    print("=" * 80)

    return {
        'results': results,
        'passed': passed,
        'failed': failed,
        'total': len(TEST_CASES),
        'pass_rate': passed / len(TEST_CASES),
        'avg_similarity': np.mean([r['similarity'] for r in results])
    }


async def test_migrated_entities(session, client: AsyncOpenAI, sample_size: int = 20) -> Dict:
    """Test that migrated entities actually have ada-002 embeddings."""
    print("\n" + "=" * 80)
    print("MIGRATED ENTITY VERIFICATION")
    print("=" * 80)
    print(f"\nSampling {sample_size} migrated entities...\n")

    # Get sample entities
    entities = await sample_migrated_entities(session, sample_size)

    if not entities:
        print("❌ No migrated entities found!")
        return {'error': 'No migrated entities'}

    print(f"✓ Found {len(entities)} migrated entities")
    print("\nVerifying embeddings are valid ada-002 vectors (1536 dimensions)...")

    valid_count = 0
    invalid_count = 0

    for name, embedding in entities:
        if isinstance(embedding, list) and len(embedding) == 1536:
            valid_count += 1
        else:
            invalid_count += 1
            print(f"  ✗ Invalid embedding: {name} (dimension: {len(embedding) if isinstance(embedding, list) else 'not a list'})")

    print(f"\n✓ {valid_count}/{len(entities)} embeddings are valid (1536 dimensions)")

    if invalid_count > 0:
        print(f"⚠️  {invalid_count} embeddings are invalid!")

    # Test similarity between sample entities
    if len(entities) >= 2:
        print("\nTesting self-similarity (should be ~1.0)...")
        name1, emb1 = entities[0]
        similarity = cosine_similarity(emb1, emb1)
        print(f"  Self-similarity: {similarity:.6f} (expected: 1.000000)")

        if abs(similarity - 1.0) < 0.0001:
            print("  ✓ Self-similarity is correct")
        else:
            print("  ⚠️  Self-similarity is off - possible embedding corruption")

    return {
        'sampled': len(entities),
        'valid': valid_count,
        'invalid': invalid_count,
        'sample_names': [name for name, _ in entities[:5]]
    }


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify ada-002 migration and multilingual performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument("--detailed", action="store_true", help="Show detailed output")
    parser.add_argument("--sample-size", type=int, default=20, help="Number of entities to sample (default: 20)")
    parser.add_argument("--skip-entity-check", action="store_true", help="Skip entity verification (only test cross-lingual)")

    args = parser.parse_args()

    print("=" * 80)
    print("ADA-002 MIGRATION VERIFICATION")
    print("=" * 80)
    print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Database: {settings.NEO4J_DATABASE}")

    # Initialize clients
    openai_client = AsyncOpenAI()
    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
    )

    try:
        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            # Check migration status
            print("\n" + "=" * 80)
            print("MIGRATION STATUS")
            print("=" * 80)

            status = await check_migration_status(session)
            print(f"\nTotal entities:    {status['total']:,}")
            print(f"Migrated (ada-002): {status['migrated']:,} ({status['migrated']/status['total']*100:.1f}%)")
            print(f"Pending:           {status['pending']:,} ({status['pending']/status['total']*100:.1f}%)")

            if status['migrated'] == 0:
                print("\n❌ ERROR: No entities have been migrated yet!")
                print("   Please run: just reembed-phase1")
                return 1

            # Test migrated entities
            if not args.skip_entity_check:
                entity_results = await test_migrated_entities(session, openai_client, args.sample_size)

            # Test cross-lingual similarity
            similarity_results = await test_cross_lingual_similarity(openai_client)

        # Final summary
        print("\n" + "=" * 80)
        print("VERIFICATION SUMMARY")
        print("=" * 80)

        print(f"\n✓ Migration Status: {status['migrated']:,}/{status['total']:,} entities migrated ({status['migrated']/status['total']*100:.1f}%)")

        if not args.skip_entity_check:
            print(f"✓ Entity Verification: {entity_results['valid']}/{entity_results['sampled']} embeddings valid")

        print(f"✓ Cross-lingual Test: {similarity_results['passed']}/{similarity_results['total']} test cases passed ({similarity_results['pass_rate']*100:.1f}%)")
        print(f"✓ Average Similarity: {similarity_results['avg_similarity']:.3f}")

        # Overall assessment
        print("\n" + "=" * 80)

        if similarity_results['pass_rate'] >= 0.90:
            print("✅ VERIFICATION PASSED - ada-002 migration is working correctly!")
            print("\nThe multilingual retrieval is performing as expected:")
            print(f"  • {similarity_results['pass_rate']*100:.1f}% test pass rate (target: ≥90%)")
            print(f"  • {similarity_results['avg_similarity']:.3f} average similarity (target: ≥0.85)")
        elif similarity_results['pass_rate'] >= 0.75:
            print("⚠️  VERIFICATION PARTIAL - ada-002 is working but not optimal")
            print(f"\nPass rate: {similarity_results['pass_rate']*100:.1f}% (target: ≥90%)")
            print("Consider re-running migration or checking for issues.")
        else:
            print("❌ VERIFICATION FAILED - ada-002 may not be working correctly!")
            print(f"\nPass rate: {similarity_results['pass_rate']*100:.1f}% (target: ≥90%)")
            print("\nPossible issues:")
            print("  • Embeddings may not be using ada-002")
            print("  • Migration may have failed")
            print("  • Check embedding_model property in Neo4j")

        print("=" * 80)

        return 0 if similarity_results['pass_rate'] >= 0.90 else 1

    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        await driver.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
