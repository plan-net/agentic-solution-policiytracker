"""
Bulk Auto-Delta Document Processor

Automatically detects unprocessed documents by comparing processed_documents.json
with current folder state, then processes the delta.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List

import structlog
from kodosumi import Tracer

# Configure logging for Ray environment
from src.flows.data_ingestion.logging_config import configure_logging
configure_logging()

logger = structlog.get_logger()

# Import Ray and document processor components
try:
    import ray
    RAY_AVAILABLE = True
    from src.flows.data_ingestion.document_processor import DocumentProcessorActor
except ImportError:
    RAY_AVAILABLE = False
    logger.warning("Ray not available - bulk processing will be limited")


def get_unprocessed_documents(base_path: str = "data/input", tracking_file: str = "data/processed_documents.json") -> List[str]:
    """
    Get list of documents that haven't been processed.

    Compares the tracking file with current folder state to find the delta.
    """
    tracking_path = Path(tracking_file)
    processed_docs = {}

    # Load processed documents
    if tracking_path.exists():
        try:
            with open(tracking_path, "r", encoding="utf-8") as f:
                processed_docs = json.load(f)
            logger.info(f"Loaded {len(processed_docs)} processed documents from tracker")
        except Exception as e:
            logger.warning(f"Could not load tracking file: {e}")
            processed_docs = {}
    else:
        logger.info("No tracking file found, treating all documents as unprocessed")

    # Get all markdown documents from both news and policy directories
    all_docs = []
    base_paths = [Path(base_path) / "news", Path(base_path) / "policy"]

    for search_path in base_paths:
        if not search_path.exists():
            logger.warning(f"Base path {search_path} does not exist, skipping")
            continue

        # Find all markdown files in this directory
        for md_file in search_path.rglob("*.md"):
            try:
                # Get relative path from base_path (stored paths in tracker are relative)
                relative_path = str(md_file.relative_to(Path(base_path)))
                all_docs.append(relative_path)
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

    Automatically detects unprocessed documents and processes them in parallel
    using Ray actors.
    """
    from kodosumi import core

    job_name = inputs.get("job_name", "Bulk Auto-Delta Processing")
    max_documents = inputs.get("max_documents", 500)

    start_time = datetime.now()

    # Step 1: Auto-detect unprocessed documents
    await tracer.markdown(f"## {job_name}\n\n")
    await tracer.markdown("### Step 1: Auto-Detecting Unprocessed Documents\n\n")
    await tracer.markdown("🔍 Scanning document directories...\n\n")

    try:
        unprocessed_docs = get_unprocessed_documents()

        if not unprocessed_docs:
            await tracer.markdown("✅ No unprocessed documents found.\n\n")
            return core.response.Markdown(
                "## Processing Complete\n\n"
                "No unprocessed documents found. All documents are up to date.\n\n"
                f"**Job Name**: {job_name}\n"
                f"**Execution Time**: {(datetime.now() - start_time).total_seconds():.1f}s\n"
            )

        # Apply 500 document safety limit
        total_unprocessed = len(unprocessed_docs)
        if total_unprocessed > max_documents:
            await tracer.markdown(
                f"⚠️ **Safety Limit Applied**: Found {total_unprocessed} unprocessed documents, "
                f"but will process only first {max_documents} documents.\n\n"
            )
            unprocessed_docs = unprocessed_docs[:max_documents]
        else:
            await tracer.markdown(f"✅ Found {total_unprocessed} unprocessed documents to process.\n\n")

        # Step 2: Process documents
        await tracer.markdown("### Step 2: Processing Documents\n\n")
        await tracer.markdown(f"📄 Processing {len(unprocessed_docs)} documents in parallel using Ray...\n\n")

        if not RAY_AVAILABLE:
            await tracer.markdown("❌ Ray is not available. Cannot process documents.\n\n")
            return core.response.Markdown(
                "## Processing Failed\n\n"
                "Ray is not available for distributed processing.\n"
            )

        # Initialize Ray actors for parallel processing
        num_actors = min(4, len(unprocessed_docs))  # Use up to 4 actors
        actors = [DocumentProcessorActor.remote(i, clear_mode=False) for i in range(num_actors)]

        # Initialize actors using ray.get for synchronous initialization
        init_tasks = [actor.initialize.remote() for actor in actors]
        init_results = ray.get(init_tasks)
        if not all(init_results):
            await tracer.markdown("❌ Failed to initialize processing actors.\n\n")
            return core.response.Markdown(
                "## Processing Failed\n\n"
                "Failed to initialize document processing actors.\n"
            )

        await tracer.markdown(f"✅ Initialized {num_actors} processing actors.\n\n")

        # Convert relative paths to absolute paths
        base_path = Path("data/input")
        absolute_paths = [str(base_path / doc_path) for doc_path in unprocessed_docs]

        # Distribute documents across actors
        tasks = []
        for i, doc_path in enumerate(absolute_paths):
            actor = actors[i % num_actors]
            tasks.append(actor.process_document.remote(Path(doc_path)))

        # Process with progress updates
        processed_count = 0
        successful_count = 0
        failed_count = 0

        await tracer.markdown("**Progress Updates:**\n\n")

        # Use ray.wait instead of asyncio.wait for Ray remote calls
        while tasks:
            # Wait for at least one task to complete
            done, tasks = ray.wait(tasks, num_returns=1, timeout=None)

            for completed_task in done:
                try:
                    result = ray.get(completed_task)
                    processed_count += 1

                    if result.get("success"):
                        successful_count += 1
                        doc_name = Path(result.get("document_path", "unknown")).name
                        entities = result.get("entity_count", 0)
                        relationships = result.get("relationship_count", 0)
                        await tracer.markdown(
                            f"- ✅ **{processed_count}/{len(unprocessed_docs)}**: {doc_name} "
                            f"({entities} entities, {relationships} relationships)\n"
                        )
                    else:
                        failed_count += 1
                        doc_name = Path(result.get("document_path", "unknown")).name
                        error = result.get("error", "Unknown error")
                        await tracer.markdown(
                            f"- ❌ **{processed_count}/{len(unprocessed_docs)}**: {doc_name} - {error}\n"
                        )

                except Exception as e:
                    failed_count += 1
                    processed_count += 1
                    await tracer.markdown(
                        f"- ❌ **{processed_count}/{len(unprocessed_docs)}**: Processing error: {e}\n"
                    )

        await tracer.markdown("\n")

        # Step 3: Generate summary
        processing_time = (datetime.now() - start_time).total_seconds()
        success_rate = (successful_count / processed_count * 100) if processed_count > 0 else 0

        await tracer.markdown("### Step 3: Processing Summary\n\n")
        await tracer.markdown("✅ **Bulk auto-delta processing complete!**\n\n")

        # Generate final report
        report = f"""## Bulk Auto-Delta Processing Complete

### Job Information
- **Job Name**: {job_name}
- **Execution Time**: {processing_time:.1f}s
- **Processing Rate**: {(processed_count / processing_time):.1f} docs/second

### Document Statistics
- **Total Unprocessed Found**: {total_unprocessed}
- **Documents Processed**: {processed_count}
- **Successful**: {successful_count} ({success_rate:.1f}%)
- **Failed**: {failed_count}

### Status
{"🎉 All documents processed successfully!" if failed_count == 0 else f"⚠️ {failed_count} document(s) failed processing."}

### Next Steps
{"- All documents are now up to date" if total_unprocessed <= max_documents else f"- {total_unprocessed - max_documents} documents remaining (run again to process next batch)"}
- Check knowledge graph at [Neo4j Browser](http://localhost:7474)
- Use chat interface at [Open WebUI](http://localhost:3000) to query new data
"""

        return core.response.Markdown(report)

    except Exception as e:
        error_msg = f"Bulk auto-delta processing failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await tracer.markdown(f"❌ **Error**: {error_msg}\n\n")

        return core.response.Markdown(
            f"""## Processing Failed

**Error**: {error_msg}

**Job Name**: {job_name}
**Execution Time**: {(datetime.now() - start_time).total_seconds():.1f}s

Please check the logs for more details.
"""
        )
