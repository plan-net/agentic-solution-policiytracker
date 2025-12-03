"""
Website Discovery Module

Provides multi-strategy website content discovery for collecting
blogs, articles, news, and press releases from German government
and political websites.
"""

from .base import BaseDiscoveryStrategy
from .models import (
    DiscoveredArticle,
    DiscoveryResult,
    DiscoveryStrategy,
    FilterDecision,
    FilterResult,
    SiteConfig,
    StrategyAvailability,
)
from .orchestrator import (
    StrategyOrchestrator,
    create_orchestrator_from_yaml,
    discover_site,
)
from .rate_limiter import RateLimiter, RateLimiterConfig, RateLimitedSession
from .rss_strategy import RSSDiscoveryStrategy
from .section_strategy import SectionDiscoveryStrategy
from .sitemap_strategy import SitemapDiscoveryStrategy

__all__ = [
    # Base classes
    "BaseDiscoveryStrategy",
    # Strategies
    "RSSDiscoveryStrategy",
    "SectionDiscoveryStrategy",
    "SitemapDiscoveryStrategy",
    # Orchestrator
    "StrategyOrchestrator",
    "create_orchestrator_from_yaml",
    "discover_site",
    # Models
    "DiscoveredArticle",
    "DiscoveryResult",
    "DiscoveryStrategy",
    "FilterDecision",
    "FilterResult",
    "SiteConfig",
    "StrategyAvailability",
    # Rate limiting
    "RateLimiter",
    "RateLimiterConfig",
    "RateLimitedSession",
]
