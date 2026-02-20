#!/usr/bin/env python3
"""
Single Document Processor for Graphiti Pipeline

Processes a single markdown file through the same Graphiti knowledge graph
pipeline used by the bulk auto delta flow (Flow 1B), without Ray overhead.

Usage:
    # Basic usage
    python scripts/process_single_document.py path/to/document.md

    # Force reprocess (ignore tracking)
    python scripts/process_single_document.py path/to/document.md --force

    # Verbose output with detailed entity/relationship info
    python scripts/process_single_document.py path/to/document.md --verbose

    # JSON output for programmatic use
    python scripts/process_single_document.py path/to/document.md --json
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()

import structlog

# Configure logging
from src.flows.data_ingestion.logging_config import configure_logging

configure_logging()

logger = structlog.get_logger()

# Import Graphiti components
from graphiti_core import Graphiti
from graphiti_core.driver.neo4j_driver import Neo4jDriver
from graphiti_core.nodes import EpisodeType

# Import project components
from src.config import graphrag_settings
from src.flows.data_ingestion.document_chunker import HybridDocumentChunker
from src.flows.data_ingestion.document_preprocessor import (
    preprocess_document,
    validate_document_quality,
)
from src.flows.data_ingestion.document_tracker import DocumentTracker
from src.flows.data_ingestion.entity_normalizer import EntityNormalizer
from src.graphrag.episode_embedding_manager import EpisodeEmbeddingManager
from src.graphrag.political_schema_v5 import (
    EDGE_TYPE_MAP_GENERAL as EDGE_TYPE_MAP,
    EDGE_TYPE_REGISTRY_GENERAL as EDGE_TYPE_REGISTRY,
    ENTITY_TYPE_REGISTRY_GENERAL as ENTITY_TYPE_REGISTRY,
)

# Configuration from environment
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "politicalmonitoring.v3")
GROUP_ID = os.getenv("GRAPHITI_GROUP_ID", "political_monitoring_v2")


def generate_episode_name(doc_path: Path, timestamp: datetime) -> str:
    """Generate consistent episode names for documents."""
    return f"political_doc_{doc_path.stem}_{timestamp.strftime('%Y%m%d_%H%M%S')}"


def extract_document_date(content: str) -> Optional[datetime]:
    """Extract document date from content using common patterns."""
    import re

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


def ensure_json_serializable(value):
    """Convert Neo4j types to JSON-serializable Python types."""
    if value is None:
        return None

    if hasattr(value, "__class__") and "DateTime" in value.__class__.__name__:
        return value.isoformat() if hasattr(value, "isoformat") else str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, list):
        return [ensure_json_serializable(item) for item in value]

    if isinstance(value, dict):
        return {k: ensure_json_serializable(v) for k, v in value.items()}

    if isinstance(value, set):
        return [ensure_json_serializable(item) for item in value]

    return value


class SingleDocumentProcessor:
    """
    Lightweight document processor for single file processing.

    Reuses components from DocumentProcessorActor without Ray overhead:
    - APISIX LLM client setup
    - HybridDocumentChunker
    - EpisodeEmbeddingManager
    - DocumentTracker
    """

    def __init__(
        self,
        force_reprocess: bool = False,
        tracking_file: str = "data/processed_documents.json",
        verbose: bool = False,
    ):
        """
        Initialize processor with optional force reprocess flag.

        Args:
            force_reprocess: If True, process even if already tracked
            tracking_file: Path to document tracking JSON file
            verbose: If True, print detailed progress
        """
        self.force_reprocess = force_reprocess
        self.verbose = verbose
        self.tracker = DocumentTracker(tracking_file=tracking_file)
        self.entity_normalizer = EntityNormalizer()
        self.graphiti_client = None
        self.episode_embedding_manager = None

    async def initialize(self) -> bool:
        """
        Initialize Graphiti client, Neo4j driver, and embedder.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            from src.flows.shared.apisix_llm_client import (
                AgentContext,
                create_apisix_graphiti_embedder,
                create_graphiti_llm_client,
            )

            # Create agent context for cost tracking
            context = AgentContext(
                agent_type="cli_script",
                agent_name="single_document_processor",
                flow_name="single_document",
            )

            # Get LLM client based on GRAPHITI_LLM_PROVIDER
            llm_client, note = create_graphiti_llm_client(context)

            # Get APISIX-configured embedder
            embedder = create_apisix_graphiti_embedder()

            # Create Neo4jDriver with the correct database name
            neo4j_driver = Neo4jDriver(
                uri=NEO4J_URI,
                user=NEO4J_USER,
                password=NEO4J_PASSWORD,
                database=NEO4J_DATABASE,
            )

            # Initialize Graphiti client
            self.graphiti_client = Graphiti(
                llm_client=llm_client,
                embedder=embedder,
                graph_driver=neo4j_driver,
            )

            await self.graphiti_client.build_indices_and_constraints()

            # Initialize episode embedding manager
            self.episode_embedding_manager = EpisodeEmbeddingManager(
                neo4j_uri=NEO4J_URI,
                neo4j_user=NEO4J_USER,
                neo4j_password=NEO4J_PASSWORD,
                neo4j_database=NEO4J_DATABASE,
            )

            if self.verbose:
                print(f"Initialized Graphiti client. {note}")
                print(f"Database: {NEO4J_DATABASE}")

            return True

        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            print(f"ERROR: Failed to initialize Graphiti client: {e}")
            print("\nTroubleshooting:")
            print("  1. Check that Neo4j is running: docker ps | grep neo4j")
            print("  2. Verify environment variables in .env file")
            print("  3. Check NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD")
            return False

    def _read_document(self, doc_path: Path) -> str:
        """Read document content with encoding detection and preprocessing."""
        try:
            with open(doc_path, encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            logger.warning(f"UTF-8 failed for {doc_path}, trying latin-1")
            with open(doc_path, encoding="latin-1") as f:
                content = f.read()

        # Preprocess content
        preprocessed = preprocess_document(content, enable_link_removal=True)

        # Apply entity name normalization
        normalized = self.entity_normalizer.normalize_text(preprocessed)

        return normalized

    async def process_document(self, doc_path_str: str) -> dict:
        """
        Process a single markdown file through Graphiti pipeline.

        Args:
            doc_path_str: Path to the markdown file

        Returns:
            Processing result dictionary
        """
        doc_path = Path(doc_path_str)
        start_time = datetime.now()

        # Validate file exists
        if not doc_path.exists():
            return {
                "status": "failed",
                "error": f"File not found: {doc_path}",
                "path": str(doc_path),
                "processing_time": 0.0,
            }

        # Validate file extension
        if doc_path.suffix.lower() not in [".md", ".txt"]:
            return {
                "status": "failed",
                "error": f"Unsupported file type: {doc_path.suffix}. Supported: .md, .txt",
                "path": str(doc_path),
                "processing_time": 0.0,
            }

        # Check if already processed
        if not self.force_reprocess and self.tracker.is_processed(str(doc_path)):
            return {
                "status": "skipped",
                "reason": "already_processed",
                "path": str(doc_path),
                "processing_time": 0.0,
            }

        try:
            # Read document content
            content = self._read_document(doc_path)
            if not content.strip():
                self.tracker.mark_failed(str(doc_path), "Document is empty")
                return {
                    "status": "failed",
                    "error": "Document is empty",
                    "path": str(doc_path),
                    "processing_time": (datetime.now() - start_time).total_seconds(),
                }

            # Validate document quality
            is_valid, quality_reason = validate_document_quality(content)
            if not is_valid:
                self.tracker.mark_failed(str(doc_path), f"Low quality: {quality_reason}")
                return {
                    "status": "skipped",
                    "reason": f"low_quality: {quality_reason}",
                    "path": str(doc_path),
                    "processing_time": (datetime.now() - start_time).total_seconds(),
                }

            # Chunk the document
            max_tokens = graphrag_settings.MAX_EPISODE_TOKENS
            overlap_ratio = graphrag_settings.CHUNK_OVERLAP_PERCENTAGE / 100
            chunker = HybridDocumentChunker(
                max_tokens=max_tokens,
                overlap_ratio=overlap_ratio,
                max_chunks_per_document=graphrag_settings.MAX_CHUNKS_PER_DOCUMENT,
                adaptive_chunk_size=graphrag_settings.ADAPTIVE_CHUNK_SIZE_ENABLED,
                max_adaptive_tokens=graphrag_settings.MAX_ADAPTIVE_TOKENS,
                chunk_limit_fallback=graphrag_settings.CHUNK_LIMIT_FALLBACK_STRATEGY,
            )
            chunks = chunker.create_chunks(content)

            if self.verbose:
                print(f"Chunked document into {len(chunks)} parts")

            # Process chunks
            episode_uuids = []
            total_entities = 0
            total_relationships = 0
            chunk_results = []
            previous_episode_uuid = None

            for chunk in chunks:
                chunk_index = chunk["chunk_index"]
                chunk_text = chunk["text"]
                chunk_token_count = chunk["token_count"]

                try:
                    # Generate episode name
                    episode_name = f"{generate_episode_name(doc_path, datetime.now())}_chunk_{chunk_index}"
                    source_description = f"Political document chunk {chunk_index + 1}/{chunk['total_chunks']}: {doc_path.name}"
                    reference_time = extract_document_date(chunk_text) or datetime.now()

                    # Chain linking
                    previous_episodes = [previous_episode_uuid] if previous_episode_uuid else None

                    if self.verbose:
                        print(f"  Processing chunk {chunk_index + 1}/{len(chunks)}...")

                    # Process through Graphiti
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

                    # Track episode UUID
                    episode_uuid = ensure_json_serializable(
                        result.episode.uuid if hasattr(result, "episode") else None
                    )
                    episode_uuids.append(episode_uuid)
                    previous_episode_uuid = episode_uuid

                    # Generate content embedding
                    if episode_uuid and self.episode_embedding_manager:
                        try:
                            await self.episode_embedding_manager.add_content_embedding(
                                episode_uuid=episode_uuid,
                                content=chunk_text,
                            )
                        except Exception as emb_error:
                            logger.warning(f"Failed to generate embedding: {emb_error}")

                    # Aggregate metrics
                    entity_count = len(result.nodes) if hasattr(result, "nodes") else 0
                    relationship_count = len(result.edges) if hasattr(result, "edges") else 0
                    total_entities += entity_count
                    total_relationships += relationship_count

                    # Extract entity names
                    entity_names = (
                        [ensure_json_serializable(node.name) for node in result.nodes]
                        if hasattr(result, "nodes")
                        else []
                    )
                    entity_uuids = (
                        [ensure_json_serializable(node.uuid) for node in result.nodes]
                        if hasattr(result, "nodes")
                        else []
                    )

                    chunk_results.append({
                        "chunk_index": chunk_index,
                        "episode_uuid": episode_uuid,
                        "entities": entity_names,
                        "entity_uuids": entity_uuids,
                        "canonical_uuids": entity_uuids,  # Same as entity_uuids without deduplication
                        "entity_count": entity_count,
                        "relationships": relationship_count,
                        "tokens": chunk_token_count,
                        "boundary_type": chunk.get("boundary_type", "unknown"),
                    })

                    if self.verbose:
                        print(f"    {chunk_token_count} tokens - {entity_count} entities, {relationship_count} relationships")

                except Exception as e:
                    logger.error(f"Failed to process chunk {chunk_index}: {e}")
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
            if success_rate >= 0.5:
                self.tracker.mark_processed_chunked_v2(
                    str(doc_path),
                    chunk_results,
                    len(chunks),
                )
            else:
                error_msg = f"Processing failed: only {successful_chunks}/{len(chunks)} chunks succeeded"
                self.tracker.mark_failed(str(doc_path), error_msg)

            return {
                "status": "completed" if success_rate >= 0.5 else "failed",
                "path": str(doc_path),
                "episode_uuids": episode_uuids,
                "total_chunks": len(chunks),
                "successful_chunks": successful_chunks,
                "entities_extracted": total_entities,
                "relationships_extracted": total_relationships,
                "processing_time": processing_time,
                "chunk_results": chunk_results,
            }

        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.error(f"Error processing {doc_path}: {e}")
            self.tracker.mark_failed(str(doc_path), error_msg)
            return {
                "status": "failed",
                "error": error_msg,
                "path": str(doc_path),
                "processing_time": (datetime.now() - start_time).total_seconds(),
            }

    async def cleanup(self):
        """Clean up Graphiti client and Neo4j connections."""
        if self.graphiti_client:
            try:
                await self.graphiti_client.close()
            except Exception as e:
                logger.warning(f"Cleanup warning: {e}")

        if self.episode_embedding_manager:
            try:
                await self.episode_embedding_manager.close()
            except Exception as e:
                logger.warning(f"Embedding manager cleanup warning: {e}")


def print_results(result: dict, verbose: bool = False, json_output: bool = False):
    """Format and print processing results."""
    if json_output:
        # Clean output for JSON
        output = {
            "status": result.get("status"),
            "path": result.get("path"),
            "processing_time": result.get("processing_time", 0),
            "total_chunks": result.get("total_chunks", 0),
            "successful_chunks": result.get("successful_chunks", 0),
            "entities_extracted": result.get("entities_extracted", 0),
            "relationships_extracted": result.get("relationships_extracted", 0),
            "episode_uuids": result.get("episode_uuids", []),
        }
        if result.get("error"):
            output["error"] = result["error"]
        if result.get("reason"):
            output["reason"] = result["reason"]
        if verbose and result.get("chunk_results"):
            output["chunk_results"] = result["chunk_results"]
        print(json.dumps(output, indent=2))
        return

    # Standard output
    print("\n" + "=" * 50)
    print("PROCESSING RESULT")
    print("=" * 50)

    status = result.get("status", "unknown")
    status_emoji = {"completed": "SUCCESS", "skipped": "SKIPPED", "failed": "FAILED"}.get(
        status, "UNKNOWN"
    )

    print(f"Status: {status_emoji}")
    print(f"File: {result.get('path', 'unknown')}")

    if result.get("reason"):
        print(f"Reason: {result['reason']}")

    if result.get("error"):
        print(f"Error: {result['error']}")

    if status == "completed":
        print(f"Processing time: {result.get('processing_time', 0):.2f}s")
        print(f"Total chunks: {result.get('total_chunks', 0)}")
        print(f"Successful chunks: {result.get('successful_chunks', 0)}")
        print(f"Entities extracted: {result.get('entities_extracted', 0)}")
        print(f"Relationships extracted: {result.get('relationships_extracted', 0)}")

        episode_uuids = result.get("episode_uuids", [])
        if episode_uuids:
            print(f"Episode UUIDs ({len(episode_uuids)}):")
            for uuid in episode_uuids[:5]:  # Show first 5
                print(f"  - {uuid}")
            if len(episode_uuids) > 5:
                print(f"  ... and {len(episode_uuids) - 5} more")

        if verbose and result.get("chunk_results"):
            print("\nChunk Details:")
            for chunk in result["chunk_results"]:
                if "error" in chunk:
                    print(f"  Chunk {chunk['chunk_index']}: ERROR - {chunk['error']}")
                else:
                    entities = chunk.get("entities", [])
                    print(
                        f"  Chunk {chunk['chunk_index']}: "
                        f"{chunk.get('tokens', 0)} tokens, "
                        f"{chunk.get('entity_count', 0)} entities, "
                        f"{chunk.get('relationships', 0)} relationships"
                    )
                    if verbose and entities:
                        for entity in entities[:5]:
                            print(f"    - {entity}")
                        if len(entities) > 5:
                            print(f"    ... and {len(entities) - 5} more")

    print("=" * 50)


async def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Process a single markdown file through the Graphiti knowledge graph pipeline"
    )
    parser.add_argument("file_path", type=str, help="Path to the markdown file to process")
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force reprocess even if already processed",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed entity and relationship information",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON (for programmatic use)",
    )
    parser.add_argument(
        "--tracking-file",
        type=str,
        default="data/processed_documents.json",
        help="Path to document tracking file (default: data/processed_documents.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate input and show what would be processed without actually processing",
    )

    args = parser.parse_args()

    # Validate file path
    file_path = Path(args.file_path)
    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        sys.exit(1)

    if file_path.suffix.lower() not in [".md", ".txt"]:
        print(f"ERROR: Unsupported file type: {file_path.suffix}")
        print("Supported types: .md, .txt")
        sys.exit(1)

    # Dry run mode
    if args.dry_run:
        print("DRY RUN MODE")
        print("=" * 50)
        print(f"File: {file_path}")
        print(f"Size: {file_path.stat().st_size} bytes")
        print(f"Force reprocess: {args.force}")
        print(f"Tracking file: {args.tracking_file}")

        tracker = DocumentTracker(tracking_file=args.tracking_file)
        is_processed = tracker.is_processed(str(file_path))
        print(f"Already processed: {is_processed}")

        if is_processed and not args.force:
            print("\nWould be SKIPPED (use --force to reprocess)")
        else:
            print("\nWould be PROCESSED")
        return

    # Print header (unless JSON output)
    if not args.json:
        print("=" * 50)
        print("Single Document Processor")
        print("=" * 50)
        print(f"File: {file_path}")
        print(f"Database: {NEO4J_DATABASE}")
        print("=" * 50)

    # Create processor
    processor = SingleDocumentProcessor(
        force_reprocess=args.force,
        tracking_file=args.tracking_file,
        verbose=args.verbose,
    )

    # Initialize
    if not args.json:
        print("\nInitializing Graphiti client...")

    if not await processor.initialize():
        sys.exit(1)

    try:
        # Process document
        if not args.json:
            print("\nProcessing document...")

        result = await processor.process_document(str(file_path))

        # Print results
        print_results(result, verbose=args.verbose, json_output=args.json)

        # Exit code based on status
        if result.get("status") == "failed":
            sys.exit(1)

    finally:
        await processor.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
