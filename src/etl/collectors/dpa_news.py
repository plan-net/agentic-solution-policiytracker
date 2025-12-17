"""
DPA News collector for political monitoring.
Collects news articles from dpa-IQ-Retriever API.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Optional
from urllib.parse import quote

import aiohttp
import structlog

logger = structlog.get_logger()


class DPANewsCollector:
    """Collects news articles from dpa-IQ-Retriever API."""

    API_BASE_URL = "https://article-retriever.iq.dpa-ai-hub.de"
    DPA_NEWS_HUB_URL = "https://www.dpa-news-hub.de/archiv/detail"
    DEFAULT_MAX_ITEMS = 50  # Default with batching support
    MAX_ITEMS_PER_REQUEST = 20  # API tends to timeout with larger requests, so we batch

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DPA_API_KEY")
        if not self.api_key:
            raise ValueError("DPA_API_KEY not provided or found in environment")

        self.headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}

        logger.info("Initialized DPANewsCollector")

    async def collect_news(
        self,
        query: str,
        max_items: int = DEFAULT_MAX_ITEMS,
        days_back: int = 1,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """
        Collect news articles from DPA API with batching support.

        Args:
            query: Search query (e.g., company name)
            max_items: Maximum number of items to collect (supports batching for >20 items)
            days_back: How many days back to search

        Returns:
            List of news articles with metadata
        """
        import asyncio

        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            # Format dates for DPA API (ISO format)
            from_datetime = start_date.strftime("%Y-%m-%dT%H:%M:%S")
            to_datetime = end_date.strftime("%Y-%m-%dT%H:%M:%S")

            # Calculate number of batches needed
            num_batches = (max_items + self.MAX_ITEMS_PER_REQUEST - 1) // self.MAX_ITEMS_PER_REQUEST

            logger.info(
                f"Collecting news for query: '{query}', days_back: {days_back}, "
                f"max_items: {max_items} ({num_batches} batch(es) of up to {self.MAX_ITEMS_PER_REQUEST} items)"
            )

            all_articles = []
            seen_urns = set()  # Track seen URNs to avoid duplicates across batches

            # Make HTTP requests with longer timeout (DPA API can be slow)
            timeout = aiohttp.ClientTimeout(total=120)  # 2 minutes per request
            async with aiohttp.ClientSession(timeout=timeout) as session:
                for batch_num in range(num_batches):
                    # Calculate how many items we still need
                    remaining = max_items - len(all_articles)
                    if remaining <= 0:
                        break

                    batch_limit = min(remaining, self.MAX_ITEMS_PER_REQUEST)

                    # For subsequent batches, adjust date range to get older articles
                    # by using the oldest article's date from the previous batch
                    batch_to_datetime = to_datetime
                    if batch_num > 0 and all_articles:
                        # Find the oldest published_date from collected articles
                        oldest_date = None
                        for article in all_articles:
                            if article.get("published_date"):
                                try:
                                    article_dt = datetime.fromisoformat(
                                        article["published_date"].replace("Z", "+00:00")
                                    )
                                    # Remove timezone for comparison
                                    if article_dt.tzinfo:
                                        article_dt = article_dt.replace(tzinfo=None)
                                    if oldest_date is None or article_dt < oldest_date:
                                        oldest_date = article_dt
                                except (ValueError, TypeError):
                                    continue

                        if oldest_date:
                            # Subtract 1 second to avoid getting the same article
                            batch_to_datetime = (oldest_date - timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%S")
                            logger.debug(f"Batch {batch_num + 1}: searching before {batch_to_datetime}")

                    # Prepare request payload
                    payload = {
                        "query": query,
                        "limit": batch_limit,
                        "from_datetime": from_datetime,
                        "to_datetime": batch_to_datetime,
                        "response_format": "article_objects_markdown",
                    }

                    logger.info(f"Batch {batch_num + 1}/{num_batches}: requesting {batch_limit} items")

                    async with session.post(
                        f"{self.API_BASE_URL}/articles/relevant",
                        headers=self.headers,
                        json=payload,
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"DPA API error {response.status}: {error_text}")
                            raise Exception(f"DPA API error {response.status}: {error_text}")

                        result = await response.json()

                    # Convert DPA results to our standard format
                    context_items = result.get("context", [])

                    # Handle case where context might be a string (markdown format) instead of list
                    if isinstance(context_items, str):
                        logger.warning(
                            "DPA API returned markdown string instead of article objects. "
                            "Ensure response_format is set to 'article_objects_markdown'."
                        )
                        break

                    if not context_items:
                        logger.info(f"Batch {batch_num + 1}: no more articles available")
                        break

                    batch_articles = []
                    for item in context_items:
                        # Skip duplicates based on URN
                        urn = item.get("urn", "")
                        if urn in seen_urns:
                            continue
                        seen_urns.add(urn)

                        article = self._normalize_article(item)
                        # Additional date filtering
                        if article.get("published_date"):
                            try:
                                article_date = datetime.fromisoformat(
                                    article["published_date"].replace("Z", "+00:00")
                                )
                                # Make start_date timezone-aware for comparison
                                if article_date.tzinfo is not None:
                                    start_date_aware = start_date.replace(
                                        tzinfo=article_date.tzinfo
                                    )
                                    if article_date >= start_date_aware:
                                        batch_articles.append(article)
                                else:
                                    if article_date >= start_date:
                                        batch_articles.append(article)
                            except (ValueError, TypeError):
                                # If date parsing fails, include the article anyway
                                batch_articles.append(article)
                        else:
                            # No date available, include the article
                            batch_articles.append(article)

                    all_articles.extend(batch_articles)
                    logger.info(
                        f"Batch {batch_num + 1}: collected {len(batch_articles)} articles "
                        f"(total: {len(all_articles)})"
                    )

                    # If we got fewer articles than requested, no more available
                    if len(context_items) < batch_limit:
                        logger.info(f"Batch {batch_num + 1}: received fewer items than requested, stopping")
                        break

                    # Add delay between batches to avoid rate limiting
                    if batch_num < num_batches - 1 and len(all_articles) < max_items:
                        await asyncio.sleep(2)  # 2 second delay between batches

            logger.info(f"Collected {len(all_articles)} total articles for query: '{query}'")
            return all_articles

        except Exception as e:
            logger.error(f"Failed to collect news for query '{query}': {e}")
            raise

    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """Parse and validate date formats from DPA articles."""
        if not date_str:
            return None

        # Try common date formats
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%fZ",
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

    def _construct_url_from_urn(self, urn: str) -> str:
        """Construct article URL from URN."""
        if not urn:
            return ""
        # URL encode the URN for safe URL construction
        return f"{self.DPA_NEWS_HUB_URL}/{quote(urn, safe=':')}"

    def _extract_language_from_tags(self, tags: list[str]) -> str:
        """Extract language code from DPA tags."""
        for tag in tags:
            if tag.startswith("dnllang:"):
                lang_code = tag.replace("dnllang:", "")
                return lang_code
        return "de"  # Default to German for DPA

    def _extract_description(self, content: str, max_length: int = 300) -> str:
        """Extract a description from the full content."""
        if not content:
            return ""

        # Take first paragraph or first max_length characters
        paragraphs = content.split("\n\n")
        first_para = paragraphs[0] if paragraphs else content

        # Remove markdown headers
        if first_para.startswith("#"):
            lines = first_para.split("\n")
            first_para = " ".join(line for line in lines if not line.startswith("#"))

        if len(first_para) <= max_length:
            return first_para.strip()

        # Truncate at word boundary
        truncated = first_para[:max_length]
        last_space = truncated.rfind(" ")
        if last_space > max_length * 0.8:  # Only truncate if we don't lose too much
            truncated = truncated[:last_space]

        return truncated.strip() + "..."

    def _normalize_article(self, dpa_article: dict[str, Any]) -> dict[str, Any]:
        """Normalize article data from DPA API to our standard format."""
        # Extract URN and construct URL
        urn = dpa_article.get("urn", "")
        url = self._construct_url_from_urn(urn)

        # Extract and validate published date
        published_date = self._parse_date(dpa_article.get("version_created_at_utc"))

        # Extract content - prefer markdown
        content = dpa_article.get("article_complete_markdown", "")

        # Extract title
        title = dpa_article.get("headline", "Untitled")

        # Extract tags
        tags = dpa_article.get("tags", [])

        # Extract language from tags
        language = self._extract_language_from_tags(tags)

        # Extract source from URN (dpa.com)
        source = "DPA"
        source_url = "https://www.dpa.com"

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
            "author": "",  # DPA doesn't provide author in response
            # Additional metadata
            "description": self._extract_description(content),
            "image_url": "",  # DPA doesn't provide images in this API
            "language": language,
            "topics": tags,
            # DPA specific
            "dpa_id": urn,
            "dpa_score": dpa_article.get("score", 0),
            "dpa_rerank_score": dpa_article.get("rerank_score"),
            # Raw data for reference
            "_raw": {**dpa_article, "collector_type": "dpa"},
        }

    async def deduplicate_articles(
        self, articles: list[dict[str, Any]], existing_urls: list[str]
    ) -> list[dict[str, Any]]:
        """Remove articles that have already been collected based on URL."""
        existing_set = set(existing_urls)
        deduplicated = []

        for article in articles:
            if article["url"] and article["url"] not in existing_set:
                deduplicated.append(article)
            else:
                logger.debug(f"Skipping duplicate article: {article['url']}")

        logger.info(
            f"Deduplicated {len(articles)} articles to {len(deduplicated)} unique articles"
        )
        return deduplicated

    def get_collector_name(self) -> str:
        """Get the name of this collector for identification."""
        return "dpa"
