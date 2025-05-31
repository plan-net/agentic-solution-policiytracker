"""
Base storage interface for ETL pipeline.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

import structlog

logger = structlog.get_logger()


class BaseStorage(ABC):
    """Abstract base class for storage implementations."""

    @abstractmethod
    async def save_document(
        self, content: str, path: str, metadata: Optional[dict[str, Any]] = None
    ) -> bool:
        """Save a document to storage."""
        pass

    @abstractmethod
    async def document_exists(self, path: str) -> bool:
        """Check if a document already exists."""
        pass

    @abstractmethod
    async def list_documents(self, prefix: str = "") -> list[str]:
        """List all documents with optional prefix filter."""
        pass

    @abstractmethod
    async def get_document(self, path: str) -> Optional[str]:
        """Retrieve a document from storage."""
        pass

    @abstractmethod
    async def delete_document(self, path: str) -> bool:
        """Delete a document from storage."""
        pass

    @abstractmethod
    async def get_metadata(self, path: str) -> Optional[dict[str, Any]]:
        """Get metadata for a document."""
        pass
