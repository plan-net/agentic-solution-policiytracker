"""
Raw Document Tracker

Tracks processing status of raw documents (PDF, DOCX, PPT, PPTX, etc.)
to prevent duplicate processing.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import structlog

logger = structlog.get_logger()


class RawDocumentTracker:
    """Track processed raw documents."""

    def __init__(self, tracking_file: str = "data/raw_documents_processed.json"):
        self.tracking_file = Path(tracking_file)
        self.processed_docs: Dict[str, Dict] = {}
        self._load_tracking_data()

    def _load_tracking_data(self):
        """Load existing tracking data from JSON file."""
        if self.tracking_file.exists():
            try:
                with open(self.tracking_file, "r", encoding="utf-8") as f:
                    self.processed_docs = json.load(f)
                logger.info(
                    f"Loaded {len(self.processed_docs)} processed documents from tracker",
                    tracking_file=str(self.tracking_file),
                )
            except Exception as e:
                logger.warning(f"Could not load tracking file: {e}")
                self.processed_docs = {}
        else:
            logger.info("No tracking file found, starting fresh")
            self.processed_docs = {}

    def _save_tracking_data(self):
        """Save tracking data to JSON file."""
        try:
            # Ensure parent directory exists
            self.tracking_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.tracking_file, "w", encoding="utf-8") as f:
                json.dump(self.processed_docs, f, indent=2, ensure_ascii=False)

            logger.debug(f"Saved tracking data: {len(self.processed_docs)} documents")
        except Exception as e:
            logger.error(f"Failed to save tracking file: {e}")

    def is_processed(self, file_path: Path) -> bool:
        """
        Check if a file has been processed.

        Args:
            file_path: Path to the raw document file

        Returns:
            True if file has been processed, False otherwise
        """
        # Use full path as key for tracking
        file_key = str(file_path.resolve())
        return file_key in self.processed_docs

    def mark_processed(
        self,
        file_path: Path,
        output_md_path: Path,
        success: bool = True,
        error: Optional[str] = None,
    ):
        """
        Mark a file as processed.

        Args:
            file_path: Path to the raw document file
            output_md_path: Path to the generated markdown file
            success: Whether processing succeeded
            error: Error message if processing failed
        """
        file_key = str(file_path.resolve())

        self.processed_docs[file_key] = {
            "filename": file_path.name,
            "processed_at": datetime.now().isoformat(),
            "output_md_path": str(output_md_path),
            "success": success,
            "error": error,
        }

        self._save_tracking_data()

        logger.info(
            f"Marked document as processed",
            filename=file_path.name,
            success=success,
            output_md=output_md_path.name,
        )

    def get_unprocessed_documents(
        self, raw_docs_dir: str = "data/input/documents_raw"
    ) -> List[Path]:
        """
        Get list of unprocessed documents from raw documents directory.

        Args:
            raw_docs_dir: Directory containing raw documents

        Returns:
            List of Path objects for unprocessed documents
        """
        raw_docs_path = Path(raw_docs_dir)

        if not raw_docs_path.exists():
            logger.warning(f"Raw documents directory does not exist: {raw_docs_dir}")
            return []

        # Supported file extensions
        SUPPORTED_EXTENSIONS = {".pdf", ".doc", ".docx", ".ppt", ".pptx"}

        # Find all supported files
        all_files = []
        for ext in SUPPORTED_EXTENSIONS:
            # Support both lowercase and uppercase extensions
            all_files.extend(raw_docs_path.rglob(f"*{ext}"))
            all_files.extend(raw_docs_path.rglob(f"*{ext.upper()}"))

        logger.info(f"Found {len(all_files)} total files in {raw_docs_dir}")

        # Filter to only unprocessed files
        unprocessed = [f for f in all_files if not self.is_processed(f)]

        logger.info(f"Found {len(unprocessed)} unprocessed documents")

        return unprocessed

    def get_stats(self) -> Dict:
        """
        Get statistics about processed documents.

        Returns:
            Dict with processing statistics
        """
        total = len(self.processed_docs)
        successful = sum(1 for doc in self.processed_docs.values() if doc.get("success"))
        failed = total - successful

        return {
            "total_processed": total,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0,
        }
