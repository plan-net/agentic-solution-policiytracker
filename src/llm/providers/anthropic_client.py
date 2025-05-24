"""Anthropic Claude LLM client implementation."""

import json
import time
from typing import Dict, List, Optional, Any

import httpx
import structlog

from src.llm.base_client import BaseLLMClient
from src.llm.models import (
    LLMProvider,
    LLMResponse,
    DocumentInsight,
    SemanticScore,
    TopicAnalysis,
    LLMReportInsights,
)

logger = structlog.get_logger()


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude API client for LLM operations."""

    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307", **kwargs):
        super().__init__(LLMProvider.ANTHROPIC, **kwargs)
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.anthropic.com/v1"

    async def _make_request(self, messages: List[Dict], **kwargs) -> LLMResponse:
        """Make request to Anthropic API."""
        start_time = time.time()

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 1000),
            "temperature": kwargs.get("temperature", 0.3),
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/messages", headers=headers, json=payload, timeout=30.0
                )

            if response.status_code == 200:
                data = response.json()
                content = data["content"][0]["text"]
                tokens_used = data.get("usage", {}).get("input_tokens", 0) + data.get(
                    "usage", {}
                ).get("output_tokens", 0)

                processing_time = (time.time() - start_time) * 1000

                return LLMResponse(
                    content=content,
                    tokens_used=tokens_used,
                    model_used=self.model,
                    provider=self.provider,
                    processing_time_ms=processing_time,
                    success=True,
                )
            else:
                error_msg = f"Anthropic API error: {response.status_code} - {response.text}"
                logger.error("Anthropic API request failed", error=error_msg)

                return LLMResponse(
                    content="",
                    provider=self.provider,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    success=False,
                    error_message=error_msg,
                )

        except Exception as e:
            error_msg = f"Anthropic request exception: {str(e)}"
            logger.error("Anthropic request failed", error=error_msg)

            return LLMResponse(
                content="",
                provider=self.provider,
                processing_time_ms=(time.time() - start_time) * 1000,
                success=False,
                error_message=error_msg,
            )

    async def complete(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate completion from prompt."""
        messages = [{"role": "user", "content": prompt}]
        return await self._make_request(messages, **kwargs)

    async def analyze_document(self, text: str, context: Dict[str, Any]) -> DocumentInsight:
        """Analyze document for insights using Claude."""

        company_terms = ", ".join(context.get("company_terms", []))
        industries = ", ".join(context.get("core_industries", []))
        markets = ", ".join(context.get("primary_markets", []))
        themes = ", ".join(context.get("strategic_themes", []))

        prompt = f"""
I need you to analyze this political/regulatory document for business relevance and impact.

<context>
Company Context:
- Company terms: {company_terms}
- Industries: {industries}  
- Primary markets: {markets}
- Strategic themes: {themes}
</context>

<document>
{text[:3000]}
</document>

Please analyze the document and provide insights in the following JSON format:

{{
    "key_themes": ["theme1", "theme2", "theme3"],
    "regulatory_indicators": ["specific regulatory requirements or indicators"],
    "urgency_signals": ["time-sensitive elements"],
    "business_impact": "clear summary of potential business impact",
    "confidence_score": 0.85,
    "reasoning": "detailed explanation of your analysis"
}}

Focus specifically on:
1. Regulatory compliance requirements that could affect the business
2. Time-sensitive deadlines or urgent actions needed  
3. Strategic business implications
4. Market or geographic impact

Provide only the JSON response without additional commentary.
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
                reasoning="Claude analysis failed",
            )

        try:
            # Clean response and parse JSON
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]

            result = json.loads(content.strip())
            return DocumentInsight(**result)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Failed to parse Claude response", error=str(e))

            # Fallback parsing from text response
            return self._parse_insight_from_text(response.content)

    def _parse_insight_from_text(self, text: str) -> DocumentInsight:
        """Parse insights from unstructured text response."""
        lines = text.lower().split("\n")

        key_themes = []
        regulatory_indicators = []
        urgency_signals = []

        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue

            if "theme" in line:
                current_section = "themes"
            elif "regulatory" in line or "compliance" in line:
                current_section = "regulatory"
            elif "urgent" in line or "deadline" in line:
                current_section = "urgency"
            elif line.startswith("-") or line.startswith("•"):
                item = line.lstrip("-• ").strip()
                if current_section == "themes":
                    key_themes.append(item)
                elif current_section == "regulatory":
                    regulatory_indicators.append(item)
                elif current_section == "urgency":
                    urgency_signals.append(item)

        return DocumentInsight(
            key_themes=key_themes[:5] or ["General analysis"],
            regulatory_indicators=regulatory_indicators[:5],
            urgency_signals=urgency_signals[:3],
            business_impact="Parsed from unstructured Claude response",
            confidence_score=0.6,
            reasoning="Fallback parsing applied to Claude response",
        )

    async def score_dimension(
        self, text: str, dimension: str, context: Dict[str, Any], rule_based_score: float
    ) -> SemanticScore:
        """Generate semantic score for a dimension using Claude."""

        dimension_descriptions = {
            "direct_impact": "Direct impact on the company/organization - mentions of company, direct regulatory requirements affecting the business",
            "industry_relevance": "Relevance to the company's industry and business model - industry-specific regulations, market dynamics",
            "geographic_relevance": "Geographic scope and market relevance - regulations in key markets, regional impact",
            "temporal_urgency": "Time sensitivity and urgency - deadlines, immediate action required, time-bound requirements",
            "strategic_alignment": "Alignment with strategic themes and priorities - fits with business strategy and goals",
        }

        description = dimension_descriptions.get(dimension, dimension)
        company_info = ", ".join(context.get("company_terms", []))

        prompt = f"""
I need you to score this document for "{dimension}" on a scale of 0-100, considering semantic meaning and context.

<scoring_context>
Dimension: {description}
Current rule-based score: {rule_based_score}
Company context: {company_info}
Industry: {", ".join(context.get("core_industries", []))}
Key markets: {", ".join(context.get("primary_markets", []))}
</scoring_context>

<document_excerpt>
{text[:2000]}
</document_excerpt>

Please provide a semantic score that considers:
1. Nuanced understanding beyond keyword matching
2. Context and implications
3. Severity and scope of impact
4. Relevance to the specific dimension

Respond in JSON format:
{{
    "semantic_score": 75,
    "reasoning": "detailed explanation for the score",
    "key_evidence": ["specific evidence supporting the score"],
    "confidence": 0.8
}}

Provide only the JSON response.
"""

        response = await self.complete(prompt, max_tokens=500)

        if not response.success:
            # Fallback to rule-based score
            return SemanticScore(
                dimension_name=dimension,
                semantic_score=rule_based_score,
                rule_based_score=rule_based_score,
                hybrid_score=rule_based_score,
                llm_reasoning="Claude unavailable - using rule-based score",
                key_evidence=["Rule-based analysis only"],
                confidence=0.5,
            )

        try:
            # Clean and parse JSON response
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]

            result = json.loads(content.strip())
            semantic_score = float(result.get("semantic_score", rule_based_score))

            # Ensure score is within bounds
            semantic_score = max(0, min(100, semantic_score))

            # Calculate hybrid score (weighted combination)
            # Give more weight to semantic score for Claude as it's more sophisticated
            hybrid_score = (rule_based_score * 0.4) + (semantic_score * 0.6)

            return SemanticScore(
                dimension_name=dimension,
                semantic_score=semantic_score,
                rule_based_score=rule_based_score,
                hybrid_score=hybrid_score,
                llm_reasoning=result.get("reasoning", "Claude semantic analysis completed"),
                key_evidence=result.get("key_evidence", []),
                confidence=float(result.get("confidence", 0.8)),
            )

        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Failed to parse Claude semantic score", error=str(e))

            # Conservative hybrid fallback
            hybrid_score = (rule_based_score * 0.7) + (rule_based_score * 0.3)

            return SemanticScore(
                dimension_name=dimension,
                semantic_score=rule_based_score,
                rule_based_score=rule_based_score,
                hybrid_score=hybrid_score,
                llm_reasoning="Fallback scoring applied - Claude parsing failed",
                key_evidence=["Parsing failed"],
                confidence=0.5,
            )

    async def analyze_topics(self, documents: List[str]) -> List[TopicAnalysis]:
        """Analyze topics across multiple documents using Claude."""

        # Combine documents for topic analysis
        combined_text = "\n\n---DOCUMENT SEPARATOR---\n\n".join(
            documents[:8]
        )  # Limit for token efficiency

        prompt = f"""
Analyze these political/regulatory documents to identify the main thematic topics.

<documents>
{combined_text[:5000]}
</documents>

Please identify 3-5 main topics that emerge from these documents and provide analysis in this JSON format:

[
    {{
        "topic_name": "Clear, descriptive topic name",
        "topic_description": "Detailed description of what this topic covers",
        "relevance_score": 85,
        "key_concepts": ["concept1", "concept2", "concept3"],
        "related_regulations": ["specific regulations or frameworks"],
        "business_implications": "clear explanation of business implications"
    }}
]

Focus on:
1. Regulatory and compliance themes
2. Business impact areas  
3. Strategic relevance
4. Market or operational implications

Provide only the JSON array response.
"""

        response = await self.complete(prompt, max_tokens=1200)

        if not response.success:
            return []

        try:
            # Clean and parse JSON response
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]

            topics_data = json.loads(content.strip())
            return [TopicAnalysis(**topic) for topic in topics_data]
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Failed to parse Claude topics response", error=str(e))
            return []

    async def generate_report_insights(
        self, scoring_results: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> LLMReportInsights:
        """Generate insights for report using Claude."""

        # Prepare summary data for Claude
        total_docs = len(scoring_results)
        high_priority = len([r for r in scoring_results if r.get("master_score", 0) >= 75])
        critical_priority = len([r for r in scoring_results if r.get("master_score", 0) >= 90])
        avg_score = (
            sum(r.get("master_score", 0) for r in scoring_results) / total_docs
            if total_docs > 0
            else 0
        )

        # Get top documents for analysis
        top_docs = sorted(scoring_results, key=lambda x: x.get("master_score", 0), reverse=True)[:5]

        prompt = f"""
Generate executive-level insights for a political monitoring report based on this analysis.

<analysis_summary>
Total documents analyzed: {total_docs}
Critical priority documents (90+): {critical_priority}
High priority documents (75+): {high_priority}
Average relevance score: {avg_score:.1f}
</analysis_summary>

<top_findings>
{chr(10).join([f"- Score {doc.get('master_score', 0):.1f}: {doc.get('overall_justification', 'No justification available')}" for doc in top_docs])}
</top_findings>

<business_context>
Industries: {", ".join(context.get("core_industries", []))}
Primary markets: {", ".join(context.get("primary_markets", []))}
Strategic themes: {", ".join(context.get("strategic_themes", []))}
</business_context>

Please provide strategic insights in this JSON format:

{{
    "executive_summary": "2-3 sentence high-level summary of key findings and their significance",
    "key_findings": ["specific, actionable finding 1", "specific, actionable finding 2", "specific, actionable finding 3", "specific, actionable finding 4"],
    "strategic_recommendations": ["specific recommendation 1", "specific recommendation 2", "specific recommendation 3"],
    "risk_assessment": "clear assessment of overall risk profile and key risk areas",
    "priority_rationale": "explanation of how items were prioritized and why top items matter",
    "market_context": "relevant market and regulatory environment context"
}}

Focus on:
1. Actionable business implications
2. Strategic risks and opportunities  
3. Regulatory compliance priorities
4. Market and competitive context

Provide only the JSON response.
"""

        response = await self.complete(prompt, max_tokens=1500)

        if not response.success:
            # Fallback insights
            return LLMReportInsights(
                executive_summary=f"Analysis of {total_docs} documents identified {high_priority} high-priority regulatory and compliance items requiring attention.",
                key_findings=["Claude analysis unavailable", "Manual review recommended"],
                strategic_recommendations=[
                    "Review high-priority documents",
                    "Monitor regulatory developments",
                ],
                risk_assessment="Unable to assess risk profile - Claude unavailable",
                priority_rationale="Automated scoring algorithm applied",
                market_context="Market context analysis unavailable",
            )

        try:
            # Clean and parse JSON response
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]

            result = json.loads(content.strip())
            return LLMReportInsights(**result)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Failed to parse Claude insights response", error=str(e))

            # Fallback with partial content
            return LLMReportInsights(
                executive_summary=response.content[:300] + "..."
                if len(response.content) > 300
                else response.content,
                key_findings=["Analysis completed with parsing limitations"],
                strategic_recommendations=["Manual review of Claude response recommended"],
                risk_assessment="Risk assessment requires manual interpretation",
                priority_rationale="Automated prioritization applied",
                market_context="Manual context analysis required",
            )
