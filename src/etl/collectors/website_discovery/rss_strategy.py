"""
RSS Feed Discovery Strategy.

Discovers content by parsing RSS/Atom feeds from configured websites.
This is the highest priority strategy as RSS provides structured,
clean data with good metadata.
"""

from __future__ import annotations

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

# Common RSS namespaces
NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "dc": "http://purl.org/dc/elements/1.1/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "media": "http://search.yahoo.com/mrss/",
}


class RSSDiscoveryStrategy(BaseDiscoveryStrategy):
    """Discovers content from RSS/Atom feeds.

    Priority 1 strategy - RSS feeds provide:
    - Clean, structured data
    - Reliable publication dates
    - Article descriptions/summaries
    - Standard format across sites
    """

    @property
    def strategy_name(self) -> DiscoveryStrategy:
        return DiscoveryStrategy.RSS

    async def discover(self, limit: Optional[int] = None) -> DiscoveryResult:
        """Discover articles from configured RSS feeds.

        Args:
            limit: Maximum number of articles to discover

        Returns:
            DiscoveryResult with discovered articles
        """
        result = DiscoveryResult(
            success=False,
            strategy=DiscoveryStrategy.RSS,
        )

        feeds_config = self._strategy_config.get("feeds", [])
        if not feeds_config:
            result.errors.append("No RSS feeds configured")
            result.mark_completed()
            return result

        max_items_per_feed = self._strategy_config.get("max_items_per_feed", 50)
        all_articles: list[DiscoveredArticle] = []

        for feed_config in feeds_config:
            feed_url = feed_config.get("url")
            category = feed_config.get("category", "general")

            if not feed_url:
                result.warnings.append(f"Feed config missing URL: {feed_config}")
                continue

            try:
                articles = await self._parse_feed(
                    feed_url,
                    category,
                    max_items_per_feed,
                )
                all_articles.extend(articles)
                logger.info(
                    f"Parsed RSS feed",
                    url=feed_url,
                    articles=len(articles),
                )
            except Exception as e:
                result.errors.append(f"Failed to parse feed {feed_url}: {str(e)}")
                logger.error(f"RSS feed parse error", url=feed_url, error=str(e))

        # Apply limit if specified
        if limit and len(all_articles) > limit:
            all_articles = all_articles[:limit]

        result.articles = all_articles
        result.urls_discovered = len(all_articles)
        result.feeds_processed = len(feeds_config)
        result.success = len(all_articles) > 0 or len(result.errors) == 0
        result.mark_completed()

        logger.info(
            f"RSS discovery complete",
            site=self.site_config.domain,
            articles=len(all_articles),
            feeds=len(feeds_config),
        )

        return result

    async def is_available(self) -> StrategyAvailability:
        """Check if RSS discovery is available for this site.

        Returns:
            StrategyAvailability indicating if feeds are accessible
        """
        feeds_config = self._strategy_config.get("feeds", [])

        if not feeds_config:
            return StrategyAvailability(
                available=False,
                reason="No RSS feeds configured",
            )

        # Check if at least one feed is accessible
        accessible_feeds = 0
        for feed_config in feeds_config:
            feed_url = feed_config.get("url")
            if feed_url and await self._check_url_exists(feed_url):
                accessible_feeds += 1

        if accessible_feeds == 0:
            return StrategyAvailability(
                available=False,
                reason=f"None of {len(feeds_config)} configured feeds are accessible",
            )

        return StrategyAvailability(
            available=True,
            reason=f"{accessible_feeds}/{len(feeds_config)} feeds accessible",
            feed_count=accessible_feeds,
        )

    async def _parse_feed(
        self,
        feed_url: str,
        category: str,
        max_items: int,
    ) -> list[DiscoveredArticle]:
        """Parse an RSS/Atom feed and extract articles.

        Args:
            feed_url: URL of the feed
            category: Category to assign to articles
            max_items: Maximum items to extract

        Returns:
            List of discovered articles
        """
        content = await self._fetch_url(feed_url)
        if not content:
            raise ValueError(f"Failed to fetch feed: {feed_url}")

        # Parse XML
        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML in feed: {e}")

        articles = []

        # Detect feed type and parse accordingly
        if root.tag == "rss" or root.tag.endswith("rss"):
            # RSS 2.0
            articles = self._parse_rss_items(root, category, max_items)
        elif root.tag == "{http://www.w3.org/2005/Atom}feed" or "atom" in root.tag.lower():
            # Atom feed
            articles = self._parse_atom_entries(root, category, max_items)
        elif root.tag == "feed":
            # Atom without namespace
            articles = self._parse_atom_entries(root, category, max_items)
        else:
            # Try RSS format as fallback
            articles = self._parse_rss_items(root, category, max_items)

        return articles

    def _parse_rss_items(
        self,
        root: ET.Element,
        category: str,
        max_items: int,
    ) -> list[DiscoveredArticle]:
        """Parse RSS 2.0 items.

        Args:
            root: XML root element
            category: Category to assign
            max_items: Maximum items to extract

        Returns:
            List of discovered articles
        """
        articles = []
        channel = root.find("channel")

        if channel is None:
            # Some feeds have items directly under root
            items = root.findall(".//item")
        else:
            items = channel.findall("item")

        for item in items[:max_items]:
            try:
                article = self._rss_item_to_article(item, category)
                if article:
                    articles.append(article)
            except Exception as e:
                logger.warning(f"Failed to parse RSS item", error=str(e))

        return articles

    def _parse_atom_entries(
        self,
        root: ET.Element,
        category: str,
        max_items: int,
    ) -> list[DiscoveredArticle]:
        """Parse Atom feed entries.

        Args:
            root: XML root element
            category: Category to assign
            max_items: Maximum items to extract

        Returns:
            List of discovered articles
        """
        articles = []

        # Try with and without namespace
        entries = root.findall("{http://www.w3.org/2005/Atom}entry")
        if not entries:
            entries = root.findall("entry")

        for entry in entries[:max_items]:
            try:
                article = self._atom_entry_to_article(entry, category)
                if article:
                    articles.append(article)
            except Exception as e:
                logger.warning(f"Failed to parse Atom entry", error=str(e))

        return articles

    def _rss_item_to_article(
        self,
        item: ET.Element,
        category: str,
    ) -> Optional[DiscoveredArticle]:
        """Convert RSS item to DiscoveredArticle.

        Args:
            item: RSS item element
            category: Category to assign

        Returns:
            DiscoveredArticle or None if invalid
        """
        # Extract URL (link is required)
        link = item.findtext("link")
        if not link:
            return None

        # Validate URL
        if not self._is_valid_article_url(link):
            return None

        # Extract title
        title = item.findtext("title") or "Untitled"

        # Extract description
        description = item.findtext("description")
        if not description:
            # Try content:encoded
            description = item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded")

        # Extract published date
        pub_date = None
        pub_date_str = item.findtext("pubDate")
        if pub_date_str:
            pub_date = self._parse_rss_date(pub_date_str)

        # Extract author
        author = item.findtext("author")
        if not author:
            author = item.findtext("{http://purl.org/dc/elements/1.1/}creator")

        # Extract GUID
        guid = item.findtext("guid")

        return DiscoveredArticle(
            url=link,
            title=title,
            source_domain=self.site_config.domain,
            discovery_strategy=DiscoveryStrategy.RSS,
            published_date=pub_date,
            description=self._clean_html(description) if description else None,
            author=author,
            category=category,
            rss_guid=guid,
        )

    def _atom_entry_to_article(
        self,
        entry: ET.Element,
        category: str,
    ) -> Optional[DiscoveredArticle]:
        """Convert Atom entry to DiscoveredArticle.

        Args:
            entry: Atom entry element
            category: Category to assign

        Returns:
            DiscoveredArticle or None if invalid
        """
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        # Extract URL from link element
        link = None
        for link_elem in entry.findall("{http://www.w3.org/2005/Atom}link"):
            rel = link_elem.get("rel", "alternate")
            if rel in ("alternate", None):
                link = link_elem.get("href")
                break

        if not link:
            # Try without namespace
            for link_elem in entry.findall("link"):
                rel = link_elem.get("rel", "alternate")
                if rel in ("alternate", None):
                    link = link_elem.get("href")
                    break

        if not link:
            return None

        # Normalize relative URLs
        link = self._normalize_url(link)

        # Validate URL
        if not self._is_valid_article_url(link):
            return None

        # Extract title
        title_elem = entry.find("{http://www.w3.org/2005/Atom}title")
        if title_elem is None:
            title_elem = entry.find("title")
        title = title_elem.text if title_elem is not None else "Untitled"

        # Extract description/summary
        summary_elem = entry.find("{http://www.w3.org/2005/Atom}summary")
        if summary_elem is None:
            summary_elem = entry.find("summary")
        description = summary_elem.text if summary_elem is not None else None

        # Extract published date
        pub_date = None
        published_elem = entry.find("{http://www.w3.org/2005/Atom}published")
        if published_elem is None:
            published_elem = entry.find("published")
        if published_elem is None:
            published_elem = entry.find("{http://www.w3.org/2005/Atom}updated")
        if published_elem is None:
            published_elem = entry.find("updated")

        if published_elem is not None and published_elem.text:
            pub_date = self._parse_iso_date(published_elem.text)

        # Extract author
        author = None
        author_elem = entry.find("{http://www.w3.org/2005/Atom}author")
        if author_elem is None:
            author_elem = entry.find("author")
        if author_elem is not None:
            name_elem = author_elem.find("{http://www.w3.org/2005/Atom}name")
            if name_elem is None:
                name_elem = author_elem.find("name")
            author = name_elem.text if name_elem is not None else None

        # Extract ID as GUID
        id_elem = entry.find("{http://www.w3.org/2005/Atom}id")
        if id_elem is None:
            id_elem = entry.find("id")
        guid = id_elem.text if id_elem is not None else None

        return DiscoveredArticle(
            url=link,
            title=title,
            source_domain=self.site_config.domain,
            discovery_strategy=DiscoveryStrategy.RSS,
            published_date=pub_date,
            description=self._clean_html(description) if description else None,
            author=author,
            category=category,
            rss_guid=guid,
        )

    def _parse_rss_date(self, date_str: str) -> Optional[datetime]:
        """Parse RFC 2822 date format used in RSS.

        Args:
            date_str: Date string to parse

        Returns:
            datetime object or None if parsing fails
        """
        from email.utils import parsedate_to_datetime

        try:
            return parsedate_to_datetime(date_str)
        except (TypeError, ValueError):
            pass

        # Try common alternatives
        formats = [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d %b %Y %H:%M:%S %z",
            "%d %b %Y %H:%M:%S",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue

        logger.warning(f"Could not parse RSS date", date=date_str)
        return None

    def _parse_iso_date(self, date_str: str) -> Optional[datetime]:
        """Parse ISO 8601 date format used in Atom.

        Args:
            date_str: Date string to parse

        Returns:
            datetime object or None if parsing fails
        """
        try:
            # Handle timezone suffix
            if date_str.endswith("Z"):
                date_str = date_str[:-1] + "+00:00"
            return datetime.fromisoformat(date_str)
        except ValueError:
            pass

        # Try without timezone
        try:
            return datetime.fromisoformat(date_str.split("+")[0].split("-")[0])
        except ValueError:
            pass

        logger.warning(f"Could not parse ISO date", date=date_str)
        return None

    def _clean_html(self, text: str) -> str:
        """Remove HTML tags from text.

        Args:
            text: Text that may contain HTML

        Returns:
            Clean text
        """
        import re

        # Remove HTML tags
        clean = re.sub(r"<[^>]+>", "", text)

        # Decode common entities
        clean = clean.replace("&nbsp;", " ")
        clean = clean.replace("&amp;", "&")
        clean = clean.replace("&lt;", "<")
        clean = clean.replace("&gt;", ">")
        clean = clean.replace("&quot;", '"')
        clean = clean.replace("&#39;", "'")

        # Normalize whitespace
        clean = re.sub(r"\s+", " ", clean)

        return clean.strip()
