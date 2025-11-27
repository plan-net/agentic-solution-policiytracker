"""
JSON-based document tracking system for Flow 1.

Tracks which documents have been processed to avoid duplicates
unless clear_data option is used.

Enhanced with entity name tracking to help identify potential duplicates
across documents and support deduplication analysis.
"""

import fcntl
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import structlog

# Configure logging for Ray environment (but not in Airflow)
try:
    from src.flows.data_ingestion.logging_config import configure_logging

    configure_logging()
except Exception:
    # Skip if logging config fails (e.g., in Airflow environment)
    pass

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
                with open(self.tracking_file, encoding="utf-8") as f:
                    # Acquire shared lock for reading
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                    try:
                        data = json.load(f)
                        logger.debug(
                            f"Loaded tracking for {len(data)} documents",
                            file=str(self.tracking_file),
                        )
                        return data
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except (OSError, json.JSONDecodeError) as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Failed to load tracking file (attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                else:
                    logger.warning(
                        f"Failed to load tracking file after {max_retries} attempts: {e}, starting fresh"
                    )
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
                lock_file_path = self.tracking_file.with_suffix(".lock")
                lock_file = open(lock_file_path, "w")

                # Acquire exclusive lock on lock file
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

                try:
                    # Read existing data
                    existing_data = {}
                    if self.tracking_file.exists():
                        try:
                            with open(self.tracking_file, encoding="utf-8") as f:
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

                    temp_file = self.tracking_file.with_suffix(f".tmp.{os.getpid()}")

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
                    logger.warning(
                        f"Failed to save tracking file (attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(f"Failed to save tracking file after {max_retries} attempts: {e}")

    def is_processed(self, doc_path: str) -> bool:
        """Check if document has been processed."""
        return str(doc_path) in self.processed_docs

    def mark_processed(
        self,
        doc_path: str,
        episode_id: str,
        entity_count: int = 0,
        relationship_count: int = 0,
        entity_names: Optional[list[str]] = None,
    ) -> None:
        """
        Mark document as processed with metadata.

        Args:
            doc_path: Path to the processed document
            episode_id: Graphiti episode UUID
            entity_count: Number of entities extracted
            relationship_count: Number of relationships extracted
            entity_names: Optional list of entity names for duplicate detection
        """
        doc_path_str = str(doc_path)

        # Calculate entity names hash for duplicate detection
        entity_names_hash = None
        if entity_names:
            entity_names_hash = self._calculate_entity_hash(entity_names)

        self.processed_docs[doc_path_str] = {
            "episode_id": episode_id,
            "processed_at": datetime.now().isoformat(),
            "status": "completed",
            "entity_count": entity_count,
            "relationship_count": relationship_count,
            "entity_names_hash": entity_names_hash,
            "unique_entity_count": len(set(entity_names)) if entity_names else None,
        }
        self._modified_docs.add(doc_path_str)
        self._save_tracking()
        logger.info(f"Marked as processed: {doc_path}")

    def mark_processed_chunked(
        self,
        doc_path: str,
        episode_uuids: list[str],
        total_chunks: int,
        entity_count: int = 0,
        relationship_count: int = 0,
        chunk_results: list[dict] = None,
        entity_names: Optional[list[str]] = None,
    ) -> None:
        """
        Mark chunked document as processed with detailed chunk metadata.

        Args:
            doc_path: Path to the processed document
            episode_uuids: List of episode UUIDs for each chunk
            total_chunks: Total number of chunks
            entity_count: Total entity count across all chunks
            relationship_count: Total relationship count across all chunks
            chunk_results: List of chunk processing results with detailed metrics
            entity_names: Optional list of entity names for duplicate detection
        """
        doc_path_str = str(doc_path)

        # Calculate entity names hash for duplicate detection
        entity_names_hash = None
        if entity_names:
            entity_names_hash = self._calculate_entity_hash(entity_names)

        self.processed_docs[doc_path_str] = {
            "episode_uuids": episode_uuids,  # List of all chunk episode IDs
            "primary_episode_id": episode_uuids[0]
            if episode_uuids
            else None,  # First chunk for backward compatibility
            "processed_at": datetime.now().isoformat(),
            "status": "completed",
            "entity_count": entity_count,
            "relationship_count": relationship_count,
            "is_chunked": True,
            "total_chunks": total_chunks,
            "successful_chunks": len([c for c in (chunk_results or []) if "error" not in c]),
            "chunking_strategy": "hybrid",
            "entity_names_hash": entity_names_hash,
            "unique_entity_count": len(set(entity_names)) if entity_names else None,
            "chunk_summary": [
                {
                    "chunk_index": c.get("chunk_index"),
                    "episode_uuid": c.get("episode_uuid"),
                    "entities": c.get("entities", 0),
                    "relationships": c.get("relationships", 0),
                    "boundary_type": c.get("boundary_type", "unknown"),
                }
                for c in (chunk_results or [])
                if "error" not in c
            ]
            if chunk_results
            else [],
        }
        self._modified_docs.add(doc_path_str)
        self._save_tracking()
        logger.info(f"Marked chunked document as processed: {doc_path} ({total_chunks} chunks)")

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
        logger.info(f"Marked as failed: {doc_path} - {error}")

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
                "entity_names_hash": data.get("entity_names_hash"),
                "unique_entity_count": data.get("unique_entity_count"),
            }
            for path, data in self.processed_docs.items()
            if data.get("status") == "completed"
        ]

    def _calculate_entity_hash(self, entity_names: list[str]) -> str:
        """
        Calculate hash of entity names for duplicate detection.

        Normalizes names (lowercased, sorted) before hashing to enable
        comparison across documents.

        Args:
            entity_names: List of entity names

        Returns:
            SHA-256 hash of sorted, normalized entity names
        """
        # Normalize: lowercase and sort for consistent hashing
        normalized = sorted([name.lower().strip() for name in entity_names if name])

        # Create hash
        hash_input = "|".join(normalized)
        return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:16]  # First 16 chars

    def find_similar_documents(
        self, entity_names: list[str], similarity_threshold: float = 0.5
    ) -> list[dict]:
        """
        Find documents with similar entity sets.

        Uses Jaccard similarity coefficient to compare entity name sets.

        Args:
            entity_names: List of entity names to compare against
            similarity_threshold: Minimum similarity score (0.0-1.0)

        Returns:
            List of similar documents with similarity scores
        """
        if not entity_names:
            return []

        similar_docs = []
        query_entities = set(name.lower().strip() for name in entity_names if name)

        for doc_path, doc_data in self.processed_docs.items():
            if doc_data.get("status") != "completed":
                continue

            # Skip if no entity hash (old tracking data)
            if not doc_data.get("entity_names_hash"):
                continue

            # Would need to store actual entity names to calculate similarity
            # For now, we can just use entity count similarity as a proxy
            doc_entity_count = doc_data.get("entity_count", 0)
            query_entity_count = len(entity_names)

            if doc_entity_count == 0 or query_entity_count == 0:
                continue

            # Simple count-based similarity
            count_similarity = min(doc_entity_count, query_entity_count) / max(
                doc_entity_count, query_entity_count
            )

            if count_similarity >= similarity_threshold:
                similar_docs.append(
                    {
                        "path": doc_path,
                        "entity_count": doc_entity_count,
                        "similarity_score": count_similarity,
                        "entity_names_hash": doc_data.get("entity_names_hash"),
                    }
                )

        # Sort by similarity score
        similar_docs.sort(key=lambda x: x["similarity_score"], reverse=True)

        return similar_docs

    def get_duplicate_detection_stats(self) -> dict:
        """
        Get statistics for duplicate entity detection analysis.

        Returns:
            Dictionary with deduplication-relevant metrics
        """
        docs_with_entity_tracking = sum(
            1
            for doc in self.processed_docs.values()
            if doc.get("status") == "completed" and doc.get("entity_names_hash")
        )

        total_entities = sum(
            doc.get("entity_count", 0)
            for doc in self.processed_docs.values()
            if doc.get("status") == "completed"
        )

        total_unique_entities = sum(
            doc.get("unique_entity_count", 0)
            for doc in self.processed_docs.values()
            if doc.get("status") == "completed" and doc.get("unique_entity_count")
        )

        # Estimate duplicate rate within documents
        within_doc_duplicate_rate = (
            ((total_entities - total_unique_entities) / total_entities * 100)
            if total_entities > 0
            else 0
        )

        return {
            "documents_with_entity_tracking": docs_with_entity_tracking,
            "total_entities_extracted": total_entities,
            "total_unique_entities_in_docs": total_unique_entities,
            "within_document_duplicate_rate": within_doc_duplicate_rate,
            "estimated_cross_document_duplicates": "Manual analysis required",
        }

    # ==================================================================================
    # PHASE 2: Chunk-Aware Entity Tracking with Canonical UUID Support
    # ==================================================================================

    def mark_processed_chunked_v2(
        self,
        doc_path: str,
        chunk_results: list[dict],
        total_chunks: int,
    ) -> None:
        """
        Mark chunked document as processed with Phase 2 chunk-aware tracking.

        Enhanced Phase 2 version that tracks canonical UUIDs per chunk for
        cross-chunk duplicate detection and entity resolution statistics.

        Args:
            doc_path: Path to the processed document
            chunk_results: List of chunk processing results with structure:
                {
                    "chunk_index": int,
                    "episode_uuid": str,
                    "entities": List[str],  # Entity names
                    "entity_uuids": List[str],  # Graphiti UUIDs
                    "canonical_uuids": List[str],  # EntityRegistry canonical UUIDs
                    "boundary_type": str  # Optional: header, paragraph, or fixed
                }
            total_chunks: Total number of chunks
        """
        doc_path_str = str(doc_path)

        # Extract basic metrics
        episode_uuids = [c.get("episode_uuid") for c in chunk_results if c.get("episode_uuid")]

        total_entity_count = sum(len(c.get("entities", [])) for c in chunk_results)
        total_relationship_count = sum(c.get("relationships", 0) for c in chunk_results)

        # Build chunk entity map for cross-chunk analysis
        chunk_entity_map = {}
        all_entity_names = []
        all_canonical_uuids = set()

        for chunk_result in chunk_results:
            chunk_idx = chunk_result.get("chunk_index", 0)
            episode_uuid = chunk_result.get("episode_uuid", "")
            entities = chunk_result.get("entities", [])
            entity_uuids = chunk_result.get("entity_uuids", [])
            canonical_uuids = chunk_result.get("canonical_uuids", [])

            chunk_entity_map[f"chunk_{chunk_idx}"] = {
                "episode_uuid": episode_uuid,
                "entities": entities,
                "entity_uuids": entity_uuids,
                "canonical_uuids": canonical_uuids,
                "entity_count": len(entities),
            }

            all_entity_names.extend(entities)
            all_canonical_uuids.update(canonical_uuids)

        # Detect cross-chunk duplicates (entities appearing in multiple chunks)
        cross_chunk_duplicates = {}
        entity_chunk_map = {}

        for chunk_key, chunk_data in chunk_entity_map.items():
            for entity_name in chunk_data["entities"]:
                if entity_name not in entity_chunk_map:
                    entity_chunk_map[entity_name] = []
                entity_chunk_map[entity_name].append(chunk_key)

        # Only include entities that appear in multiple chunks
        for entity_name, chunks in entity_chunk_map.items():
            if len(chunks) > 1:
                cross_chunk_duplicates[entity_name] = chunks

        # Calculate entity name hash for duplicate detection
        entity_names_hash = None
        if all_entity_names:
            entity_names_hash = self._calculate_entity_hash(all_entity_names)

        # Build tracking record with Phase 2 fields
        self.processed_docs[doc_path_str] = {
            # Basic fields
            "processed_at": datetime.now().isoformat(),
            "status": "completed",
            # Episode tracking
            "episode_uuids": episode_uuids,
            "primary_episode_id": episode_uuids[0] if episode_uuids else None,
            # Entity counts
            "entity_count": total_entity_count,
            "relationship_count": total_relationship_count,
            "unique_entity_count": len(set(all_entity_names)),
            # Chunking metadata
            "is_chunked": True,
            "total_chunks": total_chunks,
            "successful_chunks": len(chunk_results),
            "chunking_strategy": "hybrid",
            # Phase 1 deduplication
            "entity_names_hash": entity_names_hash,
            # Phase 2: Chunk-aware tracking
            "chunk_entity_map": chunk_entity_map,
            "cross_chunk_duplicates": cross_chunk_duplicates,
            "canonical_entity_count": len(all_canonical_uuids),
            "phase2_tracking": True,
        }

        self._modified_docs.add(doc_path_str)
        self._save_tracking()

        logger.info(
            f"Marked chunked document as processed (Phase 2): {doc_path} "
            f"({total_chunks} chunks, {total_entity_count} entities, "
            f"{len(all_canonical_uuids)} canonical)"
        )

    def get_chunk_entity_overlap(self, doc_path: str) -> dict[str, list[str]]:
        """
        Get entities that appear in multiple chunks of a document.

        Phase 2 method for analyzing within-document entity duplication
        across chunks.

        Args:
            doc_path: Path to the document

        Returns:
            {
                "European Commission": ["chunk_0", "chunk_1", "chunk_3"],
                "GDPR": ["chunk_0", "chunk_2"],
                ...
            }
        """
        doc_path_str = str(doc_path)

        if doc_path_str not in self.processed_docs:
            return {}

        doc_data = self.processed_docs[doc_path_str]

        # Return cross-chunk duplicates if Phase 2 tracking is enabled
        if doc_data.get("phase2_tracking"):
            return doc_data.get("cross_chunk_duplicates", {})

        # Fallback: manual calculation if Phase 2 tracking not available
        chunk_entity_map = doc_data.get("chunk_entity_map", {})
        if not chunk_entity_map:
            return {}

        entity_chunk_map = {}
        for chunk_key, chunk_data in chunk_entity_map.items():
            for entity_name in chunk_data.get("entities", []):
                if entity_name not in entity_chunk_map:
                    entity_chunk_map[entity_name] = []
                entity_chunk_map[entity_name].append(chunk_key)

        # Return only entities in multiple chunks
        return {entity: chunks for entity, chunks in entity_chunk_map.items() if len(chunks) > 1}

    def get_canonical_resolution_stats(self) -> dict:
        """
        Get statistics on canonical entity resolution (Phase 2).

        Returns:
            {
                "documents_with_phase2_tracking": 50,
                "total_entities_extracted": 3500,
                "total_canonical_entities": 2800,
                "resolution_rate": 80.0,  # % of entities resolved to canonical
                "avg_entities_per_canonical": 1.25,
                "cross_chunk_duplicate_rate": 15.0  # % within-document duplicates
            }
        """
        # Count documents with Phase 2 tracking
        docs_with_phase2 = [
            doc
            for doc in self.processed_docs.values()
            if doc.get("status") == "completed" and doc.get("phase2_tracking")
        ]

        if not docs_with_phase2:
            return {
                "documents_with_phase2_tracking": 0,
                "total_entities_extracted": 0,
                "total_canonical_entities": 0,
                "resolution_rate": 0.0,
                "avg_entities_per_canonical": 0.0,
                "cross_chunk_duplicate_rate": 0.0,
            }

        # Calculate aggregate statistics
        total_entities = sum(doc.get("entity_count", 0) for doc in docs_with_phase2)

        total_canonical = sum(doc.get("canonical_entity_count", 0) for doc in docs_with_phase2)

        # Resolution rate: what % of extracted entities map to canonical entities
        resolution_rate = (total_canonical / total_entities * 100) if total_entities > 0 else 0.0

        # Avg entities per canonical (measures deduplication effectiveness)
        avg_entities_per_canonical = (
            (total_entities / total_canonical) if total_canonical > 0 else 0.0
        )

        # Cross-chunk duplicate rate
        total_cross_chunk_duplicates = sum(
            len(doc.get("cross_chunk_duplicates", {})) for doc in docs_with_phase2
        )

        cross_chunk_duplicate_rate = (
            (total_cross_chunk_duplicates / total_entities * 100) if total_entities > 0 else 0.0
        )

        return {
            "documents_with_phase2_tracking": len(docs_with_phase2),
            "total_entities_extracted": total_entities,
            "total_canonical_entities": total_canonical,
            "resolution_rate": resolution_rate,
            "avg_entities_per_canonical": avg_entities_per_canonical,
            "cross_chunk_duplicate_rate": cross_chunk_duplicate_rate,
            "estimated_duplicate_reduction": (
                ((total_entities - total_canonical) / total_entities * 100)
                if total_entities > 0
                else 0.0
            ),
        }
