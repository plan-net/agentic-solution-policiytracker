import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import tempfile
import os

# Import Kodosumi app
from app import app as kodosumi_app
from kodosumi.core import InputsError


@pytest.fixture
def client():
    """Create test client for Kodosumi app."""
    return TestClient(kodosumi_app)


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
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
core_industries:
  - technology
primary_markets:
  - global
strategic_themes:
  - innovation
""")
        
        # Create sample input documents
        sample_doc = os.path.join(input_dir, "sample.txt")
        with open(sample_doc, "w") as f:
            f.write("This is a sample political document for testing.")
        
        yield {
            "input": input_dir,
            "output": output_dir,
            "context": context_dir,
            "context_file": context_file,
            "sample_doc": sample_doc
        }


@pytest.fixture
def mock_tracer():
    """Mock Kodosumi tracer."""
    tracer = AsyncMock()
    tracer.markdown = AsyncMock()
    return tracer


@pytest.fixture
def mock_request():
    """Mock FastAPI request object."""
    request = MagicMock()
    request.url = "http://localhost:8001/political-analysis"
    return request


class TestKodosumiHealthEndpoint:
    """Test Kodosumi health check endpoint."""
    
    def test_health_check(self, client):
        """Test health endpoint returns success."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "political-monitoring-agent"
        assert "version" in data


class TestKodosumiFormValidation:
    """Test Kodosumi form validation and InputsError handling."""
    
    @patch('app.Launch')
    async def test_valid_form_submission(self, mock_launch, mock_request, temp_dirs):
        """Test valid form submission creates Launch object."""
        from app import enter
        
        # Mock Launch to return success
        mock_launch.return_value = {"success": True}
        
        valid_inputs = {
            "job_name": "Test Analysis",
            "input_folder": temp_dirs["input"],
            "context_file": temp_dirs["context_file"],
            "priority_threshold": 70.0,
            "include_low_confidence": False,
            "clustering_enabled": True,
            "batch_size": 50,
            "timeout_minutes": 30,
            "instructions": "Test analysis"
        }
        
        result = await enter(mock_request, valid_inputs)
        
        # Verify Launch was called with correct parameters
        mock_launch.assert_called_once()
        call_args = mock_launch.call_args
        assert call_args[0][0] == mock_request  # request object
        assert call_args[0][1] == "political_analyzer:execute_analysis"  # entrypoint
        
        # Verify inputs were passed correctly
        passed_inputs = call_args[1]["inputs"]
        assert passed_inputs["job_name"] == "Test Analysis"
        assert passed_inputs["input_folder"] == temp_dirs["input"]
        assert passed_inputs["priority_threshold"] == 70.0
    
    async def test_missing_job_name_validation(self, mock_request):
        """Test validation error for missing job name."""
        from app import enter
        
        invalid_inputs = {
            "job_name": "",  # Empty job name
            "input_folder": "/some/path",
            "context_file": "/some/context.yaml"
        }
        
        with pytest.raises(InputsError) as exc_info:
            await enter(mock_request, invalid_inputs)
        
        # Check that the error contains job_name field error
        error = exc_info.value
        assert error.has_errors()
    
    async def test_short_job_name_validation(self, mock_request):
        """Test validation error for short job name."""
        from app import enter
        
        invalid_inputs = {
            "job_name": "ab",  # Too short (< 3 chars)
            "input_folder": "/some/path",
            "context_file": "/some/context.yaml"
        }
        
        with pytest.raises(InputsError):
            await enter(mock_request, invalid_inputs)
    
    async def test_invalid_priority_threshold(self, mock_request):
        """Test validation error for invalid priority threshold."""
        from app import enter
        
        invalid_inputs = {
            "job_name": "Valid Job Name",
            "input_folder": "/some/path",
            "context_file": "/some/context.yaml",
            "priority_threshold": 150.0  # > 100
        }
        
        with pytest.raises(InputsError):
            await enter(mock_request, invalid_inputs)
    
    async def test_invalid_batch_size(self, mock_request):
        """Test validation error for invalid batch size."""
        from app import enter
        
        invalid_inputs = {
            "job_name": "Valid Job Name",
            "input_folder": "/some/path",
            "context_file": "/some/context.yaml",
            "batch_size": 5  # < 10
        }
        
        with pytest.raises(InputsError):
            await enter(mock_request, invalid_inputs)
    
    async def test_invalid_timeout(self, mock_request):
        """Test validation error for invalid timeout."""
        from app import enter
        
        invalid_inputs = {
            "job_name": "Valid Job Name",
            "input_folder": "/some/path",
            "context_file": "/some/context.yaml",
            "timeout_minutes": 200  # > 120
        }
        
        with pytest.raises(InputsError):
            await enter(mock_request, invalid_inputs)


class TestKodosumiInputProcessing:
    """Test input processing and data transformation."""
    
    @patch('app.Launch')
    async def test_boolean_input_processing(self, mock_launch, mock_request, temp_dirs):
        """Test boolean inputs are properly converted."""
        from app import enter
        
        mock_launch.return_value = {"success": True}
        
        inputs = {
            "job_name": "Test Job",
            "input_folder": temp_dirs["input"],
            "context_file": temp_dirs["context_file"],
            "include_low_confidence": "true",  # String that should become boolean
            "clustering_enabled": "false"     # String that should become boolean
        }
        
        await enter(mock_request, inputs)
        
        # Check that Launch was called with proper boolean values
        call_args = mock_launch.call_args
        passed_inputs = call_args[1]["inputs"]
        assert passed_inputs["include_low_confidence"] is True
        assert passed_inputs["clustering_enabled"] is False
    
    @patch('app.Launch')
    async def test_numeric_input_processing(self, mock_request, temp_dirs):
        """Test numeric inputs are properly converted."""
        from app import enter
        
        with patch('app.Launch') as mock_launch:
            mock_launch.return_value = {"success": True}
            
            inputs = {
                "job_name": "Test Job",
                "input_folder": temp_dirs["input"],
                "context_file": temp_dirs["context_file"],
                "priority_threshold": "85.5",  # String that should become float
                "batch_size": "100",           # String that should become int
                "timeout_minutes": "45"       # String that should become int
            }
            
            await enter(mock_request, inputs)
            
            # Check that Launch was called with proper numeric values
            call_args = mock_launch.call_args
            passed_inputs = call_args[1]["inputs"]
            assert passed_inputs["priority_threshold"] == 85.5
            assert passed_inputs["batch_size"] == 100
            assert passed_inputs["timeout_minutes"] == 45
    
    @patch('app.Launch')
    async def test_default_values(self, mock_launch, mock_request, temp_dirs):
        """Test default values are applied correctly."""
        from app import enter
        
        mock_launch.return_value = {"success": True}
        
        # Minimal inputs - should get defaults
        inputs = {
            "job_name": "Test Job",
            "input_folder": temp_dirs["input"],
            "context_file": temp_dirs["context_file"]
        }
        
        await enter(mock_request, inputs)
        
        # Check that Launch was called with default values
        call_args = mock_launch.call_args
        passed_inputs = call_args[1]["inputs"]
        assert passed_inputs["priority_threshold"] == 70.0
        assert passed_inputs["include_low_confidence"] is False
        assert passed_inputs["clustering_enabled"] is True
        assert passed_inputs["batch_size"] == 50
        assert passed_inputs["timeout_minutes"] == 30
        assert passed_inputs["instructions"] == ""


class TestKodosumiEntrypointIntegration:
    """Test integration with political_analyzer entrypoint."""
    
    @patch('app.Launch')
    async def test_launch_path_configuration(self, mock_launch, mock_request, temp_dirs):
        """Test Launch is configured with correct entrypoint path."""
        from app import enter
        
        mock_launch.return_value = {"success": True}
        
        inputs = {
            "job_name": "Test Job",
            "input_folder": temp_dirs["input"],
            "context_file": temp_dirs["context_file"]
        }
        
        await enter(mock_request, inputs)
        
        # Verify Launch was called with correct entrypoint path
        call_args = mock_launch.call_args
        assert call_args[0][1] == "political_analyzer:execute_analysis"
    
    @patch('app.Launch')
    async def test_input_data_structure(self, mock_launch, mock_request, temp_dirs):
        """Test that inputs are structured correctly for entrypoint."""
        from app import enter
        
        mock_launch.return_value = {"success": True}
        
        inputs = {
            "job_name": "Integration Test",
            "input_folder": temp_dirs["input"],
            "context_file": temp_dirs["context_file"],
            "priority_threshold": 80.0,
            "include_low_confidence": True,
            "clustering_enabled": False,
            "batch_size": 25,
            "timeout_minutes": 60,
            "instructions": "Custom instructions"
        }
        
        await enter(mock_request, inputs)
        
        # Verify all inputs are passed to entrypoint
        call_args = mock_launch.call_args
        passed_inputs = call_args[1]["inputs"]
        
        # Check all expected keys are present
        expected_keys = {
            "job_name", "input_folder", "context_file", "priority_threshold",
            "include_low_confidence", "clustering_enabled", "batch_size", 
            "timeout_minutes", "instructions"
        }
        assert set(passed_inputs.keys()) == expected_keys
        
        # Check values match inputs
        assert passed_inputs["job_name"] == "Integration Test"
        assert passed_inputs["input_folder"] == temp_dirs["input"]
        assert passed_inputs["context_file"] == temp_dirs["context_file"]
        assert passed_inputs["priority_threshold"] == 80.0
        assert passed_inputs["include_low_confidence"] is True
        assert passed_inputs["clustering_enabled"] is False
        assert passed_inputs["batch_size"] == 25
        assert passed_inputs["timeout_minutes"] == 60
        assert passed_inputs["instructions"] == "Custom instructions"


class TestKodosumiErrorHandling:
    """Test error handling and user feedback."""
    
    async def test_multiple_validation_errors(self, mock_request):
        """Test handling multiple validation errors at once."""
        from app import enter
        
        invalid_inputs = {
            "job_name": "",                    # Empty job name
            "input_folder": "",                # Empty input folder
            "context_file": "",                # Empty context file
            "priority_threshold": 150.0,       # Invalid threshold
            "batch_size": 5,                   # Invalid batch size
            "timeout_minutes": 200             # Invalid timeout
        }
        
        with pytest.raises(InputsError) as exc_info:
            await enter(mock_request, invalid_inputs)
        
        error = exc_info.value
        assert error.has_errors()
        # Should have multiple field errors
    
    async def test_edge_case_values(self, mock_request, temp_dirs):
        """Test edge case values for numeric inputs."""
        from app import enter
        
        # Test boundary values
        boundary_inputs = {
            "job_name": "abc",  # Minimum length (3 chars)
            "input_folder": temp_dirs["input"],
            "context_file": temp_dirs["context_file"],
            "priority_threshold": 0.0,    # Minimum value
            "batch_size": 10,             # Minimum value
            "timeout_minutes": 5          # Minimum value
        }
        
        # Should not raise validation error
        with patch('app.Launch') as mock_launch:
            mock_launch.return_value = {"success": True}
            await enter(mock_request, boundary_inputs)
            assert mock_launch.called
        
        # Test maximum boundary values
        max_boundary_inputs = {
            "job_name": "Maximum boundary test",
            "input_folder": temp_dirs["input"],
            "context_file": temp_dirs["context_file"],
            "priority_threshold": 100.0,  # Maximum value
            "batch_size": 1000,           # Maximum value
            "timeout_minutes": 120        # Maximum value
        }
        
        with patch('app.Launch') as mock_launch:
            mock_launch.return_value = {"success": True}
            await enter(mock_request, max_boundary_inputs)
            assert mock_launch.called