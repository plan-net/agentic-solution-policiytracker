"""
Unit tests for LangGraph workflow nodes as required by CLAUDE.md.

Testing Requirements from CLAUDE.md:
- Test each node in isolation
- Mock Ray tasks and external APIs
- Verify state transformations
- Test both Azure Storage and local filesystem modes
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.content import DocumentMetadata, DocumentType, ProcessedContent
from src.models.job import JobRequest
from src.models.scoring import ScoringResult
from src.workflow.nodes import (
    cluster_results,
    generate_report,
    load_context,
    load_documents,
    process_documents,
    score_documents,
)
from src.workflow.state import WorkflowState


class TestWorkflowNodeIsolation:
    """Test each workflow node in isolation as required by CLAUDE.md."""

    @pytest.fixture
    def basic_state(self) -> WorkflowState:
        """Create basic workflow state for testing."""
        job_request = JobRequest(
            job_name="test_job",
            input_folder="/test/input",
            context_file="/test/context.yaml",
            priority_threshold=70.0,
            include_low_confidence=False,
            clustering_enabled=True,
        )

        return WorkflowState(
            job_id="test_job_123",
            job_request=job_request,
            file_paths=[],
            documents=[],
            context={},
            scoring_results=[],
            failed_documents=[],
            report_data=None,
            errors=[],
            current_progress={},
        )

    @pytest.mark.asyncio
    async def test_load_documents_node_isolation(self, basic_state, tmp_path):
        """Test load_documents node in isolation."""
        # Setup test directory with files
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "test1.txt").write_text("Test document 1")
        (input_dir / "test2.md").write_text("# Test document 2")

        # Update state with real directory
        basic_state.job_request.input_folder = str(input_dir)

        # Execute node
        result_state = await load_documents(basic_state)

        # Verify state transformation
        assert result_state.job_id == basic_state.job_id
        assert len(result_state.file_paths) == 2
        assert result_state.current_progress["stage"] == "documents_loaded"
        assert result_state.current_progress["documents_found"] == 2
        assert "timestamp" in result_state.current_progress

    @pytest.mark.asyncio
    async def test_load_context_node_isolation_local(self, basic_state, tmp_path, local_settings):
        """Test load_context node in isolation with local filesystem."""
        # Setup test context file
        context_file = tmp_path / "context.yaml"
        context_file.write_text(
            """
company_terms:
  - test-company
core_industries:
  - technology
primary_markets:
  - US
strategic_themes:
  - innovation
"""
        )

        # Update state with real context file
        basic_state.job_request.context_file = str(context_file)

        # Execute node
        result_state = await load_context(basic_state)

        # Verify state transformation
        assert result_state.context["company_terms"] == ["test-company"]
        assert result_state.context["core_industries"] == ["technology"]
        assert result_state.current_progress["stage"] == "context_loaded"
        assert result_state.current_progress["context_file"] == str(context_file)
        assert result_state.current_progress["source_type"] == "local_filesystem"

    @pytest.mark.asyncio
    @patch("src.workflow.nodes.AzureStorageClient")
    async def test_load_context_node_isolation_azure(
        self, mock_azure_client_class, basic_state, mock_azure_settings, sample_azure_context_file
    ):
        """Test load_context node in isolation with Azure Storage."""
        # Setup mock Azure client
        mock_client = AsyncMock()
        mock_azure_client_class.return_value = mock_client

        # Mock context file download
        import yaml

        context_yaml = yaml.dump(sample_azure_context_file).encode()
        mock_client.download_blob.return_value = context_yaml

        # Update state with Azure context file
        basic_state.job_request.context_file = "test_context.yaml"

        # Execute node
        result_state = await load_context(basic_state)

        # Verify state transformation
        assert result_state.context["company_terms"] == ["azure-test-corp", "test company"]
        assert result_state.context["core_industries"] == ["cloud", "technology"]
        assert result_state.current_progress["stage"] == "context_loaded"
        assert result_state.current_progress["source_type"] == "azure_storage"

        # Verify Azure client was called
        mock_client.download_blob.assert_called_once_with("contexts", "test_context.yaml")

    @pytest.mark.asyncio
    @patch("src.workflow.nodes.ContentProcessor")
    async def test_process_documents_node_isolation_local(
        self, mock_processor_class, basic_state, local_settings
    ):
        """Test process_documents node in isolation with local filesystem."""
        # Setup mock processor
        mock_processor = AsyncMock()
        mock_processor_class.return_value = mock_processor

        # Create mock processed document
        mock_metadata = DocumentMetadata(
            source="/test/doc.txt",
            type=DocumentType.TXT,
            file_path="/test/doc.txt",
            file_size_bytes=1024,
        )

        mock_doc = ProcessedContent(
            id="doc_001",
            raw_text="Test document content",
            metadata=mock_metadata,
            processing_timestamp=datetime.now(),
        )

        mock_processor.process_document.return_value = mock_doc

        # Setup state with file paths
        basic_state.file_paths = ["/test/doc1.txt", "/test/doc2.txt"]

        # Execute node
        result_state = await process_documents(basic_state)

        # Verify state transformation
        assert len(result_state.documents) == 2
        assert result_state.current_progress["stage"] == "processing_documents"
        assert result_state.current_progress["processed"] == 2
        assert result_state.current_progress["total"] == 2
        assert result_state.current_progress["storage_type"] == "local_filesystem"

        # Verify mock was called correctly
        assert mock_processor.process_document.call_count == 2

        # Verify processor was initialized without Azure
        mock_processor_class.assert_called_once_with(use_azure=False)

    @pytest.mark.asyncio
    @patch("src.workflow.nodes.ContentProcessor")
    async def test_process_documents_node_isolation_azure(
        self, mock_processor_class, basic_state, mock_azure_settings
    ):
        """Test process_documents node in isolation with Azure Storage."""
        # Setup mock processor
        mock_processor = AsyncMock()
        mock_processor_class.return_value = mock_processor

        # Create mock processed document with Azure metadata
        mock_metadata = DocumentMetadata(
            source="azure_doc.txt",
            type=DocumentType.TXT,
            file_path="jobs/test_job/input/azure_doc.txt",
            file_size_bytes=1024,
        )

        mock_doc = ProcessedContent(
            id="doc_001",
            raw_text="Test Azure document content",
            metadata=mock_metadata,
            processing_timestamp=datetime.now(),
        )

        mock_processor.process_document.return_value = mock_doc

        # Setup state with Azure blob paths
        basic_state.file_paths = ["jobs/test_job/input/doc1.txt", "jobs/test_job/input/doc2.txt"]

        # Execute node
        result_state = await process_documents(basic_state)

        # Verify state transformation
        assert len(result_state.documents) == 2
        assert result_state.current_progress["stage"] == "processing_documents"
        assert result_state.current_progress["processed"] == 2
        assert result_state.current_progress["total"] == 2
        assert result_state.current_progress["storage_type"] == "azure_storage"

        # Verify mock was called correctly with job_id
        assert mock_processor.process_document.call_count == 2

        # Verify processor was initialized with Azure
        mock_processor_class.assert_called_once_with(use_azure=True)

    @pytest.mark.asyncio
    @patch("src.workflow.nodes.HybridScoringEngine")
    async def test_score_documents_node_isolation(self, mock_engine_class, basic_state):
        """Test score_documents node with mocked scoring engine."""
        # Setup mock scoring engine
        mock_engine = AsyncMock()
        mock_engine_class.return_value = mock_engine

        # Create mock scoring result
        mock_result = MagicMock(spec=ScoringResult)
        mock_result.processing_time_ms = 150.0
        mock_engine.score_document_hybrid.return_value = mock_result

        # Setup state with documents and context
        mock_metadata = DocumentMetadata(
            source="/test/doc.txt",
            type=DocumentType.TXT,
            file_path="/test/doc.txt",
            file_size_bytes=1024,
        )

        mock_doc = ProcessedContent(
            id="doc_001",
            raw_text="Test document",
            metadata=mock_metadata,
            processing_timestamp=datetime.now(),
        )

        basic_state.documents = [mock_doc]
        basic_state.context = {"company_terms": ["test"]}

        # Execute node
        result_state = await score_documents(basic_state)

        # Verify state transformation
        assert len(result_state.scoring_results) == 1
        assert result_state.current_progress["stage"] == "scoring_documents"
        assert result_state.current_progress["scored"] == 1
        assert result_state.current_progress["total"] == 1

        # Verify mock was called
        mock_engine.score_document_hybrid.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.workflow.nodes.TopicClusterer")
    @patch("src.workflow.nodes.ResultAggregator")
    async def test_cluster_results_node_isolation(
        self, mock_aggregator_class, mock_clusterer_class, basic_state
    ):
        """Test cluster_results node with mocked clustering."""
        # Setup mocks
        mock_clusterer = AsyncMock()
        mock_clusterer_class.return_value = mock_clusterer
        mock_clusterer.cluster_by_topic.return_value = [{"cluster1": "data"}]

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        mock_aggregator.group_by_priority.return_value = {"high": [], "medium": []}

        # Setup state with scoring results
        basic_state.scoring_results = [MagicMock()]
        basic_state.job_request.clustering_enabled = True

        # Execute node
        result_state = await cluster_results(basic_state)

        # Verify state transformation
        assert result_state.current_progress["stage"] == "clustering_completed"
        assert "topic_clusters" in result_state.current_progress
        assert "priority_queues" in result_state.current_progress

        # Verify mocks were called
        mock_clusterer.cluster_by_topic.assert_called_once()
        mock_aggregator.group_by_priority.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.workflow.nodes.ReportGenerator")
    @patch("src.workflow.nodes.os.makedirs")
    async def test_generate_report_node_isolation_local(
        self, mock_makedirs, mock_generator_class, basic_state, local_settings
    ):
        """Test generate_report node with local filesystem."""
        # Setup mock generator
        mock_generator = AsyncMock()
        mock_generator_class.return_value = mock_generator

        mock_report_data = {"report": "data"}
        mock_generator.prepare_report_data.return_value = mock_report_data
        mock_generator.generate_markdown_report.return_value = None

        # Setup state with scoring results
        basic_state.scoring_results = [MagicMock()]
        basic_state.context = {"test": "context"}

        # Execute node
        result_state = await generate_report(basic_state)

        # Verify state transformation
        assert result_state.report_data == mock_report_data
        assert result_state.current_progress["stage"] == "report_generated"
        assert result_state.current_progress["storage_type"] == "local_filesystem"
        assert "report_file" in result_state.current_progress

        # Verify mocks were called
        mock_generator.prepare_report_data.assert_called_once()
        mock_generator.generate_markdown_report.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.workflow.nodes.AzureStorageClient")
    @patch("src.workflow.nodes.ReportGenerator")
    async def test_generate_report_node_isolation_azure(
        self, mock_generator_class, mock_azure_client_class, basic_state, mock_azure_settings
    ):
        """Test generate_report node with Azure Storage."""
        # Setup mock generator
        mock_generator = AsyncMock()
        mock_generator_class.return_value = mock_generator

        mock_report_data = {"report": "data"}
        mock_generator.prepare_report_data.return_value = mock_report_data
        mock_generator.generate_markdown_content.return_value = "# Test Report\nReport content"

        # Setup mock Azure client
        mock_azure_client = AsyncMock()
        mock_azure_client_class.return_value = mock_azure_client
        mock_azure_client.upload_blob.return_value = True

        # Setup state with scoring results
        basic_state.scoring_results = [MagicMock()]
        basic_state.context = {"test": "context"}

        # Execute node
        result_state = await generate_report(basic_state)

        # Verify state transformation
        assert result_state.report_data == mock_report_data
        assert result_state.current_progress["stage"] == "report_generated"
        assert result_state.current_progress["storage_type"] == "azure_storage"
        assert "report_file" in result_state.current_progress
        assert result_state.report_file_path.startswith("azure://")

        # Verify mocks were called
        mock_generator.prepare_report_data.assert_called_once()
        mock_generator.generate_markdown_content.assert_called_once()
        mock_azure_client.upload_blob.assert_called_once()


class TestStateTransformations:
    """Test state transformations between nodes as required by CLAUDE.md."""

    @pytest.mark.asyncio
    async def test_state_immutability_pattern(self):
        """Test that nodes don't mutate input state incorrectly."""
        original_state = WorkflowState(
            job_id="test_123",
            job_request=JobRequest(
                job_name="test", input_folder="/nonexistent", context_file="/nonexistent.yaml"
            ),
            file_paths=[],
            documents=[],
            context={},
            scoring_results=[],
            failed_documents=[],
            report_data=None,
            errors=[],
            current_progress={},
        )

        # Copy for comparison
        original_job_id = original_state.job_id
        original_file_paths = original_state.file_paths.copy()

        try:
            # This should fail, but shouldn't mutate the original state
            await load_documents(original_state)
        except Exception:
            pass  # Expected to fail with nonexistent directory

        # Verify original state wasn't mutated
        assert original_state.job_id == original_job_id
        assert original_state.file_paths == original_file_paths

    @pytest.mark.asyncio
    async def test_progress_tracking_consistency(self, tmp_path):
        """Test that progress tracking is consistent across nodes."""
        # Setup minimal valid state
        context_file = tmp_path / "context.yaml"
        context_file.write_text(
            """
company_terms: [test]
core_industries: [tech]
primary_markets: [US]
strategic_themes: [innovation]
"""
        )

        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "test.txt").write_text("test content")

        initial_state = WorkflowState(
            job_id="progress_test",
            job_request=JobRequest(
                job_name="progress_test",
                input_folder=str(input_dir),
                context_file=str(context_file),
            ),
            file_paths=[],
            documents=[],
            context={},
            scoring_results=[],
            failed_documents=[],
            report_data=None,
            errors=[],
            current_progress={},
        )

        # Test that each node updates progress correctly
        state1 = await load_documents(initial_state)
        assert "timestamp" in state1.current_progress
        assert state1.current_progress["stage"] == "documents_loaded"

        state2 = await load_context(state1)
        assert "timestamp" in state2.current_progress
        assert state2.current_progress["stage"] == "context_loaded"
        # Previous stage data should be preserved or updated appropriately


class TestErrorHandling:
    """Test error handling in workflow nodes as required by CLAUDE.md."""

    @pytest.mark.asyncio
    async def test_load_documents_error_handling(self):
        """Test load_documents handles errors gracefully."""
        state = WorkflowState(
            job_id="error_test",
            job_request=JobRequest(
                job_name="error_test", input_folder="/nonexistent/path", context_file="/test.yaml"
            ),
            file_paths=[],
            documents=[],
            context={},
            scoring_results=[],
            failed_documents=[],
            report_data=None,
            errors=[],
            current_progress={},
        )

        # Should raise WorkflowError with proper context
        with pytest.raises(Exception) as exc_info:
            await load_documents(state)

        # Verify error contains job context
        assert "error_test" in str(exc_info.value) or hasattr(exc_info.value, "job_id")

    @pytest.mark.asyncio
    async def test_context_validation_error_handling(self, tmp_path):
        """Test context loading validates required fields."""
        # Create invalid context file
        context_file = tmp_path / "invalid_context.yaml"
        context_file.write_text(
            """
company_terms: [test]
# Missing required fields
"""
        )

        state = WorkflowState(
            job_id="validation_test",
            job_request=JobRequest(
                job_name="validation_test", input_folder="/test", context_file=str(context_file)
            ),
            file_paths=[],
            documents=[],
            context={},
            scoring_results=[],
            failed_documents=[],
            report_data=None,
            errors=[],
            current_progress={},
        )

        # Should raise error for missing required fields
        with pytest.raises(Exception):
            await load_context(state)


# Note: Ray task testing class removed as Ray task infrastructure was removed from codebase
# The current implementation uses LangGraph sequential processing instead of Ray tasks
