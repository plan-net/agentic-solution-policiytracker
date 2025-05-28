"""
Apify news collector for political monitoring.
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import structlog
from apify_client import ApifyClient

logger = structlog.get_logger()


class ApifyNewsCollector:
    """Collects news articles using Apify's news scraper actor."""
    
    ACTOR_ID = "eWUEW5YpCaCBAa0Zs"
    DEFAULT_LANGUAGE = "US:en"
    DEFAULT_MAX_ITEMS = 100
    
    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or os.getenv("APIFY_API_TOKEN")
        if not self.api_token:
            raise ValueError("APIFY_API_TOKEN not provided or found in environment")
        
        self.client = ApifyClient(self.api_token)
        logger.info("Initialized ApifyNewsCollector")
    
    async def collect_news(self, 
                          query: str,
                          max_items: int = DEFAULT_MAX_ITEMS,
                          days_back: int = 1,
                          language: str = DEFAULT_LANGUAGE) -> List[Dict[str, Any]]:
        """
        Collect news articles from Apify.
        
        Args:
            query: Search query (e.g., company name)
            max_items: Maximum number of items to collect
            days_back: How many days back to search
            language: Language/locale for search
            
        Returns:
            List of news articles with metadata
        """
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            logger.info(f"Collecting news for query: '{query}', days_back: {days_back}, max_items: {max_items}")
            
            # Prepare the Actor input
            run_input = {
                "query": query,
                "topics": [],
                "topicsHashed": [],
                "language": language,
                "maxItems": max_items,
                "fetchArticleDetails": True,
                "proxyConfiguration": {"useApifyProxy": True},
                # Could add date filtering if the actor supports it
            }
            
            # Run the Actor and wait for it to finish
            run = self.client.actor(self.ACTOR_ID).call(run_input=run_input)
            
            # Fetch results from the run's dataset
            articles = []
            for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                # Filter by date if needed (if actor doesn't support date filtering)
                article_date = self._parse_date(item.get("publishedAt", item.get("date")))
                if article_date and article_date >= start_date:
                    articles.append(self._normalize_article(item))
            
            logger.info(f"Collected {len(articles)} articles for query: '{query}'")
            return articles
            
        except Exception as e:
            logger.error(f"Failed to collect news for query '{query}': {e}")
            raise
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse various date formats from news articles."""
        if not date_str:
            return None
        
        # Try common date formats
        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def _normalize_article(self, raw_article: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize article data from Apify to our standard format."""
        # Handle both the actual Apify response format and any fallbacks
        return {
            # Core fields - using actual Apify field names
            "title": raw_article.get("title", "Untitled"),
            "url": raw_article.get("link", raw_article.get("url", "")),  # Apify uses 'link'
            "content": raw_article.get("text", raw_article.get("content", "")),  # May be empty if fetchArticleDetails=false
            
            # Temporal fields (important for Graphiti)
            "published_date": raw_article.get("publishedAt", raw_article.get("date")),
            "collected_date": datetime.now().isoformat(),
            
            # Source information - Apify 'source' is a string, not object
            "source": raw_article.get("source", "Unknown"),
            "source_url": raw_article.get("sourceUrl", ""),
            "author": raw_article.get("author", ""),
            
            # Additional metadata
            "description": raw_article.get("description", ""),
            "image_url": raw_article.get("image", ""),
            "language": raw_article.get("language", self.DEFAULT_LANGUAGE),
            "topics": raw_article.get("topics", []),
            
            # Apify specific
            "apify_id": raw_article.get("guid", raw_article.get("id", "")),  # Use guid as unique ID
            "apify_run_id": raw_article.get("runId", ""),
            "loaded_url": raw_article.get("loadedUrl", ""),  # Actual loaded URL
            "rss_link": raw_article.get("rssLink", ""),
            
            # Raw data for reference (add collector type)
            "_raw": {**raw_article, "collector_type": "apify"}
        }
    
    async def deduplicate_articles(self, 
                                  articles: List[Dict[str, Any]], 
                                  existing_urls: List[str]) -> List[Dict[str, Any]]:
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