"""
Sitemap-based Discovery Strategy.

Discovers content by parsing XML sitemaps from websites.
This is the lowest priority strategy as sitemaps may be outdated
or contain many irrelevant URLs.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional
from xml.etree import ElementTree as ET

import structlog

from .base import BaseDiscoveryStrategy
from .models import (
    DiscoveredArticle,
    DiscoveryResult,
    DiscoveryStrategy,
    SiteConfig,
    StrategyAvailability,
)

logger = structlog.get_logger()

# Sitemap namespaces
SITEMAP_NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "news": "http://www.google.com/schemas/sitemap-news/0.9",
    "image": "http://www.google.com/schemas/sitemap-image/1.1",
}


class SitemapDiscoveryStrategy(BaseDiscoveryStrategy):
    """Discovers content from XML sitemaps.

    Priority 3 strategy - Sitemap parsing as fallback.
    Useful when RSS feeds and section crawling are not available.
    """

    @property
    def strategy_name(self) -> DiscoveryStrategy:
        return DiscoveryStrategy.SITEMAP

    async def discover(self, limit: Optional[int] = None) -> DiscoveryResult:
        """Discover articles from sitemaps.

        Args:
            limit: Maximum number of articles to discover

        Returns:
            DiscoveryResult with discovered articles
        """
        result = DiscoveryResult(
            success=False,
            strategy=DiscoveryStrategy.SITEMAP,
        )

        sitemap_url = self._strategy_config.get("sitemap_url")
        if not sitemap_url:
            # Try default location
            sitemap_url = f"https://{self.site_config.domain}/sitemap.xml"

        include_patterns = self._strategy_config.get("include_patterns", [])
        exclude_patterns = self._strategy_config.get("exclude_patterns", [])
        max_urls = self._strategy_config.get("max_urls", 500)

        try:
            # Fetch and parse sitemap (may be a sitemap index)
            all_urls = await self._parse_sitemap(sitemap_url, max_urls)

            logger.info(
                f"Parsed sitemap",
                url=sitemap_url,
                total_urls=len(all_urls),
            )

            # Filter URLs by patterns
            filtered_urls = self._filter_urls(
                all_urls,
                include_patterns,
                exclude_patterns,
            )

            logger.info(
                f"Filtered sitemap URLs",
                before=len(all_urls),
                after=len(filtered_urls),
            )

            # Apply limit
            if limit and len(filtered_urls) > limit:
                filtered_urls = filtered_urls[:limit]

            # Convert to DiscoveredArticle objects
            articles = [
                DiscoveredArticle(
                    url=url_data["url"],
                    title=self._extract_title_from_url(url_data["url"]),
                    source_domain=self.site_config.domain,
                    discovery_strategy=DiscoveryStrategy.SITEMAP,
                    published_date=url_data.get("lastmod"),
                    sitemap_priority=url_data.get("priority"),
                    sitemap_changefreq=url_data.get("changefreq"),
                )
                for url_data in filtered_urls
            ]

            result.articles = articles
            result.urls_discovered = len(articles)
            result.urls_filtered = len(all_urls) - len(filtered_urls)
            result.sitemaps_processed = 1  # Could be more with sitemap index
            result.success = True

        except Exception as e:
            result.errors.append(f"Failed to parse sitemap {sitemap_url}: {str(e)}")
            logger.error(f"Sitemap parse error", url=sitemap_url, error=str(e))

        result.mark_completed()

        logger.info(
            f"Sitemap discovery complete",
            site=self.site_config.domain,
            articles=len(result.articles),
        )

        return result

    async def is_available(self) -> StrategyAvailability:
        """Check if sitemap discovery is available for this site.

        Returns:
            StrategyAvailability indicating if sitemap is accessible
        """
        sitemap_url = self._strategy_config.get("sitemap_url")
        if not sitemap_url:
            sitemap_url = f"https://{self.site_config.domain}/sitemap.xml"

        if await self._check_url_exists(sitemap_url):
            return StrategyAvailability(
                available=True,
                reason=f"Sitemap accessible at {sitemap_url}",
            )

        # Try common alternative locations
        alternatives = [
            f"https://www.{self.site_config.domain}/sitemap.xml",
            f"https://{self.site_config.domain}/sitemap_index.xml",
            f"https://{self.site_config.domain}/sitemaps/sitemap.xml",
        ]

        for alt_url in alternatives:
            if await self._check_url_exists(alt_url):
                return StrategyAvailability(
                    available=True,
                    reason=f"Sitemap found at {alt_url}",
                )

        return StrategyAvailability(
            available=False,
            reason="No sitemap found at default locations",
        )

    async def _parse_sitemap(
        self,
        sitemap_url: str,
        max_urls: int,
    ) -> list[dict]:
        """Parse a sitemap or sitemap index.

        Args:
            sitemap_url: URL of the sitemap
            max_urls: Maximum URLs to extract

        Returns:
            List of URL data dictionaries
        """
        content = await self._fetch_url(sitemap_url)
        if not content:
            raise ValueError(f"Failed to fetch sitemap: {sitemap_url}")

        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML in sitemap: {e}")

        urls = []

        # Check if this is a sitemap index
        if root.tag.endswith("sitemapindex") or "sitemapindex" in root.tag:
            urls = await self._parse_sitemap_index(root, max_urls)
        else:
            # Regular sitemap
            urls = self._parse_urlset(root, max_urls)

        return urls

    async def _parse_sitemap_index(
        self,
        root: ET.Element,
        max_urls: int,
    ) -> list[dict]:
        """Parse a sitemap index and fetch child sitemaps.

        Args:
            root: XML root element
            max_urls: Maximum URLs to extract

        Returns:
            List of URL data from all child sitemaps
        """
        all_urls = []

        # Find child sitemap URLs
        sitemap_elements = root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap")
        if not sitemap_elements:
            sitemap_elements = root.findall(".//sitemap")

        for sitemap_elem in sitemap_elements:
            if len(all_urls) >= max_urls:
                break

            loc = sitemap_elem.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
            if loc is None:
                loc = sitemap_elem.find("loc")

            if loc is not None and loc.text:
                child_url = loc.text.strip()

                # Filter by include patterns if configured
                include_patterns = self._strategy_config.get("include_patterns", [])
                if include_patterns:
                    if not any(self._match_pattern(child_url, p) for p in include_patterns):
                        continue

                try:
                    child_content = await self._fetch_url(child_url)
                    if child_content:
                        child_root = ET.fromstring(child_content)
                        child_urls = self._parse_urlset(
                            child_root,
                            max_urls - len(all_urls),
                        )
                        all_urls.extend(child_urls)
                        logger.debug(
                            f"Parsed child sitemap",
                            url=child_url,
                            urls=len(child_urls),
                        )
                except Exception as e:
                    logger.warning(f"Failed to parse child sitemap", url=child_url, error=str(e))

        return all_urls

    def _parse_urlset(
        self,
        root: ET.Element,
        max_urls: int,
    ) -> list[dict]:
        """Parse a urlset sitemap.

        Args:
            root: XML root element
            max_urls: Maximum URLs to extract

        Returns:
            List of URL data dictionaries
        """
        urls = []

        url_elements = root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}url")
        if not url_elements:
            url_elements = root.findall(".//url")

        for url_elem in url_elements[:max_urls]:
            url_data = self._parse_url_element(url_elem)
            if url_data:
                urls.append(url_data)

        return urls

    def _parse_url_element(self, url_elem: ET.Element) -> Optional[dict]:
        """Parse a single URL element from sitemap.

        Args:
            url_elem: XML url element

        Returns:
            Dictionary with URL data or None
        """
        # Extract loc (required)
        loc = url_elem.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
        if loc is None:
            loc = url_elem.find("loc")

        if loc is None or not loc.text:
            return None

        url = loc.text.strip()

        # Validate URL
        if not self._is_valid_article_url(url):
            return None

        # Extract optional elements
        lastmod = None
        lastmod_elem = url_elem.find("{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod")
        if lastmod_elem is None:
            lastmod_elem = url_elem.find("lastmod")
        if lastmod_elem is not None and lastmod_elem.text:
            lastmod = self._parse_sitemap_date(lastmod_elem.text.strip())

        priority = None
        priority_elem = url_elem.find("{http://www.sitemaps.org/schemas/sitemap/0.9}priority")
        if priority_elem is None:
            priority_elem = url_elem.find("priority")
        if priority_elem is not None and priority_elem.text:
            try:
                priority = float(priority_elem.text.strip())
            except ValueError:
                pass

        changefreq = None
        changefreq_elem = url_elem.find("{http://www.sitemaps.org/schemas/sitemap/0.9}changefreq")
        if changefreq_elem is None:
            changefreq_elem = url_elem.find("changefreq")
        if changefreq_elem is not None and changefreq_elem.text:
            changefreq = changefreq_elem.text.strip()

        # Check for news sitemap extension
        news_data = self._parse_news_extension(url_elem)

        return {
            "url": url,
            "lastmod": lastmod,
            "priority": priority,
            "changefreq": changefreq,
            **news_data,
        }

    def _parse_news_extension(self, url_elem: ET.Element) -> dict:
        """Parse Google News sitemap extension.

        Args:
            url_elem: XML url element

        Returns:
            Dictionary with news data
        """
        news_data = {}

        news_elem = url_elem.find("{http://www.google.com/schemas/sitemap-news/0.9}news")
        if news_elem is None:
            return news_data

        # Extract publication date
        pub_date = news_elem.find(
            "{http://www.google.com/schemas/sitemap-news/0.9}publication_date"
        )
        if pub_date is not None and pub_date.text:
            news_data["news_pub_date"] = self._parse_sitemap_date(pub_date.text.strip())

        # Extract title
        title = news_elem.find("{http://www.google.com/schemas/sitemap-news/0.9}title")
        if title is not None and title.text:
            news_data["news_title"] = title.text.strip()

        # Extract keywords
        keywords = news_elem.find("{http://www.google.com/schemas/sitemap-news/0.9}keywords")
        if keywords is not None and keywords.text:
            news_data["news_keywords"] = keywords.text.strip()

        return news_data

    def _filter_urls(
        self,
        urls: list[dict],
        include_patterns: list[str],
        exclude_patterns: list[str],
    ) -> list[dict]:
        """Filter URLs by include/exclude patterns.

        Args:
            urls: List of URL data
            include_patterns: Patterns to include (if any, only matching are kept)
            exclude_patterns: Patterns to exclude

        Returns:
            Filtered list of URLs
        """
        filtered = []

        for url_data in urls:
            url = url_data["url"]

            # Check exclude patterns first
            if any(self._match_pattern(url, p) for p in exclude_patterns):
                continue

            # Check include patterns (if specified)
            if include_patterns:
                if not any(self._match_pattern(url, p) for p in include_patterns):
                    continue

            filtered.append(url_data)

        return filtered

    def _match_pattern(self, url: str, pattern: str) -> bool:
        """Check if URL matches a pattern.

        Supports glob-like patterns with * wildcard.

        Args:
            url: URL to check
            pattern: Pattern to match

        Returns:
            True if URL matches pattern
        """
        # Convert glob pattern to regex
        regex_pattern = pattern.replace("*", ".*")

        # If pattern starts with /, match against path only
        if pattern.startswith("/"):
            from urllib.parse import urlparse

            parsed = urlparse(url)
            return bool(re.search(regex_pattern, parsed.path))

        # Otherwise match against full URL
        return bool(re.search(regex_pattern, url))

    def _parse_sitemap_date(self, date_str: str) -> Optional[datetime]:
        """Parse sitemap date format (W3C/ISO 8601).

        Args:
            date_str: Date string to parse

        Returns:
            datetime or None
        """
        # Sitemap uses W3C/ISO 8601 format
        formats = [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
        ]

        # Handle Z suffix
        if date_str.endswith("Z"):
            date_str = date_str[:-1] + "+00:00"

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # Try fromisoformat
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            pass

        logger.warning(f"Could not parse sitemap date", date=date_str)
        return None

    def _extract_title_from_url(self, url: str) -> str:
        """Extract a human-readable title from URL.

        Args:
            url: URL to extract title from

        Returns:
            Extracted title
        """
        from urllib.parse import unquote, urlparse

        parsed = urlparse(url)
        path = unquote(parsed.path)

        # Get last path segment
        segments = [s for s in path.split("/") if s]
        if not segments:
            return "Untitled"

        # Clean up the last segment
        title = segments[-1]

        # Remove common extensions
        title = re.sub(r"\.(html?|php|aspx?)$", "", title, flags=re.IGNORECASE)

        # Replace separators with spaces
        title = re.sub(r"[-_]", " ", title)

        # Title case
        title = title.title()

        return title[:200] or "Untitled"
