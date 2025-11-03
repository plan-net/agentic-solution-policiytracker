"""
Bulk Auto-Delta Document Processor

Automatically detects unprocessed documents by comparing processed_documents.json
with current folder state, then processes them using the same pipeline as Flow 1.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List

import structlog
from kodosumi.core import Tracer

# Configure logging for Ray environment
from src.flows.data_ingestion.logging_config import configure_logging

configure_logging()

logger = structlog.get_logger()

# Configuration from environment variables
FLOW1B_MAX_DOCUMENTS = int(os.getenv("FLOW1B_MAX_DOCUMENTS", "500"))
FLOW1B_NUM_ACTORS = int(os.getenv("FLOW1B_NUM_ACTORS", "4"))

# Import Ray and document processor components
try:
    import ray

    RAY_AVAILABLE = True
    from src.flows.data_ingestion.document_processor import DocumentProcessorActor
except ImportError:
    RAY_AVAILABLE = False
    logger.warning("Ray not available - bulk processing will be limited")


def get_unprocessed_documents(
    base_path: str = "data/input", tracking_file: str = "data/processed_documents.json"
) -> List[str]:
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

    Uses the same processing pipeline and report format as Flow 1.
    """
    from kodosumi import core
    from src.flows.data_ingestion.document_processor import SimpleDocumentProcessor
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
            await tracer.markdown(f"✅ Found {total_unprocessed} unprocessed documents to process.\n\n")

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
        from graphiti_core import Graphiti

        tracker = DocumentTracker()
        processor = SimpleDocumentProcessor(tracker, clear_mode=False)

        # Initialize Graphiti client
        NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
        NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")

        graphiti_client = Graphiti(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        await graphiti_client.build_indices_and_constraints()

        # Process documents with the shared processor
        processing_results = []
        for doc_path in unprocessed_docs:
            result = await processor.process_document(Path(doc_path), graphiti_client)
            processing_results.append(result)

        # Close graphiti client
        await graphiti_client.close()

        # Get processing statistics
        stats = processor.get_processing_stats()
        tracker_stats = tracker.get_stats()

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
