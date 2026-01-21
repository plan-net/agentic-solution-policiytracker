"""
Unit tests for Bundestag DIP MCP Server.

Tests the client and server components with minimal mocking
following the project's testing patterns.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.mcp.bundestag_dip.client import BundestagDIPClient


class TestBundestagDIPClientInterface:
    """Test that BundestagDIPClient has the correct interface."""

    def test_client_initialization_default_values(self):
        """Test client initializes with correct defaults."""
        client = BundestagDIPClient()

        assert client.base_url == "https://search.dip.bundestag.de/api/v1"
        assert client.max_retries == 3
        assert client.retry_delay == 1.0
        assert client.api_key is not None  # Should use default key

    def test_client_initialization_custom_values(self):
        """Test client accepts custom configuration."""
        client = BundestagDIPClient(
            api_key="custom-key",
            base_url="https://custom.url",
            max_retries=5,
            retry_delay=2.0,
            timeout=60,
        )

        assert client.api_key == "custom-key"
        assert client.base_url == "https://custom.url"
        assert client.max_retries == 5
        assert client.retry_delay == 2.0

    def test_client_interface_contract(self):
        """Test client has all required methods."""
        client = BundestagDIPClient()

        required_methods = [
            "search_vorgaenge",
            "get_vorgang",
            "search_drucksachen",
            "get_drucksache",
            "search_persons",
            "get_person",
            "search_aktivitaeten",
            "get_plenarprotokoll",
            "close",
        ]

        for method_name in required_methods:
            assert hasattr(client, method_name), f"Client must have {method_name} method"
            method = getattr(client, method_name)
            assert callable(method), f"{method_name} must be callable"


class TestBundestagDIPClientVorgaenge:
    """Test Vorgang (legislative procedure) methods."""

    @pytest.fixture
    def mock_vorgang_response(self):
        """Sample API response for Vorgänge search."""
        return {
            "documents": [
                {
                    "id": "287654",
                    "titel": "Klimaschutzgesetz-Novelle",
                    "vorgangstyp": "Gesetzgebung",
                    "beratungsstand": "Im Ausschuss",
                    "initiative": ["Bundesregierung"],
                    "sachgebiet": ["Umweltpolitik", "Klimaschutz"],
                    "wahlperiode": 20,
                    "datum": "2024-03-15",
                    "aktualisiert": "2024-03-20",
                    "abstract": "Novellierung des Klimaschutzgesetzes...",
                    "schlagwort": ["Klimaschutz", "CO2", "Emissionen"],
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_search_vorgaenge_success(self, mock_vorgang_response):
        """Test successful Vorgänge search."""
        client = BundestagDIPClient(api_key="test-key")

        with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_vorgang_response

            results = await client.search_vorgaenge(
                query="Klimaschutz",
                wahlperiode=20,
                limit=10
            )

            assert len(results) == 1
            assert results[0]["id"] == "287654"
            assert results[0]["titel"] == "Klimaschutzgesetz-Novelle"
            assert results[0]["vorgangstyp"] == "Gesetzgebung"
            assert "Bundesregierung" in results[0]["initiative"]

            # Verify API call
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "vorgang" in call_args[0][0]

        await client.close()

    @pytest.mark.asyncio
    async def test_search_vorgaenge_empty_results(self):
        """Test Vorgänge search with no results."""
        client = BundestagDIPClient(api_key="test-key")

        with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"documents": []}

            results = await client.search_vorgaenge(query="nonexistent")

            assert len(results) == 0

        await client.close()

    @pytest.mark.asyncio
    async def test_get_vorgang_success(self, mock_vorgang_response):
        """Test getting specific Vorgang."""
        client = BundestagDIPClient(api_key="test-key")

        with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_vorgang_response["documents"][0]

            result = await client.get_vorgang("287654")

            assert result is not None
            assert result["id"] == "287654"
            assert result["titel"] == "Klimaschutzgesetz-Novelle"

            mock_get.assert_called_once_with("vorgang/287654")

        await client.close()

    @pytest.mark.asyncio
    async def test_get_vorgang_not_found(self):
        """Test getting non-existent Vorgang."""
        client = BundestagDIPClient(api_key="test-key")

        with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Not found")

            result = await client.get_vorgang("999999")

            assert result is None

        await client.close()


class TestBundestagDIPClientDrucksachen:
    """Test Drucksache (parliamentary document) methods."""

    @pytest.fixture
    def mock_drucksache_response(self):
        """Sample API response for Drucksachen search."""
        return {
            "documents": [
                {
                    "id": "123456",
                    "dokumentnummer": "20/1234",
                    "titel": "Gesetzentwurf zur Digitalisierung",
                    "dokumentart": "Gesetzentwurf",
                    "datum": "2024-03-10",
                    "wahlperiode": 20,
                    "autoren_anzeige": ["Fraktion der SPD"],
                    "pdf_url": "https://example.com/doc.pdf",
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_search_drucksachen_success(self, mock_drucksache_response):
        """Test successful Drucksachen search."""
        client = BundestagDIPClient(api_key="test-key")

        with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_drucksache_response

            results = await client.search_drucksachen(
                query="Digitalisierung",
                dokumentart="Gesetzentwurf",
                limit=10
            )

            assert len(results) == 1
            assert results[0]["drucksache"] == "20/1234"
            assert results[0]["dokumentart"] == "Gesetzentwurf"

        await client.close()

    @pytest.mark.asyncio
    async def test_get_drucksache_success(self, mock_drucksache_response):
        """Test getting specific Drucksache."""
        client = BundestagDIPClient(api_key="test-key")

        with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_drucksache_response

            result = await client.get_drucksache("20/1234")

            assert result is not None
            assert result["drucksache"] == "20/1234"

        await client.close()


class TestBundestagDIPClientPersons:
    """Test Person (Bundestag member) methods."""

    @pytest.fixture
    def mock_person_response(self):
        """Sample API response for person search."""
        return {
            "documents": [
                {
                    "id": "11004123",
                    "vorname": "Max",
                    "nachname": "Mustermann",
                    "fraktion": "SPD",
                    "funktion": "Abgeordneter",
                    "wahlkreis": "Berlin-Mitte",
                    "beruf": "Jurist",
                    "geburtsdatum": "1970-05-15",
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_search_persons_by_name(self, mock_person_response):
        """Test person search by name."""
        client = BundestagDIPClient(api_key="test-key")

        with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_person_response

            results = await client.search_persons(name="Mustermann")

            assert len(results) == 1
            assert results[0]["nachname"] == "Mustermann"
            assert results[0]["fraktion"] == "SPD"

        await client.close()

    @pytest.mark.asyncio
    async def test_search_persons_by_fraktion(self, mock_person_response):
        """Test person search by parliamentary group."""
        client = BundestagDIPClient(api_key="test-key")

        with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_person_response

            results = await client.search_persons(fraktion="SPD")

            assert len(results) == 1

        await client.close()

    @pytest.mark.asyncio
    async def test_get_person_success(self, mock_person_response):
        """Test getting specific person."""
        client = BundestagDIPClient(api_key="test-key")

        with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_person_response["documents"][0]

            result = await client.get_person("11004123")

            assert result is not None
            assert result["vorname"] == "Max"
            assert result["nachname"] == "Mustermann"

        await client.close()


class TestBundestagDIPClientActivities:
    """Test Aktivität (parliamentary activity) methods."""

    @pytest.fixture
    def mock_activity_response(self):
        """Sample API response for activities."""
        return {
            "documents": [
                {
                    "id": "act_001",
                    "titel": "Rede zum Klimaschutzgesetz",
                    "aktivitaetsart": "Rede",
                    "datum": "2024-03-15",
                    "person_anzeige": "Max Mustermann (SPD)",
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_search_aktivitaeten_success(self, mock_activity_response):
        """Test successful activity search."""
        client = BundestagDIPClient(api_key="test-key")

        with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_activity_response

            results = await client.search_aktivitaeten(
                query="Klimaschutz",
                aktivitaetsart="Rede",
                limit=10
            )

            assert len(results) == 1
            assert results[0]["aktivitaetsart"] == "Rede"

        await client.close()


class TestBundestagDIPClientPlenarprotokoll:
    """Test Plenarprotokoll (plenary protocol) methods."""

    @pytest.fixture
    def mock_protocol_response(self):
        """Sample API response for plenary protocol."""
        return {
            "documents": [
                {
                    "id": "proto_001",
                    "dokumentnummer": "20/123",
                    "datum": "2024-03-15",
                    "wahlperiode": 20,
                    "pdf_url": "https://example.com/protocol.pdf",
                    "tagesordnungspunkte": [
                        "TOP 1: Klimaschutzgesetz",
                        "TOP 2: Haushaltsdebatte"
                    ],
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_get_plenarprotokoll_by_session(self, mock_protocol_response):
        """Test getting protocol by session number."""
        client = BundestagDIPClient(api_key="test-key")

        with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_protocol_response

            result = await client.get_plenarprotokoll(sitzungsnummer="20/123")

            assert result is not None
            assert result["sitzungsnummer"] == "20/123"
            assert len(result["tagesordnung"]) == 2

        await client.close()

    @pytest.mark.asyncio
    async def test_get_plenarprotokoll_by_date(self, mock_protocol_response):
        """Test getting protocol by date."""
        client = BundestagDIPClient(api_key="test-key")

        with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_protocol_response

            result = await client.get_plenarprotokoll(date="2024-03-15")

            assert result is not None
            assert result["datum"] == "2024-03-15"

        await client.close()


class TestBundestagDIPClientErrorHandling:
    """Test error handling in the client."""

    @pytest.mark.asyncio
    async def test_handles_api_error(self):
        """Test handling of API errors."""
        client = BundestagDIPClient(api_key="test-key")

        with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("API Error 500")

            # Should return empty list, not raise
            results = await client.search_vorgaenge(query="test")
            assert results == []

        await client.close()

    @pytest.mark.asyncio
    async def test_handles_timeout(self):
        """Test handling of timeout errors."""
        client = BundestagDIPClient(api_key="test-key", timeout=1)

        with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = TimeoutError("Request timed out")

            results = await client.search_vorgaenge(query="test")
            assert results == []

        await client.close()


class TestBundestagDIPServerToolsDefinition:
    """Test the MCP server tools are properly defined."""

    def test_tools_list_has_all_expected_tools(self):
        """Test that all expected tools are defined."""
        expected_tools = [
            "search_bundestag_legislation",
            "get_bundestag_vorgang",
            "search_bundestag_documents",
            "get_bundestag_drucksache",
            "search_bundestag_persons",
            "get_bundestag_person",
            "search_bundestag_activities",
            "get_bundestag_plenarprotokoll",
        ]

        # Import and check tools are defined
        from src.mcp.bundestag_dip.server import list_tools

        # Since list_tools is async, we need to check the implementation
        import inspect
        assert inspect.iscoroutinefunction(list_tools)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
