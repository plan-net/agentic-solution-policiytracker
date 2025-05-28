"""
Exa.ai news collector for political monitoring.
"""

import asyncio
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import structlog
from exa_py import Exa

logger = structlog.get_logger()


class ExaNewsCollector:
    """Collects news articles using Exa.ai's search API."""
    
    DEFAULT_MAX_ITEMS = 100
    DEFAULT_CATEGORY = "news"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("EXA_API_KEY")
        if not self.api_key:
            raise ValueError("EXA_API_KEY not provided or found in environment")
        
        self.client = Exa(api_key=self.api_key)
        logger.info("Initialized ExaNewsCollector")
    
    async def collect_news(self, 
                          query: str,
                          max_items: int = DEFAULT_MAX_ITEMS,
                          days_back: int = 1,
                          category: str = DEFAULT_CATEGORY) -> List[Dict[str, Any]]:
        """
        Collect news articles from Exa.ai.
        
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
            
            logger.info(f"Collecting news for query: '{query}', days_back: {days_back}, max_items: {max_items}")
            
            # Search with Exa.ai - run in thread pool to avoid blocking
            import concurrent.futures
            import functools
            
            def search_exa():
                return self.client.search_and_contents(
                    query=query,
                    text=True,  # Get full text content
                    category=category,
                    num_results=max_items,
                    start_published_date=start_published_date
                )
            
            # Run with timeout
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = loop.run_in_executor(executor, search_exa)
                try:
                    result = await asyncio.wait_for(future, timeout=30.0)  # 30 second timeout
                except asyncio.TimeoutError:
                    logger.error("Exa API request timed out after 30 seconds")
                    raise TimeoutError("Exa API request timed out")
            
            # Convert Exa results to our standard format
            articles = []
            for item in result.results:
                article = self._normalize_article(item)
                # Additional date filtering (Exa might return slightly outside range)
                article_date = self._parse_date(article.get("published_date"))
                if article_date and article_date >= start_date:
                    articles.append(article)
            
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
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except (ValueError, TypeError):
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def _normalize_article(self, exa_result) -> Dict[str, Any]:
        """Normalize article data from Exa.ai to our standard format."""
        # Extract published date from Exa result
        published_date = None
        if hasattr(exa_result, 'published_date') and exa_result.published_date:
            published_date = exa_result.published_date
        
        # Extract content - Exa provides rich text content
        content = ""
        if hasattr(exa_result, 'text') and exa_result.text:
            content = exa_result.text
        
        # Extract title - use title or fallback to URL
        title = "Untitled"
        if hasattr(exa_result, 'title') and exa_result.title:
            title = exa_result.title
        elif hasattr(exa_result, 'url') and exa_result.url:
            # Extract domain as fallback title
            try:
                from urllib.parse import urlparse
                domain = urlparse(exa_result.url).netloc
                title = f"Article from {domain}"
            except:
                title = "Untitled"
        
        # Extract source information from URL
        source = "Unknown"
        source_url = ""
        if hasattr(exa_result, 'url') and exa_result.url:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(exa_result.url)
                source = parsed.netloc.replace('www.', '').replace('.com', '').replace('.', ' ').title()
                source_url = f"{parsed.scheme}://{parsed.netloc}"
            except:
                pass
        
        return {
            # Core fields
            "title": title,
            "url": getattr(exa_result, 'url', ''),
            "content": content,
            
            # Temporal fields (important for Graphiti)
            "published_date": published_date,
            "collected_date": datetime.now().isoformat(),
            
            # Source information
            "source": source,
            "source_url": source_url,
            "author": getattr(exa_result, 'author', ''),
            
            # Additional metadata
            "description": self._extract_description(content),
            "image_url": "",  # Exa doesn't provide images
            "language": "en",  # Assume English for now
            "topics": [],  # Could extract from content later
            
            # Exa specific
            "exa_id": getattr(exa_result, 'id', ''),
            "exa_score": getattr(exa_result, 'score', 0),
            
            # Raw data for reference
            "_raw": {
                'id': getattr(exa_result, 'id', ''),
                'url': getattr(exa_result, 'url', ''),
                'title': getattr(exa_result, 'title', ''),
                'score': getattr(exa_result, 'score', 0),
                'published_date': published_date,
                'author': getattr(exa_result, 'author', ''),
                'text': content[:500] + '...' if len(content) > 500 else content,  # Truncated for storage
                'collector_type': 'exa'
            }
        }
    
    def _extract_description(self, content: str, max_length: int = 300) -> str:
        """Extract a description from the full content."""
        if not content:
            return ""
        
        # Take first paragraph or first max_length characters
        paragraphs = content.split('\n\n')
        first_para = paragraphs[0] if paragraphs else content
        
        if len(first_para) <= max_length:
            return first_para.strip()
        
        # Truncate at word boundary
        truncated = first_para[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.8:  # Only truncate if we don't lose too much
            truncated = truncated[:last_space]
        
        return truncated.strip() + "..."
    
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
    
    def get_collector_name(self) -> str:
        """Get the name of this collector for identification."""
        return "exa"