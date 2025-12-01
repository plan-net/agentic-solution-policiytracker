"""Test script to verify Chat Context tracking integration."""

import asyncio
import json
import sys

import aiohttp


async def test_chat_and_context():
    """Test chat request and verify context tracking."""

    # Make a chat request
    chat_url = "http://localhost:8001/v1/chat/completions"
    chat_data = {
        "model": "political-monitoring-agent",
        "messages": [{"role": "user", "content": "What is the EU AI Act?"}],
        "stream": False
    }

    print("🚀 Making chat request...")
    async with aiohttp.ClientSession() as session:
        async with session.post(chat_url, json=chat_data) as resp:
            if resp.status != 200:
                print(f"❌ Chat request failed: {resp.status}")
                text = await resp.text()
                print(f"Response: {text}")
                return

            chat_response = await resp.json()
            print(f"✅ Chat request successful!")
            print(f"Response ID: {chat_response['id']}")

            # Extract message
            if chat_response.get("choices"):
                message = chat_response["choices"][0]["message"]["content"]
                print(f"Message preview: {message[:200]}...")

            # The session ID should be generated internally
            # Let's try to find it in the logs or check if context was tracked
            print("\n🔍 Checking if context was tracked...")

            # Try different session ID formats
            chat_id = chat_response['id']
            possible_session_ids = [
                f"session_{chat_id.replace('chatcmpl-', '')}",
                chat_id,
                f"session_{chat_id.split('-')[1] if '-' in chat_id else chat_id[:16]}"
            ]

            for session_id in possible_session_ids:
                context_url = f"http://localhost:8001/graph-viz/api/graph/context/{session_id}"
                print(f"  Trying session ID: {session_id}")

                async with session.get(context_url) as context_resp:
                    if context_resp.status == 200:
                        context_data = await context_resp.json()
                        print(f"  ✅ Context found!")
                        print(f"  Nodes: {len(context_data.get('nodes', []))}")
                        print(f"  Links: {len(context_data.get('links', []))}")
                        print(f"  Context data: {json.dumps(context_data, indent=2)}")
                        return
                    else:
                        print(f"  ❌ No context (status: {context_resp.status})")

            print("\n⚠️  Context not found with any session ID format")
            print("This could mean:")
            print("  1. Context tracking is working but session ID format is different")
            print("  2. No tools were executed (agents decided not to use knowledge graph)")
            print("  3. Context tracker integration needs debugging")


if __name__ == "__main__":
    asyncio.run(test_chat_and_context())
