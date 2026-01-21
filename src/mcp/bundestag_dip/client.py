"""
Bundestag DIP API Client for MCP Server.

Async HTTP client for accessing German Bundestag Document and Information System (DIP) API.
Wraps the existing BundestagAPIClient with MCP-specific methods.
"""

import asyncio
import logging
import os
from typing import Any, Optional

import aiohttp

logger = logging.getLogger(__name__)


class BundestagDIPClient:
    """
    Async HTTP client for Bundestag DIP API.

    Provides methods for making authenticated requests to the German parliamentary
    data API with automatic retry logic and error handling.
    """

    BASE_URL = "https://search.dip.bundestag.de/api/v1"
    DEFAULT_API_KEY = "OSOegLs.PR2lwJ1dwCeje9vTj7FPOt3hvpYKtwKkhw"  # Valid until 05/2026

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: int = 30,
    ):
        """Initialize the Bundestag DIP API client."""
        self.base_url = base_url or self.BASE_URL
        self.api_key = api_key or os.getenv("BUNDESTAG_DIP_API_KEY") or self.DEFAULT_API_KEY
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None

        logger.info(f"Initialized BundestagDIPClient (base_url={self.base_url})")

    async def _ensure_session(self):
        """Ensure aiohttp session is initialized."""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(ssl=False)
            self.session = aiohttp.ClientSession(timeout=self.timeout, connector=connector)

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.debug("Closed aiohttp session")

    async def _get(self, endpoint: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Make a GET request to the API with retry logic."""
        await self._ensure_session()

        params = params or {}
        if "apikey" not in params:
            params["apikey"] = self.api_key

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Making GET request to {url}, attempt {attempt + 1}")

                async with self.session.get(url, params=params) as response:
                    if response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", self.retry_delay * (2 ** attempt)))
                        logger.warning(f"Rate limited, retrying after {retry_after}s")
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(retry_after)
                            continue
                        raise aiohttp.ClientError("Rate limit exceeded")

                    if response.status >= 400:
                        error_text = await response.text()
                        logger.error(f"API error {response.status}: {error_text}")
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(self.retry_delay * (2 ** attempt))
                            continue
                        raise aiohttp.ClientError(f"API error {response.status}: {error_text}")

                    return await response.json()

            except asyncio.TimeoutError:
                logger.warning(f"Request timeout, attempt {attempt + 1}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    continue
                raise

        raise aiohttp.ClientError("Max retries exceeded")

    # =========================================================================
    # Vorgang (Legislative Procedures)
    # =========================================================================

    async def search_vorgaenge(
        self,
        query: str,
        wahlperiode: Optional[int] = None,
        vorgangstyp: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for legislative procedures (Vorgänge)."""
        params = {"format": "json"}

        # Build filter parameters
        if query:
            params["f.titel"] = query
        if wahlperiode:
            params["f.wahlperiode"] = str(wahlperiode)
        if vorgangstyp:
            params["f.vorgangstyp"] = vorgangstyp

        try:
            data = await self._get("vorgang", params)
            documents = data.get("documents", [])[:limit]

            results = []
            for doc in documents:
                results.append({
                    "id": doc.get("id"),
                    "titel": doc.get("titel", ""),
                    "vorgangstyp": doc.get("vorgangstyp", ""),
                    "beratungsstand": doc.get("beratungsstand", ""),
                    "initiative": doc.get("initiative", []),
                    "sachgebiet": doc.get("sachgebiet", []),
                    "wahlperiode": doc.get("wahlperiode"),
                    "datum": doc.get("datum"),
                    "aktualisiert": doc.get("aktualisiert"),
                    "abstract": doc.get("abstract", ""),
                    "schlagwort": doc.get("schlagwort", []),
                })

            logger.info(f"Found {len(results)} Vorgänge for query: {query}")
            return results

        except Exception as e:
            logger.error(f"Error searching Vorgänge: {e}")
            return []

    async def get_vorgang(self, vorgang_id: str) -> Optional[dict[str, Any]]:
        """Get detailed information about a specific Vorgang."""
        try:
            data = await self._get(f"vorgang/{vorgang_id}")

            return {
                "id": data.get("id"),
                "titel": data.get("titel", ""),
                "vorgangstyp": data.get("vorgangstyp", ""),
                "beratungsstand": data.get("beratungsstand", ""),
                "initiative": data.get("initiative", []),
                "sachgebiet": data.get("sachgebiet", []),
                "wahlperiode": data.get("wahlperiode"),
                "datum": data.get("datum"),
                "aktualisiert": data.get("aktualisiert"),
                "abstract": data.get("abstract", ""),
                "schlagwort": data.get("schlagwort", []),
            }

        except Exception as e:
            logger.error(f"Error getting Vorgang {vorgang_id}: {e}")
            return None

    # =========================================================================
    # Drucksache (Parliamentary Documents)
    # =========================================================================

    async def search_drucksachen(
        self,
        query: str,
        dokumentart: Optional[str] = None,
        wahlperiode: Optional[int] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for parliamentary documents (Drucksachen)."""
        params = {"format": "json"}

        if query:
            params["f.titel"] = query
        if dokumentart:
            params["f.dokumentart"] = dokumentart
        if wahlperiode:
            params["f.wahlperiode"] = str(wahlperiode)

        try:
            data = await self._get("drucksache", params)
            documents = data.get("documents", [])[:limit]

            results = []
            for doc in documents:
                results.append({
                    "id": doc.get("id"),
                    "drucksache": doc.get("dokumentnummer", ""),
                    "titel": doc.get("titel", ""),
                    "dokumentart": doc.get("dokumentart", ""),
                    "datum": doc.get("datum"),
                    "wahlperiode": doc.get("wahlperiode"),
                    "autoren": doc.get("autoren_anzeige", []),
                    "pdf_url": doc.get("pdf_url", ""),
                })

            logger.info(f"Found {len(results)} Drucksachen for query: {query}")
            return results

        except Exception as e:
            logger.error(f"Error searching Drucksachen: {e}")
            return []

    async def get_drucksache(self, drucksache_nummer: str) -> Optional[dict[str, Any]]:
        """Get detailed information about a specific Drucksache."""
        try:
            # Search by document number
            params = {"format": "json", "f.dokumentnummer": drucksache_nummer}
            data = await self._get("drucksache", params)

            documents = data.get("documents", [])
            if not documents:
                return None

            doc = documents[0]
            return {
                "id": doc.get("id"),
                "drucksache": doc.get("dokumentnummer", ""),
                "titel": doc.get("titel", ""),
                "dokumentart": doc.get("dokumentart", ""),
                "datum": doc.get("datum"),
                "wahlperiode": doc.get("wahlperiode"),
                "autoren": doc.get("autoren_anzeige", []),
                "pdf_url": doc.get("pdf_url", ""),
            }

        except Exception as e:
            logger.error(f"Error getting Drucksache {drucksache_nummer}: {e}")
            return None

    # =========================================================================
    # Person (Bundestag Members)
    # =========================================================================

    async def search_persons(
        self,
        name: Optional[str] = None,
        fraktion: Optional[str] = None,
        wahlperiode: Optional[int] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for Bundestag members."""
        params = {"format": "json"}

        if name:
            params["f.name"] = name
        if fraktion:
            params["f.fraktion"] = fraktion
        if wahlperiode:
            params["f.wahlperiode"] = str(wahlperiode)

        try:
            data = await self._get("person", params)
            documents = data.get("documents", [])[:limit]

            results = []
            for doc in documents:
                results.append({
                    "id": doc.get("id"),
                    "vorname": doc.get("vorname", ""),
                    "nachname": doc.get("nachname", ""),
                    "fraktion": doc.get("fraktion", ""),
                    "funktion": doc.get("funktion", ""),
                    "wahlkreis": doc.get("wahlkreis", ""),
                    "beruf": doc.get("beruf", ""),
                    "geburtsdatum": doc.get("geburtsdatum", ""),
                })

            logger.info(f"Found {len(results)} persons")
            return results

        except Exception as e:
            logger.error(f"Error searching persons: {e}")
            return []

    async def get_person(self, person_id: str) -> Optional[dict[str, Any]]:
        """Get detailed information about a Bundestag member."""
        try:
            data = await self._get(f"person/{person_id}")

            return {
                "id": data.get("id"),
                "vorname": data.get("vorname", ""),
                "nachname": data.get("nachname", ""),
                "fraktion": data.get("fraktion", ""),
                "funktion": data.get("funktion", ""),
                "wahlkreis": data.get("wahlkreis", ""),
                "beruf": data.get("beruf", ""),
                "geburtsdatum": data.get("geburtsdatum", ""),
            }

        except Exception as e:
            logger.error(f"Error getting person {person_id}: {e}")
            return None

    # =========================================================================
    # Aktivität (Parliamentary Activities)
    # =========================================================================

    async def search_aktivitaeten(
        self,
        query: Optional[str] = None,
        aktivitaetsart: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for parliamentary activities."""
        params = {"format": "json"}

        if query:
            params["f.titel"] = query
        if aktivitaetsart:
            params["f.aktivitaetsart"] = aktivitaetsart
        if date_from:
            params["f.datum.start"] = date_from
        if date_to:
            params["f.datum.end"] = date_to

        try:
            data = await self._get("aktivitaet", params)
            documents = data.get("documents", [])[:limit]

            results = []
            for doc in documents:
                results.append({
                    "id": doc.get("id"),
                    "titel": doc.get("titel", ""),
                    "aktivitaetsart": doc.get("aktivitaetsart", ""),
                    "datum": doc.get("datum"),
                    "person": doc.get("person_anzeige", ""),
                })

            logger.info(f"Found {len(results)} activities")
            return results

        except Exception as e:
            logger.error(f"Error searching activities: {e}")
            return []

    # =========================================================================
    # Plenarprotokoll (Plenary Protocols)
    # =========================================================================

    async def get_plenarprotokoll(
        self,
        sitzungsnummer: Optional[str] = None,
        date: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Get plenary protocol by session number or date."""
        params = {"format": "json"}

        if sitzungsnummer:
            params["f.dokumentnummer"] = sitzungsnummer
        if date:
            params["f.datum"] = date

        try:
            data = await self._get("plenarprotokoll", params)
            documents = data.get("documents", [])

            if not documents:
                return None

            doc = documents[0]
            return {
                "id": doc.get("id"),
                "sitzungsnummer": doc.get("dokumentnummer", ""),
                "datum": doc.get("datum"),
                "wahlperiode": doc.get("wahlperiode"),
                "pdf_url": doc.get("pdf_url", ""),
                "tagesordnung": doc.get("tagesordnungspunkte", []),
            }

        except Exception as e:
            logger.error(f"Error getting Plenarprotokoll: {e}")
            return None
