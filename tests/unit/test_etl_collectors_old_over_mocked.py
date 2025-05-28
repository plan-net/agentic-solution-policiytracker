"""
Unit tests for ETL collectors.

Tests all collector classes with mocked API responses to ensure
proper functionality without external dependencies.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from pathlib import Path
import json

from src.etl.collectors.exa_direct import ExaDirectCollector
from src.etl.collectors.policy_landscape import PolicyLandscapeCollector
from src.etl.collectors.apify_news import ApifyNewsCollector


@pytest.fixture
def mock_exa_response():
    """Mock Exa API response data."""
    return {
        "results": [
            {
                "title": "EU AI Act Passes Final Vote",
                "url": "https://example.com/eu-ai-act",
                "text": "The European Union has passed comprehensive AI regulation...",
                "publishedDate": "2024-03-15T10:30:00Z",
                "author": "Policy Reporter",
                "score": 0.95
            },
            {
                "title": "Meta Responds to DSA Requirements", 
                "url": "https://example.com/meta-dsa",
                "text": "Meta announces compliance measures for Digital Services Act...",
                "publishedDate": "2024-03-14T15:45:00Z",
                "author": "Tech News",
                "score": 0.87
            }
        ]
    }


@pytest.fixture
def mock_apify_response():
    """Mock Apify API response data."""
    return {
        "data": {
            "defaultDatasetId": "test_dataset_id"
        }
    }


@pytest.fixture
def mock_apify_items():
    """Mock Apify dataset items."""
    return [
        {
            "title": "Apple Announces Privacy Updates",
            "url": "https://example.com/apple-privacy",
            "text": "Apple introduces new privacy features...",
            "published": "2024-03-15T08:00:00Z",
            "author": "Apple Newsroom"
        }
    ]


class TestExaDirectCollector:
    """Test ExaDirectCollector functionality."""
    
    @pytest.fixture
    def collector(self):
        """Create ExaDirectCollector instance."""
        return ExaDirectCollector(api_key="test_api_key")
    
    @pytest.mark.asyncio
    async def test_collect_news_success(self, collector, mock_exa_response):
        """Test successful news collection."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Setup mock response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_exa_response
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # Test collection
            results = await collector.collect_news(
                query="EU regulation",
                max_items=10,
                days_back=7
            )
            
            # Verify results
            assert len(results) == 2
            assert results[0]['title'] == "EU AI Act Passes Final Vote"
            assert results[0]['url'] == "https://example.com/eu-ai-act"
            assert 'published_date' in results[0]
            assert 'content' in results[0]
    
    @pytest.mark.asyncio
    async def test_collect_news_api_error(self, collector):
        """Test API error handling."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Setup mock error response
            mock_response = AsyncMock()
            mock_response.status = 429  # Rate limit
            mock_response.text.return_value = "Rate limit exceeded"
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # Test error handling
            with pytest.raises(Exception) as exc_info:
                await collector.collect_news(query="test query")
            
            assert "429" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_collect_news_empty_results(self, collector):
        """Test handling of empty API results."""
        empty_response = {"results": []}
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = empty_response
            mock_post.return_value.__aenter__.return_value = mock_response
            
            results = await collector.collect_news(query="nonexistent topic")
            
            assert results == []
    
    def test_normalize_article(self, collector):
        """Test article normalization."""
        raw_item = {
            "title": "Test Article",
            "url": "https://example.com/test",
            "text": "Article content...",
            "publishedDate": "2024-03-15T10:30:00Z",
            "author": "Test Author",
            "score": 0.95
        }
        
        normalized = collector._normalize_article(raw_item)
        
        assert normalized['title'] == "Test Article"
        assert normalized['url'] == "https://example.com/test"
        assert normalized['content'] == "Article content..."
        assert normalized['author'] == "Test Author"
        assert 'published_date' in normalized
        assert 'source' in normalized


class TestApifyNewsCollector:
    """Test ApifyNewsCollector functionality."""
    
    @pytest.fixture
    def collector(self):
        """Create ApifyNewsCollector instance."""
        return ApifyNewsCollector(api_token="test_token")
    
    @pytest.mark.asyncio
    async def test_collect_news_success(self, collector, mock_apify_response, mock_apify_items):
        """Test successful news collection via Apify."""
        with patch('aiohttp.ClientSession.post') as mock_post, \
             patch('aiohttp.ClientSession.get') as mock_get:
            
            # Setup mock run response
            mock_run_response = AsyncMock()
            mock_run_response.status = 201
            mock_run_response.json.return_value = mock_apify_response
            mock_post.return_value.__aenter__.return_value = mock_run_response
            
            # Setup mock items response
            mock_items_response = AsyncMock()
            mock_items_response.status = 200
            mock_items_response.json.return_value = mock_apify_items
            mock_get.return_value.__aenter__.return_value = mock_items_response
            
            # Test collection
            results = await collector.collect_news(
                query="Apple",
                max_items=10,
                days_back=7
            )
            
            assert len(results) == 1
            assert results[0]['title'] == "Apple Announces Privacy Updates"
    
    @pytest.mark.asyncio
    async def test_collect_news_run_failure(self, collector):
        """Test handling of Apify run failure."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 400
            mock_response.text.return_value = "Bad request"
            mock_post.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(Exception) as exc_info:
                await collector.collect_news(query="test")
            
            assert "400" in str(exc_info.value)


class TestPolicyLandscapeCollector:
    """Test PolicyLandscapeCollector functionality."""
    
    @pytest.fixture
    def collector(self, tmp_path):
        """Create PolicyLandscapeCollector instance with test data."""
        # Create test client context
        client_context = {
            'client_profile': {
                'company_name': 'TestCorp',
                'primary_markets': ['EU', 'US'],
                'core_industries': ['technology', 'finance']
            },
            'regulatory_focus': {
                'topic_patterns': ['AI regulation', 'data privacy', 'cybersecurity']
            }
        }
        
        context_file = tmp_path / "client.yaml"
        import yaml
        with open(context_file, 'w') as f:
            yaml.dump(client_context, f)
        
        return PolicyLandscapeCollector(
            exa_api_key="test_key",
            client_context_path=str(context_file),
            storage_type="local"
        )
    
    @pytest.mark.asyncio
    async def test_collect_policy_documents_success(self, collector, mock_exa_response):
        """Test successful policy document collection."""
        # Mock the underlying exa collector
        collector.exa_collector.collect_news = AsyncMock(return_value={
            'success': True,
            'articles': mock_exa_response['results']
        })
        
        # Storage is already set up via the standardized interface
        
        with patch('pathlib.Path.mkdir'), \
             patch('builtins.open', create=True) as mock_open:
            
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            # Test collection
            result = await collector.collect_policy_documents(
                days_back=7,
                max_results_per_query=5,
                max_concurrent_queries=2
            )
            
            # Verify results structure
            assert result['collection_type'] == 'policy_landscape'
            assert 'queries_processed' in result
            assert 'documents_saved' in result
            assert 'processing_time_seconds' in result
            
            # Verify queries were generated
            assert result['queries_processed'] > 0
    
    @pytest.mark.asyncio 
    async def test_execute_single_query_success(self, collector, mock_exa_response):
        """Test single query execution."""
        # Mock the exa collector method properly
        collector.exa_collector.collect_news = AsyncMock(return_value={
            'success': True,
            'articles': mock_exa_response['results']
        })
        
        query_info = {
            'query': 'EU AI Act regulation',
            'category': 'AI_regulation',
            'description': 'AI regulatory updates'
        }
        
        result = await collector._execute_single_query(
            query_info, days_back=7, max_results_per_query=5
        )
        
        assert result['success'] is True
        assert result['query'] == 'EU AI Act regulation'
        assert result['category'] == 'AI_regulation'
        assert len(result['articles']) == 2
        
        # Verify articles have policy metadata
        for article in result['articles']:
            assert article['policy_category'] == 'AI_regulation'
            assert article['collection_type'] == 'policy_landscape'
    
    @pytest.mark.asyncio
    async def test_execute_single_query_failure(self, collector):
        """Test query execution error handling."""
        # Mock the exa collector to raise an exception
        collector.exa_collector.collect_news = AsyncMock(side_effect=Exception("API Error"))
        
        query_info = {
            'query': 'test query',
            'category': 'test_category',
            'description': 'test description'
        }
        
        result = await collector._execute_single_query(
            query_info, days_back=7, max_results_per_query=5
        )
        
        assert result['success'] is False
        assert result['query'] == 'test query'
        assert 'error' in result
        assert "API Error" in result['error']
    
    def test_generate_policy_filename(self, collector):
        """Test policy filename generation."""
        article = {
            'title': 'EU Digital Services Act: New Requirements for Tech Companies!',
            'url': 'https://ec.europa.eu/digital-services-act'
        }
        
        published_date = datetime(2024, 3, 15, 10, 30)
        
        filename = collector._generate_policy_filename(article, published_date)
        
        assert filename.startswith('20240315_')
        assert 'ec-europa-eu' in filename
        assert filename.endswith('.md')
        assert len(filename) < 100  # Reasonable length
    
    def test_clean_filename(self, collector):
        """Test filename cleaning."""
        test_cases = [
            ("EU AI Act: New Rules!", "eu-ai-act-new-rules"),
            ("Special chars @#$%", "special-chars"),
            ("A" * 100, "a" * 50),  # Truncation test
            ("Multiple---spaces   here", "multiple-spaces-here")
        ]
        
        for input_text, expected in test_cases:
            result = collector._clean_filename(input_text)
            assert result == expected


class TestETLIntegration:
    """Integration tests for ETL collectors."""
    
    @pytest.mark.asyncio
    async def test_collector_interface_consistency(self):
        """Test that all collectors have consistent interfaces."""
        # Test that all collectors implement collect_news with same signature
        exa_collector = ExaDirectCollector("test_key")
        apify_collector = ApifyNewsCollector("test_token")
        
        # Check method exists and has expected parameters
        assert hasattr(exa_collector, 'collect_news')
        assert hasattr(apify_collector, 'collect_news')
        
        # Check collect_news method signatures are compatible
        import inspect
        
        exa_sig = inspect.signature(exa_collector.collect_news)
        apify_sig = inspect.signature(apify_collector.collect_news)
        
        # Both should have query parameter
        assert 'query' in exa_sig.parameters
        assert 'query' in apify_sig.parameters
    
    @pytest.mark.asyncio
    async def test_policy_collector_with_real_query_generation(self, tmp_path):
        """Test policy collector with actual query generation."""
        # Create realistic client context
        client_context = {
            'client_profile': {
                'company_name': 'TechCorp',
                'primary_markets': ['EU', 'US'],
                'core_industries': ['technology']
            },
            'regulatory_focus': {
                'topic_patterns': ['AI regulation', 'data privacy']
            }
        }
        
        context_file = tmp_path / "client.yaml"
        import yaml
        with open(context_file, 'w') as f:
            yaml.dump(client_context, f)
        
        collector = PolicyLandscapeCollector(
            exa_api_key="test_key",
            client_context_path=str(context_file)
        )
        
        # Test query generation
        stats = await collector.get_collection_stats()
        
        assert stats['total_queries'] > 0
        assert stats['validation']['is_valid']
        assert 'AI_regulation' in [cat for cat in stats['categories']]


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])