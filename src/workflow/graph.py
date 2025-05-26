from typing import Any, Optional

import structlog
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from src.config import settings
from src.integrations.azure_checkpoint import AzureCheckpointSaver
from src.models.job import Job
from src.workflow.nodes import (
    cluster_results,
    generate_report,
    load_context,
    load_documents,
    process_documents,
    process_graphrag_analysis,
    score_documents,
)
from src.workflow.state import WorkflowState

logger = structlog.get_logger()


def create_workflow() -> StateGraph:
    """Create and configure LangGraph workflow with checkpointing."""

    # Create workflow graph
    workflow = StateGraph(WorkflowState)

    # Add nodes
    workflow.add_node("load_documents", load_documents)
    workflow.add_node("load_context", load_context)
    workflow.add_node("process_documents", process_documents)
    workflow.add_node("score_documents", score_documents)
    workflow.add_node("process_graphrag_analysis", process_graphrag_analysis)
    workflow.add_node("cluster_results", cluster_results)
    workflow.add_node("generate_report", generate_report)

    # Define edges (sequential flow with GraphRAG between scoring and clustering)
    workflow.set_entry_point("load_documents")
    workflow.add_edge("load_documents", "load_context")
    workflow.add_edge("load_context", "process_documents")
    workflow.add_edge("process_documents", "score_documents")
    workflow.add_edge("score_documents", "process_graphrag_analysis")
    workflow.add_edge("process_graphrag_analysis", "cluster_results")
    workflow.add_edge("cluster_results", "generate_report")
    workflow.add_edge("generate_report", END)

    return workflow


def create_checkpointer(use_azure: bool = None) -> Optional[Any]:
    """Create appropriate checkpointer based on runtime storage mode."""
    if use_azure is None:
        use_azure = getattr(settings, "USE_AZURE_STORAGE", False)

    # Azure checkpointer implementation is incomplete - using memory checkpointer for all cases
    logger.info("Using memory checkpointer")
    return MemorySaver()


async def execute_workflow(
    workflow: StateGraph,
    job: Job,
    resume_from_checkpoint: Optional[str] = None,
    initial_state: Optional[Any] = None,
) -> dict[str, Any]:
    """Execute workflow for a job with checkpointing support."""
    try:
        logger.info(
            "Starting workflow execution",
            job_id=job.id,
            resume_from_checkpoint=resume_from_checkpoint,
        )

        # Create checkpointer with runtime storage mode
        use_azure = (
            initial_state.use_azure
            if initial_state
            else getattr(settings, "USE_AZURE_STORAGE", False)
        )
        checkpointer = create_checkpointer(use_azure)

        # Compile workflow with checkpointer
        compiled_workflow = workflow.compile(checkpointer=checkpointer)

        # Create workflow configuration
        config = {
            "configurable": {
                "thread_id": job.id,
            }
        }

        # If resuming from checkpoint, add checkpoint ID
        if resume_from_checkpoint:
            config["configurable"]["checkpoint_id"] = resume_from_checkpoint
            logger.info(
                "Resuming workflow from checkpoint",
                job_id=job.id,
                checkpoint_id=resume_from_checkpoint,
            )

        # Use provided initial state or create a new one
        if initial_state is None:
            initial_state = WorkflowState(job_id=job.id, job_request=job.request)

        # Execute workflow with checkpointing
        final_state = await compiled_workflow.ainvoke(initial_state, config=config)

        # Clean up old checkpoints if using Azure Storage
        if isinstance(checkpointer, AzureCheckpointSaver):
            try:
                deleted_count = await checkpointer.cleanup_old_checkpoints(job.id, keep_last=5)
                logger.debug(
                    "Cleaned up old checkpoints", job_id=job.id, deleted_count=deleted_count
                )
            except Exception as e:
                logger.warning("Failed to cleanup old checkpoints", job_id=job.id, error=str(e))

        # Extract results from LangGraph state (AddableValuesDict)
        # Access fields directly since LangGraph returns a dict-like object
        result = {
            "report_file": final_state.get("report_file_path"),
            "checkpointing_enabled": checkpointer is not None,
            "checkpointer_type": "azure_storage"
            if isinstance(checkpointer, AzureCheckpointSaver)
            else "memory",
            "metrics": {
                "total_documents": len(final_state.get("file_paths", [])),
                "processed_documents": len(final_state.get("documents", [])),
                "failed_documents": len(final_state.get("failed_documents", [])),
                "scored_documents": len(final_state.get("scoring_results", [])),
                "errors": final_state.get("errors", []),
                "progress": final_state.get("current_progress", {}),
                "graphrag_enabled": final_state.get("graphrag_enabled", False),
                "graphrag_metrics": {
                    "search_results": len(final_state.get("graphrag_search_results", [])),
                    "entities_analyzed": final_state.get("graphrag_entity_analysis", {}).get(
                        "entities_analyzed", 0
                    ),
                    "relationships_analyzed": final_state.get("graphrag_relationship_insights", {})
                    .get("network_metrics", {})
                    .get("total_relationships", 0),
                    "comparative_analysis_performed": final_state.get(
                        "graphrag_comparative_analysis"
                    )
                    is not None,
                }
                if final_state.get("graphrag_enabled")
                else None,
                "summary": {
                    "total_documents_analyzed": len(final_state.get("documents", [])),
                    "high_priority_count": len(
                        [r for r in final_state.get("scoring_results", []) if r.master_score >= 75]
                    ),
                    "average_score": sum(
                        r.master_score for r in final_state.get("scoring_results", [])
                    )
                    / len(final_state.get("scoring_results", []))
                    if final_state.get("scoring_results")
                    else 0,
                },
            },
        }

        logger.info(
            "Workflow execution completed successfully",
            job_id=job.id,
            checkpointer_type=result["checkpointer_type"],
        )
        return result

    except Exception as e:
        logger.error("Workflow execution failed", job_id=job.id, error=str(e))
        raise


async def get_workflow_checkpoints(job_id: str) -> list[dict[str, Any]]:
    """Get available checkpoints for a workflow."""
    try:
        use_azure = getattr(settings, "USE_AZURE_STORAGE", False)

        if not use_azure:
            logger.info("Memory checkpointer doesn't support checkpoint listing")
            return []

        checkpointer = AzureCheckpointSaver()

        # List checkpoints for this job/thread
        prefix = f"threads/{job_id}/checkpoints/"
        blobs = await checkpointer.azure_client.list_blobs("checkpoints", prefix=prefix)

        checkpoints = []
        for blob in blobs:
            if blob.name.endswith(".json") and "/writes/" not in blob.name:
                checkpoint_id = blob.name.split("/")[-1].replace(".json", "")
                checkpoints.append(
                    {
                        "checkpoint_id": checkpoint_id,
                        "created_at": blob.last_modified.isoformat()
                        if blob.last_modified
                        else None,
                        "size_bytes": blob.size or 0,
                    }
                )

        # Sort by creation time (newest first)
        checkpoints.sort(key=lambda c: c["created_at"] or "", reverse=True)

        logger.info(
            "Retrieved workflow checkpoints", job_id=job_id, checkpoint_count=len(checkpoints)
        )

        return checkpoints

    except Exception as e:
        logger.error("Failed to get workflow checkpoints", job_id=job_id, error=str(e))
        return []
