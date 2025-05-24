"""OpenAI LLM client implementation."""

import json
import time
from typing import Dict, List, Optional, Any

import httpx
import structlog

from src.llm.base_client import BaseLLMClient
from src.llm.models import (
    LLMProvider, LLMResponse, DocumentInsight, SemanticScore, 
    TopicAnalysis, LLMReportInsights
)

logger = structlog.get_logger()


class OpenAIClient(BaseLLMClient):
    """OpenAI API client for LLM operations."""
    
    def __init__(self, api_key: str, model: str = "gpt-4", **kwargs):
        super().__init__(LLMProvider.OPENAI, **kwargs)
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1"
        
    async def _make_request(self, messages: List[Dict], **kwargs) -> LLMResponse:
        """Make request to OpenAI API."""
        start_time = time.time()
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.3),
            "max_tokens": kwargs.get("max_tokens", 1000)
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                tokens_used = data.get("usage", {}).get("total_tokens")
                
                processing_time = (time.time() - start_time) * 1000
                
                return LLMResponse(
                    content=content,
                    tokens_used=tokens_used,
                    model_used=self.model,
                    provider=self.provider,
                    processing_time_ms=processing_time,
                    success=True
                )
            else:
                error_msg = f"OpenAI API error: {response.status_code} - {response.text}"
                logger.error("OpenAI API request failed", error=error_msg)
                
                return LLMResponse(
                    content="",
                    provider=self.provider,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    success=False,
                    error_message=error_msg
                )
                
        except Exception as e:
            error_msg = f"OpenAI request exception: {str(e)}"
            logger.error("OpenAI request failed", error=error_msg)
            
            return LLMResponse(
                content="",
                provider=self.provider,
                processing_time_ms=(time.time() - start_time) * 1000,
                success=False,
                error_message=error_msg
            )
    
    async def complete(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate completion from prompt."""
        messages = [{"role": "user", "content": prompt}]
        return await self._make_request(messages, **kwargs)
    
    async def analyze_document(self, text: str, context: Dict[str, Any]) -> DocumentInsight:
        """Analyze document for insights using OpenAI."""
        
        company_terms = ", ".join(context.get("company_terms", []))
        industries = ", ".join(context.get("core_industries", []))
        markets = ", ".join(context.get("primary_markets", []))
        themes = ", ".join(context.get("strategic_themes", []))
        
        prompt = f"""
Analyze this political/regulatory document for business relevance. Focus on:

Company Context:
- Company terms: {company_terms}
- Industries: {industries}
- Primary markets: {markets}
- Strategic themes: {themes}

Document Text:
{text[:3000]}  # Limit text to avoid token limits

Please provide analysis in this JSON format:
{{
    "key_themes": ["theme1", "theme2", "theme3"],
    "regulatory_indicators": ["indicator1", "indicator2"],
    "urgency_signals": ["signal1", "signal2"],
    "business_impact": "summary of potential business impact",
    "confidence_score": 0.85,
    "reasoning": "explanation of the analysis"
}}

Focus on regulatory compliance, business impact, and urgency indicators.
"""
        
        response = await self.complete(prompt, max_tokens=800)
        
        if not response.success:
            # Fallback to default insights
            return DocumentInsight(
                key_themes=["Analysis unavailable"],
                regulatory_indicators=[],
                urgency_signals=[],
                business_impact="Unable to analyze - LLM unavailable",
                confidence_score=0.1,
                reasoning="LLM analysis failed"
            )
        
        try:
            # Try to parse JSON response
            result = json.loads(response.content.strip())
            return DocumentInsight(**result)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Failed to parse LLM response", error=str(e))
            
            # Fallback parsing from text response
            return self._parse_insight_from_text(response.content)
    
    def _parse_insight_from_text(self, text: str) -> DocumentInsight:
        """Parse insights from unstructured text response."""
        lines = text.lower().split('\n')
        
        key_themes = []
        regulatory_indicators = []
        urgency_signals = []
        
        for line in lines:
            if 'theme' in line or 'topic' in line:
                key_themes.append(line.strip())
            elif 'regulation' in line or 'compliance' in line:
                regulatory_indicators.append(line.strip())
            elif 'urgent' in line or 'deadline' in line:
                urgency_signals.append(line.strip())
        
        return DocumentInsight(
            key_themes=key_themes[:5] or ["General analysis"],
            regulatory_indicators=regulatory_indicators[:5],
            urgency_signals=urgency_signals[:3],
            business_impact="Parsed from unstructured response",
            confidence_score=0.6,
            reasoning="Fallback parsing applied"
        )
    
    async def score_dimension(
        self, 
        text: str, 
        dimension: str, 
        context: Dict[str, Any],
        rule_based_score: float
    ) -> SemanticScore:
        """Generate semantic score for a dimension using OpenAI."""
        
        dimension_descriptions = {
            "direct_impact": "Direct impact on the company/organization",
            "industry_relevance": "Relevance to the company's industry and business model",
            "geographic_relevance": "Geographic scope and market relevance",
            "temporal_urgency": "Time sensitivity and urgency of the content",
            "strategic_alignment": "Alignment with strategic themes and priorities"
        }
        
        description = dimension_descriptions.get(dimension, dimension)
        
        prompt = f"""
Score this document for "{description}" on a scale of 0-100.

Current rule-based score: {rule_based_score}

Context:
- Company: {", ".join(context.get("company_terms", []))}
- Industry: {", ".join(context.get("core_industries", []))}
- Markets: {", ".join(context.get("primary_markets", []))}

Document excerpt:
{text[:2000]}

Provide response in JSON format:
{{
    "semantic_score": 75,
    "reasoning": "explanation for the score",
    "key_evidence": ["evidence1", "evidence2"],
    "confidence": 0.8
}}

Consider semantic meaning, context, and nuanced understanding beyond keyword matching.
"""
        
        response = await self.complete(prompt, max_tokens=400)
        
        if not response.success:
            # Fallback to rule-based score
            return SemanticScore(
                dimension_name=dimension,
                semantic_score=rule_based_score,
                rule_based_score=rule_based_score,
                hybrid_score=rule_based_score,
                llm_reasoning="LLM unavailable - using rule-based score",
                key_evidence=["Rule-based analysis only"],
                confidence=0.5
            )
        
        try:
            result = json.loads(response.content.strip())
            semantic_score = result.get("semantic_score", rule_based_score)
            
            # Calculate hybrid score (weighted combination)
            hybrid_score = (rule_based_score * 0.6) + (semantic_score * 0.4)
            
            return SemanticScore(
                dimension_name=dimension,
                semantic_score=semantic_score,
                rule_based_score=rule_based_score,
                hybrid_score=hybrid_score,
                llm_reasoning=result.get("reasoning", "LLM analysis completed"),
                key_evidence=result.get("key_evidence", []),
                confidence=result.get("confidence", 0.7)
            )
            
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Failed to parse semantic score", error=str(e))
            
            # Simple hybrid fallback
            hybrid_score = (rule_based_score * 0.8) + (rule_based_score * 0.2)  # Conservative hybrid
            
            return SemanticScore(
                dimension_name=dimension,
                semantic_score=rule_based_score,
                rule_based_score=rule_based_score,
                hybrid_score=hybrid_score,
                llm_reasoning="Fallback scoring applied",
                key_evidence=["Parsing failed"],
                confidence=0.5
            )
    
    async def analyze_topics(self, documents: List[str]) -> List[TopicAnalysis]:
        """Analyze topics across multiple documents."""
        
        # Combine documents for topic analysis
        combined_text = "\n\n---\n\n".join(documents[:10])  # Limit to 10 docs
        
        prompt = f"""
Analyze these political/regulatory documents and identify the main topics.

Documents:
{combined_text[:4000]}

Identify 3-5 main topics and provide analysis in JSON format:
[
    {{
        "topic_name": "Topic Name",
        "topic_description": "Description of the topic",
        "relevance_score": 85,
        "key_concepts": ["concept1", "concept2"],
        "related_regulations": ["regulation1", "regulation2"],
        "business_implications": "implications for business"
    }}
]

Focus on regulatory themes, business impact, and strategic relevance.
"""
        
        response = await self.complete(prompt, max_tokens=1000)
        
        if not response.success:
            return []
        
        try:
            topics_data = json.loads(response.content.strip())
            return [TopicAnalysis(**topic) for topic in topics_data]
        except (json.JSONDecodeError, Exception):
            return []
    
    async def generate_report_insights(
        self, 
        scoring_results: List[Dict[str, Any]], 
        context: Dict[str, Any]
    ) -> LLMReportInsights:
        """Generate insights for report using OpenAI."""
        
        # Prepare summary data for LLM
        total_docs = len(scoring_results)
        high_priority = len([r for r in scoring_results if r.get("master_score", 0) >= 75])
        avg_score = sum(r.get("master_score", 0) for r in scoring_results) / total_docs if total_docs > 0 else 0
        
        # Get top documents for analysis
        top_docs = sorted(scoring_results, key=lambda x: x.get("master_score", 0), reverse=True)[:5]
        
        prompt = f"""
Generate executive insights for a political monitoring report.

Analysis Summary:
- Total documents: {total_docs}
- High priority documents: {high_priority}
- Average relevance score: {avg_score:.1f}

Top Documents:
{chr(10).join([f"- {doc.get('justification', 'No justification')} (Score: {doc.get('master_score', 0):.1f})" for doc in top_docs])}

Company Context:
- Industries: {", ".join(context.get("core_industries", []))}
- Markets: {", ".join(context.get("primary_markets", []))}
- Strategic themes: {", ".join(context.get("strategic_themes", []))}

Provide insights in JSON format:
{{
    "executive_summary": "concise summary of key findings",
    "key_findings": ["finding1", "finding2", "finding3"],
    "strategic_recommendations": ["rec1", "rec2", "rec3"],
    "risk_assessment": "overall risk assessment",
    "priority_rationale": "explanation of prioritization",
    "market_context": "relevant market context"
}}

Focus on actionable insights and strategic implications.
"""
        
        response = await self.complete(prompt, max_tokens=1200)
        
        if not response.success:
            # Fallback insights
            return LLMReportInsights(
                executive_summary=f"Analysis of {total_docs} documents with {high_priority} high-priority items identified.",
                key_findings=["LLM analysis unavailable", "Using fallback insights"],
                strategic_recommendations=["Review high-priority documents", "Monitor regulatory changes"],
                risk_assessment="Unable to assess - LLM unavailable",
                priority_rationale="Based on scoring algorithm",
                market_context="Context analysis unavailable"
            )
        
        try:
            result = json.loads(response.content.strip())
            return LLMReportInsights(**result)
        except (json.JSONDecodeError, Exception):
            # Fallback with partial content
            return LLMReportInsights(
                executive_summary=response.content[:200] + "...",
                key_findings=["Analysis completed with limitations"],
                strategic_recommendations=["Review findings manually"],
                risk_assessment="Requires manual review",
                priority_rationale="Based on automated scoring",
                market_context="Manual analysis required"
            )