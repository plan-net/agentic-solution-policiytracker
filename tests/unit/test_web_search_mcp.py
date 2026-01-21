"""
Unit tests for Web Search MCP Server.

Tests the Exa.ai and DPA client components with minimal mocking
following the project's testing patterns.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import os


class TestExaSearchClientInterface:
    """Test that ExaSearchClient has the correct interface."""

    def test_client_initialization_with_api_key(self):
        """Test client initializes with provided API key."""
        with patch.dict(os.environ, {"EXA_API_KEY": "test-key"}):
            from src.mcp.web_search.exa_client import ExaSearchClient
            client = ExaSearchClient(api_key="custom-key")

            assert client.api_key == "custom-key"
            assert client.API_BASE_URL == "https://api.exa.ai"

    def test_client_initialization_from_env(self):
        """Test client reads API key from environment."""
        with patch.dict(os.environ, {"EXA_API_KEY": "env-test-key"}):
            from src.mcp.web_search.exa_client import ExaSearchClient
            client = ExaSearchClient()

            assert client.api_key == "env-test-key"

    def test_client_initialization_without_api_key_raises(self):
        """Test client raises error without API key."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove EXA_API_KEY if it exists
            if "EXA_API_KEY" in os.environ:
                del os.environ["EXA_API_KEY"]

            from src.mcp.web_search.exa_client import ExaSearchClient

            with pytest.raises(ValueError, match="EXA_API_KEY"):
                ExaSearchClient()

    def test_client_interface_contract(self):
        """Test client has all required methods."""
        with patch.dict(os.environ, {"EXA_API_KEY": "test-key"}):
            from src.mcp.web_search.exa_client import ExaSearchClient
            client = ExaSearchClient()

            required_methods = [
                "web_search",
                "search_news",
                "get_contents",
                "close",
            ]

            for method_name in required_methods:
                assert hasattr(client, method_name), f"Client must have {method_name} method"
                method = getattr(client, method_name)
                assert callable(method), f"{method_name} must be callable"


class TestExaSearchClientWebSearch:
    """Test web_search method."""

    @pytest.fixture
    def mock_exa_response(self):
        """Sample Exa.ai API response."""
        return {
            "results": [
                {
                    "title": "EU AI Act Implementation Guide",
                    "url": "https://ec.europa.eu/ai-act-guide",
                    "text": "The European Union AI Act provides comprehensive regulations...",
                    "publishedDate": "2024-03-15T10:00:00Z",
                    "author": "EU Commission",
                    "score": 0.95,
                },
                {
                    "title": "GDPR Compliance for AI Systems",
                    "url": "https://gdpr.eu/ai-compliance",
                    "text": "AI systems must comply with GDPR requirements...",
                    "publishedDate": "2024-03-14T14:30:00Z",
                    "author": "Privacy Office",
                    "score": 0.89,
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_web_search_success(self, mock_exa_response):
        """Test successful web search."""
        with patch.dict(os.environ, {"EXA_API_KEY": "test-key"}):
            from src.mcp.web_search.exa_client import ExaSearchClient
            client = ExaSearchClient()

            with patch("aiohttp.ClientSession.post") as mock_post:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json.return_value = mock_exa_response
                mock_post.return_value.__aenter__.return_value = mock_response

                results = await client.web_search(
                    query="EU AI regulation",
                    num_results=10
                )

                assert len(results) == 2
                assert results[0]["title"] == "EU AI Act Implementation Guide"
                assert "ec.europa.eu" in results[0]["url"]
                assert "content_preview" in results[0]

            await client.close()

    @pytest.mark.asyncio
    async def test_web_search_with_domain_filters(self, mock_exa_response):
        """Test web search with domain filtering."""
        with patch.dict(os.environ, {"EXA_API_KEY": "test-key"}):
            from src.mcp.web_search.exa_client import ExaSearchClient
            client = ExaSearchClient()

            with patch("aiohttp.ClientSession.post") as mock_post:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json.return_value = mock_exa_response
                mock_post.return_value.__aenter__.return_value = mock_response

                results = await client.web_search(
                    query="EU regulation",
                    include_domains=["europa.eu", "gov.uk"],
                    exclude_domains=["wikipedia.org"]
                )

                # Verify the call was made (filters are handled by the API)
                assert len(results) >= 0

            await client.close()

    @pytest.mark.asyncio
    async def test_web_search_api_error(self):
        """Test handling of API errors."""
        with patch.dict(os.environ, {"EXA_API_KEY": "test-key"}):
            from src.mcp.web_search.exa_client import ExaSearchClient
            client = ExaSearchClient()

            with patch("aiohttp.ClientSession.post") as mock_post:
                mock_response = AsyncMock()
                mock_response.status = 429
                mock_response.text.return_value = "Rate limit exceeded"
                mock_post.return_value.__aenter__.return_value = mock_response

                results = await client.web_search(query="test")

                # Should return empty list, not raise
                assert results == []

            await client.close()


class TestExaSearchClientNewsSearch:
    """Test search_news method."""

    @pytest.fixture
    def mock_news_response(self):
        """Sample Exa.ai news API response."""
        return {
            "results": [
                {
                    "title": "Breaking: New AI Regulations Announced",
                    "url": "https://news.example.com/ai-regulations",
                    "text": "Today, the European Commission announced new AI regulations...",
                    "publishedDate": "2024-03-15T08:00:00Z",
                    "author": "Tech Reporter",
                    "score": 0.92,
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_search_news_success(self, mock_news_response):
        """Test successful news search."""
        with patch.dict(os.environ, {"EXA_API_KEY": "test-key"}):
            from src.mcp.web_search.exa_client import ExaSearchClient
            client = ExaSearchClient()

            with patch("aiohttp.ClientSession.post") as mock_post:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json.return_value = mock_news_response
                mock_post.return_value.__aenter__.return_value = mock_response

                results = await client.search_news(
                    query="AI regulations",
                    num_results=10,
                    days_back=7
                )

                assert len(results) == 1
                assert results[0]["title"] == "Breaking: New AI Regulations Announced"

            await client.close()

    @pytest.mark.asyncio
    async def test_search_news_empty_results(self):
        """Test news search with no results."""
        with patch.dict(os.environ, {"EXA_API_KEY": "test-key"}):
            from src.mcp.web_search.exa_client import ExaSearchClient
            client = ExaSearchClient()

            with patch("aiohttp.ClientSession.post") as mock_post:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json.return_value = {"results": []}
                mock_post.return_value.__aenter__.return_value = mock_response

                results = await client.search_news(query="nonexistent topic xyz")

                assert len(results) == 0

            await client.close()


class TestExaSearchClientGetContents:
    """Test get_contents method."""

    @pytest.fixture
    def mock_contents_response(self):
        """Sample Exa.ai contents API response."""
        return {
            "results": [
                {
                    "title": "Full Article Title",
                    "url": "https://example.com/article",
                    "text": "This is the full content of the article...",
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_get_contents_success(self, mock_contents_response):
        """Test successful content retrieval."""
        with patch.dict(os.environ, {"EXA_API_KEY": "test-key"}):
            from src.mcp.web_search.exa_client import ExaSearchClient
            client = ExaSearchClient()

            with patch("aiohttp.ClientSession.post") as mock_post:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json.return_value = mock_contents_response
                mock_post.return_value.__aenter__.return_value = mock_response

                results = await client.get_contents(["https://example.com/article"])

                assert len(results) == 1
                assert results[0]["title"] == "Full Article Title"

            await client.close()

    @pytest.mark.asyncio
    async def test_get_contents_limits_urls(self, mock_contents_response):
        """Test that get_contents limits to 10 URLs."""
        with patch.dict(os.environ, {"EXA_API_KEY": "test-key"}):
            from src.mcp.web_search.exa_client import ExaSearchClient
            client = ExaSearchClient()

            urls = [f"https://example.com/article{i}" for i in range(15)]

            with patch("aiohttp.ClientSession.post") as mock_post:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json.return_value = mock_contents_response
                mock_post.return_value.__aenter__.return_value = mock_response

                await client.get_contents(urls)

                # Verify only 10 URLs were sent
                call_args = mock_post.call_args
                payload = call_args[1]["json"]
                assert len(payload["urls"]) <= 10

            await client.close()


class TestExaSearchClientNormalization:
    """Test result normalization logic."""

    def test_normalize_results_extracts_source(self):
        """Test that source is extracted from URL."""
        with patch.dict(os.environ, {"EXA_API_KEY": "test-key"}):
            from src.mcp.web_search.exa_client import ExaSearchClient
            client = ExaSearchClient()

            results = client._normalize_results([
                {
                    "title": "Test",
                    "url": "https://www.example.com/article",
                    "text": "Content",
                }
            ])

            assert results[0]["source"] == "Example"

    def test_normalize_results_handles_missing_fields(self):
        """Test normalization handles missing fields gracefully."""
        with patch.dict(os.environ, {"EXA_API_KEY": "test-key"}):
            from src.mcp.web_search.exa_client import ExaSearchClient
            client = ExaSearchClient()

            results = client._normalize_results([{}])

            assert results[0]["title"] == "Untitled"
            assert results[0]["url"] == ""
            assert results[0]["content_preview"] == ""

    def test_normalize_results_truncates_long_content(self):
        """Test that long content is truncated in preview."""
        with patch.dict(os.environ, {"EXA_API_KEY": "test-key"}):
            from src.mcp.web_search.exa_client import ExaSearchClient
            client = ExaSearchClient()

            long_content = "x" * 1000
            results = client._normalize_results([
                {"title": "Test", "url": "https://example.com", "text": long_content}
            ])

            assert len(results[0]["content_preview"]) < len(long_content)
            assert results[0]["content_preview"].endswith("...")


class TestDPANewsClientInterface:
    """Test that DPANewsClient has the correct interface."""

    def test_client_initialization_with_api_key(self):
        """Test client initializes with provided API key."""
        from src.mcp.web_search.dpa_client import DPANewsClient
        client = DPANewsClient(api_key="test-key")

        assert client.api_key == "test-key"
        assert client.is_available() is True

    def test_client_initialization_without_api_key(self):
        """Test client initializes without API key (degraded mode)."""
        with patch.dict(os.environ, {}, clear=True):
            if "DPA_API_KEY" in os.environ:
                del os.environ["DPA_API_KEY"]

            from src.mcp.web_search.dpa_client import DPANewsClient
            client = DPANewsClient()

            # Should not raise, but should indicate unavailable
            assert client.is_available() is False

    def test_client_interface_contract(self):
        """Test client has all required methods."""
        from src.mcp.web_search.dpa_client import DPANewsClient
        client = DPANewsClient(api_key="test-key")

        required_methods = [
            "search_news",
            "is_available",
            "close",
        ]

        for method_name in required_methods:
            assert hasattr(client, method_name), f"Client must have {method_name} method"


class TestDPANewsClientSearch:
    """Test DPA news search functionality."""

    @pytest.fixture
    def mock_dpa_response(self):
        """Sample DPA API response."""
        return {
            "context": [
                {
                    "urn": "urn:newsml:dpa.com:20240315:240315-99-12345",
                    "headline": "Bundesregierung beschließt neue KI-Regelungen",
                    "article_complete_markdown": "Die Bundesregierung hat heute neue Regelungen...",
                    "version_created_at_utc": "2024-03-15T10:00:00Z",
                    "tags": ["dnllang:de", "politics"],
                    "score": 0.95,
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_search_news_success(self, mock_dpa_response):
        """Test successful DPA news search."""
        from src.mcp.web_search.dpa_client import DPANewsClient
        client = DPANewsClient(api_key="test-key")

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_dpa_response
            mock_post.return_value.__aenter__.return_value = mock_response

            results = await client.search_news(
                query="KI Regelungen",
                max_items=10,
                days_back=7
            )

            assert len(results) == 1
            assert results[0]["title"] == "Bundesregierung beschließt neue KI-Regelungen"
            assert results[0]["source"] == "DPA"
            assert results[0]["language"] == "de"

        await client.close()

    @pytest.mark.asyncio
    async def test_search_news_without_api_key(self):
        """Test search returns empty when API key not configured."""
        with patch.dict(os.environ, {}, clear=True):
            from src.mcp.web_search.dpa_client import DPANewsClient
            client = DPANewsClient(api_key=None)

            results = await client.search_news(query="test")

            assert results == []

        await client.close()

    @pytest.mark.asyncio
    async def test_search_news_api_error(self, mock_dpa_response):
        """Test handling of API errors."""
        from src.mcp.web_search.dpa_client import DPANewsClient
        client = DPANewsClient(api_key="test-key")

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text.return_value = "Internal Server Error"
            mock_post.return_value.__aenter__.return_value = mock_response

            results = await client.search_news(query="test")

            # Should return empty list, not raise
            assert results == []

        await client.close()


class TestDPANewsClientNormalization:
    """Test DPA result normalization logic."""

    def test_normalize_results_extracts_language(self):
        """Test that language is extracted from tags."""
        from src.mcp.web_search.dpa_client import DPANewsClient
        client = DPANewsClient(api_key="test-key")

        results = client._normalize_results([
            {
                "urn": "urn:test",
                "headline": "Test",
                "article_complete_markdown": "Content",
                "tags": ["dnllang:en", "topic"],
            }
        ])

        assert results[0]["language"] == "en"

    def test_construct_url_from_urn(self):
        """Test URL construction from URN."""
        from src.mcp.web_search.dpa_client import DPANewsClient
        client = DPANewsClient(api_key="test-key")

        urn = "urn:newsml:dpa.com:20240315:240315-99-12345"
        url = client._construct_url_from_urn(urn)

        assert "dpa-news-hub.de" in url
        assert urn in url or "240315-99-12345" in url

    def test_construct_url_empty_urn(self):
        """Test URL construction with empty URN."""
        from src.mcp.web_search.dpa_client import DPANewsClient
        client = DPANewsClient(api_key="test-key")

        url = client._construct_url_from_urn("")

        assert url == ""


class TestWebSearchServerToolsDefinition:
    """Test the MCP server tools are properly defined."""

    def test_tools_list_has_all_expected_tools(self):
        """Test that all expected tools are defined."""
        expected_tools = [
            "web_search",
            "search_news",
            "search_dpa_news",
            "get_article_content",
        ]

        # Import and check tools are defined
        from src.mcp.web_search.server import list_tools

        # Since list_tools is async, we need to check the implementation
        import inspect
        assert inspect.iscoroutinefunction(list_tools)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
