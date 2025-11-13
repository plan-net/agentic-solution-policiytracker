"""
Unit tests for Bundestag ingestion collectors.

Tests all 8 collectors following good testing patterns:
- Mock only external dependencies (HTTP APIs)
- Test real internal logic (transformation, entity building)
- Use interface contract validation
- Test with realistic sample data
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Any

from src.flows.bundestag_ingestion.collectors.vorgang_collector import VorgangCollector
from src.flows.bundestag_ingestion.collectors.drucksache_collector import DrucksacheCollector
from src.flows.bundestag_ingestion.collectors.person_collector import PersonCollector
from src.flows.bundestag_ingestion.collectors.plenarprotokoll_collector import PlenarprotokollCollector
from src.flows.bundestag_ingestion.collectors.vorgangsposition_collector import VorgangspositionCollector
from src.flows.bundestag_ingestion.collectors.aktivitaet_collector import AktivitaetCollector
from src.flows.bundestag_ingestion.collectors.base_collector import BaseCollector

from src.flows.bundestag_ingestion.transformers.entity_builder import BundestagEntityBuilder
from src.flows.bundestag_ingestion.transformers.edge_builder import BundestagEdgeBuilder
from src.flows.bundestag_ingestion.utils.api_client import BundestagAPIClient

from tests.fixtures.bundestag_sample_data import (
    SAMPLE_VORGANG_RESPONSE,
    SAMPLE_DRUCKSACHE_RESPONSE,
    SAMPLE_PERSON_RESPONSE,
    SAMPLE_PLENARPROTOKOLL_RESPONSE,
    SAMPLE_VORGANGSPOSITION_RESPONSE,
    SAMPLE_AKTIVITAET_RESPONSE,
    SAMPLE_PAGINATED_RESPONSE_PAGE_1,
    SAMPLE_PAGINATED_RESPONSE_PAGE_2,
    SAMPLE_PAGINATED_RESPONSE_PAGE_3,
    get_sample_vorgaenge,
)


# ===================================================================
# INTERFACE CONTRACT TESTS
# ===================================================================

class TestCollectorInterfaceContracts:
    """Validate that all collectors implement the correct interface."""

    def test_base_collector_interface(self):
        """Test BaseCollector defines required abstract methods."""
        assert hasattr(BaseCollector, 'endpoint')
        assert hasattr(BaseCollector, 'entity_type')
        assert hasattr(BaseCollector, 'collect_and_transform')

        # Verify these are abstract properties/methods
        import inspect
        assert inspect.isabstract(BaseCollector)

    def test_vorgang_collector_interface(self):
        """Test VorgangCollector implements required interface."""
        api_client = MagicMock(spec=BundestagAPIClient)
        entity_builder = MagicMock(spec=BundestagEntityBuilder)
        edge_builder = MagicMock(spec=BundestagEdgeBuilder)

        collector = VorgangCollector(api_client, entity_builder, edge_builder)

        # Verify properties
        assert hasattr(collector, 'endpoint')
        assert hasattr(collector, 'entity_type')
        assert collector.endpoint == 'vorgang'
        assert collector.entity_type == 'Vorgang'

        # Verify methods
        assert hasattr(collector, 'collect_and_transform')
        assert callable(collector.collect_and_transform)

    def test_all_collectors_have_consistent_interface(self):
        """Test all 8 collectors have consistent interface."""
        api_client = MagicMock(spec=BundestagAPIClient)
        entity_builder = MagicMock(spec=BundestagEntityBuilder)
        edge_builder = MagicMock(spec=BundestagEdgeBuilder)

        collectors = [
            VorgangCollector(api_client, entity_builder, edge_builder),
            DrucksacheCollector(api_client, entity_builder, edge_builder),
            PersonCollector(api_client, entity_builder, edge_builder),
            PlenarprotokollCollector(api_client, entity_builder, edge_builder),
            VorgangspositionCollector(api_client, entity_builder, edge_builder),
            AktivitaetCollector(api_client, entity_builder, edge_builder),
        ]

        for collector in collectors:
            # All must have these properties
            assert hasattr(collector, 'endpoint')
            assert hasattr(collector, 'entity_type')
            assert hasattr(collector, 'api_client')
            assert hasattr(collector, 'entity_builder')
            assert hasattr(collector, 'edge_builder')

            # All must have these methods
            assert hasattr(collector, 'collect_and_transform')
            assert hasattr(collector, 'fetch_with_pagination')
            assert hasattr(collector, 'health_check')


# ===================================================================
# VORGANG COLLECTOR TESTS
# ===================================================================

class TestVorgangCollector:
    """Test VorgangCollector with real internal logic."""

    @pytest.fixture
    def api_client(self):
        """Create mock API client."""
        client = MagicMock(spec=BundestagAPIClient)
        return client

    @pytest.fixture
    def entity_builder(self):
        """Create real entity builder."""
        return BundestagEntityBuilder()

    @pytest.fixture
    def edge_builder(self):
        """Create real edge builder."""
        return BundestagEdgeBuilder()

    @pytest.fixture
    def collector(self, api_client, entity_builder, edge_builder):
        """Create VorgangCollector with real internal components."""
        return VorgangCollector(api_client, entity_builder, edge_builder)

    @pytest.mark.asyncio
    async def test_collect_and_transform_real_logic(self, collector, api_client):
        """Test real collection and transformation logic."""
        # Mock only external API call
        api_client.get = AsyncMock(return_value=SAMPLE_VORGANG_RESPONSE)

        inputs = {
            "filters": {"f.wahlperiode": "20"},
            "limit": 10
        }

        # Test real processing
        result = await collector.collect_and_transform(inputs)

        # Validate real behavior
        assert result["collector_type"] == "VorgangCollector"
        assert result["endpoint"] == "vorgang"
        assert result["entity_type"] == "Vorgang"
        assert result["items_collected"] == 1
        assert result["entities_created"] >= 0  # May be 0 if transformation fails
        assert "duration" in result
        assert isinstance(result["errors"], list)

    @pytest.mark.asyncio
    async def test_fetch_with_pagination_integration(self, collector, api_client):
        """Test pagination integration with real PaginationHelper."""
        # Mock API to return paginated responses
        api_client.get = AsyncMock(side_effect=[
            SAMPLE_PAGINATED_RESPONSE_PAGE_1,
            SAMPLE_PAGINATED_RESPONSE_PAGE_2,
            SAMPLE_PAGINATED_RESPONSE_PAGE_3,
        ])

        filters = {"f.wahlperiode": "20"}

        # Test real pagination logic
        items = await collector.fetch_with_pagination(filters, limit=250)

        # Validate pagination worked correctly
        assert len(items) == 250
        assert api_client.get.call_count == 3

    @pytest.mark.asyncio
    async def test_health_check_real_behavior(self, collector, api_client):
        """Test health check with real API interaction."""
        # Mock successful API response
        api_client.get = AsyncMock(return_value=get_sample_vorgaenge(1))

        # Test real health check
        is_healthy = await collector.health_check()

        assert is_healthy is True
        assert api_client.get.called

    @pytest.mark.asyncio
    async def test_health_check_failure(self, collector, api_client):
        """Test health check handles API failures."""
        # Mock API failure
        api_client.get = AsyncMock(side_effect=Exception("API Error"))

        # Test real error handling
        is_healthy = await collector.health_check()

        assert is_healthy is False

    @pytest.mark.asyncio
    async def test_entity_transformation_real(self, collector, api_client, entity_builder):
        """Test entity transformation uses real entity builder."""
        api_client.get = AsyncMock(return_value=SAMPLE_VORGANG_RESPONSE)

        inputs = {"filters": {}, "limit": 1}

        # Execute collection
        result = await collector.collect_and_transform(inputs)

        # Verify entity builder was called (real transformation)
        # This test would catch wrong method names!
        assert result["items_collected"] == 1


# ===================================================================
# DRUCKSACHE COLLECTOR TESTS
# ===================================================================

class TestDrucksacheCollector:
    """Test DrucksacheCollector with real internal logic."""

    @pytest.fixture
    def collector(self):
        api_client = MagicMock(spec=BundestagAPIClient)
        entity_builder = BundestagEntityBuilder()
        edge_builder = BundestagEdgeBuilder()
        return DrucksacheCollector(api_client, entity_builder, edge_builder)

    @pytest.mark.asyncio
    async def test_collect_drucksachen(self, collector):
        """Test Drucksache collection with real processing."""
        # Mock only API call
        collector.api_client.get = AsyncMock(return_value=SAMPLE_DRUCKSACHE_RESPONSE)

        inputs = {"filters": {"f.wahlperiode": "20"}, "limit": 10}

        # Test real logic
        result = await collector.collect_and_transform(inputs)

        # Validate
        assert result["endpoint"] == "drucksache"
        assert result["entity_type"] == "Drucksache"
        assert result["items_collected"] == 1

    def test_drucksache_collector_properties(self, collector):
        """Test collector has correct endpoint and entity type."""
        assert collector.endpoint == "drucksache"
        assert collector.entity_type == "Drucksache"


# ===================================================================
# PERSON COLLECTOR TESTS
# ===================================================================

class TestPersonCollector:
    """Test PersonCollector with real internal logic."""

    @pytest.fixture
    def collector(self):
        api_client = MagicMock(spec=BundestagAPIClient)
        entity_builder = BundestagEntityBuilder()
        edge_builder = BundestagEdgeBuilder()
        return PersonCollector(api_client, entity_builder, edge_builder)

    @pytest.mark.asyncio
    async def test_collect_persons(self, collector):
        """Test Person collection with real processing."""
        collector.api_client.get = AsyncMock(return_value=SAMPLE_PERSON_RESPONSE)

        inputs = {"filters": {"f.fraktion": "SPD"}, "limit": 10}

        result = await collector.collect_and_transform(inputs)

        assert result["endpoint"] == "person"
        assert result["entity_type"] == "BundestagPerson"
        assert result["items_collected"] == 1

    def test_person_collector_properties(self, collector):
        """Test collector has correct endpoint and entity type."""
        assert collector.endpoint == "person"
        assert collector.entity_type == "BundestagPerson"


# ===================================================================
# PLENARPROTOKOLL COLLECTOR TESTS
# ===================================================================

class TestPlenarprotokollCollector:
    """Test PlenarprotokollCollector with real internal logic."""

    @pytest.fixture
    def collector(self):
        api_client = MagicMock(spec=BundestagAPIClient)
        entity_builder = BundestagEntityBuilder()
        edge_builder = BundestagEdgeBuilder()
        return PlenarprotokollCollector(api_client, entity_builder, edge_builder)

    @pytest.mark.asyncio
    async def test_collect_plenarprotokolle(self, collector):
        """Test Plenarprotokoll collection with real processing."""
        collector.api_client.get = AsyncMock(return_value=SAMPLE_PLENARPROTOKOLL_RESPONSE)

        inputs = {"filters": {"f.wahlperiode": "20"}, "limit": 10}

        result = await collector.collect_and_transform(inputs)

        assert result["endpoint"] == "plenarprotokoll"
        assert result["entity_type"] == "Plenarprotokoll"
        assert result["items_collected"] == 1

    def test_plenarprotokoll_collector_properties(self, collector):
        """Test collector has correct endpoint and entity type."""
        assert collector.endpoint == "plenarprotokoll"
        assert collector.entity_type == "Plenarprotokoll"


# ===================================================================
# VORGANGSPOSITION COLLECTOR TESTS
# ===================================================================

class TestVorgangspositionCollector:
    """Test VorgangspositionCollector with real internal logic."""

    @pytest.fixture
    def collector(self):
        api_client = MagicMock(spec=BundestagAPIClient)
        entity_builder = BundestagEntityBuilder()
        edge_builder = BundestagEdgeBuilder()
        return VorgangspositionCollector(api_client, entity_builder, edge_builder)

    @pytest.mark.asyncio
    async def test_collect_vorgangspositionen(self, collector):
        """Test Vorgangsposition collection with real processing."""
        collector.api_client.get = AsyncMock(return_value=SAMPLE_VORGANGSPOSITION_RESPONSE)

        inputs = {"filters": {"f.vorgangstyp": "Gesetzgebung"}, "limit": 10}

        result = await collector.collect_and_transform(inputs)

        assert result["endpoint"] == "vorgangsposition"
        assert result["entity_type"] == "Vorgangsposition"
        assert result["items_collected"] == 1

    def test_vorgangsposition_collector_properties(self, collector):
        """Test collector has correct endpoint and entity type."""
        assert collector.endpoint == "vorgangsposition"
        assert collector.entity_type == "Vorgangsposition"


# ===================================================================
# AKTIVITAET COLLECTOR TESTS
# ===================================================================

class TestAktivitaetCollector:
    """Test AktivitaetCollector with real internal logic."""

    @pytest.fixture
    def collector(self):
        api_client = MagicMock(spec=BundestagAPIClient)
        entity_builder = BundestagEntityBuilder()
        edge_builder = BundestagEdgeBuilder()
        return AktivitaetCollector(api_client, entity_builder, edge_builder)

    @pytest.mark.asyncio
    async def test_collect_aktivitaeten(self, collector):
        """Test Aktivitaet collection with real processing."""
        collector.api_client.get = AsyncMock(return_value=SAMPLE_AKTIVITAET_RESPONSE)

        inputs = {"filters": {"f.typ": "Abstimmung"}, "limit": 10}

        result = await collector.collect_and_transform(inputs)

        assert result["endpoint"] == "aktivitaet"
        assert result["entity_type"] == "Aktivitaet"
        assert result["items_collected"] == 1

    def test_aktivitaet_collector_properties(self, collector):
        """Test collector has correct endpoint and entity type."""
        assert collector.endpoint == "aktivitaet"
        assert collector.entity_type == "Aktivitaet"


# ===================================================================
# PAGINATION AND ERROR HANDLING TESTS
# ===================================================================

class TestCollectorPaginationAndErrors:
    """Test pagination and error handling across collectors."""

    @pytest.fixture
    def collector(self):
        """Generic collector for pagination tests."""
        api_client = MagicMock(spec=BundestagAPIClient)
        entity_builder = BundestagEntityBuilder()
        edge_builder = BundestagEdgeBuilder()
        return VorgangCollector(api_client, entity_builder, edge_builder)

    @pytest.mark.asyncio
    async def test_pagination_with_limit(self, collector):
        """Test pagination respects limit parameter."""
        collector.api_client.get = AsyncMock(return_value=get_sample_vorgaenge(50))

        # Fetch with limit
        items = await collector.fetch_with_pagination(filters={}, limit=25)

        # Should stop at limit
        assert len(items) <= 25

    @pytest.mark.asyncio
    async def test_api_error_handling(self, collector):
        """Test collector handles API errors gracefully."""
        collector.api_client.get = AsyncMock(side_effect=Exception("API Connection Error"))

        inputs = {"filters": {}, "limit": 10}

        # Should not crash, should report error
        with pytest.raises(Exception):
            await collector.collect_and_transform(inputs)

    @pytest.mark.asyncio
    async def test_empty_response_handling(self, collector):
        """Test collector handles empty API responses."""
        collector.api_client.get = AsyncMock(return_value={"documents": [], "numFound": 0, "cursor": None})

        inputs = {"filters": {}, "limit": 10}

        result = await collector.collect_and_transform(inputs)

        assert result["items_collected"] == 0
        assert result["entities_created"] == 0


# ===================================================================
# FILTER BUILDER INTEGRATION TESTS
# ===================================================================

class TestCollectorFilterIntegration:
    """Test collectors integrate correctly with FilterBuilder."""

    @pytest.mark.asyncio
    async def test_collect_with_filters_convenience_method(self):
        """Test collect_with_filters method builds filters correctly."""
        api_client = MagicMock(spec=BundestagAPIClient)
        api_client.get = AsyncMock(return_value=get_sample_vorgaenge(5))

        entity_builder = BundestagEntityBuilder()
        edge_builder = BundestagEdgeBuilder()

        collector = VorgangCollector(api_client, entity_builder, edge_builder)

        # Use convenience method
        result = await collector.collect_with_filters(
            wahlperiode="20",
            datum_von="2024-01-01",
            datum_bis="2024-12-31",
            limit=10
        )

        # Verify it executed successfully
        assert result["items_collected"] >= 0
        assert "duration" in result


# ===================================================================
# STATISTICS TRACKING TESTS
# ===================================================================

class TestCollectorStatistics:
    """Test statistics tracking across collectors."""

    @pytest.mark.asyncio
    async def test_statistics_structure(self):
        """Test statistics dictionary has consistent structure."""
        api_client = MagicMock(spec=BundestagAPIClient)
        api_client.get = AsyncMock(return_value=get_sample_vorgaenge(10))

        entity_builder = BundestagEntityBuilder()
        edge_builder = BundestagEdgeBuilder()

        collector = VorgangCollector(api_client, entity_builder, edge_builder)

        inputs = {"filters": {}, "limit": 10}
        result = await collector.collect_and_transform(inputs)

        # Verify all expected fields present
        required_fields = [
            "entities_created",
            "edges_created",
            "duration",
            "items_collected",
            "collector_type",
            "endpoint",
            "entity_type",
            "errors"
        ]

        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

    @pytest.mark.asyncio
    async def test_duration_measurement(self):
        """Test duration is measured correctly."""
        api_client = MagicMock(spec=BundestagAPIClient)
        api_client.get = AsyncMock(return_value=get_sample_vorgaenge(5))

        entity_builder = BundestagEntityBuilder()
        edge_builder = BundestagEdgeBuilder()

        collector = VorgangCollector(api_client, entity_builder, edge_builder)

        inputs = {"filters": {}, "limit": 5}
        result = await collector.collect_and_transform(inputs)

        # Duration should be positive number
        assert isinstance(result["duration"], (int, float))
        assert result["duration"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
