"""
ETL-specific test fixtures.

Provides mock data, test configurations, and helper functions
for testing ETL collectors and transformers.
"""

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml


@pytest.fixture
def sample_client_context():
    """Sample client context for testing."""
    return {
        "client_profile": {
            "company_name": "TestCorp Inc.",
            "primary_markets": ["EU", "US", "UK"],
            "core_industries": ["technology", "finance", "healthcare"],
            "regulatory_concerns": [
                "data protection",
                "AI governance",
                "cybersecurity",
                "financial services",
            ],
        },
        "regulatory_focus": {
            "topic_patterns": [
                "GDPR compliance",
                "AI Act implementation",
                "Digital Services Act",
                "cybersecurity directive",
                "financial regulation",
            ],
            "exclude_patterns": ["non-relevant topic", "sports news"],
        },
        "monitoring_scope": {
            "regulatory_bodies": ["European Commission", "SEC", "FCA", "EDPB"],
            "policy_areas": [
                "artificial intelligence",
                "data protection",
                "cybersecurity",
                "digital services",
            ],
        },
    }


@pytest.fixture
def client_context_file(sample_client_context, tmp_path):
    """Create temporary client context YAML file."""
    context_file = tmp_path / "test_client.yaml"
    with open(context_file, "w") as f:
        yaml.dump(sample_client_context, f)
    return str(context_file)


@pytest.fixture
def sample_exa_response():
    """Sample Exa API response with realistic data."""
    return {
        "results": [
            {
                "title": "European Commission Publishes AI Act Implementation Guidelines",
                "url": "https://ec.europa.eu/ai-act-guidelines-2024",
                "text": "The European Commission has released comprehensive guidelines for implementing the AI Act, providing clarity on compliance requirements for high-risk AI systems. The guidelines cover risk assessment procedures, technical documentation requirements, and conformity assessment processes. Companies developing AI systems must ensure compliance by February 2025...",
                "publishedDate": "2024-03-15T09:30:00Z",
                "author": "European Commission Press Office",
                "score": 0.95,
                "highlights": ["AI Act", "compliance requirements", "high-risk AI systems"],
            },
            {
                "title": "EDPB Issues Guidance on GDPR Enforcement in AI Systems",
                "url": "https://edpb.europa.eu/gdpr-ai-guidance-2024",
                "text": "The European Data Protection Board has issued new guidance on applying GDPR principles to artificial intelligence systems. The guidance addresses data minimization, purpose limitation, and individual rights in AI contexts. Organizations using AI for automated decision-making must implement additional safeguards...",
                "publishedDate": "2024-03-14T14:15:00Z",
                "author": "EDPB Secretariat",
                "score": 0.89,
                "highlights": ["GDPR", "AI systems", "automated decision-making"],
            },
            {
                "title": "Meta Announces DSA Compliance Measures for EU Operations",
                "url": "https://about.meta.com/dsa-compliance-2024",
                "text": "Meta has announced comprehensive measures to comply with the EU Digital Services Act, including enhanced content moderation systems, transparency reporting, and risk assessment procedures. The company will implement new tools for user reporting and appeals processes...",
                "publishedDate": "2024-03-13T16:45:00Z",
                "author": "Meta Policy Team",
                "score": 0.82,
                "highlights": ["Digital Services Act", "content moderation", "compliance measures"],
            },
        ]
    }


@pytest.fixture
def sample_apify_response():
    """Sample Apify API response."""
    return {"data": {"id": "test_run_id_123", "defaultDatasetId": "test_dataset_456"}}


@pytest.fixture
def sample_apify_items():
    """Sample Apify dataset items."""
    return [
        {
            "title": "Apple Introduces New Privacy Features in iOS 18",
            "url": "https://www.apple.com/newsroom/privacy-ios18",
            "text": "Apple has announced significant privacy enhancements in iOS 18, including on-device AI processing, enhanced app permissions, and improved data encryption. The updates respond to growing regulatory requirements across global markets...",
            "published": "2024-03-15T10:00:00Z",
            "author": "Apple Newsroom",
            "domain": "apple.com",
        },
        {
            "title": "Google Updates Privacy Policy Following EU Requirements",
            "url": "https://blog.google/privacy-policy-update-2024",
            "text": "Google has updated its privacy policy to address new European regulatory requirements, including enhanced user consent mechanisms and data portability features. The changes affect all Google services operating in the EU...",
            "published": "2024-03-12T08:30:00Z",
            "author": "Google Privacy Team",
            "domain": "google.com",
        },
    ]


@pytest.fixture
def mock_storage_client():
    """Mock storage client for testing."""
    client = MagicMock()
    client.upload_text = AsyncMock(return_value=True)
    client.download_text = AsyncMock(return_value="Mock content")
    client.upload_json = AsyncMock(return_value=True)
    client.download_json = AsyncMock(return_value={"test": "data"})
    return client


@pytest.fixture
def mock_exa_collector():
    """Mock ExaDirectCollector for testing."""
    collector = MagicMock()
    collector.collect_news = AsyncMock(
        return_value=[
            {
                "title": "Test Article",
                "url": "https://example.com/test",
                "content": "Test content...",
                "published_date": "2024-03-15T10:00:00Z",
                "author": "Test Author",
                "source": "example.com",
            }
        ]
    )
    return collector


@pytest.fixture
def sample_policy_queries():
    """Sample policy queries for testing."""
    return [
        {
            "query": "EU AI Act implementation guidelines technology companies",
            "category": "AI_regulation",
            "description": "AI Act compliance for tech sector",
        },
        {
            "query": "GDPR enforcement actions data protection technology",
            "category": "data_protection",
            "description": "GDPR compliance in tech",
        },
        {
            "query": "Digital Services Act content moderation requirements",
            "category": "digital_services",
            "description": "DSA compliance requirements",
        },
    ]


@pytest.fixture
def sample_transformed_markdown():
    """Sample transformed markdown content."""
    return """---
title: "European Commission Publishes AI Act Implementation Guidelines"
url: "https://ec.europa.eu/ai-act-guidelines-2024"
published_date: "2024-03-15T09:30:00Z"
author: "European Commission Press Office"
source: "ec.europa.eu"
collection_type: "policy_landscape"
policy_category: "AI_regulation"
extracted_date: "2024-03-15T12:00:00Z"
---

# European Commission Publishes AI Act Implementation Guidelines

**Source:** [ec.europa.eu](https://ec.europa.eu/ai-act-guidelines-2024)
**Published:** March 15, 2024
**Author:** European Commission Press Office

The European Commission has released comprehensive guidelines for implementing the AI Act, providing clarity on compliance requirements for high-risk AI systems. The guidelines cover risk assessment procedures, technical documentation requirements, and conformity assessment processes. Companies developing AI systems must ensure compliance by February 2025...

---
*Collected via ETL Pipeline - Policy Landscape Monitoring*
"""


class ETLTestHelper:
    """Helper class for ETL testing."""

    @staticmethod
    def create_test_article(
        title: str = "Test Article",
        url: str = "https://example.com/test",
        content: str = "Test content...",
        published_date: str = None,
        author: str = "Test Author",
    ) -> dict[str, Any]:
        """Create test article data."""
        if published_date is None:
            published_date = datetime.now().isoformat()

        return {
            "title": title,
            "url": url,
            "content": content,
            "published_date": published_date,
            "author": author,
            "source": "example.com",
        }

    @staticmethod
    def create_test_query(
        query: str = "test query",
        category: str = "test_category",
        description: str = "test description",
    ) -> dict[str, str]:
        """Create test query data."""
        return {"query": query, "category": category, "description": description}

    @staticmethod
    def assert_article_structure(article: dict[str, Any]):
        """Assert article has required structure."""
        required_fields = ["title", "url", "content", "published_date", "author", "source"]
        for field in required_fields:
            assert field in article, f"Missing required field: {field}"
            assert article[field] is not None, f"Field {field} should not be None"

    @staticmethod
    def assert_collection_result_structure(result: dict[str, Any]):
        """Assert collection result has required structure."""
        required_fields = [
            "collection_type",
            "start_time",
            "end_time",
            "processing_time_seconds",
            "queries_processed",
            "total_articles_found",
            "documents_saved",
        ]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

    @staticmethod
    def create_date_range(days_back: int = 7) -> tuple:
        """Create date range for testing."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        return start_date, end_date


@pytest.fixture
def etl_test_helper():
    """Provide ETL test helper instance."""
    return ETLTestHelper()


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory structure."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create subdirectories
    (data_dir / "input" / "news").mkdir(parents=True)
    (data_dir / "input" / "policy").mkdir(parents=True)
    (data_dir / "output").mkdir()
    (data_dir / "context").mkdir()

    return data_dir


@pytest.fixture
def mock_initialization_tracker():
    """Mock ETL initialization tracker."""
    tracker = MagicMock()
    tracker.is_initialized = MagicMock(return_value=False)
    tracker.get_collection_days = MagicMock(return_value=30)
    tracker.mark_initialized = AsyncMock()
    return tracker
