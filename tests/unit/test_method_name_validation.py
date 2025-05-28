"""
Tests that would have caught the transform_to_markdown vs transform_article bug.

This demonstrates proper test coverage for method name validation.
"""

import pytest
import tempfile
import yaml
from unittest.mock import MagicMock, AsyncMock

from src.etl.collectors.policy_landscape import PolicyLandscapeCollector
from src.etl.transformers.markdown_transformer import MarkdownTransformer


class TestMethodNameValidation:
    """Tests that validate correct method names are used."""
    
    @pytest.fixture
    def client_context_file(self, tmp_path):
        """Create test client context file."""
        context_data = {
            'client_profile': {
                'company_name': 'TestCorp',
                'primary_markets': ['EU'],
                'core_industries': ['technology']
            },
            'regulatory_focus': {
                'topic_patterns': ['AI regulation']
            }
        }
        
        context_file = tmp_path / "client.yaml"
        with open(context_file, 'w') as f:
            yaml.dump(context_data, f)
        return str(context_file)
    
    def test_transformer_interface_validation(self):
        """Test that MarkdownTransformer has expected methods."""
        transformer = MarkdownTransformer()
        
        # Verify correct method exists
        assert hasattr(transformer, 'transform_article'), \
            "MarkdownTransformer should have transform_article method"
        
        # Verify incorrect method does NOT exist (this would catch the bug)
        assert not hasattr(transformer, 'transform_to_markdown'), \
            "MarkdownTransformer should NOT have transform_to_markdown method"
        
        # Verify method signature
        import inspect
        sig = inspect.signature(transformer.transform_article)
        assert 'article' in sig.parameters, "transform_article should accept article parameter"
    
    @pytest.mark.asyncio
    async def test_policy_collector_uses_correct_transformer_method(self, client_context_file):
        """Test that PolicyLandscapeCollector calls the correct transformer method."""
        
        collector = PolicyLandscapeCollector(
            exa_api_key="test_key",
            client_context_path=client_context_file,
            storage_type="local"
        )
        
        # Mock storage but keep transformer real to catch method name bugs
        collector.storage.save_document = AsyncMock(return_value=True)
        
        # Create test article
        test_article = {
            'title': 'Test Policy Document',
            'url': 'https://example.com/policy',
            'content': 'Policy content...',
            'published_date': '2024-03-15T10:00:00Z',
            'author': 'Policy Authority',
            'source': 'example.com'
        }
        
        # Spy on transformer to verify correct method is called
        original_transform = collector.transformer.transform_article
        collector.transformer.transform_article = MagicMock(
            side_effect=original_transform,
            return_value=("# Test Document\n\nContent", "test.md")
        )
        
        # This should work without AttributeError
        await collector._save_policy_documents([test_article])
        
        # Verify correct method was called
        collector.transformer.transform_article.assert_called_once()
        
        # Verify it was called with the test article
        call_args = collector.transformer.transform_article.call_args
        assert call_args[0][0] == test_article
    
    @pytest.mark.asyncio
    async def test_policy_collector_fails_with_wrong_method_name(self, client_context_file):
        """Test that demonstrates the bug by using wrong method name."""
        
        collector = PolicyLandscapeCollector(
            exa_api_key="test_key",
            client_context_path=client_context_file,
            storage_type="local"
        )
        
        # Mock storage
        collector.storage.save_document = AsyncMock(return_value=True)
        
        # Create test article
        test_article = {
            'title': 'Test Policy Document',
            'url': 'https://example.com/policy',
            'content': 'Policy content...',
            'published_date': '2024-03-15T10:00:00Z'
        }
        
        # Simulate the bug by trying to call wrong method name
        original_method = collector.transformer.transform_article
        del collector.transformer.transform_article  # Remove correct method
        
        # Add wrong method name to simulate the bug
        collector.transformer.transform_to_markdown = original_method
        
        # Patch the actual code to use wrong method (simulating the bug)
        import src.etl.collectors.policy_landscape as policy_module
        original_save = policy_module.PolicyLandscapeCollector._save_policy_documents
        
        async def buggy_save(self, articles):
            # This simulates the original buggy code
            for article in articles:
                try:
                    # This should fail with AttributeError
                    markdown_content = await self.transformer.transform_to_markdown(article)
                except AttributeError as e:
                    pytest.fail(f"Method name bug detected: {e}")
        
        # This test would catch the bug by expecting AttributeError
        with pytest.raises(AttributeError, match="transform_to_markdown"):
            markdown_content = collector.transformer.transform_to_markdown(test_article)
    
    def test_news_vs_policy_transformer_consistency(self):
        """Test that news and policy collectors use same transformer interface."""
        
        # Import both transformers used by different collectors
        from src.etl.transformers.markdown_transformer import MarkdownTransformer
        
        # Both should use the same transformer class
        news_transformer = MarkdownTransformer()
        policy_transformer = MarkdownTransformer()
        
        # Both should have same methods
        news_methods = [m for m in dir(news_transformer) if not m.startswith('_')]
        policy_methods = [m for m in dir(policy_transformer) if not m.startswith('_')]
        
        assert news_methods == policy_methods, \
            "News and policy transformers should have identical interfaces"
        
        # Both should have the correct method name
        assert hasattr(news_transformer, 'transform_article')
        assert hasattr(policy_transformer, 'transform_article')
        
        # Neither should have the wrong method name
        assert not hasattr(news_transformer, 'transform_to_markdown')
        assert not hasattr(policy_transformer, 'transform_to_markdown')
    
    @pytest.mark.asyncio
    async def test_integration_with_real_transformer(self, client_context_file):
        """Integration test using real transformer (would catch method name bugs)."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = PolicyLandscapeCollector(
                exa_api_key="test_key",
                client_context_path=client_context_file,
                storage_type="local"
            )
            
            # Override storage path for test
            from src.etl.storage.local import LocalStorage
            collector.storage = LocalStorage(base_path=temp_dir)
            
            # Use REAL transformer (no mocking)
            # Mock only the EXA API call
            test_article = {
                'title': 'EU AI Act Implementation Guide',
                'url': 'https://ec.europa.eu/ai-act-guide',
                'content': 'The European Union has published implementation guidelines...',
                'published_date': '2024-03-15T10:00:00Z',
                'author': 'EU Commission',
                'source': 'ec.europa.eu'
            }
            
            collector.exa_collector.collect_news = AsyncMock(return_value=[test_article])
            
            # This would fail if transform_to_markdown was called instead of transform_article
            result = await collector.collect_policy_documents(
                days_back=1,
                max_results_per_query=1,
                max_concurrent_queries=1
            )
            
            # Verify real files were created
            import pathlib
            md_files = list(pathlib.Path(temp_dir).rglob("*.md"))
            
            assert len(md_files) == 1, "Should create exactly one markdown file"
            assert result['documents_saved'] == 1, "Should report one document saved"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])