"""
Specific test to validate and fix the policy collector parameter bug.

This test reproduces the exact error we found in the Airflow logs
and validates the fix.
"""

from unittest.mock import AsyncMock

import pytest
import yaml

from src.etl.collectors.exa_direct import ExaDirectCollector
from src.etl.collectors.policy_landscape import PolicyLandscapeCollector


class TestPolicyCollectorParameterBug:
    """Test the specific parameter mismatch bug in PolicyLandscapeCollector."""

    @pytest.fixture
    def client_context_file(self, tmp_path):
        """Create test client context file."""
        context_data = {
            "client_profile": {
                "company_name": "TestCorp",
                "primary_markets": ["EU"],
                "core_industries": ["technology"],
            },
            "regulatory_focus": {"topic_patterns": ["AI regulation"]},
        }

        context_file = tmp_path / "client.yaml"
        with open(context_file, "w") as f:
            yaml.dump(context_data, f)
        return str(context_file)

    @pytest.fixture
    def policy_collector(self, client_context_file):
        """Create PolicyLandscapeCollector instance."""
        return PolicyLandscapeCollector(
            exa_api_key="test_key", client_context_path=client_context_file
        )

    @pytest.mark.asyncio
    async def test_parameter_mismatch_bug_reproduction(self, policy_collector):
        """Reproduce the exact parameter mismatch error from Airflow logs."""

        # This test reproduces the error:
        # collect_news() got an unexpected keyword argument 'search_query'

        query_info = {
            "query": "AI regulation EU technology",
            "category": "AI_regulation",
            "description": "AI regulatory updates",
        }

        # The bug occurs because _execute_single_query calls:
        # await self.exa_collector.collect_news(search_query=query_info['query'], ...)
        # But ExaDirectCollector.collect_news expects 'query' not 'search_query'

        with pytest.raises(TypeError) as exc_info:
            await policy_collector._execute_single_query(
                query_info, days_back=7, max_results_per_query=5
            )

        # Verify it's the expected parameter error
        assert "unexpected keyword argument" in str(exc_info.value)
        assert "search_query" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_exa_direct_collector_signature(self):
        """Verify ExaDirectCollector.collect_news method signature."""
        collector = ExaDirectCollector("test_key")

        # Check the actual method signature
        import inspect

        sig = inspect.signature(collector.collect_news)

        # Verify the first parameter is 'query', not 'search_query'
        params = list(sig.parameters.keys())
        assert params[0] == "query"
        assert "search_query" not in params

    @pytest.mark.asyncio
    async def test_fix_validation_with_mock(self, policy_collector):
        """Test the fix by mocking the collect_news method with correct parameters."""

        # Mock the collect_news method to accept correct parameters
        mock_result = {
            "success": True,
            "articles": [
                {
                    "title": "Test Article",
                    "url": "https://example.com/test",
                    "content": "Test content",
                    "published_date": "2024-03-15T10:00:00Z",
                    "author": "Test Author",
                    "source": "example.com",
                }
            ],
        }

        policy_collector.exa_collector.collect_news = AsyncMock(return_value=mock_result)

        query_info = {
            "query": "AI regulation EU technology",
            "category": "AI_regulation",
            "description": "AI regulatory updates",
        }

        # This should work when the fix is applied
        result = await policy_collector._execute_single_query(
            query_info, days_back=7, max_results_per_query=5
        )

        # Verify the call was made with correct parameters
        policy_collector.exa_collector.collect_news.assert_called_once()
        call_kwargs = policy_collector.exa_collector.collect_news.call_args.kwargs

        # The fix should use 'query' parameter, not 'search_query'
        # NOTE: This test will fail until the fix is applied
        expected_call_signature = {
            "query": "AI regulation EU technology",
            # other parameters would be start_date, num_results
        }

        # Check if 'query' is in the call (indicating fix is applied)
        # or 'search_query' is in the call (indicating bug still exists)
        if "search_query" in call_kwargs:
            pytest.fail("Bug still exists: using 'search_query' instead of 'query'")

        assert "query" in call_kwargs
        assert call_kwargs["query"] == "AI regulation EU technology"

    def test_method_signature_compatibility(self):
        """Test that all ETL collectors have compatible method signatures."""
        import inspect

        from src.etl.collectors.apify_news import ApifyNewsCollector
        from src.etl.collectors.exa_direct import ExaDirectCollector

        # Get method signatures
        exa_sig = inspect.signature(ExaDirectCollector.collect_news)
        apify_sig = inspect.signature(ApifyNewsCollector.collect_news)

        # Both should have 'query' as first parameter
        exa_params = list(exa_sig.parameters.keys())
        apify_params = list(apify_sig.parameters.keys())

        assert exa_params[1] == "query"  # [0] is 'self'
        assert apify_params[1] == "query"  # [0] is 'self'

        # Verify no 'search_query' parameter exists
        assert "search_query" not in exa_params
        assert "search_query" not in apify_params


if __name__ == "__main__":
    # Run just this test to validate the bug and fix
    pytest.main([__file__, "-v", "--tb=short"])
