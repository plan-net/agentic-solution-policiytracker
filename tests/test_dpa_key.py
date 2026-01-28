#!/usr/bin/env python3
"""Quick test script for DPA API key validation."""

import asyncio
import os
import ssl
from datetime import datetime, timedelta

import aiohttp
import certifi
from dotenv import load_dotenv

# Load environment variables
load_dotenv("agentic-solution-policiytracker/.env")


async def test_dpa_api():
    """Test DPA API key with a simple request."""
    api_key = os.getenv("DPA_API_KEY")

    if not api_key:
        print("❌ DPA_API_KEY not found in environment")
        return False

    print(f"🔑 Testing DPA API key: {api_key[:10]}...")

    # DPA API endpoint
    api_url = "https://article-retriever.iq.dpa-ai-hub.de/articles/relevant"

    # Prepare headers
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }

    # Simple test query - search for last 1 day, limit 2 articles
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)

    payload = {
        "query": "germany",  # Simple broad query
        "limit": 2,
        "from_datetime": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
        "to_datetime": end_date.strftime("%Y-%m-%dT%H:%M:%S"),
        "response_format": "article_objects_markdown"
    }

    print(f"📡 Sending test request to DPA API...")
    print(f"   Query: '{payload['query']}'")
    print(f"   Date range: {payload['from_datetime']} to {payload['to_datetime']}")

    try:
        # Create SSL context with proper certificate verification
        ssl_context = ssl.create_default_context(cafile=certifi.where())

        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout, connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            async with session.post(api_url, headers=headers, json=payload) as response:
                status = response.status
                response_text = await response.text()

                if status == 200:
                    print(f"✅ SUCCESS! DPA API key is valid")

                    # Try to parse response
                    try:
                        result = await response.json()
                        context_items = result.get("context", [])
                        print(f"   Retrieved {len(context_items)} articles")

                        if context_items:
                            first_article = context_items[0]
                            print(f"   Sample article:")
                            print(f"     - Headline: {first_article.get('headline', 'N/A')[:60]}...")
                            print(f"     - URN: {first_article.get('urn', 'N/A')}")
                    except Exception as parse_error:
                        print(f"   Response received but parsing failed: {parse_error}")

                    return True

                elif status == 401:
                    print(f"❌ AUTHENTICATION FAILED (401)")
                    print(f"   Error: {response_text}")
                    print(f"   The API key is invalid or expired")
                    return False

                elif status == 402:
                    print(f"❌ PAYMENT REQUIRED (402)")
                    print(f"   Error: {response_text}")
                    print(f"   The API key may be valid but credits exhausted")
                    return False

                else:
                    print(f"❌ API ERROR ({status})")
                    print(f"   Response: {response_text[:500]}")
                    return False

    except asyncio.TimeoutError:
        print("❌ REQUEST TIMEOUT - API took too long to respond")
        return False

    except Exception as e:
        print(f"❌ REQUEST FAILED: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("DPA API Key Test")
    print("=" * 60)

    result = asyncio.run(test_dpa_api())

    print("\n" + "=" * 60)
    if result:
        print("✅ DPA API key is working correctly")
    else:
        print("❌ DPA API key test failed")
        print("\nNext steps:")
        print("1. Verify the key in .env file")
        print("2. Get a new key from: https://article-retriever.iq.dpa-ai-hub.de/docs")
        print("3. Check if credits/quota are available")
    print("=" * 60)
