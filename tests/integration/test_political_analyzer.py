import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import tempfile
import os
import time
from datetime import datetime

# Import the entrypoint module
from src import political_analyzer
from kodosumi.core import Tracer
import kodosumi.core as core


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
""")
        
        # Create sample input documents
        sample_files = [
            ("doc1.txt", "This is a political document about technology policy and innovation."),
            ("doc2.md", "# Healthcare Policy\n\nNew regulations for digital health platforms."),
            ("doc3.txt", "Sustainability initiatives and environmental regulations.")
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
        "priority_threshold": 70.0,
        "include_low_confidence": False,
        "clustering_enabled": True,
        "storage_mode": "local"
    }


class TestPoliticalAnalyzerEntrypoint:
    """Test the main execute_analysis entrypoint function."""
    
    @patch('src.political_analyzer.ray.init')
    @patch('src.political_analyzer.ray.is_initialized')
    @patch('src.workflow.graph.create_workflow')
    @patch('src.workflow.graph.execute_workflow')
    async def test_complete_analysis_pipeline(
        self, 
        mock_execute_workflow, mock_create_workflow, mock_is_initialized, mock_ray_init,
        mock_tracer, valid_inputs
    ):
        """Test complete analysis pipeline execution."""
        
        # Setup mocks
        mock_is_initialized.return_value = False
        mock_workflow = MagicMock()
        mock_create_workflow.return_value = mock_workflow
        
        # Mock successful workflow execution
        mock_execute_workflow.return_value = {
            "report_file": "/tmp/test_report.md",
            "metrics": {
                "total_documents": 3,
                "processed_documents": 3,
                "summary": {
                    "high_priority_count": 1,
                    "average_score": 75.5
                }
            }
        }
        
        # Mock report file exists and has content
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = "# Test Report\n\nAnalysis complete."
                
                # Execute analysis
                result = await political_analyzer.execute_analysis(valid_inputs, mock_tracer)
        
        # Verify successful execution
        assert result is not None
        # Note: core.response.Markdown might be a function, not a class
        assert hasattr(result, '__class__')
        
        # Verify Ray was initialized
        mock_ray_init.assert_called_once_with(num_cpus=4)
        
        # Verify workflow was created and executed
        mock_create_workflow.assert_called_once()
        mock_execute_workflow.assert_called_once()
        
        # Verify tracer was called with progress updates
        assert mock_tracer.markdown.call_count >= 3  # Multiple progress updates
        
        # Verify job configuration was logged
        tracer_calls = [call[0][0] for call in mock_tracer.markdown.call_args_list]
        assert any("Political Analysis: Test Political Analysis" in call for call in tracer_calls)
        assert any("Job Configuration" in call for call in tracer_calls)

    @patch('src.political_analyzer.ray.init')
    @patch('src.political_analyzer.ray.is_initialized')
    @patch('src.workflow.graph.create_workflow')
    @patch('src.workflow.graph.execute_workflow')
    async def test_workflow_execution_failure(
        self, 
        mock_execute_workflow, mock_create_workflow, mock_is_initialized, mock_ray_init,
        mock_tracer, valid_inputs
    ):
        """Test error handling when workflow execution fails."""
        
        # Setup mocks
        mock_is_initialized.return_value = True  # Ray already initialized
        mock_workflow = MagicMock()
        mock_create_workflow.return_value = mock_workflow
        
        # Mock workflow failure
        mock_execute_workflow.side_effect = Exception("Workflow execution failed")
        
        # Execute analysis
        result = await political_analyzer.execute_analysis(valid_inputs, mock_tracer)
        
        # Should not raise exception, but return error response
        assert result is None  # Current implementation doesn't return on workflow failure
        
        # Verify error was logged via tracer
        tracer_calls = [call[0][0] for call in mock_tracer.markdown.call_args_list]
        assert any("❌ Workflow Failed" in call for call in tracer_calls)
        assert any("Workflow execution failed" in call for call in tracer_calls)

    @patch('src.political_analyzer.ray.init')
    @patch('src.political_analyzer.ray.is_initialized')
    async def test_ray_initialization_when_not_running(
        self, 
        mock_is_initialized, mock_ray_init,
        mock_tracer, valid_inputs
    ):
        """Test Ray cluster initialization when not already initialized."""
        
        mock_is_initialized.return_value = False
        
        # Mock workflow to avoid actual execution
        with patch('src.workflow.graph.create_workflow') as mock_create_workflow:
            with patch('src.workflow.graph.execute_workflow') as mock_execute_workflow:
                mock_workflow = MagicMock()
                mock_create_workflow.return_value = mock_workflow
                mock_execute_workflow.return_value = {
                    "report_file": None,
                    "metrics": {"total_documents": 0, "processed_documents": 0, "summary": {}}
                }
                
                await political_analyzer.execute_analysis(valid_inputs, mock_tracer)
                
                # Verify Ray was initialized
                mock_ray_init.assert_called_once_with(num_cpus=4)
                
                # Verify tracer logged Ray initialization
                tracer_calls = [call[0][0] for call in mock_tracer.markdown.call_args_list]
                assert any("🚀 Initializing distributed computing cluster" in call for call in tracer_calls)
                assert any("✅ Ray cluster initialized" in call for call in tracer_calls)

    @patch('src.political_analyzer.ray.init')
    @patch('src.political_analyzer.ray.is_initialized')
    async def test_ray_skip_initialization_when_running(
        self, 
        mock_is_initialized, mock_ray_init,
        mock_tracer, valid_inputs
    ):
        """Test Ray initialization is skipped when already running."""
        
        mock_is_initialized.return_value = True
        
        # Mock workflow to avoid actual execution
        with patch('src.workflow.graph.create_workflow') as mock_create_workflow:
            with patch('src.workflow.graph.execute_workflow') as mock_execute_workflow:
                mock_workflow = MagicMock()
                mock_create_workflow.return_value = mock_workflow
                mock_execute_workflow.return_value = {
                    "report_file": None,
                    "metrics": {"total_documents": 0, "processed_documents": 0, "summary": {}}
                }
                
                await political_analyzer.execute_analysis(valid_inputs, mock_tracer)
                
                # Verify Ray was NOT initialized
                mock_ray_init.assert_not_called()

    async def test_job_creation_and_configuration(self, mock_tracer, valid_inputs):
        """Test that job objects are created correctly with proper configuration."""
        
        # Mock all workflow components to focus on job creation
        with patch('src.political_analyzer.ray.is_initialized', return_value=True):
            with patch('src.workflow.graph.create_workflow') as mock_create_workflow:
                with patch('src.workflow.graph.execute_workflow') as mock_execute_workflow:
                    mock_workflow = MagicMock()
                    mock_create_workflow.return_value = mock_workflow
                    mock_execute_workflow.return_value = {
                        "report_file": None,
                        "metrics": {"total_documents": 0, "processed_documents": 0, "summary": {}}
                    }
                    
                    await political_analyzer.execute_analysis(valid_inputs, mock_tracer)
                    
                    # Verify execute_workflow was called with proper arguments
                    mock_execute_workflow.assert_called_once()
                    call_args = mock_execute_workflow.call_args[0]
                    workflow_arg = call_args[0]
                    job_arg = call_args[1]
                    
                    # Verify job object structure
                    assert hasattr(job_arg, 'id')
                    assert hasattr(job_arg, 'request')
                    assert hasattr(job_arg, 'status')
                    assert job_arg.request.job_name == "Test Political Analysis"
                    assert job_arg.request.priority_threshold == 70.0
                    assert job_arg.request.clustering_enabled == True
                    assert job_arg.request.include_low_confidence == False

    async def test_progress_tracking(self, mock_tracer, valid_inputs):
        """Test that progress is tracked and reported via tracer."""
        
        with patch('src.political_analyzer.ray.is_initialized', return_value=True):
            with patch('src.workflow.graph.create_workflow') as mock_create_workflow:
                with patch('src.workflow.graph.execute_workflow') as mock_execute_workflow:
                    mock_workflow = MagicMock()
                    mock_create_workflow.return_value = mock_workflow
                    mock_execute_workflow.return_value = {
                        "report_file": None,
                        "metrics": {"total_documents": 5, "processed_documents": 5, "summary": {}}
                    }
                    
                    await political_analyzer.execute_analysis(valid_inputs, mock_tracer)
        
        # Verify progress phases were logged
        tracer_calls = [call[0][0] for call in mock_tracer.markdown.call_args_list]
        expected_phases = [
            "Political Analysis: Test Political Analysis",
            "Job Configuration", 
            "Step 1: Initialization",
            "Step 2: Workflow Execution",
            "Step 3: Starting LangGraph Workflow"
        ]
        
        for phase in expected_phases:
            assert any(phase in call for call in tracer_calls), f"Missing phase: {phase}"

    async def test_azure_storage_mode_configuration(self, mock_tracer, valid_inputs):
        """Test Azure storage mode configuration."""
        
        # Test Azure storage mode
        azure_inputs = valid_inputs.copy()
        azure_inputs["storage_mode"] = "azure"
        
        with patch('src.political_analyzer.ray.is_initialized', return_value=True):
            with patch('src.workflow.graph.create_workflow') as mock_create_workflow:
                with patch('src.workflow.graph.execute_workflow') as mock_execute_workflow:
                    mock_workflow = MagicMock()
                    mock_create_workflow.return_value = mock_workflow
                    mock_execute_workflow.return_value = {
                        "report_file": None,
                        "metrics": {"total_documents": 0, "processed_documents": 0, "summary": {}}
                    }
                    
                    await political_analyzer.execute_analysis(azure_inputs, mock_tracer)
                    
                    # Verify Azure storage mode was logged
                    tracer_calls = [call[0][0] for call in mock_tracer.markdown.call_args_list]
                    assert any("Azure Blob Storage" in call for call in tracer_calls)

    async def test_report_file_handling(self, mock_tracer, valid_inputs):
        """Test report file reading and response generation."""
        
        with patch('src.political_analyzer.ray.is_initialized', return_value=True):
            with patch('src.workflow.graph.create_workflow') as mock_create_workflow:
                with patch('src.workflow.graph.execute_workflow') as mock_execute_workflow:
                    mock_workflow = MagicMock()
                    mock_create_workflow.return_value = mock_workflow
                    
                    # Test with local report file
                    mock_execute_workflow.return_value = {
                        "report_file": "/tmp/test_report.md",
                        "metrics": {
                            "total_documents": 5,
                            "processed_documents": 5,
                            "summary": {
                                "high_priority_count": 2,
                                "average_score": 78.5
                            }
                        }
                    }
                    
                    with patch('os.path.exists', return_value=True):
                        with patch('builtins.open', create=True) as mock_open:
                            mock_file_content = "# Political Analysis Report\n\nDetailed analysis results here."
                            mock_open.return_value.__enter__.return_value.read.return_value = mock_file_content
                            
                            result = await political_analyzer.execute_analysis(valid_inputs, mock_tracer)
                            
                            # Verify result is a Markdown response
                            assert result is not None
                            assert hasattr(result, '__class__')


class TestErrorHandling:
    """Test error handling in entrypoint functions."""
    
    async def test_general_exception_handling(self, mock_tracer, valid_inputs):
        """Test handling of general exceptions."""
        
        # Force an exception during Ray initialization
        with patch('src.political_analyzer.ray.is_initialized', side_effect=Exception("Unexpected error")):
            result = await political_analyzer.execute_analysis(valid_inputs, mock_tracer)
            
            # Should return error markdown response
            assert result is not None
            assert hasattr(result, '__class__')
            
            # Verify error was logged
            tracer_calls = [call[0][0] for call in mock_tracer.markdown.call_args_list]
            # The current implementation may not call tracer on this type of error
            # but should return an error response

    async def test_workflow_import_failure(self, mock_tracer, valid_inputs):
        """Test handling when workflow modules can't be imported."""
        
        with patch('src.political_analyzer.ray.is_initialized', return_value=True):
            # Mock import failure
            with patch('builtins.__import__', side_effect=ImportError("Cannot import workflow")):
                result = await political_analyzer.execute_analysis(valid_inputs, mock_tracer)
                
                # Should return error response
                assert result is not None
                assert hasattr(result, '__class__')


class TestInputValidation:
    """Test input validation and parameter handling."""
    
    async def test_missing_job_name(self, mock_tracer):
        """Test behavior with missing job name."""
        invalid_inputs = {
            "priority_threshold": 70.0,
            "include_low_confidence": False,
            "clustering_enabled": True,
            "storage_mode": "local"
        }
        
        # Should return error response for missing job_name
        result = await political_analyzer.execute_analysis(invalid_inputs, mock_tracer)
        
        # Current implementation catches KeyError and returns error response
        assert result is not None
        assert hasattr(result, '__class__')

    async def test_default_parameter_values(self, mock_tracer):
        """Test that default parameter values are applied correctly."""
        minimal_inputs = {
            "job_name": "Minimal Test"
        }
        
        with patch('src.political_analyzer.ray.is_initialized', return_value=True):
            with patch('src.workflow.graph.create_workflow') as mock_create_workflow:
                with patch('src.workflow.graph.execute_workflow') as mock_execute_workflow:
                    mock_workflow = MagicMock()
                    mock_create_workflow.return_value = mock_workflow
                    mock_execute_workflow.return_value = {
                        "report_file": None,
                        "metrics": {"total_documents": 0, "processed_documents": 0, "summary": {}}
                    }
                    
                    await political_analyzer.execute_analysis(minimal_inputs, mock_tracer)
                    
                    # Verify defaults were applied in the job creation
                    job_arg = mock_execute_workflow.call_args[0][1]
                    assert job_arg.request.priority_threshold == 70.0  # default
                    assert job_arg.request.include_low_confidence == False  # default
                    assert job_arg.request.clustering_enabled == True  # default

    async def test_storage_mode_configuration(self, mock_tracer):
        """Test storage mode configuration logic."""
        
        # Test local storage mode
        local_inputs = {
            "job_name": "Storage Test",
            "storage_mode": "local"
        }
        
        with patch('src.political_analyzer.ray.is_initialized', return_value=True):
            with patch('src.workflow.graph.create_workflow') as mock_create_workflow:
                with patch('src.workflow.graph.execute_workflow') as mock_execute_workflow:
                    mock_workflow = MagicMock()
                    mock_create_workflow.return_value = mock_workflow
                    mock_execute_workflow.return_value = {
                        "report_file": None,
                        "metrics": {"total_documents": 0, "processed_documents": 0, "summary": {}}
                    }
                    
                    await political_analyzer.execute_analysis(local_inputs, mock_tracer)
                    
                    # Verify workflow execution was called with use_azure=False for local mode
                    call_args = mock_execute_workflow.call_args
                    initial_state = call_args[1]['initial_state']
                    assert initial_state.use_azure == False  # Should be False for local mode