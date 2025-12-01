"""Test graph viz with an existing session that has data."""
import asyncio
import aiohttp
import json

async def test_session():
    # Use the most recent session with data
    session_id = "session_6ae9cd17a1474cde"
    graph_url = "http://localhost:8001/graph-viz/api/graph/chat-context"
    
    print(f"🧪 Testing graph viz with session: {session_id}\n")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(graph_url, json={"session_id": session_id}) as resp:
            print(f"Status: {resp.status}")
            
            if resp.status == 200:
                result = await resp.json()
                print(f"\n✅ SUCCESS!")
                print(f"  Nodes: {len(result.get('nodes', []))}")
                print(f"  Links: {len(result.get('links', []))}")
                
                metadata = result.get('metadata', {})
                print(f"\n📋 Metadata:")
                print(f"  Session ID: {metadata.get('session_id')}")
                print(f"  Entity Count: {metadata.get('entity_count')}")
                print(f"  Relationship Count: {metadata.get('relationship_count')}")
                print(f"  Tools Used: {len(metadata.get('tools_used', []))}")
                
                if metadata.get('tools_used'):
                    print(f"\n🔧 Tools:")
                    for tool in metadata['tools_used'][:5]:
                        if isinstance(tool, dict):
                            print(f"    - {tool.get('tool_name')} at {tool.get('timestamp', 'unknown')}")
                        else:
                            print(f"    - {tool}")
                
                if result.get('nodes'):
                    print(f"\n📊 Sample Nodes (first 5):")
                    for node in result['nodes'][:5]:
                        print(f"    - {node.get('name')} ({node.get('type')})")
            else:
                text = await resp.text()
                print(f"❌ Failed: {text}")

asyncio.run(test_session())
