#!/usr/bin/env python3
"""
Simple test of Exa.ai API.
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

from exa_py import Exa


async def test_exa_simple():
    """Simple synchronous test of Exa API."""
    api_key = os.getenv("EXA_API_KEY")
    print(f"API Key: {api_key[:10]}..." if api_key else "No API key found")
    
    if not api_key:
        print("❌ No EXA_API_KEY found in environment")
        return
    
    print("🔍 Testing Exa.ai API...")
    
    try:
        exa = Exa(api_key=api_key)
        
        # Simple search without content
        print("📡 Making search request...")
        result = exa.search(
            "zalando",
            category="news", 
            num_results=3
        )
        
        print(f"✅ Search successful: {len(result.results)} results")
        
        for i, item in enumerate(result.results):
            print(f"  {i+1}. {item.title}")
            print(f"     URL: {item.url}")
            if hasattr(item, 'published_date'):
                print(f"     Date: {item.published_date}")
        
        # Test with content
        print("\n📄 Testing search with content...")
        result_with_content = exa.search_and_contents(
            "zalando",
            text=True,
            category="news",
            num_results=2
        )
        
        print(f"✅ Content search successful: {len(result_with_content.results)} results")
        
        if result_with_content.results:
            first = result_with_content.results[0]
            print(f"  Title: {first.title}")
            print(f"  Content length: {len(first.text) if hasattr(first, 'text') and first.text else 0}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_exa_simple())