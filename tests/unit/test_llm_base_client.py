"""
Unit tests for LLM base client implementation.
Tests both the abstract base class interface and the MockLLMClient implementation.
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import AsyncMock, patch

from src.llm.base_client import BaseLLMClient, MockLLMClient
from src.llm.models import (
    LLMProvider,
    LLMResponse,
    DocumentInsight,
    SemanticScore,
    TopicAnalysis,
    LLMReportInsights,
)


class TestBaseLLMClientInterface:
    """Test the abstract base class interface."""
    
    def test_base_client_initialization(self):
        """Test BaseLLMClient initialization with provider and config."""
        # Create a concrete implementation for testing
        class TestClient(BaseLLMClient):
            async def complete(self, prompt: str, **kwargs) -> LLMResponse:
                pass
            async def analyze_document(self, text: str, context: Dict[str, Any]) -> DocumentInsight:
                pass
            async def score_dimension(self, text: str, dimension: str, context: Dict[str, Any], rule_based_score: float) -> SemanticScore:
                pass
            async def analyze_topics(self, documents: List[str]) -> List[TopicAnalysis]:
                pass
            async def generate_report_insights(self, scoring_results: List[Dict[str, Any]], context: Dict[str, Any]) -> LLMReportInsights:
                pass
        
        client = TestClient(
            provider=LLMProvider.OPENAI,
            api_key="test-key",
            model="gpt-3.5-turbo"
        )
        
        assert client.provider == LLMProvider.OPENAI
        assert client.config["api_key"] == "test-key"
        assert client.config["model"] == "gpt-3.5-turbo"
    
    def test_base_client_abstract_methods(self):
        """Test that BaseLLMClient cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseLLMClient(LLMProvider.MOCK)


class TestMockLLMClient:
    """Test MockLLMClient implementation."""
    
    @pytest.fixture
    def mock_client(self):
        """Create MockLLMClient instance for testing."""
        return MockLLMClient()
    
    @pytest.fixture
    def sample_context(self):
        """Sample context for testing."""
        return {
            "company_terms": ["test-company", "acme corp"],
            "core_industries": ["technology", "software"],
            "primary_markets": ["US", "EU"],
            "strategic_themes": ["innovation", "compliance"]
        }
    
    def test_mock_client_initialization(self, mock_client):
        """Test MockLLMClient initialization."""
        assert mock_client.provider == LLMProvider.LOCAL
        assert mock_client.call_count == 0
    
    @pytest.mark.asyncio
    async def test_complete_method_basic(self, mock_client):
        """Test basic completion functionality."""
        prompt = "Analyze this document for scoring purposes"
        
        response = await mock_client.complete(prompt)
        
        assert isinstance(response, LLMResponse)
        assert response.success is True
        assert response.provider == LLMProvider.LOCAL
        assert response.model_used == "mock-llm"
        assert "moderate relevance" in response.content.lower() or "compliance" in response.content.lower()
        assert response.tokens_used > 0
        assert response.processing_time_ms >= 0
        assert mock_client.call_count == 1
    
    @pytest.mark.asyncio
    async def test_complete_method_content_variations(self, mock_client):
        """Test completion responds differently to different prompt types."""
        # Test scoring prompt
        score_response = await mock_client.complete("Score this document")
        assert "relevance" in score_response.content.lower()
        
        # Test analysis prompt
        analysis_response = await mock_client.complete("Analyze the themes")
        assert "themes" in analysis_response.content.lower()
        
        # Test summarization prompt
        summary_response = await mock_client.complete("Summarize the content")
        assert "document" in summary_response.content.lower()
        
        # Test generic prompt
        generic_response = await mock_client.complete("Do something")
        assert "analysis" in generic_response.content.lower()
        
        assert mock_client.call_count == 4
    
    @pytest.mark.asyncio
    async def test_analyze_document_method(self, mock_client, sample_context):
        """Test document analysis functionality."""
        text = "This regulation requires immediate compliance with data protection standards. Companies must implement new security measures or face penalties with a strict deadline."
        
        insight = await mock_client.analyze_document(text, sample_context)
        
        assert isinstance(insight, DocumentInsight)
        assert len(insight.key_topics) > 0
        assert "Regulatory Compliance" in insight.key_topics
        assert "Data Management" in insight.key_topics
        
        assert insight.urgency_level in ["high", "medium", "low"]
        assert insight.sentiment in ["positive", "negative", "neutral"]
        
        assert 0.0 <= insight.confidence <= 1.0
        assert "words" in insight.summary
        assert mock_client.call_count == 1
    
    @pytest.mark.asyncio
    async def test_analyze_document_minimal_content(self, mock_client, sample_context):
        """Test document analysis with minimal content."""
        text = "Brief note"
        
        insight = await mock_client.analyze_document(text, sample_context)
        
        assert isinstance(insight, DocumentInsight)
        assert "General Business" in insight.key_topics
        assert insight.urgency_level == "medium"
        assert insight.confidence >= 0.3  # Minimum confidence
    
    @pytest.mark.asyncio
    async def test_score_dimension_direct_impact(self, mock_client, sample_context):
        """Test semantic scoring for direct impact dimension."""
        text = "Test-company faces new regulations affecting core business operations"
        rule_based_score = 60.0
        
        score = await mock_client.score_dimension(text, "direct_impact", sample_context, rule_based_score)
        
        assert isinstance(score, SemanticScore)
        assert score.semantic_score > rule_based_score  # Should be boosted
        assert "adjustment" in score.reasoning
        assert len(score.key_factors) > 0
        assert 0.0 <= score.confidence <= 1.0
        assert mock_client.call_count == 1
    
    @pytest.mark.asyncio
    async def test_score_dimension_industry_relevance(self, mock_client, sample_context):
        """Test semantic scoring for industry relevance dimension."""
        text = "Technology companies and software development businesses face new requirements"
        rule_based_score = 50.0
        
        score = await mock_client.score_dimension(text, "industry_relevance", sample_context, rule_based_score)
        
        # Industry relevance test
        assert score.semantic_score > rule_based_score  # Should be boosted due to industry terms
        assert score.confidence > 0.5  # Should have higher confidence
    
    @pytest.mark.asyncio
    async def test_score_dimension_temporal_urgency(self, mock_client, sample_context):
        """Test semantic scoring for temporal urgency dimension."""
        text = "Urgent action required immediately due to regulatory deadline"
        rule_based_score = 40.0
        
        score = await mock_client.score_dimension(text, "temporal_urgency", sample_context, rule_based_score)
        
        # Temporal urgency test
        assert score.semantic_score >= 60.0  # Should be significantly boosted
        assert score.confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_score_dimension_no_boost(self, mock_client, sample_context):
        """Test semantic scoring with no semantic boost."""
        text = "General content without specific indicators"
        rule_based_score = 45.0
        
        score = await mock_client.score_dimension(text, "geographic_relevance", sample_context, rule_based_score)
        
        # Geographic relevance test
        assert score.semantic_score == rule_based_score  # No boost expected
        assert score.confidence == 0.5  # Lower confidence
    
    @pytest.mark.asyncio
    async def test_score_dimension_boundary_conditions(self, mock_client, sample_context):
        """Test semantic scoring boundary conditions."""
        text = "Test content"
        
        # Test with high rule-based score
        high_score = await mock_client.score_dimension(text, "direct_impact", sample_context, 95.0)
        assert high_score.semantic_score <= 100.0
        
        # Test with low rule-based score
        low_score = await mock_client.score_dimension(text, "direct_impact", sample_context, 5.0)
        assert low_score.semantic_score >= 0.0
    
    @pytest.mark.asyncio
    async def test_analyze_topics_comprehensive(self, mock_client):
        """Test topic analysis with multiple document types."""
        documents = [
            "New regulation requires compliance with data protection standards",
            "Privacy policy updates needed for GDPR compliance",
            "Market analysis shows competitive advantages in technology sector",
            "Business strategy should focus on regulatory compliance"
        ]
        
        topics = await mock_client.analyze_topics(documents)
        
        assert isinstance(topics, list)
        assert len(topics) >= 3  # Should detect multiple topics
        
        topic_names = [topic.topic_name for topic in topics]
        assert "Regulatory Compliance" in topic_names
        assert "Data Privacy" in topic_names
        assert "Market Analysis" in topic_names
        
        # Verify topic structure
        for topic in topics:
            assert isinstance(topic, TopicAnalysis)
            assert topic.relevance_score > 0
            assert len(topic.key_concepts) > 0
            assert len(topic.related_regulations) > 0
            assert topic.business_implications is not None
        
        assert mock_client.call_count == 1
    
    @pytest.mark.asyncio
    async def test_analyze_topics_minimal_content(self, mock_client):
        """Test topic analysis with minimal content."""
        documents = ["Short note", "Brief text"]
        
        topics = await mock_client.analyze_topics(documents)
        
        assert len(topics) == 1
        assert topics[0].topic_name == "General Content"
        assert topics[0].relevance_score == 50.0
    
    @pytest.mark.asyncio
    async def test_generate_report_insights(self, mock_client, sample_context):
        """Test report insights generation."""
        scoring_results = [
            {"master_score": 85.0, "document_id": "doc1"},
            {"master_score": 65.0, "document_id": "doc2"},
            {"master_score": 90.0, "document_id": "doc3"},
            {"master_score": 45.0, "document_id": "doc4"},
        ]
        
        insights = await mock_client.generate_report_insights(scoring_results, sample_context)
        
        assert isinstance(insights, LLMReportInsights)
        assert "4 documents" in insights.executive_summary
        assert "2 high-priority" in insights.executive_summary  # 85 and 90 >= 75
        
        assert len(insights.key_findings) >= 4
        assert len(insights.strategic_recommendations) >= 4
        
        assert insights.risk_assessment is not None
        assert insights.priority_rationale is not None
        assert insights.market_context is not None
        
        assert mock_client.call_count == 1
    
    @pytest.mark.asyncio
    async def test_generate_report_insights_empty_results(self, mock_client, sample_context):
        """Test report insights with empty scoring results."""
        scoring_results = []
        
        insights = await mock_client.generate_report_insights(scoring_results, sample_context)
        
        assert isinstance(insights, LLMReportInsights)
        assert "0 documents" in insights.executive_summary
        assert "0 high-priority" in insights.executive_summary
    
    @pytest.mark.asyncio
    async def test_call_count_tracking(self, mock_client, sample_context):
        """Test that call count is properly tracked across methods."""
        initial_count = mock_client.call_count
        
        await mock_client.complete("test prompt")
        await mock_client.analyze_document("test text", sample_context)
        await mock_client.score_dimension("test", "direct_impact", sample_context, 50.0)
        await mock_client.analyze_topics(["test doc"])
        await mock_client.generate_report_insights([{"master_score": 75}], sample_context)
        
        assert mock_client.call_count == initial_count + 5


class TestMockLLMClientEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.fixture
    def mock_client(self):
        return MockLLMClient()
    
    @pytest.mark.asyncio
    async def test_empty_text_handling(self, mock_client):
        """Test handling of empty text inputs."""
        empty_insight = await mock_client.analyze_document("", {})
        
        assert isinstance(empty_insight, DocumentInsight)
        assert "General Business" in empty_insight.key_themes
        assert empty_insight.confidence_score >= 0.3
    
    @pytest.mark.asyncio
    async def test_empty_context_handling(self, mock_client):
        """Test handling of empty context."""
        text = "Test document with company terms"
        score = await mock_client.score_dimension(text, "direct_impact", {}, 50.0)
        
        assert isinstance(score, SemanticScore)
        assert score.semantic_score == 50.0  # No boost without context
    
    @pytest.mark.asyncio
    async def test_invalid_dimension_handling(self, mock_client):
        """Test handling of unknown dimensions."""
        score = await mock_client.score_dimension("test", "unknown_dimension", {}, 50.0)
        
        assert score.dimension_name == "unknown_dimension"
        assert score.semantic_score == 50.0  # No adjustment
        assert score.confidence == 0.5
    
    @pytest.mark.asyncio
    async def test_extreme_rule_based_scores(self, mock_client):
        """Test handling of extreme rule-based scores."""
        context = {"company_terms": ["test"]}
        text = "test company regulation"
        
        # Test with score that would exceed 100 after boost
        high_score = await mock_client.score_dimension(text, "direct_impact", context, 95.0)
        assert high_score.semantic_score <= 100.0
        
        # Test with negative score
        negative_score = await mock_client.score_dimension(text, "direct_impact", context, -10.0)
        assert negative_score.semantic_score >= 0.0


class TestMockLLMClientIntegration:
    """Integration tests for MockLLMClient with realistic scenarios."""
    
    @pytest.fixture
    def mock_client(self):
        return MockLLMClient()
    
    @pytest.fixture
    def realistic_context(self):
        return {
            "company_terms": ["acme corporation", "acme", "acme corp"],
            "core_industries": ["financial services", "banking", "fintech"],
            "primary_markets": ["united states", "european union", "uk"],
            "strategic_themes": ["digital transformation", "regulatory compliance", "customer experience"]
        }
    
    @pytest.mark.asyncio
    async def test_end_to_end_document_processing(self, mock_client, realistic_context):
        """Test complete document processing workflow."""
        document_text = """
        ACME Corporation faces new financial services regulations in the European Union.
        The regulations require immediate compliance with enhanced data protection standards.
        Banks and fintech companies must implement new security measures before the December deadline.
        Failure to comply will result in significant penalties and regulatory sanctions.
        """
        
        # Step 1: Analyze document
        insight = await mock_client.analyze_document(document_text, realistic_context)
        
        assert "Regulatory Compliance" in insight.key_topics
        assert "Data Management" in insight.key_topics
        assert insight.urgency_level in ["high", "medium", "low"]
        
        # Step 2: Score multiple dimensions
        direct_impact_score = await mock_client.score_dimension(
            document_text, "direct_impact", realistic_context, 60.0
        )
        industry_score = await mock_client.score_dimension(
            document_text, "industry_relevance", realistic_context, 55.0
        )
        urgency_score = await mock_client.score_dimension(
            document_text, "temporal_urgency", realistic_context, 45.0
        )
        
        # Should all be boosted due to relevant content
        assert direct_impact_score.semantic_score > 60.0
        assert industry_score.semantic_score > 55.0
        assert urgency_score.semantic_score > 45.0
        
        # Step 3: Generate topics for multiple documents
        documents = [document_text, "General business update", "Privacy policy changes for GDPR"]
        topics = await mock_client.analyze_topics(documents)
        
        assert len(topics) >= 2
        topic_names = [t.topic_name for t in topics]
        assert "Regulatory Compliance" in topic_names
        
        # Step 4: Generate report insights
        scoring_results = [
            {"master_score": direct_impact_score.hybrid_score, "document_id": "doc1"},
            {"master_score": 45.0, "document_id": "doc2"},
            {"master_score": 80.0, "document_id": "doc3"}
        ]
        
        insights = await mock_client.generate_report_insights(scoring_results, realistic_context)
        
        assert "3 documents" in insights.executive_summary
        assert len(insights.key_findings) >= 4
        assert len(insights.strategic_recommendations) >= 4
        
        # Verify all methods were called
        assert mock_client.call_count == 6