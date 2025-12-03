"""Tests for website discovery models."""

from datetime import datetime

import pytest

from src.etl.collectors.website_discovery.models import (
    DiscoveredArticle,
    DiscoveryResult,
    DiscoveryStrategy,
    FilterDecision,
    SiteConfig,
    StrategyAvailability,
)


class TestDiscoveredArticle:
    """Tests for DiscoveredArticle model."""

    def test_create_basic_article(self):
        """Test creating a basic discovered article."""
        article = DiscoveredArticle(
            url="https://example.com/article/1",
            title="Test Article",
            source_domain="example.com",
            discovery_strategy=DiscoveryStrategy.RSS,
        )

        assert article.url == "https://example.com/article/1"
        assert article.title == "Test Article"
        assert article.source_domain == "example.com"
        assert article.discovery_strategy == DiscoveryStrategy.RSS
        assert article.content_fetched is False

    def test_article_with_metadata(self):
        """Test creating article with full metadata."""
        pub_date = datetime(2024, 1, 15)
        article = DiscoveredArticle(
            url="https://example.com/article/2",
            title="Article with Metadata",
            source_domain="example.com",
            discovery_strategy=DiscoveryStrategy.SECTION,
            published_date=pub_date,
            description="This is a test article",
            author="John Doe",
            category="politics",
        )

        assert article.published_date == pub_date
        assert article.description == "This is a test article"
        assert article.author == "John Doe"
        assert article.category == "politics"

    def test_article_hashing(self):
        """Test URL-based hashing for deduplication."""
        article1 = DiscoveredArticle(
            url="https://example.com/article/1",
            title="Article 1",
            source_domain="example.com",
            discovery_strategy=DiscoveryStrategy.RSS,
        )
        article2 = DiscoveredArticle(
            url="https://example.com/article/1",
            title="Different Title",
            source_domain="example.com",
            discovery_strategy=DiscoveryStrategy.SITEMAP,
        )
        article3 = DiscoveredArticle(
            url="https://example.com/article/2",
            title="Article 1",
            source_domain="example.com",
            discovery_strategy=DiscoveryStrategy.RSS,
        )

        # Same URL = equal
        assert article1 == article2
        assert hash(article1) == hash(article2)

        # Different URL = not equal
        assert article1 != article3
        assert hash(article1) != hash(article3)

    def test_to_article_dict(self):
        """Test conversion to markdown transformer compatible dict."""
        article = DiscoveredArticle(
            url="https://example.com/article/1",
            title="Test Article",
            source_domain="example.com",
            discovery_strategy=DiscoveryStrategy.RSS,
            description="A test description",
            published_date=datetime(2024, 1, 15, 10, 30),
        )
        article.full_content = "Full article content here."

        result = article.to_article_dict()

        assert result["title"] == "Test Article"
        assert result["url"] == "https://example.com/article/1"
        assert result["source"] == "example.com"
        assert result["description"] == "A test description"
        assert result["content"] == "Full article content here."
        assert result["collection_type"] == "website_discovery"
        assert result["discovery_method"] == "rss"
        assert result["language"] == "de"


class TestDiscoveryResult:
    """Tests for DiscoveryResult model."""

    def test_create_empty_result(self):
        """Test creating an empty discovery result."""
        result = DiscoveryResult(
            success=True,
            strategy=DiscoveryStrategy.RSS,
        )

        assert result.success is True
        assert result.strategy == DiscoveryStrategy.RSS
        assert len(result.articles) == 0
        assert len(result.errors) == 0

    def test_mark_completed(self):
        """Test marking result as completed."""
        result = DiscoveryResult(
            success=True,
            strategy=DiscoveryStrategy.RSS,
        )

        assert result.completed_at is None
        assert result.duration_seconds is None

        result.mark_completed()

        assert result.completed_at is not None
        assert result.duration_seconds is not None
        assert result.duration_seconds >= 0


class TestSiteConfig:
    """Tests for SiteConfig model."""

    def test_create_site_config(self):
        """Test creating a site configuration."""
        config = SiteConfig(
            site_key="bundesregierung",
            domain="bundesregierung.de",
            name="Bundesregierung",
            language="de",
            discovery_strategies=[
                {"type": "rss", "priority": 1, "config": {"feeds": []}},
                {"type": "section", "priority": 2, "config": {"sections": []}},
            ],
        )

        assert config.site_key == "bundesregierung"
        assert config.domain == "bundesregierung.de"
        assert config.enabled is True
        assert len(config.discovery_strategies) == 2

    def test_get_strategy_config(self):
        """Test getting configuration for a specific strategy."""
        config = SiteConfig(
            site_key="test",
            domain="test.de",
            name="Test",
            discovery_strategies=[
                {
                    "type": "rss",
                    "priority": 1,
                    "config": {"feeds": [{"url": "http://example.com/rss"}]},
                },
            ],
        )

        rss_config = config.get_strategy_config("rss")
        assert rss_config is not None
        assert "feeds" in rss_config

        missing_config = config.get_strategy_config("sitemap")
        assert missing_config is None

    def test_get_strategy_priority(self):
        """Test getting priority for a specific strategy."""
        config = SiteConfig(
            site_key="test",
            domain="test.de",
            name="Test",
            discovery_strategies=[
                {"type": "rss", "priority": 1},
                {"type": "section", "priority": 2},
            ],
        )

        assert config.get_strategy_priority("rss") == 1
        assert config.get_strategy_priority("section") == 2
        assert config.get_strategy_priority("sitemap") is None


class TestStrategyAvailability:
    """Tests for StrategyAvailability model."""

    def test_available_strategy(self):
        """Test creating available strategy result."""
        availability = StrategyAvailability(
            available=True,
            reason="3 feeds accessible",
            feed_count=3,
        )

        assert availability.available is True
        assert availability.feed_count == 3

    def test_unavailable_strategy(self):
        """Test creating unavailable strategy result."""
        availability = StrategyAvailability(
            available=False,
            reason="No RSS feeds configured",
        )

        assert availability.available is False
        assert "No RSS" in availability.reason
