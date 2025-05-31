"""Tests for utility exception classes."""

import pytest

from src.utils.exceptions import (
    BatchProcessingError,
    ConfigurationError,
    DocumentProcessingError,
    ScoringError,
    WorkflowError,
)


class TestDocumentProcessingError:
    """Test DocumentProcessingError exception."""

    def test_basic_initialization(self):
        """Test basic exception initialization."""
        error = DocumentProcessingError("/path/to/doc.pdf", "Invalid format")

        assert error.file_path == "/path/to/doc.pdf"
        assert error.message == "Invalid format"
        assert str(error) == "Document processing failed for /path/to/doc.pdf: Invalid format"

    def test_inheritance_from_exception(self):
        """Test that it inherits from Exception."""
        error = DocumentProcessingError("/path/to/doc.pdf", "Test error")
        assert isinstance(error, Exception)

    def test_can_be_raised_and_caught(self):
        """Test that exception can be raised and caught."""
        with pytest.raises(DocumentProcessingError) as exc_info:
            raise DocumentProcessingError("/test/path.pdf", "Parsing failed")

        assert exc_info.value.file_path == "/test/path.pdf"
        assert exc_info.value.message == "Parsing failed"


class TestScoringError:
    """Test ScoringError exception."""

    def test_basic_initialization(self):
        """Test basic exception initialization."""
        error = ScoringError("doc_123", "relevance", "Missing metadata")

        assert error.document_id == "doc_123"
        assert error.dimension == "relevance"
        assert error.message == "Missing metadata"
        assert str(error) == "Scoring failed for doc_123 in dimension relevance: Missing metadata"

    def test_inheritance_from_exception(self):
        """Test that it inherits from Exception."""
        error = ScoringError("doc_456", "quality", "Test error")
        assert isinstance(error, Exception)

    def test_can_be_raised_and_caught(self):
        """Test that exception can be raised and caught."""
        with pytest.raises(ScoringError) as exc_info:
            raise ScoringError("doc_789", "confidence", "Algorithm failure")

        assert exc_info.value.document_id == "doc_789"
        assert exc_info.value.dimension == "confidence"
        assert exc_info.value.message == "Algorithm failure"


class TestWorkflowError:
    """Test WorkflowError exception."""

    def test_basic_initialization(self):
        """Test basic exception initialization."""
        error = WorkflowError("job_456", "analysis_node", "Timeout occurred")

        assert error.job_id == "job_456"
        assert error.node_name == "analysis_node"
        assert error.message == "Timeout occurred"
        assert str(error) == "Workflow error in analysis_node for job job_456: Timeout occurred"

    def test_inheritance_from_exception(self):
        """Test that it inherits from Exception."""
        error = WorkflowError("job_123", "scoring_node", "Test error")
        assert isinstance(error, Exception)

    def test_can_be_raised_and_caught(self):
        """Test that exception can be raised and caught."""
        with pytest.raises(WorkflowError) as exc_info:
            raise WorkflowError("job_999", "synthesis_node", "Memory exhausted")

        assert exc_info.value.job_id == "job_999"
        assert exc_info.value.node_name == "synthesis_node"
        assert exc_info.value.message == "Memory exhausted"


class TestConfigurationError:
    """Test ConfigurationError exception."""

    def test_basic_initialization(self):
        """Test basic exception initialization."""
        error = ConfigurationError("api_key", "Missing required value")

        assert error.setting_name == "api_key"
        assert error.message == "Missing required value"
        assert str(error) == "Configuration error for api_key: Missing required value"

    def test_inheritance_from_exception(self):
        """Test that it inherits from Exception."""
        error = ConfigurationError("database_url", "Test error")
        assert isinstance(error, Exception)

    def test_can_be_raised_and_caught(self):
        """Test that exception can be raised and caught."""
        with pytest.raises(ConfigurationError) as exc_info:
            raise ConfigurationError("timeout", "Value must be positive")

        assert exc_info.value.setting_name == "timeout"
        assert exc_info.value.message == "Value must be positive"


class TestBatchProcessingError:
    """Test BatchProcessingError exception."""

    def test_basic_initialization(self):
        """Test basic exception initialization."""
        error = BatchProcessingError(3, 10, "Network failures")

        assert error.failed_count == 3
        assert error.total_count == 10
        assert error.message == "Network failures"
        assert str(error) == "Batch processing failed: 3/10 documents failed - Network failures"

    def test_inheritance_from_exception(self):
        """Test that it inherits from Exception."""
        error = BatchProcessingError(1, 5, "Test error")
        assert isinstance(error, Exception)

    def test_can_be_raised_and_caught(self):
        """Test that exception can be raised and caught."""
        with pytest.raises(BatchProcessingError) as exc_info:
            raise BatchProcessingError(7, 20, "Parser errors")

        assert exc_info.value.failed_count == 7
        assert exc_info.value.total_count == 20
        assert exc_info.value.message == "Parser errors"

    def test_zero_failures(self):
        """Test with zero failures."""
        error = BatchProcessingError(0, 10, "Actually succeeded")

        assert error.failed_count == 0
        assert error.total_count == 10
        assert str(error) == "Batch processing failed: 0/10 documents failed - Actually succeeded"

    def test_all_failures(self):
        """Test with all failures."""
        error = BatchProcessingError(5, 5, "Complete failure")

        assert error.failed_count == 5
        assert error.total_count == 5
        assert str(error) == "Batch processing failed: 5/5 documents failed - Complete failure"


class TestExceptionAttributeAccess:
    """Test that exceptions properly store and expose attributes."""

    def test_document_processing_error_attributes(self):
        """Test DocumentProcessingError attributes are accessible."""
        error = DocumentProcessingError("/some/path.doc", "Corrupt file")

        # Test attributes exist and are correct type
        assert isinstance(error.file_path, str)
        assert isinstance(error.message, str)

        # Test attribute values
        assert error.file_path == "/some/path.doc"
        assert error.message == "Corrupt file"

    def test_scoring_error_attributes(self):
        """Test ScoringError attributes are accessible."""
        error = ScoringError("doc_xyz", "priority", "No keywords found")

        assert isinstance(error.document_id, str)
        assert isinstance(error.dimension, str)
        assert isinstance(error.message, str)

        assert error.document_id == "doc_xyz"
        assert error.dimension == "priority"
        assert error.message == "No keywords found"

    def test_workflow_error_attributes(self):
        """Test WorkflowError attributes are accessible."""
        error = WorkflowError("job_abc", "validation_node", "Schema mismatch")

        assert isinstance(error.job_id, str)
        assert isinstance(error.node_name, str)
        assert isinstance(error.message, str)

        assert error.job_id == "job_abc"
        assert error.node_name == "validation_node"
        assert error.message == "Schema mismatch"

    def test_configuration_error_attributes(self):
        """Test ConfigurationError attributes are accessible."""
        error = ConfigurationError("log_level", "Invalid level specified")

        assert isinstance(error.setting_name, str)
        assert isinstance(error.message, str)

        assert error.setting_name == "log_level"
        assert error.message == "Invalid level specified"

    def test_batch_processing_error_attributes(self):
        """Test BatchProcessingError attributes are accessible."""
        error = BatchProcessingError(2, 8, "Timeout issues")

        assert isinstance(error.failed_count, int)
        assert isinstance(error.total_count, int)
        assert isinstance(error.message, str)

        assert error.failed_count == 2
        assert error.total_count == 8
        assert error.message == "Timeout issues"
