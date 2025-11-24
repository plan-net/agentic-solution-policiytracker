"""Bundestag DIP API Client for fetching person data."""
import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class BundestagDIPClient:
    """Client for Bundestag DIP (Dokumentations- und Informationssystem für Parlamentsmaterialien) API."""

    def __init__(self, api_key: Optional[str] = None, api_base_url: str = None):
        """Initialize DIP API client.

        Args:
            api_key: API key for authentication (if required)
            api_base_url: Base URL for DIP API
        """
        self.api_key = api_key
        self.api_base_url = api_base_url or "https://search.dip.bundestag.de/api/v1"
        self.timeout = httpx.Timeout(30.0)

        logger.info(f"BundestagDIPClient initialized (base_url={self.api_base_url})")

    async def get_all_person_ids(self, limit: Optional[int] = None) -> list[str]:
        """Get all person IDs from DIP API.

        Args:
            limit: Maximum number of IDs to return

        Returns:
            List of person IDs
        """
        # Note: This is a simplified implementation
        # Real DIP API may require pagination

        endpoint = "/person"
        params = {"f.typ": "Person", "format": "json"}

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
                    # Extract person IDs from response
                    # Structure depends on actual DIP API response format
                    persons = data.get("documents", [])
                    person_ids = [p.get("id") for p in persons if p.get("id")]

                    logger.info(f"Retrieved {len(person_ids)} person IDs from DIP API")
                    return person_ids
                else:
                    logger.error(f"DIP API error: {response.status_code} - {response.text}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching person IDs from DIP API: {e}")
            return []

    async def get_person_by_id(self, person_id: str) -> Optional[dict[str, Any]]:
        """Get detailed person data by ID.

        Args:
            person_id: Person ID

        Returns:
            Person data dictionary or None
        """
        endpoint = f"/person/{person_id}"

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
                    # This mapping depends on actual DIP API response structure
                    person = self._transform_dip_person(data)

                    return person
                elif response.status_code == 404:
                    logger.warning(f"Person {person_id} not found in DIP API")
                    return None
                else:
                    logger.error(f"DIP API error for person {person_id}: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching person {person_id} from DIP API: {e}")
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

    def _transform_dip_person(self, dip_data: dict[str, Any]) -> dict[str, Any]:
        """Transform DIP API person data to internal format.

        This method maps DIP API field names to our internal field names.

        Args:
            dip_data: Raw DIP API response

        Returns:
            Transformed person dictionary
        """
        # Note: This mapping is based on assumed DIP API structure
        # Actual field names may differ

        person = {
            "id": dip_data.get("id"),
            "vorname": dip_data.get("vorname"),
            "nachname": dip_data.get("nachname"),
            "titel": dip_data.get("akad_titel", ""),
            "geschlecht": dip_data.get("geschlecht"),
            "geburtsdatum": dip_data.get("geburtsdatum"),
            "geburtsort": dip_data.get("geburtsort"),
            "sterbedatum": dip_data.get("sterbedatum"),
        }

        # Add current mandate information if available
        if "aktuelles_mandat" in dip_data:
            mandate = dip_data["aktuelles_mandat"]
            person["fraktion"] = mandate.get("fraktion")
            person["land"] = mandate.get("land")
            person["wahlkreis"] = mandate.get("wahlkreis")

        return person


# Mock client for testing without actual DIP API access
class MockBundestagDIPClient:
    """Mock DIP client for testing and development."""

    def __init__(self, api_key: Optional[str] = None, api_base_url: str = None):
        """Initialize mock DIP client."""
        logger.info("MockBundestagDIPClient initialized (using mock data)")

        # Mock data for testing
        self.mock_persons = {
            "11004809": {
                "id": "11004809",
                "vorname": "Olaf",
                "nachname": "Scholz",
                "titel": "Dr.",
                "geschlecht": "männlich",
                "geburtsdatum": "1958-06-14",
                "geburtsort": "Osnabrück",
                "fraktion": "SPD",
                "land": "Hamburg",
                "wahlkreis": "Hamburg-Altona",
            },
            "11003142": {
                "id": "11003142",
                "vorname": "Angela",
                "nachname": "Merkel",
                "titel": "Dr.",
                "geschlecht": "weiblich",
                "geburtsdatum": "1954-07-17",
                "geburtsort": "Hamburg",
                "fraktion": "CDU/CSU",
                "land": "Mecklenburg-Vorpommern",
                "wahlkreis": "Vorpommern-Rügen – Vorpommern-Greifswald I",
            },
        }

    async def get_all_person_ids(self, limit: Optional[int] = None) -> list[str]:
        """Get all mock person IDs.

        Args:
            limit: Maximum number of IDs to return

        Returns:
            List of person IDs
        """
        person_ids = list(self.mock_persons.keys())

        if limit:
            person_ids = person_ids[:limit]

        logger.info(f"Returning {len(person_ids)} mock person IDs")
        return person_ids

    async def get_person_by_id(self, person_id: str) -> Optional[dict[str, Any]]:
        """Get mock person data by ID.

        Args:
            person_id: Person ID

        Returns:
            Person data dictionary or None
        """
        person = self.mock_persons.get(person_id)

        if person:
            logger.info(f"Returning mock data for person {person_id}")
        else:
            logger.warning(f"Mock person {person_id} not found")

        return person
