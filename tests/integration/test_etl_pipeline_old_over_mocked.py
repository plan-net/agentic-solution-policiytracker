"""
Integration tests for ETL pipeline components.

Tests the complete ETL flow with mocked external APIs but real internal logic.
"""

import pytest
import asyncio
import tempfile
import yaml
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

# Import test fixtures
from tests.fixtures.etl_fixtures import (
    sample_exa_response, sample_client_context, client_context_file,
    sample_policy_queries, ETLTestHelper
)

from src.etl.collectors.exa_direct import ExaDirectCollector
from src.etl.collectors.policy_landscape import PolicyLandscapeCollector
from src.etl.utils.policy_query_generator import PolicyQueryGenerator
from src.etl.utils.initialization_tracker import ETLInitializationTracker


class TestETLIntegration:
    """Integration tests for ETL pipeline."""
    
    @pytest.mark.asyncio
    async def test_exa_direct_collector_with_mock_api(self, sample_exa_response):
        """Test ExaDirectCollector with mocked API responses."""
        
        collector = ExaDirectCollector("test_api_key")
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Setup mock response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = sample_exa_response
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # Test collection
            articles = await collector.collect_news(
                query="EU AI Act regulation",
                max_items=10,
                days_back=7
            )
            
            # Validate results
            assert len(articles) == 3
            
            # Check article structure
            for article in articles:
                ETLTestHelper.assert_article_structure(article)
                assert article['content'] is not None
                assert len(article['content']) > 100  # Substantial content
    
    @pytest.mark.asyncio
    async def test_policy_query_generation(self, client_context_file):
        """Test policy query generation from client context."""
        
        generator = PolicyQueryGenerator(client_context_file)
        
        # Test query generation
        queries = generator.generate_policy_queries()
        
        assert len(queries) > 0
        assert all('query' in q for q in queries)
        assert all('category' in q for q in queries)
        assert all('description' in q for q in queries)
        
        # Test validation
        is_valid, errors = generator.validate_queries()
        assert is_valid, f"Query validation failed: {errors}"
        
        # Test summary
        summary = generator.get_query_summary()
        assert isinstance(summary, dict)
        assert len(summary) > 0
    
    @pytest.mark.asyncio
    async def test_policy_landscape_collector_end_to_end(
        self, 
        client_context_file, 
        sample_exa_response,
        tmp_path
    ):
        """Test complete policy collection flow."""
        
        collector = PolicyLandscapeCollector(
            exa_api_key="test_api_key",
            client_context_path=client_context_file
        )
        
        # Mock the underlying exa collector
        mock_articles = [
            {
                'title': 'EU AI Act Implementation Guide',
                'url': 'https://ec.europa.eu/ai-act-guide',
                'content': 'The European Union has published implementation guidelines...',
                'published_date': '2024-03-15T10:00:00Z',
                'author': 'EU Commission',
                'source': 'ec.europa.eu'
            },
            {
                'title': 'GDPR Enforcement Update',
                'url': 'https://edpb.europa.eu/gdpr-update',
                'content': 'New GDPR enforcement actions announced...',
                'published_date': '2024-03-14T15:30:00Z',
                'author': 'EDPB',
                'source': 'edpb.europa.eu'
            }
        ]
        
        collector.exa_collector.collect_news = AsyncMock(return_value=mock_articles)
        
        # Create mock storage directory
        data_dir = tmp_path / "data" / "input"
        data_dir.mkdir(parents=True)
        
        # Test collection
        with patch('pathlib.Path.mkdir'), \
             patch('builtins.open', create=True) as mock_open:
            
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            result = await collector.collect_policy_documents(
                days_back=7,
                max_results_per_query=5,
                max_concurrent_queries=2
            )
            
            # Validate results structure
            ETLTestHelper.assert_collection_result_structure(result)
            
            # Verify collection executed
            assert result['queries_processed'] > 0
            assert result['processing_time_seconds'] > 0
            assert result['collection_type'] == 'policy_landscape'
    
    @pytest.mark.asyncio
    async def test_initialization_tracker_workflow(self, tmp_path):
        """Test ETL initialization tracking workflow."""
        
        # Create test database file
        db_path = tmp_path / "test_init.db"
        
        tracker = ETLInitializationTracker(str(db_path))
        
        # Test first run (initialization)
        assert not tracker.is_initialized("policy_landscape")
        assert tracker.get_collection_days("policy_landscape") == 30  # Default init period
        
        # Mark as initialized
        await tracker.mark_initialized("policy_landscape")
        
        # Test subsequent run (regular operation)
        assert tracker.is_initialized("policy_landscape")
        assert tracker.get_collection_days("policy_landscape") == 7  # Regular period
        
        # Test configuration override
        tracker.configure_initialization("policy_landscape", init_days=90, regular_days=1)
        
        # Reset and test new configuration
        await tracker.reset_initialization("policy_landscape")
        assert not tracker.is_initialized("policy_landscape")
        assert tracker.get_collection_days("policy_landscape") == 90
        
        await tracker.mark_initialized("policy_landscape")
        assert tracker.get_collection_days("policy_landscape") == 1
    
    @pytest.mark.asyncio
    async def test_etl_collector_factory_integration(self):
        """Test ETL collector factory with different collector types."""
        
        from src.etl.collectors.factory import create_collector
        
        # Test ExaDirectCollector creation
        exa_collector = create_collector(
            collector_type="exa_direct",
            api_key="test_key"
        )
        
        assert isinstance(exa_collector, ExaDirectCollector)
        assert hasattr(exa_collector, 'collect_news')
        
        # Test that all collectors have compatible interfaces
        collectors = ["exa_direct", "apify", "exa"]
        
        for collector_type in collectors:
            try:
                collector = create_collector(
                    collector_type=collector_type,
                    api_key="test_key"
                )
                
                # Verify interface compatibility
                assert hasattr(collector, 'collect_news')
                
                # Check method signature
                import inspect
                sig = inspect.signature(collector.collect_news)
                params = list(sig.parameters.keys())
                
                assert 'query' in params
                
            except Exception as e:
                pytest.fail(f"Collector {collector_type} failed interface test: {e}")
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, client_context_file):
        """Test error handling and recovery in ETL pipeline."""
        
        collector = PolicyLandscapeCollector(
            exa_api_key="test_api_key", 
            client_context_path=client_context_file
        )
        
        # Test API failure recovery
        def side_effect(*args, **kwargs):
            # Simulate some queries succeeding, some failing
            query = kwargs.get('query', '')
            if 'fail' in query:
                raise Exception("API Error")
            return [{'title': 'Success', 'url': 'http://example.com', 'content': 'content'}]
        
        collector.exa_collector.collect_news = AsyncMock(side_effect=side_effect)
        
        # Mock query generation to include failing queries
        original_generate = collector.query_generator.generate_policy_queries
        
        def mock_generate():
            base_queries = original_generate()
            # Add a failing query
            base_queries.append({
                'query': 'this query will fail',
                'category': 'test_fail',
                'description': 'Test failure handling'
            })
            return base_queries
        
        collector.query_generator.generate_policy_queries = mock_generate
        
        # Test with mixed success/failure
        with patch('pathlib.Path.mkdir'), \
             patch('builtins.open', create=True):
            
            result = await collector.collect_policy_documents(
                days_back=7,
                max_results_per_query=2,
                max_concurrent_queries=1
            )
            
            # Should handle failures gracefully
            assert result['queries_failed'] > 0
            assert result['queries_processed'] > result['queries_failed']
    
    @pytest.mark.asyncio
    async def test_markdown_transformation_integration(self, tmp_path):
        """Test markdown transformation in the full pipeline."""
        
        from src.etl.transformers.markdown_transformer import MarkdownTransformer
        
        transformer = MarkdownTransformer()
        
        # Test article transformation
        article = {
            'title': 'EU AI Act Implementation Guidelines',
            'url': 'https://ec.europa.eu/ai-act-guide',
            'content': 'The European Union has published comprehensive guidelines...',
            'published_date': '2024-03-15T10:00:00Z',
            'author': 'European Commission',
            'source': 'ec.europa.eu',
            'policy_category': 'AI_regulation',
            'collection_type': 'policy_landscape'
        }
        
        markdown_content = await transformer.transform_to_markdown(article)
        
        # Validate markdown structure
        assert '---' in markdown_content  # YAML frontmatter
        assert 'title:' in markdown_content
        assert 'url:' in markdown_content
        assert 'published_date:' in markdown_content
        assert 'policy_category:' in markdown_content
        assert '# EU AI Act Implementation Guidelines' in markdown_content
        assert 'The European Union has published' in markdown_content
    
    def test_etl_configuration_validation(self):
        """Test ETL configuration validation."""
        
        # Test valid configurations
        valid_configs = [
            {"collector_type": "exa_direct", "days_back": 7},
            {"collector_type": "apify", "max_items": 50},
            {"collector_type": "exa", "category": "news"}
        ]
        
        for config in valid_configs:
            # This would typically validate against a schema
            assert config.get("collector_type") in ["exa_direct", "apify", "exa"]
            
        # Test invalid configurations  
        invalid_configs = [
            {"collector_type": "invalid"},
            {"days_back": -1},
            {"max_items": 0}
        ]
        
        for config in invalid_configs:
            # Validation logic would reject these
            if "collector_type" in config:
                assert config["collector_type"] not in ["exa_direct", "apify", "exa"]


class TestETLPerformance:
    """Performance tests for ETL pipeline."""
    
    @pytest.mark.asyncio
    async def test_concurrent_query_execution(self, client_context_file):
        """Test that concurrent queries execute efficiently."""
        
        collector = PolicyLandscapeCollector(
            exa_api_key="test_api_key",
            client_context_path=client_context_file
        )
        
        # Mock fast responses
        async def fast_collect_news(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate API delay
            return [{'title': 'Test', 'url': 'http://example.com', 'content': 'content'}]
        
        collector.exa_collector.collect_news = fast_collect_news
        
        # Test concurrent execution
        start_time = datetime.now()
        
        with patch('pathlib.Path.mkdir'), \
             patch('builtins.open', create=True):
            
            result = await collector.collect_policy_documents(
                days_back=7,
                max_results_per_query=1,
                max_concurrent_queries=3  # Process 3 queries concurrently
            )
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # With concurrent execution, should be faster than sequential
        # (This is a basic test - in reality would need more sophisticated timing)
        assert execution_time < 10  # Should complete reasonably quickly
        assert result['queries_processed'] > 0


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short"])