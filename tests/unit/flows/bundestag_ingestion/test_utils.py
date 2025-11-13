"""
Unit tests for Bundestag ingestion utilities.

Tests BundestagAPIClient, PaginationHelper, and FilterBuilder.
"""

import pytest
from unittest.mock import AsyncMock, patch
from src.flows.bundestag_ingestion.utils.api_client import BundestagAPIClient
from src.flows.bundestag_ingestion.utils.pagination import PaginationHelper
from src.flows.bundestag_ingestion.utils.filters import FilterBuilder
from tests.fixtures.bundestag_sample_data import (
    SAMPLE_VORGANG_RESPONSE,
    SAMPLE_PAGINATED_RESPONSE_PAGE_1,
    SAMPLE_PAGINATED_RESPONSE_PAGE_2,
    SAMPLE_PAGINATED_RESPONSE_PAGE_3,
    SAMPLE_ERROR_RATE_LIMIT,
)


class TestBundestagAPIClient:
    """Test API client with mocked HTTP requests."""

    @pytest.fixture
    def client(self):
        return BundestagAPIClient()

    @pytest.mark.asyncio
    async def test_successful_get_request(self, client):
        """Test successful API GET request."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=SAMPLE_VORGANG_RESPONSE)
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await client.get("vorgang", params={"f.wahlperiode": "20"})

            assert result == SAMPLE_VORGANG_RESPONSE
            assert mock_get.called

    @pytest.mark.asyncio
    async def test_rate_limit_retry(self, client):
        """Test API client handles rate limiting with retry."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # First call: rate limited, second call: success
            mock_response_429 = AsyncMock()
            mock_response_429.status = 429
            mock_response_429.headers = {"Retry-After": "1"}

            mock_response_200 = AsyncMock()
            mock_response_200.status = 200
            mock_response_200.json = AsyncMock(return_value=SAMPLE_VORGANG_RESPONSE)

            mock_get.return_value.__aenter__.side_effect = [mock_response_429, mock_response_200]

            result = await client.get("vorgang")

            assert result == SAMPLE_VORGANG_RESPONSE
            assert mock_get.call_count == 2

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test API health check."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"documents": [], "numFound": 0})
            mock_get.return_value.__aenter__.return_value = mock_response

            is_healthy = await client.health_check()

            assert is_healthy is True

    @pytest.mark.asyncio
    async def test_get_by_id(self, client):
        """Test fetching resource by ID."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=SAMPLE_VORGANG_RESPONSE)
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await client.get_by_id("vorgang", "287654")

            assert result == SAMPLE_VORGANG_RESPONSE


class TestPaginationHelper:
    """Test pagination helper with mocked API."""

    @pytest.fixture
    def api_client(self):
        client = AsyncMock(spec=BundestagAPIClient)
        return client

    @pytest.mark.asyncio
    async def test_pagination_multiple_pages(self, api_client):
        """Test pagination across multiple pages."""
        api_client.get = AsyncMock(side_effect=[
            SAMPLE_PAGINATED_RESPONSE_PAGE_1,
            SAMPLE_PAGINATED_RESPONSE_PAGE_2,
            SAMPLE_PAGINATED_RESPONSE_PAGE_3,
        ])

        helper = PaginationHelper(api_client, max_items=250)

        items = []
        async for item in helper.paginate("vorgang", {}):
            items.append(item)

        assert len(items) == 250
        assert api_client.get.call_count == 3

    @pytest.mark.asyncio
    async def test_pagination_with_limit(self, api_client):
        """Test pagination stops at max_items."""
        api_client.get = AsyncMock(return_value=SAMPLE_PAGINATED_RESPONSE_PAGE_1)

        helper = PaginationHelper(api_client, max_items=50)

        items = []
        async for item in helper.paginate("vorgang", {}):
            items.append(item)

        assert len(items) <= 50


class TestFilterBuilder:
    """Test filter builder creates correct query parameters."""

    @pytest.fixture
    def builder(self):
        return FilterBuilder()

    def test_build_wahlperiode_filter(self, builder):
        """Test building Wahlperiode filter."""
        filters = builder.build_filters(wahlperiode="20")

        assert "f.wahlperiode" in filters
        assert filters["f.wahlperiode"] == "20"

    def test_build_date_range_filter(self, builder):
        """Test building date range filters."""
        filters = builder.build_filters(
            datum_von="2024-01-01",
            datum_bis="2024-12-31"
        )

        assert "f.datum" in filters or "f.von" in filters

    def test_build_complex_filters(self, builder):
        """Test building multiple filters together."""
        filters = builder.build_filters(
            wahlperiode="20",
            datum_von="2024-01-01",
            limit=100
        )

        assert len(filters) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
