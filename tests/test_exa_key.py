#!/usr/bin/env python3
"""Quick test script for Exa API key validation."""

import asyncio
import os
import ssl
from datetime import datetime, timedelta

import aiohttp
import certifi
from dotenv import load_dotenv

# Load environment variables
load_dotenv("agentic-solution-policiytracker/.env")


async def test_exa_api():
    """Test Exa API key with a simple request."""
    api_key = os.getenv("EXA_API_KEY")

    if not api_key:
        print("❌ EXA_API_KEY not found in environment")
        return False

    print(f"🔑 Testing Exa API key: {api_key[:10]}...")

    # Exa API endpoint
    api_url = "https://api.exa.ai/search"

    # Prepare headers
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }

    # Simple test query - search for last 1 day, limit 2 results
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)

    payload = {
        "query": "technology news",  # Simple broad query
        "category": "news",
        "numResults": 2,
        "startPublishedDate": start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "contents": {"text": True}
    }

    print(f"📡 Sending test request to Exa API...")
    print(f"   Query: '{payload['query']}'")
    print(f"   Date range: {payload['startPublishedDate']} onwards")

    try:
        # Create SSL context with proper certificate verification
        ssl_context = ssl.create_default_context(cafile=certifi.where())

        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout, connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            async with session.post(api_url, headers=headers, json=payload) as response:
                status = response.status
                response_text = await response.text()

                if status == 200:
                    print(f"✅ SUCCESS! Exa API key is valid and has credits")

                    # Try to parse response
                    try:
                        import json
                        result = json.loads(response_text)
                        results = result.get("results", [])
                        print(f"   Retrieved {len(results)} articles")

                        if results:
                            first_article = results[0]
                            print(f"   Sample article:")
                            print(f"     - Title: {first_article.get('title', 'N/A')[:60]}...")
                            print(f"     - URL: {first_article.get('url', 'N/A')[:60]}...")
                            print(f"     - Score: {first_article.get('score', 'N/A')}")
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
                    print(f"   The API key is valid but you've exceeded your credits limit")
                    print(f"   Please top up at: https://dashboard.exa.ai/")
                    return False

                elif status == 429:
                    print(f"❌ RATE LIMIT EXCEEDED (429)")
                    print(f"   Error: {response_text}")
                    print(f"   Too many requests - wait and try again")
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
    print("Exa API Key Test")
    print("=" * 60)

    result = asyncio.run(test_exa_api())

    print("\n" + "=" * 60)
    if result:
        print("✅ Exa API key is working correctly")
    else:
        print("❌ Exa API key test failed")
        print("\nNext steps:")
        print("1. Verify the key in .env file")
        print("2. Get a new key from: https://dashboard.exa.ai/api-keys")
        print("3. Check credits at: https://dashboard.exa.ai/")
    print("=" * 60)
