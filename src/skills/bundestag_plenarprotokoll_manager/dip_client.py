"""Bundestag DIP API Client for fetching Plenarprotokoll (plenary protocol) data."""
import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class BundestagPlenarprotokollDIPClient:
    """Client for Bundestag DIP API - Plenarprotokoll endpoint."""

    def __init__(self, api_key: Optional[str] = None, api_base_url: str = None):
        """Initialize DIP API client for Plenarprotokoll.

        Args:
            api_key: API key for authentication (if required)
            api_base_url: Base URL for DIP API
        """
        self.api_key = api_key
        self.api_base_url = api_base_url or "https://search.dip.bundestag.de/api/v1"
        self.timeout = httpx.Timeout(30.0)

        logger.info(f"BundestagPlenarprotokollDIPClient initialized (base_url={self.api_base_url})")

    async def get_all_plenarprotokoll_ids(self, limit: Optional[int] = None) -> list[str]:
        """Get all Plenarprotokoll IDs from DIP API.

        Args:
            limit: Maximum number of IDs to return

        Returns:
            List of Plenarprotokoll IDs
        """
        endpoint = "/plenarprotokoll"
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
                    # Extract Plenarprotokoll IDs from response
                    protokolle = data.get("documents", [])
                    protokoll_ids = [p.get("id") for p in protokolle if p.get("id")]

                    logger.info(f"Retrieved {len(protokoll_ids)} Plenarprotokoll IDs from DIP API")
                    return protokoll_ids
                else:
                    logger.error(f"DIP API error: {response.status_code} - {response.text}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching Plenarprotokoll IDs from DIP API: {e}")
            return []

    async def get_plenarprotokoll_by_id(self, plenarprotokoll_id: str) -> Optional[dict[str, Any]]:
        """Get detailed Plenarprotokoll data by ID.

        Args:
            plenarprotokoll_id: Plenarprotokoll ID

        Returns:
            Plenarprotokoll data dictionary or None
        """
        endpoint = f"/plenarprotokoll/{plenarprotokoll_id}"

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
                    plenarprotokoll = self._transform_dip_plenarprotokoll(data)

                    return plenarprotokoll
                elif response.status_code == 404:
                    logger.warning(f"Plenarprotokoll {plenarprotokoll_id} not found in DIP API")
                    return None
                else:
                    logger.error(
                        f"DIP API error for Plenarprotokoll {plenarprotokoll_id}: {response.status_code}"
                    )
                    return None

        except Exception as e:
            logger.error(f"Error fetching Plenarprotokoll {plenarprotokoll_id} from DIP API: {e}")
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

    def _transform_dip_plenarprotokoll(self, dip_data: dict[str, Any]) -> dict[str, Any]:
        """Transform DIP API Plenarprotokoll data to internal format.

        This method maps DIP API field names to our internal field names.

        Args:
            dip_data: Raw DIP API response

        Returns:
            Transformed Plenarprotokoll dictionary
        """
        # Map DIP API fields to our schema
        plenarprotokoll = {
            "id": dip_data.get("id"),
            "plenarprotokoll_id": dip_data.get(
                "id"
            ),  # Use plenarprotokoll_id for Neo4j (matches ENTITY_ID_FIELDS)
            "titel": dip_data.get("titel", ""),
            "datum": dip_data.get("datum"),
            "wahlperiode": dip_data.get("wahlperiode"),
            "sitzungsnummer": dip_data.get("sitzungsnummer", 0),
            "herausgeber": dip_data.get("herausgeber", "Deutscher Bundestag"),
            "pdf_url": dip_data.get("fundstelle", {}).get("pdf_url", ""),
            "dokumentnummer": dip_data.get("dokumentnummer", ""),
        }

        # Add optional fields
        if "abstract" in dip_data:
            plenarprotokoll["abstract"] = dip_data["abstract"]

        if "aktualisiert" in dip_data:
            plenarprotokoll["aktualisiert"] = dip_data["aktualisiert"]

        if "fundstelle" in dip_data:
            plenarprotokoll["fundstelle"] = dip_data["fundstelle"]

        return plenarprotokoll


# Mock client for testing without actual DIP API access
class MockBundestagPlenarprotokollDIPClient:
    """Mock DIP client for Plenarprotokoll testing and development."""

    def __init__(self, api_key: Optional[str] = None, api_base_url: str = None):
        """Initialize mock DIP client."""
        logger.info("MockBundestagPlenarprotokollDIPClient initialized (using mock data)")

        # Mock data for testing - sample plenary protocols
        self.mock_plenarprotokolle = {
            "2001234": {
                "id": "2001234",
                "plenarprotokoll_id": "2001234",
                "titel": "Plenarprotokoll 20/123",
                "datum": "2024-03-15",
                "wahlperiode": 20,
                "sitzungsnummer": 123,
                "herausgeber": "Deutscher Bundestag",
                "pdf_url": "https://dserver.bundestag.de/btp/20/20123.pdf",
                "dokumentnummer": "20/123",
                "abstract": "Plenarprotokoll der 123. Sitzung des Deutschen Bundestages.",
            },
            "2005678": {
                "id": "2005678",
                "plenarprotokoll_id": "2005678",
                "titel": "Plenarprotokoll 20/124",
                "datum": "2024-03-16",
                "wahlperiode": 20,
                "sitzungsnummer": 124,
                "herausgeber": "Deutscher Bundestag",
                "pdf_url": "https://dserver.bundestag.de/btp/20/20124.pdf",
                "dokumentnummer": "20/124",
                "abstract": "Plenarprotokoll der 124. Sitzung des Deutschen Bundestages.",
            },
            "2009012": {
                "id": "2009012",
                "plenarprotokoll_id": "2009012",
                "titel": "Plenarprotokoll 20/125",
                "datum": "2024-03-17",
                "wahlperiode": 20,
                "sitzungsnummer": 125,
                "herausgeber": "Deutscher Bundestag",
                "pdf_url": "https://dserver.bundestag.de/btp/20/20125.pdf",
                "dokumentnummer": "20/125",
                "abstract": "Plenarprotokoll der 125. Sitzung des Deutschen Bundestages.",
                "fundstelle": "BT-PlPr 20/125",
            },
        }

    async def get_all_plenarprotokoll_ids(self, limit: Optional[int] = None) -> list[str]:
        """Get all mock Plenarprotokoll IDs.

        Args:
            limit: Maximum number of IDs to return

        Returns:
            List of Plenarprotokoll IDs
        """
        protokoll_ids = list(self.mock_plenarprotokolle.keys())

        if limit:
            protokoll_ids = protokoll_ids[:limit]

        logger.info(f"Returning {len(protokoll_ids)} mock Plenarprotokoll IDs")
        return protokoll_ids

    async def get_plenarprotokoll_by_id(self, plenarprotokoll_id: str) -> Optional[dict[str, Any]]:
        """Get mock Plenarprotokoll data by ID.

        Args:
            plenarprotokoll_id: Plenarprotokoll ID

        Returns:
            Plenarprotokoll data dictionary or None
        """
        plenarprotokoll = self.mock_plenarprotokolle.get(plenarprotokoll_id)

        if plenarprotokoll:
            logger.info(f"Returning mock data for Plenarprotokoll {plenarprotokoll_id}")
        else:
            logger.warning(f"Mock Plenarprotokoll {plenarprotokoll_id} not found")

        return plenarprotokoll
