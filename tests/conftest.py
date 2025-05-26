import os
import tempfile
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
import ray

from src.config import Settings
from src.models.content import DocumentMetadata, DocumentType, ProcessedContent
from src.models.job import Job, JobRequest, JobStatus
from src.models.scoring import DimensionScore, ScoringResult


@pytest.fixture
def sample_job_request():
    """Create a sample job request for testing."""
    return JobRequest(
        job_name="test_analysis",
        input_folder="/tmp/test_input",
        context_file="/tmp/test_context.yaml",
        priority_threshold=70.0,
        include_low_confidence=False,
        clustering_enabled=True,
    )


@pytest.fixture
def sample_job(sample_job_request):
    """Create a sample job for testing."""
    return Job(
        id="job_20250523_120000_TEST01",
        request=sample_job_request,
        status=JobStatus.PENDING,
        created_at=datetime.now(),
    )


@pytest.fixture
def sample_document_metadata():
    """Create sample document metadata."""
    return DocumentMetadata(
        source="test_document.pdf",
        type=DocumentType.PDF,
        file_path="/tmp/test_document.pdf",
        file_size_bytes=1024,
        created_at=datetime.now(),
        modified_at=datetime.now(),
        extraction_metadata={"pages": 5},
    )


@pytest.fixture
def sample_processed_content(sample_document_metadata):
    """Create sample processed content."""
    return ProcessedContent(
        id="doc_001",
        raw_text="This is a test document about regulatory compliance. The company must comply with GDPR regulations in the European Union.",
        metadata=sample_document_metadata,
        processing_timestamp=datetime.now(),
        word_count=20,
        language="en",
        sections=[{"title": "Introduction", "content": "Test content"}],
        extraction_errors=[],
    )


@pytest.fixture
def sample_dimension_scores():
    """Create sample dimension scores."""
    return {
        "direct_impact": DimensionScore(
            dimension_name="direct_impact",
            score=85.0,
            weight=0.40,
            justification="High regulatory impact detected",
            evidence_snippets=["must comply with GDPR"],
        ),
        "industry_relevance": DimensionScore(
            dimension_name="industry_relevance",
            score=60.0,
            weight=0.25,
            justification="General business relevance",
            evidence_snippets=["company regulations"],
        ),
    }


@pytest.fixture
def sample_scoring_result(sample_dimension_scores):
    """Create sample scoring result."""
    return ScoringResult(
        document_id="doc_001",
        master_score=75.5,
        dimension_scores=sample_dimension_scores,
        confidence_score=0.85,
        confidence_level="high",
        priority_level="high",
        topic_clusters=["compliance", "regulatory"],
        scoring_timestamp=datetime.now(),
        processing_time_ms=150.0,
        overall_justification="High regulatory compliance document",
        key_factors=["Direct regulatory requirements", "Company obligations"],
    )


@pytest.fixture
def sample_context():
    """Create sample context data."""
    return {
        "company_terms": ["testcorp", "test company"],
        "core_industries": ["technology", "software"],
        "primary_markets": ["eu", "germany", "france"],
        "strategic_themes": ["digital transformation", "compliance"],
    }


@pytest.fixture
def temp_directory():
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_files(temp_directory):
    """Create sample files for testing."""
    files = {}

    # Create sample text file
    txt_path = os.path.join(temp_directory, "sample.txt")
    with open(txt_path, "w") as f:
        f.write("This is a sample text document for testing.")
    files["txt"] = txt_path

    # Create sample markdown file
    md_path = os.path.join(temp_directory, "sample.md")
    with open(md_path, "w") as f:
        f.write("# Sample Document\n\nThis is a sample markdown document.")
    files["md"] = md_path

    return files


# Kodosumi-specific fixtures


@pytest.fixture(scope="session", autouse=True)
def setup_ray_for_tests():
    """Setup Ray for testing session."""
    if not ray.is_initialized():
        ray.init(local_mode=True, ignore_reinit_error=True)
    yield
    if ray.is_initialized():
        ray.shutdown()


@pytest.fixture
def local_settings():
    """Settings for local development/testing."""
    return Settings(
        USE_AZURE_STORAGE=False,
        AZURE_STORAGE_CONNECTION_STRING="",
        RAY_ADDRESS="auto",
        RAY_NUM_CPUS=2,
        LLM_ENABLED=False,  # Disable for testing
        DEFAULT_INPUT_FOLDER="/tmp/test_input",
        DEFAULT_OUTPUT_FOLDER="/tmp/test_output",
        DEFAULT_CONTEXT_FOLDER="/tmp/test_context",
    )


@pytest.fixture
def mock_azure_settings():
    """Settings for Azure Storage testing."""
    return Settings(
        USE_AZURE_STORAGE=True,
        AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=test;AccountKey=test==;EndpointSuffix=core.windows.net",
        RAY_ADDRESS="auto",
        RAY_NUM_CPUS=2,
        LLM_ENABLED=False,
        DEFAULT_INPUT_FOLDER="/data/input",
        DEFAULT_OUTPUT_FOLDER="/data/output",
        DEFAULT_CONTEXT_FOLDER="/data/context",
    )


@pytest.fixture
def mock_azure_storage_client():
    """Mock Azure Storage client for testing."""
    client = MagicMock()

    # Mock common methods
    client.blob_exists = AsyncMock(return_value=True)
    client.upload_blob = AsyncMock(return_value=True)
    client.download_blob = AsyncMock(return_value=b"test content")
    client.list_blobs = MagicMock(return_value=[])
    client.delete_blob = AsyncMock(return_value=True)
    client.upload_json = AsyncMock(return_value=True)
    client.download_json = AsyncMock(return_value={"test": "data"})

    return client


@pytest.fixture
def mock_kodosumi_tracer():
    """Mock Kodosumi tracer for testing."""
    tracer = AsyncMock()
    tracer.markdown = AsyncMock()
    return tracer


# Note: Ray tasks fixture removed as Ray task infrastructure was removed from codebase
# The current implementation uses LangGraph sequential processing instead


@pytest.fixture
def mock_political_analyzer_dependencies():
    """Mock all dependencies for political_analyzer module."""
    from unittest.mock import patch

    with patch("political_analyzer.ContentProcessor") as mock_processor:
        with patch("political_analyzer.RelevanceEngine") as mock_engine:
            with patch("political_analyzer.Aggregator") as mock_aggregator:
                with patch("political_analyzer.ReportGenerator") as mock_generator:
                    yield {
                        "processor": mock_processor,
                        "engine": mock_engine,
                        "aggregator": mock_aggregator,
                        "generator": mock_generator,
                    }


@pytest.fixture
def mock_ray():
    """Mock Ray functionality for testing."""

    class MockRayTask:
        def __init__(self, result):
            self._result = result

        def remote(self, *args, **kwargs):
            return self

        async def get(self):
            return self._result

    return MockRayTask


@pytest.fixture
def mock_azure_storage_client():
    """Mock Azure Storage client for testing."""
    mock_client = AsyncMock()

    # Mock blob data for testing
    mock_blob_data = {
        "test-blob.txt": b"This is test blob content",
        "jobs/test_job/input/doc1.txt": b"Test document 1 content",
        "jobs/test_job/input/doc2.md": b"# Test document 2\nMarkdown content",
        "contexts/test_context.yaml": b"""
company_terms:
  - test-company
core_industries:
  - technology
primary_markets:
  - US
strategic_themes:
  - innovation
""",
        "cache/processed/test_cache.json": b'{"id": "doc_001", "content": "cached"}',
        "reports/jobs/test_job/reports/test_report.md": b"# Test Report\nReport content",
    }

    # Mock download_blob
    async def mock_download_blob(container_type, blob_name):
        return mock_blob_data.get(blob_name)

    mock_client.download_blob = mock_download_blob

    # Mock upload_blob
    async def mock_upload_blob(container_type, blob_name, data, metadata=None, overwrite=True):
        mock_blob_data[blob_name] = data if isinstance(data, bytes) else data.encode()
        return True

    mock_client.upload_blob = mock_upload_blob

    # Mock upload_json
    async def mock_upload_json(container_type, blob_name, data, metadata=None):
        import json

        json_data = json.dumps(data).encode()
        mock_blob_data[blob_name] = json_data
        return True

    mock_client.upload_json = mock_upload_json

    # Mock download_json
    async def mock_download_json(container_type, blob_name):
        import json

        blob_data = mock_blob_data.get(blob_name)
        if blob_data:
            return json.loads(blob_data.decode())
        return None

    mock_client.download_json = mock_download_json

    # Mock list_blobs
    async def mock_list_blobs(container_type, prefix=""):
        mock_blob = MagicMock()
        blobs = []
        for blob_name in mock_blob_data.keys():
            if blob_name.startswith(prefix):
                mock_blob.name = blob_name
                mock_blob.size = len(mock_blob_data[blob_name])
                mock_blob.last_modified = datetime.now()
                blobs.append(mock_blob)
        return blobs

    mock_client.list_blobs = mock_list_blobs

    # Mock get_blob_properties
    async def mock_get_blob_properties(container_type, blob_name):
        blob_data = mock_blob_data.get(blob_name)
        if blob_data:
            return {
                "size": len(blob_data),
                "last_modified": datetime.now(),
                "content_type": "application/octet-stream",
            }
        return None

    mock_client.get_blob_properties = mock_get_blob_properties

    # Mock delete_blob
    async def mock_delete_blob(container_type, blob_name):
        if blob_name in mock_blob_data:
            del mock_blob_data[blob_name]
            return True
        return False

    mock_client.delete_blob = mock_delete_blob

    return mock_client


@pytest.fixture
def mock_azure_settings():
    """Mock Azure Storage settings for testing."""
    from unittest.mock import patch

    with patch("src.config.settings") as mock_settings:
        mock_settings.USE_AZURE_STORAGE = True
        mock_settings.AZURE_STORAGE_CONNECTION_STRING = "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://localhost:10000/devstoreaccount1"
        mock_settings.AZURE_STORAGE_ACCOUNT_NAME = "devstoreaccount1"
        mock_settings.AZURE_STORAGE_CONTAINER_NAME = "test-container"
        yield mock_settings


@pytest.fixture
def local_settings():
    """Mock local storage settings for testing."""
    from unittest.mock import patch

    with patch("src.config.settings") as mock_settings:
        mock_settings.USE_AZURE_STORAGE = False
        mock_settings.AZURE_STORAGE_CONNECTION_STRING = None
        mock_settings.DEFAULT_INPUT_FOLDER = "/tmp/test_input"
        mock_settings.DEFAULT_OUTPUT_FOLDER = "/tmp/test_output"
        yield mock_settings


@pytest.fixture
def azure_blob_metadata():
    """Sample Azure blob metadata for testing."""
    return {
        "job_id": "test_job_123",
        "document_type": "txt",
        "uploaded_at": datetime.now().isoformat(),
        "file_size": "1024",
        "processing_status": "pending",
    }


@pytest.fixture
def sample_azure_context_file():
    """Sample Azure context file content."""
    return {
        "company_terms": ["azure-test-corp", "test company"],
        "core_industries": ["cloud", "technology"],
        "primary_markets": ["global", "azure"],
        "strategic_themes": ["cloud transformation", "digital services"],
    }
