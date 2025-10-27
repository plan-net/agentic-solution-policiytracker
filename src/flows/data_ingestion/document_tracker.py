"""
JSON-based document tracking system for Flow 1.

Tracks which documents have been processed to avoid duplicates
unless clear_data option is used.
"""

import json
import fcntl
import time
from datetime import datetime
from pathlib import Path

import structlog

logger = structlog.get_logger()


class DocumentTracker:
    """Simple JSON-based document tracking to avoid reprocessing."""

    def __init__(self, tracking_file: str = "data/processed_documents.json"):
        self.tracking_file = Path(tracking_file)
        self.processed_docs: dict[str, dict] = self._load_tracking()
        # Track which documents this instance has modified
        self._modified_docs: set[str] = set()

    def _load_tracking(self) -> dict[str, dict]:
        """Load tracking data from JSON file with file locking."""
        if not self.tracking_file.exists():
            logger.debug("No tracking file found, starting fresh", file=str(self.tracking_file))
            return {}

        max_retries = 3
        for attempt in range(max_retries):
            try:
                with open(self.tracking_file, "r", encoding="utf-8") as f:
                    # Acquire shared lock for reading
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                    try:
                        data = json.load(f)
                        logger.debug(
                            f"Loaded tracking for {len(data)} documents", file=str(self.tracking_file)
                        )
                        return data
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except (OSError, json.JSONDecodeError) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Failed to load tracking file (attempt {attempt + 1}/{max_retries}): {e}")
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                else:
                    logger.warning(f"Failed to load tracking file after {max_retries} attempts: {e}, starting fresh")
                    return {}
        return {}

    def _save_tracking(self) -> None:
        """Save tracking data to JSON file with file locking and atomic writes."""
        max_retries = 5
        for attempt in range(max_retries):
            lock_file = None
            try:
                # Ensure parent directory exists
                self.tracking_file.parent.mkdir(parents=True, exist_ok=True)

                # Use a lock file instead of locking the data file
                lock_file_path = self.tracking_file.with_suffix('.lock')
                lock_file = open(lock_file_path, 'w')

                # Acquire exclusive lock on lock file
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

                try:
                    # Read existing data
                    existing_data = {}
                    if self.tracking_file.exists():
                        try:
                            with open(self.tracking_file, "r", encoding="utf-8") as f:
                                existing_data = json.load(f)
                        except json.JSONDecodeError:
                            logger.warning("Corrupted tracking file, will overwrite")

                    # Smart merge: only overwrite documents that this instance modified
                    # This prevents Actor A from overwriting Actor B's failed documents
                    merged_data = existing_data.copy()
                    for doc_path in self._modified_docs:
                        if doc_path in self.processed_docs:
                            merged_data[doc_path] = self.processed_docs[doc_path]

                    # Use unique temp file with PID to avoid collisions
                    import os
                    temp_file = self.tracking_file.with_suffix(f'.tmp.{os.getpid()}')

                    # Write to temp file
                    with open(temp_file, "w", encoding="utf-8") as f:
                        json.dump(merged_data, f, indent=2, ensure_ascii=False)

                    # Atomic rename
                    temp_file.replace(self.tracking_file)

                    # Update our in-memory state with the full merged data
                    self.processed_docs = merged_data

                    logger.debug(f"Saved tracking for {len(self.processed_docs)} documents")
                    return

                finally:
                    # Release lock
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                    lock_file.close()
                    # Clean up lock file
                    try:
                        lock_file_path.unlink()
                    except:
                        pass

            except OSError as e:
                if lock_file:
                    try:
                        lock_file.close()
                    except:
                        pass

                if attempt < max_retries - 1:
                    logger.warning(f"Failed to save tracking file (attempt {attempt + 1}/{max_retries}): {e}")
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(f"Failed to save tracking file after {max_retries} attempts: {e}")

    def is_processed(self, doc_path: str) -> bool:
        """Check if document has been processed."""
        return str(doc_path) in self.processed_docs

    def mark_processed(
        self, doc_path: str, episode_id: str, entity_count: int = 0, relationship_count: int = 0
    ) -> None:
        """Mark document as processed with metadata."""
        doc_path_str = str(doc_path)
        self.processed_docs[doc_path_str] = {
            "episode_id": episode_id,
            "processed_at": datetime.now().isoformat(),
            "status": "completed",
            "entity_count": entity_count,
            "relationship_count": relationship_count,
        }
        self._modified_docs.add(doc_path_str)
        self._save_tracking()
        logger.debug(f"Marked as processed: {doc_path}")

    def mark_failed(self, doc_path: str, error: str) -> None:
        """Mark document as failed with error details."""
        doc_path_str = str(doc_path)
        self.processed_docs[doc_path_str] = {
            "processed_at": datetime.now().isoformat(),
            "status": "failed",
            "error": error,
        }
        self._modified_docs.add(doc_path_str)
        self._save_tracking()
        logger.warning(f"Marked as failed: {doc_path} - {error}")

    def clear_all(self) -> int:
        """Clear all tracking data and return count of cleared items."""
        count = len(self.processed_docs)
        self.processed_docs = {}
        self._save_tracking()
        logger.info(f"Cleared tracking for {count} documents")
        return count

    def get_stats(self) -> dict:
        """Get processing statistics."""
        completed = sum(
            1 for doc in self.processed_docs.values() if doc.get("status") == "completed"
        )
        failed = sum(1 for doc in self.processed_docs.values() if doc.get("status") == "failed")
        total_entities = sum(doc.get("entity_count", 0) for doc in self.processed_docs.values())
        total_relationships = sum(
            doc.get("relationship_count", 0) for doc in self.processed_docs.values()
        )

        return {
            "total_processed": len(self.processed_docs),
            "completed": completed,
            "failed": failed,
            "success_rate": (completed / len(self.processed_docs) * 100)
            if self.processed_docs
            else 0,
            "total_entities": total_entities,
            "total_relationships": total_relationships,
        }

    def get_failed_documents(self) -> list:
        """Get list of failed documents with error details."""
        return [
            {
                "path": path,
                "error": data.get("error", "Unknown error"),
                "processed_at": data.get("processed_at"),
            }
            for path, data in self.processed_docs.items()
            if data.get("status") == "failed"
        ]

    def get_processed_documents(self) -> list:
        """Get list of successfully processed documents."""
        return [
            {
                "path": path,
                "episode_id": data.get("episode_id"),
                "processed_at": data.get("processed_at"),
                "entity_count": data.get("entity_count", 0),
                "relationship_count": data.get("relationship_count", 0),
            }
            for path, data in self.processed_docs.items()
            if data.get("status") == "completed"
        ]
