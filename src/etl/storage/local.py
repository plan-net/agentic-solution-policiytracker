"""
Local file system storage implementation.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
import structlog

from .base import BaseStorage

logger = structlog.get_logger()


class LocalStorage(BaseStorage):
    """Local file system storage implementation."""

    def __init__(self, base_path: str = "data/input/news"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.metadata_suffix = ".meta.json"
        logger.info(f"Initialized LocalStorage with base path: {self.base_path}")

    async def save_document(
        self, content: str, path: str, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Save a document to local storage (markdown only, no metadata files)."""
        try:
            file_path = self.base_path / path
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Save only the document (no separate metadata files)
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(content)

            # Note: Metadata is embedded in markdown frontmatter, no separate JSON files needed
            logger.info(f"Saved document to: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save document {path}: {e}")
            return False

    async def document_exists(self, path: str) -> bool:
        """Check if a document exists in local storage."""
        file_path = self.base_path / path
        return file_path.exists()

    async def list_documents(self, prefix: str = "") -> List[str]:
        """List all documents with optional prefix filter."""
        try:
            search_path = self.base_path / prefix if prefix else self.base_path

            # Find all markdown files
            md_files = list(search_path.rglob("*.md"))

            # Convert to relative paths
            relative_paths = [
                str(f.relative_to(self.base_path))
                for f in md_files
                if not f.name.endswith(self.metadata_suffix)
            ]

            logger.info(f"Found {len(relative_paths)} documents with prefix '{prefix}'")
            return sorted(relative_paths)

        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return []

    async def get_document(self, path: str) -> Optional[str]:
        """Retrieve a document from local storage."""
        try:
            file_path = self.base_path / path

            if not file_path.exists():
                logger.warning(f"Document not found: {path}")
                return None

            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()

            return content

        except Exception as e:
            logger.error(f"Failed to read document {path}: {e}")
            return None

    async def delete_document(self, path: str) -> bool:
        """Delete a document from local storage."""
        try:
            file_path = self.base_path / path
            meta_path = file_path.with_suffix(file_path.suffix + self.metadata_suffix)

            if file_path.exists():
                file_path.unlink()

            if meta_path.exists():
                meta_path.unlink()

            logger.info(f"Deleted document: {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete document {path}: {e}")
            return False

    async def get_metadata(self, path: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a document."""
        try:
            file_path = self.base_path / path
            meta_path = file_path.with_suffix(file_path.suffix + self.metadata_suffix)

            if not meta_path.exists():
                return None

            async with aiofiles.open(meta_path, "r", encoding="utf-8") as f:
                content = await f.read()
                metadata = json.loads(content)

            return metadata

        except Exception as e:
            logger.error(f"Failed to read metadata for {path}: {e}")
            return None
