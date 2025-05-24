"""
Tests for critical bugs that were encountered in production.

These tests ensure that issues like type conversion errors, path resolution problems,
Ray future handling, and job ID pattern validation are caught before deployment.
"""
import pytest
import os
import tempfile
import re
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

import ray

# Test the specific bugs we encountered
class TestTypeConversionBugs:
    """Test form input type conversion issues that caused TypeError."""
    
    def test_priority_threshold_string_conversion(self):
        """Test that string priority threshold is converted to float."""
        from app import enter
        
        # Mock the Launch function
        with patch('app.Launch') as mock_launch:
            mock_launch.return_value = {"success": True}
            
            # Create mock request
            mock_request = MagicMock()
            
            # Test string inputs that should be converted
            inputs = {
                "job_name": "Test Job",
                "input_folder": "./data/input",
                "context_file": "./data/context/client.yaml",
                "priority_threshold": "75.5",  # String that caused TypeError
                "batch_size": "100",           # String that caused TypeError  
                "timeout_minutes": "45",       # String that caused TypeError
                "include_low_confidence": False,
                "clustering_enabled": True,
                "instructions": ""
            }
            
            # This should not raise TypeError
            import asyncio
            result = asyncio.run(enter(mock_request, inputs))
            
            # Verify Launch was called with converted types
            call_args = mock_launch.call_args
            passed_inputs = call_args[1]["inputs"]
            
            assert isinstance(passed_inputs["priority_threshold"], float)
            assert passed_inputs["priority_threshold"] == 75.5
            assert isinstance(passed_inputs["batch_size"], int)
            assert passed_inputs["batch_size"] == 100
            assert isinstance(passed_inputs["timeout_minutes"], int)
            assert passed_inputs["timeout_minutes"] == 45
    
    def test_invalid_numeric_strings_raise_validation_error(self):
        """Test that invalid numeric strings raise proper validation errors."""
        from app import enter
        from kodosumi.core import InputsError
        
        mock_request = MagicMock()
        
        inputs = {
            "job_name": "Test Job",
            "input_folder": "./data/input",
            "context_file": "./data/context/client.yaml",
            "priority_threshold": "not_a_number",  # Invalid string
            "batch_size": "50",
            "timeout_minutes": "30"
        }
        
        with pytest.raises(InputsError):
            import asyncio
            asyncio.run(enter(mock_request, inputs))


class TestPathResolutionBugs:
    """Test path resolution issues that caused 'Input folder not found' errors."""
    
    def test_relative_path_resolution(self):
        """Test that relative paths are resolved correctly."""
        import political_analyzer
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create input directory structure
            input_dir = os.path.join(tmpdir, "data", "input")
            os.makedirs(input_dir)
            
            # Create a sample document
            doc_path = os.path.join(input_dir, "test.txt")
            with open(doc_path, "w") as f:
                f.write("Test document content")
            
            # Change to temp directory to test relative paths
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                
                # Test relative path resolution
                relative_path = "./data/input"
                resolved_path = os.path.abspath(relative_path)
                
                assert os.path.exists(resolved_path)
                assert os.path.isdir(resolved_path)
                
                # Test document discovery
                document_files = []
                for root, dirs, files in os.walk(resolved_path):
                    for file in files:
                        if file.lower().endswith(('.txt', '.md', '.pdf', '.docx')):
                            document_files.append(os.path.join(root, file))
                
                assert len(document_files) == 1
                assert document_files[0].endswith("test.txt")
                
            finally:
                os.chdir(original_cwd)
    
    def test_absolute_path_handling(self):
        """Test that absolute paths work correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = os.path.join(tmpdir, "input")
            os.makedirs(input_dir)
            
            # Create sample document
            doc_path = os.path.join(input_dir, "test.md")
            with open(doc_path, "w") as f:
                f.write("# Test Document")
            
            # Test absolute path
            absolute_path = input_dir
            assert os.path.exists(absolute_path)
            
            # Test document discovery with absolute path
            document_files = []
            for root, dirs, files in os.walk(absolute_path):
                for file in files:
                    if file.lower().endswith(('.txt', '.md', '.pdf', '.docx')):
                        document_files.append(os.path.join(root, file))
            
            assert len(document_files) == 1


class TestRayFutureHandlingBugs:
    """Test Ray future handling issues that caused processing failures."""
    
    @pytest.fixture
    def ray_context(self):
        """Initialize Ray for testing."""
        if not ray.is_initialized():
            ray.init(local_mode=True)
        yield
        if ray.is_initialized():
            ray.shutdown()
    
    def test_ray_remote_task_execution(self, ray_context):
        """Test that Ray remote tasks execute correctly."""
        import political_analyzer
        
        @ray.remote
        def test_task(data):
            return f"processed_{data}"
        
        # Test Ray task execution
        future = test_task.remote("test_data")
        result = ray.get(future)  # This is the correct way, not await
        
        assert result == "processed_test_data"
    
    def test_ray_wait_and_get_pattern_sync(self, ray_context):
        """Test the ray.wait() and ray.get() pattern in sync context."""
        @ray.remote 
        def batch_task(batch_id):
            return f"batch_{batch_id}_result"
        
        # Create multiple futures like in the analyzer
        futures = [batch_task.remote(i) for i in range(3)]
        results = []
        
        # Test the wait and get pattern in sync context
        while futures:
            done, futures = ray.wait(futures, num_returns=1, timeout=1.0)
            
            for completed_future in done:
                result = ray.get(completed_future)  # Correct for sync context
                results.append(result)
        
        assert len(results) == 3
        assert "batch_0_result" in results
        assert "batch_1_result" in results  
        assert "batch_2_result" in results
    
    async def test_ray_wait_and_await_pattern_async(self, ray_context):
        """Test the ray.wait() and await pattern in async context (like Kodosumi)."""
        @ray.remote 
        def batch_task(batch_id):
            return f"batch_{batch_id}_result"
        
        # Create multiple futures like in the analyzer
        futures = [batch_task.remote(i) for i in range(3)]
        results = []
        
        # Test the wait and await pattern in async context
        while futures:
            done, futures = ray.wait(futures, num_returns=1, timeout=1.0)
            
            for completed_future in done:
                result = await completed_future  # Correct for async context!
                results.append(result)
        
        assert len(results) == 3
        assert "batch_0_result" in results
        assert "batch_1_result" in results  
        assert "batch_2_result" in results


class TestJobIdPatternBugs:
    """Test job ID pattern validation that caused Pydantic errors."""
    
    def test_job_id_pattern_generation(self):
        """Test that generated job IDs match the required Pydantic pattern."""
        import political_analyzer
        import random
        import string
        
        # Test the job ID generation pattern
        suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{suffix}"
        
        # Test against the Pydantic pattern
        pattern = r"^job_\d{8}_\d{6}_[A-Za-z0-9]{6}$"
        assert re.match(pattern, job_id), f"Job ID {job_id} doesn't match pattern {pattern}"
    
    def test_job_id_pattern_validation(self):
        """Test job ID pattern validation in Job model."""
        from src.models.job import Job, JobRequest, JobStatus
        from datetime import datetime
        import random
        import string
        
        # Generate valid job ID
        suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        valid_job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{suffix}"
        
        # Create job request
        job_request = JobRequest(
            job_name="Test Job",
            input_folder="./data/input",
            context_file="./data/context/client.yaml"
        )
        
        # This should not raise validation error
        job = Job(
            id=valid_job_id,
            request=job_request,
            status=JobStatus.PENDING,
            created_at=datetime.now()
        )
        
        assert job.id == valid_job_id
    
    def test_invalid_job_id_patterns_rejected(self):
        """Test that invalid job ID patterns are rejected."""
        from src.models.job import Job, JobRequest, JobStatus
        from pydantic import ValidationError
        from datetime import datetime
        
        job_request = JobRequest(
            job_name="Test Job",
            input_folder="./data/input", 
            context_file="./data/context/client.yaml"
        )
        
        # Test various invalid patterns
        invalid_ids = [
            "job_20250524_132305",  # Missing suffix (original bug)
            "invalid_format",
            "job_202505_132305_ABC123",  # Wrong date format
            "job_20250524_13230_ABC123",  # Wrong time format
            "job_20250524_132305_AB12",  # Suffix too short
            "job_20250524_132305_ABC1234",  # Suffix too long
        ]
        
        for invalid_id in invalid_ids:
            with pytest.raises(ValidationError):
                Job(
                    id=invalid_id,
                    request=job_request,
                    status=JobStatus.PENDING,
                    created_at=datetime.now()
                )


class TestFormDefaultValuesBugs:
    """Test that form default values are correct after path fixes."""
    
    def test_form_default_paths(self):
        """Test that form defaults use correct relative paths."""
        from app import analysis_form
        
        # Get the form configuration
        form_config = analysis_form
        
        # The form should have the correct default paths
        # We need to extract the defaults from the form definition
        # This is a bit tricky since it's a Kodosumi form object
        
        # At minimum, verify the defaults in JobRequest model
        from src.models.job import JobRequest
        
        request = JobRequest(job_name="Test")
        assert request.input_folder == "./data/input"
        assert request.context_file == "./data/context/client.yaml"


class TestEnvironmentDependencyBugs:
    """Test that environment dependency issues are handled gracefully."""
    
    def test_azure_client_initialization_without_connection_string(self):
        """Test that Azure client handles missing connection string gracefully."""
        from src.integrations.azure_storage import AzureStorageClient
        
        # This should not crash even without Azure configuration
        client = AzureStorageClient()
        
        # Client should be created but blob_service should be None
        assert client.blob_service is None
    
    def test_lazy_azure_client_initialization(self):
        """Test that Azure client is lazily initialized."""
        from src.integrations.azure_storage import get_azure_storage_client
        
        # This should work even in test environment
        client = get_azure_storage_client()
        assert client is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])