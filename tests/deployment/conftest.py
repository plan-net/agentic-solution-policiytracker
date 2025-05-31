"""Deployment-specific test fixtures and configuration."""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any

import aiohttp
import pytest
from graphiti_core import Graphiti

from src.config import settings

logger = logging.getLogger(__name__)


# Deployment test configuration
class DeploymentConfig:
    """Configuration for deployment tests."""

    # Ray Serve configuration
    RAY_ADDRESS = "localhost:8001"
    HEALTH_TIMEOUT = 30
    RESPONSE_TIMEOUT = 60
    CONCURRENT_USERS = 3

    # Testing configuration
    OPENAI_MODEL = "gpt-4o-mini"
    MAX_RETRIES = 3
    QUALITY_THRESHOLD = 0.8
    PERFORMANCE_THRESHOLD = 45  # seconds

    # Service endpoints
    CHAT_ENDPOINT = "http://localhost:8001/chat/v1/chat/completions"
    HEALTH_ENDPOINT = "http://localhost:8001/chat/health"
    MODELS_ENDPOINT = "http://localhost:8001/chat/v1/models"


@pytest.fixture(scope="session")
def deployment_config():
    """Provide deployment configuration."""
    return DeploymentConfig()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def ray_serve_deployment(deployment_config):
    """Use existing Ray Serve deployment for testing."""

    # We assume Ray and Ray Serve are already running from `just start`
    # Just wait for deployment to be ready
    await _wait_for_deployment_ready(deployment_config)

    # Return a mock handle since we're using existing deployment
    yield "existing-deployment"

    # No cleanup needed - let the user manage the deployment lifecycle


async def _wait_for_deployment_ready(config: DeploymentConfig, max_attempts: int = 30):
    """Wait for the deployment to be ready."""

    for attempt in range(max_attempts):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    config.HEALTH_ENDPOINT, timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("status") == "healthy":
                            logger.info(f"Deployment ready after {attempt + 1} attempts")
                            return
        except Exception as e:
            logger.debug(f"Attempt {attempt + 1}: {e}")

        await asyncio.sleep(1)

    raise TimeoutError(f"Deployment not ready after {max_attempts} attempts")


@pytest.fixture
async def http_client():
    """Provide HTTP client for API testing."""

    async with aiohttp.ClientSession() as session:
        yield session


@pytest.fixture
async def graphiti_client():
    """Provide Graphiti client with test data."""

    client = Graphiti(settings.NEO4J_URI, settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)

    # Initialize indices and constraints
    await client.build_indices_and_constraints()

    # Ensure some test data exists
    await _ensure_test_data(client)

    yield client

    # Cleanup could go here if needed


async def _ensure_test_data(client: Graphiti):
    """Ensure basic test data exists in the knowledge graph."""

    # Add a simple test episode if graph is empty
    try:
        test_content = """
        The European Union's General Data Protection Regulation (GDPR) is a comprehensive
        data protection law that came into effect on May 25, 2018. It requires companies
        like Meta and Google to implement strict data protection measures when processing
        personal data of EU citizens.
        """

        await client.add_episode(
            name="test_gdpr_episode",
            episode_body=test_content,
            source="text",
            source_description="Test data for deployment tests",
        )

        logger.info("Test data added to knowledge graph")

    except Exception as e:
        logger.warning(f"Could not add test data: {e}")


@pytest.fixture
def sample_queries():
    """Provide sample test queries for different scenarios."""

    return {
        "basic_information": [
            "What is GDPR?",
            "Tell me about the EU AI Act",
            "What is the Digital Services Act?",
        ],
        "relationship_analysis": [
            "How does GDPR affect Meta?",
            "What is the relationship between EU AI Act and US tech companies?",
            "How do privacy regulations impact Google's business?",
        ],
        "temporal_analysis": [
            "How has EU data protection evolved since GDPR?",
            "What regulatory changes happened in 2024?",
            "Show me the timeline of AI regulation in Europe",
        ],
        "complex_analysis": [
            "Analyze the impact of EU digital regulations on US tech companies operating in Europe",
            "How do different European privacy laws interact with each other?",
            "What are the compliance requirements for AI companies under EU regulation?",
        ],
        "edge_cases": [
            "",  # Empty query
            "   ",  # Whitespace only
            "What is the meaning of life?",  # Off-topic
            "A" * 1000,  # Very long query
            "🤖 AI regulations 🇪🇺",  # With emojis
        ],
    }


@pytest.fixture
def performance_thresholds():
    """Performance thresholds for different query types."""

    return {
        "simple_queries": 15,  # seconds
        "complex_queries": 45,  # seconds
        "streaming_latency": 2,  # seconds for first chunk
        "memory_usage": 4 * 1024 * 1024 * 1024,  # 4GB in bytes
        "concurrent_requests": 5,  # number of simultaneous users
    }


@pytest.fixture
def quality_metrics():
    """Expected quality metrics for responses."""

    return {
        "minimum_quality_score": 0.7,
        "target_quality_score": 0.8,
        "entity_extraction_accuracy": 0.9,
        "tool_selection_precision": 0.85,
        "source_attribution_rate": 0.95,
    }


@asynccontextmanager
async def measure_performance():
    """Context manager to measure response time and resource usage."""

    start_time = time.time()
    start_memory = _get_memory_usage()

    try:
        yield {"start_time": start_time, "start_memory": start_memory}
    finally:
        end_time = time.time()
        end_memory = _get_memory_usage()

        metrics = {
            "response_time": end_time - start_time,
            "memory_delta": end_memory - start_memory,
            "peak_memory": max(start_memory, end_memory),
        }

        logger.info(f"Performance metrics: {metrics}")


def _get_memory_usage() -> int:
    """Get current memory usage in bytes."""
    try:
        import psutil

        process = psutil.Process()
        return process.memory_info().rss
    except ImportError:
        return 0


class TestDataValidator:
    """Validates test data and responses for quality."""

    @staticmethod
    def validate_response_structure(response: dict[str, Any]) -> bool:
        """Validate OpenAI-compatible response structure."""
        required_fields = ["id", "object", "created", "model", "choices"]

        for field in required_fields:
            if field not in response:
                return False

        if not response["choices"]:
            return False

        choice = response["choices"][0]
        if "message" not in choice or "content" not in choice["message"]:
            return False

        return True

    @staticmethod
    def validate_streaming_chunk(chunk: dict[str, Any]) -> bool:
        """Validate streaming response chunk structure."""
        required_fields = ["id", "object", "created", "model", "choices"]

        for field in required_fields:
            if field not in chunk:
                return False

        if not chunk["choices"]:
            return False

        choice = chunk["choices"][0]
        if "delta" not in choice:
            return False

        return True

    @staticmethod
    def extract_thinking_content(content: str) -> tuple[str, str]:
        """Extract thinking and response content from streamed response."""
        thinking = ""
        response = ""

        # Look for thinking tags
        if "<think>" in content and "</think>" in content:
            start = content.find("<think>")
            end = content.find("</think>") + len("</think>")
            thinking = content[start:end]
            response = content[end:].strip()
        elif "<thinking>" in content and "</thinking>" in content:
            start = content.find("<thinking>")
            end = content.find("</thinking>") + len("</thinking>")
            thinking = content[start:end]
            response = content[end:].strip()
        else:
            response = content

        return thinking, response


@pytest.fixture
def test_validator():
    """Provide test data validator."""
    return TestDataValidator()


# Pytest configuration for deployment tests
def pytest_configure(config):
    """Configure pytest for deployment tests."""

    # Add custom markers
    config.addinivalue_line(
        "markers", "deployment: mark test as deployment test (requires real services)"
    )
    config.addinivalue_line("markers", "slow: mark test as slow (takes more than 10 seconds)")
    config.addinivalue_line("markers", "requires_data: mark test as requiring knowledge graph data")


def pytest_collection_modifyitems(config, items):
    """Modify test collection for deployment tests."""

    # Skip tests if required environment variables are missing
    required_env_vars = ["OPENAI_API_KEY", "NEO4J_URI"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        skip_reason = f"Missing environment variables: {', '.join(missing_vars)}"
        skip_mark = pytest.mark.skip(reason=skip_reason)

        for item in items:
            item.add_marker(skip_mark)
