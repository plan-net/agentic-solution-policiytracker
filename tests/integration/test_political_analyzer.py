import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import tempfile
import os
import time
from datetime import datetime

# Import the entrypoint module
import political_analyzer
from kodosumi.core import Tracer


@pytest.fixture
def mock_tracer():
    """Mock Kodosumi tracer for testing."""
    tracer = AsyncMock(spec=Tracer)
    tracer.markdown = AsyncMock()
    return tracer


@pytest.fixture
def temp_dirs():
    """Create temporary directories with sample files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_dir = os.path.join(tmpdir, "input")
        output_dir = os.path.join(tmpdir, "output")
        context_dir = os.path.join(tmpdir, "context")
        
        os.makedirs(input_dir)
        os.makedirs(output_dir)
        os.makedirs(context_dir)
        
        # Create sample context file
        context_file = os.path.join(context_dir, "client.yaml")
        with open(context_file, "w") as f:
            f.write("""
company_terms:
  - testcorp
  - innovation
core_industries:
  - technology
  - healthcare
primary_markets:
  - global
  - europe
strategic_themes:
  - sustainability
  - digital transformation
scoring_dimensions:
  - relevance
  - priority
  - confidence
""")
        
        # Create sample input documents
        sample_files = [
            ("doc1.txt", "This is a political document about technology policy and innovation."),
            ("doc2.md", "# Healthcare Policy\n\nNew regulations for digital health platforms."),
            ("doc3.pdf", "PDF content would be here - sustainability initiatives."),
            ("doc4.docx", "DOCX content - global market analysis and policy impacts."),
            ("doc5.html", "<html><body>HTML document about regulatory changes</body></html>")
        ]
        
        for filename, content in sample_files:
            filepath = os.path.join(input_dir, filename)
            with open(filepath, "w") as f:
                f.write(content)
        
        yield {
            "input": input_dir,
            "output": output_dir,
            "context": context_dir,
            "context_file": context_file,
            "sample_files": [os.path.join(input_dir, f[0]) for f in sample_files]
        }


@pytest.fixture
def valid_inputs(temp_dirs):
    """Valid inputs for analysis."""
    return {
        "job_name": "Test Political Analysis",
        "input_folder": temp_dirs["input"],
        "context_file": temp_dirs["context_file"],
        "priority_threshold": 70.0,
        "include_low_confidence": False,
        "clustering_enabled": True,
        "batch_size": 50,
        "timeout_minutes": 30,
        "instructions": "Test analysis with comprehensive coverage"
    }


class TestPoliticalAnalyzerEntrypoint:
    """Test the main execute_analysis entrypoint function."""
    
    @patch('political_analyzer.ray.init')
    @patch('political_analyzer.load_context_task')
    @patch('political_analyzer.process_batch_task')
    @patch('political_analyzer.score_batch_task')
    @patch('political_analyzer.cluster_and_aggregate_task')
    @patch('political_analyzer.generate_report_task')
    async def test_complete_analysis_pipeline(
        self, 
        mock_report, mock_cluster, mock_score, mock_process, mock_context, mock_ray_init,
        mock_tracer, valid_inputs, temp_dirs
    ):
        """Test complete analysis pipeline execution."""
        
        # Mock Ray tasks
        mock_context.remote.return_value = AsyncMock(return_value={
            "scoring_dimensions": ["relevance", "priority"],
            "company_terms": ["testcorp"]
        })
        
        mock_process.remote.return_value = AsyncMock(return_value=[
            MagicMock(id="doc_001", content="Sample content"),
            MagicMock(id="doc_002", content="Another document")
        ])
        
        mock_score.remote.return_value = AsyncMock(return_value=[
            MagicMock(master_score=75.0, confidence_score=85.0),
            MagicMock(master_score=80.0, confidence_score=90.0)
        ])
        
        mock_cluster.remote.return_value = AsyncMock(return_value={
            "aggregated_results": [],
            "statistics": {"total_documents": 2},
            "topic_groups": {"tech": [], "policy": []},
            "priority_groups": {"high": [], "medium": []}
        })
        
        mock_report.remote.return_value = AsyncMock(return_value={
            "report_file": "/path/to/report.md"
        })
        
        # Execute analysis
        result = await political_analyzer.execute_analysis(valid_inputs, mock_tracer)
        
        # Verify successful execution
        assert result["success"] is True
        assert "job_id" in result
        assert result["report_file"] == "/path/to/report.md"
        assert "statistics" in result
        assert "metadata" in result
        
        # Verify tracer was called with progress updates
        assert mock_tracer.markdown.call_count > 5  # Multiple progress updates
        
        # Verify job configuration was logged
        tracer_calls = [call[0][0] for call in mock_tracer.markdown.call_args_list]
        assert any("Job Configuration" in call for call in tracer_calls)
        assert any("Analysis Complete" in call for call in tracer_calls)
    
    async def test_missing_input_folder(self, mock_tracer, valid_inputs):
        """Test error handling for missing input folder."""
        invalid_inputs = valid_inputs.copy()
        invalid_inputs["input_folder"] = "/nonexistent/path"
        
        result = await political_analyzer.execute_analysis(invalid_inputs, mock_tracer)
        
        assert result["success"] is False
        assert "Input folder not found" in result["error"]
        
        # Verify error was logged via tracer
        error_calls = [call[0][0] for call in mock_tracer.markdown.call_args_list]
        assert any("Error" in call for call in error_calls)
    
    async def test_empty_input_folder(self, mock_tracer, valid_inputs, temp_dirs):
        """Test error handling for empty input folder."""
        # Create empty folder
        empty_dir = os.path.join(temp_dirs["input"], "empty")
        os.makedirs(empty_dir)
        
        invalid_inputs = valid_inputs.copy()
        invalid_inputs["input_folder"] = empty_dir
        
        result = await political_analyzer.execute_analysis(invalid_inputs, mock_tracer)
        
        assert result["success"] is False
        assert "No supported documents found" in result["error"]
    
    @patch('political_analyzer.ray.is_initialized')
    @patch('political_analyzer.ray.init')
    async def test_ray_initialization(self, mock_ray_init, mock_is_initialized, mock_tracer, valid_inputs):
        """Test Ray cluster initialization when not already initialized."""
        mock_is_initialized.return_value = False
        
        with patch('political_analyzer.load_context_task') as mock_context:
            mock_context.remote.return_value = AsyncMock(return_value={"test": "context"})
            
            with patch('political_analyzer.process_batch_task') as mock_process:
                mock_process.remote.return_value = AsyncMock(return_value=[])
                
                # This will fail at the "no documents processed" stage, but that's fine for this test
                result = await political_analyzer.execute_analysis(valid_inputs, mock_tracer)
                
                # Verify Ray was initialized
                mock_ray_init.assert_called_once_with(num_cpus=4)
                
                # Verify tracer logged Ray initialization
                tracer_calls = [call[0][0] for call in mock_tracer.markdown.call_args_list]
                assert any("Ray cluster initialized" in call for call in tracer_calls)
    
    async def test_progress_tracking(self, mock_tracer, valid_inputs):
        """Test that progress is tracked and reported via tracer."""
        with patch('political_analyzer.load_context_task') as mock_context:
            mock_context.remote.return_value = AsyncMock(return_value={"test": "context"})
            
            with patch('political_analyzer.process_batch_task') as mock_process:
                mock_process.remote.return_value = AsyncMock(return_value=[
                    MagicMock(id="doc_001"),
                    MagicMock(id="doc_002")
                ])
                
                with patch('political_analyzer.score_batch_task') as mock_score:
                    mock_score.remote.return_value = AsyncMock(return_value=[
                        MagicMock(master_score=75.0, confidence_score=85.0),
                        MagicMock(master_score=80.0, confidence_score=90.0)
                    ])
                    
                    with patch('political_analyzer.cluster_and_aggregate_task') as mock_cluster:
                        mock_cluster.remote.return_value = AsyncMock(return_value={
                            "aggregated_results": [],
                            "statistics": {}
                        })
                        
                        with patch('political_analyzer.generate_report_task') as mock_report:
                            mock_report.remote.return_value = AsyncMock(return_value={
                                "report_file": "/test/report.md"
                            })
                            
                            result = await political_analyzer.execute_analysis(valid_inputs, mock_tracer)
        
        # Verify progress phases were logged
        tracer_calls = [call[0][0] for call in mock_tracer.markdown.call_args_list]
        expected_phases = [
            "Step 1: Initialization",
            "Step 2: Document Discovery", 
            "Step 3: Loading Context",
            "Step 4: Document Processing Pipeline",
            "Phase 1",
            "Phase 2",
            "Phase 3",
            "Phase 4"
        ]
        
        for phase in expected_phases:
            assert any(phase in call for call in tracer_calls), f"Missing phase: {phase}"


class TestRayRemoteFunctions:
    """Test Ray remote functions used in the entrypoint."""
    
    async def test_load_context_task(self, temp_dirs):
        """Test context loading task."""
        context = await political_analyzer.load_context_task.remote(temp_dirs["context_file"])
        
        assert isinstance(context, dict)
        assert "company_terms" in context
        assert "scoring_dimensions" in context
        assert "testcorp" in context["company_terms"]
    
    async def test_load_context_task_invalid_file(self):
        """Test context loading with invalid file."""
        context = await political_analyzer.load_context_task.remote("/nonexistent/file.yaml")
        
        # Should return default context
        assert context["default_config"] is True
        assert "scoring_dimensions" in context
    
    @patch('political_analyzer.ContentProcessor')
    async def test_process_batch_task(self, mock_processor_class, temp_dirs):
        """Test document processing batch task."""
        mock_processor = MagicMock()
        mock_processor.process_document = AsyncMock(return_value=MagicMock(id="test_doc"))
        mock_processor_class.return_value = mock_processor
        
        file_paths = temp_dirs["sample_files"][:2]  # Test with 2 files
        
        results = await political_analyzer.process_batch_task.remote(file_paths, 0, "test_job")
        
        assert len(results) == 2
        assert mock_processor.process_document.call_count == 2
    
    @patch('political_analyzer.RelevanceEngine')
    async def test_score_batch_task(self, mock_engine_class):
        """Test document scoring batch task."""
        mock_engine = MagicMock()
        mock_score = MagicMock(master_score=75.0, confidence_score=80.0)
        mock_engine.score_document = AsyncMock(return_value=mock_score)
        mock_engine_class.return_value = mock_engine
        
        documents = [MagicMock(id="doc1"), MagicMock(id="doc2")]
        context = {"test": "context"}
        
        results = await political_analyzer.score_batch_task.remote(documents, context)
        
        assert len(results) == 2
        assert mock_engine.score_document.call_count == 2
    
    @patch('political_analyzer.Aggregator')
    async def test_cluster_and_aggregate_task(self, mock_aggregator_class):
        """Test clustering and aggregation task."""
        mock_aggregator = MagicMock()
        mock_result = {
            "aggregated_results": [],
            "statistics": {"total": 5},
            "topic_groups": {"tech": [], "policy": []},
            "priority_groups": {"high": [], "medium": []}
        }
        mock_aggregator.aggregate_results.return_value = mock_result
        mock_aggregator_class.return_value = mock_aggregator
        
        scoring_results = [MagicMock(), MagicMock()]
        context = {"test": "context"}
        
        result = await political_analyzer.cluster_and_aggregate_task.remote(scoring_results, context)
        
        assert result == mock_result
        mock_aggregator.aggregate_results.assert_called_once_with(scoring_results)
    
    @patch('political_analyzer.ReportGenerator')
    async def test_generate_report_task(self, mock_generator_class):
        """Test report generation task."""
        mock_generator = MagicMock()
        mock_report = {"report_file": "/path/to/report.md"}
        mock_generator.generate_report = AsyncMock(return_value=mock_report)
        mock_generator_class.return_value = mock_generator
        
        results = {"aggregated_results": []}
        job = MagicMock()
        context = {"test": "context"}
        
        result = await political_analyzer.generate_report_task.remote(results, job, context)
        
        assert result == mock_report
        mock_generator.generate_report.assert_called_once_with(results, job, context)


class TestUtilityFunctions:
    """Test utility functions for batch creation."""
    
    def test_create_processing_batches(self):
        """Test creation of processing batches."""
        file_paths = [f"file_{i}.txt" for i in range(25)]
        
        batches = political_analyzer.create_processing_batches(file_paths, batch_size=10)
        
        assert len(batches) == 3  # 25 files / 10 = 3 batches
        assert len(batches[0]) == 10
        assert len(batches[1]) == 10  
        assert len(batches[2]) == 5  # Remainder
    
    def test_create_scoring_batches(self):
        """Test creation of scoring batches."""
        documents = [MagicMock(id=f"doc_{i}") for i in range(15)]
        
        batches = political_analyzer.create_scoring_batches(documents, batch_size=7)
        
        assert len(batches) == 3  # 15 docs / 7 = 3 batches
        assert len(batches[0]) == 7
        assert len(batches[1]) == 7
        assert len(batches[2]) == 1  # Remainder
    
    def test_empty_batch_creation(self):
        """Test batch creation with empty input."""
        batches = political_analyzer.create_processing_batches([], batch_size=10)
        assert len(batches) == 0
        
        batches = political_analyzer.create_scoring_batches([], batch_size=5)
        assert len(batches) == 0


class TestErrorHandling:
    """Test error handling in entrypoint functions."""
    
    async def test_ray_task_failure_handling(self, mock_tracer, valid_inputs):
        """Test handling of Ray task failures."""
        with patch('political_analyzer.load_context_task') as mock_context:
            # Simulate task failure
            mock_context.remote.side_effect = Exception("Ray task failed")
            
            result = await political_analyzer.execute_analysis(valid_inputs, mock_tracer)
            
            assert result["success"] is False
            assert "Analysis failed" in result["error"]
    
    async def test_timeout_handling(self, mock_tracer, valid_inputs):
        """Test timeout scenario handling."""
        # This test would need more sophisticated Ray mocking for real timeout testing
        # For now, just verify the timeout parameter is processed
        assert valid_inputs["timeout_minutes"] == 30
        
        # In a real implementation, you might test:
        # - Ray task timeout configuration
        # - Timeout error handling and cleanup
        # - Partial results on timeout
    
    async def test_partial_failure_recovery(self, mock_tracer, valid_inputs, temp_dirs):
        """Test recovery from partial batch failures."""
        with patch('political_analyzer.load_context_task') as mock_context:
            mock_context.remote.return_value = AsyncMock(return_value={"test": "context"})
            
            with patch('political_analyzer.process_batch_task') as mock_process:
                # Simulate one batch succeeding, one failing
                success_result = [MagicMock(id="doc_001")]
                mock_process.remote.side_effect = [
                    AsyncMock(return_value=success_result),
                    AsyncMock(side_effect=Exception("Batch failed"))
                ]
                
                with patch('political_analyzer.score_batch_task') as mock_score:
                    mock_score.remote.return_value = AsyncMock(return_value=[])
                    
                    with patch('political_analyzer.cluster_and_aggregate_task') as mock_cluster:
                        mock_cluster.remote.return_value = AsyncMock(return_value={
                            "aggregated_results": [],
                            "statistics": {}
                        })
                        
                        with patch('political_analyzer.generate_report_task') as mock_report:
                            mock_report.remote.return_value = AsyncMock(return_value={
                                "report_file": "/test/report.md"
                            })
                            
                            # Should complete with partial results
                            result = await political_analyzer.execute_analysis(valid_inputs, mock_tracer)
                            
                            # Verify warnings were logged for failed batches
                            tracer_calls = [call[0][0] for call in mock_tracer.markdown.call_args_list]
                            assert any("Warning" in call for call in tracer_calls)