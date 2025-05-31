"""Tests for data ingestion flow app."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from kodosumi.core import InputsError

from src.flows.data_ingestion.app import DataIngestionFlow, app, ingest_documents


class TestDataIngestionApp:
    """Test data ingestion app functionality."""

    def test_serve_api_initialized(self):
        """Test that ServeAPI app is properly initialized."""
        assert app is not None
        assert hasattr(app, 'enter')
        assert hasattr(app, 'get')

    def test_data_ingestion_form_structure(self):
        """Test that data ingestion form has expected structure."""
        from src.flows.data_ingestion.app import data_ingestion_form

        # Form should be a Model object with fields
        assert data_ingestion_form is not None
        # We can't easily test the internal structure without Kodosumi running,
        # but we can verify it's defined

    @pytest.mark.asyncio
    async def test_ingest_documents_missing_job_name(self):
        """Test validation when job name is missing."""
        mock_request = MagicMock()
        inputs = {}

        with pytest.raises(InputsError):
            await ingest_documents(mock_request, inputs)

    @pytest.mark.asyncio
    async def test_ingest_documents_short_job_name(self):
        """Test validation when job name is too short."""
        mock_request = MagicMock()
        inputs = {"job_name": "ab"}  # Too short

        with pytest.raises(InputsError):
            await ingest_documents(mock_request, inputs)

    @pytest.mark.asyncio
    async def test_ingest_documents_invalid_document_limit(self):
        """Test validation with invalid document limits."""
        mock_request = MagicMock()

        # Test non-numeric limit
        inputs = {"job_name": "Test Job", "document_limit": "not_a_number"}
        with pytest.raises(InputsError):
            await ingest_documents(mock_request, inputs)

        # Test negative limit
        inputs = {"job_name": "Test Job", "document_limit": -1}
        with pytest.raises(InputsError):
            await ingest_documents(mock_request, inputs)

        # Test limit too high
        inputs = {"job_name": "Test Job", "document_limit": 150}
        with pytest.raises(InputsError):
            await ingest_documents(mock_request, inputs)

    @pytest.mark.asyncio
    async def test_ingest_documents_nonexistent_source_path(self):
        """Test validation when source path doesn't exist."""
        mock_request = MagicMock()
        inputs = {
            "job_name": "Test Job",
            "document_limit": 10
        }

        # Mock the path to not exist
        with patch('pathlib.Path.exists', return_value=False):
            with pytest.raises(InputsError):
                await ingest_documents(mock_request, inputs)

    @pytest.mark.asyncio
    async def test_ingest_documents_no_documents_found(self, temp_directory):
        """Test validation when no documents are found."""
        mock_request = MagicMock()
        inputs = {
            "job_name": "Test Job",
            "document_limit": 10
        }

        # Create empty directory structure
        source_path = Path(temp_directory) / "policy"
        source_path.mkdir(parents=True)

        with patch('src.flows.data_ingestion.app.Path') as mock_path:
            mock_path_instance = MagicMock()
            mock_path.return_value = mock_path_instance
            # Mock empty glob results
            mock_path_instance.exists.return_value = True
            mock_path_instance.rglob.return_value = []

            with pytest.raises(InputsError):
                await ingest_documents(mock_request, inputs)

    @pytest.mark.asyncio
    async def test_ingest_documents_valid_input(self, temp_directory):
        """Test successful validation with valid inputs."""
        mock_request = MagicMock()
        inputs = {
            "job_name": "Valid Test Job",
            "document_limit": 5,
            "clear_data": True
        }

        # Create directory with test documents
        source_path = Path(temp_directory) / "policy"
        source_path.mkdir(parents=True)

        # Create test files
        (source_path / "test1.md").write_text("Test document 1")
        (source_path / "test2.txt").write_text("Test document 2")

        with patch('src.flows.data_ingestion.app.Path') as mock_path, \
             patch('src.flows.data_ingestion.app.Launch') as mock_launch:

            # Mock path operations
            mock_path_instance = MagicMock()
            mock_path.return_value = mock_path_instance
            mock_path_instance.exists.return_value = True

            # Mock glob to find our test files
            mock_glob_results = [Path("test1.md"), Path("test2.txt")]
            mock_path_instance.rglob.return_value = mock_glob_results

            # Mock Launch to return a response
            mock_launch.return_value = {"status": "launched"}

            result = await ingest_documents(mock_request, inputs)

            # Verify Launch was called with correct parameters
            mock_launch.assert_called_once()
            call_args = mock_launch.call_args

            assert call_args[0][0] == mock_request  # request parameter
            assert call_args[0][1] == "src.flows.data_ingestion.data_ingestion_analyzer:execute_ingestion"

            # Check inputs passed to Launch
            launch_inputs = call_args[1]['inputs']
            assert launch_inputs['job_name'] == "Valid Test Job"
            assert launch_inputs['document_limit'] == 5
            assert launch_inputs['clear_data'] is True
            assert launch_inputs['enable_communities'] is False
            assert launch_inputs['source_path'] == "data/input/policy/"

    @pytest.mark.asyncio
    async def test_ingest_documents_default_values(self, temp_directory):
        """Test that default values are handled correctly."""
        mock_request = MagicMock()
        inputs = {
            "job_name": "Test Job"
            # Missing document_limit and clear_data
        }

        # Create directory with test documents
        source_path = Path(temp_directory) / "policy"
        source_path.mkdir(parents=True)
        (source_path / "test.md").write_text("Test document")

        with patch('src.flows.data_ingestion.app.Path') as mock_path, \
             patch('src.flows.data_ingestion.app.Launch') as mock_launch:

            mock_path_instance = MagicMock()
            mock_path.return_value = mock_path_instance
            mock_path_instance.exists.return_value = True
            mock_path_instance.rglob.return_value = [Path("test.md")]

            mock_launch.return_value = {"status": "launched"}

            await ingest_documents(mock_request, inputs)

            # Check default values
            launch_inputs = mock_launch.call_args[1]['inputs']
            assert launch_inputs['document_limit'] == 10  # Default value
            assert launch_inputs['clear_data'] is False  # Default value

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check endpoint."""
        from src.flows.data_ingestion.app import health_check

        result = await health_check()

        assert result['status'] == 'healthy'
        assert result['service'] == 'political-monitoring-agent-flow1'
        assert result['version'] == '0.2.0'
        assert result['flow'] == 'data_ingestion'

    def test_data_ingestion_flow_class(self):
        """Test DataIngestionFlow deployment class."""
        # Test that the class is defined and can be referenced
        assert DataIngestionFlow is not None

        # Test that it's callable (Ray deployment classes are callable)
        assert callable(DataIngestionFlow)


class TestInputValidation:
    """Test input validation logic in detail."""

    @pytest.mark.asyncio
    async def test_job_name_validation_edge_cases(self):
        """Test edge cases for job name validation."""
        mock_request = MagicMock()

        # Exactly 3 characters (should pass)
        inputs = {"job_name": "abc", "document_limit": 5}

        with patch('src.flows.data_ingestion.app.Path') as mock_path:
            mock_path_instance = MagicMock()
            mock_path.return_value = mock_path_instance
            mock_path_instance.exists.return_value = True
            mock_path_instance.rglob.return_value = [Path("test.md")]

            with patch('src.flows.data_ingestion.app.Launch') as mock_launch:
                mock_launch.return_value = {"status": "launched"}

                # Should not raise error
                await ingest_documents(mock_request, inputs)
                assert mock_launch.called

    @pytest.mark.asyncio
    async def test_document_limit_boundary_values(self):
        """Test boundary values for document limit."""
        mock_request = MagicMock()

        with patch('src.flows.data_ingestion.app.Path') as mock_path:
            mock_path_instance = MagicMock()
            mock_path.return_value = mock_path_instance
            mock_path_instance.exists.return_value = True
            mock_path_instance.rglob.return_value = [Path("test.md")]

            with patch('src.flows.data_ingestion.app.Launch') as mock_launch:
                mock_launch.return_value = {"status": "launched"}

                # Test minimum valid value
                inputs = {"job_name": "Test Job", "document_limit": 1}
                await ingest_documents(mock_request, inputs)

                # Test maximum valid value
                inputs = {"job_name": "Test Job", "document_limit": 100}
                await ingest_documents(mock_request, inputs)

                assert mock_launch.call_count == 2

    @pytest.mark.asyncio
    async def test_clear_data_boolean_conversion(self):
        """Test that clear_data is properly converted to boolean."""
        mock_request = MagicMock()

        with patch('src.flows.data_ingestion.app.Path') as mock_path, \
             patch('src.flows.data_ingestion.app.Launch') as mock_launch:

            mock_path_instance = MagicMock()
            mock_path.return_value = mock_path_instance
            mock_path_instance.exists.return_value = True
            mock_path_instance.rglob.return_value = [Path("test.md")]
            mock_launch.return_value = {"status": "launched"}

            # Test various truthy values
            for value in [True, "true", "on", 1, "yes"]:
                inputs = {"job_name": "Test Job", "clear_data": value}
                await ingest_documents(mock_request, inputs)

                launch_inputs = mock_launch.call_args[1]['inputs']
                assert launch_inputs['clear_data'] is True

            # Test falsy values
            for value in [False, "", 0, None]:
                inputs = {"job_name": "Test Job", "clear_data": value}
                await ingest_documents(mock_request, inputs)

                launch_inputs = mock_launch.call_args[1]['inputs']
                assert launch_inputs['clear_data'] is False


class TestDocumentDiscovery:
    """Test document discovery logic."""

    @pytest.mark.asyncio
    async def test_document_patterns_detection(self, temp_directory):
        """Test that both .txt and .md files are detected."""
        mock_request = MagicMock()
        inputs = {"job_name": "Test Job"}

        # Create test directory structure
        source_path = Path(temp_directory) / "policy"
        source_path.mkdir(parents=True)

        # Create subdirectories with different file types
        subdir1 = source_path / "2024-01"
        subdir1.mkdir()
        (subdir1 / "doc1.md").write_text("Markdown doc")
        (subdir1 / "doc2.txt").write_text("Text doc")

        subdir2 = source_path / "2024-02"
        subdir2.mkdir()
        (subdir2 / "doc3.md").write_text("Another markdown")

        # Mock the actual path operations
        with patch('src.flows.data_ingestion.app.Path') as mock_path, \
             patch('src.flows.data_ingestion.app.Launch') as mock_launch:

            mock_path_instance = MagicMock()
            mock_path.return_value = mock_path_instance
            mock_path_instance.exists.return_value = True

            # Simulate finding files
            def mock_rglob(pattern):
                if pattern == "*.txt":
                    return [Path("doc2.txt")]
                elif pattern == "*.md":
                    return [Path("doc1.md"), Path("doc3.md")]
                return []

            mock_path_instance.rglob.side_effect = mock_rglob
            mock_launch.return_value = {"status": "launched"}

            await ingest_documents(mock_request, inputs)

            # Should have called rglob for both patterns
            assert mock_path_instance.rglob.call_count == 2
            mock_launch.assert_called_once()

    @pytest.mark.asyncio
    async def test_mixed_file_types_in_directory(self, temp_directory):
        """Test handling directory with mixed file types."""
        mock_request = MagicMock()
        inputs = {"job_name": "Test Job"}

        source_path = Path(temp_directory) / "policy"
        source_path.mkdir(parents=True)

        # Create files of different types
        (source_path / "document.md").write_text("Supported markdown")
        (source_path / "text.txt").write_text("Supported text")
        (source_path / "image.jpg").write_bytes(b"fake image")  # Unsupported
        (source_path / "video.mp4").write_bytes(b"fake video")  # Unsupported

        with patch('src.flows.data_ingestion.app.Path') as mock_path, \
             patch('src.flows.data_ingestion.app.Launch') as mock_launch:

            mock_path_instance = MagicMock()
            mock_path.return_value = mock_path_instance
            mock_path_instance.exists.return_value = True

            # Only return supported file types
            def mock_rglob(pattern):
                if pattern == "*.txt":
                    return [Path("text.txt")]
                elif pattern == "*.md":
                    return [Path("document.md")]
                return []

            mock_path_instance.rglob.side_effect = mock_rglob
            mock_launch.return_value = {"status": "launched"}

            await ingest_documents(mock_request, inputs)

            # Should succeed with supported files only
            mock_launch.assert_called_once()


class TestErrorHandling:
    """Test error handling and validation."""

    @pytest.mark.asyncio
    async def test_inputs_error_accumulation(self):
        """Test that multiple validation errors are accumulated."""
        mock_request = MagicMock()
        inputs = {
            "job_name": "",  # Missing
            "document_limit": "invalid"  # Invalid type
        }

        with patch('pathlib.Path.exists', return_value=False):  # Missing directory
            with pytest.raises(InputsError) as exc_info:
                await ingest_documents(mock_request, inputs)

            # Should have multiple errors
            error = exc_info.value
            assert error.has_errors()

    @pytest.mark.asyncio
    async def test_type_conversion_errors(self):
        """Test handling of type conversion errors."""
        mock_request = MagicMock()

        # Test various invalid document limit values
        invalid_limits = [
            "not_a_number",
            "12.5.7",  # Invalid float format
            None,
            [],
            {},
        ]

        for invalid_limit in invalid_limits:
            inputs = {
                "job_name": "Test Job",
                "document_limit": invalid_limit
            }

            with pytest.raises(InputsError):
                await ingest_documents(mock_request, inputs)
