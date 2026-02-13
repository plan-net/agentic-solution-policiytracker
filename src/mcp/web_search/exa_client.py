"""
Exa.ai API Client for MCP Server.

Async HTTP client for web and news search via Exa.ai API.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Optional

import aiohttp

logger = logging.getLogger(__name__)


class ExaSearchClient:
    """
    Async HTTP client for Exa.ai search API.

    Provides web search and news search capabilities.
    Supports routing through APISIX gateway when USE_APISIX_FOR_EXA=true.
    """

    API_BASE_URL = "https://api.exa.ai"

    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        """Initialize the Exa.ai client."""
        self.api_key = api_key or os.getenv("EXA_API_KEY")
        if not self.api_key:
            raise ValueError("EXA_API_KEY not provided or found in environment")

        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key
        }
        self.session: Optional[aiohttp.ClientSession] = None

        # APISIX Gateway support
        self.use_apisix = os.getenv("USE_APISIX_FOR_EXA", "false").lower() == "true"
        self.apisix_url = os.getenv("APISIX_GATEWAY_URL", "http://localhost:9080")

        if self.use_apisix:
            logger.info(f"Initialized ExaSearchClient via APISIX: {self.apisix_url}/exa")
        else:
            logger.info("Initialized ExaSearchClient (direct API)")

    async def _ensure_session(self):
        """Ensure aiohttp session is initialized."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.debug("Closed Exa aiohttp session")

    async def web_search(
        self,
        query: str,
        num_results: int = 10,
        include_domains: Optional[list[str]] = None,
        exclude_domains: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        """
        Perform a general web search.

        Args:
            query: Search query
            num_results: Number of results to return
            include_domains: Only include results from these domains
            exclude_domains: Exclude results from these domains

        Returns:
            List of search results
        """
        await self._ensure_session()

        payload = {
            "query": query,
            "numResults": min(num_results, 100),
            "contents": {"text": True},
        }

        if include_domains:
            payload["includeDomains"] = include_domains
        if exclude_domains:
            payload["excludeDomains"] = exclude_domains

        # Determine URL based on APISIX setting
        if self.use_apisix:
            url = f"{self.apisix_url}/exa/search"
        else:
            url = f"{self.API_BASE_URL}/search"

        try:
            async with self.session.post(
                url,
                headers=self.headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Exa API error {response.status}: {error_text}")
                    return []

                data = await response.json()
                results = self._normalize_results(data.get("results", []))
                logger.info(f"Web search found {len(results)} results for: {query}")
                return results

        except Exception as e:
            logger.error(f"Error in web search: {e}")
            return []

    async def search_news(
        self,
        query: str,
        num_results: int = 10,
        days_back: int = 7,
        include_domains: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        """
        Search for news articles.

        Args:
            query: Search query
            num_results: Number of results to return
            days_back: How many days back to search
            include_domains: Only include results from these domains

        Returns:
            List of news articles
        """
        await self._ensure_session()

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        start_published_date = start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        payload = {
            "query": query,
            "category": "news",
            "numResults": min(num_results, 100),
            "startPublishedDate": start_published_date,
            "contents": {"text": True},
        }

        if include_domains:
            payload["includeDomains"] = include_domains

        # Determine URL based on APISIX setting
        if self.use_apisix:
            url = f"{self.apisix_url}/exa/search"
        else:
            url = f"{self.API_BASE_URL}/search"

        try:
            async with self.session.post(
                url,
                headers=self.headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Exa API error {response.status}: {error_text}")
                    return []

                data = await response.json()
                results = self._normalize_results(data.get("results", []))
                logger.info(f"News search found {len(results)} results for: {query}")
                return results

        except Exception as e:
            logger.error(f"Error in news search: {e}")
            return []

    async def get_contents(self, urls: list[str]) -> list[dict[str, Any]]:
        """
        Get content for specific URLs.

        Args:
            urls: List of URLs to fetch content for

        Returns:
            List of content results
        """
        await self._ensure_session()

        payload = {
            "urls": urls[:10],  # Limit to 10 URLs
            "contents": {"text": True},
        }

        # Determine URL based on APISIX setting
        if self.use_apisix:
            url = f"{self.apisix_url}/exa/contents"
        else:
            url = f"{self.API_BASE_URL}/contents"

        try:
            async with self.session.post(
                url,
                headers=self.headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Exa API error {response.status}: {error_text}")
                    return []

                data = await response.json()
                results = self._normalize_results(data.get("results", []))
                logger.info(f"Got content for {len(results)} URLs")
                return results

        except Exception as e:
            logger.error(f"Error getting contents: {e}")
            return []

    def _normalize_results(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Normalize Exa.ai results to standard format."""
        normalized = []

        for item in results:
            # Extract source from URL
            source = "Unknown"
            url = item.get("url", "")
            if url:
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    domain = parsed.netloc.replace("www.", "")
                    source_parts = domain.split(".")
                    if len(source_parts) >= 2:
                        source = source_parts[0].replace("-", " ").title()
                except Exception:
                    pass

            # Parse date
            published_date = item.get("publishedDate", "")
            if published_date:
                try:
                    # Try to parse and reformat
                    dt = datetime.fromisoformat(published_date.replace("Z", "+00:00"))
                    published_date = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    pass

            content = item.get("text", "")
            normalized.append({
                "title": item.get("title", "Untitled"),
                "url": url,
                "source": source,
                "published_date": published_date,
                "content": content,
                "content_preview": content[:500] + "..." if len(content) > 500 else content,
                "score": item.get("score", 0),
                "author": item.get("author", ""),
            })

        return normalized
