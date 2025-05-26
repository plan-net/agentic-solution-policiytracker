from datetime import datetime

import pytest
from pydantic import ValidationError

from src.models.content import ProcessedContent
from src.models.job import Job, JobRequest, JobStatus
from src.models.scoring import ConfidenceLevel, PriorityLevel, ScoringResult


class TestJobModels:
    """Test job-related models."""

    def test_job_request_validation(self):
        """Test job request validation."""
        # Valid request
        request = JobRequest(
            job_name="test_job",
            input_folder="/data/input",
            context_file="/data/context/client.yaml",
        )
        assert request.job_name == "test_job"
        assert request.priority_threshold == 70.0  # Default value

        # Invalid job name (too long)
        with pytest.raises(ValidationError):
            JobRequest(job_name="x" * 101)

        # Path traversal attempt
        with pytest.raises(ValidationError):
            JobRequest(job_name="test", input_folder="../../../etc/passwd")

    def test_job_id_validation(self):
        """Test job ID format validation."""
        valid_request = JobRequest(job_name="test")

        # Valid job ID
        job = Job(
            id="job_20250523_120000_ABC123",
            request=valid_request,
            status=JobStatus.PENDING,
            created_at=datetime.now(),
        )
        assert job.id == "job_20250523_120000_ABC123"

        # Invalid job ID format
        with pytest.raises(ValidationError):
            Job(
                id="invalid_format",
                request=valid_request,
                status=JobStatus.PENDING,
                created_at=datetime.now(),
            )


class TestContentModels:
    """Test content-related models."""

    def test_processed_content_word_count(self, sample_document_metadata):
        """Test automatic word count calculation."""
        content = ProcessedContent(
            id="doc_001",
            raw_text="This is a test document with ten words exactly here.",
            metadata=sample_document_metadata,
            processing_timestamp=datetime.now(),
        )
        assert content.word_count == 10

    def test_processed_content_text_stripping(self, sample_document_metadata):
        """Test text stripping in validation."""
        content = ProcessedContent(
            id="doc_001",
            raw_text="  \n  Whitespace test  \n  ",
            metadata=sample_document_metadata,
            processing_timestamp=datetime.now(),
        )
        assert content.raw_text == "Whitespace test"


class TestScoringModels:
    """Test scoring-related models."""

    def test_confidence_level_calculation(self, sample_dimension_scores):
        """Test automatic confidence level calculation."""
        # High confidence
        result = ScoringResult(
            document_id="doc_001",
            master_score=80.0,
            dimension_scores=sample_dimension_scores,
            confidence_score=0.85,
            confidence_level="high",  # Will be overridden
            priority_level="high",
            scoring_timestamp=datetime.now(),
            processing_time_ms=100.0,
            overall_justification="Test",
            key_factors=[],
        )
        assert result.confidence_level == ConfidenceLevel.HIGH

        # Create new result with low confidence
        low_conf_result = ScoringResult(
            document_id="doc_001",
            master_score=80.0,
            dimension_scores=sample_dimension_scores,
            confidence_score=0.5,  # Low confidence
            scoring_timestamp=datetime.now(),
            processing_time_ms=100.0,
            overall_justification="Test",
            key_factors=[],
        )
        assert low_conf_result.confidence_level == ConfidenceLevel.LOW

    def test_priority_level_calculation(self, sample_dimension_scores):
        """Test automatic priority level calculation."""
        # Critical priority
        result = ScoringResult(
            document_id="doc_001",
            master_score=95.0,
            dimension_scores=sample_dimension_scores,
            confidence_score=0.8,
            scoring_timestamp=datetime.now(),
            processing_time_ms=100.0,
            overall_justification="Test",
            key_factors=[],
        )
        assert result.priority_level == PriorityLevel.CRITICAL

        # Low priority
        low_priority_result = ScoringResult(
            document_id="doc_002",
            master_score=30.0,
            dimension_scores=sample_dimension_scores,
            confidence_score=0.8,
            scoring_timestamp=datetime.now(),
            processing_time_ms=100.0,
            overall_justification="Test",
            key_factors=[],
        )
        assert low_priority_result.priority_level == PriorityLevel.LOW

    def test_dimension_score_validation(self):
        """Test dimension score validation."""
        from src.models.scoring import DimensionScore

        # Valid score
        dim_score = DimensionScore(
            dimension_name="test_dim",
            score=75.0,
            weight=0.25,
            justification="Test justification",
            evidence_snippets=["evidence 1", "evidence 2"],
        )
        assert dim_score.score == 75.0

        # Score out of range
        with pytest.raises(ValidationError):
            DimensionScore(
                dimension_name="test_dim",
                score=150.0,  # Invalid: > 100
                weight=0.25,
                justification="Test",
            )

        # Weight out of range
        with pytest.raises(ValidationError):
            DimensionScore(
                dimension_name="test_dim",
                score=75.0,
                weight=1.5,  # Invalid: > 1
                justification="Test",
            )
