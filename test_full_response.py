"""Test to see full response including visualization."""

import asyncio
import httpx


async def test_full_response():
    """Test and print full response."""

    print("🧪 Testing Full Response\n")

    test_query = "What regulations affect online retail?"

    print(f"📝 Test Query: {test_query}\n")
    print("🔄 Sending request to chat API...")

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "http://localhost:8001/v1/chat/completions",
            json={
                "model": "political-monitoring-agent",
                "messages": [{"role": "user", "content": test_query}],
                "stream": False,
            },
        )

        if response.status_code != 200:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return

        result = response.json()

        # Extract response content
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]

            print("✅ Response received!\n")
            print("=" * 80)
            print("FULL RESPONSE:")
            print("=" * 80)
            print(content)
            print("=" * 80)

            # Check for visualization
            if "<iframe" in content:
                print("\n✅ SUCCESS: Found iframe tag in response!")
            else:
                print("\n⚠️ WARNING: No iframe found in response")

            if "graph visualization" in content.lower():
                print("✅ Found visualization heading")

            print(f"\nResponse length: {len(content)} characters")


if __name__ == "__main__":
    asyncio.run(test_full_response())
