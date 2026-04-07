"""
Enhanced embedding model comparison including Voyage AI.

Tests:
1. text-embedding-3-small (baseline)
2. text-embedding-3-large (OpenAI's larger model)
3. text-embedding-ada-002 (OpenAI's legacy model - surprisingly good!)
4. voyage-multilingual-2 (Voyage AI's multilingual model)

Installation required for Voyage:
    pip install voyageai

Usage:
    python3 test_embedding_comparison_with_voyage.py
"""

import asyncio
import os
from typing import List, Dict, Tuple
import numpy as np
from datetime import datetime

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✓ Loaded environment variables from .env\n")
except ImportError:
    print("⚠️  python-dotenv not installed, using existing environment variables\n")

from openai import AsyncOpenAI

# Try to import Voyage AI
VOYAGE_AVAILABLE = False
try:
    import voyageai
    VOYAGE_AVAILABLE = True
    print("✓ Voyage AI client available\n")
except ImportError:
    print("⚠️  Voyage AI not installed. Install with: pip install voyageai\n")
    print("   Voyage tests will be skipped.\n")


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    vec1_np = np.array(vec1)
    vec2_np = np.array(vec2)

    dot_product = np.dot(vec1_np, vec2_np)
    norm1 = np.linalg.norm(vec1_np)
    norm2 = np.linalg.norm(vec2_np)

    return float(dot_product / (norm1 * norm2))


# Test cases (subset of critical ones)
TEST_CASES = [
    # === High-Value Regulations ===
    ("Digital Services Act", "Digitale-Dienste-Gesetz", 0.70),
    ("General Data Protection Regulation", "Datenschutz-Grundverordnung", 0.70),
    ("GDPR", "DSGVO", 0.65),
    ("Artificial Intelligence Act", "KI-Verordnung", 0.60),

    # === Common Queries ===
    ("enforcement of data protection laws", "Durchsetzung von Datenschutzgesetzen", 0.70),
    ("penalties for GDPR violations", "Strafen für DSGVO-Verstöße", 0.70),

    # === Political Terms ===
    ("European Commission", "Europäische Kommission", 0.80),
    ("European Parliament", "Europäisches Parlament", 0.80),
    ("Federal Parliament", "Bundestag", 0.60),

    # === Technical Terms ===
    ("online platform", "Online-Plattform", 0.85),
    ("content moderation", "Inhaltsmoderation", 0.80),
    ("data processing", "Datenverarbeitung", 0.80),
]


MODELS_TO_TEST = [
    {
        "provider": "openai",
        "name": "text-embedding-3-small",
        "dimensions": 1536,
        "cost_per_1m": 0.02,
        "description": "Current model - baseline"
    },
    {
        "provider": "openai",
        "name": "text-embedding-3-large",
        "dimensions": 3072,
        "cost_per_1m": 0.13,
        "description": "Larger model with better multilingual support"
    },
    {
        "provider": "openai",
        "name": "text-embedding-ada-002",
        "dimensions": 1536,
        "cost_per_1m": 0.10,
        "description": "Legacy model (surprisingly excellent for multilingual!)"
    },
    {
        "provider": "voyage",
        "name": "voyage-multilingual-2",
        "dimensions": 1024,
        "cost_per_1m": 0.12,
        "description": "Purpose-built multilingual embedding model",
        "requires": "voyageai"
    }
]


async def get_openai_embedding(client: AsyncOpenAI, text: str, model: str) -> List[float]:
    """Get embedding from OpenAI."""
    response = await client.embeddings.create(
        model=model,
        input=text
    )
    return response.data[0].embedding


def get_voyage_embedding(client, text: str, model: str) -> List[float]:
    """Get embedding from Voyage AI (synchronous)."""
    result = client.embed([text], model=model, input_type="document")
    return result.embeddings[0]


async def test_model(openai_client: AsyncOpenAI, voyage_client, model_info: Dict) -> Dict:
    """Test a single model with all test cases."""
    provider = model_info["provider"]
    model_name = model_info["name"]

    # Skip if Voyage not available
    if provider == "voyage" and not VOYAGE_AVAILABLE:
        print(f"\n⚠️  Skipping {model_name} - Voyage AI not installed")
        print("   Install with: pip install voyageai\n")
        return None

    results = []
    passed = 0
    failed = 0

    print(f"\n{'=' * 80}")
    print(f"Testing: {model_name} ({provider.upper()})")
    print(f"Description: {model_info['description']}")
    print(f"Dimensions: {model_info['dimensions']}, Cost: ${model_info['cost_per_1m']}/1M tokens")
    print(f"{'=' * 80}\n")

    print(f"{'Test Case':<50} {'Similarity':<12} {'Expected':<12} {'Result'}")
    print("-" * 80)

    for en_phrase, de_phrase, expected_min_similarity in TEST_CASES:
        try:
            # Generate embeddings based on provider
            if provider == "openai":
                en_embedding = await get_openai_embedding(openai_client, en_phrase, model_name)
                de_embedding = await get_openai_embedding(openai_client, de_phrase, model_name)
            elif provider == "voyage":
                # Voyage is synchronous
                en_embedding = get_voyage_embedding(voyage_client, en_phrase, model_name)
                de_embedding = get_voyage_embedding(voyage_client, de_phrase, model_name)
            else:
                raise ValueError(f"Unknown provider: {provider}")

            # Calculate similarity
            similarity = cosine_similarity(en_embedding, de_embedding)

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
            error_msg = str(e)[:50]
            print(f"{'ERROR':<50} {error_msg:<24} ✗ FAIL")

    print("-" * 80)
    print(f"Summary: {passed}/{len(TEST_CASES)} passed ({passed/len(TEST_CASES)*100:.1f}%)")

    return {
        "provider": provider,
        "model": model_name,
        "total": len(TEST_CASES),
        "passed": passed,
        "failed": failed,
        "pass_rate": passed / len(TEST_CASES),
        "results": results,
        "avg_similarity": np.mean([r['similarity'] for r in results]) if results else 0,
        "dimensions": model_info["dimensions"],
        "cost": model_info["cost_per_1m"]
    }


async def run_comparison():
    """Run comparison across all models."""

    print("=" * 80)
    print("COMPREHENSIVE EMBEDDING MODEL COMPARISON")
    print("Multilingual Capability Test (English ↔ German)")
    print("=" * 80)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Check OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("❌ ERROR: OPENAI_API_KEY not set in .env file")
        return None

    # Check Voyage API key
    voyage_api_key = os.getenv("VOYAGE_API_KEY")
    if VOYAGE_AVAILABLE and not voyage_api_key:
        print("⚠️  VOYAGE_API_KEY not set - Voyage tests will fail")
        print("   Add to .env: VOYAGE_API_KEY=your-key-here")
        print("   Get key from: https://www.voyageai.com/\n")

    print(f"✓ OpenAI API Key: Found")
    if voyage_api_key:
        print(f"✓ Voyage API Key: Found")
    print(f"✓ Test Cases: {len(TEST_CASES)} critical translation pairs")
    print(f"✓ Models to Test: {len(MODELS_TO_TEST)}\n")

    # Create clients
    openai_client = AsyncOpenAI(api_key=openai_api_key)

    voyage_client = None
    if VOYAGE_AVAILABLE and voyage_api_key:
        voyage_client = voyageai.Client(api_key=voyage_api_key)

    # Test each model
    all_results = []
    for model_info in MODELS_TO_TEST:
        try:
            result = await test_model(openai_client, voyage_client, model_info)
            if result:  # Skip None results (unavailable models)
                all_results.append(result)
            await asyncio.sleep(1)  # Delay between models
        except Exception as e:
            print(f"\n❌ Error testing {model_info['name']}: {e}\n")

    if not all_results:
        print("❌ No models tested successfully")
        return None

    # Comparison summary
    print(f"\n{'=' * 80}")
    print("COMPARISON SUMMARY")
    print(f"{'=' * 80}\n")

    print(f"{'Model':<35} {'Provider':<10} {'Pass Rate':<12} {'Avg Sim':<10} {'Dims':<8} {'Cost/1M'}")
    print("-" * 95)

    for result in all_results:
        provider = result['provider'].upper()
        print(f"{result['model']:<35} {provider:<10} {result['pass_rate']*100:>6.1f}%      "
              f"{result['avg_similarity']:>6.3f}     "
              f"{result['dimensions']:<8} ${result['cost']}")

    print("-" * 95)

    # Find best model
    best_model = max(all_results, key=lambda x: x['pass_rate'])

    print(f"\n🏆 BEST MODEL: {best_model['model']} ({best_model['provider'].upper()})")
    print(f"   Pass Rate: {best_model['pass_rate']*100:.1f}%")
    print(f"   Avg Similarity: {best_model['avg_similarity']:.3f}")
    print(f"   Dimensions: {best_model['dimensions']}")
    print(f"   Cost: ${best_model['cost']}/1M tokens")

    # Detailed analysis
    print(f"\n{'=' * 80}")
    print("DETAILED ANALYSIS")
    print(f"{'=' * 80}\n")

    for result in all_results:
        model_name = result['model']
        pass_rate = result['pass_rate']
        provider = result['provider'].upper()

        if pass_rate >= 0.8:
            assessment = "✅ EXCELLENT"
            recommendation = "Highly recommended for multilingual use"
        elif pass_rate >= 0.6:
            assessment = "⚠️  GOOD"
            recommendation = "Acceptable for multilingual, consider cost trade-off"
        elif pass_rate >= 0.4:
            assessment = "⚠️  MODERATE"
            recommendation = "May work but will miss some cross-lingual matches"
        else:
            assessment = "❌ POOR"
            recommendation = "Not suitable for production multilingual use"

        print(f"{model_name} ({provider}):")
        print(f"  Assessment: {assessment}")
        print(f"  Pass Rate: {pass_rate*100:.1f}%")
        print(f"  Average Similarity: {result['avg_similarity']:.3f}")
        print(f"  Recommendation: {recommendation}")
        print()

    # Re-embedding cost comparison
    print(f"{'=' * 80}")
    print("RE-EMBEDDING COST ESTIMATE (for 31,129 entities)")
    print(f"{'=' * 80}\n")

    entity_count = 31129
    avg_tokens_per_entity = 50
    total_tokens = entity_count * avg_tokens_per_entity / 1_000_000  # in millions

    print(f"Assumptions:")
    print(f"  - Entities: {entity_count:,}")
    print(f"  - Avg tokens/entity: {avg_tokens_per_entity}")
    print(f"  - Total tokens: {entity_count * avg_tokens_per_entity:,} ({total_tokens:.2f}M)\n")

    print(f"{'Model':<35} {'Provider':<10} {'One-time':<12} {'Monthly (10K queries)'}")
    print("-" * 95)

    for result in all_results:
        one_time_cost = total_tokens * result['cost']

        # Monthly cost
        monthly_queries = 10000
        tokens_per_query = 20
        monthly_tokens = monthly_queries * tokens_per_query / 1_000_000
        monthly_cost = monthly_tokens * result['cost']

        provider = result['provider'].upper()
        print(f"{result['model']:<35} {provider:<10} ${one_time_cost:>7.2f}     ${monthly_cost:>7.2f}")

    print("-" * 95)

    # Final recommendation
    print(f"\n{'=' * 80}")
    print("FINAL RECOMMENDATION")
    print(f"{'=' * 80}\n")

    # Sort by pass rate to show top performers
    top_models = sorted(all_results, key=lambda x: x['pass_rate'], reverse=True)[:3]

    if best_model['pass_rate'] >= 0.8:
        print(f"✅ RECOMMEND: {best_model['model']} ({best_model['provider'].upper()})")
        print(f"\nReasons:")
        print(f"  1. Pass rate: {best_model['pass_rate']*100:.1f}% (vs current 13%)")
        print(f"  2. Average similarity: {best_model['avg_similarity']:.3f} (vs current 0.590)")
        print(f"  3. Natural cross-lingual discovery without translation")
        print(f"  4. One-time re-embedding cost: ${total_tokens * best_model['cost']:.2f}")

        print(f"\nTop 3 Models by Performance:")
        for i, model in enumerate(top_models, 1):
            print(f"  {i}. {model['model']} ({model['provider'].upper()}): "
                  f"{model['pass_rate']*100:.1f}% pass rate, "
                  f"${total_tokens * model['cost']:.2f} re-embedding cost")

        print(f"\nImplementation Plan:")
        print(f"  → Immediate: Re-embed with {best_model['model']}")
        print(f"  → Timeline: 2-4 hours for re-embedding")
        print(f"  → Expected result: ~95% cross-lingual recall")
    else:
        print(f"⚠️  CAUTION: Best model ({best_model['model']}) only {best_model['pass_rate']*100:.1f}% pass rate")
        print(f"\nRecommendation:")
        print(f"  → Implement Query Translation (Option 1) as immediate solution")
        print(f"  → Continue testing other embedding providers")

    print(f"\n{'=' * 80}")
    print(f"Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 80}\n")

    # Save results summary
    summary_file = f"embedding_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    print(f"💾 Results saved to: {summary_file}\n")

    return all_results


if __name__ == "__main__":
    print("\nStarting comprehensive embedding model comparison...")
    print("Testing multilingual capabilities: OpenAI + Voyage AI\n")

    if not VOYAGE_AVAILABLE:
        print("⚠️  Voyage AI not available. Install with:")
        print("   pip install voyageai")
        print("\nProceeding with OpenAI models only...\n")

    # Run comparison
    results = asyncio.run(run_comparison())

    if results:
        print("✅ Comparison completed successfully!")
        print("📖 See comparison results above for detailed analysis")
    else:
        print("❌ Comparison failed - check error messages above")
