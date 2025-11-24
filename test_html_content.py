"""Test what HTML is in the response."""

import asyncio
import httpx


async def test_html_content():
    """Test and check HTML content in response."""

    print("🧪 Testing HTML Content in Response\n")

    test_query = "What is zalando?"

    print(f"📝 Test Query: {test_query}\n")
    print("🔄 Sending request...")

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
            print(f"❌ Request failed: {response.status_code}")
            return

        result = response.json()

        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]

            # Extract just the visualization section
            if "## 📊 Interactive Knowledge Graph Visualization" in content:
                viz_section = content.split("## 📊 Interactive Knowledge Graph Visualization")[1]

                print("=" * 80)
                print("VISUALIZATION SECTION:")
                print("=" * 80)
                print(viz_section[:1000])
                print("=" * 80)

                # Check for iframe
                if "<iframe" in viz_section:
                    print("\n✅ <iframe> tag found in API response")

                    # Extract iframe
                    iframe_start = viz_section.index("<iframe")
                    iframe_end = viz_section.index("</iframe>") + len("</iframe>")
                    iframe_html = viz_section[iframe_start:iframe_end]

                    print("\nIframe HTML:")
                    print("-" * 80)
                    print(iframe_html)
                    print("-" * 80)
                else:
                    print("\n❌ No <iframe> tag found in API response")
                    print("\nThis suggests the iframe was stripped before reaching the API")
            else:
                print("⚠️ No visualization section found in response")


if __name__ == "__main__":
    asyncio.run(test_html_content())
