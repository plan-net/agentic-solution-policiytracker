"""
Ad-hoc Document/URL Processor

Orchestrates preprocessing, conversion, and processing of ad-hoc URLs
and documents through the political monitoring pipeline.
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List

import structlog
from kodosumi.core import Tracer

# Configure logging for Ray environment
from src.flows.data_ingestion.logging_config import configure_logging

configure_logging()

logger = structlog.get_logger()


async def execute_adhoc_processing(inputs: dict, tracer: Tracer):
    """
    Execute ad-hoc URL or document processing.

    Uses the same processing pipeline and report format as Flow 1.
    """
    from kodosumi import core
    from src.flows.data_ingestion.report_generator import IngestionReportGenerator
    from src.flows.shared.document_converter import DocumentConverter
    from src.flows.shared.url_to_markdown import URLToMarkdownConverter
    from src.flows.shared.markdown_processor import MarkdownProcessor

    job_name = inputs.get("job_name", "Ad-hoc Processing")
    input_type = inputs.get("input_type", "urls")
    max_items = inputs.get("max_items", 10)

    start_time = datetime.now()

    logger.info(
        "Starting ad-hoc processing",
        job_name=job_name,
        input_type=input_type,
        max_items=max_items,
    )

    # Step 1: Display header
    await tracer.markdown(
        f"""
# 📄 {job_name} - Starting

**Configuration:**
- Input Type: {input_type.upper()}
- Item Limit: {max_items}
- Processing Mode: Ad-hoc (with automatic markdown conversion)

---
"""
    )

    try:
        # Step 2: Convert to markdown based on input type
        await tracer.markdown("## 🔄 Converting to Markdown\\n\\n")

        markdown_paths = []

        if input_type == "urls":
            # Process URLs
            await tracer.markdown("🌐 Fetching and converting URLs...\\n\\n")

            urls_text = inputs.get("urls", "")
            urls = [url.strip() for url in urls_text.split("\n") if url.strip()]
            urls = urls[:max_items]  # Apply safety limit

            converter = URLToMarkdownConverter()

            for i, url in enumerate(urls, 1):
                await tracer.markdown(f"📥 {i}/{len(urls)}: Fetching {url}...\\n\\n")
                try:
                    md_path = await converter.fetch_and_convert(url)
                    if md_path:
                        markdown_paths.append(md_path)
                        await tracer.markdown(f"✅ Converted: {md_path.name}\\n\\n")
                    else:
                        await tracer.markdown(f"❌ Failed to fetch URL\\n\\n")
                except Exception as e:
                    logger.error(f"URL conversion failed for {url}: {e}")
                    await tracer.markdown(f"❌ Error: {str(e)}\\n\\n")

        elif input_type == "documents":
            # Process uploaded documents
            await tracer.markdown("📁 Converting uploaded documents...\\n\\n")

            documents = inputs.get("documents", [])
            documents = documents[:max_items]  # Apply safety limit

            converter = DocumentConverter()

            # Create temporary directory for uploaded files
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                for i, doc in enumerate(documents, 1):
                    filename = doc.get("filename", f"document_{i}")
                    content = doc.get("content", b"")

                    await tracer.markdown(f"📄 {i}/{len(documents)}: Converting {filename}...\\n\\n")

                    try:
                        # Save uploaded file to temp location
                        temp_file = temp_path / filename
                        with open(temp_file, "wb") as f:
                            if isinstance(content, bytes):
                                f.write(content)
                            else:
                                f.write(content.encode())

                        # Also save to documents_raw for transparency
                        raw_dir = Path("data/input/documents_raw")
                        raw_dir.mkdir(parents=True, exist_ok=True)
                        raw_file = raw_dir / filename
                        with open(raw_file, "wb") as f:
                            if isinstance(content, bytes):
                                f.write(content)
                            else:
                                f.write(content.encode())

                        # Convert to markdown
                        md_path = await converter.convert_and_save(temp_file)
                        markdown_paths.append(md_path)
                        await tracer.markdown(f"✅ Converted: {md_path.name}\\n\\n")

                    except Exception as e:
                        logger.error(f"Document conversion failed for {filename}: {e}")
                        await tracer.markdown(f"❌ Error: {str(e)}\\n\\n")

        if not markdown_paths:
            await tracer.markdown("❌ No items could be converted to markdown.\\n\\n")
            return core.response.Markdown(
                f"""# {job_name} - Failed

## No Items Converted

All {input_type} failed to convert to markdown format.

**Job Name**: {job_name}
**Input Type**: {input_type.upper()}
**Execution Time**: {(datetime.now() - start_time).total_seconds():.1f}s

Please check the error messages above and try again.
"""
            )

        await tracer.markdown(
            f"✅ Successfully converted {len(markdown_paths)} item(s) to markdown.\\n\\n---\\n\\n"
        )

        # Step 3: Process markdown files using Flow 1's pipeline
        await tracer.markdown("## 🚀 Processing Documents\\n\\n")
        await tracer.markdown(f"Processing {len(markdown_paths)} markdown file(s)...\\n\\n")

        processor = MarkdownProcessor()
        processing_summary = await processor.process_markdown_files(markdown_paths)

        # Step 4: Display processing statistics
        await tracer.markdown("## ✅ Processing Complete\\n\\n")
        await tracer.markdown(
            f"""
**Processing Statistics:**
- **Total Items:** {processing_summary.get('processed', 0)}
- **Successful:** {processing_summary.get('successful', 0)}
- **Failed:** {processing_summary.get('failed', 0)}
- **Success Rate:** {processing_summary.get('success_rate', 0):.1f}%

**Knowledge Graph Growth:**
- **Total Entities:** {processing_summary.get('total_entities', 0)}
- **Total Relationships:** {processing_summary.get('total_relationships', 0)}
- **Avg Entities/Item:** {processing_summary.get('avg_entities_per_doc', 0):.1f}
- **Processing Time:** {processing_summary.get('processing_time', 0):.2f}s

---
"""
        )

        # Step 5: Generate comprehensive report using Flow 1's report generator
        total_time = (datetime.now() - start_time).total_seconds()
        report_generator = IngestionReportGenerator()

        # Prepare configuration for report generator
        config = {
            "job_name": job_name,
            "source_path": f"Ad-hoc {input_type.upper()}",
            "document_limit": max_items,
            "clear_data": False,
            "enable_communities": False,
            "graph_group_id": os.getenv("GRAPHITI_GROUP_ID", "political_monitoring_v2"),
            "neo4j_uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        }

        # Generate the comprehensive report
        report_content = await report_generator.generate_report(
            processing_results=processing_summary.get("results", []),
            communities=[],  # Flow 1C doesn't build communities
            config=config,
            job_name=job_name,
        )

        await tracer.markdown("### ✅ Analysis Complete! Report ready for viewing.")

        return core.response.Markdown(report_content)

    except Exception as e:
        error_msg = f"Ad-hoc processing failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await tracer.markdown(f"❌ **Error**: {error_msg}\\n\\n")

        return core.response.Markdown(
            f"""# {job_name} - Failed

**Error Details:**
```
{error_msg}
```

**Troubleshooting Steps:**
1. For URLs: Check that URLs are accessible and contain article content
2. For Documents: Verify file formats are supported (PDF/DOCX/TXT/PPT/PPTX)
3. Check that Neo4j is running: `docker ps | grep neo4j`
4. Verify environment variables in `.env` file
5. Review logs for detailed error information

**Job Name**: {job_name}
**Input Type**: {input_type.upper()}
**Execution Time**: {(datetime.now() - start_time).total_seconds():.1f}s

Please check the logs for more details.
"""
        )
