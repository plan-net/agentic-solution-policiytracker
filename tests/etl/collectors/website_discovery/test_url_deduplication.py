"""Tests for URL deduplication."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.etl.utils.url_deduplication import URLDeduplicator


@pytest.fixture
def temp_state_file():
    """Create a temporary state file for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_state.json"


@pytest.fixture
def deduplicator(temp_state_file):
    """Create a URLDeduplicator instance."""
    return URLDeduplicator(state_file=str(temp_state_file))


class TestURLDeduplicator:
    """Tests for URLDeduplicator."""

    def test_initialization(self, deduplicator):
        """Test deduplicator initialization."""
        assert deduplicator is not None
        assert deduplicator.state_file.parent.exists()

    def test_mark_and_check_processed(self, deduplicator):
        """Test marking and checking processed URLs."""
        url = "https://example.com/article/1"

        assert deduplicator.is_processed(url) is False

        deduplicator.mark_processed(url, source="example.com")

        assert deduplicator.is_processed(url) is True

    def test_filter_new_urls(self, deduplicator):
        """Test filtering new URLs from a list."""
        # Mark some URLs as processed
        deduplicator.mark_processed("https://example.com/article/1")
        deduplicator.mark_processed("https://example.com/article/2")

        all_urls = [
            "https://example.com/article/1",  # Already processed
            "https://example.com/article/2",  # Already processed
            "https://example.com/article/3",  # New
            "https://example.com/article/4",  # New
        ]

        new_urls = deduplicator.filter_new_urls(all_urls)

        assert len(new_urls) == 2
        assert "https://example.com/article/3" in new_urls
        assert "https://example.com/article/4" in new_urls

    def test_url_normalization(self, deduplicator):
        """Test URL normalization for consistent hashing."""
        # These should be treated as the same URL
        url1 = "https://example.com/article/1"
        url2 = "https://example.com/article/1/"
        url3 = "https://example.com/article/1?utm_source=twitter"

        deduplicator.mark_processed(url1)

        # All variations should be recognized as processed
        assert deduplicator.is_processed(url2) is True
        assert deduplicator.is_processed(url3) is True

    def test_persistence(self, temp_state_file):
        """Test state persistence across instances."""
        # First instance
        dedup1 = URLDeduplicator(state_file=str(temp_state_file))
        dedup1.mark_processed("https://example.com/article/1")
        dedup1.save_state()

        # Second instance loads state
        dedup2 = URLDeduplicator(state_file=str(temp_state_file))
        assert dedup2.is_processed("https://example.com/article/1") is True

    def test_cleanup_old_entries(self, temp_state_file):
        """Test cleanup of old entries."""
        deduplicator = URLDeduplicator(state_file=str(temp_state_file))

        # Add a URL with old timestamp
        old_date = (datetime.now() - timedelta(days=100)).isoformat()
        deduplicator._state["processed_urls"]["old_hash"] = {
            "url": "https://example.com/old",
            "processed_at": old_date,
            "source": "example.com",
        }

        # Add a recent URL
        deduplicator.mark_processed("https://example.com/new")

        # Cleanup entries older than 90 days
        removed = deduplicator.cleanup_old_entries(days=90)

        assert removed == 1
        assert not deduplicator.is_processed("https://example.com/old")
        assert deduplicator.is_processed("https://example.com/new")

    def test_update_run_stats(self, deduplicator):
        """Test updating run statistics."""
        deduplicator.update_run_stats(discovered=50, saved=25, site="example.com")

        stats = deduplicator.get_stats()

        assert stats["total_discovered"] == 50
        assert stats["total_saved"] == 25
        assert "example.com" in stats["site_statistics"]
        assert stats["site_statistics"]["example.com"]["total_discovered"] == 50

    def test_get_stats(self, deduplicator):
        """Test getting statistics."""
        deduplicator.mark_processed("https://example.com/1")
        deduplicator.mark_processed("https://example.com/2")

        stats = deduplicator.get_stats()

        assert stats["urls_tracked"] == 2
        assert "state_file" in stats

    def test_context_manager(self, temp_state_file):
        """Test using deduplicator as context manager."""
        with URLDeduplicator(state_file=str(temp_state_file)) as dedup:
            dedup.mark_processed("https://example.com/1")

        # State should be saved after context exit
        with open(temp_state_file, "r") as f:
            saved_state = json.load(f)

        assert len(saved_state.get("processed_urls", {})) == 1

    def test_get_processed_urls_for_site(self, deduplicator):
        """Test getting processed URLs for a specific site."""
        deduplicator.mark_processed("https://site1.com/1", source="site1.com")
        deduplicator.mark_processed("https://site1.com/2", source="site1.com")
        deduplicator.mark_processed("https://site2.com/1", source="site2.com")

        site1_urls = deduplicator.get_processed_urls_for_site("site1.com")
        site2_urls = deduplicator.get_processed_urls_for_site("site2.com")

        assert len(site1_urls) == 2
        assert len(site2_urls) == 1
        assert "https://site1.com/1" in site1_urls

    def test_empty_state_file(self, temp_state_file):
        """Test handling of non-existent state file."""
        deduplicator = URLDeduplicator(state_file=str(temp_state_file))

        # Should work with empty state
        assert deduplicator.is_processed("https://example.com/1") is False
        assert deduplicator.get_stats()["urls_tracked"] == 0

    def test_corrupted_state_file(self, temp_state_file):
        """Test handling of corrupted state file."""
        # Write invalid JSON
        with open(temp_state_file, "w") as f:
            f.write("not valid json {{{")

        # Should handle gracefully and start with empty state
        deduplicator = URLDeduplicator(state_file=str(temp_state_file))
        assert deduplicator.get_stats()["urls_tracked"] == 0

    def test_metadata_storage(self, deduplicator):
        """Test storing additional metadata with URL."""
        url = "https://example.com/1"
        metadata = {"title": "Test Article", "saved_at": "2024-01-01"}

        deduplicator.mark_processed(url, source="example.com", metadata=metadata)
        deduplicator.save_state()

        # Check metadata was stored
        url_hash = deduplicator._url_hash(url)
        stored_data = deduplicator._state["processed_urls"][url_hash]

        assert stored_data["metadata"]["title"] == "Test Article"
