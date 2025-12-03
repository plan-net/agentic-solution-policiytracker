"""
Data models for website discovery pipeline.

Defines core data structures for discovered articles, discovery results,
and strategy metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class DiscoveryStrategy(Enum):
    """Enumeration of available discovery strategies."""

    RSS = "rss"
    SECTION = "section"
    SITEMAP = "sitemap"


class FilterDecision(Enum):
    """Possible outcomes of relevance filtering."""

    RELEVANT = "relevant"
    NOT_RELEVANT = "not_relevant"
    UNCERTAIN = "uncertain"


@dataclass
class DiscoveredArticle:
    """Represents an article discovered from a website.

    Contains metadata extracted during discovery (before full content fetch).
    """

    # Core identifiers
    url: str
    title: str

    # Discovery metadata
    source_domain: str
    discovery_strategy: DiscoveryStrategy
    discovered_at: datetime = field(default_factory=datetime.now)

    # Optional metadata (may be available from RSS/sitemap)
    published_date: Optional[datetime] = None
    description: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None

    # Strategy-specific metadata
    rss_guid: Optional[str] = None
    sitemap_priority: Optional[float] = None
    sitemap_changefreq: Optional[str] = None
    section_path: Optional[str] = None

    # Processing state
    content_fetched: bool = False
    full_content: Optional[str] = None
    relevance_score: Optional[float] = None
    filter_decision: Optional[FilterDecision] = None

    def __hash__(self) -> int:
        """URL-based hashing for deduplication."""
        return hash(self.url)

    def __eq__(self, other: object) -> bool:
        """URL-based equality for deduplication."""
        if not isinstance(other, DiscoveredArticle):
            return False
        return self.url == other.url

    def to_article_dict(self) -> dict[str, Any]:
        """Convert to article dict format compatible with MarkdownTransformer."""
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source_domain,
            "source_url": f"https://{self.source_domain}",
            "published_date": self.published_date.isoformat() if self.published_date else None,
            "collected_date": datetime.now().isoformat(),
            "description": self.description or "",
            "content": self.full_content or "",
            "author": self.author or "",
            "language": "de",  # German government sites
            "topics": [],
            "collection_type": "website_discovery",
            "discovery_method": self.discovery_strategy.value,
        }


@dataclass
class StrategyAvailability:
    """Result of checking if a discovery strategy is available for a site."""

    available: bool
    reason: Optional[str] = None
    checked_at: datetime = field(default_factory=datetime.now)

    # Strategy-specific availability info
    feed_count: Optional[int] = None  # For RSS
    section_count: Optional[int] = None  # For section
    sitemap_url_count: Optional[int] = None  # For sitemap


@dataclass
class DiscoveryResult:
    """Result of running a discovery strategy."""

    # Success/failure status
    success: bool
    strategy: DiscoveryStrategy

    # Discovered articles
    articles: list[DiscoveredArticle] = field(default_factory=list)

    # Timing
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    # Statistics
    urls_discovered: int = 0
    urls_filtered: int = 0
    urls_deduplicated: int = 0

    # Errors and warnings
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # Strategy-specific metadata
    feeds_processed: Optional[int] = None  # For RSS
    pages_crawled: Optional[int] = None  # For section
    sitemaps_processed: Optional[int] = None  # For sitemap

    def mark_completed(self) -> None:
        """Mark the discovery as completed and calculate duration."""
        self.completed_at = datetime.now()
        self.duration_seconds = (self.completed_at - self.started_at).total_seconds()


@dataclass
class FilterResult:
    """Result of relevance filtering for an article."""

    decision: FilterDecision
    stage: str  # "keyword" or "llm"

    # Scoring details
    keyword_score: Optional[float] = None
    llm_score: Optional[float] = None
    final_score: Optional[float] = None

    # Score breakdown by dimension
    score_breakdown: Optional[dict[str, float]] = None

    # Explanation (especially useful for LLM decisions)
    explanation: Optional[str] = None

    # Matched keywords/patterns
    matched_keywords: list[str] = field(default_factory=list)
    matched_patterns: list[str] = field(default_factory=list)


@dataclass
class SiteConfig:
    """Configuration for a single website to discover content from."""

    # Site identification
    site_key: str
    domain: str
    name: str
    language: str = "de"
    enabled: bool = True

    # Discovery strategies (ordered by priority)
    discovery_strategies: list[dict[str, Any]] = field(default_factory=list)

    def get_strategy_config(self, strategy_type: str) -> Optional[dict[str, Any]]:
        """Get configuration for a specific strategy type."""
        for strategy in self.discovery_strategies:
            if strategy.get("type") == strategy_type:
                return strategy.get("config", {})
        return None

    def get_strategy_priority(self, strategy_type: str) -> Optional[int]:
        """Get priority for a specific strategy type."""
        for strategy in self.discovery_strategies:
            if strategy.get("type") == strategy_type:
                return strategy.get("priority")
        return None


@dataclass
class DiscoveryState:
    """Persistent state for tracking processed URLs across runs."""

    # URL tracking
    processed_urls: dict[str, datetime] = field(default_factory=dict)  # url -> processed_at

    # Run tracking
    last_run: Optional[datetime] = None
    total_articles_discovered: int = 0
    total_articles_saved: int = 0

    # Per-site statistics
    site_statistics: dict[str, dict[str, Any]] = field(default_factory=dict)

    def mark_url_processed(self, url: str) -> None:
        """Mark a URL as processed."""
        self.processed_urls[url] = datetime.now()

    def is_url_processed(self, url: str) -> bool:
        """Check if a URL has been processed."""
        return url in self.processed_urls

    def cleanup_old_urls(self, days: int = 90) -> int:
        """Remove URLs older than specified days. Returns count removed."""
        cutoff = datetime.now()
        old_urls = [
            url
            for url, processed_at in self.processed_urls.items()
            if (cutoff - processed_at).days > days
        ]
        for url in old_urls:
            del self.processed_urls[url]
        return len(old_urls)
