"""
Bundestag DIP API Client.

Async HTTP client for accessing German Bundestag Document and Information System (DIP) API.
Implements robust error handling with exponential backoff and rate limiting.
"""

import asyncio
from typing import Any, Optional

import aiohttp
import structlog

logger = structlog.get_logger()


class BundestagAPIClient:
    """
    Async HTTP client for Bundestag DIP API.

    Provides methods for making authenticated requests to the German parliamentary
    data API with automatic retry logic and error handling.

    Attributes:
        base_url: Base URL for the DIP API
        api_key: API authentication key
        session: Aiohttp client session
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay in seconds for exponential backoff
    """

    BASE_URL = "https://search.dip.bundestag.de/api/v1/"
    DEFAULT_API_KEY = "OSOegLs.PR2lwJ1dwCeje9vTj7FPOt3hvpYKtwKkhw"  # Valid until 05/2026

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: int = 30,
    ):
        """
        Initialize the Bundestag API client.

        Args:
            api_key: API authentication key (defaults to public key)
            base_url: Base URL for the API (defaults to production)
            max_retries: Maximum number of retry attempts on failure
            retry_delay: Initial delay in seconds for exponential backoff
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or self.BASE_URL
        self.api_key = api_key or self.DEFAULT_API_KEY
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None

        logger.info(
            "Initialized BundestagAPIClient", base_url=self.base_url, max_retries=self.max_retries
        )

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self):
        """Ensure aiohttp session is initialized."""
        if self.session is None or self.session.closed:
            # Create connector with SSL verification disabled for development
            # Note: In production, ensure proper SSL certificates are installed
            connector = aiohttp.TCPConnector(ssl=False)
            self.session = aiohttp.ClientSession(timeout=self.timeout, connector=connector)
            logger.debug("Created new aiohttp session with SSL verification disabled")

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.debug("Closed aiohttp session")

    async def get(self, endpoint: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """
        Make a GET request to the API with retry logic.

        Args:
            endpoint: API endpoint (relative to base_url)
            params: Query parameters for the request

        Returns:
            JSON response as dictionary

        Raises:
            aiohttp.ClientError: On request failure after all retries
        """
        await self._ensure_session()

        # Add API key to parameters
        params = params or {}
        if "apikey" not in params:
            params["apikey"] = self.api_key

        # Construct full URL (ensure proper slash handling)
        base = self.base_url.rstrip("/")
        endpoint = endpoint.lstrip("/")
        url = f"{base}/{endpoint}"

        # Retry loop with exponential backoff
        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    "Making GET request", url=url, attempt=attempt + 1, max_retries=self.max_retries
                )

                async with self.session.get(url, params=params) as response:
                    # Handle rate limiting
                    if response.status == 429:
                        retry_after = int(
                            response.headers.get("Retry-After", self.retry_delay * (2**attempt))
                        )
                        logger.warning(
                            "Rate limited by API", retry_after=retry_after, attempt=attempt + 1
                        )

                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(retry_after)
                            continue
                        else:
                            raise aiohttp.ClientError(
                                f"Rate limit exceeded after {self.max_retries} attempts"
                            )

                    # Handle errors
                    if response.status >= 400:
                        error_text = await response.text()
                        logger.error(
                            "API request failed", status=response.status, error=error_text, url=url
                        )

                        if attempt < self.max_retries - 1:
                            delay = self.retry_delay * (2**attempt)
                            logger.info(f"Retrying after {delay}s delay", attempt=attempt + 1)
                            await asyncio.sleep(delay)
                            continue
                        else:
                            raise aiohttp.ClientError(
                                f"API request failed with status {response.status}: {error_text}"
                            )

                    # Success - parse and return JSON
                    data = await response.json()
                    logger.info("API request successful", endpoint=endpoint, status=response.status)
                    return data

            except asyncio.TimeoutError:
                logger.warning("Request timeout", url=url, attempt=attempt + 1)

                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2**attempt)
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise aiohttp.ClientError(f"Request timeout after {self.max_retries} attempts")

            except aiohttp.ClientError as e:
                logger.error("Client error during request", error=str(e), attempt=attempt + 1)

                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2**attempt)
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise

        # Should never reach here due to raises in loop
        raise aiohttp.ClientError("Unexpected error in retry loop")

    async def get_by_id(self, endpoint: str, resource_id: str) -> dict[str, Any]:
        """
        Get a specific resource by ID.

        Args:
            endpoint: API endpoint (e.g., 'vorgang', 'drucksache')
            resource_id: Unique identifier for the resource

        Returns:
            JSON response as dictionary

        Raises:
            aiohttp.ClientError: On request failure
        """
        full_endpoint = f"{endpoint}/{resource_id}"

        logger.info("Fetching resource by ID", endpoint=endpoint, resource_id=resource_id)

        return await self.get(full_endpoint)

    async def health_check(self) -> bool:
        """
        Check if the API is accessible.

        Returns:
            True if API is reachable, False otherwise
        """
        try:
            # Try to fetch a minimal response
            await self.get("vorgang", params={"f.datum": "2024-01-01", "num": 1})
            logger.info("API health check passed")
            return True
        except Exception as e:
            logger.error("API health check failed", error=str(e))
            return False
