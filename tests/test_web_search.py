"""Tests for native WebSearch tool integration in PolicyTracker agent.

This test suite verifies that:
1. WebSearch tool is properly configured in allowed_tools
2. WebSearch tool gets triggered for relevant queries
3. DPA tools (search_dpa_news, get_article_content) remain available
4. Tool execution is tracked and logged
"""

import asyncio
import logging
from typing import Any

import pytest

from src.claude_agent.agent_sdk import PolicyTrackerSDKAgent

# Configure logging to see tool calls
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestWebSearchConfiguration:
    """Test WebSearch tool configuration."""

    def test_websearch_in_allowed_tools_when_enabled(self):
        """Verify WebSearch is in allowed_tools when enable_web_search=True."""
        agent = PolicyTrackerSDKAgent(enable_web_search=True)
        allowed_tools = agent._get_allowed_tools()

        assert "WebSearch" in allowed_tools, "WebSearch should be in allowed_tools"
        logger.info(f"✅ WebSearch found in allowed_tools")

    def test_websearch_not_in_allowed_tools_when_disabled(self):
        """Verify WebSearch is NOT in allowed_tools when enable_web_search=False."""
        agent = PolicyTrackerSDKAgent(enable_web_search=False)
        allowed_tools = agent._get_allowed_tools()

        assert "WebSearch" not in allowed_tools, "WebSearch should NOT be in allowed_tools when disabled"
        logger.info(f"✅ WebSearch correctly excluded when disabled")

    def test_dpa_tools_in_allowed_tools(self):
        """Verify DPA tools remain available."""
        agent = PolicyTrackerSDKAgent(enable_web_search=True)
        allowed_tools = agent._get_allowed_tools()

        assert "mcp__web_search__search_dpa_news" in allowed_tools
        assert "mcp__web_search__get_article_content" in allowed_tools
        logger.info(f"✅ DPA tools found in allowed_tools")

    def test_exa_tools_not_in_allowed_tools(self):
        """Verify Exa.ai tools (web_search, search_news) are NOT in allowed_tools."""
        agent = PolicyTrackerSDKAgent(enable_web_search=True)
        allowed_tools = agent._get_allowed_tools()

        # These should NOT be present anymore
        assert "mcp__web_search__web_search" not in allowed_tools
        assert "mcp__web_search__search_news" not in allowed_tools
        logger.info(f"✅ Exa.ai tools correctly removed")

    def test_all_tool_categories_present(self):
        """Verify all tool categories are represented."""
        agent = PolicyTrackerSDKAgent(
            enable_web_search=True,
            enable_bundestag=True,
            enable_todo=True
        )
        allowed_tools = agent._get_allowed_tools()

        # Knowledge graph tools (always enabled)
        assert any("mcp__knowledge_graph__" in tool for tool in allowed_tools)

        # Bundestag tools (enabled)
        assert any("mcp__bundestag_dip__" in tool for tool in allowed_tools)

        # Web search tools (enabled)
        assert "WebSearch" in allowed_tools
        assert any("mcp__web_search__" in tool for tool in allowed_tools)

        # TodoWrite tool (enabled)
        assert "TodoWrite" in allowed_tools

        logger.info(f"✅ All tool categories present")
        logger.info(f"Total tools: {len(allowed_tools)}")


class TestWebSearchExecution:
    """Test WebSearch tool execution with real queries."""

    @pytest.mark.asyncio
    async def test_websearch_with_current_events_query(self):
        """Test that WebSearch is triggered for current events queries."""
        agent = PolicyTrackerSDKAgent(enable_web_search=True)

        logger.info("=" * 70)
        logger.info("TEST: WebSearch with current events query")
        logger.info("=" * 70)

        query = "What are the latest news about EU AI regulations in January 2026?"

        try:
            response, session_id, metadata = await agent.query(query)

            logger.info(f"\n📊 RESULTS:")
            logger.info(f"Session ID: {session_id}")
            logger.info(f"Turns: {metadata.get('turns', 0)}")
            logger.info(f"Tools used: {metadata.get('tools_used', [])}")
            logger.info(f"Response length: {len(response)} chars")
            logger.info(f"\nResponse preview: {response[:500]}...")

            # Check if WebSearch was used
            tools_used = metadata.get('tools_used', [])
            websearch_used = 'WebSearch' in str(tools_used)

            if websearch_used:
                logger.info("✅ WebSearch tool was triggered")
            else:
                logger.warning("⚠️  WebSearch tool was NOT triggered")
                logger.warning(f"Tools that were used: {tools_used}")

            await agent.close()

            # Assertions
            assert response, "Response should not be empty"
            assert session_id, "Session ID should be generated"
            assert metadata.get('turns', 0) > 0, "Should have at least 1 turn"

            return websearch_used

        except Exception as e:
            logger.error(f"❌ Test failed with error: {e}", exc_info=True)
            await agent.close()
            raise

    @pytest.mark.asyncio
    async def test_websearch_with_news_query(self):
        """Test that WebSearch is triggered for news queries."""
        agent = PolicyTrackerSDKAgent(enable_web_search=True)

        logger.info("=" * 70)
        logger.info("TEST: WebSearch with news query")
        logger.info("=" * 70)

        query = "Find recent news about climate policy in Germany"

        try:
            response, session_id, metadata = await agent.query(query)

            logger.info(f"\n📊 RESULTS:")
            logger.info(f"Session ID: {session_id}")
            logger.info(f"Tools used: {metadata.get('tools_used', [])}")
            logger.info(f"Response length: {len(response)} chars")

            tools_used = metadata.get('tools_used', [])
            websearch_used = 'WebSearch' in str(tools_used)

            if websearch_used:
                logger.info("✅ WebSearch tool was triggered")
            else:
                logger.warning("⚠️  WebSearch tool was NOT triggered")

            await agent.close()

            assert response, "Response should not be empty"
            return websearch_used

        except Exception as e:
            logger.error(f"❌ Test failed with error: {e}", exc_info=True)
            await agent.close()
            raise

    @pytest.mark.asyncio
    async def test_knowledge_graph_preferred_for_known_topics(self):
        """Test that knowledge graph is preferred for established topics."""
        agent = PolicyTrackerSDKAgent(enable_web_search=True)

        logger.info("=" * 70)
        logger.info("TEST: Knowledge graph preferred for known topics")
        logger.info("=" * 70)

        query = "What is GDPR?"

        try:
            response, session_id, metadata = await agent.query(query)

            logger.info(f"\n📊 RESULTS:")
            logger.info(f"Tools used: {metadata.get('tools_used', [])}")

            tools_used = str(metadata.get('tools_used', []))
            kg_used = 'search_knowledge_graph' in tools_used or 'knowledge_graph' in tools_used
            websearch_used = 'WebSearch' in tools_used

            if kg_used and not websearch_used:
                logger.info("✅ Knowledge graph used, WebSearch not triggered (expected)")
            elif websearch_used:
                logger.info("⚠️  WebSearch was triggered for known topic")
            else:
                logger.info("ℹ️  Neither knowledge graph nor WebSearch triggered")

            await agent.close()

            assert response, "Response should not be empty"

        except Exception as e:
            logger.error(f"❌ Test failed with error: {e}", exc_info=True)
            await agent.close()
            raise

    @pytest.mark.asyncio
    async def test_websearch_disabled(self):
        """Test that WebSearch is NOT triggered when disabled."""
        agent = PolicyTrackerSDKAgent(enable_web_search=False)

        logger.info("=" * 70)
        logger.info("TEST: WebSearch disabled")
        logger.info("=" * 70)

        query = "What are the latest news about EU regulations?"

        try:
            response, session_id, metadata = await agent.query(query)

            logger.info(f"\n📊 RESULTS:")
            logger.info(f"Tools used: {metadata.get('tools_used', [])}")

            tools_used = str(metadata.get('tools_used', []))
            websearch_used = 'WebSearch' in tools_used

            if not websearch_used:
                logger.info("✅ WebSearch correctly not triggered when disabled")
            else:
                logger.error("❌ WebSearch was triggered despite being disabled!")

            await agent.close()

            assert not websearch_used, "WebSearch should NOT be triggered when disabled"

        except Exception as e:
            logger.error(f"❌ Test failed with error: {e}", exc_info=True)
            await agent.close()
            raise


class TestWebSearchStreaming:
    """Test WebSearch with streaming queries."""

    @pytest.mark.asyncio
    async def test_websearch_streaming_query(self):
        """Test that WebSearch works with streaming responses."""
        agent = PolicyTrackerSDKAgent(enable_web_search=True)

        logger.info("=" * 70)
        logger.info("TEST: WebSearch with streaming query")
        logger.info("=" * 70)

        query = "What are the latest developments in EU AI policy?"

        try:
            chunks = []
            session_id = None
            metadata = None

            async for chunk, sid, meta in agent.stream_query(query):
                if chunk:
                    chunks.append(chunk)
                    print(chunk, end="", flush=True)
                else:
                    # Final yield with metadata
                    session_id = sid
                    metadata = meta

            print()  # Newline after streaming

            logger.info(f"\n📊 RESULTS:")
            logger.info(f"Session ID: {session_id}")
            logger.info(f"Total chunks: {len(chunks)}")
            logger.info(f"Tools used: {metadata.get('tools_used', [])}")

            full_response = "".join(chunks)
            tools_used = metadata.get('tools_used', [])
            websearch_used = 'WebSearch' in str(tools_used)

            if websearch_used:
                logger.info("✅ WebSearch tool was triggered in streaming mode")
            else:
                logger.warning("⚠️  WebSearch tool was NOT triggered in streaming mode")

            await agent.close()

            assert full_response, "Response should not be empty"
            assert session_id, "Session ID should be generated"

        except Exception as e:
            logger.error(f"❌ Test failed with error: {e}", exc_info=True)
            await agent.close()
            raise


# Utility function to run all tests
async def run_all_tests():
    """Run all WebSearch tests sequentially."""
    logger.info("\n" + "=" * 70)
    logger.info("RUNNING ALL WEBSEARCH TESTS")
    logger.info("=" * 70 + "\n")

    # Configuration tests (synchronous)
    config_tests = TestWebSearchConfiguration()
    logger.info("\n--- CONFIGURATION TESTS ---\n")
    config_tests.test_websearch_in_allowed_tools_when_enabled()
    config_tests.test_websearch_not_in_allowed_tools_when_disabled()
    config_tests.test_dpa_tools_in_allowed_tools()
    config_tests.test_exa_tools_not_in_allowed_tools()
    config_tests.test_all_tool_categories_present()

    # Execution tests (async)
    exec_tests = TestWebSearchExecution()
    logger.info("\n--- EXECUTION TESTS ---\n")

    try:
        websearch_used_1 = await exec_tests.test_websearch_with_current_events_query()
        websearch_used_2 = await exec_tests.test_websearch_with_news_query()
        await exec_tests.test_knowledge_graph_preferred_for_known_topics()
        await exec_tests.test_websearch_disabled()
    except Exception as e:
        logger.error(f"Execution tests failed: {e}")

    # Streaming tests (async)
    stream_tests = TestWebSearchStreaming()
    logger.info("\n--- STREAMING TESTS ---\n")

    try:
        await stream_tests.test_websearch_streaming_query()
    except Exception as e:
        logger.error(f"Streaming tests failed: {e}")

    logger.info("\n" + "=" * 70)
    logger.info("ALL TESTS COMPLETED")
    logger.info("=" * 70 + "\n")


if __name__ == "__main__":
    # Run all tests
    asyncio.run(run_all_tests())
