#!/usr/bin/env python3
"""Quick diagnostic script to verify WebSearch tool configuration and test execution.

This script provides a fast way to:
1. Check if WebSearch is in allowed_tools
2. Test a single query to see if WebSearch is triggered
3. Display detailed logs of tool usage

Usage:
    python scripts/test_websearch_quick.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.claude_agent.agent_sdk import PolicyTrackerSDKAgent

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def check_configuration():
    """Check if WebSearch is properly configured."""
    print_section("STEP 1: Configuration Check")

    agent = PolicyTrackerSDKAgent(enable_web_search=True)
    allowed_tools = agent._get_allowed_tools()

    print(f"Total allowed tools: {len(allowed_tools)}\n")

    # Check for WebSearch
    websearch_present = "WebSearch" in allowed_tools
    print(f"{'✅' if websearch_present else '❌'} WebSearch in allowed_tools: {websearch_present}")

    # Check for DPA tools
    dpa_tools = [t for t in allowed_tools if 'web_search' in t]
    print(f"✅ DPA/Web search MCP tools: {len(dpa_tools)}")
    for tool in dpa_tools:
        print(f"   - {tool}")

    # Check for old Exa.ai tools
    has_old_web_search = "mcp__web_search__web_search" in allowed_tools
    has_old_search_news = "mcp__web_search__search_news" in allowed_tools

    if has_old_web_search or has_old_search_news:
        print(f"\n⚠️  WARNING: Old Exa.ai tools still present!")
        if has_old_web_search:
            print(f"   - mcp__web_search__web_search")
        if has_old_search_news:
            print(f"   - mcp__web_search__search_news")
    else:
        print(f"\n✅ Old Exa.ai tools correctly removed")

    # Print all allowed tools for reference
    print(f"\n📋 All allowed tools:")
    for i, tool in enumerate(sorted(allowed_tools), 1):
        print(f"   {i:2d}. {tool}")

    return websearch_present


async def test_websearch_execution():
    """Test WebSearch with a real query."""
    print_section("STEP 2: Execution Test")

    agent = PolicyTrackerSDKAgent(enable_web_search=True)

    query = "What are the latest news about EU AI regulations in 2026?"
    print(f"Query: {query}\n")
    print("Executing query... (this may take 30-60 seconds)\n")

    try:
        response, session_id, metadata = await agent.query(query)

        print(f"✅ Query completed successfully!\n")
        print(f"📊 Results:")
        print(f"   Session ID: {session_id}")
        print(f"   Turns: {metadata.get('turns', 0)}")
        print(f"   Model: {metadata.get('model', 'unknown')}")
        print(f"   Entities tracked: {metadata.get('entities_tracked', 0)}")

        # Check tools used
        tools_used = metadata.get('tools_used', [])
        print(f"\n🔧 Tools used ({len(tools_used)}):")
        if tools_used:
            for tool in tools_used:
                print(f"   - {tool}")
        else:
            print(f"   (none recorded in metadata)")

        # Check if WebSearch was used
        websearch_used = 'WebSearch' in str(tools_used)
        print(f"\n{'✅' if websearch_used else '⚠️ '} WebSearch triggered: {websearch_used}")

        if not websearch_used:
            print(f"\n⚠️  WebSearch was NOT triggered!")
            print(f"   Possible reasons:")
            print(f"   1. Agent chose other tools (knowledge graph, Bundestag API)")
            print(f"   2. WebSearch tool not properly registered with SDK")
            print(f"   3. MCP server connection issue")
            print(f"   4. Query answered from existing knowledge")

        # Print response preview
        print(f"\n📄 Response preview (first 500 chars):")
        print(f"   {response[:500]}...")
        print(f"\n   [Total response length: {len(response)} characters]")

        await agent.close()

        return websearch_used, metadata

    except Exception as e:
        print(f"\n❌ Query failed with error:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        await agent.close()
        return False, {}


async def test_websearch_disabled():
    """Test that WebSearch is NOT used when disabled."""
    print_section("STEP 3: Disabled Configuration Test")

    agent = PolicyTrackerSDKAgent(enable_web_search=False)
    allowed_tools = agent._get_allowed_tools()

    websearch_present = "WebSearch" in allowed_tools
    print(f"{'❌' if websearch_present else '✅'} WebSearch in allowed_tools (should be False): {websearch_present}")

    if websearch_present:
        print(f"\n⚠️  ERROR: WebSearch is present even though enable_web_search=False!")
        return False

    print(f"\n✅ WebSearch correctly excluded when disabled")
    return True


def print_summary(config_ok: bool, websearch_triggered: bool, disabled_ok: bool):
    """Print test summary."""
    print_section("SUMMARY")

    print(f"Configuration Check:  {'✅ PASS' if config_ok else '❌ FAIL'}")
    print(f"WebSearch Triggered:  {'✅ YES' if websearch_triggered else '⚠️  NO'}")
    print(f"Disabled Test:        {'✅ PASS' if disabled_ok else '❌ FAIL'}")

    print(f"\n" + "-" * 70)

    if config_ok and websearch_triggered and disabled_ok:
        print(f"✅ All checks passed! WebSearch is properly configured and working.")
    elif config_ok and not websearch_triggered:
        print(f"⚠️  WebSearch is configured but not triggered.")
        print(f"   This may be expected if:")
        print(f"   - The agent used knowledge graph or other tools instead")
        print(f"   - The query was answerable without web search")
        print(f"   Try a more recent/breaking news query to force web search")
    else:
        print(f"❌ Some checks failed. Review the output above for details.")

    print(f"-" * 70 + "\n")


async def main():
    """Run all diagnostic checks."""
    print("\n" + "=" * 70)
    print("  WebSearch Diagnostic Tool")
    print("  PolicyTracker Agent - Native Web Search Integration Test")
    print("=" * 70)

    # Step 1: Configuration check
    config_ok = check_configuration()

    if not config_ok:
        print(f"\n❌ Configuration check failed! WebSearch not in allowed_tools.")
        print(f"   Please verify that enable_web_search=True in agent initialization.")
        return

    # Step 2: Execution test
    websearch_triggered, metadata = await test_websearch_execution()

    # Step 3: Disabled configuration test
    disabled_ok = await test_websearch_disabled()

    # Summary
    print_summary(config_ok, websearch_triggered, disabled_ok)

    # Additional diagnostics if WebSearch not triggered
    if config_ok and not websearch_triggered:
        print_section("ADDITIONAL DIAGNOSTICS")
        print(f"If WebSearch is not triggering, check:")
        print(f"1. MCP server logs for connection issues")
        print(f"2. Agent system prompt (should mention WebSearch)")
        print(f"3. Try more explicit queries like:")
        print(f"   - 'Search the web for latest EU news'")
        print(f"   - 'Find recent articles about climate policy'")
        print(f"4. Check allowed_tools is passed to ClaudeAgentOptions")
        print(f"5. Verify ANTHROPIC_API_KEY environment variable is set")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
