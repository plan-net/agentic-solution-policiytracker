"""Debug script to test context tracking with tool execution."""

import asyncio
import aiohttp
import json


async def test_context_tracking_debug():
    """Test context tracking with a query that requires tool usage."""

    # Make a chat request
    chat_url = "http://localhost:8001/v1/chat/completions"
    chat_data = {
        "model": "political-monitoring-agent",
        "messages": [{"role": "user", "content": "Search for entities related to GDPR in the knowledge graph"}],
        "stream": True
    }

    print("🚀 Testing context tracking with explicit tool usage query...\n")

    session_id = None

    async with aiohttp.ClientSession() as session:
        # Make streaming chat request
        print("📤 Sending chat request...")
        async with session.post(chat_url, json=chat_data) as resp:
            if resp.status != 200:
                print(f"❌ Chat request failed: {resp.status}")
                return

            print("✅ Streaming response:\n" + "="*80)

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
                                print(content, end='', flush=True)
                    except json.JSONDecodeError:
                        pass

            print("\n" + "="*80)

            # Extract session ID from response
            import re
            match = re.search(r'Session ID: (session_[a-f0-9]+)', full_content)
            if match:
                session_id = match.group(1)
                print(f"\n📋 Extracted Session ID: {session_id}")
            else:
                print("\n⚠️  Could not extract session ID from response")
                return

        # Wait a moment for context to be tracked
        print("\n⏳ Waiting 2 seconds for context to be tracked...")
        await asyncio.sleep(2)

        # Try to fetch context
        print(f"\n🔍 Fetching context for session: {session_id}")
        context_url = "http://localhost:8001/graph-viz/api/graph/chat-context"
        context_data = {"session_id": session_id, "query": "GDPR"}

        async with session.post(context_url, json=context_data) as context_resp:
            print(f"   Status: {context_resp.status}")

            if context_resp.status == 200:
                context_data = await context_resp.json()
                print(f"   ✅ Context found!")
                print(f"   📊 Nodes: {len(context_data.get('nodes', []))}")
                print(f"   🔗 Links: {len(context_data.get('links', []))}")

                if context_data.get('nodes'):
                    print(f"\n   Sample nodes:")
                    for node in context_data['nodes'][:3]:
                        print(f"      - {node.get('name')} ({node.get('type')})")

                if context_data.get('metadata'):
                    print(f"\n   Metadata:")
                    print(f"      Tools used: {context_data['metadata'].get('tools_used', [])}")
                    print(f"      Entity count: {context_data['metadata'].get('entity_count', 0)}")
            else:
                error_text = await context_resp.text()
                print(f"   ❌ Context not found")
                print(f"   Response: {error_text}")

                print(f"\n🔍 Debugging info:")
                print(f"   - Session ID format: {session_id}")
                print(f"   - Response included tools? {('⚡ Executing Tools' in full_content)}")
                print(f"   - Response included planning? {('📋 Planning Execution' in full_content)}")


if __name__ == "__main__":
    asyncio.run(test_context_tracking_debug())
