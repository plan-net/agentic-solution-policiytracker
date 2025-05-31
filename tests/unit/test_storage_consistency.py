"""
Test that both news and policy collectors use consistent storage interfaces.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import yaml

from src.etl.collectors.policy_landscape import PolicyLandscapeCollector
from src.etl.storage.local import LocalStorage


class TestStorageConsistency:
    """Test that all collectors use consistent storage patterns."""

    @pytest.fixture
    def client_context_file(self, tmp_path):
        """Create test client context file."""
        context_data = {
            "client_profile": {
                "company_name": "TestCorp",
                "primary_markets": ["EU"],
                "core_industries": ["technology"],
            },
            "regulatory_focus": {"topic_patterns": ["AI regulation"]},
        }

        context_file = tmp_path / "client.yaml"
        with open(context_file, "w") as f:
            yaml.dump(context_data, f)
        return str(context_file)

    @pytest.mark.asyncio
    async def test_policy_collector_uses_storage_interface(self, client_context_file):
        """Test that PolicyLandscapeCollector uses standardized storage interface."""

        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize collector with local storage
            collector = PolicyLandscapeCollector(
                exa_api_key="test_key",
                client_context_path=client_context_file,
                storage_type="local",
            )

            # Override the storage base path for testing
            collector.storage = LocalStorage(base_path=temp_dir)

            # Mock the exa collector to return test articles
            test_articles = [
                {
                    "title": "EU AI Act Implementation Guide",
                    "url": "https://ec.europa.eu/ai-act-guide",
                    "content": "The European Union has published implementation guidelines...",
                    "published_date": "2024-03-15T10:00:00Z",
                    "author": "EU Commission",
                    "source": "ec.europa.eu",
                }
            ]

            collector.exa_collector.collect_news = AsyncMock(return_value=test_articles)

            # Test document saving
            result = await collector.collect_policy_documents(
                days_back=7, max_results_per_query=1, max_concurrent_queries=1
            )

            # Verify storage interface was used correctly
            assert result["documents_saved"] == 1
            assert result["collection_type"] == "policy_landscape"

            # Check that files were created via storage interface
            base_path = Path(temp_dir)
            md_files = list(base_path.rglob("*.md"))
            json_files = list(base_path.rglob("*.json"))

            assert len(md_files) == 1, "Should create exactly one markdown file"
            assert len(json_files) == 0, "Should not create any JSON files"

            # Verify the content structure
            with open(md_files[0]) as f:
                content = f.read()

            assert 'title: "EU AI Act Implementation Guide"' in content
            assert "collection_type: policy_landscape" in content
            assert "policy_category:" in content

    def test_storage_interface_consistency(self):
        """Test that storage interfaces are consistent across collectors."""

        # Test that both news and policy use the same storage factory
        from src.etl.storage import get_storage

        # Create storage instances
        news_storage = get_storage("local", base_path="data/input/news")
        policy_storage = get_storage("local", base_path="data/input")

        # Both should be LocalStorage instances
        assert isinstance(news_storage, LocalStorage)
        assert isinstance(policy_storage, LocalStorage)

        # Both should have the save_document method with same signature
        import inspect

        news_sig = inspect.signature(news_storage.save_document)
        policy_sig = inspect.signature(policy_storage.save_document)

        assert news_sig == policy_sig, "Storage interfaces should be identical"

        # Both should have consistent method sets
        news_methods = set(dir(news_storage))
        policy_methods = set(dir(policy_storage))

        assert news_methods == policy_methods, "Storage instances should have same methods"

    @pytest.mark.asyncio
    async def test_metadata_consistency(self, client_context_file):
        """Test that both collectors create consistent metadata structures."""

        with tempfile.TemporaryDirectory() as temp_dir:
            collector = PolicyLandscapeCollector(
                exa_api_key="test_key",
                client_context_path=client_context_file,
                storage_type="local",
            )

            collector.storage = LocalStorage(base_path=temp_dir)

            # Mock article with metadata
            test_article = {
                "title": "Test Policy Document",
                "url": "https://example.com/policy",
                "content": "Policy content...",
                "published_date": "2024-03-15T10:00:00Z",
                "author": "Policy Authority",
                "source": "example.com",
                "policy_category": "AI_regulation",
                "collection_type": "policy_landscape",
                "query_description": "AI regulatory updates",
            }

            collector.exa_collector.collect_news = AsyncMock(return_value=[test_article])

            # Collect documents
            await collector.collect_policy_documents(
                days_back=7, max_results_per_query=1, max_concurrent_queries=1
            )

            # Read the created file
            md_files = list(Path(temp_dir).rglob("*.md"))
            assert len(md_files) == 1

            with open(md_files[0]) as f:
                content = f.read()

            # Verify consistent metadata structure (same as news collection)
            expected_fields = [
                "title:",
                "url:",
                "published_date:",
                "author:",
                "source:",
                "collection_type:",
                "policy_category:",
                "collector_type:",
            ]

            for field in expected_fields:
                assert field in content, f"Missing metadata field: {field}"

    def test_collector_initialization_consistency(self, client_context_file):
        """Test that collector initialization patterns are consistent."""

        # Both collectors should initialize with similar parameters
        policy_collector = PolicyLandscapeCollector(
            exa_api_key="test_key", client_context_path=client_context_file, storage_type="local"
        )

        # Verify internal structure
        assert hasattr(policy_collector, "storage"), "Should have storage attribute"
        assert hasattr(policy_collector, "exa_collector"), "Should have exa_collector"
        assert hasattr(policy_collector, "transformer"), "Should have transformer"

        # Storage should be initialized correctly
        assert isinstance(policy_collector.storage, LocalStorage)

        # Check that the base path is set correctly
        expected_path = Path("data/input")
        actual_path = policy_collector.storage.base_path
        assert actual_path.name == expected_path.name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
