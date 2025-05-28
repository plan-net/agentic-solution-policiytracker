#!/usr/bin/env python3
"""
Direct test of Exa.ai API without async.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from exa_py import Exa


def test_exa_direct():
    """Direct synchronous test of Exa API."""
    api_key = os.getenv("EXA_API_KEY")
    print(f"API Key: {api_key[:10]}..." if api_key else "No API key found")
    
    if not api_key:
        print("❌ No EXA_API_KEY found in environment")
        return
    
    print("🔍 Testing Exa.ai API directly...")
    
    try:
        exa = Exa(api_key=api_key)
        
        # Simple search first
        print("📡 Making simple search request...")
        result = exa.search(
            "zalando europe ecommerce",
            category="news", 
            num_results=3
        )
        
        print(f"✅ Search successful: {len(result.results)} results")
        
        for i, item in enumerate(result.results):
            print(f"  {i+1}. {item.title[:60]}...")
            print(f"     URL: {item.url[:50]}...")
            print(f"     Score: {getattr(item, 'score', 'N/A')}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = test_exa_direct()
    sys.exit(0 if success else 1)