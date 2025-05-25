"""Base LLM client interface and implementation."""

import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

import structlog

from src.llm.models import (
    LLMProvider,
    LLMResponse,
    DocumentInsight,
    SemanticScore,
    TopicAnalysis,
    LLMReportInsights,
    LLMAnalysisRequest,
)

logger = structlog.get_logger()


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    def __init__(self, provider: LLMProvider, **kwargs):
        self.provider = provider
        self.config = kwargs

    @abstractmethod
    async def complete(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate completion from prompt."""
        pass

    @abstractmethod
    async def analyze_document(self, text: str, context: Dict[str, Any]) -> DocumentInsight:
        """Analyze document for insights."""
        pass

    @abstractmethod
    async def score_dimension(
        self, text: str, dimension: str, context: Dict[str, Any], rule_based_score: float
    ) -> SemanticScore:
        """Generate semantic score for a dimension."""
        pass

    @abstractmethod
    async def analyze_topics(self, documents: List[str]) -> List[TopicAnalysis]:
        """Analyze topics across multiple documents."""
        pass

    @abstractmethod
    async def generate_report_insights(
        self, scoring_results: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> LLMReportInsights:
        """Generate insights for report."""
        pass


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing and fallback."""

    def __init__(self):
        super().__init__(LLMProvider.LOCAL)
        self.call_count = 0

    async def complete(self, prompt: str, **kwargs) -> LLMResponse:
        """Mock completion that returns a simple response."""
        self.call_count += 1
        start_time = time.time()

        # Simple mock response based on prompt content
        if "score" in prompt.lower():
            content = "This document shows moderate relevance with some regulatory implications."
        elif "analyze" in prompt.lower():
            content = "Key themes include compliance, regulation, and business impact."
        elif "summarize" in prompt.lower():
            content = "The document discusses regulatory requirements and compliance obligations."
        else:
            content = "Analysis complete with relevant findings identified."

        processing_time = (time.time() - start_time) * 1000

        return LLMResponse(
            content=content,
            tokens_used=len(content.split()),
            model_used="mock-llm",
            provider=self.provider,
            processing_time_ms=processing_time,
            success=True,
        )

    async def analyze_document(self, text: str, context: Dict[str, Any]) -> DocumentInsight:
        """Mock document analysis."""
        self.call_count += 1

        # Extract some basic insights from text
        word_count = len(text.split())

        # Mock analysis based on text content
        key_themes = []
        if "regulation" in text.lower():
            key_themes.append("Regulatory Compliance")
        if "data" in text.lower():
            key_themes.append("Data Management")
        if "market" in text.lower():
            key_themes.append("Market Analysis")
        if not key_themes:
            key_themes.append("General Business")

        regulatory_indicators = []
        if "must comply" in text.lower():
            regulatory_indicators.append("Compliance requirement")
        if "penalty" in text.lower():
            regulatory_indicators.append("Penalty risk")
        if "deadline" in text.lower():
            regulatory_indicators.append("Time-sensitive deadline")

        urgency_signals = []
        if "immediate" in text.lower() or "urgent" in text.lower():
            urgency_signals.append("High urgency")
        if "deadline" in text.lower():
            urgency_signals.append("Time constraint")

        # Confidence based on text length and keyword presence
        confidence = min(0.9, max(0.3, word_count / 1000 + len(key_themes) * 0.1))

        return DocumentInsight(
            provider=self.provider,
            key_topics=key_themes,
            sentiment="neutral" if len(urgency_signals) == 0 else "negative",
            urgency_level="high" if len(urgency_signals) > 0 else "medium",
            confidence=confidence,
            summary=f"Analysis based on {word_count} words with {len(key_themes)} key themes identified",
        )

    async def score_dimension(
        self, text: str, dimension: str, context: Dict[str, Any], rule_based_score: float
    ) -> SemanticScore:
        """Mock semantic scoring."""
        self.call_count += 1

        # Simple semantic scoring logic
        text_lower = text.lower()

        # Boost or reduce score based on semantic indicators
        semantic_adjustment = 0

        if dimension == "direct_impact":
            if any(term in text_lower for term in context.get("company_terms", [])):
                semantic_adjustment = 15
            elif "regulation" in text_lower or "compliance" in text_lower:
                semantic_adjustment = 10

        elif dimension == "industry_relevance":
            if any(industry in text_lower for industry in context.get("core_industries", [])):
                semantic_adjustment = 12
            elif "business" in text_lower or "market" in text_lower:
                semantic_adjustment = 8

        elif dimension == "temporal_urgency":
            if "urgent" in text_lower or "immediate" in text_lower:
                semantic_adjustment = 20
            elif "deadline" in text_lower:
                semantic_adjustment = 15

        # Calculate semantic score
        semantic_score = min(100, max(0, rule_based_score + semantic_adjustment))

        # Hybrid score (weighted combination)
        hybrid_score = (rule_based_score * 0.6) + (semantic_score * 0.4)

        confidence = 0.7 if semantic_adjustment > 0 else 0.5

        return SemanticScore(
            provider=self.provider,
            semantic_score=semantic_score,
            confidence=confidence,
            reasoning=f"Semantic analysis detected {semantic_adjustment} point adjustment for {dimension}",
            key_factors=[f"Evidence found for {dimension} dimension"],
        )

    async def analyze_topics(self, documents: List[str]) -> List[TopicAnalysis]:
        """Mock topic analysis."""
        self.call_count += 1

        # Simple topic extraction based on common words
        all_text = " ".join(documents).lower()

        topics = []

        if "regulation" in all_text or "compliance" in all_text:
            topics.append(
                TopicAnalysis(
                    topic_name="Regulatory Compliance",
                    topic_description="Documents related to regulatory requirements and compliance",
                    relevance_score=85.0,
                    key_concepts=["compliance", "regulation", "requirements"],
                    related_regulations=["GDPR", "Data Protection Laws"],
                    business_implications="High compliance requirements for business operations",
                )
            )

        if "data" in all_text or "privacy" in all_text:
            topics.append(
                TopicAnalysis(
                    topic_name="Data Privacy",
                    topic_description="Documents focusing on data protection and privacy",
                    relevance_score=75.0,
                    key_concepts=["data protection", "privacy", "personal information"],
                    related_regulations=["GDPR", "Data Protection Act"],
                    business_implications="Data handling practices must align with privacy regulations",
                )
            )

        if "market" in all_text or "business" in all_text:
            topics.append(
                TopicAnalysis(
                    topic_name="Market Analysis",
                    topic_description="Business and market-related documents",
                    relevance_score=65.0,
                    key_concepts=["market", "business", "strategy"],
                    related_regulations=["Competition Law", "Market Regulations"],
                    business_implications="Market positioning and competitive considerations",
                )
            )

        if not topics:
            topics.append(
                TopicAnalysis(
                    topic_name="General Content",
                    topic_description="General business content",
                    relevance_score=50.0,
                    key_concepts=["general", "business"],
                    related_regulations=["General Business Law"],
                    business_implications="Standard business considerations apply",
                )
            )

        return topics

    async def generate_report_insights(
        self, scoring_results: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> LLMReportInsights:
        """Mock report insights generation."""
        self.call_count += 1

        total_docs = len(scoring_results)
        high_priority = len([r for r in scoring_results if r.get("master_score", 0) >= 75])
        avg_score = (
            sum(r.get("master_score", 0) for r in scoring_results) / total_docs
            if total_docs > 0
            else 0
        )

        return LLMReportInsights(
            executive_summary=f"Analysis of {total_docs} documents reveals {high_priority} high-priority items with an average relevance score of {avg_score:.1f}. Key regulatory and compliance themes dominate the document set.",
            key_findings=[
                f"Identified {high_priority} high-priority documents requiring immediate attention",
                f"Average relevance score of {avg_score:.1f} indicates moderate to high overall importance",
                "Regulatory compliance themes are prominent across the document set",
                "Several time-sensitive items require prompt action",
            ],
            strategic_recommendations=[
                "Prioritize review of high-scoring documents within 48 hours",
                "Establish compliance monitoring process for ongoing requirements",
                "Develop response protocols for urgent regulatory changes",
                "Create stakeholder communication plan for key findings",
            ],
            risk_assessment="Moderate risk profile with several high-impact regulatory requirements identified. Immediate action required for compliance-related items.",
            priority_rationale="Prioritization based on regulatory impact, business relevance, and temporal urgency. High-scoring items pose significant compliance or business risks.",
            market_context="Current regulatory environment shows increased focus on compliance and data protection. Market trends indicate continued regulatory evolution.",
        )
