#!/usr/bin/env python3
"""
Test the direct Exa.ai collector.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from src.etl.collectors import ExaDirectCollector


async def test_exa_direct_collector():
    """Test the direct Exa collector."""
    print("🔍 Testing Exa.ai Direct Collector")
    print("=" * 40)
    
    try:
        collector = ExaDirectCollector()
        
        # Test collection
        articles = await collector.collect_news(
            query="zalando",
            max_items=5,
            days_back=3
        )
        
        print(f"✅ Collected {len(articles)} articles")
        
        # Show article details
        for i, article in enumerate(articles, 1):
            print(f"\n📰 Article {i}:")
            print(f"  Title: {article['title'][:80]}...")
            print(f"  URL: {article['url']}")
            print(f"  Published: {article.get('published_date', 'Unknown')}")
            print(f"  Content length: {len(article.get('content', ''))} chars")
            print(f"  Source: {article.get('source', 'Unknown')}")
            print(f"  Score: {article.get('exa_score', 'N/A')}")
            
            # Show content preview
            content = article.get('content', '')
            if content:
                preview = content[:200].replace('\n', ' ')
                print(f"  Preview: {preview}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_exa_direct_collector())
    sys.exit(0 if success else 1)