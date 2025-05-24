"""
Unit tests for LLM integration components.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from src.llm.service import LLMService
from src.llm.base_client import MockLLMClient
from src.llm.providers.openai_client import OpenAIClient
from src.llm.providers.anthropic_client import AnthropicClient
from src.llm.models import DocumentInsight, SemanticScore, LLMProvider
from src.scoring.hybrid_engine import HybridScoringEngine
from src.models.content import ProcessedContent
from src.models.scoring import ScoringResult


class TestLLMService:
    """Test LLM service functionality."""
    
    @pytest.fixture
    def mock_context(self) -> Dict[str, Any]:
        return {
            "company_terms": ["tech", "software"],
            "core_industries": ["technology"],
            "primary_markets": ["US", "EU"],
            "strategic_themes": ["innovation", "growth"]
        }
    
    @pytest.fixture
    def llm_service(self) -> LLMService:
        """Create LLM service with mock setup."""
        service = LLMService()
        service.enabled = False  # Start with disabled for controlled testing
        return service
    
    @pytest.mark.asyncio
    async def test_analyze_document_fallback(self, llm_service, mock_context):
        """Test document analysis falls back to mock when LLM disabled."""
        result = await llm_service.analyze_document("test document", mock_context)
        
        assert isinstance(result, DocumentInsight)
        assert result.confidence >= 0.0
        assert result.confidence <= 1.0
        assert len(result.key_topics) > 0
        assert result.sentiment in ["positive", "negative", "neutral"]
    
    @pytest.mark.asyncio
    async def test_score_dimension_fallback(self, llm_service, mock_context):
        """Test semantic scoring falls back to mock when LLM disabled."""
        result = await llm_service.score_dimension_semantic(
            "test text", "direct_impact", mock_context, 75.0
        )
        
        assert isinstance(result, SemanticScore)
        assert 0.0 <= result.semantic_score <= 100.0
        assert 0.0 <= result.confidence <= 1.0
        assert len(result.reasoning) > 0
    
    @pytest.mark.asyncio 
    @patch('src.llm.service.settings')
    async def test_llm_service_initialization(self, mock_settings):
        """Test LLM service initializes correctly with different configs."""
        # Test with Anthropic configuration
        mock_settings.LLM_ENABLED = True
        mock_settings.ANTHROPIC_API_KEY = "test-key"
        mock_settings.ANTHROPIC_MODEL = "claude-3-haiku-20240307"
        mock_settings.OPENAI_API_KEY = None
        
        with patch('src.llm.providers.anthropic_client.AnthropicClient') as mock_client:
            mock_client.return_value = MagicMock()
            service = LLMService()
            
            assert service.enabled is True
            mock_client.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_concurrent_execution(self, llm_service, mock_context):
        """Test concurrent LLM operations work correctly."""
        # Run multiple operations concurrently
        tasks = [
            llm_service.analyze_document(f"document {i}", mock_context)
            for i in range(3)
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        for result in results:
            assert isinstance(result, DocumentInsight)


class TestMockLLMClient:
    """Test mock LLM client provides consistent fallback behavior."""
    
    @pytest.fixture
    def mock_client(self) -> MockLLMClient:
        return MockLLMClient()
    
    @pytest.fixture
    def mock_context(self) -> Dict[str, Any]:
        return {
            "company_terms": ["finance", "banking"],
            "core_industries": ["financial_services"],
            "primary_markets": ["US"],
            "strategic_themes": ["digital_transformation"]
        }
    
    @pytest.mark.asyncio
    async def test_mock_analyze_document(self, mock_client, mock_context):
        """Test mock document analysis returns valid results."""
        result = await mock_client.analyze_document("Banking regulation document", mock_context)
        
        assert isinstance(result, DocumentInsight)
        assert result.provider == LLMProvider.MOCK
        assert len(result.key_topics) > 0
        assert result.sentiment in ["positive", "negative", "neutral"]
        assert 0.5 <= result.confidence <= 0.8  # Mock confidence range
    
    @pytest.mark.asyncio
    async def test_mock_score_dimension(self, mock_client, mock_context):
        """Test mock semantic scoring."""
        result = await mock_client.score_dimension(
            "New banking regulations affect digital payments",
            "industry_relevance",
            mock_context,
            80.0
        )
        
        assert isinstance(result, SemanticScore)
        assert result.provider == LLMProvider.MOCK
        # Mock should adjust score based on rule-based input
        assert 70.0 <= result.semantic_score <= 90.0
        assert 0.5 <= result.confidence <= 0.8
    
    @pytest.mark.asyncio
    async def test_mock_consistency(self, mock_client, mock_context):
        """Test mock client provides consistent results for same input."""
        text = "Technology innovation in financial services"
        
        result1 = await mock_client.analyze_document(text, mock_context)
        result2 = await mock_client.analyze_document(text, mock_context)
        
        # Should be similar but not identical (some randomness for realism)
        assert result1.sentiment == result2.sentiment
        assert abs(result1.confidence - result2.confidence) < 0.1


class TestHybridScoringEngine:
    """Test hybrid scoring engine combining rule-based and LLM scoring."""
    
    @pytest.fixture
    def sample_document(self) -> ProcessedContent:
        return ProcessedContent(
            id="test-doc-1",
            title="Technology Investment Policy",
            raw_text="Government announces new technology investment incentives for startups",
            content_type="text/plain",
            source_path="/test/doc.txt",
            processing_metadata={
                "word_count": 15,
                "language": "en"
            }
        )
    
    @pytest.fixture
    def hybrid_context(self) -> Dict[str, Any]:
        return {
            "company_terms": ["technology", "startups"],
            "core_industries": ["technology"],
            "primary_markets": ["US"],
            "strategic_themes": ["investment", "innovation"]
        }
    
    @pytest.mark.asyncio
    async def test_hybrid_scoring_with_llm_disabled(self, sample_document, hybrid_context):
        """Test hybrid engine works when LLM is disabled."""
        engine = HybridScoringEngine(hybrid_context)
        
        result = await engine.score_document_hybrid(sample_document)
        
        assert isinstance(result, ScoringResult)
        assert result.document_id == "test-doc-1"
        assert hasattr(result, 'master_score')
        assert 0.0 <= result.master_score <= 100.0
        
        # Should have rule-based scores
        assert 'direct_impact' in result.dimension_scores
        assert 'industry_relevance' in result.dimension_scores
    
    @pytest.mark.asyncio
    @patch('src.llm.service.LLMService')
    async def test_hybrid_scoring_with_llm_enabled(self, mock_llm_service, sample_document, hybrid_context):
        """Test hybrid engine with mocked LLM enabled."""
        # Setup mock LLM service
        mock_service = AsyncMock()
        mock_service.enabled = True
        
        # Mock document insights
        mock_insights = DocumentInsight(
            provider=LLMProvider.MOCK,
            key_topics=["technology", "policy"],
            sentiment="positive",
            urgency_level="medium",
            confidence=0.85,
            summary="Policy about technology investment incentives"
        )
        mock_service.analyze_document.return_value = mock_insights
        
        # Mock semantic scores
        mock_semantic_score = SemanticScore(
            provider=LLMProvider.MOCK,
            semantic_score=82.0,
            confidence=0.8,
            reasoning="Strong relevance to technology sector",
            key_factors=["technology focus", "investment theme"]
        )
        mock_service.score_dimension_semantic.return_value = mock_semantic_score
        
        mock_llm_service.return_value = mock_service
        
        engine = HybridScoringEngine(hybrid_context)
        result = await engine.score_document_hybrid(sample_document)
        
        assert isinstance(result, ScoringResult)
        assert result.master_score > 0.0
        
        # Should have called LLM service
        mock_service.analyze_document.assert_called_once()
        # Should have called semantic scoring for each dimension
        assert mock_service.score_dimension_semantic.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_hybrid_batch_processing(self, hybrid_context):
        """Test batch processing of documents."""
        documents = [
            ProcessedContent(
                id=f"doc-{i}",
                title=f"Document {i}",
                raw_text=f"Content of document {i}",
                content_type="text/plain",
                source_path=f"/test/doc{i}.txt",
                processing_metadata={"word_count": 10}
            )
            for i in range(3)
        ]
        
        engine = HybridScoringEngine(hybrid_context)
        results = await engine.score_documents_batch(documents)
        
        assert len(results) == 3
        for result in results:
            assert isinstance(result, ScoringResult)
            assert result.master_score >= 0.0


class TestLangfuseIntegration:
    """Test Langfuse integration functionality."""
    
    @pytest.mark.asyncio
    @patch('src.integrations.langfuse_client.asyncio.to_thread')
    async def test_langfuse_trace_creation(self, mock_to_thread):
        """Test Langfuse trace creation with fallback."""
        from src.integrations.langfuse_client import langfuse_client
        
        # Mock successful trace creation
        mock_trace = MagicMock()
        mock_trace.id = "test-trace-123"
        mock_to_thread.return_value = mock_trace
        
        async with langfuse_client.trace("test_operation") as trace:
            assert trace is not None
            trace.update_output({"result": "success"})
    
    @pytest.mark.asyncio 
    async def test_langfuse_fallback_mode(self):
        """Test Langfuse works in fallback mode when not configured."""
        from src.integrations.langfuse_client import langfuse_client
        
        # Reset initialization state for clean test
        langfuse_client._initialization_attempted = False
        langfuse_client._available = False
        
        async with langfuse_client.trace("test_operation") as trace:
            # Should work even when Langfuse is not available
            assert trace is not None
            trace.update_output({"result": "fallback_success"})
    
    @pytest.mark.asyncio
    async def test_langfuse_prompt_fallback(self):
        """Test prompt retrieval with fallback."""
        from src.integrations.langfuse_client import langfuse_client
        
        fallback_prompt = "Default prompt content"
        
        result = await langfuse_client.get_prompt(
            "test_prompt",
            fallback_prompt=fallback_prompt
        )
        
        # Should return fallback when Langfuse unavailable
        assert result == fallback_prompt


@pytest.mark.integration
class TestEndToEndLLMFlow:
    """Integration tests for complete LLM workflow."""
    
    @pytest.mark.asyncio
    async def test_complete_document_processing_flow(self):
        """Test complete flow from document to LLM-enhanced scoring."""
        # Create test document
        document = ProcessedContent(
            id="integration-test-doc",
            title="AI Regulation Impact Assessment", 
            raw_text="New artificial intelligence regulations require companies to implement ethical AI frameworks for automated decision-making systems.",
            content_type="text/plain",
            source_path="/test/ai_regulation.txt",
            processing_metadata={
                "word_count": 20,
                "language": "en",
                "processing_time_ms": 150
            }
        )
        
        # Test context
        context = {
            "company_terms": ["AI", "artificial intelligence", "automated"],
            "core_industries": ["technology", "software"],
            "primary_markets": ["US", "EU"],
            "strategic_themes": ["compliance", "ethics", "regulation"]
        }
        
        # Create hybrid scoring engine (will use mock LLM)
        engine = HybridScoringEngine(context)
        
        # Process document
        result = await engine.score_document_hybrid(document)
        
        # Verify complete result structure
        assert isinstance(result, ScoringResult)
        assert result.document_id == "integration-test-doc"
        assert result.master_score >= 0.0
        assert result.master_score <= 100.0
        
        # Should have all dimension scores
        expected_dimensions = [
            "direct_impact", "industry_relevance", "geographic_relevance", 
            "temporal_urgency", "strategic_alignment"
        ]
        for dimension in expected_dimensions:
            assert dimension in result.dimension_scores
            score = result.dimension_scores[dimension]
            assert 0.0 <= score <= 100.0
        
        # Should have justification
        assert result.justification is not None
        assert len(result.justification) > 0
        
        # Should have confidence score
        assert hasattr(result, 'confidence')
        assert result.processing_time_ms > 0