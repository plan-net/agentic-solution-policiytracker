"""
Section-based Discovery Strategy.

Discovers content by crawling specific sections of a website
(e.g., /aktuelles, /news, /presse) and extracting article links.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin, urlparse

import structlog
from bs4 import BeautifulSoup

from .base import BaseDiscoveryStrategy
from .models import (
    DiscoveredArticle,
    DiscoveryResult,
    DiscoveryStrategy,
    SiteConfig,
    StrategyAvailability,
)

logger = structlog.get_logger()


class SectionDiscoveryStrategy(BaseDiscoveryStrategy):
    """Discovers content by crawling website sections.

    Priority 2 strategy - Section crawling when RSS is not available.
    Extracts article links from listing pages (news, press releases, etc.)
    """

    @property
    def strategy_name(self) -> DiscoveryStrategy:
        return DiscoveryStrategy.SECTION

    async def discover(self, limit: Optional[int] = None) -> DiscoveryResult:
        """Discover articles from configured sections.

        Args:
            limit: Maximum number of articles to discover

        Returns:
            DiscoveryResult with discovered articles
        """
        result = DiscoveryResult(
            success=False,
            strategy=DiscoveryStrategy.SECTION,
        )

        sections_config = self._strategy_config.get("sections", [])
        if not sections_config:
            result.errors.append("No sections configured")
            result.mark_completed()
            return result

        follow_pagination = self._strategy_config.get("follow_pagination", True)
        max_pages = self._strategy_config.get("max_pages", 10)

        all_articles: list[DiscoveredArticle] = []
        pages_crawled = 0

        for section_config in sections_config:
            section_path = section_config.get("path")
            section_name = section_config.get("name", section_path)
            section_depth = section_config.get("depth", 1)

            if not section_path:
                result.warnings.append(f"Section config missing path: {section_config}")
                continue

            try:
                articles, pages = await self._crawl_section(
                    section_path,
                    section_name,
                    section_depth,
                    follow_pagination,
                    max_pages,
                    limit - len(all_articles) if limit else None,
                )
                all_articles.extend(articles)
                pages_crawled += pages

                logger.info(
                    f"Crawled section",
                    path=section_path,
                    articles=len(articles),
                    pages=pages,
                )

                # Check limit
                if limit and len(all_articles) >= limit:
                    break

            except Exception as e:
                result.errors.append(f"Failed to crawl section {section_path}: {str(e)}")
                logger.error(f"Section crawl error", path=section_path, error=str(e))

        # Deduplicate by URL
        seen_urls = set()
        unique_articles = []
        for article in all_articles:
            if article.url not in seen_urls:
                seen_urls.add(article.url)
                unique_articles.append(article)

        # Apply limit if specified
        if limit and len(unique_articles) > limit:
            unique_articles = unique_articles[:limit]

        result.articles = unique_articles
        result.urls_discovered = len(unique_articles)
        result.urls_deduplicated = len(all_articles) - len(unique_articles)
        result.pages_crawled = pages_crawled
        result.success = len(unique_articles) > 0 or len(result.errors) == 0
        result.mark_completed()

        logger.info(
            f"Section discovery complete",
            site=self.site_config.domain,
            articles=len(unique_articles),
            pages=pages_crawled,
        )

        return result

    async def is_available(self) -> StrategyAvailability:
        """Check if section discovery is available for this site.

        Returns:
            StrategyAvailability indicating if sections are accessible
        """
        sections_config = self._strategy_config.get("sections", [])

        if not sections_config:
            return StrategyAvailability(
                available=False,
                reason="No sections configured",
            )

        # Check if at least one section is accessible
        accessible_sections = 0
        for section_config in sections_config:
            section_path = section_config.get("path")
            if section_path:
                section_url = self._normalize_url(section_path)
                if await self._check_url_exists(section_url):
                    accessible_sections += 1

        if accessible_sections == 0:
            return StrategyAvailability(
                available=False,
                reason=f"None of {len(sections_config)} configured sections are accessible",
            )

        return StrategyAvailability(
            available=True,
            reason=f"{accessible_sections}/{len(sections_config)} sections accessible",
            section_count=accessible_sections,
        )

    async def _crawl_section(
        self,
        section_path: str,
        section_name: str,
        depth: int,
        follow_pagination: bool,
        max_pages: int,
        limit: Optional[int],
    ) -> tuple[list[DiscoveredArticle], int]:
        """Crawl a section and extract article links.

        Args:
            section_path: Path to the section
            section_name: Human-readable section name
            depth: How deep to follow links
            follow_pagination: Whether to follow pagination
            max_pages: Maximum pages to crawl
            limit: Maximum articles to return

        Returns:
            Tuple of (articles, pages_crawled)
        """
        section_url = self._normalize_url(section_path)
        articles: list[DiscoveredArticle] = []
        pages_crawled = 0
        visited_urls = set()

        # Queue of URLs to visit with their depth
        to_visit = [(section_url, 0)]

        while to_visit and pages_crawled < max_pages:
            if limit and len(articles) >= limit:
                break

            current_url, current_depth = to_visit.pop(0)

            if current_url in visited_urls:
                continue
            visited_urls.add(current_url)

            # Fetch page content
            content = await self._fetch_url(current_url)
            if not content:
                continue

            pages_crawled += 1

            try:
                soup = BeautifulSoup(content, "html.parser")

                # Extract article links from this page
                page_articles = self._extract_article_links(
                    soup,
                    current_url,
                    section_name,
                )
                articles.extend(page_articles)

                # Find pagination links if enabled
                if follow_pagination and pages_crawled < max_pages:
                    next_pages = self._find_pagination_links(soup, current_url, visited_urls)
                    for next_url in next_pages:
                        to_visit.append((next_url, current_depth))

                # Find deeper links if depth allows
                if current_depth < depth - 1:
                    deeper_links = self._find_section_links(
                        soup,
                        current_url,
                        section_path,
                        visited_urls,
                    )
                    for deeper_url in deeper_links:
                        to_visit.append((deeper_url, current_depth + 1))

            except Exception as e:
                logger.warning(f"Error parsing section page", url=current_url, error=str(e))

        return articles, pages_crawled

    def _extract_article_links(
        self,
        soup: BeautifulSoup,
        page_url: str,
        section_name: str,
    ) -> list[DiscoveredArticle]:
        """Extract article links from a page.

        Args:
            soup: Parsed HTML
            page_url: URL of the page being parsed
            section_name: Section name for metadata

        Returns:
            List of discovered articles
        """
        articles = []

        # Common article container patterns for German government sites
        article_selectors = [
            "article",
            ".article",
            ".news-item",
            ".news-list-item",
            ".pressemitteilung",
            ".aktuelles-item",
            ".teaser",
            ".card",
            ".list-item",
            "[class*='news']",
            "[class*='article']",
            "[class*='beitrag']",
        ]

        # Find article containers
        article_elements = []
        for selector in article_selectors:
            try:
                found = soup.select(selector)
                article_elements.extend(found)
            except Exception:
                continue

        # Also look for links in common list structures
        list_selectors = [
            "ul.news-list a",
            "ul.article-list a",
            ".content-area a",
            "main a",
            "#content a",
        ]

        standalone_links = []
        for selector in list_selectors:
            try:
                found = soup.select(selector)
                standalone_links.extend(found)
            except Exception:
                continue

        # Process article containers
        seen_urls = set()
        for element in article_elements:
            article = self._extract_from_container(element, page_url, section_name)
            if article and article.url not in seen_urls:
                seen_urls.add(article.url)
                articles.append(article)

        # Process standalone links
        for link in standalone_links:
            href = link.get("href")
            if not href:
                continue

            url = self._normalize_url(href, page_url)

            if url in seen_urls:
                continue

            if not self._is_article_link(url, link):
                continue

            seen_urls.add(url)

            title = link.get_text(strip=True) or link.get("title", "Untitled")

            article = DiscoveredArticle(
                url=url,
                title=title[:200],  # Limit title length
                source_domain=self.site_config.domain,
                discovery_strategy=DiscoveryStrategy.SECTION,
                section_path=section_name,
            )
            articles.append(article)

        return articles

    def _extract_from_container(
        self,
        element,
        page_url: str,
        section_name: str,
    ) -> Optional[DiscoveredArticle]:
        """Extract article data from an article container element.

        Args:
            element: BeautifulSoup element
            page_url: URL of the page
            section_name: Section name for metadata

        Returns:
            DiscoveredArticle or None
        """
        # Find the main link
        link = element.find("a", href=True)
        if not link:
            return None

        href = link.get("href")
        if not href:
            return None

        url = self._normalize_url(href, page_url)

        if not self._is_article_link(url, link):
            return None

        # Extract title - check multiple sources
        title = None

        # Try heading elements
        for heading_tag in ["h1", "h2", "h3", "h4"]:
            heading = element.find(heading_tag)
            if heading:
                title = heading.get_text(strip=True)
                break

        # Fall back to link text or title attribute
        if not title:
            title = link.get_text(strip=True) or link.get("title", "")

        if not title:
            title = "Untitled"

        # Extract description
        description = None
        desc_selectors = [".description", ".summary", ".teaser-text", ".intro", "p"]
        for selector in desc_selectors:
            desc_elem = element.select_one(selector)
            if desc_elem and desc_elem.get_text(strip=True):
                description = desc_elem.get_text(strip=True)[:500]
                break

        # Extract date
        published_date = None
        date_selectors = [".date", ".datum", "time", ".published", "[datetime]"]
        for selector in date_selectors:
            date_elem = element.select_one(selector)
            if date_elem:
                # Try datetime attribute first
                datetime_attr = date_elem.get("datetime")
                if datetime_attr:
                    published_date = self._parse_date(datetime_attr)
                    break
                # Try text content
                date_text = date_elem.get_text(strip=True)
                if date_text:
                    published_date = self._parse_date(date_text)
                    if published_date:
                        break

        return DiscoveredArticle(
            url=url,
            title=title[:200],
            source_domain=self.site_config.domain,
            discovery_strategy=DiscoveryStrategy.SECTION,
            published_date=published_date,
            description=description,
            section_path=section_name,
        )

    def _is_article_link(self, url: str, link_element) -> bool:
        """Determine if a link is likely an article.

        Args:
            url: Normalized URL
            link_element: BeautifulSoup link element

        Returns:
            True if link appears to be an article
        """
        # Must be valid URL
        if not self._is_valid_article_url(url):
            return False

        # Must be on the same domain
        url_domain = self._extract_domain(url)
        site_domain = self.site_config.domain.replace("www.", "")
        if url_domain != site_domain:
            return False

        # Check URL patterns that suggest an article
        article_patterns = [
            r"/\d{4}/\d{2}/",  # Date in URL
            r"/news/",
            r"/aktuelles/",
            r"/presse/",
            r"/pressemitteilung",
            r"/beitrag/",
            r"/artikel/",
            r"/meldung/",
            r"/mitteilung/",
        ]

        url_lower = url.lower()
        for pattern in article_patterns:
            if re.search(pattern, url_lower):
                return True

        # Check link has meaningful text (not just "mehr" or icons)
        link_text = link_element.get_text(strip=True).lower()
        skip_texts = {"mehr", "more", "...", ">", "»", "lesen", "weiterlesen"}
        if link_text in skip_texts:
            return False

        # If has significant text, consider it an article
        if len(link_text) > 20:
            return True

        return False

    def _find_pagination_links(
        self,
        soup: BeautifulSoup,
        current_url: str,
        visited: set[str],
    ) -> list[str]:
        """Find pagination links on a page.

        Args:
            soup: Parsed HTML
            current_url: Current page URL
            visited: Set of already visited URLs

        Returns:
            List of pagination URLs
        """
        pagination_urls = []

        # Common pagination selectors
        pagination_selectors = [
            ".pagination a",
            ".pager a",
            "nav.pagination a",
            ".page-navigation a",
            "[class*='pagination'] a",
            "a.next",
            "a[rel='next']",
        ]

        for selector in pagination_selectors:
            try:
                links = soup.select(selector)
                for link in links:
                    href = link.get("href")
                    if href:
                        url = self._normalize_url(href, current_url)
                        if url not in visited and self._is_same_section(url, current_url):
                            pagination_urls.append(url)
            except Exception:
                continue

        return pagination_urls

    def _find_section_links(
        self,
        soup: BeautifulSoup,
        current_url: str,
        section_path: str,
        visited: set[str],
    ) -> list[str]:
        """Find deeper section links (subcategories).

        Args:
            soup: Parsed HTML
            current_url: Current page URL
            section_path: Original section path
            visited: Set of already visited URLs

        Returns:
            List of deeper section URLs
        """
        section_urls = []

        # Find subsection links
        for link in soup.find_all("a", href=True):
            href = link.get("href")
            url = self._normalize_url(href, current_url)

            if url in visited:
                continue

            # Must be within the same section
            if not self._is_same_section(url, current_url):
                continue

            # Must look like a listing page, not an article
            if self._is_valid_article_url(url):
                # Check if it's a category/listing page pattern
                if re.search(r"/kategorie/|/category/|/thema/|/rubrik/", url.lower()):
                    section_urls.append(url)

        return section_urls

    def _is_same_section(self, url: str, section_url: str) -> bool:
        """Check if URL is within the same section.

        Args:
            url: URL to check
            section_url: Section URL

        Returns:
            True if URL is within the section
        """
        parsed_url = urlparse(url)
        parsed_section = urlparse(section_url)

        # Must be same domain
        if parsed_url.netloc != parsed_section.netloc:
            return False

        # Path should be under section path
        section_path = parsed_section.path.rstrip("/")
        url_path = parsed_url.path.rstrip("/")

        return url_path.startswith(section_path)

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse a date string in various German formats.

        Args:
            date_str: Date string to parse

        Returns:
            datetime or None
        """
        # German date formats
        formats = [
            "%d.%m.%Y",
            "%d. %B %Y",
            "%d.%m.%Y %H:%M",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
            "%d. %b %Y",
        ]

        # German month names
        german_months = {
            "januar": "01",
            "februar": "02",
            "märz": "03",
            "april": "04",
            "mai": "05",
            "juni": "06",
            "juli": "07",
            "august": "08",
            "september": "09",
            "oktober": "10",
            "november": "11",
            "dezember": "12",
        }

        # Try ISO format first
        try:
            if "T" in date_str:
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            pass

        # Normalize German month names
        date_lower = date_str.lower()
        for german, num in german_months.items():
            if german in date_lower:
                date_str = re.sub(
                    german, num, date_str, flags=re.IGNORECASE
                )
                formats.append("%d. %m %Y")
                break

        # Try each format
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue

        return None
