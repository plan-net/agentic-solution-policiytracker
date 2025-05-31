"""
Simple document processor using direct Graphiti API.

Focused on doing one thing well: processing documents into temporal knowledge graph.
"""

import asyncio
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import structlog
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from pydantic import BaseModel, Field

from src.flows.data_ingestion.document_tracker import DocumentTracker

logger = structlog.get_logger()


# Political domain entity types for Graphiti
class Policy(BaseModel):
    """Government policies, laws, and regulations that create compliance obligations and affect companies."""

    policy_name: str = Field(
        ...,
        description="Official name of the policy, law, or regulation that companies must comply with",
    )
    jurisdiction: str | None = Field(
        None,
        description="Geographic region where this policy is enforced and companies must comply",
    )
    status: str | None = Field(
        None, description="Current legislative status: draft, enacted, implemented, or repealed"
    )


class Company(BaseModel):
    """Business entities that are subject to government regulations and policies."""

    company_name: str = Field(
        ...,
        description="Name of the company that may be regulated, fined, or required to comply with policies",
    )
    industry: str | None = Field(
        None, description="Business sector that determines which regulations apply to this company"
    )


class Politician(BaseModel):
    """Political figures who propose, support, or oppose policies and regulations."""

    politician_name: str = Field(
        ...,
        description="Name of the politician who influences, proposes, or votes on policies affecting companies",
    )
    position: str | None = Field(
        None,
        description="Official role that grants authority to create or influence regulatory policy",
    )


POLITICAL_ENTITY_TYPES = {
    "Policy": Policy,
    "Company": Company,
    "Politician": Politician,
}

# Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")
GROUP_ID = os.getenv("GRAPHITI_GROUP_ID", "political_monitoring_v2")


def generate_episode_name(doc_path, timestamp: datetime) -> str:
    """Generate consistent episode names for documents."""
    if isinstance(doc_path, str):
        doc_path = Path(doc_path)
    return f"political_doc_{doc_path.stem}_{timestamp.strftime('%Y%m%d_%H%M%S')}"


def extract_document_date(content: str) -> Optional[datetime]:
    """Extract document date from content using common patterns."""
    content_start = content[:1000]

    # ISO format: 2024-05-27, Published: 2024-05-27
    iso_pattern = r"(?:Published|Date|Updated|Effective):\s*(\d{4}-\d{2}-\d{2})"
    match = re.search(iso_pattern, content_start, re.IGNORECASE)
    if match:
        try:
            date_str = match.group(1)
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
            if 2020 <= parsed_date.year <= 2030:
                return parsed_date
        except ValueError:
            pass

    return None


# Only import ray if available
try:
    import ray

    RAY_AVAILABLE = True

    @ray.remote
    class DocumentProcessorActor:
        """Ray actor for processing documents with persistent Graphiti connection."""

        def __init__(self, actor_id: int, clear_mode: bool = False):
            self.actor_id = actor_id
            self.clear_mode = clear_mode
            self.graphiti_client = None
            self.tracker = DocumentTracker()

        async def initialize(self):
            """Initialize the Graphiti client connection."""
            try:
                self.graphiti_client = Graphiti(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
                await self.graphiti_client.build_indices_and_constraints()
                logger.info(f"Actor {self.actor_id}: Graphiti client initialized")
                return True
            except Exception as e:
                logger.error(f"Actor {self.actor_id}: Failed to initialize: {e}")
                return False

        def _read_document(self, doc_path: Path) -> str:
            """Read document content with encoding detection."""
            try:
                with open(doc_path, encoding="utf-8") as f:
                    return f.read()
            except UnicodeDecodeError:
                logger.warning(
                    f"Actor {self.actor_id}: UTF-8 failed for {doc_path}, trying latin-1"
                )
                with open(doc_path, encoding="latin-1") as f:
                    return f.read()

        async def process_document(self, doc_path_str: str) -> dict[str, any]:
            """Process a single document through Graphiti."""
            doc_path = Path(doc_path_str)
            start_time = datetime.now()

            try:
                # Check if already processed
                if not self.clear_mode and self.tracker.is_processed(doc_path):
                    return {
                        "status": "skipped",
                        "path": str(doc_path),
                        "actor_id": self.actor_id,
                        "processing_time": 0.0,
                        "entity_count": 0,
                        "relationship_count": 0,
                    }

                # Read and process document
                content = self._read_document(doc_path)
                if not content.strip():
                    raise ValueError("Document is empty")

                episode_name = generate_episode_name(doc_path, datetime.now())
                reference_time = extract_document_date(content) or datetime.now()

                # Process through Graphiti directly
                result = await self.graphiti_client.add_episode(
                    name=episode_name,
                    episode_body=content,
                    source_description=f"Political document: {doc_path.name}",
                    reference_time=reference_time,
                    source=EpisodeType.text,
                    group_id=GROUP_ID,
                    entity_types=POLITICAL_ENTITY_TYPES,
                )

                # Extract metrics
                entity_count = len(result.nodes) if hasattr(result, "nodes") else 0
                relationship_count = len(result.edges) if hasattr(result, "edges") else 0

                # Mark as processed
                episode_id = result.episode.uuid if hasattr(result, "episode") else None
                self.tracker.mark_processed(
                    doc_path,
                    {
                        "episode_id": episode_id,
                        "entity_count": entity_count,
                        "relationship_count": relationship_count,
                        "processed_at": datetime.now().isoformat(),
                        "actor_id": self.actor_id,
                    },
                )

                processing_time = (datetime.now() - start_time).total_seconds()

                logger.info(
                    f"Actor {self.actor_id}: Successfully processed {doc_path.name} "
                    f"({entity_count} entities, {relationship_count} relationships) "
                    f"in {processing_time:.2f}s"
                )

                return {
                    "status": "success",
                    "path": str(doc_path),
                    "actor_id": self.actor_id,
                    "episode_id": episode_id,
                    "entity_count": entity_count,
                    "relationship_count": relationship_count,
                    "processing_time": processing_time,
                }

            except Exception as e:
                processing_time = (datetime.now() - start_time).total_seconds()
                logger.error(f"Actor {self.actor_id}: Failed to process {doc_path.name}: {e}")

                return {
                    "status": "failed",
                    "path": str(doc_path),
                    "actor_id": self.actor_id,
                    "error": str(e),
                    "processing_time": processing_time,
                    "entity_count": 0,
                    "relationship_count": 0,
                }

        async def process_batch(self, doc_paths: list[str]) -> list[dict[str, any]]:
            """Process a batch of documents."""
            results = []
            for doc_path in doc_paths:
                result = await self.process_document(doc_path)
                results.append(result)
            return results

        async def cleanup(self):
            """Clean up resources."""
            if self.graphiti_client:
                try:
                    await self.graphiti_client.close()
                except Exception as e:
                    logger.warning(f"Actor {self.actor_id}: Cleanup warning: {e}")

except ImportError:
    RAY_AVAILABLE = False
    logger.warning("Ray not available, falling back to sequential processing")


class SimpleDocumentProcessor:
    """Lean document processor with direct Graphiti integration."""

    def __init__(self, tracker: DocumentTracker, clear_mode: bool = False):
        self.tracker = tracker
        self.clear_mode = clear_mode
        self.processing_stats = {
            "total_documents": 0,
            "processed": 0,
            "skipped": 0,
            "failed": 0,
            "total_entities": 0,
            "total_relationships": 0,
            "processing_time": 0.0,
        }

    def _read_document(self, doc_path: Path) -> str:
        """Read document content with encoding detection."""
        try:
            # Try UTF-8 first
            with open(doc_path, encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            # Fallback to latin-1 for legacy documents
            logger.warning(f"UTF-8 failed for {doc_path}, trying latin-1")
            with open(doc_path, encoding="latin-1") as f:
                return f.read()

    async def process_document(self, doc_path: Path, graphiti_client: Graphiti) -> dict[str, any]:
        """Process a single document through Graphiti."""
        start_time = datetime.now()

        try:
            # Check if already processed (unless clear mode)
            if not self.clear_mode and self.tracker.is_processed(str(doc_path)):
                logger.debug(f"Skipping already processed document: {doc_path}")
                self.processing_stats["skipped"] += 1
                return {
                    "status": "skipped",
                    "reason": "already_processed",
                    "path": str(doc_path),
                    "processing_time": 0.0,
                }

            # Read document content
            try:
                content = self._read_document(doc_path)
                if not content.strip():
                    raise ValueError("Document is empty")

                logger.debug(f"Read document: {doc_path} ({len(content)} characters)")
            except Exception as e:
                error_msg = f"Failed to read document: {e}"
                self.tracker.mark_failed(str(doc_path), error_msg)
                self.processing_stats["failed"] += 1
                return {
                    "status": "failed",
                    "error": error_msg,
                    "path": str(doc_path),
                    "processing_time": (datetime.now() - start_time).total_seconds(),
                }

            # Process through Graphiti
            episode_name = generate_episode_name(doc_path, datetime.now())
            # Handle both Path objects and strings for source description
            doc_name = doc_path.name if hasattr(doc_path, "name") else Path(doc_path).name
            source_description = f"Political document: {doc_name}"
            reference_time = extract_document_date(content) or datetime.now()

            try:
                result = await graphiti_client.add_episode(
                    name=episode_name,
                    episode_body=content,
                    source_description=source_description,
                    reference_time=reference_time,
                    source=EpisodeType.text,
                    group_id=GROUP_ID,
                    entity_types=POLITICAL_ENTITY_TYPES,
                )

                # Track successful processing
                self.tracker.mark_processed(
                    str(doc_path),
                    result["episode_id"],
                    result["entity_count"],
                    result["relationship_count"],
                )

                processing_time = (datetime.now() - start_time).total_seconds()
                self.processing_stats["processed"] += 1
                self.processing_stats["total_entities"] += result["entity_count"]
                self.processing_stats["total_relationships"] += result["relationship_count"]
                self.processing_stats["processing_time"] += processing_time

                doc_name = doc_path.name if hasattr(doc_path, "name") else Path(doc_path).name
                logger.info(
                    f"Processed document: {doc_name}",
                    entities=result["entity_count"],
                    relationships=result["relationship_count"],
                    time=f"{processing_time:.2f}s",
                )

                return {
                    "status": "success",
                    "path": str(doc_path),
                    "episode_id": result["episode_id"],
                    "entity_count": result["entity_count"],
                    "relationship_count": result["relationship_count"],
                    "processing_time": processing_time,
                    "content_length": len(content),
                    "entities": result.get("entities", []),
                    "document_date": reference_time.strftime("%Y-%m-%d")
                    if reference_time != datetime.now()
                    else None,
                    "content_preview": content[:200] + "..." if len(content) > 200 else content,
                }

            except Exception as e:
                error_msg = f"Graphiti processing failed: {e}"
                self.tracker.mark_failed(str(doc_path), error_msg)
                self.processing_stats["failed"] += 1

                return {
                    "status": "failed",
                    "error": error_msg,
                    "path": str(doc_path),
                    "processing_time": (datetime.now() - start_time).total_seconds(),
                }

        except Exception as e:
            # Catch-all for unexpected errors
            error_msg = f"Unexpected error: {e}"
            logger.error(f"Unexpected error processing {doc_path}: {e}")
            self.processing_stats["failed"] += 1
            return {
                "status": "failed",
                "error": error_msg,
                "path": str(doc_path),
                "processing_time": (datetime.now() - start_time).total_seconds(),
            }

    async def process_documents(
        self, source_path: Path, document_limit: int = 10, tracer=None
    ) -> list[dict[str, any]]:
        """Process multiple documents from source directory."""
        start_time = datetime.now()

        # Find documents
        if not source_path.exists():
            raise ValueError(f"Source path does not exist: {source_path}")

        if source_path.is_file():
            documents = [source_path]
        else:
            # Find all supported document files using same logic as find_documents
            documents = []
            for ext in get_supported_extensions():
                pattern = f"**/*{ext}"
                documents.extend(source_path.rglob(pattern))

        if not documents:
            raise ValueError(f"No documents found in: {source_path}")

        # Apply document limit
        documents = documents[:document_limit]
        self.processing_stats["total_documents"] = len(documents)

        logger.info(f"Processing {len(documents)} documents from {source_path}")

        if tracer:
            await tracer.markdown(
                f"""📄 **Processing {len(documents)} documents**

Found documents:
{chr(10).join([f"• `{doc.name}`" for doc in documents])}

---
"""
            )

        # Process documents with Ray actors
        results = await self._process_with_ray(documents, tracer)

        # Update stats and log failures
        for result in results:
            if result["status"] == "success":
                self.processing_stats["processed"] += 1
                self.processing_stats["total_entities"] += result["entity_count"]
                self.processing_stats["total_relationships"] += result["relationship_count"]
            elif result["status"] == "skipped":
                self.processing_stats["skipped"] += 1
            else:
                self.processing_stats["failed"] += 1
                # Log first few failures for debugging
                if self.processing_stats["failed"] <= 3:
                    logger.error(
                        f"Document processing failed: {result['path']} - {result.get('error', 'Unknown error')}"
                    )

        total_time = (datetime.now() - start_time).total_seconds()
        self.processing_stats["total_processing_time"] = total_time

        # Calculate performance metrics
        docs_per_minute = (len(documents) / total_time) * 60 if total_time > 0 else 0
        sequential_estimate = len(documents) * 12  # 12s per doc estimate
        speedup = sequential_estimate / total_time if total_time > 0 else 1

        # Final summary for tracer
        if tracer:
            await tracer.markdown(
                f"""---

🎉 **Ray parallel processing completed!**

**Performance:**
- 🚀 **{docs_per_minute:.1f} documents/minute** (Target: 20-40)
- ⏱️ **{total_time:.1f}s total time** vs {sequential_estimate:.0f}s sequential estimate
- 📈 **{speedup:.1f}x speedup** over sequential processing

**Summary:**
- ✅ **{self.processing_stats["processed"]} processed**
- ⏭️ **{self.processing_stats["skipped"]} skipped**
- ❌ **{self.processing_stats["failed"]} failed**
- 🧠 **{self.processing_stats["total_entities"]} total entities extracted**
- 🔗 **{self.processing_stats["total_relationships"]} total relationships extracted**

---
"""
            )

        logger.info(
            f"Ray parallel processing completed in {total_time:.2f}s",
            total=len(documents),
            processed=self.processing_stats["processed"],
            skipped=self.processing_stats["skipped"],
            failed=self.processing_stats["failed"],
            docs_per_minute=docs_per_minute,
            speedup=speedup,
        )

        return results

    async def _process_with_ray(self, documents: list[Path], tracer) -> list[dict[str, any]]:
        """Process documents using Ray actors."""
        # Initialize Ray if not already done
        if not ray.is_initialized():
            ray.init(log_to_driver=False)

        # Create Ray actors
        num_actors = min(3, len(documents))
        actors = [DocumentProcessorActor.remote(i, self.clear_mode) for i in range(num_actors)]

        # Initialize actors (properly await async methods)
        init_results = await asyncio.gather(*[actor.initialize.remote() for actor in actors])

        successful_actors = [actor for actor, success in zip(actors, init_results) if success]

        logger.info(f"Actor initialization results: {init_results}")
        logger.info(f"Successful actors: {len(successful_actors)}/{len(actors)}")

        if not successful_actors:
            raise RuntimeError("No actors could be initialized")

        if tracer:
            await tracer.markdown(
                f"🚀 **Using {len(successful_actors)} Ray actors** for parallel processing"
            )

        # Create balanced batches
        batch_size = max(1, len(documents) // len(successful_actors))
        batches = []
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            if batch:
                batches.append([str(doc) for doc in batch])

        # Process batches in parallel (properly await async methods)
        batch_tasks = []
        for actor, batch in zip(successful_actors, batches):
            if batch:
                task = actor.process_batch.remote(batch)
                batch_tasks.append(task)

        if tracer:
            await tracer.markdown("⏳ **Processing documents in parallel...**")

        # Wait for results (properly await async methods)
        batch_results = await asyncio.gather(*batch_tasks)

        # Flatten results
        results = []
        for batch_result in batch_results:
            results.extend(batch_result)

        # Cleanup actors (properly await async methods)
        await asyncio.gather(*[actor.cleanup.remote() for actor in successful_actors])

        return results

    def get_processing_stats(self) -> dict[str, any]:
        """Get detailed processing statistics."""
        stats = self.processing_stats.copy()

        if stats["processed"] > 0:
            stats["avg_processing_time"] = stats["processing_time"] / stats["processed"]
            stats["avg_entities_per_doc"] = stats["total_entities"] / stats["processed"]
            stats["avg_relationships_per_doc"] = stats["total_relationships"] / stats["processed"]
        else:
            stats["avg_processing_time"] = 0.0
            stats["avg_entities_per_doc"] = 0.0
            stats["avg_relationships_per_doc"] = 0.0

        if stats["total_documents"] > 0:
            stats["success_rate"] = (stats["processed"] / stats["total_documents"]) * 100
        else:
            stats["success_rate"] = 0.0

        return stats


def get_supported_extensions() -> list[str]:
    """Get list of supported document extensions."""
    return [".txt", ".md"]


def find_documents(source_path: Path, limit: Optional[int] = None) -> list[Path]:
    """Find all supported documents in source path."""
    if not source_path.exists():
        return []

    if source_path.is_file():
        if source_path.suffix.lower() in get_supported_extensions():
            return [source_path]
        return []

    documents = []
    for ext in get_supported_extensions():
        pattern = f"**/*{ext}"
        documents.extend(source_path.rglob(pattern))

    # Sort by name for consistent processing order
    documents.sort()

    if limit:
        documents = documents[:limit]

    return documents
