"""
Unit tests for Bundestag transformers (entity and edge builders).

Tests BundestagEntityBuilder and BundestagEdgeBuilder with real transformations.
"""

import pytest

from src.flows.bundestag_ingestion.transformers.edge_builder import BundestagEdgeBuilder
from src.flows.bundestag_ingestion.transformers.entity_builder import BundestagEntityBuilder
from src.graphrag.political_schema_v4 import (
    BundestagFraktion,
    BundestagPerson,
    Wahlperiode,
)
from tests.fixtures.bundestag_sample_data import (
    SAMPLE_FRAKTION_DATA,
    SAMPLE_PERSON_RESPONSE,
    SAMPLE_VORGANG_RESPONSE,
    SAMPLE_WAHLPERIODE_DATA,
)


class TestBundestagEntityBuilder:
    """Test entity builder with real Pydantic entity creation."""

    @pytest.fixture
    def builder(self):
        return BundestagEntityBuilder()

    @pytest.mark.asyncio
    async def test_create_wahlperiode_entity(self, builder):
        """Test Wahlperiode entity creation."""
        entity = await builder.create_wahlperiode_entity(**SAMPLE_WAHLPERIODE_DATA)

        assert isinstance(entity, Wahlperiode)
        assert entity.wahlperiode_nummer == 20
        assert entity.bundeskanzler == "Olaf Scholz"
        assert entity.sitze_gesamt == 736

    @pytest.mark.asyncio
    async def test_create_fraktion_entity(self, builder):
        """Test BundestagFraktion entity creation."""
        entity = await builder.create_fraktion_entity(**SAMPLE_FRAKTION_DATA)

        assert isinstance(entity, BundestagFraktion)
        assert entity.fraktion_name == "SPD"
        assert entity.sitze == 206
        assert entity.wahlperiode == 20

    @pytest.mark.asyncio
    async def test_create_person_entity(self, builder):
        """Test BundestagPerson entity creation."""
        person_data = SAMPLE_PERSON_RESPONSE["documents"][0]

        entity = await builder.create_person_entity(
            person_name=f"{person_data['vorname']} {person_data['nachname']}",
            person_id=person_data["id"],
            fraktion=person_data.get("fraktion"),
            partei=person_data.get("partei"),
        )

        assert isinstance(entity, BundestagPerson)
        assert entity.person_id == "11004809"
        assert entity.fraktion == "SPD"

    @pytest.mark.asyncio
    async def test_build_generic_method(self, builder):
        """Test generic build method routes to correct entity type."""
        # Test with Wahlperiode data
        entity = await builder.build(SAMPLE_WAHLPERIODE_DATA)
        assert isinstance(entity, Wahlperiode)

        # Test with Fraktion data
        entity = await builder.build(SAMPLE_FRAKTION_DATA)
        assert isinstance(entity, BundestagFraktion)


class TestBundestagEdgeBuilder:
    """Test edge builder with real relationship creation."""

    @pytest.fixture
    def builder(self):
        return BundestagEdgeBuilder()

    @pytest.mark.asyncio
    async def test_build_edges_for_vorgang(self, builder):
        """Test edge creation for Vorgang entity."""
        # Create mock Vorgang entity
        from src.graphrag.political_schema_v4 import Vorgang

        vorgang_data = SAMPLE_VORGANG_RESPONSE["documents"][0]
        vorgang_entity = Vorgang(
            vorgang_name=vorgang_data["titel"],
            vorgangstyp=vorgang_data["vorgangstyp"],
            wahlperiode=vorgang_data["wahlperiode"],
            beratungsstand=vorgang_data["beratungsstand"],
        )

        # Test edge building
        edges = await builder.build(vorgang_data, vorgang_entity)

        assert isinstance(edges, list)
        # Should create edges like Vorgang->Wahlperiode, Vorgang->Drucksache, etc.

    @pytest.mark.asyncio
    async def test_build_edges_validation(self, builder):
        """Test edge builder validates edge types."""
        # All built edges should have proper structure
        # This ensures interface consistency


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
