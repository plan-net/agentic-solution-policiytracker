#!/usr/bin/env python3
"""
Simple Policy Collection Test

Direct test of policy components without dependencies.
"""

import sys
import os
from pathlib import Path

# Add src to path for imports (from _dev_testing subdirectory)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from etl.utils.policy_query_generator import PolicyQueryGenerator


def test_policy_query_generation():
    """Test policy query generation from client context."""
    print("🔍 Testing Policy Query Generation")
    print("-" * 50)
    
    try:
        # Initialize generator
        generator = PolicyQueryGenerator("data/context/client.yaml")
        
        # Test query generation
        queries = generator.generate_policy_queries()
        print(f"✅ Generated {len(queries)} queries")
        
        # Show summary by category
        summary = generator.get_query_summary()
        print(f"\n📊 Query Categories:")
        for category, count in summary.items():
            print(f"  • {category}: {count} queries")
        
        # Show sample queries
        print(f"\n📝 Sample Queries:")
        for i, query in enumerate(queries[:5]):
            print(f"  {i+1}. {query['category']}: {query['query']}")
        
        # Validate queries
        is_valid, errors = generator.validate_queries()
        print(f"\n🔍 Validation: {'✅ PASSED' if is_valid else '❌ FAILED'}")
        if errors:
            for error in errors:
                print(f"  • {error}")
        
        return is_valid
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_client_context():
    """Test client context file parsing."""
    print("\n📄 Testing Client Context")
    print("-" * 50)
    
    try:
        context_file = Path("data/context/client.yaml")
        
        if not context_file.exists():
            print(f"❌ Client context file not found: {context_file}")
            return False
        
        print(f"✅ Client context file found")
        
        # Test loading
        generator = PolicyQueryGenerator(str(context_file))
        context_data = generator.context_data
        
        # Check required sections
        required_sections = [
            'company_terms', 'core_industries', 'primary_markets',
            'topic_patterns', 'direct_impact_keywords'
        ]
        
        for section in required_sections:
            if section in context_data:
                print(f"✅ Section '{section}': {len(context_data[section])} items")
            else:
                print(f"❌ Missing section: {section}")
                return False
        
        # Show topic patterns
        topic_patterns = context_data.get('topic_patterns', {})
        print(f"\n📋 Topic Patterns ({len(topic_patterns)} categories):")
        for category, terms in topic_patterns.items():
            print(f"  • {category}: {len(terms)} terms")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_file_structure():
    """Test policy file structure."""
    print("\n📁 Testing File Structure")
    print("-" * 50)
    
    try:
        policy_dir = Path("data/input/policy")
        
        if not policy_dir.exists():
            print(f"❌ Policy directory not found: {policy_dir}")
            return False
        
        print(f"✅ Policy directory exists: {policy_dir}")
        
        # Check for .gitkeep
        gitkeep_file = policy_dir / ".gitkeep"
        if gitkeep_file.exists():
            print(f"✅ .gitkeep file found")
        
        # Test directory creation
        test_dir = policy_dir / "2024-05"
        test_dir.mkdir(exist_ok=True)
        
        if test_dir.exists():
            print(f"✅ Can create subdirectories")
            try:
                test_dir.rmdir()
                print(f"✅ Cleaned up test directory")
            except OSError:
                print(f"ℹ️ Test directory contains files")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def main():
    """Run simplified policy tests."""
    print("🧪 Policy Collection System - Simple Test")
    print("=" * 60)
    
    tests = [
        ("Client Context", test_client_context),
        ("File Structure", test_file_structure),
        ("Query Generation", test_policy_query_generation),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"\n{'✅ PASS' if result else '❌ FAIL'}: {test_name}")
        except Exception as e:
            print(f"\n💥 ERROR: {test_name} - {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Policy system is ready.")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed.")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    exit(main())