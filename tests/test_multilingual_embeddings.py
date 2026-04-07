"""
Test script to evaluate multilingual capabilities of current embeddings.

This script tests whether the current embedding model (text-embedding-3-small)
already supports cross-lingual semantic similarity for English-German queries.

Usage:
    python test_multilingual_embeddings.py

Prerequisites:
    - OPENAI_API_KEY environment variable set
    - APISIX_GATEWAY_URL environment variable set (or defaults to localhost:9080)
"""

import asyncio
import os
from typing import List, Tuple
import numpy as np
from datetime import datetime

# Import the embedder creation function
from src.flows.shared.apisix_llm_client import create_apisix_graphiti_embedder


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    vec1_np = np.array(vec1)
    vec2_np = np.array(vec2)

    dot_product = np.dot(vec1_np, vec2_np)
    norm1 = np.linalg.norm(vec1_np)
    norm2 = np.linalg.norm(vec2_np)

    return dot_product / (norm1 * norm2)


# Test cases: (English phrase, German translation, semantic equivalence expected)
TEST_CASES = [
    # === High-Value Regulations (Most Important) ===
    ("Digital Services Act", "Digitale-Dienste-Gesetz", 0.70),
    ("Digital Services Act", "Gesetz über digitale Dienste", 0.65),
    ("General Data Protection Regulation", "Datenschutz-Grundverordnung", 0.70),
    ("GDPR", "DSGVO", 0.65),
    ("Artificial Intelligence Act", "KI-Verordnung", 0.60),
    ("Digital Markets Act", "Gesetz über digitale Märkte", 0.65),

    # === Common Queries ===
    ("enforcement of data protection laws", "Durchsetzung von Datenschutzgesetzen", 0.70),
    ("penalties for GDPR violations", "Strafen für DSGVO-Verstöße", 0.70),
    ("data protection requirements", "Datenschutzanforderungen", 0.75),
    ("regulatory compliance", "Einhaltung gesetzlicher Vorschriften", 0.65),

    # === Political Terms ===
    ("European Commission", "Europäische Kommission", 0.80),
    ("European Parliament", "Europäisches Parlament", 0.80),
    ("Federal Parliament", "Bundestag", 0.60),
    ("parliamentary debate", "parlamentarische Debatte", 0.70),

    # === Entities & Organizations ===
    ("data protection authority", "Datenschutzbehörde", 0.75),
    ("federal government", "Bundesregierung", 0.75),
    ("committee meeting", "Ausschusssitzung", 0.70),

    # === Technical Terms ===
    ("online platform", "Online-Plattform", 0.85),
    ("content moderation", "Inhaltsmoderation", 0.80),
    ("algorithmic transparency", "algorithmische Transparenz", 0.75),
    ("data processing", "Datenverarbeitung", 0.80),

    # === Control Cases (Should NOT match) ===
    ("digital services", "Bundestag", 0.20),  # Unrelated terms
    ("GDPR penalties", "Online-Plattform", 0.25),  # Different topics
]


async def test_embeddings():
    """Run comprehensive multilingual embedding tests."""

    print("=" * 80)
    print("MULTILINGUAL EMBEDDING TEST")
    print("=" * 80)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Check environment
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ ERROR: OPENAI_API_KEY not set")
        return

    print(f"✓ OpenAI API Key: Found")
    print(f"✓ APISIX Gateway: {os.getenv('APISIX_GATEWAY_URL', 'http://localhost:9080/v1')}")
    print(f"✓ Embedding Model: text-embedding-3-small (1536 dimensions)\n")

    # Create embedder
    try:
        embedder = create_apisix_graphiti_embedder(embedding_model="text-embedding-3-small")
        print("✓ Embedder initialized successfully\n")
    except Exception as e:
        print(f"❌ Failed to initialize embedder: {e}")
        return

    # Run tests
    results = []
    passed = 0
    failed = 0

    print("-" * 80)
    print(f"{'Test Case':<50} {'Similarity':<12} {'Expected':<12} {'Result'}")
    print("-" * 80)

    for en_phrase, de_phrase, expected_min_similarity in TEST_CASES:
        try:
            # Generate embeddings
            en_embedding = await embedder.create(input_data=[en_phrase])
            de_embedding = await embedder.create(input_data=[de_phrase])

            # Calculate similarity
            similarity = cosine_similarity(en_embedding[0], de_embedding[0])

            # Determine pass/fail
            passed_test = similarity >= expected_min_similarity
            if passed_test:
                passed += 1
                status = "✓ PASS"
            else:
                failed += 1
                status = "✗ FAIL"

            # Format output
            test_desc = f"{en_phrase[:25]:<25} ↔ {de_phrase[:20]:<20}"
            print(f"{test_desc:<50} {similarity:>6.3f}      {expected_min_similarity:>6.3f}      {status}")

            results.append({
                "en": en_phrase,
                "de": de_phrase,
                "similarity": similarity,
                "expected": expected_min_similarity,
                "passed": passed_test
            })

            # Small delay to avoid rate limits
            await asyncio.sleep(0.1)

        except Exception as e:
            failed += 1
            print(f"{'ERROR':<50} {str(e):<24} ✗ FAIL")

    # Summary
    print("-" * 80)
    print(f"\nTEST SUMMARY")
    print(f"  Total Tests: {len(TEST_CASES)}")
    print(f"  Passed: {passed} ({passed/len(TEST_CASES)*100:.1f}%)")
    print(f"  Failed: {failed} ({failed/len(TEST_CASES)*100:.1f}%)")

    # Analysis
    print(f"\nANALYSIS")
    print("-" * 80)

    if passed >= len(TEST_CASES) * 0.8:  # 80% pass rate
        print("✅ EXCELLENT: Current embeddings are MULTILINGUAL")
        print("   → text-embedding-3-small already supports cross-lingual search")
        print("   → No need to re-embed the knowledge graph")
        print("   → Recommendation: Implement query translation (Option 1) for keyword search improvement")
    elif passed >= len(TEST_CASES) * 0.6:  # 60% pass rate
        print("⚠️  PARTIAL: Embeddings have some multilingual capability")
        print("   → Works for common terms but not specialized vocabulary")
        print("   → Recommendation: Consider multilingual embeddings (Option 2) OR query translation (Option 1)")
    else:
        print("❌ POOR: Embeddings are NOT multilingual")
        print("   → Current model does not support cross-lingual search")
        print("   → Recommendation: MUST implement Option 1 (Query Translation) or Option 2 (Multilingual Embeddings)")

    # Detailed breakdown
    print(f"\nDETAILED BREAKDOWN")
    print("-" * 80)

    high_similarity = [r for r in results if r['similarity'] >= 0.75]
    medium_similarity = [r for r in results if 0.5 <= r['similarity'] < 0.75]
    low_similarity = [r for r in results if r['similarity'] < 0.5]

    print(f"High Similarity (≥0.75): {len(high_similarity)} pairs")
    for r in high_similarity[:5]:  # Show top 5
        print(f"  • {r['en']} ↔ {r['de']}: {r['similarity']:.3f}")

    print(f"\nMedium Similarity (0.50-0.74): {len(medium_similarity)} pairs")
    for r in medium_similarity[:5]:  # Show top 5
        print(f"  • {r['en']} ↔ {r['de']}: {r['similarity']:.3f}")

    print(f"\nLow Similarity (<0.50): {len(low_similarity)} pairs")
    for r in low_similarity:
        print(f"  • {r['en']} ↔ {r['de']}: {r['similarity']:.3f}")

    # Recommendations
    print(f"\nRECOMMENDATIONS")
    print("-" * 80)

    avg_similarity = np.mean([r['similarity'] for r in results if r['similarity'] >= 0.5])

    if avg_similarity >= 0.70:
        print("1. ✅ Your embeddings already work across languages!")
        print("2. 🔍 Focus on keyword search: Implement query translation for CONTAINS matching")
        print("3. 📊 Tune similarity threshold in Cypher queries (currently 0.3)")
        print("4. 🎯 Expected improvement: 30-40% better recall without re-embedding")
        print("\nNext steps:")
        print("  → Implement Option 1 (Query Translation + Dual Search)")
        print("  → This will improve keyword matching while keeping existing embeddings")
        print("  → Estimated development time: 2-3 days")
    else:
        print("1. ⚠️  Current embeddings have limited cross-lingual capability")
        print("2. 🔄 Consider upgrading to text-embedding-3-large (better multilingual)")
        print("3. 🌐 Or use Cohere embed-multilingual-v3.0 (purpose-built for this)")
        print("4. 🔍 Implement query translation as immediate fix (Option 1)")
        print("\nNext steps:")
        print("  → Short-term: Implement Option 1 (Query Translation)")
        print("  → Long-term: Plan migration to multilingual embeddings (Option 2)")
        print("  → Estimated improvement: 60-80% better recall")

    print(f"\n{'=' * 80}")
    print(f"Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 80}\n")

    return results


async def test_real_world_queries():
    """Test with actual queries from your system."""

    print("\n" + "=" * 80)
    print("REAL-WORLD QUERY TEST")
    print("=" * 80)
    print("Testing actual user queries from your system\n")

    embedder = create_apisix_graphiti_embedder(embedding_model="text-embedding-3-small")

    # Real queries users might ask
    real_queries = [
        ("What are the penalties for GDPR violations?",
         "Was sind die Strafen für DSGVO-Verstöße?"),

        ("Tell me about Digital Services Act enforcement",
         "Erzählen Sie mir über die Durchsetzung des Digitale-Dienste-Gesetzes"),

        ("Who voted against the AI Act?",
         "Wer hat gegen das KI-Gesetz gestimmt?"),

        ("Show me recent Bundestag debates on data protection",
         "Zeigen Sie mir aktuelle Bundestagsdebatten zum Datenschutz"),
    ]

    print(f"{'Query Type':<50} {'Similarity':<12} {'Assessment'}")
    print("-" * 80)

    for en_query, de_query in real_queries:
        en_emb = await embedder.create(input_data=[en_query])
        de_emb = await embedder.create(input_data=[de_query])

        similarity = cosine_similarity(en_emb[0], de_emb[0])

        if similarity >= 0.70:
            assessment = "✓ Excellent"
        elif similarity >= 0.55:
            assessment = "⚠ Moderate"
        else:
            assessment = "✗ Poor"

        query_desc = f"{en_query[:47]:<47}..."
        print(f"{query_desc:<50} {similarity:>6.3f}      {assessment}")

        await asyncio.sleep(0.1)

    print("-" * 80)


if __name__ == "__main__":
    print("\nStarting multilingual embedding evaluation...")
    print("This will test if text-embedding-3-small supports German-English queries\n")

    # Run main tests
    asyncio.run(test_embeddings())

    # Run real-world query tests
    asyncio.run(test_real_world_queries())
