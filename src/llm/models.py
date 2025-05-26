"""LLM-specific models for enhanced analysis."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LANGFUSE = "langfuse"  # For prompt management
    LOCAL = "local"  # For local models
    MOCK = "mock"  # For testing and fallback


class DocumentInsight(BaseModel):
    """LLM-generated insights about a document."""

    provider: LLMProvider = Field(default=LLMProvider.MOCK)
    key_topics: list[str] = Field(default_factory=list, description="Key topics identified")
    sentiment: str = Field(default="neutral", description="Document sentiment")
    urgency_level: str = Field(default="medium", description="Urgency level assessment")
    confidence: float = Field(default=0.6, ge=0, le=1, description="Analysis confidence")
    summary: str = Field(default="", description="Brief document summary")


class SemanticScore(BaseModel):
    """LLM-generated semantic scoring."""

    provider: LLMProvider = Field(default=LLMProvider.MOCK)
    semantic_score: float = Field(ge=0, le=100, description="LLM semantic score 0-100")
    confidence: float = Field(ge=0, le=1, description="LLM confidence in scoring")
    reasoning: str = Field(description="LLM explanation for the score")
    key_factors: list[str] = Field(
        default_factory=list, description="Key factors influencing the score"
    )


class TopicAnalysis(BaseModel):
    """LLM-powered topic analysis."""

    topic_name: str
    document_indices: list[int] = Field(
        default_factory=list, description="Document indices in this cluster"
    )
    confidence: float = Field(default=0.8, ge=0, le=1, description="Clustering confidence")
    description: str = Field(description="Description of the topic cluster")

    # Additional fields used in base_client.py
    topic_description: Optional[str] = Field(default=None, description="Detailed topic description")
    relevance_score: Optional[float] = Field(
        default=None, description="Relevance score for this topic"
    )
    key_concepts: Optional[list[str]] = Field(
        default_factory=list, description="Key concepts in this topic"
    )
    related_regulations: Optional[list[str]] = Field(
        default_factory=list, description="Related regulations"
    )
    business_implications: Optional[str] = Field(default=None, description="Business implications")


class LLMReportInsights(BaseModel):
    """LLM-generated insights for reports."""

    executive_summary: str = Field(description="LLM-generated executive summary")
    key_findings: list[str] = Field(description="Top insights from analysis")
    recommendations: list[str] = Field(
        default_factory=list, description="Strategic action recommendations"
    )
    risk_assessment: str = Field(description="Overall risk assessment")
    confidence: float = Field(default=0.8, ge=0, le=1, description="Analysis confidence")

    # Additional fields used in base_client.py
    strategic_recommendations: Optional[list[str]] = Field(
        default_factory=list, description="Strategic recommendations"
    )
    priority_rationale: Optional[str] = Field(default=None, description="Priority rationale")
    market_context: Optional[str] = Field(default=None, description="Market context")

    # Optional fields that the LLM might include
    strategic_implications: Optional[dict[str, str]] = Field(
        default=None, description="Strategic implications breakdown"
    )

    model_config = ConfigDict(extra="ignore")


class LLMAnalysisRequest(BaseModel):
    """Request structure for LLM analysis."""

    document_text: str
    context: dict[str, Any]
    analysis_type: str = Field(description="Type of analysis requested")
    max_tokens: Optional[int] = Field(default=1000, description="Maximum tokens for response")
    temperature: Optional[float] = Field(default=0.3, description="LLM temperature setting")


class LLMResponse(BaseModel):
    """Generic LLM response wrapper."""

    content: str
    tokens_used: Optional[int] = None
    model_used: Optional[str] = None
    provider: LLMProvider
    processing_time_ms: float
    success: bool = True
    error_message: Optional[str] = None
