"""
Bulk Auto-Delta Document Processor

Automatically detects unprocessed documents by comparing processed_documents.json
with current folder state, then processes them using the same pipeline as Flow 1.
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

import structlog
from kodosumi.core import Tracer

# Configure logging for Ray environment
from src.flows.data_ingestion.logging_config import configure_logging

configure_logging()

logger = structlog.get_logger()

# Configuration from environment variables
FLOW1B_MAX_DOCUMENTS = int(os.getenv("FLOW1B_MAX_DOCUMENTS", "500"))
FLOW1B_NUM_ACTORS = int(os.getenv("FLOW1B_NUM_ACTORS", "4"))

# Import Ray for parallel processing
try:
    import ray

    RAY_AVAILABLE = True
except ImportError:
    RAY_AVAILABLE = False
    logger.warning("Ray not available - bulk processing will be limited")


def distribute_documents_to_actors(documents: list, num_actors: int) -> list[list]:
    """
    Distribute documents evenly across actors, ensuring all documents are processed.

    Uses a balanced distribution algorithm that ensures:
    - All documents are assigned to an actor
    - Load is balanced as evenly as possible
    - No documents are skipped due to remainder in division

    Example:
        5 documents, 2 actors -> [[doc0, doc1, doc2], [doc3, doc4]]
        7 documents, 3 actors -> [[doc0, doc1, doc2], [doc3, doc4], [doc5, doc6]]
    """
    if num_actors <= 0 or not documents:
        return []

    base_size = len(documents) // num_actors
    remainder = len(documents) % num_actors

    batches = []
    start = 0
    for i in range(num_actors):
        # First 'remainder' actors get one extra document
        batch_size = base_size + (1 if i < remainder else 0)
        end = start + batch_size
        if start < len(documents):  # Ensure we don't go past document list
            batches.append(documents[start:end])
        start = end

    return batches


def get_unprocessed_documents(
    base_path: str = "data/input", tracking_file: str = "data/processed_documents.json"
) -> list[str]:
    """
    Get list of documents that haven't been processed.

    Compares the tracking file with current folder state to find the delta.
    """
    tracking_path = Path(tracking_file)
    processed_docs = {}

    # Load processed documents
    if tracking_path.exists():
        try:
            with open(tracking_path, encoding="utf-8") as f:
                processed_docs = json.load(f)
            logger.info(f"Loaded {len(processed_docs)} processed documents from tracker")
        except Exception as e:
            logger.warning(f"Could not load tracking file: {e}")
            processed_docs = {}
    else:
        logger.info("No tracking file found, treating all documents as unprocessed")

    # Get all markdown documents from news, policy, and documents_md directories
    all_docs = []
    base_paths = [
        Path(base_path) / "news",
        Path(base_path) / "policy",
        Path(base_path) / "documents_md",
    ]

    for search_path in base_paths:
        if not search_path.exists():
            logger.warning(f"Base path {search_path} does not exist, skipping")
            continue

        # Find all markdown files in this directory
        for md_file in search_path.rglob("*.md"):
            try:
                # Get path as stored in tracking file (full path from project root)
                # Tracking file stores paths like: data/input/policy/2025-05/file.md
                full_relative_path = str(md_file)
                all_docs.append(full_relative_path)
            except ValueError:
                # Skip if file is not under base_path
                continue

    logger.info(f"Found {len(all_docs)} total documents in storage")

    # Filter to only unprocessed documents
    unprocessed = [doc for doc in all_docs if doc not in processed_docs]

    logger.info(f"Found {len(unprocessed)} unprocessed documents")
    return unprocessed


async def execute_bulk_auto_processing(inputs: dict, tracer: Tracer):
    """
    Execute bulk auto-delta document processing.

    Uses parallel Ray actors for fast processing and the same report format as Flow 1.
    """
    from kodosumi import core

    from src.flows.data_ingestion.document_tracker import DocumentTracker
    from src.flows.data_ingestion.report_generator import IngestionReportGenerator

    job_name = inputs.get("job_name", "Bulk Auto-Delta Processing")
    max_documents = inputs.get("max_documents", FLOW1B_MAX_DOCUMENTS)

    start_time = datetime.now()

    logger.info(
        "Starting bulk auto-delta processing",
        job_name=job_name,
        max_documents=max_documents,
        num_actors=FLOW1B_NUM_ACTORS,
    )

    # Step 1: Auto-detect unprocessed documents
    await tracer.markdown(
        f"""
# 📄 {job_name} - Starting

**Configuration:**
- Mode: Auto-Delta Detection
- Document Limit: {max_documents} per run
- Parallel Actors: {FLOW1B_NUM_ACTORS}
- Clear Data: ❌ No (preserves existing graph)

---
"""
    )

    await tracer.markdown("## 📊 Document Discovery\n\n")
    await tracer.markdown("🔍 Scanning for unprocessed documents...\n\n")

    try:
        unprocessed_docs = get_unprocessed_documents()

        if not unprocessed_docs:
            await tracer.markdown("✅ No unprocessed documents found.\n\n")
            return core.response.Markdown(
                f"""# {job_name} - Complete

## No Unprocessed Documents

All documents are up to date. The knowledge graph is current.

**Job Name**: {job_name}
**Execution Time**: {(datetime.now() - start_time).total_seconds():.1f}s
"""
            )

        # Apply safety limit
        total_unprocessed = len(unprocessed_docs)
        if total_unprocessed > max_documents:
            await tracer.markdown(
                f"⚠️ **Safety Limit Applied**: Found {total_unprocessed} unprocessed documents, "
                f"but will process only first {max_documents} documents.\n\n"
            )
            unprocessed_docs = unprocessed_docs[:max_documents]
        else:
            await tracer.markdown(
                f"✅ Found {total_unprocessed} unprocessed documents to process.\n\n"
            )

        # Display documents to be processed
        await tracer.markdown(
            f"""
Found **{len(unprocessed_docs)}** documents to process:
{chr(10).join(f"- {Path(doc).name}" for doc in unprocessed_docs[:10])}
{'...' if len(unprocessed_docs) > 10 else ''}

---
"""
        )

        # Step 2: Process documents using Flow 1's processor
        await tracer.markdown("## 🚀 Processing Documents\n\n")
        await tracer.markdown(f"Processing {len(unprocessed_docs)} documents...\n\n")

        # Initialize components (same as Flow 1)
        from src.flows.data_ingestion.document_processor import DocumentProcessorActor

        tracker = DocumentTracker()

        # Initialize Ray if not already done
        if not ray.is_initialized():
            ray.init(log_to_driver=True)

        # Create Ray actors for parallel processing
        num_actors = min(FLOW1B_NUM_ACTORS, len(unprocessed_docs))
        actors = [DocumentProcessorActor.remote(i, clear_mode=False) for i in range(num_actors)]

        # Initialize actors
        init_results = await asyncio.gather(*[actor.initialize.remote() for actor in actors])
        successful_actors = [actor for actor, success in zip(actors, init_results) if success]

        logger.info(f"Actor initialization: {len(successful_actors)}/{num_actors} successful")

        if not successful_actors:
            raise RuntimeError("No actors could be initialized for parallel processing")

        await tracer.markdown(
            f"🚀 **Using {len(successful_actors)} Ray actors** for parallel processing\n\n"
        )

        # Create balanced batches using proper distribution algorithm
        unprocessed_docs_str = [str(doc) for doc in unprocessed_docs]
        batches = distribute_documents_to_actors(unprocessed_docs_str, len(successful_actors))

        # Verify all documents are assigned
        total_assigned = sum(len(batch) for batch in batches)
        logger.info(
            f"Document distribution: {len(unprocessed_docs)} files → {len(batches)} batches "
            f"(assigned: {total_assigned}, actors: {len(successful_actors)})"
        )

        # Display batch assignments
        await tracer.markdown("📋 **Batch Assignments:**\n\n")
        for i, (actor, batch) in enumerate(zip(successful_actors, batches), 1):
            doc_names = [Path(doc).name for doc in batch[:3]]
            remaining = len(batch) - 3
            doc_list = ", ".join(doc_names)
            if remaining > 0:
                doc_list += f" ... and {remaining} more"
            await tracer.markdown(f"- **Actor {i}**: {len(batch)} documents ({doc_list})\n")
        await tracer.markdown("\n")

        # Process batches in parallel
        batch_refs = []
        actor_info = []
        for i, (actor, batch) in enumerate(zip(successful_actors, batches), 1):
            if batch:
                ref = actor.process_batch.remote(batch)
                batch_refs.append(ref)
                actor_info.append({"actor_id": i, "batch_size": len(batch), "batch": batch})

        await tracer.markdown("⏳ **Processing documents in parallel...**\n\n")

        # Live progress tracking with periodic polling
        completed_actors = 0
        pending_refs = batch_refs.copy()
        last_progress_update = {}  # Track last shown progress per actor
        poll_count = 0

        while pending_refs:
            poll_count += 1

            # Poll actor progress
            for i, actor in enumerate(successful_actors):
                if i < len(actor_info):
                    try:
                        progress = ray.get(actor.get_progress.remote(), timeout=2)
                        actor_id = actor_info[i]["actor_id"]

                        files_done = progress.get("files_completed", 0)
                        total_files = progress.get("total_files", 0)
                        current_file = progress.get("current_file", "")
                        current_chunk = progress.get("current_chunk", 0)
                        total_chunks = progress.get("total_chunks", 0)
                        entities = progress.get("entities_extracted", 0)
                        relationships = progress.get("relationships_extracted", 0)
                        status = progress.get("status", "idle")

                        # Create a state tuple for change detection
                        last_key = f"actor_{actor_id}"
                        current_state = (files_done, current_file, current_chunk, entities)

                        # Show update if state changed OR first poll with actual progress
                        show_update = last_progress_update.get(last_key) != current_state

                        # Show progress only when files complete (not per chunk/file-start)
                        # Only show every 10th file or the last file to reduce UI clutter
                        if show_update and status == "file_completed" and files_done > 0:
                            if files_done == total_files or files_done % 10 == 0:
                                last_progress_update[last_key] = current_state
                                await tracer.markdown(
                                    f"✓ **Actor {actor_id}**: Progress {files_done}/{total_files} files "
                                    f"({entities} entities extracted)\n\n"
                                )
                    except Exception as e:
                        # Log exception on first few failures for debugging
                        if poll_count <= 2:
                            logger.debug(f"Progress poll failed for actor {i}: {e}")

            # Use Ray's wait to check for completed actors (shorter timeout for more responsive polling)
            done_refs, pending_refs = ray.wait(pending_refs, num_returns=1, timeout=2)

            for ref in done_refs:
                completed_actors += 1
                actor_idx = batch_refs.index(ref)
                await tracer.markdown(
                    f"✅ **Actor {actor_info[actor_idx]['actor_id']}** completed: "
                    f"{actor_info[actor_idx]['batch_size']} documents processed "
                    f"({completed_actors}/{len(successful_actors)} actors done)\n\n"
                )

        # Gather all results using Ray's get
        batch_results = ray.get(batch_refs)

        # Flatten results
        processing_results = []
        for batch_result in batch_results:
            processing_results.extend(batch_result)

        # Update tracker with processed documents
        for result in processing_results:
            if result.get("status") == "completed":
                tracker.mark_processed(
                    result.get("file_path", ""),
                    result.get("entities_extracted", 0),
                    result.get("relationships_extracted", 0),
                )

        # Calculate processing stats from results
        total_entities = sum(r.get("entities_extracted", 0) for r in processing_results)
        total_relationships = sum(r.get("relationships_extracted", 0) for r in processing_results)
        successful = sum(1 for r in processing_results if r.get("status") == "completed")
        failed = len(processing_results) - successful
        processing_time = sum(r.get("processing_time", 0) for r in processing_results)

        # Build stats dict for display
        stats = {
            "total_documents": len(processing_results),
            "processed": successful,
            "skipped": 0,
            "failed": failed,
            "success_rate": (successful / len(processing_results) * 100)
            if len(processing_results) > 0
            else 0,
            "total_entities": total_entities,
            "total_relationships": total_relationships,
            "avg_entities_per_doc": (total_entities / successful) if successful > 0 else 0,
            "total_processing_time": processing_time,
        }

        # Step 3: Generate comprehensive report (same format as Flow 1)
        await tracer.markdown("## ✅ Document Processing Complete\n\n")
        await tracer.markdown(
            f"""
**Processing Statistics:**
- **Total Documents:** {stats.get('total_documents', 0)}
- **Processed:** {stats.get('processed', 0)}
- **Skipped:** {stats.get('skipped', 0)}
- **Failed:** {stats.get('failed', 0)}
- **Success Rate:** {stats.get('success_rate', 0):.1f}%

**Knowledge Graph Growth:**
- **Total Entities:** {stats.get('total_entities', 0)}
- **Total Relationships:** {stats.get('total_relationships', 0)}
- **Avg Entities/Doc:** {stats.get('avg_entities_per_doc', 0):.1f}
- **Processing Time:** {stats.get('total_processing_time', 0):.2f}s

---
"""
        )

        # Calculate total execution time
        total_time = (datetime.now() - start_time).total_seconds()

        # Generate final comprehensive report using Flow 1's report generator
        report_generator = IngestionReportGenerator()

        # Prepare configuration for report generator
        config = {
            "job_name": job_name,
            "source_path": "Auto-detected (news + policy)",
            "document_limit": max_documents,
            "clear_data": False,
            "enable_communities": False,
            "graph_group_id": os.getenv("GRAPHITI_GROUP_ID", "political_monitoring_v2"),
            "neo4j_uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        }

        # Generate the comprehensive report
        report_content = await report_generator.generate_report(
            processing_results=processing_results,
            communities=[],  # Flow 1B doesn't build communities
            config=config,
            job_name=job_name,
        )

        await tracer.markdown("### ✅ Analysis Complete! Report ready for viewing.")

        return core.response.Markdown(report_content)

    except Exception as e:
        error_msg = f"Bulk auto-delta processing failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await tracer.markdown(f"❌ **Error**: {error_msg}\n\n")

        return core.response.Markdown(
            f"""# {job_name} - Failed

**Error Details:**
```
{error_msg}
```

**Troubleshooting Steps:**
1. Check that Neo4j is running: `docker ps | grep neo4j`
2. Verify environment variables in `.env` file
3. Check document paths exist and contain supported files (.md)
4. Review logs for detailed error information

**Job Name**: {job_name}
**Execution Time**: {(datetime.now() - start_time).total_seconds():.1f}s

Please check the logs for more details.
"""
        )
