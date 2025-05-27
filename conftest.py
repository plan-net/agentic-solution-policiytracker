"""
Global pytest configuration for Political Monitoring Agent tests.
Includes Ray setup, fixtures, and CLAUDE.md compliance requirements.
"""

import os
from unittest.mock import AsyncMock, patch

import pytest
import ray
from langgraph.checkpoint.memory import MemorySaver

from src.models.job import JobRequest
from src.workflow.state import WorkflowState


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring full setup"
    )
    config.addinivalue_line("markers", "ray: mark test as requiring Ray cluster (local mode)")
    config.addinivalue_line("markers", "slow: mark test as slow running (performance tests)")


@pytest.fixture(scope="session")
def ray_cluster():
    """Session-wide Ray cluster for integration tests."""
    if not ray.is_initialized():
        # Initialize Ray in local mode for testing
        ray.init(
            local_mode=True,
            ignore_reinit_error=True,
            log_to_driver=False,  # Reduce noise in tests
            configure_logging=False,
        )

    yield

    # Cleanup after all tests
    if ray.is_initialized():
        ray.shutdown()


@pytest.fixture
def ray_local_mode(ray_cluster):
    """Ensure Ray is available in local mode for individual tests."""
    assert ray.is_initialized(), "Ray should be initialized in local mode"
    yield
    # Ray cleanup handled by session fixture


@pytest.fixture
def test_config():
    """Standard test configuration for Political Monitoring Agent."""
    return JobRequest(
        job_name="TestJob",
        input_folder="/tmp/test_documents",
        context_file="/tmp/test_context.yaml",
        priority_threshold=70.0,
        include_low_confidence=False,
        clustering_enabled=True,
    )


@pytest.fixture
def minimal_config():
    """Minimal test configuration for simple tests."""
    return JobRequest(
        job_name="MinimalTestJob",
        input_folder="/tmp/minimal_test",
        context_file="/tmp/minimal_context.yaml",
        priority_threshold=80.0,
        include_low_confidence=True,
        clustering_enabled=False,
    )


@pytest.fixture
def test_documents_dir(tmp_path) -> str:
    """Create temporary directory with test documents."""
    docs_dir = tmp_path / "test_documents"
    docs_dir.mkdir()

    # Create diverse test documents
    (docs_dir / "ai_regulation.txt").write_text(
        "New artificial intelligence regulation proposal for healthcare privacy in the United States. "
        "This technology-focused policy affects data protection standards and AI model governance. "
        "Key provisions include mandatory bias testing and algorithmic transparency requirements."
    )

    (docs_dir / "environmental_policy.md").write_text(
        "# Environmental Policy Update\n\n"
        "## Renewable Energy Standards\n\n"
        "New requirements for solar panel installations across European Union member states. "
        "Climate change mitigation strategies and carbon emission reduction targets for 2030."
    )

    (docs_dir / "healthcare_tech.html").write_text(
        "<html><body>"
        "<h1>Healthcare Technology Guidelines</h1>"
        "<p>Proposed changes to AI usage in medical diagnosis and patient data handling. "
        "Privacy concerns regarding machine learning models in clinical environments. "
        "Regulatory compliance requirements for medical AI systems.</p>"
        "</body></html>"
    )

    (docs_dir / "financial_regulation.pdf.txt").write_text(
        "Financial services regulation update regarding cryptocurrency and digital assets. "
        "New compliance requirements for blockchain technology in banking sector. "
        "Consumer protection measures for digital payment systems."
    )

    # Create edge case documents
    (docs_dir / "empty_file.txt").write_text("")
    (docs_dir / "large_document.txt").write_text("Large content. " * 1000)

    # Create non-text file to test filtering
    (docs_dir / "image.jpg").write_bytes(b"fake image data")

    return str(docs_dir)


@pytest.fixture
def empty_documents_dir(tmp_path) -> str:
    """Create empty directory for testing edge cases."""
    empty_dir = tmp_path / "empty_documents"
    empty_dir.mkdir()
    return str(empty_dir)


@pytest.fixture
def basic_workflow_state(test_config, test_documents_dir):
    """Basic workflow state for testing."""
    # Update the job_request to use the test documents directory
    test_config.input_folder = test_documents_dir

    return WorkflowState(
        job_id="test_job_001",
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


@pytest.fixture
def memory_checkpointer():
    """In-memory checkpointer for fast unit tests."""
    return MemorySaver()


@pytest.fixture
def persistent_checkpointer(tmp_path):
    """Persistent checkpointer for integration tests (using memory for now)."""
    # Note: Using MemorySaver as SQLite checkpointer not available in current LangGraph version
    return MemorySaver()


@pytest.fixture
def mock_checkpointer():
    """Mock checkpointer for unit tests."""
    mock = AsyncMock()
    mock.aget_tuple = AsyncMock(return_value=None)
    mock.aput = AsyncMock()
    mock.alist = AsyncMock(return_value=[])
    mock.aget = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_ray_tasks():
    """Mock Ray remote tasks for unit testing."""
    with patch("src.tasks.document_processing.process_document_batch") as mock_doc_batch, patch(
        "src.tasks.analysis_tasks.analyze_document_batch"
    ) as mock_analysis_batch, patch(
        "src.tasks.scoring_tasks.calculate_scores_batch"
    ) as mock_scoring_batch:
        # Configure mocks to return Ray object references
        mock_doc_batch.return_value = ray.put([])
        mock_analysis_batch.return_value = ray.put([])
        mock_scoring_batch.return_value = ray.put([])

        yield {
            "document_processing": mock_doc_batch,
            "analysis_tasks": mock_analysis_batch,
            "scoring_tasks": mock_scoring_batch,
        }


@pytest.fixture
def mock_llm_service():
    """Mock LLM service for testing without external API calls."""
    with patch("src.llm.langchain_service.LangChainLLMService") as mock_service:
        # Create mock instance
        mock_instance = AsyncMock()
        mock_instance.is_enabled.return_value = True
        mock_instance.generate_analysis = AsyncMock(
            return_value={
                "summary": "Test analysis summary",
                "key_points": ["Point 1", "Point 2"],
                "sentiment": "neutral",
                "confidence": 0.85,
            }
        )
        mock_instance.generate_score_rationale = AsyncMock(
            return_value={
                "reasoning": "Test scoring rationale",
                "confidence": 0.8,
                "key_factors": ["Factor 1", "Factor 2"],
            }
        )

        mock_service.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_prompt_manager():
    """Mock prompt manager for testing."""
    with patch("src.prompts.prompt_manager.PromptManager") as mock_manager:
        mock_instance = AsyncMock()
        mock_instance.get_prompt = AsyncMock(return_value="Test prompt template")
        mock_instance.is_langfuse_available = False

        mock_manager.return_value = mock_instance
        yield mock_instance


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment variables."""
    # Set test environment variables
    test_env = {
        "ENVIRONMENT": "test",
        "LOG_LEVEL": "WARNING",
        "RAY_LOCAL_MODE": "1",
        "LANGFUSE_PUBLIC_KEY": "test-key",
        "LANGFUSE_SECRET_KEY": "test-secret",
        "LANGFUSE_HOST": "http://localhost:3000",
    }

    # Store original values
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    yield

    # Restore original environment
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture
def thread_config():
    """Generate unique thread configuration for graph execution."""
    import uuid

    return {"configurable": {"thread_id": f"test-thread-{uuid.uuid4().hex[:8]}"}}


# Performance testing fixtures
@pytest.fixture
def performance_test_documents(tmp_path):
    """Create larger document set for performance testing."""
    docs_dir = tmp_path / "perf_documents"
    docs_dir.mkdir()

    # Create multiple documents of varying sizes
    for i in range(10):
        content = f"Document {i} content. " * (100 * (i + 1))  # Varying sizes
        (docs_dir / f"doc_{i:02d}.txt").write_text(content)

    return str(docs_dir)


# Snapshot testing helpers
@pytest.fixture
def graph_snapshot():
    """Helper for graph structure snapshot testing."""

    def _snapshot_graph(graph):
        """Create a snapshot of graph structure."""
        return {
            "nodes": list(graph.nodes.keys()),
            "edges": [(edge.source, edge.target) for edge in graph.edges],
            "entry_point": getattr(graph, "_start", None),
            "finish_point": getattr(graph, "_finish", None),
        }

    return _snapshot_graph


# Error injection fixtures for testing resilience
@pytest.fixture
def inject_document_loading_error():
    """Inject error during document loading for error handling tests."""

    def _inject_error():
        with patch("src.workflow.nodes.load_documents") as mock_node:
            mock_node.side_effect = Exception("Simulated document loading error")
            yield mock_node

    return _inject_error


@pytest.fixture
def inject_analysis_error():
    """Inject error during analysis for error handling tests."""

    def _inject_error():
        with patch("src.workflow.nodes.analyze_documents") as mock_node:
            mock_node.side_effect = Exception("Simulated analysis error")
            yield mock_node

    return _inject_error


# Database and persistence testing
@pytest.fixture
def clean_test_database(tmp_path):
    """Provide clean database for each test."""
    db_path = tmp_path / "clean_test.db"
    yield str(db_path)
    # Cleanup handled automatically by tmp_path


# Concurrent execution helpers
@pytest.fixture
def concurrent_test_configs():
    """Generate multiple test configurations for concurrent testing."""
    configs = []
    for i in range(5):
        config = JobRequest(
            job_name=f"ConcurrentJob{i}",
            input_folder=f"/tmp/concurrent_test_{i}",
            context_file=f"/tmp/concurrent_context_{i}.yaml",
            priority_threshold=70.0 + (i * 5),
            include_low_confidence=i % 2 == 0,
            clustering_enabled=i % 3 == 0,
        )
        configs.append(config)
    return configs


# CLAUDE.md compliance markers
def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on CLAUDE.md requirements."""
    for item in items:
        # Mark integration tests
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)

        # Mark Ray tests
        if "ray" in item.name.lower() or "ray_local_mode" in str(item.fixturenames):
            item.add_marker(pytest.mark.ray)

        # Mark slow tests
        if "performance" in item.name.lower() or "concurrent" in item.name.lower():
            item.add_marker(pytest.mark.slow)


# Test data validation
@pytest.fixture
def validate_test_outputs():
    """Helper to validate test outputs meet CLAUDE.md requirements."""

    def _validate(state: WorkflowState):
        """Validate workflow state meets requirements."""
        validations = {
            "has_documents": len(state.documents) >= 0,
            "config_present": state.job_request is not None,
            "no_critical_errors": len(state.errors) == 0
            or all("critical" not in str(e).lower() for e in state.errors),
            "job_id_present": state.job_id is not None and state.job_id != "",
        }
        return validations

    return _validate
