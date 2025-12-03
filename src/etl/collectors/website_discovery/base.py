"""
Base class for website discovery strategies.

Provides the abstract interface that all discovery strategies must implement,
plus common utility methods for HTTP requests and content extraction.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import aiohttp
import structlog

from .models import DiscoveryResult, DiscoveryStrategy, SiteConfig, StrategyAvailability

logger = structlog.get_logger()


class BaseDiscoveryStrategy(ABC):
    """Abstract base class for URL discovery strategies.

    Each strategy (RSS, Section, Sitemap) must implement:
    - strategy_name: Identify the strategy type
    - priority: Determine fallback order
    - discover: Main discovery logic
    - is_available: Check if strategy can be used for a site
    """

    def __init__(
        self,
        site_config: SiteConfig,
        http_session: Optional[aiohttp.ClientSession] = None,
        user_agent: str = "PolicyTracker/1.0 (Political Monitoring Research)",
        request_timeout: int = 30,
    ):
        """Initialize the discovery strategy.

        Args:
            site_config: Configuration for the target website
            http_session: Optional shared aiohttp session
            user_agent: User-Agent header for requests
            request_timeout: Request timeout in seconds
        """
        self.site_config = site_config
        self._session = http_session
        self._owns_session = http_session is None
        self.user_agent = user_agent
        self.request_timeout = request_timeout

        # Get strategy-specific config
        self._strategy_config = site_config.get_strategy_config(self.strategy_name.value) or {}

        logger.info(
            f"Initialized {self.strategy_name.value} strategy",
            site=site_config.domain,
            config_keys=list(self._strategy_config.keys()),
        )

    @property
    @abstractmethod
    def strategy_name(self) -> DiscoveryStrategy:
        """Return the strategy type identifier."""
        pass

    @property
    def priority(self) -> int:
        """Return the priority for this strategy (lower = higher priority).

        Defaults to configured priority or a fallback based on strategy type.
        """
        configured = self.site_config.get_strategy_priority(self.strategy_name.value)
        if configured is not None:
            return configured

        # Default priorities
        defaults = {
            DiscoveryStrategy.RSS: 1,
            DiscoveryStrategy.SECTION: 2,
            DiscoveryStrategy.SITEMAP: 3,
        }
        return defaults.get(self.strategy_name, 99)

    @abstractmethod
    async def discover(self, limit: Optional[int] = None) -> DiscoveryResult:
        """Execute the discovery strategy to find articles.

        Args:
            limit: Optional maximum number of articles to discover

        Returns:
            DiscoveryResult containing discovered articles and metadata
        """
        pass

    @abstractmethod
    async def is_available(self) -> StrategyAvailability:
        """Check if this strategy is available for the configured site.

        Returns:
            StrategyAvailability indicating whether the strategy can be used
        """
        pass

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create the HTTP session."""
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.request_timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers=self._get_default_headers(),
            )
        return self._session

    async def close(self) -> None:
        """Close the HTTP session if we own it."""
        if self._owns_session and self._session is not None:
            await self._session.close()
            self._session = None

    def _get_default_headers(self) -> dict[str, str]:
        """Get default HTTP headers for requests."""
        return {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

    async def _fetch_url(self, url: str) -> Optional[str]:
        """Fetch content from a URL.

        Args:
            url: URL to fetch

        Returns:
            Response text content, or None if failed
        """
        try:
            session = await self.get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.warning(
                        f"HTTP {response.status} for URL",
                        url=url,
                        status=response.status,
                    )
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching URL", url=url, error=str(e))
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching URL", url=url, error=str(e))
            return None

    async def _check_url_exists(self, url: str) -> bool:
        """Check if a URL exists (returns 200 status).

        Args:
            url: URL to check

        Returns:
            True if URL exists and returns 200
        """
        try:
            session = await self.get_session()
            async with session.head(url, allow_redirects=True) as response:
                return response.status == 200
        except Exception:
            return False

    def _normalize_url(self, url: str, base_url: Optional[str] = None) -> str:
        """Normalize a URL to absolute form.

        Args:
            url: URL to normalize (may be relative)
            base_url: Base URL for resolving relative URLs

        Returns:
            Absolute URL
        """
        from urllib.parse import urljoin, urlparse

        # Already absolute
        if url.startswith(("http://", "https://")):
            return url

        # Use base_url or construct from site domain
        if base_url is None:
            base_url = f"https://{self.site_config.domain}"

        return urljoin(base_url, url)

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return parsed.netloc.replace("www.", "")

    def _is_valid_article_url(self, url: str) -> bool:
        """Check if URL looks like a valid article URL.

        Filters out common non-article URLs (images, PDFs, etc.)
        """
        # Exclude patterns
        exclude_patterns = [
            ".pdf",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".svg",
            ".ico",
            ".css",
            ".js",
            ".xml",
            ".json",
            "/feed",
            "/rss",
            "/sitemap",
            "/robots.txt",
            "/favicon",
            "/cdn-cgi/",
            "/wp-content/uploads/",
            "/static/",
            "/assets/",
        ]

        url_lower = url.lower()
        return not any(pattern in url_lower for pattern in exclude_patterns)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(site={self.site_config.domain}, priority={self.priority})"
