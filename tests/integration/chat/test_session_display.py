"""Test script to verify session ID is displayed in streaming response."""

import asyncio
import aiohttp


async def test_streaming_with_session_id():
    """Test streaming chat to see session ID display."""

    chat_url = "http://localhost:8001/v1/chat/completions"
    chat_data = {
        "model": "political-monitoring-agent",
        "messages": [{"role": "user", "content": "What is GDPR?"}],
        "stream": True
    }

    print("🚀 Testing streaming chat with session ID display...\n")

    async with aiohttp.ClientSession() as session:
        async with session.post(chat_url, json=chat_data) as resp:
            if resp.status != 200:
                print(f"❌ Request failed: {resp.status}")
                text = await resp.text()
                print(f"Response: {text}")
                return

            print("✅ Streaming response:")
            print("-" * 80)

            # Read streaming response
            full_content = ""
            async for line in resp.content:
                line_text = line.decode('utf-8').strip()

                if line_text.startswith('data: '):
                    data_content = line_text[6:]  # Remove 'data: ' prefix

                    if data_content == '[DONE]':
                        break

                    try:
                        import json
                        chunk_data = json.loads(data_content)

                        if 'choices' in chunk_data and chunk_data['choices']:
                            delta = chunk_data['choices'][0].get('delta', {})
                            content = delta.get('content', '')

                            if content:
                                full_content += content
                                print(content, end='', flush=True)
                    except json.JSONDecodeError:
                        pass

            print("\n" + "-" * 80)

            # Check if session ID was displayed
            if "Session ID:" in full_content:
                print("\n✅ SUCCESS: Session ID is displayed in the response!")

                # Extract and show the session ID
                import re
                match = re.search(r'Session ID: (session_[a-f0-9]+)', full_content)
                if match:
                    session_id = match.group(1)
                    print(f"📋 Extracted Session ID: {session_id}")
                    print(f"\n💡 You can now use this session ID in the Graph Viz Chat Context feature!")
            else:
                print("\n⚠️  Session ID not found in response")


if __name__ == "__main__":
    asyncio.run(test_streaming_with_session_id())
