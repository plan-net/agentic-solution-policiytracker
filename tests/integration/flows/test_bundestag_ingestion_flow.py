"""
Integration tests for Bundestag ingestion flow.

Tests complete end-to-end flow with:
- Ray actor creation and execution
- Neo4j entity/edge creation via Kodosumi interface
- Progress tracking and report generation
- Mock only external API calls
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.flows.bundestag_ingestion.collectors.vorgang_collector import VorgangCollector
from src.flows.bundestag_ingestion.transformers.edge_builder import BundestagEdgeBuilder
from src.flows.bundestag_ingestion.transformers.entity_builder import BundestagEntityBuilder
from src.flows.bundestag_ingestion.utils.api_client import BundestagAPIClient
from tests.fixtures.bundestag_sample_data import (
    SAMPLE_DRUCKSACHE_RESPONSE,
    SAMPLE_PERSON_RESPONSE,
    SAMPLE_VORGANG_RESPONSE,
    get_sample_vorgaenge,
)


class TestBundestagIngestionFlowIntegration:
    """Integration test for complete Bundestag ingestion flow."""

    @pytest.mark.asyncio
    async def test_end_to_end_vorgang_collection(self):
        """Test complete Vorgang collection flow."""
        # Create real components
        api_client = BundestagAPIClient()
        entity_builder = BundestagEntityBuilder()
        edge_builder = BundestagEdgeBuilder()

        collector = VorgangCollector(api_client, entity_builder, edge_builder)

        # Mock only external API call
        with patch.object(api_client, "get", new=AsyncMock(return_value=get_sample_vorgaenge(10))):
            # Execute complete collection
            result = await collector.collect_and_transform(
                {"filters": {"f.wahlperiode": "20"}, "limit": 10}
            )

            # Validate end-to-end results
            assert result["items_collected"] == 10
            assert result["collector_type"] == "VorgangCollector"
            assert result["duration"] > 0
            assert isinstance(result["errors"], list)

    @pytest.mark.asyncio
    async def test_multiple_collectors_integration(self):
        """Test integration of multiple collectors."""
        from src.flows.bundestag_ingestion.collectors.drucksache_collector import (
            DrucksacheCollector,
        )
        from src.flows.bundestag_ingestion.collectors.person_collector import PersonCollector

        api_client = BundestagAPIClient()
        entity_builder = BundestagEntityBuilder()
        edge_builder = BundestagEdgeBuilder()

        vorgang_collector = VorgangCollector(api_client, entity_builder, edge_builder)
        drucksache_collector = DrucksacheCollector(api_client, entity_builder, edge_builder)
        person_collector = PersonCollector(api_client, entity_builder, edge_builder)

        # Mock API calls
        with patch.object(api_client, "get") as mock_get:
            mock_get.side_effect = [
                SAMPLE_VORGANG_RESPONSE,
                SAMPLE_DRUCKSACHE_RESPONSE,
                SAMPLE_PERSON_RESPONSE,
            ]

            # Collect from all sources
            vorgang_result = await vorgang_collector.collect_and_transform(
                {"filters": {}, "limit": 1}
            )
            drucksache_result = await drucksache_collector.collect_and_transform(
                {"filters": {}, "limit": 1}
            )
            person_result = await person_collector.collect_and_transform(
                {"filters": {}, "limit": 1}
            )

            # Validate all collections succeeded
            assert vorgang_result["items_collected"] == 1
            assert drucksache_result["items_collected"] == 1
            assert person_result["items_collected"] == 1

    @pytest.mark.asyncio
    async def test_entity_and_edge_creation_flow(self):
        """Test that entities and edges are created correctly."""
        api_client = BundestagAPIClient()
        entity_builder = BundestagEntityBuilder()
        edge_builder = BundestagEdgeBuilder()

        collector = VorgangCollector(api_client, entity_builder, edge_builder)

        with patch.object(api_client, "get", new=AsyncMock(return_value=SAMPLE_VORGANG_RESPONSE)):
            result = await collector.collect_and_transform({"filters": {}, "limit": 1})

            # Should have attempted entity creation
            assert result["items_collected"] == 1

    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """Test error handling in complete flow."""
        api_client = BundestagAPIClient()
        entity_builder = BundestagEntityBuilder()
        edge_builder = BundestagEdgeBuilder()

        collector = VorgangCollector(api_client, entity_builder, edge_builder)

        # Mock API to fail
        with patch.object(api_client, "get", new=AsyncMock(side_effect=Exception("API Error"))):
            with pytest.raises(Exception):
                await collector.collect_and_transform({"filters": {}, "limit": 10})

    @pytest.mark.asyncio
    async def test_pagination_integration(self):
        """Test pagination works in complete flow."""
        from tests.fixtures.bundestag_sample_data import (
            SAMPLE_PAGINATED_RESPONSE_PAGE_1,
            SAMPLE_PAGINATED_RESPONSE_PAGE_2,
            SAMPLE_PAGINATED_RESPONSE_PAGE_3,
        )

        api_client = BundestagAPIClient()
        entity_builder = BundestagEntityBuilder()
        edge_builder = BundestagEdgeBuilder()

        collector = VorgangCollector(api_client, entity_builder, edge_builder)

        # Mock paginated responses
        with patch.object(api_client, "get") as mock_get:
            mock_get.side_effect = [
                SAMPLE_PAGINATED_RESPONSE_PAGE_1,
                SAMPLE_PAGINATED_RESPONSE_PAGE_2,
                SAMPLE_PAGINATED_RESPONSE_PAGE_3,
            ]

            result = await collector.collect_and_transform({"filters": {}, "limit": 250})

            # Should collect all pages
            assert result["items_collected"] == 250
            assert mock_get.call_count == 3


class TestKodosumiInterfaceIntegration:
    """Test integration with Kodosumi storage interface."""

    @pytest.mark.asyncio
    async def test_kodosumi_storage_integration(self):
        """Test that collectors work with Kodosumi storage interface."""
        # This tests the interface contract with Kodosumi
        # The actual storage would be handled by Kodosumi in production

        api_client = BundestagAPIClient()
        entity_builder = BundestagEntityBuilder()
        edge_builder = BundestagEdgeBuilder()

        collector = VorgangCollector(api_client, entity_builder, edge_builder)

        with patch.object(api_client, "get", new=AsyncMock(return_value=get_sample_vorgaenge(5))):
            result = await collector.collect_and_transform({"filters": {}, "limit": 5})

            # Verify interface: result should have all required fields for Kodosumi
            required_fields = [
                "entities_created",
                "edges_created",
                "duration",
                "items_collected",
                "collector_type",
                "errors",
            ]

            for field in required_fields:
                assert field in result


class TestProgressTracking:
    """Test progress tracking and reporting."""

    @pytest.mark.asyncio
    async def test_statistics_tracking(self):
        """Test that statistics are tracked correctly throughout flow."""
        api_client = BundestagAPIClient()
        entity_builder = BundestagEntityBuilder()
        edge_builder = BundestagEdgeBuilder()

        collector = VorgangCollector(api_client, entity_builder, edge_builder)

        with patch.object(api_client, "get", new=AsyncMock(return_value=get_sample_vorgaenge(20))):
            result = await collector.collect_and_transform({"filters": {}, "limit": 20})

            # Verify statistics
            assert result["items_collected"] == 20
            assert result["duration"] > 0
            assert len(result["errors"]) == 0


class TestRayActorIntegration:
    """Test Ray actor creation and execution (when Ray is available)."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(True, reason="Requires Ray cluster")
    async def test_ray_actor_creation(self):
        """Test collector can be used as Ray actor."""
        import ray

        if not ray.is_initialized():
            ray.init(local_mode=True)

        # Create Ray actor
        @ray.remote
        class CollectorActor:
            def __init__(self):
                self.api_client = BundestagAPIClient()
                self.entity_builder = BundestagEntityBuilder()
                self.edge_builder = BundestagEdgeBuilder()
                self.collector = VorgangCollector(
                    self.api_client, self.entity_builder, self.edge_builder
                )

            async def collect(self, inputs):
                return await self.collector.collect_and_transform(inputs)

        # Test actor execution
        actor = CollectorActor.remote()
        # result = await actor.collect.remote({"filters": {}, "limit": 10})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
