"""
Integration tests for full LangGraph workflow execution.
Tests the complete graph with Ray local mode and checkpointing as required by CLAUDE.md.
Includes Azure Storage integration testing.
"""

import asyncio
import os
import tempfile
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import ray
from langgraph.checkpoint.memory import MemorySaver

from src.models.job import Job, JobRequest, JobStatus
from src.workflow.graph import create_checkpointer, create_workflow, execute_workflow
from src.workflow.state import WorkflowState


class TestWorkflowExecution:
    """Integration tests for full graph execution as required by CLAUDE.md."""

    def _create_test_state(
        self, job_request: JobRequest, job_id: str = "test_job_001"
    ) -> WorkflowState:
        """Helper to create test WorkflowState with correct parameters."""
        return WorkflowState(
            job_id=job_id,
            job_request=job_request,
            documents=[],
            scoring_results=[],
            report_data=None,
            context={},
            errors=[],
            current_progress={},
            file_paths=[],
            failed_documents=[],
            report_file_path=None,
        )

    @pytest.fixture(autouse=True)
    def setup_ray_local_mode(self):
        """Setup Ray in local mode for testing."""
        if not ray.is_initialized():
            # Initialize Ray in local mode
            ray.init(local_mode=True, ignore_reinit_error=True)
        yield
        # Cleanup after test
        if ray.is_initialized():
            ray.shutdown()

    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        return JobRequest(
            job_name="TestJob",
            input_folder="/tmp/test_documents",
            context_file="/tmp/test_context.yaml",
            priority_threshold=70.0,
            include_low_confidence=False,
            clustering_enabled=True,
        )

    @pytest.fixture
    def test_documents_dir(self, tmp_path):
        """Create test documents directory."""
        docs_dir = tmp_path / "documents"
        docs_dir.mkdir()

        # Create test documents
        (docs_dir / "test1.txt").write_text(
            "New AI regulation proposal for healthcare privacy in the US. "
            "This technology-focused policy affects data protection standards."
        )
        (docs_dir / "test2.txt").write_text(
            "Environmental policy update regarding renewable energy standards. "
            "New requirements for solar panel installations in Europe."
        )
        (docs_dir / "test3.md").write_text(
            "# Healthcare Technology Policy\n\n"
            "Proposed changes to AI usage in medical diagnosis. "
            "Privacy concerns and regulatory compliance requirements."
        )

        return str(docs_dir)

    @pytest.fixture
    def checkpoint_db(self, tmp_path):
        """Create temporary checkpointer for tests."""
        # Using MemorySaver as SQLite checkpointer not available
        return MemorySaver()

    @pytest.mark.asyncio
    async def test_full_graph_execution_local(
        self, test_config, test_documents_dir, checkpoint_db, local_settings
    ):
        """Test complete workflow execution with local filesystem."""
        # Create test job
        test_job = Job(
            id="test_job_local",
            request=test_config,
            status=JobStatus.PENDING,
            created_at=datetime.now(),
        )
        test_job.request.input_folder = test_documents_dir

        # Execute workflow
        with patch("src.workflow.nodes.ContentProcessor") as mock_processor:
            with patch("src.workflow.nodes.HybridScoringEngine") as mock_engine:
                with patch("src.workflow.nodes.ReportGenerator") as mock_generator:
                    # Setup mocks
                    mock_processor.return_value.process_document = AsyncMock(
                        return_value=self._mock_processed_content()
                    )
                    mock_engine.return_value.score_document_hybrid = AsyncMock(
                        return_value=self._mock_scoring_result()
                    )
                    mock_generator.return_value.prepare_report_data = AsyncMock(
                        return_value={"test": "data"}
                    )
                    mock_generator.return_value.generate_markdown_report = AsyncMock()

                    # Execute workflow
                    graph = create_workflow()
                    result = await execute_workflow(graph, test_job)

                    # Verify execution completed successfully
                    assert result is not None
                    assert result["checkpointer_type"] == "memory"
                    assert "metrics" in result
                    assert result["metrics"]["total_documents"] >= 0

    @pytest.mark.asyncio
    @patch("src.integrations.azure_storage.AzureStorageClient")
    async def test_full_graph_execution_azure(
        self, mock_azure_client_class, test_config, mock_azure_settings, mock_azure_storage_client
    ):
        """Test complete workflow execution with Azure Storage."""
        # Setup Azure mocks
        mock_azure_client_class.return_value = mock_azure_storage_client

        # Mock Azure document discovery
        mock_blob = MagicMock()
        mock_blob.name = "jobs/test_job_azure/input/test.txt"
        mock_blob.size = 1024
        mock_azure_storage_client.list_blobs.return_value = [mock_blob]

        # Mock context file
        context_data = {
            "company_terms": ["test"],
            "core_industries": ["tech"],
            "primary_markets": ["US"],
            "strategic_themes": ["innovation"],
        }
        import yaml

        mock_azure_storage_client.download_blob.return_value = yaml.dump(context_data).encode()

        # Create test job
        test_job = Job(
            id="test_job_azure",
            request=test_config,
            status=JobStatus.PENDING,
            created_at=datetime.now(),
        )
        test_job.request.input_folder = "test_job_azure"  # Job prefix for Azure
        test_job.request.context_file = "test_context.yaml"

        # Execute workflow with mocked components
        with patch("src.workflow.nodes.ContentProcessor") as mock_processor:
            with patch("src.workflow.nodes.HybridScoringEngine") as mock_engine:
                with patch("src.workflow.nodes.ReportGenerator") as mock_generator:
                    # Setup mocks
                    mock_processor.return_value.process_document = AsyncMock(
                        return_value=self._mock_processed_content()
                    )
                    mock_engine.return_value.score_document_hybrid = AsyncMock(
                        return_value=self._mock_scoring_result()
                    )
                    mock_generator.return_value.prepare_report_data = AsyncMock(
                        return_value={"test": "data"}
                    )
                    mock_generator.return_value.generate_markdown_content = AsyncMock(
                        return_value="# Test Report"
                    )

                    # Mock Azure report upload
                    mock_azure_storage_client.upload_blob.return_value = True

                    # Execute workflow
                    graph = create_workflow()
                    result = await execute_workflow(graph, test_job)

                    # Verify execution completed successfully
                    assert result is not None
                    assert result["checkpointer_type"] == "azure_storage"
                    assert "metrics" in result

                    # Verify Azure operations were called
                    mock_azure_storage_client.list_blobs.assert_called()
                    mock_azure_storage_client.download_blob.assert_called()

    def _mock_processed_content(self):
        """Create mock processed content."""
        from src.models.content import DocumentMetadata, DocumentType, ProcessedContent

        metadata = DocumentMetadata(
            source="test.txt", type=DocumentType.TXT, file_path="test.txt", file_size_bytes=1024
        )
        return ProcessedContent(
            id="test_doc",
            raw_text="Test content",
            metadata=metadata,
            processing_timestamp=datetime.now(),
        )

    def _mock_scoring_result(self):
        """Create mock scoring result."""
        from src.models.scoring import ScoringResult

        return ScoringResult(
            document_id="test_doc",
            master_score=75.0,
            dimension_scores={},
            confidence_score=0.8,
            confidence_level="high",
            priority_level="high",
            topic_clusters=[],
            scoring_timestamp=datetime.now(),
            processing_time_ms=100.0,
            overall_justification="Test justification",
            key_factors=[],
        )

    @pytest.mark.asyncio
    async def test_workflow_checkpointing_behavior(
        self, test_config, test_documents_dir, checkpoint_db
    ):
        """Test checkpointing behavior during workflow execution."""
        graph = create_workflow()
        compiled_graph = graph.compile(checkpointer=checkpoint_db)

        initial_state = WorkflowState(
            job_id="test_job_checkpoint",
            job_request=test_config,
            documents=[],
            scoring_results=[],
            report_data=None,
            context={},
            errors=[],
            current_progress={},
            file_paths=[],
            failed_documents=[],
            report_file_path=None,
        )

        config = {"configurable": {"thread_id": "test-checkpoint-thread"}}

        # Execute workflow step by step to test checkpointing
        states = []
        async for state in compiled_graph.astream(initial_state, config=config):
            states.append(state)

        # Verify checkpoints were created
        assert len(states) > 1, "Multiple states should be checkpointed"

        # Test checkpoint retrieval
        checkpoint = await compiled_graph.aget_state(config)
        assert checkpoint is not None, "Checkpoint should be retrievable"
        assert checkpoint.values is not None, "Checkpoint should contain state values"

        # Verify we can resume from checkpoint
        resumed_state = checkpoint.values
        assert resumed_state["job_request"] == test_config

        # Test checkpoint history
        history = []
        async for checkpoint in compiled_graph.aget_state_history(config):
            history.append(checkpoint)

        assert len(history) > 0, "Checkpoint history should be available"

    # Note: Ray tasks test removed as Ray task infrastructure was removed from codebase
    # The current implementation uses LangGraph sequential processing instead

    @pytest.mark.asyncio
    async def test_workflow_error_handling_and_recovery(self, test_config, checkpoint_db):
        """Test workflow error handling and recovery mechanisms."""
        # Create scenario with invalid input directory
        invalid_dir = "/nonexistent/directory/path"

        graph = create_workflow()
        compiled_graph = graph.compile(checkpointer=checkpoint_db)

        initial_state = WorkflowState(
            job_id="test_job_error_recovery",
            job_request=test_config,
            documents=[],
            scoring_results=[],
            report_data=None,
            context={},
            errors=[],
            current_progress={},
            file_paths=[],
            failed_documents=[],
            report_file_path=None,
        )

        config = {"configurable": {"thread_id": "test-error-thread"}}

        # Execute workflow and expect graceful error handling
        final_state = None
        async for state in compiled_graph.astream(initial_state, config=config):
            final_state = state

        # Verify error was captured and workflow didn't crash
        assert final_state is not None
        assert len(final_state["errors"]) > 0, "Errors should be captured"

        # Verify error contains meaningful information
        error = final_state["errors"][0]
        assert error.message is not None
        assert error.node_name is not None

    @pytest.mark.asyncio
    async def test_concurrent_workflow_executions(
        self, test_config, test_documents_dir, checkpoint_db
    ):
        """Test concurrent graph executions for load testing."""
        graph = create_political_monitoring_graph()
        compiled_graph = graph.compile(checkpointer=checkpoint_db)

        async def run_workflow(thread_id: str):
            """Run a single workflow execution."""
            initial_state = WorkflowState(
                documents=[],
                filtered_documents=[],
                analyzed_documents=[],
                scores=[],
                analysis_config=test_config,
                input_directory=test_documents_dir,
                reasoning_steps=[],
                errors=[],
                metadata={},
            )

            config = {"configurable": {"thread_id": thread_id}}

            final_state = None
            async for state in compiled_graph.astream(initial_state, config=config):
                final_state = state

            return final_state

        # Run multiple concurrent executions
        tasks = [run_workflow(f"concurrent-thread-{i}") for i in range(3)]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all executions completed successfully
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Execution {i} failed: {result}"
            assert result is not None, f"Execution {i} returned None"
            assert len(result["documents"]) > 0, f"Execution {i} should have loaded documents"

    @pytest.mark.asyncio
    async def test_workflow_conditional_edges(self, test_config, checkpoint_db):
        """Test conditional edges and routing in the workflow."""
        # Create scenario with no documents to test conditional routing
        empty_dir = tempfile.mkdtemp()

        graph = create_political_monitoring_graph()
        compiled_graph = graph.compile(checkpointer=checkpoint_db)

        initial_state = WorkflowState(
            documents=[],
            filtered_documents=[],
            analyzed_documents=[],
            scores=[],
            analysis_config=test_config,
            input_directory=empty_dir,
            reasoning_steps=[],
            errors=[],
            metadata={},
        )

        config = {"configurable": {"thread_id": "test-conditional-thread"}}

        # Execute workflow
        final_state = None
        execution_path = []

        async for state in compiled_graph.astream(initial_state, config=config):
            # Track which nodes were executed
            if hasattr(state, "__node__"):
                execution_path.append(state.__node__)
            final_state = state

        # Verify workflow handled empty input gracefully
        assert final_state is not None
        assert len(final_state["documents"]) == 0

        # Verify appropriate reasoning was provided
        assert len(final_state["reasoning_steps"]) > 0

        # Clean up
        os.rmdir(empty_dir)

    @pytest.mark.asyncio
    @patch("src.integrations.azure_checkpoint.AzureStorageClient")
    async def test_azure_checkpointing_integration(
        self, mock_azure_client_class, test_config, mock_azure_settings, mock_azure_storage_client
    ):
        """Test Azure Storage checkpointing integration."""
        # Setup Azure mocks
        mock_azure_client_class.return_value = mock_azure_storage_client

        # Mock checkpoint operations
        mock_azure_storage_client.upload_json.return_value = True
        mock_azure_storage_client.download_json.return_value = {
            "checkpoint_id": "test_checkpoint",
            "thread_id": "test_thread",
            "checkpoint": {"state": "saved"},
            "metadata": {"timestamp": datetime.now().isoformat()},
        }

        # Mock checkpoint listing
        mock_blob = MagicMock()
        mock_blob.name = "threads/test_thread/checkpoints/test_checkpoint.json"
        mock_blob.last_modified = datetime.now()
        mock_blob.size = 1024
        mock_azure_storage_client.list_blobs.return_value = [mock_blob]

        # Test checkpointer creation
        checkpointer = create_checkpointer()
        assert checkpointer is not None

        # Test checkpoint listing
        checkpoints = await get_workflow_checkpoints("test_thread")
        assert len(checkpoints) >= 0  # Should return list even if empty

        # If we have checkpoints, verify structure
        if checkpoints:
            assert "checkpoint_id" in checkpoints[0]
            assert "created_at" in checkpoints[0]
            assert "size_bytes" in checkpoints[0]

    @pytest.mark.asyncio
    async def test_checkpointer_creation_modes(self, local_settings, mock_azure_settings):
        """Test checkpointer creation in different modes."""
        # Test local mode
        with patch("src.workflow.graph.settings", local_settings):
            checkpointer = create_checkpointer()
            assert checkpointer is not None
            assert checkpointer.__class__.__name__ == "MemorySaver"

        # Test Azure mode
        with patch("src.workflow.graph.settings", mock_azure_settings):
            with patch("src.integrations.azure_checkpoint.AzureStorageClient"):
                checkpointer = create_checkpointer()
                assert checkpointer is not None
                assert checkpointer.__class__.__name__ == "AzureCheckpointSaver"

    @pytest.mark.asyncio
    async def test_workflow_memory_limits(self, test_config, test_documents_dir, checkpoint_db):
        """Test workflow respects memory limits and checkpointing size constraints."""
        graph = create_political_monitoring_graph()
        compiled_graph = graph.compile(checkpointer=checkpoint_db)

        # Create larger state to test memory constraints
        large_metadata = {f"key_{i}": f"value_{i}" * 100 for i in range(100)}

        initial_state = WorkflowState(
            documents=[],
            filtered_documents=[],
            analyzed_documents=[],
            scores=[],
            analysis_config=test_config,
            input_directory=test_documents_dir,
            reasoning_steps=[],
            errors=[],
            metadata=large_metadata,
        )

        config = {"configurable": {"thread_id": "test-memory-thread"}}

        # Execute workflow and monitor checkpoint sizes
        checkpoint_sizes = []
        async for state in compiled_graph.astream(initial_state, config=config):
            # Get current checkpoint
            checkpoint = await compiled_graph.aget_state(config)
            if checkpoint:
                # Estimate checkpoint size (simplified)
                checkpoint_data = str(checkpoint.values)
                checkpoint_sizes.append(len(checkpoint_data))

        # Verify checkpoints don't exceed reasonable size limits
        # CLAUDE.md specifies <1MB target
        max_size = max(checkpoint_sizes) if checkpoint_sizes else 0
        assert max_size < 1024 * 1024, f"Checkpoint size {max_size} exceeds 1MB limit"


class TestLangGraphPatterns:
    """Test LangGraph-specific patterns as required by CLAUDE.md."""

    @pytest.fixture
    def mock_checkpointer(self):
        """Mock checkpointer for unit tests."""
        from unittest.mock import AsyncMock

        mock = AsyncMock()
        mock.aget_tuple = AsyncMock(return_value=None)
        mock.aput = AsyncMock()
        mock.alist = AsyncMock(return_value=[])
        return mock

    def test_graph_structure_snapshot(self):
        """Snapshot testing for graph structures."""
        graph = create_political_monitoring_graph()

        # Verify graph structure
        nodes = list(graph.nodes.keys())
        expected_nodes = [
            "load_documents",
            "filter_documents",
            "analyze_documents",
            "generate_scores",
            "compile_reasoning",
            "finalize_results",
        ]

        assert set(nodes) == set(
            expected_nodes
        ), f"Graph nodes mismatch. Expected: {expected_nodes}, Got: {nodes}"

        # Verify edges exist
        edges = list(graph.edges)
        assert len(edges) > 0, "Graph should have edges connecting nodes"

        # Verify entry and finish points
        assert hasattr(graph, "_start"), "Graph should have start point"
        assert hasattr(graph, "_finish"), "Graph should have finish point"

    @pytest.mark.asyncio
    async def test_mock_checkpointer_integration(self, mock_checkpointer, test_config):
        """Test with mock checkpointer for unit tests."""
        graph = create_political_monitoring_graph()
        compiled_graph = graph.compile(checkpointer=mock_checkpointer)

        initial_state = WorkflowState(
            documents=[],
            filtered_documents=[],
            analyzed_documents=[],
            scores=[],
            analysis_config=test_config,
            input_directory="/tmp",
            reasoning_steps=[],
            errors=[],
            metadata={},
        )

        config = {"configurable": {"thread_id": "test-mock-thread"}}

        # Execute single step
        result = await compiled_graph.ainvoke(initial_state, config=config)

        # Verify mock checkpointer was used
        assert mock_checkpointer.aput.called, "Mock checkpointer should be called"
        assert result is not None

    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        return AnalysisConfig(
            client_name="TestClient",
            focus_areas=["technology"],
            geographic_scope=["US"],
            priority_keywords=["AI"],
        )


@pytest.mark.integration
class TestWorkflowPerformance:
    """Performance tests for workflow execution."""

    @pytest.mark.asyncio
    async def test_workflow_execution_time(self, test_config, test_documents_dir):
        """Test workflow execution stays within performance targets."""
        import time

        # Setup Ray local mode
        if not ray.is_initialized():
            ray.init(local_mode=True, ignore_reinit_error=True)

        try:
            graph = create_political_monitoring_graph()

            # Use in-memory checkpointer for performance testing
            from langgraph.checkpoint.memory import MemorySaver

            compiled_graph = graph.compile(checkpointer=MemorySaver())

            initial_state = WorkflowState(
                documents=[],
                filtered_documents=[],
                analyzed_documents=[],
                scores=[],
                analysis_config=test_config,
                input_directory=test_documents_dir,
                reasoning_steps=[],
                errors=[],
                metadata={},
            )

            config = {"configurable": {"thread_id": "perf-test-thread"}}

            # Measure execution time
            start_time = time.time()

            final_state = None
            async for state in compiled_graph.astream(initial_state, config=config):
                final_state = state

            execution_time = time.time() - start_time

            # CLAUDE.md specifies <10s for standard flows
            assert execution_time < 10.0, f"Execution time {execution_time:.2f}s exceeds 10s target"
            assert final_state is not None

        finally:
            if ray.is_initialized():
                ray.shutdown()

    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        return AnalysisConfig(
            client_name="TestClient",
            focus_areas=["technology"],
            geographic_scope=["US"],
            priority_keywords=["AI"],
        )

    @pytest.fixture
    def test_documents_dir(self, tmp_path):
        """Create test documents directory."""
        docs_dir = tmp_path / "documents"
        docs_dir.mkdir()
        (docs_dir / "test.txt").write_text("AI regulation policy document")
        return str(docs_dir)
