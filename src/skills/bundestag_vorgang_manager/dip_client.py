"""Bundestag DIP API Client for fetching Vorgang (legislative procedure) data."""
import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class BundestagVorgangDIPClient:
    """Client for Bundestag DIP API - Vorgang endpoint."""

    def __init__(self, api_key: Optional[str] = None, api_base_url: str = None):
        """Initialize DIP API client for Vorgang.

        Args:
            api_key: API key for authentication (if required)
            api_base_url: Base URL for DIP API
        """
        self.api_key = api_key
        self.api_base_url = api_base_url or "https://search.dip.bundestag.de/api/v1"
        self.timeout = httpx.Timeout(30.0)

        logger.info(f"BundestagVorgangDIPClient initialized (base_url={self.api_base_url})")

    async def get_all_vorgang_ids(
        self, limit: Optional[int] = None, wahlperiode: Optional[str] = None
    ) -> list[str]:
        """Get all Vorgang IDs from DIP API with cursor-based pagination.

        Args:
            limit: Maximum number of IDs to return
            wahlperiode: Filter by Wahlperiode (e.g., "21")

        Returns:
            List of Vorgang IDs
        """
        endpoint = "/vorgang"
        all_vorgang_ids = []
        collected = 0
        cursor = None
        page_num = 0

        # Base params for all requests
        base_params = {"format": "json"}

        # Add API key as query parameter (required by DIP API)
        if self.api_key:
            base_params["apikey"] = self.api_key

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

                        # Extract Vorgang IDs from response
                        vorgaenge = data.get("documents", [])
                        page_ids = [v.get("id") for v in vorgaenge if v.get("id")]

                        all_vorgang_ids.extend(page_ids)
                        collected += len(page_ids)

                        logger.info(
                            f"Page {page_num}: Retrieved {len(page_ids)} Vorgang IDs (total: {collected})"
                        )

                        # Check if we've reached the limit
                        if limit and collected >= limit:
                            logger.info(f"Reached limit of {limit} Vorgang IDs")
                            all_vorgang_ids = all_vorgang_ids[:limit]  # Trim to exact limit
                            break

                        # Check for next page cursor
                        cursor = data.get("cursor")
                        if not cursor:
                            logger.info("No more pages available")
                            break

                    elif response.status_code == 429:
                        # Rate limit - log and stop
                        logger.warning(
                            f"Rate limit hit at page {page_num}, returning {collected} IDs collected so far"
                        )
                        break
                    else:
                        logger.error(f"DIP API error: {response.status_code} - {response.text}")
                        break

                logger.info(
                    f"Retrieved total of {len(all_vorgang_ids)} Vorgang IDs from DIP API across {page_num} pages"
                )
                return all_vorgang_ids

        except Exception as e:
            logger.error(f"Error fetching Vorgang IDs from DIP API: {e}")
            return all_vorgang_ids  # Return what we collected before the error

    async def get_vorgang_by_id(self, vorgang_id: str) -> Optional[dict[str, Any]]:
        """Get detailed Vorgang data by ID.

        Args:
            vorgang_id: Vorgang ID

        Returns:
            Vorgang data dictionary or None
        """
        endpoint = f"/vorgang/{vorgang_id}"
        params = {"format": "json"}

        # Add API key as query parameter (required by DIP API)
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
                    vorgang = self._transform_dip_vorgang(data)

                    return vorgang
                elif response.status_code == 404:
                    logger.warning(f"Vorgang {vorgang_id} not found in DIP API")
                    return None
                else:
                    logger.error(f"DIP API error for Vorgang {vorgang_id}: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching Vorgang {vorgang_id} from DIP API: {e}")
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

    def _transform_dip_vorgang(self, dip_data: dict[str, Any]) -> dict[str, Any]:
        """Transform DIP API Vorgang data to internal format.

        This method maps DIP API field names to our internal field names.

        Args:
            dip_data: Raw DIP API response

        Returns:
            Transformed Vorgang dictionary
        """
        # Map DIP API fields to our schema
        vorgang = {
            "id": dip_data.get("id"),
            "vorgang_id": dip_data.get("id"),  # Also store as vorgang_id for Neo4j
            "titel": dip_data.get("titel", ""),
            "vorgangstyp": dip_data.get("vorgangstyp", ""),
            "beratungsstand": dip_data.get("beratungsstand", ""),
            "initiative": dip_data.get("initiative", []),
            "sachgebiet": dip_data.get("sachgebiet", []),
            "wahlperiode": dip_data.get("wahlperiode"),
            "datum": dip_data.get("datum"),
            "aktualisiert": dip_data.get("aktualisiert"),
        }

        # Add optional fields
        if "abstract" in dip_data:
            vorgang["abstract"] = dip_data["abstract"]

        if "schlagwort" in dip_data:
            vorgang["schlagwort"] = dip_data["schlagwort"]

        return vorgang


# Mock client for testing without actual DIP API access
class MockBundestagVorgangDIPClient:
    """Mock DIP client for Vorgang testing and development."""

    def __init__(self, api_key: Optional[str] = None, api_base_url: str = None):
        """Initialize mock DIP client."""
        logger.info("MockBundestagVorgangDIPClient initialized (using mock data)")

        # Mock data for testing - sample legislative procedures
        self.mock_vorgaenge = {
            "287654": {
                "id": "287654",
                "vorgang_id": "287654",
                "titel": "Gesetz zur Stärkung der Cybersicherheit",
                "vorgangstyp": "Gesetzgebung",
                "beratungsstand": "In Beratung",
                "initiative": ["Bundesregierung"],
                "sachgebiet": ["Informationsgesellschaft", "Sicherheit"],
                "wahlperiode": 20,
                "datum": "2024-03-15",
                "aktualisiert": "2024-11-10",
                "abstract": "Gesetz zur Verbesserung der Cybersicherheit in Deutschland.",
            },
            "289123": {
                "id": "289123",
                "vorgang_id": "289123",
                "titel": "Antrag zur Förderung erneuerbarer Energien",
                "vorgangstyp": "Antrag",
                "beratungsstand": "Abgeschlossen",
                "initiative": ["Fraktion BÜNDNIS 90/DIE GRÜNEN"],
                "sachgebiet": ["Energie", "Umwelt"],
                "wahlperiode": 20,
                "datum": "2024-01-20",
                "aktualisiert": "2024-06-30",
                "abstract": "Antrag zur verstärkten Förderung erneuerbarer Energien.",
            },
            "291456": {
                "id": "291456",
                "vorgang_id": "291456",
                "titel": "Gesetz zur digitalen Verwaltung",
                "vorgangstyp": "Gesetzgebung",
                "beratungsstand": "Verkündet",
                "initiative": ["Bundesregierung", "Bundesrat"],
                "sachgebiet": ["Verwaltung", "Digitalisierung"],
                "wahlperiode": 20,
                "datum": "2024-02-10",
                "aktualisiert": "2024-10-15",
                "abstract": "Gesetz zur Modernisierung der öffentlichen Verwaltung.",
            },
        }

    async def get_all_vorgang_ids(
        self, limit: Optional[int] = None, wahlperiode: Optional[str] = None
    ) -> list[str]:
        """Get all mock Vorgang IDs.

        Args:
            limit: Maximum number of IDs to return
            wahlperiode: Filter by Wahlperiode (e.g., "21")

        Returns:
            List of Vorgang IDs
        """
        vorgang_ids = list(self.mock_vorgaenge.keys())

        # Filter by wahlperiode if specified
        if wahlperiode:
            wahlperiode_int = int(wahlperiode)
            vorgang_ids = [
                vid
                for vid in vorgang_ids
                if self.mock_vorgaenge[vid].get("wahlperiode") == wahlperiode_int
            ]

        if limit:
            vorgang_ids = vorgang_ids[:limit]

        logger.info(f"Returning {len(vorgang_ids)} mock Vorgang IDs")
        return vorgang_ids

    async def get_vorgang_by_id(self, vorgang_id: str) -> Optional[dict[str, Any]]:
        """Get mock Vorgang data by ID.

        Args:
            vorgang_id: Vorgang ID

        Returns:
            Vorgang data dictionary or None
        """
        vorgang = self.mock_vorgaenge.get(vorgang_id)

        if vorgang:
            logger.info(f"Returning mock data for Vorgang {vorgang_id}")
        else:
            logger.warning(f"Mock Vorgang {vorgang_id} not found")

        return vorgang
