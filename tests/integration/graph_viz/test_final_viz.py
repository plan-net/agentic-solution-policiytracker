"""Final test showing what users see in Open WebUI."""

import asyncio
import httpx


async def test_final_visualization():
    """Show final visualization format."""

    print("🎯 Final Visualization Test\n")
    print("=" * 80)
    print("This is what you'll see in Open WebUI:")
    print("=" * 80)

    test_query = "What companies are mentioned?"

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "http://localhost:8001/v1/chat/completions",
            json={
                "model": "political-monitoring-agent",
                "messages": [{"role": "user", "content": test_query}],
                "stream": False,
            },
        )

        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]

            # Show just the visualization section
            if "## 📊 Interactive Knowledge Graph Visualization" in content:
                viz_start = content.index("## 📊 Interactive Knowledge Graph Visualization")
                viz_section = content[viz_start:]

                print("\n" + viz_section)
                print("\n" + "=" * 80)

                # Extract the URL
                if "http://localhost:5173" in viz_section:
                    import re

                    url_match = re.search(r"http://localhost:5173[^\)]+", viz_section)
                    if url_match:
                        url = url_match.group(0)
                        print("\n✅ SUCCESS! You can click the link in Open WebUI")
                        print(f"\n📍 Direct URL: {url}")
                        print("\n💡 In Open WebUI, you'll see a clickable link that opens")
                        print("   the interactive 3D graph in a new browser tab!")


if __name__ == "__main__":
    asyncio.run(test_final_visualization())
