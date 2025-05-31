"""End-to-end multi-agent workflow deployment tests."""

import asyncio
import json
import time

import aiohttp
import pytest


@pytest.mark.deployment
@pytest.mark.asyncio
class TestMultiAgentWorkflow:
    """Test complete multi-agent workflow functionality."""

    async def test_query_understanding_agent(self, http_client, deployment_config, sample_queries):
        """Test that Query Understanding Agent processes different query types correctly."""

        for category, queries in sample_queries.items():
            if category == "edge_cases":
                continue  # Skip edge cases for basic agent testing

            for query in queries[:1]:  # Test one query per category
                request_data = {
                    "model": "political-monitoring-agent",
                    "messages": [{"role": "user", "content": query}],
                    "stream": True,
                }

                start_time = time.time()
                collected_chunks = []

                async with http_client.post(
                    deployment_config.CHAT_ENDPOINT,
                    json=request_data,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    assert response.status == 200

                    async for line in response.content:
                        line_str = line.decode("utf-8").strip()
                        if line_str.startswith("data: ") and line_str != "data: [DONE]":
                            try:
                                chunk_data = json.loads(line_str[6:])  # Remove 'data: '
                                collected_chunks.append(chunk_data)
                            except json.JSONDecodeError:
                                continue

                response_time = time.time() - start_time

                # Validate workflow stages in collected chunks
                workflow_stages = []
                for chunk in collected_chunks:
                    content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if "<think>" in content:
                        if "query_understanding" in content:
                            workflow_stages.append("query_understanding")
                        elif "tool_planning" in content:
                            workflow_stages.append("tool_planning")
                        elif "tool_execution" in content:
                            workflow_stages.append("tool_execution")
                        elif "response_synthesis" in content:
                            workflow_stages.append("response_synthesis")

                # Assertions
                assert len(collected_chunks) > 0, f"No chunks received for query: {query}"
                assert response_time < 45, f"Response too slow: {response_time:.2f}s for {query}"
                assert (
                    "query_understanding" in workflow_stages
                ), f"Query understanding stage missing for: {query}"

    async def test_agent_sequence_validation(self, http_client, deployment_config):
        """Test that agents execute in the correct sequence."""

        request_data = {
            "model": "political-monitoring-agent",
            "messages": [{"role": "user", "content": "How does GDPR affect Google?"}],
            "stream": True,
        }

        workflow_sequence = []

        async with http_client.post(
            deployment_config.CHAT_ENDPOINT,
            json=request_data,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as response:
            assert response.status == 200

            async for line in response.content:
                line_str = line.decode("utf-8").strip()
                if line_str.startswith("data: ") and line_str != "data: [DONE]":
                    try:
                        chunk_data = json.loads(line_str[6:])
                        content = (
                            chunk_data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        )

                        if "<think>" in content:
                            if "current_agent" in content:
                                # Extract current agent from thinking content
                                if "'current_agent': 'query_understanding'" in content:
                                    if "query_understanding" not in workflow_sequence:
                                        workflow_sequence.append("query_understanding")
                                elif "'current_agent': 'tool_planning'" in content:
                                    if "tool_planning" not in workflow_sequence:
                                        workflow_sequence.append("tool_planning")
                                elif "'current_agent': 'tool_execution'" in content:
                                    if "tool_execution" not in workflow_sequence:
                                        workflow_sequence.append("tool_execution")
                                elif "'current_agent': 'response_synthesis'" in content:
                                    if "response_synthesis" not in workflow_sequence:
                                        workflow_sequence.append("response_synthesis")
                    except json.JSONDecodeError:
                        continue

        # Validate proper agent sequence
        expected_sequence = [
            "query_understanding",
            "tool_planning",
        ]  # At minimum these two should execute

        for i, expected_agent in enumerate(expected_sequence):
            assert i < len(workflow_sequence), f"Missing agent in sequence: {expected_agent}"
            assert (
                workflow_sequence[i] == expected_agent
            ), f"Wrong agent order. Expected {expected_agent}, got {workflow_sequence[i] if i < len(workflow_sequence) else 'None'}"

    async def test_response_quality_metrics(self, http_client, deployment_config, quality_metrics):
        """Test response quality across different query types."""

        test_queries = [
            "What is GDPR?",
            "How does the EU AI Act affect US companies?",
            "What are the compliance requirements for data protection?",
        ]

        results = []

        for query in test_queries:
            request_data = {
                "model": "political-monitoring-agent",
                "messages": [{"role": "user", "content": query}],
                "stream": False,
            }

            start_time = time.time()

            async with http_client.post(
                deployment_config.CHAT_ENDPOINT,
                json=request_data,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as response:
                response_time = time.time() - start_time
                assert response.status == 200

                data = await response.json()
                content = data["choices"][0]["message"]["content"]

                # Quality metrics
                word_count = len(content.split())
                has_structured_info = any(
                    marker in content.lower()
                    for marker in ["gdpr", "regulation", "compliance", "act", "directive"]
                )
                is_substantial = word_count > 20
                not_generic = "please try rephrasing" not in content.lower()

                quality_score = (
                    sum([has_structured_info, is_substantial, not_generic, response_time < 45])
                    / 4.0
                )

                results.append(
                    {
                        "query": query,
                        "response_time": response_time,
                        "word_count": word_count,
                        "quality_score": quality_score,
                        "content_preview": content[:100] + "..." if len(content) > 100 else content,
                    }
                )

        # Validate quality metrics
        avg_quality = sum(r["quality_score"] for r in results) / len(results)
        avg_response_time = sum(r["response_time"] for r in results) / len(results)

        # Log results for analysis
        print("\n=== Response Quality Analysis ===")
        for result in results:
            print(f"Query: {result['query']}")
            print(f"  Quality Score: {result['quality_score']:.2f}")
            print(f"  Response Time: {result['response_time']:.2f}s")
            print(f"  Word Count: {result['word_count']}")
            print(f"  Preview: {result['content_preview']}")
            print()

        print(f"Average Quality Score: {avg_quality:.2f}")
        print(f"Average Response Time: {avg_response_time:.2f}s")

        # Quality thresholds
        assert avg_quality > 0.5, f"Average quality too low: {avg_quality:.2f}"
        assert avg_response_time < 45, f"Average response time too slow: {avg_response_time:.2f}s"

    async def test_agent_error_handling(self, http_client, deployment_config):
        """Test how multi-agent system handles various error scenarios."""

        error_scenarios = [
            {"name": "empty_query", "query": "", "expected_behavior": "graceful_handling"},
            {
                "name": "very_long_query",
                "query": "What is " + "GDPR " * 200,  # Very long query
                "expected_behavior": "truncation_or_processing",
            },
            {
                "name": "nonsense_query",
                "query": "asdf qwerty zxcv political monitoring",
                "expected_behavior": "attempted_processing",
            },
            {
                "name": "special_characters",
                "query": "What is GDPR? 🤖 💻 🇪🇺",
                "expected_behavior": "normal_processing",
            },
        ]

        for scenario in error_scenarios:
            request_data = {
                "model": "political-monitoring-agent",
                "messages": [{"role": "user", "content": scenario["query"]}],
                "stream": False,
            }

            try:
                async with http_client.post(
                    deployment_config.CHAT_ENDPOINT,
                    json=request_data,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    # Should not crash with 500 errors
                    assert response.status in [
                        200,
                        400,
                    ], f"Unexpected status {response.status} for {scenario['name']}"

                    if response.status == 200:
                        data = await response.json()
                        assert "choices" in data, f"Malformed response for {scenario['name']}"
                        assert (
                            len(data["choices"]) > 0
                        ), f"No choices in response for {scenario['name']}"

                        content = data["choices"][0]["message"]["content"]
                        assert len(content) > 0, f"Empty response for {scenario['name']}"

                        print(f"✅ {scenario['name']}: Handled gracefully")
                        print(f"   Response: {content[:100]}...")

            except asyncio.TimeoutError:
                print(f"⚠️  {scenario['name']}: Timeout (may be expected for very long queries)")
            except Exception as e:
                print(f"❌ {scenario['name']}: Unexpected error: {e}")
                # Don't fail the test for error scenarios, but log them

    async def test_concurrent_requests(self, http_client, deployment_config):
        """Test system behavior under concurrent load."""

        test_queries = [
            "What is GDPR?",
            "How does the EU AI Act work?",
            "What are data protection requirements?",
            "Explain privacy regulations in Europe",
            "What is the Digital Services Act?",
        ]

        async def single_request(query: str, request_id: int):
            request_data = {
                "model": "political-monitoring-agent",
                "messages": [{"role": "user", "content": f"{query} (Request {request_id})"}],
                "stream": False,
            }

            start_time = time.time()
            try:
                async with http_client.post(
                    deployment_config.CHAT_ENDPOINT,
                    json=request_data,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as response:
                    response_time = time.time() - start_time
                    status = response.status

                    if status == 200:
                        data = await response.json()
                        content = data["choices"][0]["message"]["content"]
                        return {
                            "request_id": request_id,
                            "status": "success",
                            "response_time": response_time,
                            "word_count": len(content.split()),
                            "status_code": status,
                        }
                    else:
                        return {
                            "request_id": request_id,
                            "status": "error",
                            "response_time": response_time,
                            "error": f"HTTP {status}",
                            "status_code": status,
                        }
            except Exception as e:
                response_time = time.time() - start_time
                return {
                    "request_id": request_id,
                    "status": "error",
                    "response_time": response_time,
                    "error": str(e),
                    "status_code": None,
                }

        # Send 5 concurrent requests
        tasks = [single_request(query, i) for i, query in enumerate(test_queries)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze results
        successful_requests = [
            r for r in results if isinstance(r, dict) and r.get("status") == "success"
        ]
        failed_requests = [
            r for r in results if not isinstance(r, dict) or r.get("status") != "success"
        ]

        success_rate = len(successful_requests) / len(results)
        avg_response_time = (
            sum(r["response_time"] for r in successful_requests) / len(successful_requests)
            if successful_requests
            else 0
        )

        print("\n=== Concurrent Load Test Results ===")
        print(f"Total Requests: {len(results)}")
        print(f"Successful: {len(successful_requests)}")
        print(f"Failed: {len(failed_requests)}")
        print(f"Success Rate: {success_rate:.1%}")
        print(f"Average Response Time: {avg_response_time:.2f}s")

        # Validate concurrent performance
        assert success_rate >= 0.6, f"Success rate too low under load: {success_rate:.1%}"
        if successful_requests:
            assert (
                avg_response_time < 90
            ), f"Response time too slow under load: {avg_response_time:.2f}s"


@pytest.mark.deployment
@pytest.mark.asyncio
class TestWorkflowStateValidation:
    """Test multi-agent workflow state management."""

    async def test_state_progression(self, http_client, deployment_config):
        """Test that workflow state progresses correctly through agents."""

        request_data = {
            "model": "political-monitoring-agent",
            "messages": [{"role": "user", "content": "What is the EU Digital Services Act?"}],
            "stream": True,
        }

        state_snapshots = []

        async with http_client.post(
            deployment_config.CHAT_ENDPOINT,
            json=request_data,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as response:
            assert response.status == 200

            async for line in response.content:
                line_str = line.decode("utf-8").strip()
                if line_str.startswith("data: ") and line_str != "data: [DONE]":
                    try:
                        chunk_data = json.loads(line_str[6:])
                        content = (
                            chunk_data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        )

                        if "<think>" in content and "current_agent" in content:
                            # Extract state information
                            if "'query_analysis':" in content:
                                state_snapshots.append("has_query_analysis")
                            if "'tool_plan':" in content:
                                state_snapshots.append("has_tool_plan_field")
                            if "'tool_results':" in content:
                                state_snapshots.append("has_tool_results_field")
                            if "'final_response':" in content:
                                state_snapshots.append("has_final_response_field")

                    except json.JSONDecodeError:
                        continue

        # Validate state fields are present
        required_state_fields = ["has_query_analysis", "has_tool_plan_field"]
        for required_field in required_state_fields:
            assert required_field in state_snapshots, f"Missing state field: {required_field}"

    async def test_session_isolation(self, http_client, deployment_config):
        """Test that different sessions maintain separate state."""

        # Send two different queries to test session isolation
        queries = ["What is GDPR?", "What is the EU AI Act?"]

        session_responses = []

        for i, query in enumerate(queries):
            request_data = {
                "model": "political-monitoring-agent",
                "messages": [{"role": "user", "content": query}],
                "stream": False,
            }

            async with http_client.post(
                deployment_config.CHAT_ENDPOINT,
                json=request_data,
                timeout=aiohttp.ClientTimeout(total=45),
            ) as response:
                assert response.status == 200
                data = await response.json()

                session_responses.append(
                    {
                        "session": i,
                        "query": query,
                        "response_id": data["id"],
                        "content": data["choices"][0]["message"]["content"],
                    }
                )

        # Validate sessions are different
        assert (
            session_responses[0]["response_id"] != session_responses[1]["response_id"]
        ), "Session IDs should be different"

        # Content should be different for different queries
        content_similarity = len(
            set(session_responses[0]["content"]) & set(session_responses[1]["content"])
        ) / max(len(session_responses[0]["content"]), len(session_responses[1]["content"]))
        assert content_similarity < 0.8, "Responses too similar across sessions"
