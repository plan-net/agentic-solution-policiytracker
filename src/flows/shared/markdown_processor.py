"""
Unified Markdown Processor

Processes markdown files using Flow 1's proven pipeline and updates
the document tracking file. Shared by both document and URL workflows.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import structlog
from graphiti_core import Graphiti

# Configure logging for Ray environment
from src.flows.data_ingestion.logging_config import configure_logging

configure_logging()

from src.flows.data_ingestion.document_processor import SimpleDocumentProcessor
from src.flows.data_ingestion.document_tracker import DocumentTracker

logger = structlog.get_logger()

# Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")


class MarkdownProcessor:
    """Process markdown files using Flow 1's processing pipeline."""

    def __init__(self):
        self.tracker = DocumentTracker()
        logger.info("Initialized MarkdownProcessor with Flow 1 pipeline")

    async def process_markdown_files(
        self, markdown_paths: List[Path]
    ) -> Dict[str, Any]:
        """
        Process markdown files using Flow 1's SimpleDocumentProcessor.

        Args:
            markdown_paths: List of markdown file paths to process

        Returns:
            Processing results with statistics
        """
        if not markdown_paths:
            logger.warning("No markdown files to process")
            return {
                "processed": 0,
                "successful": 0,
                "failed": 0,
                "results": [],
                "processing_time": 0,
            }

        start_time = datetime.now()

        # Initialize Flow 1's processor
        processor = SimpleDocumentProcessor(self.tracker, clear_mode=False)

        # Initialize Graphiti client with APISIX routing
        from src.flows.shared.apisix_llm_client import (
            AgentContext,
            create_graphiti_apisix_config,
        )

        # Create agent context for cost tracking
        agent_context = AgentContext(
            agent_type="kodosumi_flow",
            agent_name="markdown_processor",
            flow_name="adhoc_processing",
        )

        # Get APISIX-configured LLM client
        llm_client, note = create_graphiti_apisix_config(agent_context)

        # Initialize Graphiti with APISIX routing
        graphiti_client = Graphiti(
            NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, llm_client=llm_client
        )
        await graphiti_client.build_indices_and_constraints()

        logger.info("Graphiti client initialized with APISIX routing")
        logger.debug(note)  # Log the Week 1 limitation note

        logger.info(f"Processing {len(markdown_paths)} markdown files...")

        # Process each markdown file
        processing_results = []
        for md_path in markdown_paths:
            try:
                logger.info(f"Processing: {md_path.name}")
                result = await processor.process_document(md_path, graphiti_client)
                processing_results.append(result)
            except Exception as e:
                logger.error(f"Failed to process {md_path.name}: {e}", exc_info=True)
                processing_results.append({
                    "file_path": str(md_path),
                    "success": False,
                    "error": str(e),
                    "processed_at": datetime.now().isoformat(),
                })

        # Close graphiti client
        await graphiti_client.close()

        # Calculate statistics
        successful = [r for r in processing_results if r.get("success")]
        failed = [r for r in processing_results if not r.get("success")]
        processing_time = (datetime.now() - start_time).total_seconds()

        # Get processor statistics
        stats = processor.get_processing_stats()

        result_summary = {
            "processed": len(processing_results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": (
                (len(successful) / len(processing_results) * 100)
                if processing_results
                else 0
            ),
            "processing_time": processing_time,
            "total_entities": stats.get("total_entities", 0),
            "total_relationships": stats.get("total_relationships", 0),
            "avg_entities_per_doc": stats.get("avg_entities_per_doc", 0),
            "results": processing_results,
        }

        logger.info(
            f"Processing complete: {len(successful)}/{len(processing_results)} successful",
            processing_time=f"{processing_time:.2f}s",
        )

        return result_summary
