"""Test chat endpoint to generate LangWatch traces."""
import asyncio
import json

import aiohttp


async def test_chat_request():
    """Send a test chat request to generate traces."""

    url = "http://localhost:8001/chat/v1/chat/completions"

    payload = {
        "model": "political-monitoring-agent",
        "messages": [
            {"role": "user", "content": "Hello! This is a test message for LangWatch tracing."}
        ],
        "stream": False,
    }

    print("Sending test request to chat endpoint...")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("=" * 60)

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                url, json=payload, timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                print(f"Status: {response.status}")

                if response.status == 200:
                    result = await response.json()
                    print("\nResponse received:")
                    print(json.dumps(result, indent=2))
                    print("\n" + "=" * 60)
                    print("✅ Request successful!")
                    print("Check LangWatch UI for traces at: http://localhost:5560")
                else:
                    text = await response.text()
                    print(f"Error response: {text}")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    print("LangWatch Trace Test")
    print("=" * 60)
    asyncio.run(test_chat_request())
