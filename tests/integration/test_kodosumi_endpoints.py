import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import tempfile
import os

# Import Kodosumi app
from src.app import app as kodosumi_app
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
    
    @patch('src.app.Launch')
    async def test_valid_form_submission(self, mock_launch, mock_request):
        """Test valid form submission creates Launch object."""
        from src.app import enter
        
        # Mock Launch to return success
        mock_launch.return_value = {"success": True}
        
        valid_inputs = {
            "job_name": "Test Analysis",
            "storage_mode": "local",
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
        assert call_args[0][1] == "src.political_analyzer:execute_analysis"  # entrypoint
        
        # Verify inputs were passed correctly
        passed_inputs = call_args[1]["inputs"]
        assert passed_inputs["job_name"] == "Test Analysis"
        assert passed_inputs["storage_mode"] == "local"
        assert passed_inputs["priority_threshold"] == 70.0
    
    async def test_missing_job_name_validation(self, mock_request):
        """Test validation error for missing job name."""
        from src.app import enter
        
        invalid_inputs = {
            "job_name": "",  # Empty job name
            "storage_mode": "local"
        }
        
        with pytest.raises(InputsError) as exc_info:
            await enter(mock_request, invalid_inputs)
        
        # Check that the error contains job_name field error
        error = exc_info.value
        assert error.has_errors()
    
    async def test_short_job_name_validation(self, mock_request):
        """Test validation error for short job name."""
        from src.app import enter
        
        invalid_inputs = {
            "job_name": "ab",  # Too short (< 3 chars)
            "storage_mode": "local"
        }
        
        with pytest.raises(InputsError):
            await enter(mock_request, invalid_inputs)
    
    async def test_invalid_priority_threshold(self, mock_request):
        """Test validation error for invalid priority threshold."""
        from src.app import enter
        
        invalid_inputs = {
            "job_name": "Valid Job Name",
            "storage_mode": "local",
            "priority_threshold": 150.0  # > 100
        }
        
        with pytest.raises(InputsError):
            await enter(mock_request, invalid_inputs)
    
    async def test_invalid_batch_size(self, mock_request):
        """Test validation error for invalid batch size."""
        from src.app import enter
        
        invalid_inputs = {
            "job_name": "Valid Job Name",
            "storage_mode": "local",
            "batch_size": 5  # < 10
        }
        
        with pytest.raises(InputsError):
            await enter(mock_request, invalid_inputs)
    
    async def test_invalid_timeout(self, mock_request):
        """Test validation error for invalid timeout."""
        from src.app import enter
        
        invalid_inputs = {
            "job_name": "Valid Job Name",
            "storage_mode": "local",
            "timeout_minutes": 200  # > 120
        }
        
        with pytest.raises(InputsError):
            await enter(mock_request, invalid_inputs)
    
    async def test_invalid_storage_mode(self, mock_request):
        """Test validation error for invalid storage mode."""
        from src.app import enter
        
        invalid_inputs = {
            "job_name": "Valid Job Name",
            "storage_mode": "invalid_mode"
        }
        
        with pytest.raises(InputsError):
            await enter(mock_request, invalid_inputs)


class TestKodosumiInputProcessing:
    """Test input processing and data transformation."""
    
    @patch('src.app.Launch')
    async def test_boolean_input_processing(self, mock_launch, mock_request):
        """Test boolean inputs are properly converted."""
        from src.app import enter
        
        mock_launch.return_value = {"success": True}
        
        inputs = {
            "job_name": "Test Job",
            "storage_mode": "local",
            "include_low_confidence": "true",  # String that should become boolean
            "clustering_enabled": "false"     # String that should become boolean
        }
        
        await enter(mock_request, inputs)
        
        # Check that Launch was called with proper boolean values
        call_args = mock_launch.call_args
        passed_inputs = call_args[1]["inputs"]
        assert passed_inputs["include_low_confidence"] is True
        assert passed_inputs["clustering_enabled"] is False
    
    @patch('src.app.Launch')
    async def test_numeric_input_processing(self, mock_request):
        """Test numeric inputs are properly converted."""
        from src.app import enter
        
        with patch('src.app.Launch') as mock_launch:
            mock_launch.return_value = {"success": True}
            
            inputs = {
                "job_name": "Test Job",
                "storage_mode": "local",
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
    
    @patch('src.app.Launch')
    async def test_default_values(self, mock_launch, mock_request):
        """Test default values are applied correctly."""
        from src.app import enter
        
        mock_launch.return_value = {"success": True}
        
        # Minimal inputs - should get defaults
        inputs = {
            "job_name": "Test Job",
            "storage_mode": "local"
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
        assert passed_inputs["storage_mode"] == "local"


class TestKodosumiEntrypointIntegration:
    """Test integration with political_analyzer entrypoint."""
    
    @patch('src.app.Launch')
    async def test_launch_path_configuration(self, mock_launch, mock_request):
        """Test Launch is configured with correct entrypoint path."""
        from src.app import enter
        
        mock_launch.return_value = {"success": True}
        
        inputs = {
            "job_name": "Test Job",
            "storage_mode": "local"
        }
        
        await enter(mock_request, inputs)
        
        # Verify Launch was called with correct entrypoint path
        call_args = mock_launch.call_args
        assert call_args[0][1] == "src.political_analyzer:execute_analysis"
    
    @patch('src.app.Launch')
    async def test_input_data_structure(self, mock_launch, mock_request):
        """Test that inputs are structured correctly for entrypoint."""
        from src.app import enter
        
        mock_launch.return_value = {"success": True}
        
        inputs = {
            "job_name": "Integration Test",
            "storage_mode": "azure",
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
            "job_name", "storage_mode", "priority_threshold",
            "include_low_confidence", "clustering_enabled", "batch_size", 
            "timeout_minutes", "instructions"
        }
        assert set(passed_inputs.keys()) == expected_keys
        
        # Check values match inputs
        assert passed_inputs["job_name"] == "Integration Test"
        assert passed_inputs["storage_mode"] == "azure"
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
        from src.app import enter
        
        invalid_inputs = {
            "job_name": "",                    # Empty job name
            "storage_mode": "invalid_mode",    # Invalid storage mode
            "priority_threshold": 150.0,       # Invalid threshold
            "batch_size": 5,                   # Invalid batch size
            "timeout_minutes": 200             # Invalid timeout
        }
        
        with pytest.raises(InputsError) as exc_info:
            await enter(mock_request, invalid_inputs)
        
        error = exc_info.value
        assert error.has_errors()
        # Should have multiple field errors
    
    async def test_edge_case_values(self, mock_request):
        """Test edge case values for numeric inputs."""
        from src.app import enter
        
        # Test boundary values
        boundary_inputs = {
            "job_name": "abc",  # Minimum length (3 chars)
            "storage_mode": "local",
            "priority_threshold": 0.0,    # Minimum value
            "batch_size": 10,             # Minimum value
            "timeout_minutes": 5          # Minimum value
        }
        
        # Should not raise validation error
        with patch('src.app.Launch') as mock_launch:
            mock_launch.return_value = {"success": True}
            await enter(mock_request, boundary_inputs)
            assert mock_launch.called
        
        # Test maximum boundary values
        max_boundary_inputs = {
            "job_name": "Maximum boundary test",
            "storage_mode": "azure",
            "priority_threshold": 100.0,  # Maximum value
            "batch_size": 1000,           # Maximum value
            "timeout_minutes": 120        # Maximum value
        }
        
        with patch('src.app.Launch') as mock_launch:
            mock_launch.return_value = {"success": True}
            await enter(mock_request, max_boundary_inputs)
            assert mock_launch.called


class TestConfigurationIntegration:
    """Test integration with simplified configuration system."""
    
    @patch('src.config.settings')
    @patch('src.app.Launch')
    async def test_azure_mode_configuration(self, mock_launch, mock_settings, mock_request):
        """Test Azure mode uses correct configuration."""
        from src.app import enter
        
        # Setup mock settings for Azure mode
        mock_settings.USE_AZURE_STORAGE = True
        mock_settings.input_path = "jobs/test_job_123/input"
        mock_settings.context_path = "client/context.yaml"
        mock_settings.output_path = "jobs/test_job_123/output"
        
        mock_launch.return_value = {"success": True}
        
        inputs = {
            "job_name": "Azure Test",
            "storage_mode": "azure"
        }
        
        await enter(mock_request, inputs)
        
        # Verify Launch was called with Azure storage mode
        call_args = mock_launch.call_args
        passed_inputs = call_args[1]["inputs"]
        assert passed_inputs["storage_mode"] == "azure"
    
    @patch('src.config.settings')
    @patch('src.app.Launch')
    async def test_local_mode_configuration(self, mock_launch, mock_settings, mock_request):
        """Test local mode uses correct configuration."""
        from src.app import enter
        
        # Setup mock settings for local mode
        mock_settings.USE_AZURE_STORAGE = False
        mock_settings.input_path = "./data/input"
        mock_settings.context_path = "./data/context/client.yaml"
        mock_settings.output_path = "./data/output"
        
        mock_launch.return_value = {"success": True}
        
        inputs = {
            "job_name": "Local Test",
            "storage_mode": "local"
        }
        
        await enter(mock_request, inputs)
        
        # Verify Launch was called with local storage mode
        call_args = mock_launch.call_args
        passed_inputs = call_args[1]["inputs"]
        assert passed_inputs["storage_mode"] == "local"
    
    async def test_storage_mode_azure_validation(self, mock_request):
        """Test Azure storage mode validation."""
        from src.app import enter
        
        inputs = {
            "job_name": "Azure Test",
            "storage_mode": "azure"
        }
        
        with patch('src.app.Launch') as mock_launch:
            mock_launch.return_value = {"success": True}
            await enter(mock_request, inputs)
            
            call_args = mock_launch.call_args
            passed_inputs = call_args[1]["inputs"]
            assert passed_inputs["storage_mode"] == "azure"
    
    async def test_storage_mode_local_validation(self, mock_request):
        """Test local storage mode validation."""
        from src.app import enter
        
        inputs = {
            "job_name": "Local Test",
            "storage_mode": "local"
        }
        
        with patch('src.app.Launch') as mock_launch:
            mock_launch.return_value = {"success": True}
            await enter(mock_request, inputs)
            
            call_args = mock_launch.call_args
            passed_inputs = call_args[1]["inputs"]
            assert passed_inputs["storage_mode"] == "local"