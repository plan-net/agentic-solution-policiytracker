"""
Simple document processor using direct Graphiti API.

Focused on doing one thing well: processing documents into temporal knowledge graph.
"""

import asyncio
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

import structlog

# Configure logging for Ray environment
from src.flows.data_ingestion.logging_config import configure_logging
configure_logging()

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType

from src.flows.data_ingestion.document_tracker import DocumentTracker
from src.graphrag.schema_converter import (
    get_entity_types,
    get_edge_types,
    get_edge_type_map,
)

from src.graphrag.political_schema_v3 import (
    ENTITY_TYPE_REGISTRY,
    EDGE_TYPE_REGISTRY,
    EDGE_TYPE_MAP,
    SCHEMA_INFO,
)

logger = structlog.get_logger()

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
            """Initialize the Graphiti client connection with APISIX routing."""
            try:
                from src.flows.shared.apisix_llm_client import (
                    AgentContext,
                    create_graphiti_apisix_config,
                )

                # Create agent context for cost tracking
                context = AgentContext(
                    agent_type="kodosumi_flow",
                    agent_name="graphiti_document_processor",
                    flow_name="data_ingestion",
                )

                # Get APISIX-configured LLM client
                llm_client, note = create_graphiti_apisix_config(context)

                # Initialize Graphiti with APISIX routing
                self.graphiti_client = Graphiti(
                    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, llm_client=llm_client
                )
                await self.graphiti_client.build_indices_and_constraints()

                logger.info(
                    f"Actor {self.actor_id}: Graphiti client initialized with APISIX routing"
                )
                logger.warning(note)  # Log the Week 1 limitation
                return True
            except Exception as e:
                logger.error(f"Actor {self.actor_id}: Failed to initialize: {e}")
                return False

        def _read_document(self, doc_path: Path) -> str:
            """Read document content with encoding detection and preprocessing."""
            try:
                with open(doc_path, encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                logger.warning(
                    f"Actor {self.actor_id}: UTF-8 failed for {doc_path}, trying latin-1"
                )
                with open(doc_path, encoding="latin-1") as f:
                    content = f.read()

            # Apply preprocessing (link removal, deduplication, whitespace cleaning)
            from src.flows.data_ingestion.document_preprocessor import preprocess_document
            return preprocess_document(content, enable_link_removal=True)

        async def _process_chunked_document(self, doc_path: Path, chunks: List[Dict]) -> dict:
            """
            Process a document that has been chunked into multiple parts.

            Uses chain linking strategy: each chunk links to the immediately previous chunk.

            Args:
                doc_path: Path to the document being processed
                chunks: List of chunk dictionaries from HybridDocumentChunker

            Returns:
                Processing result dictionary with aggregated statistics
            """
            start_time = datetime.now()
            episode_uuids = []
            total_entities = 0
            total_relationships = 0
            chunk_results = []
            previous_episode_uuid = None

            logger.info(
                f"Actor {self.actor_id}: Processing chunked document: {doc_path.name} ({len(chunks)} chunks)"
            )

            for chunk in chunks:
                chunk_index = chunk["chunk_index"]
                chunk_text = chunk["text"]
                chunk_token_count = chunk["token_count"]

                try:
                    # Generate episode name for this chunk
                    episode_name = f"{generate_episode_name(doc_path, datetime.now())}_chunk_{chunk_index}"
                    source_description = f"Political document chunk {chunk_index + 1}/{chunk['total_chunks']}: {doc_path.name}"
                    reference_time = extract_document_date(chunk_text) or datetime.now()

                    # Chain linking: link to previous chunk if it exists
                    previous_episodes = [previous_episode_uuid] if previous_episode_uuid else None

                    # Process chunk through Graphiti
                    result = await self.graphiti_client.add_episode(
                        name=episode_name,
                        episode_body=chunk_text,
                        source_description=source_description,
                        reference_time=reference_time,
                        source=EpisodeType.text,
                        group_id=GROUP_ID,
                        entity_types=ENTITY_TYPE_REGISTRY,
                        edge_types=EDGE_TYPE_REGISTRY,
                        edge_type_map=EDGE_TYPE_MAP,
                        previous_episode_uuids=previous_episodes,
                    )

                    # Track this episode for chain linking
                    episode_uuid = result.episode.uuid if hasattr(result, "episode") else None
                    episode_uuids.append(episode_uuid)
                    previous_episode_uuid = episode_uuid

                    # Aggregate metrics
                    entity_count = len(result.nodes) if hasattr(result, "nodes") else 0
                    relationship_count = len(result.edges) if hasattr(result, "edges") else 0
                    total_entities += entity_count
                    total_relationships += relationship_count

                    chunk_results.append({
                        "chunk_index": chunk_index,
                        "episode_uuid": episode_uuid,
                        "entities": entity_count,
                        "relationships": relationship_count,
                        "tokens": chunk_token_count,
                        "boundary_type": chunk.get("boundary_type", "unknown"),
                    })

                    logger.debug(
                        f"Actor {self.actor_id}: Processed chunk {chunk_index + 1}/{len(chunks)}",
                        entities=entity_count,
                        relationships=relationship_count,
                        tokens=chunk_token_count,
                    )

                except Exception as e:
                    error_msg = f"Failed to process chunk {chunk_index}: {e}"
                    logger.error(f"Actor {self.actor_id}: {error_msg}")
                    chunk_results.append({
                        "chunk_index": chunk_index,
                        "error": str(e),
                        "tokens": chunk_token_count,
                    })

            # Calculate success rate
            successful_chunks = len([c for c in chunk_results if "error" not in c])
            success_rate = successful_chunks / len(chunks) if chunks else 0

            processing_time = (datetime.now() - start_time).total_seconds()

            # Track in document tracker (will add mark_processed_chunked method)
            if success_rate >= 0.5:  # At least 50% of chunks succeeded
                # For now, use the regular mark_processed with aggregated data
                self.tracker.mark_processed(
                    str(doc_path),
                    episode_uuids[0] if episode_uuids else None,
                    total_entities,
                    total_relationships,
                )
            else:
                error_msg = f"Chunked processing failed: only {successful_chunks}/{len(chunks)} chunks succeeded"
                self.tracker.mark_failed(str(doc_path), error_msg)

            logger.info(
                f"Actor {self.actor_id}: Completed chunked processing: {doc_path.name}",
                chunks=len(chunks),
                successful=successful_chunks,
                total_entities=total_entities,
                total_relationships=total_relationships,
                time=f"{processing_time:.2f}s",
            )

            return {
                "status": "success" if success_rate >= 0.5 else "partial_failure",
                "path": str(doc_path),
                "actor_id": self.actor_id,
                "episode_uuids": episode_uuids,
                "total_chunks": len(chunks),
                "successful_chunks": successful_chunks,
                "entity_count": total_entities,
                "relationship_count": total_relationships,
                "processing_time": processing_time,
                "chunk_results": chunk_results,
                "chunking_strategy": "hybrid",
            }

        async def process_document(self, doc_path_str: str) -> dict[str, any]:
            """Process a single document through Graphiti with robust error handling."""
            doc_path = Path(doc_path_str)
            start_time = datetime.now()

            try:
                # Check if already processed (unless clear mode)
                if not self.clear_mode and self.tracker.is_processed(str(doc_path)):
                    logger.info(f"Actor {self.actor_id}: Skipping already processed document: {doc_path}")
                    return {
                        "status": "skipped",
                        "reason": "already_processed",
                        "path": str(doc_path),
                        "actor_id": self.actor_id,
                        "processing_time": 0.0,
                    }

                # Read document content
                try:
                    content = self._read_document(doc_path)
                    if not content.strip():
                        raise ValueError("Document is empty")

                    logger.debug(f"Actor {self.actor_id}: Read document: {doc_path} ({len(content)} characters)")
                except Exception as e:
                    error_msg = f"Failed to read document: {e}"
                    self.tracker.mark_failed(str(doc_path), error_msg)
                    logger.error(f"Actor {self.actor_id}: {error_msg}")
                    return {
                        "status": "failed",
                        "error": error_msg,
                        "path": str(doc_path),
                        "actor_id": self.actor_id,
                        "processing_time": (datetime.now() - start_time).total_seconds(),
                    }

                # Chunk the document using hybrid strategy (ALWAYS chunk for consistency)
                from src.flows.data_ingestion.document_chunker import HybridDocumentChunker

                # Initialize chunker with default settings (120K tokens, 10% overlap)
                chunker = HybridDocumentChunker(max_tokens=120000, overlap_ratio=0.10)
                chunks = chunker.create_chunks(content)

                logger.info(
                    f"Actor {self.actor_id}: Chunked document {doc_path.name} into {len(chunks)} parts",
                    total_chunks=len(chunks),
                    boundary_types=[c.get("boundary_type") for c in chunks],
                )

                # Process all chunks (delegates to _process_chunked_document)
                try:
                    result = await self._process_chunked_document(doc_path, chunks)

                    # Return the result from chunked processing
                    processing_time = result.get("processing_time", 0.0)

                    logger.info(
                        f"Actor {self.actor_id}: Processed document: {doc_path.name}",
                        chunks=result.get("total_chunks", 0),
                        entities=result.get("entity_count", 0),
                        relationships=result.get("relationship_count", 0),
                        time=f"{processing_time:.2f}s",
                    )

                    # Return the chunked processing result
                    return result

                except Exception as e:
                    error_msg = f"Chunked processing failed: {e}"
                    self.tracker.mark_failed(str(doc_path), error_msg)
                    logger.error(f"Actor {self.actor_id}: {error_msg}")

                    return {
                        "status": "failed",
                        "error": error_msg,
                        "path": str(doc_path),
                        "actor_id": self.actor_id,
                        "processing_time": (datetime.now() - start_time).total_seconds(),
                    }

            except Exception as e:
                # Catch-all for unexpected errors
                error_msg = f"Unexpected error: {e}"
                logger.error(f"Actor {self.actor_id}: Unexpected error processing {doc_path}: {e}")
                self.tracker.mark_failed(str(doc_path), error_msg)
                return {
                    "status": "failed",
                    "error": error_msg,
                    "path": str(doc_path),
                    "actor_id": self.actor_id,
                    "processing_time": (datetime.now() - start_time).total_seconds(),
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
        """Read document content with encoding detection and preprocessing."""
        try:
            # Try UTF-8 first
            with open(doc_path, encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            # Fallback to latin-1 for legacy documents
            logger.warning(f"UTF-8 failed for {doc_path}, trying latin-1")
            with open(doc_path, encoding="latin-1") as f:
                content = f.read()

        # Apply preprocessing (link removal, deduplication, whitespace cleaning)
        from src.flows.data_ingestion.document_preprocessor import preprocess_document
        return preprocess_document(content, enable_link_removal=True)

    async def _process_chunked_document(self, doc_path: Path, chunks: List[Dict], graphiti_client: Graphiti) -> dict:
        """Process a document that has been chunked (same as DocumentProcessorActor version but adapted for SimpleDocumentProcessor)."""
        start_time = datetime.now()
        episode_uuids = []
        total_entities = 0
        total_relationships = 0
        chunk_results = []
        previous_episode_uuid = None

        logger.info(f"Processing chunked document: {doc_path.name} ({len(chunks)} chunks)")

        for chunk in chunks:
            chunk_index = chunk["chunk_index"]
            chunk_text = chunk["text"]
            chunk_token_count = chunk["token_count"]

            try:
                # Generate episode name for this chunk
                episode_name = f"{generate_episode_name(doc_path, datetime.now())}_chunk_{chunk_index}"
                doc_name = doc_path.name if hasattr(doc_path, "name") else Path(doc_path).name
                source_description = f"Political document chunk {chunk_index + 1}/{chunk['total_chunks']}: {doc_name}"

                # Extract reference time with detailed logging
                extracted_date = extract_document_date(chunk_text)
                reference_time = extracted_date or datetime.now()

                # DETAILED LOGGING: Capture what we're about to pass to Graphiti
                print(f"\n=== CHUNK PROCESSING DEBUG ===", flush=True)
                print(f"Chunk index: {chunk_index}", flush=True)
                print(f"Episode name: {episode_name}", flush=True)
                print(f"Extracted date: {extracted_date}", flush=True)
                print(f"Reference time: {reference_time}", flush=True)
                print(f"Reference time type: {type(reference_time).__name__}", flush=True)
                print(f"Reference time is None: {reference_time is None}", flush=True)
                print(f"Chunk text length: {len(chunk_text)}", flush=True)
                print(f"==========================\n", flush=True)

                logger.info(
                    "About to call add_episode for chunk",
                    chunk_index=chunk_index,
                    episode_name=episode_name,
                    extracted_date=extracted_date,
                    reference_time=reference_time,
                    reference_time_type=type(reference_time).__name__,
                    reference_time_is_none=(reference_time is None),
                    chunk_text_length=len(chunk_text),
                    chunk_text_preview=chunk_text[:200] if chunk_text else None,
                )

                # Chain linking: link to previous chunk if it exists
                previous_episodes = [previous_episode_uuid] if previous_episode_uuid else None

                # Process chunk through Graphiti
                logger.debug(
                    "Calling graphiti_client.add_episode",
                    reference_time_value=str(reference_time),
                    reference_time_isoformat=reference_time.isoformat() if reference_time else None,
                )

                result = await graphiti_client.add_episode(
                    name=episode_name,
                    episode_body=chunk_text,
                    source_description=source_description,
                    reference_time=reference_time,
                    source=EpisodeType.text,
                    group_id=GROUP_ID,
                    entity_types=ENTITY_TYPE_REGISTRY,
                    edge_types=EDGE_TYPE_REGISTRY,
                    edge_type_map=EDGE_TYPE_MAP,
                    previous_episode_uuids=previous_episodes,
                )

                # Track this episode for chain linking
                episode_uuid = result.episode.uuid if hasattr(result, "episode") else None
                episode_uuids.append(episode_uuid)
                previous_episode_uuid = episode_uuid

                # Aggregate metrics
                entity_count = len(result.nodes) if hasattr(result, "nodes") else 0
                relationship_count = len(result.edges) if hasattr(result, "edges") else 0
                total_entities += entity_count
                total_relationships += relationship_count

                chunk_results.append({
                    "chunk_index": chunk_index,
                    "episode_uuid": episode_uuid,
                    "entities": entity_count,
                    "relationships": relationship_count,
                    "tokens": chunk_token_count,
                    "boundary_type": chunk.get("boundary_type", "unknown"),
                })

                logger.debug(
                    f"Processed chunk {chunk_index + 1}/{len(chunks)}",
                    entities=entity_count,
                    relationships=relationship_count,
                    tokens=chunk_token_count,
                )

            except Exception as e:
                error_msg = f"Failed to process chunk {chunk_index}: {e}"

                # DETAILED ERROR LOGGING: Capture full exception details
                print(f"\n=== CHUNK PROCESSING ERROR ===", flush=True)
                print(f"Chunk index: {chunk_index}", flush=True)
                print(f"Error type: {type(e).__name__}", flush=True)
                print(f"Error message: {str(e)}", flush=True)
                print(f"Error repr: {repr(e)}", flush=True)
                print(f"Reference time: {reference_time if 'reference_time' in locals() else 'NOT_SET'}", flush=True)
                print(f"Extracted date: {extracted_date if 'extracted_date' in locals() else 'NOT_SET'}", flush=True)
                print(f"============================\n", flush=True)

                import traceback
                traceback.print_exc()

                logger.error(
                    "Chunk processing failed with exception",
                    chunk_index=chunk_index,
                    error_message=str(e),
                    error_type=type(e).__name__,
                    exception_details=repr(e),
                    reference_time_value=str(reference_time) if 'reference_time' in locals() else "NOT_SET",
                    extracted_date_value=str(extracted_date) if 'extracted_date' in locals() else "NOT_SET",
                    chunk_text_preview=chunk_text[:200] if chunk_text else None,
                    exc_info=True,  # Include full traceback
                )

                chunk_results.append({
                    "chunk_index": chunk_index,
                    "error": str(e),
                    "tokens": chunk_token_count,
                })

        # Calculate success rate
        successful_chunks = len([c for c in chunk_results if "error" not in c])
        success_rate = successful_chunks / len(chunks) if chunks else 0

        processing_time = (datetime.now() - start_time).total_seconds()

        # Track in document tracker
        if success_rate >= 0.5:  # At least 50% of chunks succeeded
            self.tracker.mark_processed(
                str(doc_path),
                episode_uuids[0] if episode_uuids else None,
                total_entities,
                total_relationships,
            )
            self.processing_stats["processed"] += 1
        else:
            error_msg = f"Chunked processing failed: only {successful_chunks}/{len(chunks)} chunks succeeded"
            self.tracker.mark_failed(str(doc_path), error_msg)
            self.processing_stats["failed"] += 1

        # Update stats
        self.processing_stats["total_entities"] += total_entities
        self.processing_stats["total_relationships"] += total_relationships
        self.processing_stats["processing_time"] += processing_time

        logger.info(
            f"Completed chunked processing: {doc_path.name}",
            chunks=len(chunks),
            successful=successful_chunks,
            total_entities=total_entities,
            total_relationships=total_relationships,
            time=f"{processing_time:.2f}s",
        )

        return {
            "status": "success" if success_rate >= 0.5 else "partial_failure",
            "path": str(doc_path),
            "episode_uuids": episode_uuids,
            "total_chunks": len(chunks),
            "successful_chunks": successful_chunks,
            "entity_count": total_entities,
            "relationship_count": total_relationships,
            "processing_time": processing_time,
            "chunk_results": chunk_results,
            "chunking_strategy": "hybrid",
        }

    async def process_document(self, doc_path: Path, graphiti_client: Graphiti) -> dict[str, any]:
        """Process a single document through Graphiti."""
        start_time = datetime.now()

        try:
            # Check if already processed (unless clear mode)
            if not self.clear_mode and self.tracker.is_processed(str(doc_path)):
                logger.info(f"Skipping already processed document: {doc_path}")
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

            # Chunk the document using hybrid strategy (ALWAYS chunk for consistency)
            from src.flows.data_ingestion.document_chunker import HybridDocumentChunker

            # Initialize chunker with default settings (120K tokens, 10% overlap)
            chunker = HybridDocumentChunker(max_tokens=120000, overlap_ratio=0.10)
            chunks = chunker.create_chunks(content)

            doc_name = doc_path.name if hasattr(doc_path, "name") else Path(doc_path).name
            logger.info(
                f"Chunked document {doc_name} into {len(chunks)} parts",
                total_chunks=len(chunks),
                boundary_types=[c.get("boundary_type") for c in chunks],
            )

            # Process all chunks (delegates to _process_chunked_document)
            try:
                result = await self._process_chunked_document(doc_path, chunks, graphiti_client)

                # Return the result from chunked processing
                doc_name = doc_path.name if hasattr(doc_path, "name") else Path(doc_path).name
                logger.info(
                    f"Processed document: {doc_name}",
                    chunks=result.get("total_chunks", 0),
                    entities=result.get("entity_count", 0),
                    relationships=result.get("relationship_count", 0),
                    time=f"{result.get('processing_time', 0.0):.2f}s",
                )

                return result

            except Exception as e:
                error_msg = f"Chunked processing failed: {e}"
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
            self.tracker.mark_failed(str(doc_path), error_msg)
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
            ray.init(log_to_driver=True)  # Enable driver logging to see worker logs

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
