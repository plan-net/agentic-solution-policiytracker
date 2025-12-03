"""
Strategy Orchestrator for website discovery.

Orchestrates multiple discovery strategies with fallback logic:
RSS (priority 1) → Section (priority 2) → Sitemap (priority 3)
"""

from __future__ import annotations

from typing import Optional

import aiohttp
import structlog

from .base import BaseDiscoveryStrategy
from .models import DiscoveredArticle, DiscoveryResult, DiscoveryStrategy, SiteConfig
from .rate_limiter import RateLimiter, RateLimiterConfig
from .rss_strategy import RSSDiscoveryStrategy
from .section_strategy import SectionDiscoveryStrategy
from .sitemap_strategy import SitemapDiscoveryStrategy

logger = structlog.get_logger()


class StrategyOrchestrator:
    """Orchestrates discovery strategies with fallback.

    Tries strategies in priority order (RSS → Section → Sitemap)
    and falls back to the next strategy if the current one fails
    or returns insufficient results.
    """

    def __init__(
        self,
        site_config: SiteConfig,
        rate_limiter: Optional[RateLimiter] = None,
        http_session: Optional[aiohttp.ClientSession] = None,
        min_results: int = 5,
        user_agent: str = "PolicyTracker/1.0 (Political Monitoring Research)",
    ):
        """Initialize the orchestrator.

        Args:
            site_config: Configuration for the target website
            rate_limiter: Optional shared rate limiter
            http_session: Optional shared HTTP session
            min_results: Minimum results before trying next strategy
            user_agent: User-Agent header for requests
        """
        self.site_config = site_config
        self.rate_limiter = rate_limiter or RateLimiter()
        self._session = http_session
        self._owns_session = http_session is None
        self.min_results = min_results
        self.user_agent = user_agent

        # Initialize strategies
        self._strategies: list[BaseDiscoveryStrategy] = []
        self._init_strategies()

        logger.info(
            f"Initialized StrategyOrchestrator",
            site=site_config.domain,
            strategies=[s.strategy_name.value for s in self._strategies],
        )

    def _init_strategies(self) -> None:
        """Initialize configured discovery strategies."""
        strategy_classes = {
            "rss": RSSDiscoveryStrategy,
            "section": SectionDiscoveryStrategy,
            "sitemap": SitemapDiscoveryStrategy,
        }

        for strategy_def in self.site_config.discovery_strategies:
            strategy_type = strategy_def.get("type")
            if strategy_type not in strategy_classes:
                logger.warning(f"Unknown strategy type", type=strategy_type)
                continue

            strategy_class = strategy_classes[strategy_type]
            strategy = strategy_class(
                site_config=self.site_config,
                http_session=self._session,
                user_agent=self.user_agent,
            )
            self._strategies.append(strategy)

        # Sort by priority
        self._strategies.sort(key=lambda s: s.priority)

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create the HTTP session."""
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={"User-Agent": self.user_agent},
            )
            # Update strategies with the new session
            for strategy in self._strategies:
                strategy._session = self._session
        return self._session

    async def close(self) -> None:
        """Close the HTTP session and strategies."""
        for strategy in self._strategies:
            await strategy.close()

        if self._owns_session and self._session is not None:
            await self._session.close()
            self._session = None

    async def discover_content(
        self,
        limit: Optional[int] = None,
        strategy_filter: Optional[list[DiscoveryStrategy]] = None,
    ) -> DiscoveryResult:
        """Discover content using configured strategies with fallback.

        Args:
            limit: Maximum number of articles to discover
            strategy_filter: Optional list of strategies to use

        Returns:
            DiscoveryResult from the first successful strategy
        """
        # Ensure session is available
        await self.get_session()

        # Filter strategies if specified
        strategies = self._strategies
        if strategy_filter:
            strategies = [
                s for s in strategies if s.strategy_name in strategy_filter
            ]

        if not strategies:
            return DiscoveryResult(
                success=False,
                strategy=DiscoveryStrategy.RSS,
                errors=["No strategies available"],
            )

        all_errors = []
        tried_strategies = []

        for strategy in strategies:
            logger.info(
                f"Trying discovery strategy",
                strategy=strategy.strategy_name.value,
                site=self.site_config.domain,
                priority=strategy.priority,
            )

            tried_strategies.append(strategy.strategy_name.value)

            # Check if strategy is available
            availability = await strategy.is_available()
            if not availability.available:
                logger.info(
                    f"Strategy not available",
                    strategy=strategy.strategy_name.value,
                    reason=availability.reason,
                )
                all_errors.append(
                    f"{strategy.strategy_name.value}: {availability.reason}"
                )
                continue

            # Try the strategy
            try:
                result = await strategy.discover(limit)

                if result.success and len(result.articles) >= self.min_results:
                    logger.info(
                        f"Strategy succeeded",
                        strategy=strategy.strategy_name.value,
                        articles=len(result.articles),
                    )
                    return result

                # Strategy returned insufficient results
                if result.success:
                    logger.info(
                        f"Strategy returned insufficient results",
                        strategy=strategy.strategy_name.value,
                        articles=len(result.articles),
                        min_required=self.min_results,
                    )
                    all_errors.append(
                        f"{strategy.strategy_name.value}: Only {len(result.articles)} results (need {self.min_results})"
                    )

                    # If this is the last strategy, return what we have
                    if strategy == strategies[-1]:
                        return result
                else:
                    all_errors.extend(result.errors)

            except Exception as e:
                logger.error(
                    f"Strategy failed with exception",
                    strategy=strategy.strategy_name.value,
                    error=str(e),
                )
                all_errors.append(f"{strategy.strategy_name.value}: {str(e)}")

        # All strategies failed
        return DiscoveryResult(
            success=False,
            strategy=strategies[0].strategy_name if strategies else DiscoveryStrategy.RSS,
            errors=all_errors,
            warnings=[f"Tried strategies: {', '.join(tried_strategies)}"],
        )

    async def discover_with_all_strategies(
        self,
        limit_per_strategy: Optional[int] = None,
    ) -> dict[DiscoveryStrategy, DiscoveryResult]:
        """Discover content using all strategies (not just first success).

        Useful for gathering maximum content or comparing strategies.

        Args:
            limit_per_strategy: Maximum articles per strategy

        Returns:
            Dictionary mapping strategy to its result
        """
        await self.get_session()

        results = {}

        for strategy in self._strategies:
            try:
                result = await strategy.discover(limit_per_strategy)
                results[strategy.strategy_name] = result
            except Exception as e:
                logger.error(
                    f"Strategy failed",
                    strategy=strategy.strategy_name.value,
                    error=str(e),
                )
                results[strategy.strategy_name] = DiscoveryResult(
                    success=False,
                    strategy=strategy.strategy_name,
                    errors=[str(e)],
                )

        return results

    async def check_all_availability(self) -> dict[DiscoveryStrategy, bool]:
        """Check availability of all strategies.

        Returns:
            Dictionary mapping strategy to availability
        """
        await self.get_session()

        availability = {}

        for strategy in self._strategies:
            result = await strategy.is_available()
            availability[strategy.strategy_name] = result.available

        return availability

    def get_strategy(self, strategy_type: DiscoveryStrategy) -> Optional[BaseDiscoveryStrategy]:
        """Get a specific strategy by type.

        Args:
            strategy_type: Strategy type to get

        Returns:
            Strategy instance or None
        """
        for strategy in self._strategies:
            if strategy.strategy_name == strategy_type:
                return strategy
        return None

    def __repr__(self) -> str:
        return f"StrategyOrchestrator(site={self.site_config.domain}, strategies={len(self._strategies)})"


async def discover_site(
    site_config: SiteConfig,
    limit: Optional[int] = None,
    rate_limiter: Optional[RateLimiter] = None,
) -> DiscoveryResult:
    """Convenience function to discover content from a site.

    Args:
        site_config: Site configuration
        limit: Maximum articles to discover
        rate_limiter: Optional shared rate limiter

    Returns:
        DiscoveryResult with discovered articles
    """
    orchestrator = StrategyOrchestrator(
        site_config=site_config,
        rate_limiter=rate_limiter,
    )

    try:
        return await orchestrator.discover_content(limit)
    finally:
        await orchestrator.close()


def create_orchestrator_from_yaml(
    site_key: str,
    websites_config: dict,
    rate_limiter: Optional[RateLimiter] = None,
) -> StrategyOrchestrator:
    """Create an orchestrator from YAML configuration.

    Args:
        site_key: Site key in the configuration
        websites_config: Loaded websites.yaml configuration
        rate_limiter: Optional shared rate limiter

    Returns:
        Configured StrategyOrchestrator

    Raises:
        ValueError: If site_key not found in configuration
    """
    sites = websites_config.get("websites", {})

    if site_key not in sites:
        raise ValueError(f"Site '{site_key}' not found in configuration")

    site_data = sites[site_key]

    # Create SiteConfig from YAML
    site_config = SiteConfig(
        site_key=site_key,
        domain=site_data.get("domain"),
        name=site_data.get("name"),
        language=site_data.get("language", "de"),
        enabled=site_data.get("enabled", True),
        discovery_strategies=site_data.get("discovery_strategies", []),
    )

    # Get discovery settings
    discovery_settings = websites_config.get("discovery_settings", {})
    user_agent = discovery_settings.get(
        "user_agent",
        "PolicyTracker/1.0 (Political Monitoring Research)",
    )

    return StrategyOrchestrator(
        site_config=site_config,
        rate_limiter=rate_limiter,
        user_agent=user_agent,
    )
