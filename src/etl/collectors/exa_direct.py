"""
Direct HTTP Exa.ai news collector for political monitoring.
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp
import structlog

logger = structlog.get_logger()


class ExaDirectCollector:
    """Collects news articles using direct HTTP calls to Exa.ai API."""

    API_BASE_URL = "https://api.exa.ai"
    DEFAULT_MAX_ITEMS = 100
    DEFAULT_CATEGORY = "news"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("EXA_API_KEY")
        if not self.api_key:
            raise ValueError("EXA_API_KEY not provided or found in environment")

        self.headers = {"Content-Type": "application/json", "x-api-key": self.api_key}

        logger.info("Initialized ExaDirectCollector")

    async def collect_news(
        self,
        query: str,
        max_items: int = DEFAULT_MAX_ITEMS,
        days_back: int = 1,
        category: str = DEFAULT_CATEGORY,
    ) -> List[Dict[str, Any]]:
        """
        Collect news articles from Exa.ai using direct HTTP calls.

        Args:
            query: Search query (e.g., company name)
            max_items: Maximum number of items to collect
            days_back: How many days back to search
            category: Search category (default: "news")

        Returns:
            List of news articles with metadata
        """
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            start_published_date = start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")

            logger.info(
                f"Collecting news for query: '{query}', days_back: {days_back}, max_items: {max_items}"
            )

            # Prepare request payload
            payload = {
                "query": query,
                "category": category,
                "numResults": max_items,
                "startPublishedDate": start_published_date,
                "contents": {"text": True},
            }

            # Make HTTP request with timeout
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.API_BASE_URL}/search", headers=self.headers, json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Exa API error {response.status}: {error_text}")
                        raise Exception(f"Exa API error {response.status}: {error_text}")

                    result = await response.json()

            # Convert Exa results to our standard format
            articles = []
            for item in result.get("results", []):
                article = self._normalize_article(item)
                # Additional date filtering (Exa might return slightly outside range)
                if article.get("published_date"):
                    try:
                        article_date = datetime.fromisoformat(
                            article["published_date"].replace("Z", "+00:00")
                        )
                        if article_date >= start_date:
                            articles.append(article)
                    except (ValueError, TypeError):
                        # If date parsing fails, include the article anyway
                        articles.append(article)
                else:
                    # No date available, include the article
                    articles.append(article)

            logger.info(f"Collected {len(articles)} articles for query: '{query}'")
            return articles

        except Exception as e:
            logger.error(f"Failed to collect news for query '{query}': {e}")
            raise

    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """Parse and validate date formats from news articles."""
        if not date_str:
            return None

        # Try common date formats
        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]

        parsed_date = None
        for fmt in formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                break
            except (ValueError, TypeError):
                continue

        if not parsed_date:
            logger.warning(f"Could not parse date: {date_str}")
            return None

        # Validate date is not in the future
        now = datetime.now()
        if parsed_date > now:
            logger.warning(f"Date {date_str} is in the future, using current date instead")
            parsed_date = now

        # Validate date is not too old (e.g., before 1990)
        min_date = datetime(1990, 1, 1)
        if parsed_date < min_date:
            logger.warning(f"Date {date_str} is too old, using current date instead")
            parsed_date = now

        return parsed_date.isoformat()

    def _normalize_article(self, exa_result: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize article data from Exa.ai to our standard format."""
        # Extract and validate published date
        published_date = self._parse_date(exa_result.get("publishedDate"))

        # Extract content - Exa provides rich text content
        content = exa_result.get("text", "")

        # Extract title
        title = exa_result.get("title", "Untitled")

        # Extract source information from URL
        source = "Unknown"
        source_url = ""
        url = exa_result.get("url", "")

        if url:
            try:
                from urllib.parse import urlparse

                parsed = urlparse(url)
                # Clean up domain for source name
                domain = parsed.netloc.replace("www.", "")
                source_parts = domain.split(".")
                if len(source_parts) >= 2:
                    source = source_parts[0].replace("-", " ").title()
                source_url = f"{parsed.scheme}://{parsed.netloc}"
            except:
                pass

        return {
            # Core fields
            "title": title,
            "url": url,
            "content": content,
            # Temporal fields (important for Graphiti)
            "published_date": published_date,
            "collected_date": datetime.now().isoformat(),
            # Source information
            "source": source,
            "source_url": source_url,
            "author": exa_result.get("author", ""),
            # Additional metadata
            "description": self._extract_description(content),
            "image_url": exa_result.get("image", ""),
            "language": "en",  # Assume English for now
            "topics": [],  # Could extract from content later
            # Exa specific
            "exa_id": exa_result.get("id", ""),
            "exa_score": exa_result.get("score", 0),
            # Raw data for reference
            "_raw": {**exa_result, "collector_type": "exa_direct"},
        }

    def _extract_description(self, content: str, max_length: int = 300) -> str:
        """Extract a description from the full content."""
        if not content:
            return ""

        # Take first paragraph or first max_length characters
        paragraphs = content.split("\n\n")
        first_para = paragraphs[0] if paragraphs else content

        if len(first_para) <= max_length:
            return first_para.strip()

        # Truncate at word boundary
        truncated = first_para[:max_length]
        last_space = truncated.rfind(" ")
        if last_space > max_length * 0.8:  # Only truncate if we don't lose too much
            truncated = truncated[:last_space]

        return truncated.strip() + "..."

    async def deduplicate_articles(
        self, articles: List[Dict[str, Any]], existing_urls: List[str]
    ) -> List[Dict[str, Any]]:
        """Remove articles that have already been collected based on URL."""
        existing_set = set(existing_urls)
        deduplicated = []

        for article in articles:
            if article["url"] and article["url"] not in existing_set:
                deduplicated.append(article)
            else:
                logger.debug(f"Skipping duplicate article: {article['url']}")

        logger.info(f"Deduplicated {len(articles)} articles to {len(deduplicated)} unique articles")
        return deduplicated

    def get_collector_name(self) -> str:
        """Get the name of this collector for identification."""
        return "exa_direct"
