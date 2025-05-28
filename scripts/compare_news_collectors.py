#!/usr/bin/env python3
"""
Compare Apify and Exa.ai news collectors.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from src.etl.collectors import ApifyNewsCollector, ExaNewsCollector, ExaDirectCollector, get_available_collectors


async def test_collector(collector, name: str, query: str = "zalando"):
    """Test a specific collector."""
    print(f"\n=== Testing {name} ===")
    try:
        articles = await collector.collect_news(
            query=query,
            max_items=5,  # Small number for testing
            days_back=3
        )
        
        print(f"✅ {name}: Collected {len(articles)} articles")
        
        # Show first article details
        if articles:
            article = articles[0]
            print(f"  📰 Title: {article['title'][:80]}...")
            print(f"  🌐 URL: {article['url']}")
            print(f"  📅 Published: {article.get('published_date', 'Unknown')}")
            print(f"  📝 Content length: {len(article.get('content', ''))}")
            print(f"  🔖 Source: {article.get('source', 'Unknown')}")
            
            if name.lower() == 'exa':
                print(f"  ⭐ Score: {article.get('exa_score', 'N/A')}")
            
        return len(articles)
        
    except Exception as e:
        print(f"❌ {name}: Error - {e}")
        return 0


async def main():
    """Compare both collectors."""
    print("🔍 News Collector Comparison")
    print("=" * 40)
    
    # Check available collectors
    available = get_available_collectors()
    print(f"Available collectors: {available}")
    
    if not available:
        print("❌ No collectors available. Please configure API keys in .env:")
        print("   APIFY_API_TOKEN=your_token")
        print("   EXA_API_KEY=your_key")
        return
    
    query = "zalando"  # Test query
    results = {}
    
    # Test Apify if available
    if "apify" in available:
        try:
            apify_collector = ApifyNewsCollector()
            results["Apify"] = await test_collector(apify_collector, "Apify", query)
        except Exception as e:
            print(f"❌ Could not initialize Apify collector: {e}")
    
    # Test Exa Direct if available (preferred)
    if "exa_direct" in available:
        try:
            exa_direct_collector = ExaDirectCollector()
            results["Exa.ai Direct"] = await test_collector(exa_direct_collector, "Exa.ai Direct", query)
        except Exception as e:
            print(f"❌ Could not initialize Exa direct collector: {e}")
    
    # Test Exa Python client if available  
    if "exa" in available:
        try:
            exa_collector = ExaNewsCollector()
            results["Exa.ai Python"] = await test_collector(exa_collector, "Exa.ai Python", query)
        except Exception as e:
            print(f"❌ Could not initialize Exa collector: {e}")
    
    # Summary
    print(f"\n📊 Results Summary")
    print("=" * 20)
    for collector, count in results.items():
        print(f"{collector}: {count} articles")
    
    # Recommendations
    print(f"\n💡 Recommendations")
    print("=" * 20)
    if "exa_direct" in available and results.get("Exa.ai Direct", 0) > 0:
        print("✅ Exa.ai Direct provides full article content and is fast/reliable")
        print("   Set NEWS_COLLECTOR=exa_direct in your .env file (recommended)")
    elif "exa" in available and results.get("Exa.ai Python", 0) > 0:
        print("✅ Exa.ai Python client provides full content but may be slower")
        print("   Set NEWS_COLLECTOR=exa in your .env file")
    elif "apify" in available and results.get("Apify", 0) > 0:
        print("✅ Apify provides RSS headlines and summaries")
        print("   Set NEWS_COLLECTOR=apify in your .env file")
    else:
        print("❌ No working collectors found")


if __name__ == "__main__":
    asyncio.run(main())