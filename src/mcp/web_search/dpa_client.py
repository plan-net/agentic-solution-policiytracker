"""
DPA News API Client for MCP Server.

Async HTTP client for German Press Agency (DPA) news search.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Optional
from urllib.parse import quote

import aiohttp

logger = logging.getLogger(__name__)


class DPANewsClient:
    """
    Async HTTP client for DPA-IQ-Retriever API.

    Provides German press agency news search capabilities.
    """

    API_BASE_URL = "https://article-retriever.iq.dpa-ai-hub.de"
    DPA_NEWS_HUB_URL = "https://www.dpa-news-hub.de/archiv/detail"

    def __init__(self, api_key: Optional[str] = None, timeout: int = 120):
        """Initialize the DPA News client."""
        self.api_key = api_key or os.getenv("DPA_API_KEY")
        if not self.api_key:
            logger.warning("DPA_API_KEY not provided - DPA search will be unavailable")

        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.headers = {
            "X-API-Key": self.api_key or "",
            "Content-Type": "application/json"
        }
        self.session: Optional[aiohttp.ClientSession] = None

        logger.info("Initialized DPANewsClient")

    async def _ensure_session(self):
        """Ensure aiohttp session is initialized."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.debug("Closed DPA aiohttp session")

    def is_available(self) -> bool:
        """Check if DPA client is properly configured."""
        return self.api_key is not None and len(self.api_key) > 0

    async def search_news(
        self,
        query: str,
        max_items: int = 20,
        days_back: int = 7,
    ) -> list[dict[str, Any]]:
        """
        Search for news articles from DPA.

        Args:
            query: Search query
            max_items: Maximum number of items to return
            days_back: How many days back to search

        Returns:
            List of news articles
        """
        if not self.is_available():
            logger.warning("DPA API key not configured")
            return []

        await self._ensure_session()

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        from_datetime = start_date.strftime("%Y-%m-%dT%H:%M:%S")
        to_datetime = end_date.strftime("%Y-%m-%dT%H:%M:%S")

        payload = {
            "query": query,
            "limit": min(max_items, 20),  # API limit
            "from_datetime": from_datetime,
            "to_datetime": to_datetime,
            "response_format": "article_objects_markdown",
        }

        try:
            async with self.session.post(
                f"{self.API_BASE_URL}/articles/relevant",
                headers=self.headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"DPA API error {response.status}: {error_text}")
                    return []

                data = await response.json()
                context_items = data.get("context", [])

                if isinstance(context_items, str):
                    logger.warning("DPA returned markdown instead of article objects")
                    return []

                results = self._normalize_results(context_items)
                logger.info(f"DPA search found {len(results)} results for: {query}")
                return results

        except Exception as e:
            logger.error(f"Error in DPA search: {e}")
            return []

    def _normalize_results(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Normalize DPA results to standard format."""
        normalized = []

        for item in items:
            urn = item.get("urn", "")
            url = self._construct_url_from_urn(urn)

            # Parse date
            published_date = item.get("version_created_at_utc", "")
            if published_date:
                try:
                    dt = datetime.fromisoformat(published_date.replace("Z", "+00:00"))
                    published_date = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    pass

            content = item.get("article_complete_markdown", "")
            tags = item.get("tags", [])

            # Extract language
            language = "de"
            for tag in tags:
                if tag.startswith("dnllang:"):
                    language = tag.replace("dnllang:", "")
                    break

            normalized.append({
                "title": item.get("headline", "Untitled"),
                "url": url,
                "source": "DPA",
                "published_date": published_date,
                "content": content,
                "content_preview": content[:500] + "..." if len(content) > 500 else content,
                "score": item.get("score", 0),
                "language": language,
                "tags": tags,
                "dpa_urn": urn,
            })

        return normalized

    def _construct_url_from_urn(self, urn: str) -> str:
        """Construct article URL from URN."""
        if not urn:
            return ""
        return f"{self.DPA_NEWS_HUB_URL}/{quote(urn, safe=':')}"
