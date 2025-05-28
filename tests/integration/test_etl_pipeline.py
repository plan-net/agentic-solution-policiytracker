"""
Properly written ETL integration tests.

These tests focus on real component interactions with minimal mocking,
following the principles in test-patterns.md.
"""

import pytest
import asyncio
import tempfile
import yaml
from pathlib import Path
from unittest.mock import AsyncMock, patch
from datetime import datetime

from src.etl.collectors.exa_direct import ExaDirectCollector
from src.etl.collectors.policy_landscape import PolicyLandscapeCollector
from src.etl.transformers.markdown_transformer import MarkdownTransformer
from src.etl.storage.local import LocalStorage
from src.etl.storage import get_storage
from src.etl.utils.initialization_tracker import ETLInitializationTracker


class TestETLEndToEndIntegration:
    """Test complete ETL workflows with real component interactions."""
    
    @pytest.fixture
    def realistic_client_context(self, tmp_path):
        """Create realistic client context for testing."""
        context_data = {
            'client_profile': {
                'company_name': 'TechCorp Europe',
                'primary_markets': ['EU', 'US', 'UK'],
                'core_industries': ['technology', 'artificial-intelligence', 'e-commerce'],
                'regulatory_concerns': [
                    'AI governance and compliance',
                    'Data protection and privacy',
                    'Digital services regulation',
                    'Competition law'
                ]
            },
            'regulatory_focus': {
                'topic_patterns': [
                    'AI Act implementation',
                    'GDPR enforcement',
                    'Digital Services Act compliance',
                    'Digital Markets Act',
                    'NIS2 Directive cybersecurity'
                ],
                'exclude_patterns': [
                    'sports and entertainment',
                    'weather reports'
                ]
            },
            'monitoring_scope': {
                'regulatory_bodies': [
                    'European Commission',
                    'European Data Protection Board',
                    'Member State authorities'
                ],
                'policy_areas': [
                    'artificial intelligence',
                    'data protection',
                    'cybersecurity',
                    'digital services',
                    'competition'
                ]
            }
        }
        
        context_file = tmp_path / "realistic_client.yaml"
        with open(context_file, 'w') as f:
            yaml.dump(context_data, f)
        return str(context_file)
    
    @pytest.mark.asyncio
    async def test_complete_policy_collection_workflow(self, realistic_client_context):
        """Test complete policy collection workflow with real components."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize real collector with real storage
            collector = PolicyLandscapeCollector(
                exa_api_key="test_key",
                client_context_path=realistic_client_context,
                storage_type="local"
            )
            
            # Use real storage in temp directory
            collector.storage = LocalStorage(base_path=temp_dir)
            
            # Mock only external API - return realistic data
            realistic_articles = [
                {
                    'title': 'European Commission Publishes AI Act Implementation Guidelines',
                    'url': 'https://ec.europa.eu/ai-act-implementation-2024',
                    'content': 'The European Commission has released comprehensive implementation guidelines for the AI Act, providing detailed compliance requirements for high-risk AI systems. Organizations must implement risk management systems, ensure data quality, and maintain human oversight.',
                    'published_date': '2024-03-15T09:00:00Z',
                    'author': 'European Commission',
                    'source': 'ec.europa.eu'
                },
                {
                    'title': 'EDPB Issues New GDPR Guidance on AI Systems',
                    'url': 'https://edpb.europa.eu/gdpr-ai-guidance-2024',
                    'content': 'The European Data Protection Board has issued updated guidance on applying GDPR principles to artificial intelligence systems, addressing data minimization, purpose limitation, and automated decision-making requirements.',
                    'published_date': '2024-03-14T14:30:00Z',
                    'author': 'EDPB Secretariat',
                    'source': 'edpb.europa.eu'
                },
                {
                    'title': 'German DPA Fines Tech Company for Cookie Banner Violations',
                    'url': 'https://www.lda.bayern.de/en/news/cookie-fine-2024',
                    'content': 'The Bavarian Data Protection Authority has imposed a significant fine on a technology company for using manipulative cookie banners that do not comply with GDPR consent requirements.',
                    'published_date': '2024-03-13T11:15:00Z',
                    'author': 'Bavarian DPA',
                    'source': 'lda.bayern.de'
                }
            ]
            
            collector.exa_collector.collect_news = AsyncMock(return_value=realistic_articles)
            
            # Execute real workflow
            result = await collector.collect_policy_documents(
                days_back=7,
                max_results_per_query=3,
                max_concurrent_queries=2
            )
            
            # Validate real workflow results
            assert result['collection_type'] == 'policy_landscape'
            assert result['queries_processed'] > 0
            assert result['total_articles_found'] == 3
            assert result['documents_saved'] == 3  # All unique articles should be saved
            
            # Validate real file creation
            md_files = list(Path(temp_dir).rglob("*.md"))
            json_files = list(Path(temp_dir).rglob("*.json"))
            
            assert len(md_files) == 3, "Should create 3 markdown files"
            assert len(json_files) == 0, "Should not create any JSON files"
            
            # Validate real file structure
            for md_file in md_files:
                assert str(md_file).startswith(temp_dir), "Files should be in temp directory"
                assert '/policy/' in str(md_file), "Should be in policy subdirectory"
                assert '2024-03' in str(md_file), "Should be in date-based subdirectory"
                
                # Validate real file content
                with open(md_file, 'r') as f:
                    content = f.read()
                
                assert content.startswith('---'), "Should have YAML frontmatter"
                assert 'collection_type: policy_landscape' in content
                assert 'policy_category:' in content
                assert 'collector_type: exa_direct' in content
                
                # Should contain actual article content
                assert any(title in content for title in [
                    'AI Act Implementation Guidelines',
                    'GDPR Guidance on AI Systems', 
                    'Cookie Banner Violations'
                ])
    
    @pytest.mark.asyncio
    async def test_storage_interface_consistency_across_collectors(self):
        """Test that all collectors use storage consistently."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test that storage factory creates consistent interfaces
            news_storage = get_storage("local", base_path=f"{temp_dir}/news")
            policy_storage = get_storage("local", base_path=f"{temp_dir}/policy")
            
            # Both should have identical interfaces
            news_methods = set([m for m in dir(news_storage) if not m.startswith('_')])
            policy_methods = set([m for m in dir(policy_storage) if not m.startswith('_')])
            
            assert news_methods == policy_methods, "Storage interfaces should be identical"
            
            # Test real saving behavior is consistent
            test_content = """---
title: "Test Document"
url: "https://example.com/test"
---

# Test Document
Content here.
"""
            
            metadata = {'url': 'https://example.com/test', 'type': 'test'}
            
            # Both should save files identically
            news_success = await news_storage.save_document(test_content, "test.md", metadata)
            policy_success = await policy_storage.save_document(test_content, "test.md", metadata)
            
            assert news_success == policy_success == True
            
            # Both should create only markdown files (no JSON)
            news_files = list(Path(f"{temp_dir}/news").rglob("*"))
            policy_files = list(Path(f"{temp_dir}/policy").rglob("*"))
            
            news_md = [f for f in news_files if f.is_file() and f.suffix == '.md']
            policy_md = [f for f in policy_files if f.is_file() and f.suffix == '.md']
            news_json = [f for f in news_files if f.is_file() and f.suffix == '.json']
            policy_json = [f for f in policy_files if f.is_file() and f.suffix == '.json']
            
            assert len(news_md) == 1 and len(policy_md) == 1
            assert len(news_json) == 0 and len(policy_json) == 0
    
    @pytest.mark.asyncio
    async def test_transformer_real_processing_consistency(self):
        """Test transformer produces consistent results across different use cases."""
        
        transformer = MarkdownTransformer()
        
        # Test with different types of articles
        test_articles = [
            {
                'title': 'Policy Document: EU AI Act Guidelines',
                'url': 'https://ec.europa.eu/ai-act',
                'content': 'Comprehensive guidelines for AI compliance...',
                'published_date': '2024-03-15T10:00:00Z',
                'author': 'European Commission',
                'source': 'ec.europa.eu',
                'collection_type': 'policy_landscape',
                'policy_category': 'AI_regulation'
            },
            {
                'title': 'News Article: Company Announces Privacy Updates',
                'url': 'https://company.com/privacy-update',
                'content': 'Company announces new privacy features...',
                'published_date': '2024-03-15T11:00:00Z',
                'author': 'Company Newsroom',
                'source': 'company.com',
                'collection_type': 'news'
            }
        ]
        
        # Test real transformation for both types
        results = []
        for article in test_articles:
            markdown_content, filename = transformer.transform_article(article)
            results.append((markdown_content, filename))
        
        # Validate consistent processing
        for markdown_content, filename in results:
            # All should have proper YAML frontmatter
            assert markdown_content.startswith('---')
            assert 'title:' in markdown_content
            assert 'url:' in markdown_content
            assert 'published_date:' in markdown_content
            
            # All should have proper markdown structure
            assert '\n# ' in markdown_content
            
            # All should have valid filenames
            assert filename.endswith('.md')
            assert len(filename) > 10
    
    @pytest.mark.asyncio
    async def test_initialization_tracker_real_behavior(self):
        """Test initialization tracker with real database operations."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_init.db"
            
            # Test real initialization tracking
            tracker = ETLInitializationTracker(str(db_path))
            
            # Test first run behavior
            assert not tracker.is_initialized('policy_landscape')
            assert tracker.get_collection_days('policy_landscape') == 30  # Initialization period
            
            # Test marking as initialized
            await tracker.mark_initialized('policy_landscape')
            
            # Test subsequent run behavior
            assert tracker.is_initialized('policy_landscape')
            assert tracker.get_collection_days('policy_landscape') == 7  # Regular period
            
            # Test database persistence (create new tracker instance)
            tracker2 = ETLInitializationTracker(str(db_path))
            assert tracker2.is_initialized('policy_landscape')
            assert tracker2.get_collection_days('policy_landscape') == 7
    
    @pytest.mark.asyncio
    async def test_error_recovery_and_partial_success(self, realistic_client_context):
        """Test real error handling and partial success scenarios."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = PolicyLandscapeCollector(
                exa_api_key="test_key",
                client_context_path=realistic_client_context,
                storage_type="local"
            )
            
            collector.storage = LocalStorage(base_path=temp_dir)
            
            # Mock API to return mix of valid and problematic articles
            mixed_articles = [
                {
                    'title': 'Valid Article 1',
                    'url': 'https://example.com/valid1',
                    'content': 'Valid content...',
                    'published_date': '2024-03-15T10:00:00Z',
                    'author': 'Author 1',
                    'source': 'example.com'
                },
                {
                    'title': 'Valid Article 2',
                    'url': 'https://example.com/valid2',
                    'content': 'More valid content...',
                    'published_date': '2024-03-14T10:00:00Z',
                    'author': 'Author 2',
                    'source': 'example.com'
                },
                {
                    # Article with missing required fields (will cause processing errors)
                    'title': 'Problematic Article',
                    'url': 'https://example.com/problematic',
                    # Missing content, published_date, etc.
                }
            ]
            
            collector.exa_collector.collect_news = AsyncMock(return_value=mixed_articles)
            
            # Execute collection (should handle errors gracefully)
            result = await collector.collect_policy_documents(
                days_back=7,
                max_results_per_query=5,
                max_concurrent_queries=1
            )
            
            # Should succeed partially
            assert result['total_articles_found'] == 3
            assert result['documents_saved'] >= 2  # At least the valid articles
            
            # Should create files for valid articles
            md_files = list(Path(temp_dir).rglob("*.md"))
            assert len(md_files) >= 2
            
            # Files should contain valid content
            for md_file in md_files:
                with open(md_file, 'r') as f:
                    content = f.read()
                assert 'Valid Article' in content or content.strip() != ''


class TestRealComponentInteractions:
    """Test real interactions between ETL components."""
    
    @pytest.mark.asyncio
    async def test_query_generation_to_collection_integration(self, realistic_client_context):
        """Test real integration from query generation through to document collection."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = PolicyLandscapeCollector(
                exa_api_key="test_key",
                client_context_path=realistic_client_context,
                storage_type="local"
            )
            
            # Test real query generation
            stats = await collector.get_collection_stats()
            
            # Should generate realistic queries based on client context
            assert stats['total_queries'] > 0
            assert stats['validation']['is_valid']
            
            # Queries should reflect client context
            categories = stats['categories']
            assert len(categories) > 0
            
            # Should include AI and data protection related queries
            category_names = list(categories.keys())
            ai_related = any('ai' in cat.lower() or 'data' in cat.lower() 
                           for cat in category_names)
            assert ai_related, f"Should include AI/data related categories, got: {category_names}"
    
    @pytest.mark.asyncio
    async def test_deduplication_across_collection_runs(self, realistic_client_context):
        """Test real deduplication behavior across multiple collection runs."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = PolicyLandscapeCollector(
                exa_api_key="test_key",
                client_context_path=realistic_client_context,
                storage_type="local"
            )
            
            collector.storage = LocalStorage(base_path=temp_dir)
            
            # Same articles returned by API
            same_articles = [
                {
                    'title': 'EU Policy Update',
                    'url': 'https://ec.europa.eu/policy-update',
                    'content': 'Policy content...',
                    'published_date': '2024-03-15T10:00:00Z',
                    'author': 'EU Commission',
                    'source': 'ec.europa.eu'
                }
            ]
            
            collector.exa_collector.collect_news = AsyncMock(return_value=same_articles)
            
            # First collection run
            result1 = await collector.collect_policy_documents(
                days_back=7,
                max_results_per_query=5,
                max_concurrent_queries=1
            )
            
            # Second collection run (same articles)
            result2 = await collector.collect_policy_documents(
                days_back=7,
                max_results_per_query=5,
                max_concurrent_queries=1
            )
            
            # Should find articles but not duplicate them
            assert result1['documents_saved'] == 1
            assert result2['documents_saved'] == 0  # Should be deduplicated
            
            # Should only have one file
            md_files = list(Path(temp_dir).rglob("*.md"))
            assert len(md_files) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])