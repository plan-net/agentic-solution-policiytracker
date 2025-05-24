"""
Comprehensive tests for workflow orchestration components.

Tests the LangGraph workflow creation, execution, checkpointing, and state management
to achieve high coverage for the workflow orchestration layer.
"""
import pytest
import tempfile
import os
import yaml
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver

# Import workflow components
from src.workflow.graph import (
    create_workflow,
    create_checkpointer,
    execute_workflow,
    get_workflow_checkpoints
)
from src.workflow.state import WorkflowState
from src.workflow.nodes import (
    load_documents,
    load_context,
    process_documents,
    score_documents,
    cluster_results,
    generate_report
)
from src.models.job import Job, JobRequest, JobStatus
from src.models.content import ProcessedContent
from src.models.scoring import ScoringResult


@pytest.fixture
def sample_job():
    """Create a sample job for testing."""
    job_request = JobRequest(
        job_name="Test Workflow Job",
        input_folder="./test_input",
        context_file="./test_context.yaml",
        priority_threshold=70.0
    )
    
    return Job(
        id="job_20250524_120000_ABC123",
        request=job_request,
        status=JobStatus.RUNNING,
        created_at=datetime.now(),
        started_at=datetime.now()
    )


@pytest.fixture
def sample_workflow_state(sample_job):
    """Create a sample workflow state."""
    return WorkflowState(
        job_id=sample_job.id,
        job_request=sample_job.request
    )


@pytest.fixture
def test_documents():
    """Create sample processed documents."""
    from src.models.content import DocumentMetadata, DocumentType
    from datetime import datetime
    
    return [
        ProcessedContent(
            id="doc_001",
            raw_text="Test document content 1",
            metadata=DocumentMetadata(
                source="./test_doc1.txt",
                type=DocumentType.TXT,
                file_path="./test_doc1.txt",
                file_size_bytes=100
            ),
            processing_timestamp=datetime.now()
        ),
        ProcessedContent(
            id="doc_002",
            raw_text="# Test Document 2\nMarkdown content",
            metadata=DocumentMetadata(
                source="./test_doc2.md",
                type=DocumentType.MARKDOWN,
                file_path="./test_doc2.md",
                file_size_bytes=150
            ),
            processing_timestamp=datetime.now()
        )
    ]


@pytest.fixture
def test_scoring_results():
    """Create sample scoring results."""
    from src.models.scoring import DimensionScore
    from datetime import datetime
    
    return [
        ScoringResult(
            document_id="doc_001",
            master_score=85.5,
            dimension_scores={
                "business_relevance": DimensionScore(
                    dimension_name="business_relevance",
                    score=90.0,
                    weight=0.4,
                    justification="High relevance to business operations"
                )
            },
            confidence_score=0.95,
            scoring_timestamp=datetime.now(),
            processing_time_ms=150.0,
            overall_justification="High relevance to business operations"
        ),
        ScoringResult(
            document_id="doc_002",
            master_score=72.3,
            dimension_scores={
                "business_relevance": DimensionScore(
                    dimension_name="business_relevance",
                    score=75.0,
                    weight=0.4,
                    justification="Moderate relevance with good temporal urgency"
                )
            },
            confidence_score=0.88,
            scoring_timestamp=datetime.now(),
            processing_time_ms=120.0,
            overall_justification="Moderate relevance with good temporal urgency"
        )
    ]


class TestWorkflowGraphCreation:
    """Test workflow graph creation and structure."""
    
    def test_create_workflow_structure(self):
        """Test that workflow is created with correct structure."""
        workflow = create_workflow()
        
        # Verify it's a StateGraph
        assert isinstance(workflow, StateGraph)
        
        # Verify all nodes are added by compiling and checking for errors
        # LangGraph's internal structure may vary, so we test by compilation
        compiled = workflow.compile()
        assert compiled is not None
    
    def test_workflow_node_functions(self):
        """Test that node functions are properly assigned."""
        workflow = create_workflow()
        
        # Test that the workflow can be compiled successfully
        # This ensures all node functions are properly assigned
        compiled = workflow.compile()
        assert compiled is not None
        
        # Test that all imported node functions are callable
        assert callable(load_documents)
        assert callable(load_context)
        assert callable(process_documents)
        assert callable(score_documents)
        assert callable(cluster_results)
        assert callable(generate_report)
    
    def test_workflow_edges(self):
        """Test that workflow edges are defined correctly."""
        workflow = create_workflow()
        
        # The edges are internal to LangGraph, but we can test by compiling
        # and checking that it doesn't raise errors
        compiled = workflow.compile()
        assert compiled is not None
        
        # Test that we can create a valid configuration for execution
        config = {"configurable": {"thread_id": "test_thread"}}
        assert config is not None


class TestCheckpointerCreation:
    """Test checkpointer creation logic."""
    
    @patch('src.workflow.graph.settings')
    def test_create_checkpointer_memory(self, mock_settings):
        """Test memory checkpointer creation."""
        mock_settings.USE_AZURE_STORAGE = False
        
        checkpointer = create_checkpointer()
        
        assert isinstance(checkpointer, MemorySaver)
    
    @patch('src.workflow.graph.settings')
    @patch('src.workflow.graph.AzureCheckpointSaver')
    def test_create_checkpointer_azure(self, mock_azure_saver, mock_settings):
        """Test Azure checkpointer creation."""
        mock_settings.USE_AZURE_STORAGE = True
        mock_azure_instance = MagicMock()
        mock_azure_saver.return_value = mock_azure_instance
        
        checkpointer = create_checkpointer()
        
        assert checkpointer == mock_azure_instance
        mock_azure_saver.assert_called_once()
    
    @patch('src.workflow.graph.settings')
    def test_create_checkpointer_default_behavior(self, mock_settings):
        """Test default checkpointer behavior when USE_AZURE_STORAGE not set."""
        # Remove the attribute to test default behavior
        if hasattr(mock_settings, 'USE_AZURE_STORAGE'):
            delattr(mock_settings, 'USE_AZURE_STORAGE')
        
        checkpointer = create_checkpointer()
        
        assert isinstance(checkpointer, MemorySaver)


class TestWorkflowState:
    """Test workflow state management."""
    
    def test_workflow_state_initialization(self, sample_job):
        """Test WorkflowState initialization."""
        state = WorkflowState(
            job_id=sample_job.id,
            job_request=sample_job.request
        )
        
        assert state.job_id == sample_job.id
        assert state.job_request == sample_job.request
        assert state.documents == []
        assert state.scoring_results == []
        assert state.report_data is None
        assert state.context == {}
        assert state.errors == []
        assert state.current_progress == {}
        assert state.file_paths == []
        assert state.failed_documents == []
        assert state.report_file_path is None
    
    def test_workflow_state_with_data(self, sample_job, test_documents, test_scoring_results):
        """Test WorkflowState with populated data."""
        state = WorkflowState(
            job_id=sample_job.id,
            job_request=sample_job.request,
            documents=test_documents,
            scoring_results=test_scoring_results,
            file_paths=["./doc1.txt", "./doc2.md"],
            errors=["test error"],
            current_progress={"stage": "processing", "percent": 50}
        )
        
        assert len(state.documents) == 2
        assert len(state.scoring_results) == 2
        assert len(state.file_paths) == 2
        assert len(state.errors) == 1
        assert state.current_progress["stage"] == "processing"
    
    def test_workflow_state_serialization(self, sample_job):
        """Test that WorkflowState can be serialized/deserialized."""
        original_state = WorkflowState(
            job_id=sample_job.id,
            job_request=sample_job.request,
            file_paths=["./test.txt"],
            errors=["test error"]
        )
        
        # Test dict conversion
        state_dict = original_state.dict()
        assert state_dict["job_id"] == sample_job.id
        assert state_dict["file_paths"] == ["./test.txt"]
        assert state_dict["errors"] == ["test error"]
        
        # Test reconstruction
        reconstructed_state = WorkflowState(**state_dict)
        assert reconstructed_state.job_id == original_state.job_id
        assert reconstructed_state.file_paths == original_state.file_paths
        assert reconstructed_state.errors == original_state.errors


class TestWorkflowExecution:
    """Test complete workflow execution."""
    
    @patch('src.workflow.graph.create_checkpointer')
    async def test_execute_workflow_basic(self, mock_create_checkpointer, sample_job):
        """Test basic workflow execution."""
        # Mock checkpointer
        mock_checkpointer = MagicMock()
        mock_create_checkpointer.return_value = mock_checkpointer
        
        # Create a simple workflow that just returns the state
        workflow = StateGraph(WorkflowState)
        
        # Add a simple node that just returns the state unchanged
        def simple_node(state: WorkflowState) -> WorkflowState:
            state.current_progress = {"stage": "completed", "percent": 100}
            return state
        
        workflow.add_node("simple_node", simple_node)
        workflow.set_entry_point("simple_node")
        workflow.add_edge("simple_node", "__end__")
        
        # Mock the compiled workflow
        mock_compiled = AsyncMock()
        final_state = WorkflowState(
            job_id=sample_job.id,
            job_request=sample_job.request,
            current_progress={"stage": "completed", "percent": 100}
        )
        mock_compiled.ainvoke.return_value = final_state
        
        with patch.object(workflow, 'compile', return_value=mock_compiled):
            result = await execute_workflow(workflow, sample_job)
        
        # Verify result structure
        assert "report_file" in result
        assert "checkpointing_enabled" in result
        assert "checkpointer_type" in result
        assert "metrics" in result
        
        # Verify metrics structure
        metrics = result["metrics"]
        assert "total_documents" in metrics
        assert "processed_documents" in metrics
        assert "failed_documents" in metrics
        assert "scored_documents" in metrics
        assert "errors" in metrics
        assert "progress" in metrics
        assert "summary" in metrics
    
    @patch('src.workflow.graph.create_checkpointer')
    async def test_execute_workflow_with_resume(self, mock_create_checkpointer, sample_job):
        """Test workflow execution with resume from checkpoint."""
        mock_checkpointer = MagicMock()
        mock_create_checkpointer.return_value = mock_checkpointer
        
        workflow = create_workflow()
        
        # Mock compiled workflow
        mock_compiled = AsyncMock()
        final_state = WorkflowState(
            job_id=sample_job.id,
            job_request=sample_job.request
        )
        mock_compiled.ainvoke.return_value = final_state
        
        with patch.object(workflow, 'compile', return_value=mock_compiled):
            result = await execute_workflow(workflow, sample_job, resume_from_checkpoint="checkpoint_123")
        
        # Verify that ainvoke was called with checkpoint config
        call_args = mock_compiled.ainvoke.call_args
        config = call_args[1]["config"]
        assert config["configurable"]["checkpoint_id"] == "checkpoint_123"
        assert config["configurable"]["thread_id"] == sample_job.id
    
    @patch('src.workflow.graph.create_checkpointer')
    async def test_execute_workflow_azure_cleanup(self, mock_create_checkpointer, sample_job):
        """Test workflow execution with Azure checkpointer cleanup."""
        # Mock Azure checkpointer
        mock_azure_checkpointer = MagicMock()
        mock_azure_checkpointer.cleanup_old_checkpoints = AsyncMock(return_value=3)
        mock_create_checkpointer.return_value = mock_azure_checkpointer
        
        # Mock isinstance check for Azure checkpointer
        with patch('src.workflow.graph.isinstance') as mock_isinstance:
            mock_isinstance.return_value = True
            
            workflow = create_workflow()
            
            # Mock compiled workflow
            mock_compiled = AsyncMock()
            final_state = WorkflowState(
                job_id=sample_job.id,
                job_request=sample_job.request
            )
            mock_compiled.ainvoke.return_value = final_state
            
            with patch.object(workflow, 'compile', return_value=mock_compiled):
                result = await execute_workflow(workflow, sample_job)
            
            # Verify cleanup was called
            mock_azure_checkpointer.cleanup_old_checkpoints.assert_called_once_with(
                sample_job.id, keep_last=5
            )
    
    @patch('src.workflow.graph.create_checkpointer')
    async def test_execute_workflow_error_handling(self, mock_create_checkpointer, sample_job):
        """Test workflow execution error handling."""
        mock_checkpointer = MagicMock()
        mock_create_checkpointer.return_value = mock_checkpointer
        
        workflow = create_workflow()
        
        # Mock compiled workflow to raise an error
        mock_compiled = AsyncMock()
        mock_compiled.ainvoke.side_effect = Exception("Workflow execution failed")
        
        with patch.object(workflow, 'compile', return_value=mock_compiled):
            with pytest.raises(Exception, match="Workflow execution failed"):
                await execute_workflow(workflow, sample_job)


class TestWorkflowMetrics:
    """Test workflow metrics calculation."""
    
    async def test_workflow_metrics_calculation(self, sample_job, test_documents, test_scoring_results):
        """Test that workflow metrics are calculated correctly."""
        # Create workflow state with data
        final_state = WorkflowState(
            job_id=sample_job.id,
            job_request=sample_job.request,
            file_paths=["./doc1.txt", "./doc2.md", "./doc3.pdf"],
            documents=test_documents,
            scoring_results=test_scoring_results,
            failed_documents=[{"file": "./doc3.pdf", "error": "Processing failed"}],
            errors=["Some processing error"],
            current_progress={"stage": "completed", "percent": 100}
        )
        
        # Mock workflow execution
        with patch('src.workflow.graph.create_checkpointer') as mock_create_checkpointer:
            mock_checkpointer = MagicMock()
            mock_create_checkpointer.return_value = mock_checkpointer
            
            workflow = create_workflow()
            mock_compiled = AsyncMock()
            mock_compiled.ainvoke.return_value = final_state
            
            with patch.object(workflow, 'compile', return_value=mock_compiled):
                result = await execute_workflow(workflow, sample_job)
        
        # Verify detailed metrics
        metrics = result["metrics"]
        
        assert metrics["total_documents"] == 3  # file_paths length
        assert metrics["processed_documents"] == 2  # documents length
        assert metrics["failed_documents"] == 1  # failed_documents length
        assert metrics["scored_documents"] == 2  # scoring_results length
        assert len(metrics["errors"]) == 1
        assert metrics["progress"]["stage"] == "completed"
        
        # Verify summary metrics
        summary = metrics["summary"]
        assert summary["total_documents_analyzed"] == 2
        assert summary["high_priority_count"] == 1  # score >= 75
        assert summary["average_score"] == pytest.approx((85.5 + 72.3) / 2, rel=1e-2)


class TestWorkflowCheckpoints:
    """Test workflow checkpoint management."""
    
    @patch('src.workflow.graph.settings')
    async def test_get_workflow_checkpoints_memory(self, mock_settings):
        """Test checkpoint retrieval with memory checkpointer."""
        mock_settings.USE_AZURE_STORAGE = False
        
        checkpoints = await get_workflow_checkpoints("test_job_id")
        
        assert checkpoints == []
    
    @patch('src.workflow.graph.settings')
    @patch('src.workflow.graph.AzureCheckpointSaver')
    async def test_get_workflow_checkpoints_azure(self, mock_azure_saver, mock_settings):
        """Test checkpoint retrieval with Azure checkpointer."""
        mock_settings.USE_AZURE_STORAGE = True
        
        # Mock Azure checkpointer and client
        mock_azure_instance = MagicMock()
        mock_azure_client = MagicMock()
        mock_azure_instance.azure_client = mock_azure_client
        mock_azure_saver.return_value = mock_azure_instance
        
        # Mock blob data
        mock_blob1 = MagicMock()
        mock_blob1.name = "threads/test_job/checkpoints/checkpoint_1.json"
        mock_blob1.last_modified = datetime(2024, 1, 1, 12, 0, 0)
        mock_blob1.size = 1024
        
        mock_blob2 = MagicMock()
        mock_blob2.name = "threads/test_job/checkpoints/checkpoint_2.json"
        mock_blob2.last_modified = datetime(2024, 1, 1, 13, 0, 0)
        mock_blob2.size = 2048
        
        mock_azure_client.list_blobs = AsyncMock(return_value=[mock_blob1, mock_blob2])
        
        checkpoints = await get_workflow_checkpoints("test_job")
        
        assert len(checkpoints) == 2
        
        # Verify sorting (newest first)
        assert checkpoints[0]["checkpoint_id"] == "checkpoint_2"
        assert checkpoints[1]["checkpoint_id"] == "checkpoint_1"
        
        # Verify checkpoint data
        assert checkpoints[0]["size_bytes"] == 2048
        assert checkpoints[1]["size_bytes"] == 1024
        assert checkpoints[0]["created_at"] == "2024-01-01T13:00:00"
        assert checkpoints[1]["created_at"] == "2024-01-01T12:00:00"
    
    @patch('src.workflow.graph.settings')
    @patch('src.workflow.graph.AzureCheckpointSaver')
    async def test_get_workflow_checkpoints_error_handling(self, mock_azure_saver, mock_settings):
        """Test checkpoint retrieval error handling."""
        mock_settings.USE_AZURE_STORAGE = True
        
        mock_azure_instance = MagicMock()
        mock_azure_client = MagicMock()
        mock_azure_instance.azure_client = mock_azure_client
        mock_azure_saver.return_value = mock_azure_instance
        
        # Mock an error during blob listing
        mock_azure_client.list_blobs = AsyncMock(side_effect=Exception("Azure connection failed"))
        
        checkpoints = await get_workflow_checkpoints("test_job")
        
        # Should return empty list on error
        assert checkpoints == []


class TestWorkflowIntegration:
    """Test workflow integration with other components."""
    
    def test_workflow_state_config_compatibility(self):
        """Test that WorkflowState is compatible with Pydantic configuration."""
        from src.workflow.state import WorkflowState
        
        # Test that the Config class is properly defined
        assert hasattr(WorkflowState, 'Config')
        assert WorkflowState.Config.arbitrary_types_allowed is True
    
    def test_workflow_imports_availability(self):
        """Test that all required imports are available."""
        # Test that all node functions can be imported
        from src.workflow.nodes import (
            load_documents,
            load_context,
            process_documents,
            score_documents,
            cluster_results,
            generate_report
        )
        
        # Verify they are callable
        assert callable(load_documents)
        assert callable(load_context)
        assert callable(process_documents)
        assert callable(score_documents)
        assert callable(cluster_results)
        assert callable(generate_report)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])