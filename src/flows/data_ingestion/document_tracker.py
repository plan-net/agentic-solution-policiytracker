"""
JSON-based document tracking system for Flow 1.

Tracks which documents have been processed to avoid duplicates
unless clear_data option is used.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import structlog

logger = structlog.get_logger()


class DocumentTracker:
    """Simple JSON-based document tracking to avoid reprocessing."""
    
    def __init__(self, tracking_file: str = "data/processed_documents.json"):
        self.tracking_file = Path(tracking_file)
        self.processed_docs: Dict[str, dict] = self._load_tracking()
    
    def _load_tracking(self) -> Dict[str, dict]:
        """Load tracking data from JSON file."""
        if not self.tracking_file.exists():
            logger.info("No tracking file found, starting fresh", file=str(self.tracking_file))
            return {}
        
        try:
            with open(self.tracking_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Loaded tracking for {len(data)} documents", file=str(self.tracking_file))
                return data
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load tracking file: {e}, starting fresh")
            return {}
    
    def _save_tracking(self) -> None:
        """Save tracking data to JSON file."""
        try:
            # Ensure parent directory exists
            self.tracking_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.tracking_file, 'w', encoding='utf-8') as f:
                json.dump(self.processed_docs, f, indent=2, ensure_ascii=False)
                
            logger.debug(f"Saved tracking for {len(self.processed_docs)} documents")
        except IOError as e:
            logger.error(f"Failed to save tracking file: {e}")
    
    def is_processed(self, doc_path: str) -> bool:
        """Check if document has been processed."""
        return str(doc_path) in self.processed_docs
    
    def mark_processed(self, doc_path: str, episode_id: str, entity_count: int = 0, 
                      relationship_count: int = 0) -> None:
        """Mark document as processed with metadata."""
        self.processed_docs[str(doc_path)] = {
            "episode_id": episode_id,
            "processed_at": datetime.now().isoformat(),
            "status": "completed",
            "entity_count": entity_count,
            "relationship_count": relationship_count
        }
        self._save_tracking()
        logger.debug(f"Marked as processed: {doc_path}")
    
    def mark_failed(self, doc_path: str, error: str) -> None:
        """Mark document as failed with error details."""
        self.processed_docs[str(doc_path)] = {
            "processed_at": datetime.now().isoformat(),
            "status": "failed",
            "error": error
        }
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
        completed = sum(1 for doc in self.processed_docs.values() if doc.get("status") == "completed")
        failed = sum(1 for doc in self.processed_docs.values() if doc.get("status") == "failed")
        total_entities = sum(doc.get("entity_count", 0) for doc in self.processed_docs.values())
        total_relationships = sum(doc.get("relationship_count", 0) for doc in self.processed_docs.values())
        
        return {
            "total_processed": len(self.processed_docs),
            "completed": completed,
            "failed": failed,
            "success_rate": (completed / len(self.processed_docs) * 100) if self.processed_docs else 0,
            "total_entities": total_entities,
            "total_relationships": total_relationships
        }
    
    def get_failed_documents(self) -> list:
        """Get list of failed documents with error details."""
        return [
            {
                "path": path,
                "error": data.get("error", "Unknown error"),
                "processed_at": data.get("processed_at")
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
                "relationship_count": data.get("relationship_count", 0)
            }
            for path, data in self.processed_docs.items()
            if data.get("status") == "completed"
        ]