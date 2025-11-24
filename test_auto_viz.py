"""Quick test for automatic graph visualization feature."""

import asyncio
import httpx


async def test_auto_visualization():
    """Test that graph visualization is automatically appended to responses."""

    print("🧪 Testing Automatic Graph Visualization\n")

    # Test query that should trigger knowledge graph tools
    test_query = "What is s.Oliver and what regulations affect it?"

    print(f"📝 Test Query: {test_query}\n")
    print("🔄 Sending request to chat API...")

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "http://localhost:8001/v1/chat/completions",
            json={
                "model": "political-monitoring-agent",
                "messages": [
                    {"role": "user", "content": test_query}
                ],
                "stream": False
            }
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
            print("RESPONSE CONTENT:")
            print("=" * 80)
            print(content[:500])  # Show first 500 chars
            print("...")
            print("=" * 80)

            # Check if visualization was included
            if "graph visualization" in content.lower() or "iframe" in content.lower():
                print("\n✅ SUCCESS: Graph visualization was automatically appended!")
                print("   - Found iframe or visualization HTML in response")
            else:
                print("\n⚠️  WARNING: Graph visualization may not have been appended")
                print("   - Check if any knowledge graph tools were executed")

            # Check for iframe specifically
            if "<iframe" in content:
                print("   - ✅ Found <iframe> tag")
                print(f"   - Iframe URL: http://localhost:5173 with session parameter")

            # Check for visualization instructions
            if "How to Use" in content or "Click nodes" in content:
                print("   - ✅ Found visualization usage instructions")

        else:
            print("❌ No response content found in API result")
            print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(test_auto_visualization())
