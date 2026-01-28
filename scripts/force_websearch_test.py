#!/usr/bin/env python3
"""Test script to force WebSearch usage with explicit queries."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.claude_agent.agent_sdk import PolicyTrackerSDKAgent


async def test_force_websearch():
    """Test queries that should force WebSearch usage."""

    # Queries designed to force web search
    test_queries = [
        "Search the web for breaking news about EU regulations from today",
        "Use web search to find latest articles about climate policy published this week",
        "Find web search results for recent developments in German data protection",
    ]

    agent = PolicyTrackerSDKAgent(enable_web_search=True)

    for i, query in enumerate(test_queries, 1):
        print("\n" + "=" * 70)
        print(f"TEST {i}/{len(test_queries)}")
        print("=" * 70)
        print(f"Query: {query}\n")

        try:
            response, session_id, metadata = await agent.query(query)

            tools_used = metadata.get('tools_used', [])
            websearch_used = 'WebSearch' in str(tools_used)

            print(f"\n{'✅' if websearch_used else '⚠️ '} WebSearch used: {websearch_used}")
            print(f"Tools: {tools_used[:3] if len(tools_used) > 3 else tools_used}")
            print(f"Response length: {len(response)} chars")

            if websearch_used:
                print(f"\n🎉 SUCCESS! WebSearch was triggered!")
                print(f"Response preview: {response[:300]}...")
                break

        except Exception as e:
            print(f"❌ Error: {e}")
            continue

    await agent.close()


if __name__ == "__main__":
    asyncio.run(test_force_websearch())
