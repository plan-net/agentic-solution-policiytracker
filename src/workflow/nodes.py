import os
import time
from datetime import datetime

import structlog
import yaml

from src.analysis.aggregator import ResultAggregator
from src.analysis.topic_clusterer import TopicClusterer
from src.config import settings
from src.graphrag.knowledge_builder import PoliticalKnowledgeBuilder
from src.integrations.azure_storage import AzureStorageClient
from src.output.report_generator import ReportGenerator
from src.processors.batch_loader import BatchDocumentLoader
from src.processors.content_processor import ContentProcessor
from src.scoring.hybrid_engine import HybridScoringEngine
from src.utils.exceptions import WorkflowError
from src.utils.validators import validate_context_file, validate_directory_exists
from src.workflow.state import WorkflowState

logger = structlog.get_logger()


async def load_documents(state: WorkflowState) -> WorkflowState:
    """Load and validate documents from input folder or Azure Storage."""
    try:
        logger.info("Starting document loading", job_id=state.job_id)

        input_source = state.job_request.input_folder

        # Use runtime storage mode from state
        use_azure = state.use_azure

        if use_azure:
            logger.info("Using Azure Storage for document loading", job_id=state.job_id)
            # For Azure Storage, input_source is the full path, don't pass job_id
            loader = BatchDocumentLoader(use_azure=True)
            file_paths = await loader.discover_files(input_source)
        else:
            # Validate local input folder
            if not validate_directory_exists(input_source):
                raise WorkflowError(
                    state.job_id, "load_documents", f"Input folder not accessible: {input_source}"
                )

            loader = BatchDocumentLoader(use_azure=False)
            file_paths = await loader.discover_files(input_source)

        if not file_paths:
            source_type = "Azure Storage" if use_azure else "input folder"
            raise WorkflowError(
                state.job_id, "load_documents", f"No supported documents found in {source_type}"
            )

        logger.info(
            f"Discovered {len(file_paths)} documents",
            job_id=state.job_id,
            source_type="Azure Storage" if use_azure else "local",
        )

        state.file_paths = file_paths
        state.current_progress = {
            "stage": "documents_loaded",
            "documents_found": len(file_paths),
            "source_type": "azure_storage" if use_azure else "local_filesystem",
            "timestamp": datetime.now().isoformat(),
        }

        return state

    except Exception as e:
        error_msg = f"Failed to load documents: {str(e)}"
        state.errors.append(error_msg)
        logger.error(error_msg, job_id=state.job_id)
        raise WorkflowError(state.job_id, "load_documents", error_msg)


async def load_context(state: WorkflowState) -> WorkflowState:
    """Load client context from YAML file or Azure Storage."""
    try:
        logger.info("Loading context file", job_id=state.job_id)

        context_file = state.job_request.context_file
        use_azure = state.use_azure

        if use_azure:
            logger.info(
                "Loading context from Azure Storage", job_id=state.job_id, context_file=context_file
            )

            # Initialize Azure Storage client
            azure_client = AzureStorageClient()

            # Download context file from Azure Storage
            context_blob_data = await azure_client.download_blob("contexts", context_file)
            if not context_blob_data:
                raise WorkflowError(
                    state.job_id,
                    "load_context",
                    f"Context file not found in Azure Storage: {context_file}",
                )

            # Parse YAML from blob data
            context_data = yaml.safe_load(context_blob_data.decode("utf-8"))
        else:
            # Validate local context file
            validate_context_file(context_file)

            # Load YAML context from local file
            with open(context_file, encoding="utf-8") as f:
                context_data = yaml.safe_load(f)

        # Validate required fields
        required_fields = [
            "company_terms",
            "core_industries",
            "primary_markets",
            "strategic_themes",
        ]
        for field in required_fields:
            if field not in context_data:
                raise WorkflowError(
                    state.job_id, "load_context", f"Missing required field: {field}"
                )

        state.context = context_data
        state.current_progress = {
            "stage": "context_loaded",
            "context_file": context_file,
            "source_type": "azure_storage" if use_azure else "local_filesystem",
            "timestamp": datetime.now().isoformat(),
        }

        logger.info("Context loaded successfully", job_id=state.job_id)
        return state

    except Exception as e:
        error_msg = f"Failed to load context: {str(e)}"
        state.errors.append(error_msg)
        logger.error(error_msg, job_id=state.job_id)
        raise WorkflowError(state.job_id, "load_context", error_msg)


async def process_documents(state: WorkflowState) -> WorkflowState:
    """Process documents using Ray tasks with Azure Storage integration."""
    try:
        logger.info("Starting document processing", job_id=state.job_id)

        use_azure = state.use_azure
        processor = ContentProcessor(use_azure=use_azure)
        processed_docs = []
        failed_docs = []

        # Process documents (this will be enhanced with Ray tasks later)
        for i, file_path in enumerate(state.file_paths):
            try:
                doc = await processor.process_document(
                    file_path, f"doc_{i:03d}", job_id=state.job_id
                )
                processed_docs.append(doc)

                # Update progress
                progress_pct = ((i + 1) / len(state.file_paths)) * 100
                state.current_progress = {
                    "stage": "processing_documents",
                    "processed": i + 1,
                    "total": len(state.file_paths),
                    "progress_percent": round(progress_pct, 1),
                    "storage_type": "azure_storage" if use_azure else "local_filesystem",
                    "timestamp": datetime.now().isoformat(),
                }

            except Exception as e:
                failed_docs.append(
                    {
                        "file_path": file_path,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                logger.warning(
                    "Failed to process document",
                    job_id=state.job_id,
                    file_path=file_path,
                    error=str(e),
                )

        # Check if we have enough successful documents
        success_rate = len(processed_docs) / len(state.file_paths)
        if success_rate < 0.5:
            raise WorkflowError(
                state.job_id,
                "process_documents",
                f"Too many failed documents: {success_rate:.1%} success rate",
            )

        state.documents = processed_docs
        state.failed_documents = failed_docs

        logger.info(
            "Document processing completed",
            job_id=state.job_id,
            processed=len(processed_docs),
            failed=len(failed_docs),
            storage_type="Azure Storage" if use_azure else "local",
        )

        return state

    except Exception as e:
        error_msg = f"Document processing failed: {str(e)}"
        state.errors.append(error_msg)
        logger.error(error_msg, job_id=state.job_id)
        raise WorkflowError(state.job_id, "process_documents", error_msg)


async def score_documents(state: WorkflowState) -> WorkflowState:
    """Score documents using relevance engine."""
    try:
        logger.info("Starting document scoring", job_id=state.job_id)

        scoring_engine = HybridScoringEngine(state.context)
        scoring_results = []

        for i, document in enumerate(state.documents):
            try:
                start_time = time.time()
                result = await scoring_engine.score_document_hybrid(document, job_id=state.job_id)
                processing_time = (time.time() - start_time) * 1000

                # Add processing time to result
                result.processing_time_ms = processing_time
                scoring_results.append(result)

                # Update progress
                progress_pct = ((i + 1) / len(state.documents)) * 100
                state.current_progress = {
                    "stage": "scoring_documents",
                    "scored": i + 1,
                    "total": len(state.documents),
                    "progress_percent": round(progress_pct, 1),
                    "timestamp": datetime.now().isoformat(),
                }

            except Exception as e:
                logger.warning(
                    "Failed to score document",
                    job_id=state.job_id,
                    document_id=document.id,
                    error=str(e),
                )
                # Continue with other documents

        state.scoring_results = scoring_results

        logger.info("Document scoring completed", job_id=state.job_id, scored=len(scoring_results))

        return state

    except Exception as e:
        error_msg = f"Document scoring failed: {str(e)}"
        state.errors.append(error_msg)
        logger.error(error_msg, job_id=state.job_id)
        raise WorkflowError(state.job_id, "score_documents", error_msg)


async def cluster_results(state: WorkflowState) -> WorkflowState:
    """Cluster results by topic and priority."""
    try:
        logger.info("Starting result clustering", job_id=state.job_id)

        if not state.job_request.clustering_enabled:
            logger.info("Clustering disabled, skipping", job_id=state.job_id)
            state.current_progress = {
                "stage": "clustering_skipped",
                "timestamp": datetime.now().isoformat(),
            }
            return state

        # Topic clustering with context
        clusterer = TopicClusterer()
        topic_clusters = await clusterer.cluster_by_topic(
            state.scoring_results, state.context, state.job_id
        )

        # Result aggregation
        aggregator = ResultAggregator()
        priority_queues = aggregator.group_by_priority(state.scoring_results)

        # Store clustering results in state for report generation
        state.current_progress = {
            "stage": "clustering_completed",
            "topic_clusters": len(topic_clusters),
            "priority_queues": len(priority_queues),
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(
            "Result clustering completed", job_id=state.job_id, clusters=len(topic_clusters)
        )

        return state

    except Exception as e:
        error_msg = f"Result clustering failed: {str(e)}"
        state.errors.append(error_msg)
        logger.error(error_msg, job_id=state.job_id)
        raise WorkflowError(state.job_id, "cluster_results", error_msg)


async def generate_report(state: WorkflowState) -> WorkflowState:
    """Generate final markdown report and save to local or Azure Storage."""
    try:
        logger.info("Starting report generation", job_id=state.job_id)

        generator = ReportGenerator()
        use_azure = state.use_azure

        # Generate report data
        report_data = await generator.prepare_report_data(
            state.job_id,
            state.job_request.job_name,
            state.scoring_results,
            state.failed_documents,
            state.context,
            state.job_request.dict(),
        )

        report_filename = f"{state.job_request.job_name}_{state.job_id}_report.md"

        if use_azure:
            logger.info("Saving report to Azure Storage", job_id=state.job_id)

            # Generate markdown content
            report_content = await generator.generate_markdown_content(report_data)

            # Upload to Azure Storage
            azure_client = AzureStorageClient()
            blob_name = f"jobs/{state.job_id}/reports/{report_filename}"

            upload_success = await azure_client.upload_blob(
                "reports",
                blob_name,
                report_content,
                metadata={
                    "job_id": state.job_id,
                    "job_name": state.job_request.job_name,
                    "generated_at": datetime.now().isoformat(),
                    "document_count": str(len(state.scoring_results)),
                },
            )

            if not upload_success:
                raise WorkflowError(
                    state.job_id, "generate_report", "Failed to upload report to Azure Storage"
                )

            report_path = f"azure://{blob_name}"

        else:
            # Generate markdown file locally
            output_folder = settings.output_path
            os.makedirs(output_folder, exist_ok=True)

            report_path = os.path.join(output_folder, report_filename)
            await generator.generate_markdown_report(report_data, report_path)

        state.report_data = report_data
        state.report_file_path = report_path
        state.current_progress = {
            "stage": "report_generated",
            "report_file": report_path,
            "storage_type": "azure_storage" if use_azure else "local_filesystem",
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(
            "Report generation completed",
            job_id=state.job_id,
            report_path=report_path,
            storage_type="Azure Storage" if use_azure else "local",
        )

        return state

    except Exception as e:
        error_msg = f"Report generation failed: {str(e)}"
        state.errors.append(error_msg)
        logger.error(error_msg, job_id=state.job_id)
        raise WorkflowError(state.job_id, "generate_report", error_msg)


async def process_graphrag_analysis(state: WorkflowState) -> WorkflowState:
    """Process documents using GraphRAG for enhanced political intelligence insights.

    This node performs:
    1. GraphRAG search on processed documents
    2. Entity analysis using Langfuse prompts
    3. Relationship insights generation
    4. Comparative analysis with traditional results
    """
    try:
        # Skip GraphRAG processing if not enabled
        if not state.graphrag_enabled:
            logger.info("GraphRAG processing disabled, skipping", job_id=state.job_id)
            return state

        logger.info("Starting GraphRAG analysis", job_id=state.job_id)

        # Prepare company context from job request and client context
        company_context = {
            "terms": state.context.get("company_terms", []),
            "industries": state.context.get("core_industries", []),
            "markets": state.context.get("primary_markets", []),
            "themes": state.context.get("strategic_themes", []),
            "strategic_focus": state.job_request.job_name,
        }

        # Initialize GraphRAG knowledge builder
        builder = PoliticalKnowledgeBuilder(
            uri=settings.NEO4J_URI,
            username=settings.NEO4J_USERNAME,
            password=settings.NEO4J_PASSWORD,
            database=settings.NEO4J_DATABASE,
            openai_api_key=settings.OPENAI_API_KEY,
        )

        async with builder:
            # Perform GraphRAG search based on job name/topic
            search_query = state.job_request.job_name
            logger.info("Performing GraphRAG search", job_id=state.job_id, query=search_query)

            # Basic vector + fulltext search
            basic_search_results = await builder.search_documents(search_query, top_k=10)

            # Enhanced graph traversal search
            graph_traversal_results = await builder.search_with_graph_traversal(
                search_query, top_k=10
            )

            state.graphrag_search_results = basic_search_results
            logger.info(
                "GraphRAG search completed",
                job_id=state.job_id,
                basic_results=len(basic_search_results),
                graph_results=graph_traversal_results.get("total_results", 0),
            )

            # Entity analysis using Langfuse prompts
            logger.info("Performing GraphRAG entity analysis", job_id=state.job_id)
            entity_analysis = await builder.analyze_entities_with_langfuse(
                query_results=basic_search_results,
                company_context=company_context,
                query_topic=search_query,
                session_id=state.job_id,
            )
            state.graphrag_entity_analysis = entity_analysis

            entities_analyzed = entity_analysis.get("entities_analyzed", 0)
            relationships_analyzed = entity_analysis.get("relationships_analyzed", 0)
            logger.info(
                "Entity analysis completed",
                job_id=state.job_id,
                entities=entities_analyzed,
                relationships=relationships_analyzed,
            )

            # Relationship insights generation
            logger.info("Generating GraphRAG relationship insights", job_id=state.job_id)
            relationship_insights = await builder.generate_relationship_insights(
                query_results=basic_search_results,
                company_context=company_context,
                query_topic=search_query,
                session_id=state.job_id,
            )
            state.graphrag_relationship_insights = relationship_insights

            network_metrics = relationship_insights.get("network_metrics", {})
            logger.info(
                "Relationship insights completed",
                job_id=state.job_id,
                total_relationships=network_metrics.get("total_relationships", 0),
                entity_types=network_metrics.get("entity_types", 0),
            )

            # Comparative analysis with traditional results
            if state.scoring_results:
                logger.info("Performing comparative analysis", job_id=state.job_id)

                # Prepare traditional results summary
                traditional_results = {
                    "method": "hybrid_scoring_engine",
                    "total_documents": len(state.scoring_results),
                    "average_relevance": sum(r.master_score for r in state.scoring_results)
                    / len(state.scoring_results),
                    "average_confidence": sum(r.confidence_score for r in state.scoring_results)
                    / len(state.scoring_results),
                    "key_findings": [r.document_id for r in state.scoring_results[:5]],
                    "scoring_dimensions": ["relevance", "priority", "sentiment", "urgency"],
                }

                comparative_analysis = await builder.compare_with_traditional_analysis(
                    graphrag_results={
                        "entity_analysis": entity_analysis,
                        "relationship_insights": relationship_insights,
                    },
                    traditional_results=traditional_results,
                    company_context=company_context,
                    session_id=state.job_id,
                )
                state.graphrag_comparative_analysis = comparative_analysis

                logger.info(
                    "Comparative analysis completed",
                    job_id=state.job_id,
                    traditional_confidence=traditional_results.get("average_confidence", 0),
                    graphrag_confidence=comparative_analysis.get("confidence", 0),
                )

            # Update progress
            state.current_progress = {
                "stage": "graphrag_analysis_completed",
                "basic_search_results": len(basic_search_results),
                "graph_traversal_results": graph_traversal_results.get("total_results", 0),
                "entities_analyzed": entities_analyzed,
                "relationships_analyzed": relationships_analyzed,
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(
                "GraphRAG analysis completed successfully",
                job_id=state.job_id,
                basic_results=len(basic_search_results),
                entities=entities_analyzed,
                relationships=relationships_analyzed,
            )

        return state

    except Exception as e:
        error_msg = f"GraphRAG analysis failed: {str(e)}"
        state.errors.append(error_msg)
        logger.error(error_msg, job_id=state.job_id, exc_info=True)

        # Don't raise WorkflowError - make GraphRAG optional
        # Just log the error and continue with traditional workflow
        logger.warning("Continuing workflow without GraphRAG analysis", job_id=state.job_id)
        return state
