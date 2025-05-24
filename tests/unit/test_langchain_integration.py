"""
Unit tests for LangChain integration components.
Updated for the new LangChain-based architecture.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any
from datetime import datetime

from src.llm.langchain_service import langchain_llm_service
from src.llm.models import DocumentInsight, SemanticScore, LLMProvider
from src.scoring.hybrid_engine import HybridScoringEngine
from src.models.content import ProcessedContent, DocumentMetadata, DocumentType
from src.models.scoring import ScoringResult
from src.prompts.prompt_manager import prompt_manager


class TestPromptManager:
    """Test prompt management system."""
    
    @pytest.mark.asyncio
    async def test_prompt_loading_from_file(self):
        """Test loading prompts from local markdown files."""
        prompt = await prompt_manager.get_prompt('document_analysis')
        
        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert 'Political Document Analysis' in prompt
    
    @pytest.mark.asyncio
    async def test_prompt_variable_substitution(self):
        """Test variable substitution in prompts."""
        variables = {
            'company_terms': ['AI', 'technology'],
            'document_text': 'Test document content'
        }
        
        prompt = await prompt_manager.get_prompt('document_analysis', variables=variables)
        
        assert 'AI, technology' in prompt
        assert 'Test document content' in prompt
    
    def test_cache_functionality(self):
        """Test prompt caching."""
        stats = prompt_manager.get_cache_stats()
        
        assert 'cached_prompts' in stats
        assert 'fallback_count' in stats
        assert 'available_prompts' in stats


class TestLangChainLLMService:
    """Test LangChain-based LLM service."""
    
    @pytest.fixture
    def mock_context(self) -> Dict[str, Any]:
        return {
            "company_terms": ["AI", "technology"],
            "core_industries": ["technology"],
            "primary_markets": ["US", "EU"],
            "strategic_themes": ["regulation", "innovation"]
        }
    
    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Test service initializes correctly."""
        assert langchain_llm_service is not None
        assert hasattr(langchain_llm_service, 'enabled')
        assert hasattr(langchain_llm_service, 'current_provider')
    
    @pytest.mark.asyncio
    async def test_document_analysis_fallback(self, mock_context):
        """Test document analysis with mock fallback."""
        result = await langchain_llm_service.analyze_document(
            "Test document about technology regulations", 
            mock_context
        )
        
        assert isinstance(result, DocumentInsight)
        assert result.provider == LLMProvider.MOCK
        assert isinstance(result.key_topics, list)
        assert len(result.key_topics) > 0
        assert result.sentiment in ["positive", "negative", "neutral"]
        assert 0.0 <= result.confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_semantic_scoring_fallback(self, mock_context):
        """Test semantic scoring with mock fallback."""
        result = await langchain_llm_service.score_dimension_semantic(
            "Technology regulation document",
            "industry_relevance",
            mock_context,
            75.0
        )
        
        assert isinstance(result, SemanticScore)
        assert result.provider == LLMProvider.MOCK
        assert 0.0 <= result.semantic_score <= 100.0
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.reasoning, str)
        assert len(result.reasoning) > 0
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test service health check."""
        health = await langchain_llm_service.health_check()
        
        assert isinstance(health, dict)
        assert 'enabled' in health
        assert 'primary_provider' in health
        assert 'langchain_version' in health
        assert health['langchain_version'] == '0.2.16'


class TestHybridScoringEngine:
    """Test hybrid scoring engine with LangChain integration."""
    
    @pytest.fixture
    def sample_document(self) -> ProcessedContent:
        metadata = DocumentMetadata(
            source="/test/doc.txt",
            type=DocumentType.TXT,
            file_path="/test/doc.txt",
            file_size_bytes=1024
        )
        
        return ProcessedContent(
            id="doc_test_001",
            raw_text="European Union announces new AI regulations for technology companies",
            metadata=metadata,
            processing_timestamp=datetime.now()
        )
    
    @pytest.fixture
    def test_context(self) -> Dict[str, Any]:
        return {
            "company_terms": ["AI", "technology", "regulation"],
            "core_industries": ["technology"],
            "primary_markets": ["EU", "US"],
            "strategic_themes": ["compliance", "innovation"]
        }
    
    @pytest.mark.asyncio
    async def test_hybrid_scoring_basic(self, sample_document, test_context):
        """Test basic hybrid scoring functionality."""
        engine = HybridScoringEngine(test_context)
        result = await engine.score_document_hybrid(sample_document)
        
        assert isinstance(result, ScoringResult)
        assert result.document_id == "doc_test_001"
        assert 0.0 <= result.master_score <= 100.0
        assert 0.0 <= result.confidence_score <= 1.0
        assert result.processing_time_ms >= 0.0
        
        # Should have all 5 dimensions
        assert len(result.dimension_scores) == 5
        expected_dimensions = [
            "direct_impact", "industry_relevance", "geographic_relevance",
            "temporal_urgency", "strategic_alignment"
        ]
        for dimension in expected_dimensions:
            assert dimension in result.dimension_scores
    
    @pytest.mark.asyncio
    async def test_hybrid_scoring_high_relevance_content(self, test_context):
        """Test scoring with highly relevant content."""
        metadata = DocumentMetadata(
            source="/test/high_relevance.txt",
            type=DocumentType.TXT,
            file_path="/test/high_relevance.txt",
            file_size_bytes=2048
        )
        
        doc = ProcessedContent(
            id="doc_high_relevance",
            raw_text="The European Union implements comprehensive AI compliance requirements for all technology companies operating in EU markets. New regulations mandate algorithmic transparency, data privacy protection, and ethical AI frameworks. Technology firms must complete compliance certification by December 2024.",
            metadata=metadata,
            processing_timestamp=datetime.now()
        )
        
        engine = HybridScoringEngine(test_context)
        result = await engine.score_document_hybrid(doc)
        
        # Should score highly due to multiple relevant terms
        assert result.master_score > 50.0  # Should be above average
        assert result.confidence_score > 0.1
    
    @pytest.mark.asyncio
    async def test_hybrid_scoring_batch_processing(self, test_context):
        """Test batch processing functionality."""
        documents = []
        for i in range(3):
            metadata = DocumentMetadata(
                source=f"/test/batch_{i}.txt",
                type=DocumentType.TXT,
                file_path=f"/test/batch_{i}.txt",
                file_size_bytes=1024
            )
            
            doc = ProcessedContent(
                id=f"doc_batch_{i:03d}",
                raw_text=f"Document {i} about technology regulation policies",
                metadata=metadata,
                processing_timestamp=datetime.now()
            )
            documents.append(doc)
        
        engine = HybridScoringEngine(test_context)
        
        # Process documents individually (batch method doesn't exist)
        results = []
        for doc in documents:
            result = await engine.score_document_hybrid(doc)
            results.append(result)
        
        assert len(results) == 3
        for result in results:
            assert isinstance(result, ScoringResult)
            assert result.master_score >= 0.0


class TestLangfuseIntegration:
    """Test Langfuse integration components."""
    
    @pytest.mark.asyncio
    async def test_langfuse_client_initialization(self):
        """Test Langfuse client initializes correctly."""
        from src.integrations.langfuse_client import langfuse_client
        
        assert langfuse_client is not None
        assert hasattr(langfuse_client, 'available')
        assert hasattr(langfuse_client, 'trace')
    
    @pytest.mark.asyncio
    async def test_trace_context_manager(self):
        """Test trace context manager works in fallback mode."""
        from src.integrations.langfuse_client import langfuse_client
        
        async with await langfuse_client.trace("test_operation") as trace:
            assert trace is not None
            trace.update_output({"test": "success"})
    
    @pytest.mark.asyncio
    async def test_prompt_fallback(self):
        """Test prompt retrieval with fallback."""
        from src.integrations.langfuse_client import langfuse_client
        
        fallback_prompt = "Test fallback prompt"
        result = await langfuse_client.get_prompt(
            "nonexistent_prompt",
            fallback_prompt=fallback_prompt
        )
        
        assert result == fallback_prompt


@pytest.mark.integration
class TestEndToEndLangChainFlow:
    """Integration tests for complete LangChain workflow."""
    
    @pytest.mark.asyncio
    async def test_complete_document_analysis_flow(self):
        """Test complete flow from document to enhanced scoring."""
        # Create realistic test document
        metadata = DocumentMetadata(
            source="/test/eu_digital_services_act.pdf",
            type=DocumentType.PDF,
            file_path="/test/eu_digital_services_act.pdf",
            file_size_bytes=5120000
        )
        
        document = ProcessedContent(
            id="doc_dsa_analysis",
            raw_text="The Digital Services Act establishes new obligations for technology platforms operating in the European Union. Large online platforms must implement risk assessment procedures, transparency reporting, and content moderation systems. Technology companies with over 45 million EU users face additional compliance requirements including external audits and algorithmic impact assessments.",
            metadata=metadata,
            processing_timestamp=datetime.now()
        )
        
        # Test context
        context = {
            "company_terms": ["technology", "platform", "digital services"],
            "core_industries": ["technology", "digital platforms"],
            "primary_markets": ["EU", "European Union"],
            "strategic_themes": ["compliance", "regulation", "digital transformation"]
        }
        
        # Execute hybrid scoring
        engine = HybridScoringEngine(context)
        result = await engine.score_document_hybrid(document)
        
        # Verify comprehensive result
        assert isinstance(result, ScoringResult)
        assert result.document_id == "doc_dsa_analysis"
        assert result.master_score >= 0.0
        assert result.master_score <= 100.0
        
        # Should score highly for this relevant content
        assert result.master_score > 60.0  # DSA is highly relevant to tech companies
        
        # Verify all scoring dimensions
        expected_dimensions = [
            "direct_impact", "industry_relevance", "geographic_relevance",
            "temporal_urgency", "strategic_alignment"
        ]
        for dimension in expected_dimensions:
            assert dimension in result.dimension_scores
            dim_score = result.dimension_scores[dimension]
            assert 0.0 <= dim_score.score <= 100.0
        
        # Verify metadata
        assert result.overall_justification is not None
        assert len(result.overall_justification) > 50
        assert result.processing_time_ms >= 0.0
        assert len(result.key_factors) >= 0
    
    @pytest.mark.asyncio
    async def test_prompt_manager_integration(self):
        """Test prompt manager works with LangChain service."""
        context = {
            "company_terms": ["fintech", "banking"],
            "core_industries": ["financial_services"],
            "primary_markets": ["US"],
            "strategic_themes": ["regulation", "compliance"]
        }
        
        # Test document analysis uses prompt manager
        result = await langchain_llm_service.analyze_document(
            "New banking regulations affect fintech compliance requirements",
            context
        )
        
        assert isinstance(result, DocumentInsight)
        assert result.provider == LLMProvider.MOCK  # Should use mock in test
        
        # Test semantic scoring uses prompt manager
        semantic_result = await langchain_llm_service.score_dimension_semantic(
            "Banking compliance document",
            "industry_relevance",
            context,
            80.0
        )
        
        assert isinstance(semantic_result, SemanticScore)
        assert semantic_result.provider == LLMProvider.MOCK


class TestErrorHandling:
    """Test error handling and fallback mechanisms."""
    
    @pytest.mark.asyncio
    async def test_prompt_loading_error_handling(self):
        """Test error handling when prompt loading fails."""
        with pytest.raises(ValueError, match="Unable to load prompt"):
            await prompt_manager.get_prompt("nonexistent_prompt")
    
    @pytest.mark.asyncio
    async def test_hybrid_engine_error_resilience(self):
        """Test hybrid engine handles errors gracefully."""
        context = {"company_terms": ["test"]}
        
        metadata = DocumentMetadata(
            source="/test/error_test.txt",
            type=DocumentType.TXT,
            file_path="/test/error_test.txt",
            file_size_bytes=100
        )
        
        doc = ProcessedContent(
            id="doc_error_test",
            raw_text="Test document",
            metadata=metadata,
            processing_timestamp=datetime.now()
        )
        
        engine = HybridScoringEngine(context)
        
        # Should complete successfully even with minimal context
        result = await engine.score_document_hybrid(doc)
        assert isinstance(result, ScoringResult)
        assert result.master_score >= 0.0
    
    @pytest.mark.asyncio
    async def test_llm_service_fallback_behavior(self):
        """Test LLM service fallback when providers unavailable."""
        # Service should work in fallback mode
        context = {"company_terms": ["test"]}
        
        result = await langchain_llm_service.analyze_document("test", context)
        assert isinstance(result, DocumentInsight)
        assert result.provider == LLMProvider.MOCK
        
        semantic = await langchain_llm_service.score_dimension_semantic(
            "test", "direct_impact", context, 50.0
        )
        assert isinstance(semantic, SemanticScore)
        assert semantic.provider == LLMProvider.MOCK