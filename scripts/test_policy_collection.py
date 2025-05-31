#!/usr/bin/env python3
"""
Policy Collection System Test

Comprehensive test of the policy landscape collection system including:
- Policy query generation from client context
- PolicyLandscapeCollector functionality
- End-to-end collection workflow
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from etl.utils.policy_query_generator import PolicyQueryGenerator
from etl.collectors.policy_landscape import PolicyLandscapeCollector


async def test_policy_query_generation():
    """Test policy query generation from client context."""
    print("\n" + "=" * 60)
    print("🔍 TESTING POLICY QUERY GENERATION")
    print("=" * 60)

    try:
        # Initialize generator
        generator = PolicyQueryGenerator("data/context/client.yaml")

        # Test query generation
        print("\n📋 Generating policy queries...")
        queries = generator.generate_policy_queries()

        print(f"✅ Generated {len(queries)} queries")

        # Show summary by category
        summary = generator.get_query_summary()
        print(f"\n📊 Query Categories:")
        for category, count in summary.items():
            print(f"  • {category}: {count} queries")

        # Show sample queries
        print(f"\n📝 Sample Queries (first 5):")
        for i, query in enumerate(queries[:5]):
            print(f"  {i+1}. {query['category']}: {query['query'][:80]}...")
            print(f"     └─ {query['description']}")

        # Validate queries
        print(f"\n🔍 Validating queries...")
        is_valid, errors = generator.validate_queries()

        if is_valid:
            print("✅ Query validation passed")
        else:
            print("❌ Query validation failed:")
            for error in errors:
                print(f"  • {error}")
            return False

        return True

    except Exception as e:
        print(f"❌ Query generation test failed: {e}")
        return False


async def test_policy_collection_setup():
    """Test policy collection setup and configuration."""
    print("\n" + "=" * 60)
    print("⚙️ TESTING POLICY COLLECTION SETUP")
    print("=" * 60)

    try:
        # Check for API key
        api_key = os.getenv("EXA_API_KEY")
        if not api_key:
            print("⚠️ EXA_API_KEY not found - collection test will be skipped")
            return False

        print("✅ EXA_API_KEY found")

        # Initialize collector
        print("\n🔧 Initializing PolicyLandscapeCollector...")
        collector = PolicyLandscapeCollector(
            exa_api_key=api_key, client_context_path="data/context/client.yaml"
        )

        # Get collection stats
        print("\n📊 Getting collection statistics...")
        stats = await collector.get_collection_stats()

        print(f"✅ Collection setup completed:")
        print(f"  • Total queries: {stats['total_queries']}")
        print(f"  • Categories: {len(stats['categories'])}")
        print(f"  • Estimated API calls: {stats['estimated_api_calls']}")
        print(f"  • Max documents: {stats['estimated_max_documents']}")

        # Show categories
        print(f"\n📋 Policy Categories:")
        for category, count in stats["categories"].items():
            print(f"  • {category}: {count} queries")

        # Validation check
        if not stats["validation"]["is_valid"]:
            print(f"\n❌ Validation errors:")
            for error in stats["validation"]["errors"]:
                print(f"  • {error}")
            return False

        print(f"\n✅ Validation passed")
        return True

    except Exception as e:
        print(f"❌ Collection setup test failed: {e}")
        return False


async def test_policy_collection_limited():
    """Test limited policy collection (if API key available)."""
    print("\n" + "=" * 60)
    print("🚀 TESTING LIMITED POLICY COLLECTION")
    print("=" * 60)

    try:
        # Check for API key
        api_key = os.getenv("EXA_API_KEY")
        if not api_key:
            print("⚠️ EXA_API_KEY not found - skipping collection test")
            return True  # Not a failure, just skipped

        print("🔑 API key available, running limited collection test...")

        # Initialize collector
        collector = PolicyLandscapeCollector(
            exa_api_key=api_key, client_context_path="data/context/client.yaml"
        )

        print("\n🎯 Collecting policy documents (limited scope)...")
        print("  • Days back: 7")
        print("  • Max results per query: 2")
        print("  • Max concurrent queries: 2")

        # Run limited collection
        result = await collector.collect_policy_documents(
            days_back=7,
            max_results_per_query=2,  # Very limited for testing
            max_concurrent_queries=2,
        )

        print(f"\n✅ Collection completed!")
        print(f"  • Processing time: {result['processing_time_seconds']:.1f}s")
        print(f"  • Queries processed: {result['queries_processed']}")
        print(f"  • Queries failed: {result['queries_failed']}")
        print(f"  • Articles found: {result['total_articles_found']}")
        print(f"  • Documents saved: {result['documents_saved']}")

        # Show categories covered
        if result["categories_covered"]:
            print(f"\n📋 Categories covered:")
            for category, count in result["categories_covered"].items():
                print(f"  • {category}: {count} documents")

        # Show sample documents
        if result.get("sample_documents"):
            print(f"\n📄 Sample documents saved:")
            for doc in result["sample_documents"][:3]:
                print(f"  • {doc['filename']}")
                print(f"    Category: {doc['category']}")
                print(f"    Path: {doc['file_path']}")

        # Quality checks
        success_rate = (result["queries_processed"] - result["queries_failed"]) / max(
            result["queries_processed"], 1
        )

        print(f"\n📈 Quality Metrics:")
        print(f"  • Success rate: {success_rate:.1%}")
        print(
            f"  • Docs per query: {result['documents_saved'] / max(result['queries_processed'], 1):.1f}"
        )

        if result["failed_queries"]:
            print(f"\n⚠️ Failed queries ({len(result['failed_queries'])}):")
            for query in result["failed_queries"][:3]:
                print(f"  • {query[:50]}...")

        return True

    except Exception as e:
        print(f"❌ Collection test failed: {e}")
        return False


async def test_file_structure():
    """Test that policy file structure is properly set up."""
    print("\n" + "=" * 60)
    print("📁 TESTING FILE STRUCTURE")
    print("=" * 60)

    try:
        # Check policy directory exists
        policy_dir = Path("data/input/policy")

        if not policy_dir.exists():
            print(f"❌ Policy directory not found: {policy_dir}")
            return False

        print(f"✅ Policy directory exists: {policy_dir}")

        # Check for .gitkeep file
        gitkeep_file = policy_dir / ".gitkeep"
        if gitkeep_file.exists():
            print(f"✅ .gitkeep file found")
        else:
            print(f"⚠️ .gitkeep file not found (optional)")

        # Check if we can create a subdirectory
        test_dir = policy_dir / "2024-05"
        test_dir.mkdir(exist_ok=True)

        if test_dir.exists():
            print(f"✅ Can create subdirectories: {test_dir}")

            # Clean up test directory if empty
            try:
                test_dir.rmdir()
                print(f"✅ Cleaned up test directory")
            except OSError:
                print(f"ℹ️ Test directory not empty (contains files)")

        return True

    except Exception as e:
        print(f"❌ File structure test failed: {e}")
        return False


async def test_client_context_parsing():
    """Test client context YAML parsing."""
    print("\n" + "=" * 60)
    print("📄 TESTING CLIENT CONTEXT PARSING")
    print("=" * 60)

    try:
        context_file = Path("data/context/client.yaml")

        if not context_file.exists():
            print(f"❌ Client context file not found: {context_file}")
            return False

        print(f"✅ Client context file found: {context_file}")

        # Test loading
        generator = PolicyQueryGenerator(str(context_file))
        context_data = generator.context_data

        # Check required sections
        required_sections = [
            "company_terms",
            "core_industries",
            "primary_markets",
            "topic_patterns",
            "direct_impact_keywords",
        ]

        missing_sections = []
        for section in required_sections:
            if section not in context_data:
                missing_sections.append(section)
            else:
                print(f"✅ Section '{section}': {len(context_data[section])} items")

        if missing_sections:
            print(f"❌ Missing sections: {missing_sections}")
            return False

        # Check topic patterns structure
        topic_patterns = context_data.get("topic_patterns", {})
        print(f"\n📋 Topic Patterns ({len(topic_patterns)} categories):")
        for category, terms in topic_patterns.items():
            print(f"  • {category}: {len(terms)} terms")

        return True

    except Exception as e:
        print(f"❌ Client context test failed: {e}")
        return False


async def main():
    """Run all policy collection tests."""
    print("🧪 POLICY COLLECTION SYSTEM TEST")
    print("=" * 80)
    print("Testing policy landscape collection system for Flow 1")

    test_results = []

    # Run all tests
    tests = [
        ("Client Context Parsing", test_client_context_parsing),
        ("File Structure", test_file_structure),
        ("Policy Query Generation", test_policy_query_generation),
        ("Collection Setup", test_policy_collection_setup),
        ("Limited Collection", test_policy_collection_limited),
    ]

    for test_name, test_func in tests:
        try:
            print(f"\n🔧 Running: {test_name}")
            result = await test_func()
            test_results.append((test_name, result))

            if result:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")

        except Exception as e:
            print(f"💥 {test_name}: ERROR - {e}")
            test_results.append((test_name, False))

    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")

    print(f"\nOverall: {passed}/{total} tests passed ({passed/total:.1%})")

    if passed == total:
        print("\n🎉 All tests passed! Policy collection system is ready.")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Check the output above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
