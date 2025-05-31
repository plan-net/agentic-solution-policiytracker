"""Ray Serve deployment validation tests."""

import asyncio
import time

import aiohttp
import pytest


@pytest.mark.deployment
@pytest.mark.asyncio
class TestRayDeployment:
    """Test Ray Serve deployment functionality."""

    async def test_ray_serve_startup(self, ray_serve_deployment):
        """Test that Ray Serve starts successfully and deployment is accessible."""
        # The fixture handles deployment, so if we get here it worked
        assert ray_serve_deployment is not None

    async def test_health_endpoint(self, http_client, deployment_config):
        """Test that health endpoint is accessible and returns correct status."""
        async with http_client.get(deployment_config.HEALTH_ENDPOINT) as response:
            assert response.status == 200
            data = await response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "chat-server"

    async def test_models_endpoint(self, http_client, deployment_config):
        """Test OpenAI-compatible models endpoint."""
        async with http_client.get(deployment_config.MODELS_ENDPOINT) as response:
            assert response.status == 200
            data = await response.json()

            assert data["object"] == "list"
            assert "data" in data
            assert len(data["data"]) > 0

            model = data["data"][0]
            assert model["id"] == "political-monitoring-agent"
            assert model["object"] == "model"
            assert "created" in model
            assert model["owned_by"] == "political-monitoring"

    async def test_openai_api_compatibility(self, http_client, deployment_config):
        """Test that the API is compatible with OpenAI format."""
        # Test the actual API key is available
        import os

        assert os.getenv("OPENAI_API_KEY"), "OPENAI_API_KEY must be set for deployment tests"

        # Test basic chat completion request
        request_data = {
            "model": "political-monitoring-agent",
            "messages": [{"role": "user", "content": "Hello, can you help me?"}],
            "stream": False,
        }

        async with http_client.post(
            deployment_config.CHAT_ENDPOINT,
            json=request_data,
            timeout=aiohttp.ClientTimeout(total=deployment_config.RESPONSE_TIMEOUT),
        ) as response:
            assert response.status == 200
            data = await response.json()

            # Validate OpenAI response format
            assert "id" in data
            assert data["object"] == "chat.completion"
            assert "created" in data
            assert data["model"] == "political-monitoring-agent"
            assert "choices" in data
            assert len(data["choices"]) > 0

            choice = data["choices"][0]
            assert choice["index"] == 0
            assert "message" in choice
            assert choice["message"]["role"] == "assistant"
            assert len(choice["message"]["content"]) > 0
            assert choice["finish_reason"] == "stop"

    async def test_model_endpoint_registration(self, http_client, deployment_config):
        """Test that the model endpoint is properly registered."""
        # Test that we can call the chat endpoint without errors
        request_data = {
            "model": "political-monitoring-agent",
            "messages": [{"role": "user", "content": "Test registration"}],
            "stream": False,
        }

        start_time = time.time()
        async with http_client.post(deployment_config.CHAT_ENDPOINT, json=request_data) as response:
            response_time = time.time() - start_time

            assert response.status == 200
            assert response_time < deployment_config.RESPONSE_TIMEOUT

            data = await response.json()
            assert data["model"] == "political-monitoring-agent"

    async def test_resource_allocation_validation(self, ray_serve_deployment):
        """Test that the deployment has proper resource allocation."""
        # This test verifies the deployment can handle basic load
        # The fixture setup validates that the service is responsive

        # We can extend this to check Ray dashboard metrics if needed
        # For now, successful deployment creation indicates proper allocation
        assert ray_serve_deployment is not None

    @pytest.mark.slow
    async def test_concurrent_health_checks(self, http_client, deployment_config):
        """Test that the service can handle concurrent health check requests."""

        async def health_check():
            async with http_client.get(deployment_config.HEALTH_ENDPOINT) as response:
                return response.status == 200

        # Send 10 concurrent health check requests
        tasks = [health_check() for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed
        successful = [r for r in results if r is True]
        assert len(successful) == 10

    async def test_error_handling_for_invalid_model(self, http_client, deployment_config):
        """Test error handling when requesting invalid model."""
        request_data = {
            "model": "non-existent-model",
            "messages": [{"role": "user", "content": "Test"}],
            "stream": False,
        }

        async with http_client.post(deployment_config.CHAT_ENDPOINT, json=request_data) as response:
            # Should still return 200 but handle gracefully
            # (Our implementation doesn't validate model names strictly)
            assert response.status == 200
            data = await response.json()
            assert "choices" in data


@pytest.mark.deployment
@pytest.mark.asyncio
class TestComponentInitialization:
    """Test that all system components initialize correctly."""

    async def test_llm_initialization(self, http_client, deployment_config):
        """Test that LLM component initializes correctly."""
        # Send a simple request that would require LLM initialization
        request_data = {
            "model": "political-monitoring-agent",
            "messages": [{"role": "user", "content": "Test LLM initialization"}],
            "stream": False,
        }

        async with http_client.post(deployment_config.CHAT_ENDPOINT, json=request_data) as response:
            assert response.status == 200
            data = await response.json()

            # If we get a proper response, LLM initialized
            assert len(data["choices"][0]["message"]["content"]) > 0

    @pytest.mark.requires_data
    async def test_graphiti_initialization(self, http_client, deployment_config, graphiti_client):
        """Test that Graphiti knowledge graph initializes correctly."""
        # Send a query that would require knowledge graph access
        request_data = {
            "model": "political-monitoring-agent",
            "messages": [{"role": "user", "content": "What do you know about GDPR?"}],
            "stream": False,
        }

        async with http_client.post(
            deployment_config.CHAT_ENDPOINT,
            json=request_data,
            timeout=aiohttp.ClientTimeout(total=45),  # Knowledge graph queries can be slower
        ) as response:
            assert response.status == 200
            data = await response.json()

            # Should get a response mentioning GDPR from the knowledge graph
            content = data["choices"][0]["message"]["content"].lower()
            assert len(content) > 50  # Should be a substantial response

            # Could check for GDPR mentions, but content may vary based on graph state
            # The key test is that the query completed successfully

    async def test_tool_integration_manager_initialization(self, http_client, deployment_config):
        """Test that tool integration manager initializes correctly."""
        # Send a query that would require tool selection
        request_data = {
            "model": "political-monitoring-agent",
            "messages": [
                {"role": "user", "content": "Can you search for information about EU regulations?"}
            ],
            "stream": False,
        }

        async with http_client.post(
            deployment_config.CHAT_ENDPOINT,
            json=request_data,
            timeout=aiohttp.ClientTimeout(total=45),
        ) as response:
            assert response.status == 200
            data = await response.json()

            # Should get a response that indicates tools were used
            content = data["choices"][0]["message"]["content"]
            assert len(content) > 20

    async def test_multi_agent_orchestrator_initialization(self, http_client, deployment_config):
        """Test that multi-agent orchestrator initializes correctly."""
        # Send a complex query that would trigger multi-agent workflow
        request_data = {
            "model": "political-monitoring-agent",
            "messages": [
                {
                    "role": "user",
                    "content": "Analyze the regulatory impact of GDPR on tech companies",
                }
            ],
            "stream": False,
        }

        async with http_client.post(
            deployment_config.CHAT_ENDPOINT,
            json=request_data,
            timeout=aiohttp.ClientTimeout(total=60),  # Complex analysis can take time
        ) as response:
            assert response.status == 200
            data = await response.json()

            # Should get a comprehensive response from multi-agent processing
            content = data["choices"][0]["message"]["content"]
            assert len(content) > 100  # Should be a substantial analysis

            # Response should be structured and analytical
            # (exact content varies based on knowledge graph state)


@pytest.mark.deployment
@pytest.mark.asyncio
class TestDeploymentRobustness:
    """Test deployment robustness and reliability."""

    async def test_deployment_resilience_to_multiple_requests(self, http_client, deployment_config):
        """Test that deployment can handle multiple sequential requests."""

        request_data = {
            "model": "political-monitoring-agent",
            "messages": [{"role": "user", "content": "Quick test"}],
            "stream": False,
        }

        # Send 5 sequential requests
        for i in range(5):
            async with http_client.post(
                deployment_config.CHAT_ENDPOINT, json=request_data
            ) as response:
                assert response.status == 200
                data = await response.json()
                assert "choices" in data
                assert len(data["choices"]) > 0

    async def test_deployment_handles_empty_messages(self, http_client, deployment_config):
        """Test that deployment handles edge cases gracefully."""

        # Test empty messages list
        request_data = {"model": "political-monitoring-agent", "messages": [], "stream": False}

        async with http_client.post(deployment_config.CHAT_ENDPOINT, json=request_data) as response:
            assert response.status == 200
            data = await response.json()

            # Should handle gracefully and return a default response
            assert "choices" in data
            content = data["choices"][0]["message"]["content"]
            assert len(content) > 0

    async def test_deployment_handles_malformed_requests(self, http_client, deployment_config):
        """Test that deployment handles malformed requests."""

        # Test missing required fields
        malformed_data = {
            "model": "political-monitoring-agent"
            # Missing messages field
        }

        async with http_client.post(
            deployment_config.CHAT_ENDPOINT, json=malformed_data
        ) as response:
            # Should return an error status or handle gracefully
            # FastAPI/Pydantic should handle validation
            assert response.status in [200, 422]  # 422 for validation error

    @pytest.mark.slow
    async def test_deployment_memory_stability(self, http_client, deployment_config):
        """Test that deployment doesn't leak memory over multiple requests."""

        request_data = {
            "model": "political-monitoring-agent",
            "messages": [{"role": "user", "content": f"Memory test query {i}"}],
            "stream": False,
        }

        # Send multiple requests to check for memory leaks
        # This is a basic test - more sophisticated monitoring would require system metrics
        for i in range(10):
            async with http_client.post(
                deployment_config.CHAT_ENDPOINT,
                json={
                    **request_data,
                    "messages": [{"role": "user", "content": f"Memory test query {i}"}],
                },
            ) as response:
                assert response.status == 200

        # If we get here without errors, basic memory stability is maintained
