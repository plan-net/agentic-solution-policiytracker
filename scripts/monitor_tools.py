#!/usr/bin/env python3
"""Real-time tool usage monitor for debugging WebSearch and other tools.

This script provides detailed logging of tool calls during agent execution,
helping you understand which tools are being invoked and why.

Usage:
    python scripts/monitor_tools.py "Your query here"
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.claude_agent.agent_sdk import PolicyTrackerSDKAgent

# Configure very detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Reduce noise from some loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class ToolCallMonitor:
    """Monitor tool calls during agent execution."""

    def __init__(self):
        self.tool_calls = []
        self.current_turn = 0

    def log_tool_call(self, tool_name: str, tool_input: Any = None):
        """Log a tool call."""
        self.current_turn += 1
        call_info = {
            "turn": self.current_turn,
            "tool": tool_name,
            "input": tool_input
        }
        self.tool_calls.append(call_info)

        print("\n" + "=" * 70)
        print(f"🔧 TOOL CALL #{self.current_turn}: {tool_name}")
        print("=" * 70)
        if tool_input:
            print(f"Input: {tool_input}")
        print()

    def print_summary(self):
        """Print summary of all tool calls."""
        print("\n" + "=" * 70)
        print(f"📊 TOOL CALL SUMMARY")
        print("=" * 70)
        print(f"Total tool calls: {len(self.tool_calls)}\n")

        if self.tool_calls:
            for call in self.tool_calls:
                print(f"Turn {call['turn']}: {call['tool']}")
        else:
            print("(No tool calls recorded)")

        # Count tool usage
        tool_counts = {}
        for call in self.tool_calls:
            tool = call['tool']
            tool_counts[tool] = tool_counts.get(tool, 0) + 1

        if tool_counts:
            print(f"\nTool usage frequency:")
            for tool, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
                print(f"  {tool}: {count}x")

        # Check if WebSearch was used
        websearch_used = any('WebSearch' in call['tool'] for call in self.tool_calls)
        print(f"\n{'✅' if websearch_used else '⚠️ '} WebSearch used: {websearch_used}")


async def run_query_with_monitoring(query: str):
    """Run a query with detailed tool monitoring."""
    print("\n" + "=" * 70)
    print("  TOOL USAGE MONITOR")
    print("=" * 70)
    print(f"\nQuery: {query}")
    print(f"Timestamp: {asyncio.get_event_loop().time()}")

    monitor = ToolCallMonitor()

    # Initialize agent
    agent = PolicyTrackerSDKAgent(
        enable_web_search=True,
        enable_bundestag=True,
        enable_todo=True
    )

    # Check configuration
    allowed_tools = agent._get_allowed_tools()
    print(f"\n📋 Allowed tools: {len(allowed_tools)}")
    print(f"   WebSearch enabled: {'WebSearch' in allowed_tools}")
    print(f"   TodoWrite enabled: {'TodoWrite' in allowed_tools}")
    print(f"   DPA tools: {sum(1 for t in allowed_tools if 'web_search' in t)}")

    print(f"\n⏳ Executing query... (this may take 30-60 seconds)\n")

    try:
        # Execute query
        response, session_id, metadata = await agent.query(query)

        print("\n" + "=" * 70)
        print("✅ QUERY COMPLETED")
        print("=" * 70)

        # Print metadata
        print(f"\n📊 Metadata:")
        print(f"   Session ID: {session_id}")
        print(f"   Turns: {metadata.get('turns', 0)}")
        print(f"   Model: {metadata.get('model', 'unknown')}")
        print(f"   Entities tracked: {metadata.get('entities_tracked', 0)}")

        # Print tools used from metadata
        tools_used = metadata.get('tools_used', [])
        print(f"\n🔧 Tools used (from metadata): {len(tools_used)}")
        if tools_used:
            for i, tool in enumerate(tools_used, 1):
                print(f"   {i}. {tool}")
                monitor.log_tool_call(str(tool))
        else:
            print(f"   (none recorded)")

        # Print response
        print(f"\n📄 Response:")
        print(f"{'-' * 70}")
        print(response)
        print(f"{'-' * 70}")
        print(f"Length: {len(response)} characters")

        # Print tool summary
        monitor.print_summary()

        await agent.close()

        return metadata

    except Exception as e:
        print(f"\n❌ ERROR during query execution:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        await agent.close()
        return None


async def main():
    """Main entry point."""
    # Get query from command line or use default
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        # Default queries to test different scenarios
        queries = [
            "What are the latest news about EU AI regulations?",
            "Find recent articles about climate policy in Germany",
            "Search the web for breaking news about data protection",
        ]

        print("\n" + "=" * 70)
        print("  No query provided. Choose a test query:")
        print("=" * 70)
        for i, q in enumerate(queries, 1):
            print(f"{i}. {q}")
        print(f"{len(queries) + 1}. Enter custom query")

        choice = input(f"\nEnter choice (1-{len(queries) + 1}): ").strip()

        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(queries):
                query = queries[choice_num - 1]
            elif choice_num == len(queries) + 1:
                query = input("Enter your query: ").strip()
            else:
                print("Invalid choice, using default query")
                query = queries[0]
        except ValueError:
            print("Invalid input, using default query")
            query = queries[0]

    # Run query with monitoring
    await run_query_with_monitoring(query)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
