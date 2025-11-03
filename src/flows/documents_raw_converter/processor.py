"""
Raw Document Auto-Conversion Processor

Automatically scans data/input/documents_raw/ for new documents,
converts them to markdown, and saves to data/input/documents_md/.
"""

from datetime import datetime
from pathlib import Path
from typing import List

import structlog
from kodosumi.core import Tracer

from src.flows.documents_raw_converter.raw_tracker import RawDocumentTracker
from src.flows.shared.document_converter import DocumentConverter

# Configure logging
from src.flows.data_ingestion.logging_config import configure_logging

configure_logging()

logger = structlog.get_logger()


async def execute_raw_document_conversion(inputs: dict, tracer: Tracer):
    """
    Execute raw document auto-conversion processing.

    Scans documents_raw folder for new files, converts to markdown
    with policy-compatible metadata.
    """
    from kodosumi import core

    job_name = inputs.get("job_name", "Raw Document Auto-Conversion")
    raw_docs_dir = inputs.get("raw_docs_dir", "data/input/documents_raw")
    output_dir = inputs.get("output_dir", "data/input/documents_md")

    start_time = datetime.now()

    logger.info(
        "Starting raw document conversion",
        job_name=job_name,
        raw_docs_dir=raw_docs_dir,
        output_dir=output_dir,
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

**Process:**
1. Scan for unprocessed documents
2. Convert to markdown with policy-compatible metadata
3. Save to output directory
4. Track processed files

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

        if not unprocessed_docs:
            await tracer.markdown("✅ No unprocessed documents found.\n\n")
            return core.response.Markdown(
                f"""# {job_name} - Complete

## No Unprocessed Documents

All documents in `{raw_docs_dir}` have already been processed.

**Job Name**: {job_name}
**Execution Time**: {(datetime.now() - start_time).total_seconds():.1f}s
"""
            )

        # Display documents to be processed
        await tracer.markdown(
            f"""
Found **{len(unprocessed_docs)}** documents to process:

{chr(10).join(f"- {doc.name} ({doc.suffix.upper()})" for doc in unprocessed_docs[:10])}
{'...' if len(unprocessed_docs) > 10 else ''}

---
"""
        )

        # Process documents
        await tracer.markdown("## 🔄 Converting Documents\n\n")

        processing_results = []
        successful = 0
        failed = 0

        for i, doc_path in enumerate(unprocessed_docs, 1):
            await tracer.markdown(
                f"📄 Processing {i}/{len(unprocessed_docs)}: {doc_path.name}...\n\n"
            )

            try:
                # Convert document to markdown
                output_path = await converter.convert_and_save(doc_path)

                # Mark as processed
                tracker.mark_processed(
                    file_path=doc_path, output_md_path=output_path, success=True
                )

                processing_results.append(
                    {
                        "source_file": doc_path.name,
                        "output_file": output_path.name,
                        "status": "success",
                        "error": None,
                    }
                )

                successful += 1
                await tracer.markdown(f"✅ Converted to: {output_path.name}\n\n")

            except Exception as e:
                error_msg = str(e)
                logger.error(
                    f"Failed to convert document",
                    filename=doc_path.name,
                    error=error_msg,
                )

                # Mark as processed with error
                tracker.mark_processed(
                    file_path=doc_path,
                    output_md_path=Path(output_dir) / "error.md",
                    success=False,
                    error=error_msg,
                )

                processing_results.append(
                    {
                        "source_file": doc_path.name,
                        "output_file": None,
                        "status": "failed",
                        "error": error_msg,
                    }
                )

                failed += 1
                await tracer.markdown(f"❌ Error: {error_msg}\n\n")

        # Generate completion report
        await tracer.markdown("## ✅ Document Conversion Complete\n\n")

        total_time = (datetime.now() - start_time).total_seconds()
        tracker_stats = tracker.get_stats()

        await tracer.markdown(
            f"""
**Conversion Statistics:**
- **Total Documents**: {len(unprocessed_docs)}
- **Successful**: {successful}
- **Failed**: {failed}
- **Success Rate**: {(successful / len(unprocessed_docs) * 100) if len(unprocessed_docs) > 0 else 0:.1f}%
- **Processing Time**: {total_time:.2f}s

**Tracking Statistics:**
- **Total Processed (All Time)**: {tracker_stats['total_processed']}
- **Successful (All Time)**: {tracker_stats['successful']}
- **Failed (All Time)**: {tracker_stats['failed']}

---
"""
        )

        # Generate comprehensive report
        report_content = _generate_conversion_report(
            job_name=job_name,
            processing_results=processing_results,
            tracker_stats=tracker_stats,
            total_time=total_time,
            raw_docs_dir=raw_docs_dir,
            output_dir=output_dir,
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
    processing_results: List[dict],
    tracker_stats: dict,
    total_time: float,
    raw_docs_dir: str,
    output_dir: str,
) -> str:
    """Generate comprehensive conversion report."""

    successful_results = [r for r in processing_results if r["status"] == "success"]
    failed_results = [r for r in processing_results if r["status"] == "failed"]

    report = f"""# {job_name} - Complete

## Summary

Successfully converted **{len(successful_results)}** documents out of **{len(processing_results)}** total documents.

**Configuration:**
- **Source Directory**: `{raw_docs_dir}`
- **Output Directory**: `{output_dir}`
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
            report += (
                f"| {result['source_file']} | {result['output_file']} | {source_ext} |\n"
            )

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
                result["error"][:50] + "..."
                if len(result["error"]) > 50
                else result["error"]
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
2. **Process with Flow 1B** to add documents to knowledge graph
3. **Query via chat interface** to explore new content

**Access Points:**
- [Kodosumi Admin](http://localhost:3370) - Run Flow 1B
- [Chat Interface](http://localhost:3000) - Query new content
- [Neo4j Browser](http://localhost:7474) - Explore knowledge graph

---

**Job Name**: {job_name}
**Completed**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

    return report
