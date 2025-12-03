"""
URL deduplication with persistent state.

Provides URL tracking across DAG runs to avoid reprocessing
the same content.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger()


class URLDeduplicator:
    """Manages URL deduplication with persistent JSON state.

    Features:
    - Hash-based URL tracking
    - Persistent state across runs
    - Automatic cleanup of old entries
    - Per-site statistics
    """

    def __init__(
        self,
        state_file: str = "data/state/website_discovery_state.json",
        lookback_days: int = 90,
    ):
        """Initialize the URL deduplicator.

        Args:
            state_file: Path to the persistent state file
            lookback_days: Number of days to keep URLs in state
        """
        self.state_file = Path(state_file)
        self.lookback_days = lookback_days
        self._state: dict = {}
        self._modified = False

        # Ensure directory exists
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing state
        self._load_state()

        logger.info(
            "Initialized URLDeduplicator",
            state_file=str(self.state_file),
            lookback_days=lookback_days,
            urls_tracked=len(self._state.get("processed_urls", {})),
        )

    def _load_state(self) -> None:
        """Load state from disk."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    self._state = json.load(f)
                logger.debug(
                    "Loaded state from disk",
                    urls=len(self._state.get("processed_urls", {})),
                )
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load state, starting fresh", error=str(e))
                self._state = self._empty_state()
        else:
            self._state = self._empty_state()

    def _empty_state(self) -> dict:
        """Create empty state structure."""
        return {
            "processed_urls": {},  # url_hash -> {url, processed_at, source}
            "last_run": None,
            "total_discovered": 0,
            "total_saved": 0,
            "site_statistics": {},
        }

    def save_state(self) -> None:
        """Save state to disk."""
        if not self._modified:
            return

        try:
            with open(self.state_file, "w") as f:
                json.dump(self._state, f, indent=2, default=str)
            self._modified = False
            logger.debug(
                "Saved state to disk",
                urls=len(self._state.get("processed_urls", {})),
            )
        except IOError as e:
            logger.error(f"Failed to save state", error=str(e))

    def _url_hash(self, url: str) -> str:
        """Generate a hash for a URL.

        Normalizes URL before hashing to handle minor variations.
        """
        # Normalize URL
        normalized = url.lower().strip()
        if normalized.endswith("/"):
            normalized = normalized[:-1]

        # Remove common tracking parameters
        from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

        parsed = urlparse(normalized)
        params = parse_qs(parsed.query)

        # Remove known tracking parameters
        tracking_params = {"utm_source", "utm_medium", "utm_campaign", "ref", "fbclid"}
        filtered_params = {k: v for k, v in params.items() if k not in tracking_params}

        # Reconstruct URL
        clean_query = urlencode(filtered_params, doseq=True)
        clean_url = urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                clean_query,
                "",  # Remove fragment
            )
        )

        return hashlib.sha256(clean_url.encode()).hexdigest()[:16]

    def is_processed(self, url: str) -> bool:
        """Check if a URL has already been processed.

        Args:
            url: URL to check

        Returns:
            True if URL was previously processed
        """
        url_hash = self._url_hash(url)
        return url_hash in self._state.get("processed_urls", {})

    def mark_processed(
        self,
        url: str,
        source: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Mark a URL as processed.

        Args:
            url: URL to mark
            source: Source site domain
            metadata: Optional additional metadata
        """
        url_hash = self._url_hash(url)

        if "processed_urls" not in self._state:
            self._state["processed_urls"] = {}

        self._state["processed_urls"][url_hash] = {
            "url": url,
            "processed_at": datetime.now().isoformat(),
            "source": source,
            "metadata": metadata or {},
        }

        self._modified = True

    def filter_new_urls(self, urls: list[str]) -> list[str]:
        """Filter a list of URLs to only new (unprocessed) ones.

        Args:
            urls: List of URLs to filter

        Returns:
            List of URLs that haven't been processed
        """
        new_urls = [url for url in urls if not self.is_processed(url)]
        logger.info(
            f"Filtered URLs",
            total=len(urls),
            new=len(new_urls),
            duplicates=len(urls) - len(new_urls),
        )
        return new_urls

    def cleanup_old_entries(self, days: Optional[int] = None) -> int:
        """Remove entries older than specified days.

        Args:
            days: Number of days to keep (defaults to lookback_days)

        Returns:
            Number of entries removed
        """
        days = days or self.lookback_days
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()

        processed = self._state.get("processed_urls", {})
        old_hashes = []

        for url_hash, data in processed.items():
            processed_at = data.get("processed_at", "")
            if processed_at < cutoff_str:
                old_hashes.append(url_hash)

        for url_hash in old_hashes:
            del processed[url_hash]

        if old_hashes:
            self._modified = True
            logger.info(f"Cleaned up old entries", removed=len(old_hashes), days=days)

        return len(old_hashes)

    def update_run_stats(
        self,
        discovered: int,
        saved: int,
        site: Optional[str] = None,
    ) -> None:
        """Update statistics after a run.

        Args:
            discovered: Number of URLs discovered
            saved: Number of articles saved
            site: Site domain (for per-site stats)
        """
        self._state["last_run"] = datetime.now().isoformat()
        self._state["total_discovered"] = self._state.get("total_discovered", 0) + discovered
        self._state["total_saved"] = self._state.get("total_saved", 0) + saved

        if site:
            if "site_statistics" not in self._state:
                self._state["site_statistics"] = {}

            if site not in self._state["site_statistics"]:
                self._state["site_statistics"][site] = {
                    "total_discovered": 0,
                    "total_saved": 0,
                    "last_run": None,
                }

            self._state["site_statistics"][site]["total_discovered"] += discovered
            self._state["site_statistics"][site]["total_saved"] += saved
            self._state["site_statistics"][site]["last_run"] = datetime.now().isoformat()

        self._modified = True

    def get_stats(self) -> dict:
        """Get deduplication statistics."""
        return {
            "urls_tracked": len(self._state.get("processed_urls", {})),
            "last_run": self._state.get("last_run"),
            "total_discovered": self._state.get("total_discovered", 0),
            "total_saved": self._state.get("total_saved", 0),
            "site_statistics": self._state.get("site_statistics", {}),
            "state_file": str(self.state_file),
        }

    def get_processed_urls_for_site(self, site: str) -> list[str]:
        """Get list of processed URLs for a specific site.

        Args:
            site: Site domain to filter by

        Returns:
            List of processed URLs for the site
        """
        urls = []
        for data in self._state.get("processed_urls", {}).values():
            if data.get("source") == site:
                urls.append(data.get("url"))
        return urls

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save_state()
