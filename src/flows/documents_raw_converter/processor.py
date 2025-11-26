"""
Raw Document Auto-Conversion Processor

Automatically scans data/input/documents_raw/ for new documents,
converts them to markdown, saves to data/input/documents_md/,
and processes them through Graphiti for knowledge graph extraction.
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path

import structlog
from kodosumi.core import Tracer

# Configure logging
from src.flows.data_ingestion.logging_config import configure_logging
from src.flows.documents_raw_converter.raw_tracker import RawDocumentTracker
from src.flows.shared.document_converter import DocumentConverter

configure_logging()

logger = structlog.get_logger()

# Configuration from environment variables
FLOW1D_NUM_ACTORS = int(os.getenv("FLOW1D_NUM_ACTORS", "2"))
FLOW1D_ENABLE_GRAPHITI = os.getenv("FLOW1D_ENABLE_GRAPHITI", "true").lower() == "true"

# Import Ray for parallel processing
try:
    import ray

    RAY_AVAILABLE = True
except ImportError:
    RAY_AVAILABLE = False
    logger.warning("Ray not available - parallel Graphiti processing will be limited")


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


def get_unprocessed_markdown_files(
    md_dir: str = "data/input/documents_md", tracking_file: str = "data/processed_documents.json"
) -> list[str]:
    """
    Get list of markdown files that haven't been processed by Graphiti yet.

    Compares markdown files in md_dir with processed_documents.json tracker
    to find documents that need Graphiti processing.

    Args:
        md_dir: Directory containing markdown files
        tracking_file: Path to DocumentTracker JSON file

    Returns:
        List of absolute paths to unprocessed markdown files
    """
    import json

    md_path = Path(md_dir)
    tracking_path = Path(tracking_file)

    # Load processed documents tracker
    processed_docs = {}
    if tracking_path.exists():
        try:
            with open(tracking_path, encoding="utf-8") as f:
                processed_docs = json.load(f)
            logger.info(f"Loaded {len(processed_docs)} processed documents from tracker")
        except Exception as e:
            logger.warning(f"Could not load tracking file: {e}")
            processed_docs = {}
    else:
        logger.info("No tracking file found, all markdown files will be processed")

    # Get all markdown files from documents_md directory
    all_md_files = []
    if md_path.exists():
        for md_file in md_path.rglob("*.md"):
            # Store as string path for comparison
            all_md_files.append(str(md_file))
    else:
        logger.warning(f"Markdown directory {md_dir} does not exist")
        return []

    logger.info(f"Found {len(all_md_files)} total markdown files in {md_dir}")

    # Filter to only unprocessed documents
    unprocessed = [md_file for md_file in all_md_files if md_file not in processed_docs]

    logger.info(f"Found {len(unprocessed)} unprocessed markdown files for Graphiti processing")
    return unprocessed


async def execute_raw_document_conversion(inputs: dict, tracer: Tracer):
    """
    Execute raw document auto-conversion processing.

    Scans documents_raw folder for new files, converts to markdown
    with policy-compatible metadata, and processes through Graphiti.
    """
    from kodosumi import core

    job_name = inputs.get("job_name", "Raw Document Auto-Conversion")
    raw_docs_dir = inputs.get("raw_docs_dir", "data/input/documents_raw")
    output_dir = inputs.get("output_dir", "data/input/documents_md")
    enable_graphiti = inputs.get("enable_graphiti", FLOW1D_ENABLE_GRAPHITI)

    start_time = datetime.now()

    logger.info(
        "Starting raw document conversion",
        job_name=job_name,
        raw_docs_dir=raw_docs_dir,
        output_dir=output_dir,
        enable_graphiti=enable_graphiti,
        num_actors=FLOW1D_NUM_ACTORS,
    )

    # Display header
    await tracer.markdown(
        f"""
# 📄 {job_name} - Starting

**Configuration:**
- Source Directory: `{raw_docs_dir}`
- Output Directory: `{output_dir}`
- Supported Formats: PDF, DOC, DOCX, PPT, PPTX
- Tracking File: `data/raw_documents_processed.json`
- Graphiti Processing: {'✅ Enabled' if enable_graphiti else '❌ Disabled'}
- Parallel Actors: {FLOW1D_NUM_ACTORS if enable_graphiti else 'N/A'}

**Process:**
1. Scan for unprocessed documents
2. Convert to markdown with policy-compatible metadata
3. Save to output directory
{'4. Process through Graphiti for knowledge graph extraction' if enable_graphiti else ''}
{'5. Track processed files with entity statistics' if enable_graphiti else '4. Track processed files'}

---
"""
    )

    await tracer.markdown("## 🔍 Document Discovery\n\n")
    await tracer.markdown("Scanning for unprocessed documents...\n\n")

    try:
        # Initialize components
        tracker = RawDocumentTracker()
        converter = DocumentConverter(output_dir=output_dir)

        # Get unprocessed documents
        unprocessed_docs = tracker.get_unprocessed_documents(raw_docs_dir)

        # Step 1: Convert documents to markdown (if any raw documents found)
        conversion_results = []
        converted_files = []
        conversion_failed = 0

        if not unprocessed_docs:
            await tracer.markdown(f"✅ No unprocessed raw documents found in `{raw_docs_dir}`.\n\n")
            await tracer.markdown("---\n\n")
            # Don't return early - continue to Phase 2 to check for unprocessed markdown files
        else:
            # Display documents to be processed
            await tracer.markdown(
                f"""
Found **{len(unprocessed_docs)}** documents to process:

{chr(10).join(f"- {doc.name} ({doc.suffix.upper()})" for doc in unprocessed_docs[:10])}
{'...' if len(unprocessed_docs) > 10 else ''}

---
"""
            )

            await tracer.markdown("## 🔄 Converting Documents to Markdown\n\n")

            for i, doc_path in enumerate(unprocessed_docs, 1):
                await tracer.markdown(
                    f"📄 Converting {i}/{len(unprocessed_docs)}: {doc_path.name}...\n\n"
                )

                try:
                    # Convert document to markdown
                    output_path = await converter.convert_and_save(doc_path)

                    conversion_results.append(
                        {
                            "source_file": doc_path.name,
                            "output_file": output_path.name,
                            "output_path": str(output_path),
                            "status": "converted",
                            "error": None,
                        }
                    )

                    converted_files.append(str(output_path))
                    await tracer.markdown(f"✅ Converted to: {output_path.name}\n\n")

                except Exception as e:
                    error_msg = str(e)
                    logger.error(
                        "Failed to convert document",
                        filename=doc_path.name,
                        error=error_msg,
                    )

                    conversion_results.append(
                        {
                            "source_file": doc_path.name,
                            "output_file": None,
                            "output_path": None,
                            "status": "conversion_failed",
                            "error": error_msg,
                        }
                    )

                    conversion_failed += 1
                    await tracer.markdown(f"❌ Conversion Error: {error_msg}\n\n")

            await tracer.markdown(
                f"""
**Conversion Complete:**
- Converted: {len(converted_files)}
- Failed: {conversion_failed}

---
"""
            )

        # Step 2: Process through Graphiti (independent of conversion results)
        # This allows processing of any unprocessed markdown files, not just newly converted ones
        processing_results = conversion_results  # Default to conversion results
        graphiti_stats = {
            "total_entities": 0,
            "total_relationships": 0,
            "processed": 0,
            "failed": 0,
        }

        if enable_graphiti and RAY_AVAILABLE:
            await tracer.markdown("## 🧠 Processing with Graphiti Knowledge Graph\n\n")
            await tracer.markdown("🔍 Scanning for unprocessed markdown files...\n\n")

            # Get ALL unprocessed markdown files from documents_md directory
            # (not just the ones converted in this run)
            unprocessed_md_files = get_unprocessed_markdown_files(
                md_dir=output_dir, tracking_file="data/processed_documents.json"
            )

            if not unprocessed_md_files:
                await tracer.markdown(
                    "✅ No unprocessed markdown files found. All documents are up to date.\n\n"
                )
                # Continue to final reporting
            else:
                await tracer.markdown(
                    f"""
Found **{len(unprocessed_md_files)}** unprocessed markdown files:
{chr(10).join(f"- {Path(doc).name}" for doc in unprocessed_md_files[:10])}
{'...' if len(unprocessed_md_files) > 10 else ''}

---
"""
                )

                try:
                    # Import components for Graphiti processing
                    from src.flows.data_ingestion.document_processor import DocumentProcessorActor
                    from src.flows.data_ingestion.document_tracker import DocumentTracker

                    graphiti_tracker = DocumentTracker()

                    # Initialize Ray if not already done
                    if not ray.is_initialized():
                        ray.init(log_to_driver=True)

                    # Create Ray actors for parallel processing
                    num_actors = min(FLOW1D_NUM_ACTORS, len(unprocessed_md_files))
                    actors = [
                        DocumentProcessorActor.remote(i, clear_mode=False)
                        for i in range(num_actors)
                    ]

                    # Initialize actors
                    init_results = await asyncio.gather(
                        *[actor.initialize.remote() for actor in actors]
                    )
                    successful_actors = [
                        actor for actor, success in zip(actors, init_results) if success
                    ]

                    logger.info(
                        f"Actor initialization: {len(successful_actors)}/{num_actors} successful"
                    )

                    if not successful_actors:
                        raise RuntimeError("No actors could be initialized for parallel processing")

                    await tracer.markdown(
                        f"🚀 **Using {len(successful_actors)} Ray actors** for parallel Graphiti processing\n\n"
                    )

                    # Create balanced batches using proper distribution algorithm
                    batches = distribute_documents_to_actors(
                        unprocessed_md_files, len(successful_actors)
                    )

                    # Verify all documents are assigned
                    total_assigned = sum(len(batch) for batch in batches)
                    logger.info(
                        f"Document distribution: {len(unprocessed_md_files)} files → {len(batches)} batches "
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
                        await tracer.markdown(
                            f"- **Actor {i}**: {len(batch)} documents ({doc_list})\n"
                        )
                    await tracer.markdown("\n")

                    # Process batches in parallel
                    batch_refs = []
                    actor_info = []
                    for i, (actor, batch) in enumerate(zip(successful_actors, batches), 1):
                        if batch:
                            ref = actor.process_batch.remote(batch)
                            batch_refs.append(ref)
                            actor_info.append(
                                {"actor_id": i, "batch_size": len(batch), "batch": batch}
                            )

                    await tracer.markdown(
                        "⏳ **Processing documents through Graphiti in parallel...**\n\n"
                    )

                    # Wait for results with progress tracking using Ray's wait
                    completed = 0
                    pending_refs = batch_refs.copy()

                    while pending_refs:
                        # Use Ray's wait (not asyncio.wait) - returns lists, not sets
                        done_refs, pending_refs = ray.wait(pending_refs, num_returns=1, timeout=5)

                        for ref in done_refs:
                            completed += 1
                            actor_idx = batch_refs.index(ref)
                            await tracer.markdown(
                                f"✅ **Actor {actor_info[actor_idx]['actor_id']}** completed: "
                                f"{actor_info[actor_idx]['batch_size']} documents processed "
                                f"({completed}/{len(successful_actors)} actors done)\n\n"
                            )

                    # Gather all results using Ray's get
                    batch_results = ray.get(batch_refs)

                    # Flatten results
                    graphiti_results = []
                    for batch_result in batch_results:
                        graphiti_results.extend(batch_result)

                    # Update tracker with processed documents
                    for result in graphiti_results:
                        if result.get("status") == "completed":
                            graphiti_tracker.mark_processed(
                                result.get("file_path", ""),
                                result.get("entities_extracted", 0),
                                result.get("relationships_extracted", 0),
                            )

                    # Calculate Graphiti processing stats
                    graphiti_stats["total_entities"] = sum(
                        r.get("entities_extracted", 0) for r in graphiti_results
                    )
                    graphiti_stats["total_relationships"] = sum(
                        r.get("relationships_extracted", 0) for r in graphiti_results
                    )
                    graphiti_stats["processed"] = sum(
                        1 for r in graphiti_results if r.get("status") == "completed"
                    )
                    graphiti_stats["failed"] = len(graphiti_results) - graphiti_stats["processed"]

                    # Merge conversion and Graphiti results for display
                    graphiti_results_map = {r.get("file_path"): r for r in graphiti_results}
                    for conv_result in conversion_results:
                        output_path = conv_result.get("output_path")
                        if output_path and output_path in graphiti_results_map:
                            graphiti_result = graphiti_results_map[output_path]
                            conv_result.update(
                                {
                                    "entities_extracted": graphiti_result.get(
                                        "entities_extracted", 0
                                    ),
                                    "relationships_extracted": graphiti_result.get(
                                        "relationships_extracted", 0
                                    ),
                                    "graphiti_status": graphiti_result.get("status", "unknown"),
                                }
                            )

                    processing_results = conversion_results

                    await tracer.markdown(
                        f"""
**Graphiti Processing Complete:**
- Processed: {graphiti_stats['processed']}
- Failed: {graphiti_stats['failed']}
- Total Entities: {graphiti_stats['total_entities']}
- Total Relationships: {graphiti_stats['total_relationships']}

---
"""
                    )

                except Exception as e:
                    error_msg = f"Graphiti processing failed: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    await tracer.markdown(
                        f"⚠️ **Warning**: {error_msg}\n\nContinuing with conversion results only.\n\n"
                    )

        elif enable_graphiti and not RAY_AVAILABLE:
            await tracer.markdown("⚠️ **Skipping Graphiti processing**: Ray not available.\n\n")

        # Mark documents as processed in raw tracker
        for result in processing_results:
            if result.get("status") in ["converted", "conversion_failed"]:
                # Find original source path
                source_name = result.get("source_file")
                source_path = next((d for d in unprocessed_docs if d.name == source_name), None)

                if source_path:
                    output_path = (
                        Path(result.get("output_path"))
                        if result.get("output_path")
                        else Path(output_dir) / "error.md"
                    )
                    tracker.mark_processed(
                        file_path=source_path,
                        output_md_path=output_path,
                        success=result.get("status") == "converted",
                        error=result.get("error"),
                    )

        # Calculate final stats
        successful = sum(1 for r in processing_results if r.get("status") == "converted")
        failed = len(processing_results) - successful

        # Generate completion report
        await tracer.markdown("## ✅ Processing Complete\n\n")

        total_time = (datetime.now() - start_time).total_seconds()
        tracker_stats = tracker.get_stats()

        stats_markdown = f"""
**Conversion Statistics:**
- **Total Documents**: {len(unprocessed_docs)}
- **Successful**: {successful}
- **Failed**: {failed}
- **Success Rate**: {(successful / len(unprocessed_docs) * 100) if len(unprocessed_docs) > 0 else 0:.1f}%
"""

        if enable_graphiti and graphiti_stats["processed"] > 0:
            stats_markdown += f"""
**Graphiti Knowledge Graph Statistics:**
- **Processed**: {graphiti_stats['processed']}
- **Failed**: {graphiti_stats['failed']}
- **Total Entities**: {graphiti_stats['total_entities']}
- **Total Relationships**: {graphiti_stats['total_relationships']}
- **Avg Entities/Doc**: {(graphiti_stats['total_entities'] / graphiti_stats['processed']) if graphiti_stats['processed'] > 0 else 0:.1f}
"""

        stats_markdown += f"""
**Performance:**
- **Processing Time**: {total_time:.2f}s
- **Avg Time/Doc**: {(total_time / len(unprocessed_docs)) if len(unprocessed_docs) > 0 else 0:.2f}s

**Tracking Statistics:**
- **Total Processed (All Time)**: {tracker_stats['total_processed']}
- **Successful (All Time)**: {tracker_stats['successful']}
- **Failed (All Time)**: {tracker_stats['failed']}

---
"""

        await tracer.markdown(stats_markdown)

        # Generate comprehensive report
        report_content = _generate_conversion_report(
            job_name=job_name,
            processing_results=processing_results,
            tracker_stats=tracker_stats,
            graphiti_stats=graphiti_stats if enable_graphiti else None,
            total_time=total_time,
            raw_docs_dir=raw_docs_dir,
            output_dir=output_dir,
            enable_graphiti=enable_graphiti,
        )

        await tracer.markdown("### ✅ Conversion Complete! Report ready for viewing.")

        return core.response.Markdown(report_content)

    except Exception as e:
        error_msg = f"Raw document conversion failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await tracer.markdown(f"❌ **Error**: {error_msg}\n\n")

        return core.response.Markdown(
            f"""# {job_name} - Failed

**Error Details:**
```
{error_msg}
```

**Troubleshooting Steps:**
1. Check that `{raw_docs_dir}` directory exists
2. Verify document formats are supported (PDF, DOC, DOCX, PPT, PPTX)
3. Ensure output directory `{output_dir}` is writable
4. Check that required libraries are installed (pypdf, python-docx, python-pptx)
5. Review logs for detailed error information

**Job Name**: {job_name}
**Execution Time**: {(datetime.now() - start_time).total_seconds():.1f}s

Please check the logs for more details.
"""
        )


def _generate_conversion_report(
    job_name: str,
    processing_results: list[dict],
    tracker_stats: dict,
    graphiti_stats: dict | None,
    total_time: float,
    raw_docs_dir: str,
    output_dir: str,
    enable_graphiti: bool,
) -> str:
    """Generate comprehensive conversion report."""

    successful_results = [r for r in processing_results if r["status"] == "converted"]
    failed_results = [
        r for r in processing_results if r["status"] in ["conversion_failed", "failed"]
    ]

    report = f"""# {job_name} - Complete

## Summary

Successfully converted **{len(successful_results)}** documents out of **{len(processing_results)}** total documents.

**Configuration:**
- **Source Directory**: `{raw_docs_dir}`
- **Output Directory**: `{output_dir}`
- **Graphiti Processing**: {'✅ Enabled' if enable_graphiti else '❌ Disabled'}
- **Execution Time**: {total_time:.2f}s
- **Tracking File**: `data/raw_documents_processed.json`

---

## Conversion Statistics

| Metric | Value |
|--------|-------|
| Total Documents | {len(processing_results)} |
| Successful | {len(successful_results)} |
| Failed | {len(failed_results)} |
| Success Rate | {(len(successful_results) / len(processing_results) * 100) if len(processing_results) > 0 else 0:.1f}% |
| Avg Time/Doc | {(total_time / len(processing_results)) if len(processing_results) > 0 else 0:.2f}s |

---
"""

    # Add Graphiti statistics if enabled and processed
    if graphiti_stats and graphiti_stats["processed"] > 0:
        report += f"""
## Graphiti Knowledge Graph Statistics

| Metric | Value |
|--------|-------|
| Documents Processed | {graphiti_stats['processed']} |
| Failed | {graphiti_stats['failed']} |
| Total Entities Extracted | {graphiti_stats['total_entities']} |
| Total Relationships | {graphiti_stats['total_relationships']} |
| Avg Entities/Doc | {(graphiti_stats['total_entities'] / graphiti_stats['processed']) if graphiti_stats['processed'] > 0 else 0:.1f} |
| Avg Relationships/Doc | {(graphiti_stats['total_relationships'] / graphiti_stats['processed']) if graphiti_stats['processed'] > 0 else 0:.1f} |

---
"""

    report += """
## Processing Details

"""

    # Successful conversions
    if successful_results:
        report += f"""
### ✅ Successfully Converted ({len(successful_results)})

| Source File | Output File | Format |
|------------|-------------|--------|
"""
        for result in successful_results[:20]:  # Limit to first 20
            source_ext = Path(result["source_file"]).suffix.upper().replace(".", "")
            report += f"| {result['source_file']} | {result['output_file']} | {source_ext} |\n"

        if len(successful_results) > 20:
            report += f"\n*...and {len(successful_results) - 20} more*\n"

    # Failed conversions
    if failed_results:
        report += f"""

### ❌ Failed Conversions ({len(failed_results)})

| Source File | Error |
|------------|-------|
"""
        for result in failed_results:
            error_short = (
                result["error"][:50] + "..." if len(result["error"]) > 50 else result["error"]
            )
            report += f"| {result['source_file']} | {error_short} |\n"

    # Overall tracking statistics
    report += f"""

---

## Overall Tracking Statistics

| Metric | Value |
|--------|-------|
| Total Processed (All Time) | {tracker_stats['total_processed']} |
| Successful (All Time) | {tracker_stats['successful']} |
| Failed (All Time) | {tracker_stats['failed']} |
| Success Rate (All Time) | {tracker_stats['success_rate']:.1f}% |

---

## Next Steps

1. **Review converted documents** in `{output_dir}`
"""

    if enable_graphiti and graphiti_stats and graphiti_stats["processed"] > 0:
        report += """2. **Query knowledge graph** via chat interface to explore extracted entities
3. **Explore relationships** in Neo4j Browser
4. **Run Flow 1B** to process additional documents from `data/input/policy` or `data/input/news`
"""
    else:
        report += """2. **Process with Flow 1B** to add documents to knowledge graph
3. **Query via chat interface** to explore content
"""

    report += f"""
**Access Points:**
- [Chat Interface](http://localhost:3000) - Query content and entities
- [Neo4j Browser](http://localhost:7474) - Explore knowledge graph
- [Kodosumi Admin](http://localhost:3370) - Run additional flows
- [Ray Dashboard](http://localhost:8265) - Monitor processing

---

**Job Name**: {job_name}
**Completed**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

    return report
