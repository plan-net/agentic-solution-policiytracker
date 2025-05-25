"""LLM-specific models for enhanced analysis."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


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
    key_topics: List[str] = Field(default_factory=list, description="Key topics identified")
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
    key_factors: List[str] = Field(
        default_factory=list, description="Key factors influencing the score"
    )


class TopicAnalysis(BaseModel):
    """LLM-powered topic analysis."""

    topic_name: str
    document_indices: List[int] = Field(description="Document indices in this cluster")
    confidence: float = Field(ge=0, le=1, description="Clustering confidence")
    description: str = Field(description="Description of the topic cluster")


class LLMReportInsights(BaseModel):
    """LLM-generated insights for reports."""

    executive_summary: str = Field(description="LLM-generated executive summary")
    key_findings: List[str] = Field(description="Top insights from analysis")
    recommendations: List[str] = Field(description="Strategic action recommendations")
    risk_assessment: str = Field(description="Overall risk assessment")
    confidence: float = Field(ge=0, le=1, description="Analysis confidence")
    
    # Optional fields that the LLM might include
    strategic_implications: Optional[Dict[str, str]] = Field(default=None, description="Strategic implications breakdown")
    
    class Config:
        # Allow extra fields that the LLM might return
        extra = "ignore"


class LLMAnalysisRequest(BaseModel):
    """Request structure for LLM analysis."""

    document_text: str
    context: Dict[str, Any]
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
