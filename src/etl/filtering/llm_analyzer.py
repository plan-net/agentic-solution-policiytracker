"""
LLM-based relevance analyzer.

Optional component for analyzing borderline cases that the
keyword scorer is uncertain about. Uses OpenAI-compatible API.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional

import structlog

from ..utils.schema_helpers import extract_industries, extract_markets

logger = structlog.get_logger()


@dataclass
class LLMAnalysisResult:
    """Result of LLM relevance analysis."""

    score: float  # 0-100
    is_relevant: bool
    explanation: str
    confidence: float  # 0-1
    model_used: str
    tokens_used: int = 0


class LLMAnalyzer:
    """LLM-based relevance analyzer for borderline cases.

    Uses OpenAI-compatible API (supports OpenAI, Azure, local models)
    to analyze content that keyword scoring is uncertain about.
    """

    # Default prompt template for German political content
    ANALYSIS_PROMPT = """Analyze the following article for relevance to political monitoring for a company.

Company Context:
- Industry: {industries}
- Key Markets: {markets}
- Strategic Themes: {themes}

Article Title: {title}

Article Content (excerpt):
{content}

Evaluate if this article is relevant for political/regulatory monitoring.
Consider:
1. Does it discuss regulations, policies, or laws that could affect the company's industry?
2. Does it mention specific markets or regions the company operates in?
3. Does it cover strategic themes like digital transformation, sustainability, or data privacy?
4. Is it actionable for compliance or strategic planning?

Respond in JSON format:
{{
    "score": <0-100>,
    "is_relevant": <true/false>,
    "explanation": "<brief explanation in English>",
    "confidence": <0.0-1.0>
}}"""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        client_config: Optional[dict[str, Any]] = None,
        relevance_threshold: float = 50.0,
    ):
        """Initialize the LLM analyzer.

        Args:
            model: Model name to use
            api_key: OpenAI API key (or from env)
            api_base: Optional custom API base URL
            client_config: Client configuration for context
            relevance_threshold: Score threshold for relevance
        """
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.api_base = api_base
        self.client_config = client_config or {}
        self.relevance_threshold = relevance_threshold

        # Extract context from client config using schema helpers
        industries_list = extract_industries(self.client_config)
        if not industries_list:
            industries_list = ["e-commerce"]
        self._industries = ", ".join(industries_list[:5])

        # Extract markets using helper
        primary_markets, secondary_markets = extract_markets(self.client_config)
        self._markets = ", ".join(primary_markets[:5] + secondary_markets[:3])

        self._themes = ", ".join(
            self.client_config.get("strategic_themes", [])[:5]
        )

        self._enabled = bool(self.api_key)

        if self._enabled:
            logger.info(
                "Initialized LLMAnalyzer",
                model=model,
                threshold=relevance_threshold,
            )
        else:
            logger.warning("LLMAnalyzer disabled - no API key provided")

    @property
    def is_enabled(self) -> bool:
        """Check if LLM analysis is enabled."""
        return self._enabled

    async def analyze(
        self,
        title: str,
        content: str,
        max_content_length: int = 2000,
    ) -> LLMAnalysisResult:
        """Analyze content for relevance using LLM.

        Args:
            title: Article title
            content: Article content
            max_content_length: Maximum content length to send

        Returns:
            LLMAnalysisResult with score and explanation
        """
        if not self._enabled:
            return LLMAnalysisResult(
                score=50.0,
                is_relevant=True,  # Default to including uncertain content
                explanation="LLM analysis disabled - defaulting to include",
                confidence=0.0,
                model_used="none",
            )

        # Truncate content if too long
        content_excerpt = content[:max_content_length]
        if len(content) > max_content_length:
            content_excerpt += "..."

        # Build prompt
        prompt = self.ANALYSIS_PROMPT.format(
            industries=self._industries,
            markets=self._markets,
            themes=self._themes,
            title=title,
            content=content_excerpt,
        )

        try:
            result = await self._call_llm(prompt)
            return result
        except Exception as e:
            logger.error("LLM analysis failed", error=str(e))
            return LLMAnalysisResult(
                score=50.0,
                is_relevant=True,  # Default to including on error
                explanation=f"Analysis failed: {str(e)}",
                confidence=0.0,
                model_used=self.model,
            )

    async def analyze_batch(
        self,
        articles: list[tuple[str, str]],  # (title, content) pairs
        max_content_length: int = 1000,
    ) -> list[LLMAnalysisResult]:
        """Analyze multiple articles in batch.

        Args:
            articles: List of (title, content) tuples
            max_content_length: Maximum content length per article

        Returns:
            List of analysis results
        """
        results = []

        for title, content in articles:
            result = await self.analyze(title, content, max_content_length)
            results.append(result)

        return results

    async def _call_llm(self, prompt: str) -> LLMAnalysisResult:
        """Make API call to LLM.

        Args:
            prompt: Full prompt to send

        Returns:
            LLMAnalysisResult parsed from response
        """
        import json

        import aiohttp

        # Determine API endpoint
        if self.api_base:
            api_url = f"{self.api_base}/chat/completions"
        else:
            api_url = "https://api.openai.com/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a political monitoring analyst. Respond only with valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 300,
        }

        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(api_url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API error {response.status}: {error_text}")

                data = await response.json()

        # Parse response
        content = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)

        # Extract JSON from response
        try:
            # Try to parse as JSON directly
            result_data = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code block
            import re

            json_match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
            if json_match:
                result_data = json.loads(json_match.group(1))
            else:
                # Try to find JSON object in text
                json_match = re.search(r"\{.*\}", content, re.DOTALL)
                if json_match:
                    result_data = json.loads(json_match.group(0))
                else:
                    raise ValueError("Could not parse JSON from response")

        return LLMAnalysisResult(
            score=float(result_data.get("score", 50)),
            is_relevant=bool(result_data.get("is_relevant", True)),
            explanation=str(result_data.get("explanation", "")),
            confidence=float(result_data.get("confidence", 0.5)),
            model_used=self.model,
            tokens_used=tokens,
        )

    def estimate_cost(self, num_articles: int, avg_tokens_per_article: int = 500) -> float:
        """Estimate cost for analyzing a number of articles.

        Args:
            num_articles: Number of articles to analyze
            avg_tokens_per_article: Average tokens per article

        Returns:
            Estimated cost in USD
        """
        # Approximate pricing (adjust based on actual model)
        pricing = {
            "gpt-4o-mini": 0.00015 / 1000,  # $0.15 per 1M tokens
            "gpt-4o": 0.0025 / 1000,  # $2.50 per 1M tokens
            "gpt-3.5-turbo": 0.0005 / 1000,  # $0.50 per 1M tokens
        }

        price_per_token = pricing.get(self.model, 0.00015 / 1000)
        total_tokens = num_articles * avg_tokens_per_article

        return total_tokens * price_per_token
