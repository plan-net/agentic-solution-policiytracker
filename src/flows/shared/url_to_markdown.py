"""
URL to Markdown Converter

Fetches URL content and converts to markdown format using the same
transformer used by ETL pipelines.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import aiohttp
import structlog

logger = structlog.get_logger()


class URLToMarkdownConverter:
    """Convert URLs to markdown format for processing."""

    def __init__(self, output_dir: str = "data/input/documents_md"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized URLToMarkdownConverter with output: {self.output_dir}")

    async def fetch_and_convert(self, url: str) -> Optional[Path]:
        """
        Fetch URL content and convert to markdown.

        Args:
            url: URL to fetch and convert

        Returns:
            Path to saved markdown file, or None if failed
        """
        try:
            # Fetch URL content
            article_data = await self._fetch_url(url)

            if not article_data:
                logger.error(f"Failed to fetch URL: {url}")
                return None

            # Convert to markdown using ETL transformer
            from src.etl.transformers.markdown_transformer import MarkdownTransformer

            transformer = MarkdownTransformer()
            markdown_content, filename = transformer.transform_article(article_data)

            # Save to output directory
            output_path = self.output_dir / filename

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            logger.info(f"Saved markdown from URL to: {output_path}")

            return output_path

        except Exception as e:
            logger.error(f"URL conversion failed for {url}: {e}", exc_info=True)
            return None

    async def _fetch_url(self, url: str) -> Optional[dict[str, Any]]:
        """
        Fetch URL content and extract article data.

        Args:
            url: URL to fetch

        Returns:
            Normalized article data dict, or None if failed
        """
        try:
            import ssl

            import certifi

            # Create SSL context with proper certificate verification
            ssl_context = ssl.create_default_context(cafile=certifi.where())

            timeout = aiohttp.ClientTimeout(total=30)
            connector = aiohttp.TCPConnector(ssl=ssl_context)

            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                async with session.get(url, headers=self._get_headers()) as response:
                    if response.status != 200:
                        logger.error(f"HTTP {response.status} for URL: {url}")
                        return None

                    html_content = await response.text()
                    content_type = response.headers.get("Content-Type", "")

                    # Check if actually HTML
                    if "text/html" not in content_type:
                        logger.warning(f"Non-HTML content type: {content_type} for {url}")

                    # Extract article data from HTML
                    article_data = await self._extract_article_data(url, html_content)

                    return article_data

        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return None

    async def _extract_article_data(self, url: str, html_content: str) -> dict[str, Any]:
        """
        Extract article data from HTML content.

        Args:
            url: Source URL
            html_content: HTML content

        Returns:
            Normalized article data
        """
        try:
            from bs4 import BeautifulSoup
            from readability import Document
        except ImportError:
            raise ImportError(
                "beautifulsoup4 and readability-lxml are required. "
                "Install: pip install beautifulsoup4 readability-lxml"
            )

        soup = BeautifulSoup(html_content, "html.parser")

        # Extract metadata
        title = self._extract_title(soup)
        author = self._extract_author(soup)
        published_date = self._extract_published_date(soup)
        description = self._extract_description(soup)

        # Use readability to extract main content
        doc = Document(html_content)
        content_html = doc.summary()
        content_soup = BeautifulSoup(content_html, "html.parser")
        content_text = content_soup.get_text(separator="\n\n", strip=True)

        # Extract source domain
        source = urlparse(url).netloc.replace("www.", "")

        # Build normalized article data (compatible with ETL transformer)
        article_data = {
            "title": title or "Untitled",
            "url": url,
            "source": source,
            "source_url": url,
            "author": author,
            "published_date": published_date or datetime.now().isoformat(),
            "collected_date": datetime.now().isoformat(),
            "description": description or "",
            "content": content_text,
            "language": "en",  # Could enhance with language detection
            "topics": [],
            "collection_type": "adhoc_url",
        }

        return article_data

    def _extract_title(self, soup) -> Optional[str]:
        """Extract article title from HTML."""
        # Try Open Graph
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"]

        # Try Twitter Card
        twitter_title = soup.find("meta", attrs={"name": "twitter:title"})
        if twitter_title and twitter_title.get("content"):
            return twitter_title["content"]

        # Try standard title tag
        if soup.title and soup.title.string:
            return soup.title.string.strip()

        # Try h1
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)

        return None

    def _extract_author(self, soup) -> Optional[str]:
        """Extract author from HTML."""
        # Try meta author tag
        author_meta = soup.find("meta", attrs={"name": "author"})
        if author_meta and author_meta.get("content"):
            return author_meta["content"]

        # Try Open Graph
        og_author = soup.find("meta", property="article:author")
        if og_author and og_author.get("content"):
            return og_author["content"]

        return None

    def _extract_published_date(self, soup) -> Optional[str]:
        """Extract published date from HTML."""
        # Try meta date tags
        date_patterns = [
            {"property": "article:published_time"},
            {"name": "publishdate"},
            {"name": "pub_date"},
            {"name": "date"},
        ]

        for pattern in date_patterns:
            meta_tag = soup.find("meta", attrs=pattern)
            if meta_tag and meta_tag.get("content"):
                return meta_tag["content"]

        # Try time tags
        time_tag = soup.find("time")
        if time_tag and time_tag.get("datetime"):
            return time_tag["datetime"]

        return None

    def _extract_description(self, soup) -> Optional[str]:
        """Extract description from HTML."""
        # Try Open Graph
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            return og_desc["content"]

        # Try meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            return meta_desc["content"]

        return None

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for requests."""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
