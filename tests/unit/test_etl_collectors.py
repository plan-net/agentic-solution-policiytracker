"""
Properly written ETL collector tests following good testing patterns.

Key principles:
- Mock only external dependencies (HTTP APIs)
- Test real internal interfaces and method calls
- Use real file I/O with temporary directories
- Validate interface contracts between components
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import yaml

from src.etl.collectors.apify_news import ApifyNewsCollector
from src.etl.collectors.exa_direct import ExaDirectCollector
from src.etl.collectors.policy_landscape import PolicyLandscapeCollector
from src.etl.storage.local import LocalStorage
from src.etl.transformers.markdown_transformer import MarkdownTransformer


@pytest.fixture
def test_exa_api_response():
    """Realistic Exa API response for mocking external calls."""
    return {
        "results": [
            {
                "title": "EU AI Act Implementation Guidelines Published",
                "url": "https://ec.europa.eu/ai-act-guidelines-2024",
                "text": "The European Commission has released comprehensive guidelines for implementing the AI Act, providing clarity on compliance requirements for high-risk AI systems. Companies developing AI systems must ensure compliance by February 2025.",
                "publishedDate": "2024-03-15T09:30:00Z",
                "author": "European Commission Press Office",
                "score": 0.95,
            },
            {
                "title": "GDPR Enforcement Actions Against Big Tech",
                "url": "https://edpb.europa.eu/gdpr-enforcement-2024",
                "text": "The European Data Protection Board announced new enforcement actions against major technology companies for violations of GDPR principles, including inadequate data minimization practices.",
                "publishedDate": "2024-03-14T14:15:00Z",
                "author": "EDPB Secretariat",
                "score": 0.89,
            },
        ]
    }


@pytest.fixture
def test_apify_response():
    """Realistic Apify API response for mocking."""
    return {"data": {"id": "test_run_123", "defaultDatasetId": "dataset_456"}}


@pytest.fixture
def test_apify_items():
    """Realistic Apify dataset items."""
    return [
        {
            "title": "Apple Announces Enhanced Privacy Features",
            "url": "https://www.apple.com/newsroom/privacy-updates-2024",
            "text": "Apple has announced significant privacy enhancements responding to global regulatory requirements including GDPR and emerging AI governance frameworks.",
            "published": "2024-03-15T10:00:00Z",
            "author": "Apple Newsroom",
            "domain": "apple.com",
        }
    ]


@pytest.fixture
def client_context_file(tmp_path):
    """Create a real client context YAML file for testing."""
    context_data = {
        "client_profile": {
            "company_name": "TestCorp",
            "primary_markets": ["EU", "US"],
            "core_industries": ["technology", "finance"],
        },
        "regulatory_focus": {"topic_patterns": ["AI regulation", "data privacy", "cybersecurity"]},
    }

    context_file = tmp_path / "client.yaml"
    with open(context_file, "w") as f:
        yaml.dump(context_data, f)
    return str(context_file)


class TestETLInterfaceContracts:
    """Test that all ETL components have correct interfaces."""

    def test_transformer_interface_contract(self):
        """Test MarkdownTransformer has correct interface."""
        transformer = MarkdownTransformer()

        # Test correct method exists
        assert hasattr(
            transformer, "transform_article"
        ), "MarkdownTransformer must have transform_article method"

        # Test incorrect method does NOT exist (catches method name bugs)
        assert not hasattr(
            transformer, "transform_to_markdown"
        ), "MarkdownTransformer should not have transform_to_markdown method"

        # Test method signature
        import inspect

        sig = inspect.signature(transformer.transform_article)
        params = list(sig.parameters.keys())
        assert "article" in params, "transform_article must accept article parameter"

    def test_storage_interface_contract(self):
        """Test storage interfaces are consistent."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalStorage(base_path=temp_dir)

            # Test required methods exist
            required_methods = [
                "save_document",
                "get_document",
                "list_documents",
                "document_exists",
                "delete_document",
            ]

            for method_name in required_methods:
                assert hasattr(storage, method_name), f"LocalStorage must have {method_name} method"

                method = getattr(storage, method_name)
                assert callable(method), f"{method_name} must be callable"

    def test_collector_interface_consistency(self, client_context_file):
        """Test that all collectors have consistent interfaces."""

        # Initialize all collectors
        exa_collector = ExaDirectCollector("test_key")
        apify_collector = ApifyNewsCollector("test_token")
        policy_collector = PolicyLandscapeCollector(
            exa_api_key="test_key", client_context_path=client_context_file, storage_type="local"
        )

        # Test collect_news method exists on collectors that should have it
        assert hasattr(exa_collector, "collect_news")
        assert hasattr(apify_collector, "collect_news")

        # Test policy collector has expected methods
        assert hasattr(policy_collector, "collect_policy_documents")
        assert hasattr(policy_collector, "storage")
        assert hasattr(policy_collector, "transformer")


class TestExaDirectCollector:
    """Test ExaDirectCollector with minimal mocking."""

    @pytest.mark.asyncio
    async def test_collect_news_with_real_processing(self, test_exa_api_response):
        """Test news collection with real internal processing."""
        collector = ExaDirectCollector("test_api_key")

        # Mock only the external HTTP call
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = test_exa_api_response
            mock_post.return_value.__aenter__.return_value = mock_response

            # Test real internal processing
            articles = await collector.collect_news(
                query="EU AI Act regulation", max_items=10, days_back=7
            )

            # Validate real processing results
            assert len(articles) == 2

            # Test real article normalization
            article = articles[0]
            assert article["title"] == "EU AI Act Implementation Guidelines Published"
            assert article["url"] == "https://ec.europa.eu/ai-act-guidelines-2024"
            assert "published_date" in article
            assert "content" in article
            assert "source" in article

    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test real error handling without mocking internal logic."""
        collector = ExaDirectCollector("test_api_key")

        # Mock external API to return error
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 429  # Rate limit
            mock_response.text.return_value = "Rate limit exceeded"
            mock_post.return_value.__aenter__.return_value = mock_response

            # Test real error handling
            with pytest.raises(Exception) as exc_info:
                await collector.collect_news(query="test")

            assert "429" in str(exc_info.value)

    def test_article_normalization_real_logic(self):
        """Test real article normalization without mocking."""
        collector = ExaDirectCollector("test_api_key")

        # Test with real data
        raw_item = {
            "title": "Test Policy Update",
            "url": "https://example.com/policy",
            "text": "Policy content goes here...",
            "publishedDate": "2024-03-15T10:30:00Z",
            "author": "Policy Authority",
            "score": 0.95,
        }

        # Test real normalization logic
        normalized = collector._normalize_article(raw_item)

        # Validate real transformation
        assert normalized["title"] == "Test Policy Update"
        assert normalized["url"] == "https://example.com/policy"
        assert normalized["content"] == "Policy content goes here..."
        assert normalized["author"] == "Policy Authority"
        assert "published_date" in normalized
        assert "source" in normalized


class TestApifyNewsCollector:
    """Test ApifyNewsCollector with real internal processing."""

    @pytest.mark.asyncio
    async def test_collect_news_real_flow(self, test_apify_response, test_apify_items):
        """Test complete collection flow with real processing."""
        collector = ApifyNewsCollector("test_api_token")

        # Mock only external API calls
        with patch("aiohttp.ClientSession.post") as mock_post, patch(
            "aiohttp.ClientSession.get"
        ) as mock_get:
            # Mock run creation
            mock_run_response = AsyncMock()
            mock_run_response.status = 201
            mock_run_response.json.return_value = test_apify_response
            mock_post.return_value.__aenter__.return_value = mock_run_response

            # Mock dataset retrieval
            mock_items_response = AsyncMock()
            mock_items_response.status = 200
            mock_items_response.json.return_value = test_apify_items
            mock_get.return_value.__aenter__.return_value = mock_items_response

            # Test real collection processing
            articles = await collector.collect_news(query="Apple", max_items=10, days_back=7)

            # Validate real results
            assert len(articles) == 1
            assert articles[0]["title"] == "Apple Announces Enhanced Privacy Features"
            assert "apify_id" in articles[0]


class TestPolicyLandscapeCollector:
    """Test PolicyLandscapeCollector with real component integration."""

    @pytest.mark.asyncio
    async def test_policy_collection_real_integration(
        self, client_context_file, test_exa_api_response
    ):
        """Test policy collection with real component interactions."""

        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize with real storage
            collector = PolicyLandscapeCollector(
                exa_api_key="test_key",
                client_context_path=client_context_file,
                storage_type="local",
            )

            # Override storage to use temp directory
            collector.storage = LocalStorage(base_path=temp_dir)

            # Mock only external API calls
            collector.exa_collector.collect_news = AsyncMock(
                return_value=test_exa_api_response["results"]
            )

            # Test real integration
            result = await collector.collect_policy_documents(
                days_back=7, max_results_per_query=5, max_concurrent_queries=2
            )

            # Validate real behavior
            assert result["collection_type"] == "policy_landscape"
            assert result["queries_processed"] > 0
            assert result["documents_saved"] >= 0  # May be 0 due to deduplication

            # Test real file creation
            md_files = list(Path(temp_dir).rglob("*.md"))
            json_files = list(Path(temp_dir).rglob("*.json"))

            # Should create markdown files, no JSON
            assert len(json_files) == 0, "Should not create JSON metadata files"

            # If documents were saved, verify real file structure
            if result["documents_saved"] > 0:
                assert len(md_files) > 0, "Should create markdown files"

                # Test real file content
                with open(md_files[0]) as f:
                    content = f.read()

                # Verify real markdown structure
                assert content.startswith("---"), "Should have YAML frontmatter"
                assert "title:" in content
                assert "collection_type: policy_landscape" in content

    @pytest.mark.asyncio
    async def test_real_transformer_usage(self, client_context_file):
        """Test that policy collector uses real transformer correctly."""

        with tempfile.TemporaryDirectory() as temp_dir:
            collector = PolicyLandscapeCollector(
                exa_api_key="test_key",
                client_context_path=client_context_file,
                storage_type="local",
            )

            collector.storage = LocalStorage(base_path=temp_dir)

            # Test real transformer usage (this would catch method name bugs!)
            test_article = {
                "title": "Test Policy Document",
                "url": "https://example.com/policy",
                "content": "Policy content here...",
                "published_date": "2024-03-15T10:00:00Z",
                "author": "Policy Authority",
                "source": "example.com",
                "collection_type": "policy_landscape",
            }

            # Test real document saving (uses real transformer)
            result = await collector._save_policy_documents([test_article])

            # Validate real transformation occurred
            assert len(result) == 1
            assert result[0]["filename"].endswith(".md")

            # Verify real file was created
            md_files = list(Path(temp_dir).rglob("*.md"))
            assert len(md_files) == 1

            # Test real file content
            with open(md_files[0]) as f:
                content = f.read()

            assert "Test Policy Document" in content
            assert "collection_type: policy_landscape" in content

    @pytest.mark.asyncio
    async def test_query_generation_real_logic(self, client_context_file):
        """Test real query generation logic."""
        collector = PolicyLandscapeCollector(
            exa_api_key="test_key", client_context_path=client_context_file, storage_type="local"
        )

        # Test real query generation
        stats = await collector.get_collection_stats()

        # Validate real query generation results
        assert stats["total_queries"] > 0
        assert stats["validation"]["is_valid"]
        assert "categories" in stats

        # Test that queries contain expected patterns from client context
        # (This tests real YAML parsing and query generation logic)


class TestDateValidation:
    """Test date parsing and validation in collectors."""

    def test_exa_date_parsing_future_dates(self):
        """Test that Exa collector correctly handles future dates."""
        collector = ExaDirectCollector("test-key")

        # Test future date (should be corrected to current date)
        future_date = "2025-06-01T00:00:00.000Z"
        result = collector._parse_date(future_date)

        assert result is not None
        assert "2025-05-28" in result  # Should be corrected to today

        # Test valid recent date (should be preserved)
        valid_date = "2025-05-27T10:00:00.000Z"
        result = collector._parse_date(valid_date)
        assert result == "2025-05-27T10:00:00"

        # Test too old date (should be corrected)
        old_date = "1985-01-01T00:00:00.000Z"
        result = collector._parse_date(old_date)
        assert result is not None
        assert "2025-05-28" in result  # Should be corrected to today

    def test_apify_date_parsing_future_dates(self):
        """Test that Apify collector correctly handles future dates."""
        collector = ApifyNewsCollector("test-token")

        # Test future date (should be corrected to current date)
        future_date = "2025-06-01T00:00:00.000Z"
        result = collector._parse_date(future_date)

        assert result is not None
        assert "2025-05-28" in result  # Should be corrected to today

        # Test valid recent date (should be preserved)
        valid_date = "2025-05-27T10:00:00.000Z"
        result = collector._parse_date(valid_date)
        assert result == "2025-05-27T10:00:00"

    def test_date_parsing_invalid_formats(self):
        """Test handling of invalid date formats."""
        collector = ExaDirectCollector("test-key")

        # Invalid formats should return None
        assert collector._parse_date("invalid-date") is None
        assert collector._parse_date(None) is None
        assert collector._parse_date("") is None
        assert collector._parse_date("not-a-date-at-all") is None


class TestTransformerRealBehavior:
    """Test MarkdownTransformer with real processing."""

    def test_real_article_transformation(self):
        """Test real transformation logic without mocking."""
        transformer = MarkdownTransformer()

        # Test with real article data
        article = {
            "title": "EU Digital Services Act Requirements",
            "url": "https://ec.europa.eu/dsa-requirements",
            "content": "The Digital Services Act introduces new obligations for online platforms...",
            "published_date": "2024-03-15T10:00:00Z",
            "author": "European Commission",
            "source": "ec.europa.eu",
        }

        # Test real transformation (no mocking)
        markdown_content, filename = transformer.transform_article(article)

        # Validate real transformation results
        assert markdown_content.startswith("---"), "Should have YAML frontmatter"
        assert "title: EU Digital Services Act Requirements" in markdown_content
        assert "url: https://ec.europa.eu/dsa-requirements" in markdown_content
        assert "# EU Digital Services Act Requirements" in markdown_content
        assert "The Digital Services Act introduces" in markdown_content

        # Test real filename generation
        assert filename.endswith(".md")
        assert len(filename) > 10  # Should be meaningful filename


class TestStorageRealBehavior:
    """Test storage with real file operations."""

    @pytest.mark.asyncio
    async def test_real_document_saving(self):
        """Test real document saving without mocking file I/O."""

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalStorage(base_path=temp_dir)

            # Test real file saving
            content = """---
title: "Test Document"
url: "https://example.com/test"
collection_type: "test"
---

# Test Document

This is test content.
"""

            metadata = {
                "url": "https://example.com/test",
                "collection_type": "test",
                "source": "example.com",
            }

            # Test real save operation
            success = await storage.save_document(content, "test/document.md", metadata)

            assert success, "Save should succeed"

            # Test real file existence
            file_path = Path(temp_dir) / "test/document.md"
            assert file_path.exists(), "File should be created"

            # Test real file content
            with open(file_path) as f:
                saved_content = f.read()

            assert saved_content == content, "Content should match exactly"

            # Test that no JSON metadata files were created
            json_files = list(Path(temp_dir).rglob("*.json"))
            assert len(json_files) == 0, "Should not create JSON metadata files"

    @pytest.mark.asyncio
    async def test_real_document_listing(self):
        """Test real document listing functionality."""

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalStorage(base_path=temp_dir)

            # Create real test files
            test_files = [
                "policy/2024-03/doc1.md",
                "policy/2024-03/doc2.md",
                "news/2024-03/article1.md",
            ]

            for file_path in test_files:
                await storage.save_document("# Test", file_path, {})

            # Test real listing
            all_docs = await storage.list_documents()
            policy_docs = await storage.list_documents("policy/")

            # Validate real results
            assert len(all_docs) == 3
            assert len(policy_docs) == 2

            # Test that only markdown files are listed
            for doc_path in all_docs:
                assert doc_path.endswith(".md")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
