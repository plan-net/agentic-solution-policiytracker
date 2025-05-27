"""
Political Document Processor for Graphiti Integration.

This module provides the core document processing pipeline that extracts political
entities and relationships using LLM prompts and stores them in Graphiti temporal
knowledge graphs.

Version: 0.2.0 - Direct Graphiti API Integration
"""

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

from graphiti_core import Graphiti
from pydantic import BaseModel, Field

from src.llm.base_client import BaseLLMClient
from src.models.content import DocumentMetadata
from src.processors.document_reader import DocumentReader
from src.utils.exceptions import ConfigurationError, DocumentProcessingError

from .political_schema_v2 import (
    ExtractionResult,
    create_entity_from_dict,
    create_relationship_from_dict,
)

logger = logging.getLogger(__name__)


class ProcessingResult(BaseModel):
    """Result of document processing operation."""

    document_path: str = Field(..., description="Path to processed document")
    episode_id: Optional[str] = Field(None, description="Graphiti episode UUID")
    entities_extracted: int = Field(0, description="Number of entities extracted")
    relationships_extracted: int = Field(0, description="Number of relationships extracted")
    processing_time_seconds: float = Field(0.0, description="Processing duration")
    success: bool = Field(False, description="Whether processing succeeded")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    extraction_confidence: Optional[float] = Field(None, description="Overall confidence score")
    business_impact_level: Optional[str] = Field(
        None, description="High/Medium/Low business impact"
    )


class GraphitiConfig(BaseModel):
    """Configuration for Graphiti client connection."""

    neo4j_uri: str = Field(..., description="Neo4j connection URI")
    neo4j_user: str = Field(..., description="Neo4j username")
    neo4j_password: str = Field(..., description="Neo4j password")
    group_id: str = Field(default="political_docs", description="Graphiti group ID for episodes")


class PoliticalDocumentProcessor:
    """
    Core processor for political documents using Direct Graphiti API.

    This processor:
    1. Extracts text from political documents
    2. Uses LLM prompts to extract entities and relationships
    3. Creates structured episodes for Graphiti ingestion
    4. Stores results in temporal knowledge graph
    5. Provides processing statistics and error handling
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        graphiti_config: GraphitiConfig,
        prompts_dir: Optional[Path] = None,
    ):
        self.llm_client = llm_client
        self.graphiti_config = graphiti_config
        self.prompts_dir = prompts_dir or Path(__file__).parent.parent / "prompts"
        self.document_reader = DocumentReader()
        self.graphiti_client: Optional[Graphiti] = None

        # Load prompts
        self._load_prompts()

    def _load_prompts(self) -> None:
        """Load prompt templates from markdown files."""
        try:
            # Entity extraction prompt
            entity_prompt_path = self.prompts_dir / "political" / "entity_extraction.md"
            self.entity_extraction_prompt = self._load_prompt_file(entity_prompt_path)

            # Episode creation prompt
            episode_prompt_path = self.prompts_dir / "graphiti" / "episode_creation.md"
            self.episode_creation_prompt = self._load_prompt_file(episode_prompt_path)

            # Relationship analysis prompt
            relationship_prompt_path = self.prompts_dir / "political" / "relationship_analysis.md"
            self.relationship_analysis_prompt = self._load_prompt_file(relationship_prompt_path)

            logger.info("Successfully loaded prompt templates")

        except Exception as e:
            logger.error(f"Failed to load prompts: {e}")
            raise DocumentProcessingError("prompts", f"Prompt loading failed: {e}")

    def _load_prompt_file(self, prompt_path: Path) -> str:
        """Load prompt content from markdown file, extracting content after frontmatter."""
        try:
            content = prompt_path.read_text(encoding="utf-8")

            # Extract content after frontmatter (after second ---)
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    return parts[2].strip()

            return content.strip()

        except Exception as e:
            logger.error(f"Failed to load prompt from {prompt_path}: {e}")
            raise DocumentProcessingError(str(prompt_path), f"Failed to load prompt: {e}")

    async def __aenter__(self):
        """Async context manager entry - initialize Graphiti client."""
        try:
            self.graphiti_client = Graphiti(
                self.graphiti_config.neo4j_uri,
                self.graphiti_config.neo4j_user,
                self.graphiti_config.neo4j_password,
            )
            await self.graphiti_client.build_indices_and_constraints()
            logger.info("Graphiti client initialized successfully")
            return self

        except Exception as e:
            logger.error(f"Failed to initialize Graphiti client: {e}")
            raise ConfigurationError("graphiti", f"Graphiti initialization failed: {e}")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup Graphiti client."""
        if self.graphiti_client:
            try:
                # Close Graphiti client if it has a close method
                if hasattr(self.graphiti_client, "close"):
                    await self.graphiti_client.close()
                logger.info("Graphiti client closed successfully")
            except Exception as e:
                logger.warning(f"Error closing Graphiti client: {e}")

    async def process_document(self, document_path: Path) -> ProcessingResult:
        """
        Process a single political document through the complete pipeline.

        Args:
            document_path: Path to the document to process

        Returns:
            ProcessingResult with processing statistics and results
        """
        start_time = datetime.now()
        result = ProcessingResult(document_path=str(document_path))

        try:
            logger.info(f"Processing document: {document_path}")

            # Step 1: Extract document content and metadata
            document_content, document_metadata = await self._extract_document_content(
                document_path
            )

            # Step 2: Extract entities and relationships using LLM
            extraction_result = await self._extract_entities_and_relationships(
                document_content, document_metadata
            )

            # Step 3: Create structured episode for Graphiti
            episode_content = await self._create_episode_content(
                document_content, document_metadata, extraction_result
            )

            # Step 4: Store episode in Graphiti
            episode_result = await self._store_episode_in_graphiti(
                episode_content, document_metadata
            )

            # Step 5: Update processing result
            processing_time = (datetime.now() - start_time).total_seconds()

            result.episode_id = episode_result.episode.uuid
            result.entities_extracted = len(episode_result.nodes)
            result.relationships_extracted = (
                len(episode_result.episode.entity_edges)
                if episode_result.episode.entity_edges
                else 0
            )
            result.processing_time_seconds = processing_time
            result.success = True
            result.extraction_confidence = extraction_result.extraction_confidence
            result.business_impact_level = extraction_result.processing_metadata.get(
                "business_impact_level"
            )

            logger.info(
                f"Successfully processed {document_path}: "
                f"{result.entities_extracted} entities, "
                f"{result.relationships_extracted} relationships, "
                f"{processing_time:.2f}s"
            )

        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            result.processing_time_seconds = processing_time
            result.success = False
            result.error_message = str(e)

            logger.error(f"Failed to process {document_path}: {e}")

        return result

    async def _extract_document_content(self, document_path: Path) -> tuple[str, DocumentMetadata]:
        """Extract text content and metadata from document."""
        try:
            # Read document content and metadata
            content, metadata = await self.document_reader.read_document(str(document_path))

            return content, metadata

        except Exception as e:
            raise DocumentProcessingError(
                str(document_path), f"Document content extraction failed: {e}"
            )

    def _detect_content_type(self, document_path: Path) -> str:
        """Detect document content type from file extension."""
        suffix = document_path.suffix.lower()
        content_type_map = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
            ".txt": "text/plain",
            ".md": "text/markdown",
        }
        return content_type_map.get(suffix, "text/plain")

    async def _extract_entities_and_relationships(
        self, content: str, metadata: DocumentMetadata
    ) -> ExtractionResult:
        """Extract political entities and relationships using LLM."""
        try:
            # Prepare the extraction prompt with document content
            prompt = f"{self.entity_extraction_prompt}\n\n## DOCUMENT TO ANALYZE:\n\n{content}"

            # Call LLM for entity extraction
            response = await self.llm_client.generate_response(
                prompt=prompt,
                system_message="You are an expert political and regulatory analyst. Extract entities and relationships as specified in the prompt.",
                response_format="json",
            )

            # Parse LLM response
            extraction_data = json.loads(response)

            # Convert to structured objects
            entities = []
            for entity_data in extraction_data.get("entities", []):
                try:
                    entity = create_entity_from_dict(
                        {
                            "name": entity_data["name"],
                            "entity_type": entity_data["type"],
                            "properties": entity_data.get("properties", {}),
                            "jurisdiction": entity_data.get("jurisdiction"),
                            "confidence_score": entity_data.get("properties", {}).get(
                                "confidence", 0.5
                            ),
                        }
                    )
                    entities.append(entity)
                except Exception as e:
                    logger.warning(f"Failed to create entity from {entity_data}: {e}")

            relationships = []
            for rel_data in extraction_data.get("relationships", []):
                try:
                    relationship = create_relationship_from_dict(
                        {
                            "source_entity": rel_data["source"],
                            "target_entity": rel_data["target"],
                            "relationship_type": rel_data["type"],
                            "properties": rel_data.get("properties", {}),
                            "confidence_score": rel_data.get("properties", {}).get(
                                "confidence", 0.5
                            ),
                        }
                    )
                    relationships.append(relationship)
                except Exception as e:
                    logger.warning(f"Failed to create relationship from {rel_data}: {e}")

            # Create extraction result
            extraction_result = ExtractionResult(
                entities=entities,
                relationships=relationships,
                document_id=metadata.source,
                extraction_confidence=extraction_data.get("metadata", {}).get(
                    "extraction_confidence", 0.7
                ),
                processing_metadata=extraction_data.get("metadata", {}),
            )

            logger.info(
                f"Extracted {len(entities)} entities and {len(relationships)} relationships"
            )
            return extraction_result

        except Exception as e:
            raise DocumentProcessingError(metadata.source, f"Entity extraction failed: {e}")

    async def _create_episode_content(
        self, content: str, metadata: DocumentMetadata, extraction_result: ExtractionResult
    ) -> str:
        """Create structured episode content optimized for Graphiti ingestion."""
        try:
            # Generate episode name following convention
            doc_date = metadata.modified_at or datetime.now()
            episode_name = self._generate_episode_name(metadata.source, doc_date)

            # Structure episode content
            episode_content = f"""
POLITICAL DOCUMENT ANALYSIS
Title: {metadata.source}
Date: {doc_date.strftime('%Y-%m-%d')}
Type: Political/Regulatory Document
Source: Document Processing Pipeline

DOCUMENT CONTENT:
{content}

EXTRACTED METADATA:
Entities Found: {len(extraction_result.entities)}
Relationships Found: {len(extraction_result.relationships)}
Extraction Confidence: {extraction_result.extraction_confidence:.2f}
Business Impact Level: {extraction_result.processing_metadata.get('business_impact_level', 'Unknown')}
Key Policy Areas: {extraction_result.processing_metadata.get('affected_industries', [])}
Key Dates: {extraction_result.processing_metadata.get('key_dates', [])}
Jurisdictions: {extraction_result.processing_metadata.get('jurisdiction_focus', 'Unknown')}
            """.strip()

            return episode_content

        except Exception as e:
            raise DocumentProcessingError(metadata.source, f"Episode content creation failed: {e}")

    def _generate_episode_name(self, file_name: str, doc_date: datetime) -> str:
        """Generate episode name following naming convention."""
        # Clean file name for use in episode name
        clean_name = Path(file_name).stem.lower()
        clean_name = "".join(c if c.isalnum() else "_" for c in clean_name)
        clean_name = clean_name[:50]  # Limit length

        # Generate timestamp
        timestamp = doc_date.strftime("%Y%m%d_%H%M%S")

        return f"political_doc_{clean_name}_{timestamp}"

    async def _store_episode_in_graphiti(self, episode_content: str, metadata: DocumentMetadata):
        """Store structured episode in Graphiti temporal knowledge graph."""
        try:
            if not self.graphiti_client:
                raise ConfigurationError("graphiti", "Graphiti client not initialized")

            # Determine reference time (document date or current time)
            reference_time = metadata.modified_at or datetime.now(UTC)
            if reference_time.tzinfo is None:
                reference_time = reference_time.replace(tzinfo=UTC)

            # Generate episode name
            episode_name = self._generate_episode_name(metadata.source, reference_time)

            # Create episode in Graphiti
            result = await self.graphiti_client.add_episode(
                name=episode_name,
                episode_body=episode_content,
                source="text",
                source_description=f"Political document: {metadata.source}",
                reference_time=reference_time,
            )

            logger.info(f"Created Graphiti episode: {episode_name} (ID: {result.episode.uuid})")
            return result

        except Exception as e:
            raise DocumentProcessingError(metadata.source, f"Graphiti episode creation failed: {e}")

    async def process_documents_batch(
        self, document_paths: list[Path], batch_size: int = 3
    ) -> list[ProcessingResult]:
        """
        Process multiple documents in batches to avoid overwhelming the system.

        Args:
            document_paths: List of document paths to process
            batch_size: Number of documents to process concurrently

        Returns:
            List of ProcessingResult objects
        """
        results = []

        logger.info(f"Processing {len(document_paths)} documents in batches of {batch_size}")

        for i in range(0, len(document_paths), batch_size):
            batch = document_paths[i : i + batch_size]

            logger.info(f"Processing batch {i // batch_size + 1}: {len(batch)} documents")

            # Process batch concurrently
            batch_tasks = [self.process_document(doc_path) for doc_path in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Handle exceptions in batch results
            for doc_path, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    error_result = ProcessingResult(
                        document_path=str(doc_path), success=False, error_message=str(result)
                    )
                    results.append(error_result)
                    logger.error(f"Batch processing error for {doc_path}: {result}")
                else:
                    results.append(result)

            # Small delay between batches to avoid overwhelming the system
            if i + batch_size < len(document_paths):
                await asyncio.sleep(1)

        # Generate summary statistics
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_entities = sum(r.entities_extracted for r in results if r.success)
        total_relationships = sum(r.relationships_extracted for r in results if r.success)

        logger.info(
            f"Batch processing complete: {successful} successful, {failed} failed, "
            f"{total_entities} total entities, {total_relationships} total relationships"
        )

        return results

    async def search_entities(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Search for entities in the Graphiti knowledge graph.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            List of entity dictionaries
        """
        try:
            if not self.graphiti_client:
                raise ConfigurationError("graphiti", "Graphiti client not initialized")

            # Perform search using Graphiti
            search_results = await self.graphiti_client.search(query)

            # Convert results to structured format
            entities = []
            if hasattr(search_results, "nodes"):
                for node in search_results.nodes[:limit]:
                    entities.append(
                        {
                            "name": node.name,
                            "labels": node.labels,
                            "uuid": node.uuid,
                            "created_at": node.created_at.isoformat() if node.created_at else None,
                            "group_id": getattr(node, "group_id", None),
                        }
                    )

            logger.info(f"Search query '{query}' returned {len(entities)} entities")
            return entities

        except Exception as e:
            logger.error(f"Entity search failed: {e}")
            raise DocumentProcessingError("search", f"Search failed: {e}")

    def get_processing_statistics(self, results: list[ProcessingResult]) -> dict[str, Any]:
        """Generate comprehensive processing statistics."""
        if not results:
            return {"message": "No processing results to analyze"}

        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]

        stats = {
            "summary": {
                "total_documents": len(results),
                "successful": len(successful_results),
                "failed": len(failed_results),
                "success_rate": len(successful_results) / len(results) if results else 0,
            },
            "processing_performance": {
                "total_processing_time": sum(r.processing_time_seconds for r in results),
                "average_processing_time": sum(r.processing_time_seconds for r in results)
                / len(results),
                "fastest_processing": min(r.processing_time_seconds for r in results),
                "slowest_processing": max(r.processing_time_seconds for r in results),
            },
            "extraction_performance": {
                "total_entities": sum(r.entities_extracted for r in successful_results),
                "total_relationships": sum(r.relationships_extracted for r in successful_results),
                "average_entities_per_doc": sum(r.entities_extracted for r in successful_results)
                / len(successful_results)
                if successful_results
                else 0,
                "average_relationships_per_doc": sum(
                    r.relationships_extracted for r in successful_results
                )
                / len(successful_results)
                if successful_results
                else 0,
            },
            "quality_metrics": {
                "average_confidence": sum(r.extraction_confidence or 0 for r in successful_results)
                / len(successful_results)
                if successful_results
                else 0,
                "high_confidence_documents": sum(
                    1 for r in successful_results if (r.extraction_confidence or 0) > 0.8
                ),
                "business_impact_distribution": {
                    level: sum(1 for r in successful_results if r.business_impact_level == level)
                    for level in ["high", "medium", "low"]
                },
            },
            "error_analysis": {
                "failed_documents": [
                    {"path": r.document_path, "error": r.error_message} for r in failed_results
                ],
                "common_error_types": {},  # Could be enhanced to categorize errors
            },
        }

        return stats
