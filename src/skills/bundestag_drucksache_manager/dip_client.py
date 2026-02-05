"""Bundestag DIP API Client for fetching Drucksache (parliamentary document) data."""
import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class BundestagDrucksacheDIPClient:
    """Client for Bundestag DIP API - Drucksache endpoint."""

    def __init__(self, api_key: Optional[str] = None, api_base_url: str = None):
        """Initialize DIP API client for Drucksache.

        Args:
            api_key: API key for authentication (if required)
            api_base_url: Base URL for DIP API
        """
        self.api_key = api_key
        self.api_base_url = api_base_url or "https://search.dip.bundestag.de/api/v1"
        self.timeout = httpx.Timeout(30.0)

        logger.info(f"BundestagDrucksacheDIPClient initialized (base_url={self.api_base_url})")

    async def get_all_drucksache_ids(
        self, limit: Optional[int] = None, wahlperiode: Optional[str] = None
    ) -> list[str]:
        """Get all Drucksache IDs from DIP API with cursor-based pagination.

        Args:
            limit: Maximum number of IDs to return
            wahlperiode: Filter by Wahlperiode (e.g., "20", "21")

        Returns:
            List of Drucksache IDs
        """
        endpoint = "/drucksache"
        all_drucksache_ids = []
        collected = 0
        cursor = None
        page_num = 0

        # Base params for all requests
        base_params = {"format": "json"}

        # Add API key as query parameter (DIP API authentication method)
        if self.api_key:
            base_params["apikey"] = self.api_key

        # Add wahlperiode filter
        if wahlperiode:
            base_params["f.wahlperiode"] = wahlperiode

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Paginate through all results
                while True:
                    page_num += 1
                    params = base_params.copy()

                    # Add cursor for pagination (if not first page)
                    if cursor:
                        params["cursor"] = cursor

                    logger.info(f"Fetching page {page_num} (collected so far: {collected})")

                    response = await client.get(
                        f"{self.api_base_url}{endpoint}",
                        params=params,
                        headers=self._get_headers(),
                    )

                    if response.status_code == 200:
                        data = response.json()

                        # Extract Drucksache IDs from response
                        drucksachen = data.get("documents", [])
                        page_ids = [d.get("id") for d in drucksachen if d.get("id")]

                        all_drucksache_ids.extend(page_ids)
                        collected += len(page_ids)

                        # Check if we've reached the limit
                        if limit and collected >= limit:
                            all_drucksache_ids = all_drucksache_ids[:limit]
                            logger.info(f"Reached limit of {limit} Drucksache IDs")
                            break

                        # Check for next page cursor
                        cursor = data.get("cursor")
                        if not cursor or not page_ids:
                            # No more pages
                            break
                    else:
                        logger.error(f"DIP API error: {response.status_code} - {response.text}")
                        break

            logger.info(f"Retrieved {len(all_drucksache_ids)} Drucksache IDs from DIP API")
            return all_drucksache_ids

        except Exception as e:
            logger.error(f"Error fetching Drucksache IDs from DIP API: {e}")
            return all_drucksache_ids

    async def get_drucksache_by_id(self, drucksache_id: str) -> Optional[dict[str, Any]]:
        """Get detailed Drucksache data by ID.

        Args:
            drucksache_id: Drucksache ID

        Returns:
            Drucksache data dictionary or None
        """
        endpoint = f"/drucksache/{drucksache_id}"
        params = {"format": "json"}

        # Add API key as query parameter (DIP API authentication method)
        if self.api_key:
            params["apikey"] = self.api_key

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.api_base_url}{endpoint}",
                    params=params,
                    headers=self._get_headers(),
                )

                if response.status_code == 200:
                    data = response.json()

                    # Transform DIP API response to our internal format
                    drucksache = self._transform_dip_drucksache(data)

                    return drucksache
                elif response.status_code == 404:
                    logger.warning(f"Drucksache {drucksache_id} not found in DIP API")
                    return None
                else:
                    logger.error(
                        f"DIP API error for Drucksache {drucksache_id}: {response.status_code}"
                    )
                    return None

        except Exception as e:
            logger.error(f"Error fetching Drucksache {drucksache_id} from DIP API: {e}")
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

    def _transform_dip_drucksache(self, dip_data: dict[str, Any]) -> dict[str, Any]:
        """Transform DIP API Drucksache data to internal format.

        This method maps DIP API field names to our internal field names.

        Args:
            dip_data: Raw DIP API response

        Returns:
            Transformed Drucksache dictionary
        """
        # Map DIP API fields to our schema
        drucksache = {
            "id": dip_data.get("id"),
            "drucksache_nummer": dip_data.get(
                "id"
            ),  # Use drucksache_nummer for Neo4j (matches ENTITY_ID_FIELDS)
            "dokumentnummer": dip_data.get("dokumentnummer", ""),
            "dokumentart": dip_data.get("dokumentart", ""),
            "titel": dip_data.get("titel", ""),
            "datum": dip_data.get("datum"),
            "wahlperiode": dip_data.get("wahlperiode"),
            "herausgeber": dip_data.get("herausgeber", ""),
            "pdf_url": dip_data.get("fundstelle", {}).get("pdf_url", ""),
            "autoren": dip_data.get("autoren", []),
        }

        # Add optional fields
        if "abstract" in dip_data:
            drucksache["abstract"] = dip_data["abstract"]

        if "ressort" in dip_data:
            drucksache["ressort"] = dip_data["ressort"]

        if "aktualisiert" in dip_data:
            drucksache["aktualisiert"] = dip_data["aktualisiert"]

        return drucksache


# Mock client for testing without actual DIP API access
class MockBundestagDrucksacheDIPClient:
    """Mock DIP client for Drucksache testing and development."""

    def __init__(self, api_key: Optional[str] = None, api_base_url: str = None):
        """Initialize mock DIP client."""
        logger.info("MockBundestagDrucksacheDIPClient initialized (using mock data)")

        # Mock data for testing - sample parliamentary documents
        self.mock_drucksachen = {
            "2001234": {
                "id": "2001234",
                "drucksache_nummer": "2001234",
                "dokumentnummer": "20/1234",
                "dokumentart": "Gesetzentwurf",
                "titel": "Entwurf eines Gesetzes zur Stärkung der Cybersicherheit",
                "datum": "2024-03-15",
                "wahlperiode": 20,
                "herausgeber": "Bundesregierung",
                "pdf_url": "https://dserver.bundestag.de/btd/20/012/2001234.pdf",
                "autoren": ["Bundesregierung"],
                "abstract": "Gesetzentwurf zur Verbesserung der Cybersicherheit in Deutschland.",
            },
            "2005678": {
                "id": "2005678",
                "drucksache_nummer": "2005678",
                "dokumentnummer": "20/5678",
                "dokumentart": "Antrag",
                "titel": "Antrag zur Förderung erneuerbarer Energien",
                "datum": "2024-01-20",
                "wahlperiode": 20,
                "herausgeber": "Fraktion BÜNDNIS 90/DIE GRÜNEN",
                "pdf_url": "https://dserver.bundestag.de/btd/20/056/2005678.pdf",
                "autoren": ["Fraktion BÜNDNIS 90/DIE GRÜNEN"],
                "abstract": "Antrag zur verstärkten Förderung erneuerbarer Energien.",
            },
            "2009012": {
                "id": "2009012",
                "drucksache_nummer": "2009012",
                "dokumentnummer": "20/9012",
                "dokumentart": "Beschlussempfehlung",
                "titel": "Beschlussempfehlung zum Gesetz zur digitalen Verwaltung",
                "datum": "2024-10-05",
                "wahlperiode": 20,
                "herausgeber": "Ausschuss für Inneres und Heimat",
                "pdf_url": "https://dserver.bundestag.de/btd/20/090/2009012.pdf",
                "autoren": ["Ausschuss für Inneres und Heimat"],
                "abstract": "Beschlussempfehlung zur Modernisierung der öffentlichen Verwaltung.",
                "ressort": "Inneres",
            },
        }

    async def get_all_drucksache_ids(self, limit: Optional[int] = None) -> list[str]:
        """Get all mock Drucksache IDs.

        Args:
            limit: Maximum number of IDs to return

        Returns:
            List of Drucksache IDs
        """
        drucksache_ids = list(self.mock_drucksachen.keys())

        if limit:
            drucksache_ids = drucksache_ids[:limit]

        logger.info(f"Returning {len(drucksache_ids)} mock Drucksache IDs")
        return drucksache_ids

    async def get_drucksache_by_id(self, drucksache_id: str) -> Optional[dict[str, Any]]:
        """Get mock Drucksache data by ID.

        Args:
            drucksache_id: Drucksache ID

        Returns:
            Drucksache data dictionary or None
        """
        drucksache = self.mock_drucksachen.get(drucksache_id)

        if drucksache:
            logger.info(f"Returning mock data for Drucksache {drucksache_id}")
        else:
            logger.warning(f"Mock Drucksache {drucksache_id} not found")

        return drucksache
