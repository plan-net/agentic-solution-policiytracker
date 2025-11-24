"""Quick test for graph visualization - creates session and immediately tests visualization."""

import asyncio
import aiohttp
import json


async def test_graph_viz_immediately():
    """Test graph viz by creating session and immediately querying it."""

    chat_url = "http://localhost:8001/v1/chat/completions"
    graph_url = "http://localhost:8001/graph-viz/api/graph/chat-context"

    print("🚀 Step 1: Creating chat session...")

    chat_data = {
        "model": "political-monitoring-agent",
        "messages": [{"role": "user", "content": "What is GDPR?"}],
        "stream": True
    }

    session_id = None

    async with aiohttp.ClientSession() as session:
        # Step 1: Create chat session
        async with session.post(chat_url, json=chat_data) as resp:
            if resp.status != 200:
                print(f"❌ Chat request failed: {resp.status}")
                return

            print("✅ Chat session created, extracting session ID...")

            full_content = ""
            async for line in resp.content:
                line_text = line.decode('utf-8').strip()
                if line_text.startswith('data: '):
                    data_content = line_text[6:]
                    if data_content == '[DONE]':
                        break
                    try:
                        chunk_data = json.loads(data_content)
                        if 'choices' in chunk_data and chunk_data['choices']:
                            delta = chunk_data['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                full_content += content
                    except json.JSONDecodeError:
                        pass

            # Extract session ID
            import re
            match = re.search(r'Session ID: (session_[a-f0-9]+)', full_content)
            if match:
                session_id = match.group(1)
                print(f"📋 Extracted Session ID: {session_id}\n")
            else:
                print("❌ Could not extract session ID")
                return

        # Step 2: Immediately query graph visualization (within 5 min TTL!)
        print("🚀 Step 2: Querying graph visualization (within TTL)...")

        graph_data = {"session_id": session_id}

        async with session.post(graph_url, json=graph_data) as resp:
            if resp.status != 200:
                print(f"❌ Graph viz request failed: {resp.status}")
                text = await resp.text()
                print(f"Response: {text}")
                return

            result = await resp.json()

            print("✅ Graph visualization response:")
            print("-" * 80)
            print(json.dumps(result, indent=2))
            print("-" * 80)

            if result.get('nodes'):
                print(f"\n✅ SUCCESS: Graph has {len(result['nodes'])} nodes and {len(result['links'])} links!")
                print(f"\n💡 You can now view this in the UI at: http://localhost:5173")
                print(f"   Session ID: {session_id}")
            else:
                error = result.get('metadata', {}).get('error', 'Unknown error')
                print(f"\n⚠️  No nodes found. Error: {error}")


if __name__ == "__main__":
    asyncio.run(test_graph_viz_immediately())
