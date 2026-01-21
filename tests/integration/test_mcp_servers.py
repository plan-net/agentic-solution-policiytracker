"""
Integration tests for MCP Servers.

Tests the MCP servers end-to-end with FastAPI test client.
Requires services to be running for full integration tests.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import os
import sys


# Check if MCP package is available
try:
    from mcp.server import Server
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

# Only import modules if MCP is available
if MCP_AVAILABLE:
    from src.mcp.bundestag_dip import server as bundestag_server
    from src.mcp.bundestag_dip import client as bundestag_client
    from src.mcp.web_search import server as websearch_server
    from src.mcp.web_search import exa_client
    from src.mcp.web_search import dpa_client
else:
    bundestag_server = None
    bundestag_client = None
    websearch_server = None
    exa_client = None
    dpa_client = None

# Skip all tests if MCP is not available
pytestmark = pytest.mark.skipif(
    not MCP_AVAILABLE,
    reason="MCP package not installed (pip install mcp>=1.0.0)"
)


class TestBundestagDIPMCPServerIntegration:
    """Integration tests for Bundestag DIP MCP Server."""

    @pytest.fixture
    def mock_dip_client(self):
        """Create a mock DIP client for testing."""
        client = MagicMock()
        client.base_url = "https://search.dip.bundestag.de/api/v1"
        client.search_vorgaenge = AsyncMock(return_value=[
            {
                "id": "287654",
                "titel": "Test Vorgang",
                "vorgangstyp": "Gesetzgebung",
                "beratungsstand": "Im Ausschuss",
                "initiative": ["Bundesregierung"],
                "sachgebiet": ["Umweltpolitik"],
                "wahlperiode": 20,
                "datum": "2024-03-15",
                "aktualisiert": "2024-03-20",
                "abstract": "Test abstract",
                "schlagwort": ["Test"],
            }
        ])
        client.get_vorgang = AsyncMock(return_value={
            "id": "287654",
            "titel": "Test Vorgang",
            "vorgangstyp": "Gesetzgebung",
            "beratungsstand": "Im Ausschuss",
            "initiative": ["Bundesregierung"],
            "sachgebiet": ["Umweltpolitik"],
            "wahlperiode": 20,
            "datum": "2024-03-15",
            "aktualisiert": "2024-03-20",
            "abstract": "Test abstract",
            "schlagwort": ["Test"],
        })
        client.search_drucksachen = AsyncMock(return_value=[])
        client.get_drucksache = AsyncMock(return_value=None)
        client.search_persons = AsyncMock(return_value=[])
        client.get_person = AsyncMock(return_value=None)
        client.search_aktivitaeten = AsyncMock(return_value=[])
        client.get_plenarprotokoll = AsyncMock(return_value=None)
        client.close = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_search_legislation_handler(self, mock_dip_client):
        """Test search_bundestag_legislation tool handler."""
        # Patch the module's dip_client directly
        original_client = bundestag_server.dip_client
        bundestag_server.dip_client = mock_dip_client

        try:
            result = await bundestag_server.handle_search_legislation({
                "query": "Klimaschutz",
                "wahlperiode": 20,
                "limit": 10
            })

            assert len(result) == 1
            assert "Test Vorgang" in result[0].text
            mock_dip_client.search_vorgaenge.assert_called_once()
        finally:
            bundestag_server.dip_client = original_client

    @pytest.mark.asyncio
    async def test_get_vorgang_handler(self, mock_dip_client):
        """Test get_bundestag_vorgang tool handler."""
        original_client = bundestag_server.dip_client
        bundestag_server.dip_client = mock_dip_client

        try:
            result = await bundestag_server.handle_get_vorgang("287654")

            assert len(result) == 1
            assert "Test Vorgang" in result[0].text
            mock_dip_client.get_vorgang.assert_called_once_with("287654")
        finally:
            bundestag_server.dip_client = original_client

    @pytest.mark.asyncio
    async def test_search_legislation_no_results(self, mock_dip_client):
        """Test search with no results."""
        mock_dip_client.search_vorgaenge = AsyncMock(return_value=[])

        original_client = bundestag_server.dip_client
        bundestag_server.dip_client = mock_dip_client

        try:
            result = await bundestag_server.handle_search_legislation({
                "query": "nonexistent"
            })

            assert "No legislative procedures found" in result[0].text
        finally:
            bundestag_server.dip_client = original_client

    @pytest.mark.asyncio
    async def test_search_documents_handler(self, mock_dip_client):
        """Test search_bundestag_documents tool handler."""
        mock_dip_client.search_drucksachen = AsyncMock(return_value=[
            {
                "drucksache": "20/1234",
                "titel": "Test Drucksache",
                "dokumentart": "Gesetzentwurf",
                "datum": "2024-03-15",
                "autoren": ["SPD"],
            }
        ])

        original_client = bundestag_server.dip_client
        bundestag_server.dip_client = mock_dip_client

        try:
            result = await bundestag_server.handle_search_documents({
                "query": "Test",
                "limit": 10
            })

            assert len(result) == 1
            assert "Test Drucksache" in result[0].text
        finally:
            bundestag_server.dip_client = original_client

    @pytest.mark.asyncio
    async def test_search_persons_handler(self, mock_dip_client):
        """Test search_bundestag_persons tool handler."""
        mock_dip_client.search_persons = AsyncMock(return_value=[
            {
                "id": "123",
                "vorname": "Max",
                "nachname": "Mustermann",
                "fraktion": "SPD",
            }
        ])

        original_client = bundestag_server.dip_client
        bundestag_server.dip_client = mock_dip_client

        try:
            result = await bundestag_server.handle_search_persons({
                "name": "Mustermann"
            })

            assert len(result) == 1
            assert "Mustermann" in result[0].text
        finally:
            bundestag_server.dip_client = original_client


class TestWebSearchMCPServerIntegration:
    """Integration tests for Web Search MCP Server."""

    @pytest.fixture
    def mock_exa_client(self):
        """Create a mock Exa client for testing."""
        client = MagicMock()
        client.web_search = AsyncMock(return_value=[
            {
                "title": "EU AI Act Guide",
                "url": "https://europa.eu/ai-act",
                "source": "Europa",
                "published_date": "2024-03-15",
                "content_preview": "Comprehensive guide to EU AI regulations...",
            }
        ])
        client.search_news = AsyncMock(return_value=[
            {
                "title": "Breaking News: AI Regulation",
                "url": "https://news.example.com/ai",
                "source": "News",
                "published_date": "2024-03-15",
                "author": "Reporter",
                "content_preview": "New regulations announced...",
            }
        ])
        client.get_contents = AsyncMock(return_value=[
            {
                "title": "Full Article",
                "url": "https://example.com/article",
                "content": "Full article content here...",
            }
        ])
        client.close = AsyncMock()
        return client

    @pytest.fixture
    def mock_dpa_client(self):
        """Create a mock DPA client for testing."""
        client = MagicMock()
        client.is_available = MagicMock(return_value=True)
        client.search_news = AsyncMock(return_value=[
            {
                "title": "DPA Nachricht",
                "url": "https://dpa.com/news/123",
                "published_date": "2024-03-15",
                "language": "de",
                "content_preview": "Deutsche Nachrichten...",
            }
        ])
        client.close = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_web_search_handler(self, mock_exa_client, mock_dpa_client):
        """Test web_search tool handler."""
        original_exa = websearch_server.exa_client
        original_dpa = websearch_server.dpa_client
        websearch_server.exa_client = mock_exa_client
        websearch_server.dpa_client = mock_dpa_client

        try:
            result = await websearch_server.handle_web_search({
                "query": "EU AI regulation",
                "num_results": 10
            })

            assert len(result) == 1
            assert "EU AI Act Guide" in result[0].text
            mock_exa_client.web_search.assert_called_once()
        finally:
            websearch_server.exa_client = original_exa
            websearch_server.dpa_client = original_dpa

    @pytest.mark.asyncio
    async def test_search_news_handler(self, mock_exa_client, mock_dpa_client):
        """Test search_news tool handler."""
        original_exa = websearch_server.exa_client
        original_dpa = websearch_server.dpa_client
        websearch_server.exa_client = mock_exa_client
        websearch_server.dpa_client = mock_dpa_client

        try:
            result = await websearch_server.handle_search_news({
                "query": "AI regulation",
                "num_results": 10,
                "days_back": 7
            })

            assert len(result) == 1
            assert "Breaking News" in result[0].text
        finally:
            websearch_server.exa_client = original_exa
            websearch_server.dpa_client = original_dpa

    @pytest.mark.asyncio
    async def test_dpa_search_handler(self, mock_exa_client, mock_dpa_client):
        """Test search_dpa_news tool handler."""
        original_exa = websearch_server.exa_client
        original_dpa = websearch_server.dpa_client
        websearch_server.exa_client = mock_exa_client
        websearch_server.dpa_client = mock_dpa_client

        try:
            result = await websearch_server.handle_search_dpa_news({
                "query": "KI Regelungen",
                "max_items": 10,
                "days_back": 7
            })

            assert len(result) == 1
            assert "DPA Nachricht" in result[0].text
        finally:
            websearch_server.exa_client = original_exa
            websearch_server.dpa_client = original_dpa

    @pytest.mark.asyncio
    async def test_dpa_search_unavailable(self, mock_exa_client):
        """Test DPA search when API not configured."""
        mock_dpa = MagicMock()
        mock_dpa.is_available = MagicMock(return_value=False)

        original_exa = websearch_server.exa_client
        original_dpa = websearch_server.dpa_client
        websearch_server.exa_client = mock_exa_client
        websearch_server.dpa_client = mock_dpa

        try:
            result = await websearch_server.handle_search_dpa_news({
                "query": "test"
            })

            assert "not configured" in result[0].text
        finally:
            websearch_server.exa_client = original_exa
            websearch_server.dpa_client = original_dpa

    @pytest.mark.asyncio
    async def test_get_article_content_handler(self, mock_exa_client, mock_dpa_client):
        """Test get_article_content tool handler."""
        original_exa = websearch_server.exa_client
        original_dpa = websearch_server.dpa_client
        websearch_server.exa_client = mock_exa_client
        websearch_server.dpa_client = mock_dpa_client

        try:
            result = await websearch_server.handle_get_article_content({
                "urls": ["https://example.com/article"]
            })

            assert len(result) == 1
            assert "Full Article" in result[0].text
        finally:
            websearch_server.exa_client = original_exa
            websearch_server.dpa_client = original_dpa

    @pytest.mark.asyncio
    async def test_get_article_content_empty_urls(self, mock_exa_client, mock_dpa_client):
        """Test get_article_content with no URLs."""
        original_exa = websearch_server.exa_client
        original_dpa = websearch_server.dpa_client
        websearch_server.exa_client = mock_exa_client
        websearch_server.dpa_client = mock_dpa_client

        try:
            result = await websearch_server.handle_get_article_content({
                "urls": []
            })

            assert "No URLs provided" in result[0].text
        finally:
            websearch_server.exa_client = original_exa
            websearch_server.dpa_client = original_dpa


class TestMCPToolCallDispatch:
    """Test MCP tool call dispatching."""

    @pytest.fixture
    def mock_clients(self):
        """Create mock clients for testing."""
        dip_client = MagicMock()
        dip_client.base_url = "https://search.dip.bundestag.de/api/v1"
        dip_client.search_vorgaenge = AsyncMock(return_value=[])
        dip_client.close = AsyncMock()

        exa = MagicMock()
        exa.web_search = AsyncMock(return_value=[])
        exa.close = AsyncMock()

        dpa = MagicMock()
        dpa.is_available = MagicMock(return_value=True)
        dpa.search_news = AsyncMock(return_value=[])
        dpa.close = AsyncMock()

        return dip_client, exa, dpa

    @pytest.mark.asyncio
    async def test_bundestag_call_tool_dispatches_correctly(self, mock_clients):
        """Test that call_tool correctly dispatches to handlers."""
        dip_client, _, _ = mock_clients

        original_client = bundestag_server.dip_client
        bundestag_server.dip_client = dip_client

        try:
            result = await bundestag_server.call_tool("search_bundestag_legislation", {"query": "test"})
            assert result is not None
        finally:
            bundestag_server.dip_client = original_client

    @pytest.mark.asyncio
    async def test_bundestag_call_tool_unknown_tool(self, mock_clients):
        """Test that call_tool handles unknown tools."""
        dip_client, _, _ = mock_clients

        original_client = bundestag_server.dip_client
        bundestag_server.dip_client = dip_client

        try:
            result = await bundestag_server.call_tool("unknown_tool", {})
            assert "Unknown tool" in result[0].text
        finally:
            bundestag_server.dip_client = original_client

    @pytest.mark.asyncio
    async def test_websearch_call_tool_dispatches_correctly(self, mock_clients):
        """Test that call_tool correctly dispatches to handlers."""
        _, exa, dpa = mock_clients

        original_exa = websearch_server.exa_client
        original_dpa = websearch_server.dpa_client
        websearch_server.exa_client = exa
        websearch_server.dpa_client = dpa

        try:
            result = await websearch_server.call_tool("web_search", {"query": "test"})
            assert result is not None
        finally:
            websearch_server.exa_client = original_exa
            websearch_server.dpa_client = original_dpa

    @pytest.mark.asyncio
    async def test_websearch_call_tool_unknown_tool(self, mock_clients):
        """Test that call_tool handles unknown tools."""
        _, exa, dpa = mock_clients

        original_exa = websearch_server.exa_client
        original_dpa = websearch_server.dpa_client
        websearch_server.exa_client = exa
        websearch_server.dpa_client = dpa

        try:
            result = await websearch_server.call_tool("unknown_tool", {})
            assert "Unknown tool" in result[0].text
        finally:
            websearch_server.exa_client = original_exa
            websearch_server.dpa_client = original_dpa


class TestMCPToolListExports:
    """Test that MCP tools are properly exported for discovery."""

    @pytest.mark.asyncio
    async def test_bundestag_list_tools(self):
        """Test that Bundestag server lists all tools."""
        tools = await bundestag_server.list_tools()

        assert len(tools) == 8

        tool_names = [t.name for t in tools]
        expected = [
            "search_bundestag_legislation",
            "get_bundestag_vorgang",
            "search_bundestag_documents",
            "get_bundestag_drucksache",
            "search_bundestag_persons",
            "get_bundestag_person",
            "search_bundestag_activities",
            "get_bundestag_plenarprotokoll",
        ]

        for name in expected:
            assert name in tool_names

    @pytest.mark.asyncio
    async def test_websearch_list_tools(self):
        """Test that Web Search server lists all tools."""
        tools = await websearch_server.list_tools()

        assert len(tools) == 4

        tool_names = [t.name for t in tools]
        expected = [
            "web_search",
            "search_news",
            "search_dpa_news",
            "get_article_content",
        ]

        for name in expected:
            assert name in tool_names

    @pytest.mark.asyncio
    async def test_tools_have_valid_input_schemas(self):
        """Test that all tools have valid input schemas."""
        bundestag_tools = await bundestag_server.list_tools()
        websearch_tools = await websearch_server.list_tools()

        all_tools = bundestag_tools + websearch_tools

        for tool in all_tools:
            assert tool.inputSchema is not None
            assert "type" in tool.inputSchema
            assert tool.inputSchema["type"] == "object"
            assert "properties" in tool.inputSchema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
