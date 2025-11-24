"""Bundestag DIP API Client for fetching Aktivitaet (parliamentary activity) data."""
import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class BundestagAktivitaetDIPClient:
    """Client for Bundestag DIP API - Aktivitaet endpoint."""

    def __init__(self, api_key: Optional[str] = None, api_base_url: str = None):
        """Initialize DIP API client for Aktivitaet.

        Args:
            api_key: API key for authentication (if required)
            api_base_url: Base URL for DIP API
        """
        self.api_key = api_key
        self.api_base_url = api_base_url or "https://search.dip.bundestag.de/api/v1"
        self.timeout = httpx.Timeout(30.0)

        logger.info(f"BundestagAktivitaetDIPClient initialized (base_url={self.api_base_url})")

    async def get_all_aktivitaet_ids(self, limit: Optional[int] = None) -> list[str]:
        """Get all Aktivitaet IDs from DIP API.

        Args:
            limit: Maximum number of IDs to return

        Returns:
            List of Aktivitaet IDs
        """
        endpoint = "/aktivitaet"
        params = {"format": "json"}

        if limit:
            params["rows"] = limit

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.api_base_url}{endpoint}",
                    params=params,
                    headers=self._get_headers(),
                )

                if response.status_code == 200:
                    data = response.json()
                    # Extract Aktivitaet IDs from response
                    aktivitaeten = data.get("documents", [])
                    aktivitaet_ids = [a.get("id") for a in aktivitaeten if a.get("id")]

                    logger.info(f"Retrieved {len(aktivitaet_ids)} Aktivitaet IDs from DIP API")
                    return aktivitaet_ids
                else:
                    logger.error(f"DIP API error: {response.status_code} - {response.text}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching Aktivitaet IDs from DIP API: {e}")
            return []

    async def get_aktivitaet_by_id(self, aktivitaet_id: str) -> Optional[dict[str, Any]]:
        """Get detailed Aktivitaet data by ID.

        Args:
            aktivitaet_id: Aktivitaet ID

        Returns:
            Aktivitaet data dictionary or None
        """
        endpoint = f"/aktivitaet/{aktivitaet_id}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.api_base_url}{endpoint}",
                    params={"format": "json"},
                    headers=self._get_headers(),
                )

                if response.status_code == 200:
                    data = response.json()

                    # Transform DIP API response to our internal format
                    aktivitaet = self._transform_dip_aktivitaet(data)

                    return aktivitaet
                elif response.status_code == 404:
                    logger.warning(f"Aktivitaet {aktivitaet_id} not found in DIP API")
                    return None
                else:
                    logger.error(
                        f"DIP API error for Aktivitaet {aktivitaet_id}: {response.status_code}"
                    )
                    return None

        except Exception as e:
            logger.error(f"Error fetching Aktivitaet {aktivitaet_id} from DIP API: {e}")
            return None

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for API requests.

        Returns:
            Headers dictionary
        """
        headers = {"Accept": "application/json"}

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        return headers

    def _transform_dip_aktivitaet(self, dip_data: dict[str, Any]) -> dict[str, Any]:
        """Transform DIP API Aktivitaet data to internal format.

        This method maps DIP API field names to our internal field names.

        Args:
            dip_data: Raw DIP API response

        Returns:
            Transformed Aktivitaet dictionary
        """
        # Map DIP API fields to our schema
        aktivitaet = {
            "id": dip_data.get("id"),
            "aktivitaet_id": dip_data.get(
                "id"
            ),  # Use aktivitaet_id for Neo4j (matches ENTITY_ID_FIELDS)
            "aktivitaetsart": dip_data.get("aktivitaetsart", ""),
            "titel": dip_data.get("titel", ""),
            "datum": dip_data.get("datum"),
            "wahlperiode": dip_data.get("wahlperiode"),
            "person_id": dip_data.get("person", {}).get("id", ""),
            "person_name": dip_data.get("person", {}).get("vorname", "")
            + " "
            + dip_data.get("person", {}).get("nachname", ""),
            "dokumentart": dip_data.get("dokumentart", ""),
            "drucksache_nummer": dip_data.get("drucksache", {}).get("nummer", ""),
        }

        # Add optional fields
        if "abstract" in dip_data:
            aktivitaet["abstract"] = dip_data["abstract"]

        if "fundstelle" in dip_data:
            aktivitaet["fundstelle"] = dip_data["fundstelle"]

        if "aktualisiert" in dip_data:
            aktivitaet["aktualisiert"] = dip_data["aktualisiert"]

        return aktivitaet


# Mock client for testing without actual DIP API access
class MockBundestagAktivitaetDIPClient:
    """Mock DIP client for Aktivitaet testing and development."""

    def __init__(self, api_key: Optional[str] = None, api_base_url: str = None):
        """Initialize mock DIP client."""
        logger.info("MockBundestagAktivitaetDIPClient initialized (using mock data)")

        # Mock data for testing - sample parliamentary activities
        self.mock_aktivitaeten = {
            "100001": {
                "id": "100001",
                "aktivitaet_id": "100001",
                "aktivitaetsart": "Rede",
                "titel": "Rede zur Künstlichen Intelligenz im Bundestag",
                "datum": "2024-03-15",
                "wahlperiode": 20,
                "person_id": "11004809",
                "person_name": "Anna Schmidt",
                "dokumentart": "Plenarprotokoll",
                "drucksache_nummer": "20/1234",
                "abstract": "Rede zur Regulierung von Künstlicher Intelligenz in Deutschland.",
            },
            "100002": {
                "id": "100002",
                "aktivitaet_id": "100002",
                "aktivitaetsart": "Abstimmung",
                "titel": "Abstimmung zum Klimaschutzgesetz",
                "datum": "2024-02-20",
                "wahlperiode": 20,
                "person_id": "11004322",
                "person_name": "Michael Müller",
                "dokumentart": "Beschlussempfehlung",
                "drucksache_nummer": "20/5678",
                "abstract": "Namentliche Abstimmung zum Klimaschutzgesetz 2024.",
            },
            "100003": {
                "id": "100003",
                "aktivitaet_id": "100003",
                "aktivitaetsart": "Anfrage",
                "titel": "Schriftliche Anfrage zur Cybersicherheit",
                "datum": "2024-10-05",
                "wahlperiode": 20,
                "person_id": "11003638",
                "person_name": "Lisa Weber",
                "dokumentart": "Kleine Anfrage",
                "drucksache_nummer": "20/9012",
                "abstract": "Anfrage zum aktuellen Stand der Cybersicherheit in Bundesbehörden.",
                "fundstelle": "BT-Drs 20/9012",
            },
        }

    async def get_all_aktivitaet_ids(self, limit: Optional[int] = None) -> list[str]:
        """Get all mock Aktivitaet IDs.

        Args:
            limit: Maximum number of IDs to return

        Returns:
            List of Aktivitaet IDs
        """
        aktivitaet_ids = list(self.mock_aktivitaeten.keys())

        if limit:
            aktivitaet_ids = aktivitaet_ids[:limit]

        logger.info(f"Returning {len(aktivitaet_ids)} mock Aktivitaet IDs")
        return aktivitaet_ids

    async def get_aktivitaet_by_id(self, aktivitaet_id: str) -> Optional[dict[str, Any]]:
        """Get mock Aktivitaet data by ID.

        Args:
            aktivitaet_id: Aktivitaet ID

        Returns:
            Aktivitaet data dictionary or None
        """
        aktivitaet = self.mock_aktivitaeten.get(aktivitaet_id)

        if aktivitaet:
            logger.info(f"Returning mock data for Aktivitaet {aktivitaet_id}")
        else:
            logger.warning(f"Mock Aktivitaet {aktivitaet_id} not found")

        return aktivitaet
