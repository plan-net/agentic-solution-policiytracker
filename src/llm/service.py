"""LLM service manager with provider selection and fallback."""

import asyncio
from typing import Dict, List, Optional, Any

import structlog

from src.config import settings
from src.integrations.langfuse_client import langfuse_client
from src.llm.base_client import BaseLLMClient, MockLLMClient
from src.llm.providers.openai_client import OpenAIClient
from src.llm.providers.anthropic_client import AnthropicClient
from src.llm.models import (
    LLMProvider,
    DocumentInsight,
    SemanticScore,
    TopicAnalysis,
    LLMReportInsights,
)

logger = structlog.get_logger()


class LLMService:
    """Central LLM service with provider management and fallbacks."""

    def __init__(self):
        self.primary_client: Optional[BaseLLMClient] = None
        self.fallback_client: MockLLMClient = MockLLMClient()
        self.enabled = False
        self._setup_clients()

    def _setup_clients(self):
        """Setup LLM clients based on configuration."""
        try:
            # Check which LLM providers are configured
            openai_key = getattr(settings, "OPENAI_API_KEY", None)
            anthropic_key = getattr(settings, "ANTHROPIC_API_KEY", None)
            llm_enabled = getattr(settings, "LLM_ENABLED", False)

            if not llm_enabled:
                logger.info("LLM integration disabled in configuration")
                return

            if anthropic_key:
                try:
                    self.primary_client = AnthropicClient(
                        api_key=anthropic_key,
                        model=getattr(settings, "ANTHROPIC_MODEL", "claude-3-haiku-20240307"),
                    )
                    self.enabled = True
                    logger.info("Initialized Anthropic Claude client")
                except Exception as e:
                    logger.warning("Failed to initialize Anthropic client", error=str(e))

            elif openai_key:
                try:
                    self.primary_client = OpenAIClient(
                        api_key=openai_key, model=getattr(settings, "OPENAI_MODEL", "gpt-4")
                    )
                    self.enabled = True
                    logger.info("Initialized OpenAI client")
                except Exception as e:
                    logger.warning("Failed to initialize OpenAI client", error=str(e))

            if not self.primary_client:
                logger.info("No LLM provider configured - using mock client for testing")

        except Exception as e:
            logger.error("Failed to setup LLM clients", error=str(e))

    async def _execute_with_fallback(self, operation_name: str, primary_func, fallback_func):
        """Execute LLM operation with fallback to mock client."""
        if not self.enabled or not self.primary_client:
            logger.debug(f"Using fallback for {operation_name} - LLM not available")
            return await fallback_func()

        try:
            # Try primary LLM client
            result = await primary_func()
            logger.debug(f"Successfully executed {operation_name} with primary LLM")
            return result

        except Exception as e:
            logger.warning(f"Primary LLM failed for {operation_name}, using fallback", error=str(e))
            return await fallback_func()

    async def analyze_document(self, text: str, context: Dict[str, Any]) -> DocumentInsight:
        """Analyze document with LLM insights."""

        async with await langfuse_client.trace(
            name="analyze_document",
            input_data={"text_length": len(text), "context_keys": list(context.keys())},
            metadata={"operation": "document_analysis"},
        ) as trace:

            async def primary_analysis():
                return await self.primary_client.analyze_document(text, context)

            async def fallback_analysis():
                return await self.fallback_client.analyze_document(text, context)

            result = await self._execute_with_fallback(
                "document_analysis", primary_analysis, fallback_analysis
            )

            trace.update_output(
                {
                    "key_topics_count": len(result.key_topics),
                    "sentiment": result.sentiment,
                    "confidence": result.confidence,
                }
            )

            return result

    async def score_dimension_semantic(
        self, text: str, dimension: str, context: Dict[str, Any], rule_based_score: float
    ) -> SemanticScore:
        """Generate semantic score for dimension."""

        async with langfuse_client.trace(
            name="score_dimension_semantic",
            input_data={
                "dimension": dimension,
                "rule_based_score": rule_based_score,
                "text_length": len(text),
            },
            metadata={"operation": "semantic_scoring"},
        ) as trace:

            async def primary_scoring():
                return await self.primary_client.score_dimension(
                    text, dimension, context, rule_based_score
                )

            async def fallback_scoring():
                return await self.fallback_client.score_dimension(
                    text, dimension, context, rule_based_score
                )

            result = await self._execute_with_fallback(
                "semantic_scoring", primary_scoring, fallback_scoring
            )

            trace.update_output(
                {
                    "semantic_score": result.semantic_score,
                    "confidence": result.confidence,
                    "reasoning_length": len(result.reasoning),
                }
            )

            return result

    async def analyze_topics_semantic(self, documents: List[str]) -> List[TopicAnalysis]:
        """Analyze topics using semantic understanding."""

        async def primary_topic_analysis():
            return await self.primary_client.analyze_topics(documents)

        async def fallback_topic_analysis():
            return await self.fallback_client.analyze_topics(documents)

        return await self._execute_with_fallback(
            "topic_analysis", primary_topic_analysis, fallback_topic_analysis
        )

    async def generate_report_insights(
        self, scoring_results: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> LLMReportInsights:
        """Generate LLM-powered report insights."""

        async def primary_insights():
            return await self.primary_client.generate_report_insights(scoring_results, context)

        async def fallback_insights():
            return await self.fallback_client.generate_report_insights(scoring_results, context)

        return await self._execute_with_fallback(
            "report_insights", primary_insights, fallback_insights
        )

    async def batch_analyze_documents(
        self, documents_with_context: List[tuple[str, Dict[str, Any]]]
    ) -> List[DocumentInsight]:
        """Analyze multiple documents in parallel."""

        # Limit concurrent requests to avoid rate limiting
        max_concurrent = getattr(settings, "LLM_MAX_CONCURRENT", 3)
        semaphore = asyncio.Semaphore(max_concurrent)

        async def analyze_single(text_context_pair):
            async with semaphore:
                text, context = text_context_pair
                return await self.analyze_document(text, context)

        # Execute analyses in parallel with concurrency limit
        tasks = [analyze_single(pair) for pair in documents_with_context]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and return successful results
        insights = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Document analysis failed for item {i}", error=str(result))
                # Add fallback insight
                insights.append(
                    DocumentInsight(
                        key_themes=["Analysis failed"],
                        regulatory_indicators=[],
                        urgency_signals=[],
                        business_impact="Analysis unavailable",
                        confidence_score=0.1,
                        reasoning="Batch analysis failed",
                    )
                )
            else:
                insights.append(result)

        return insights

    async def batch_score_dimensions(
        self, scoring_requests: List[Dict[str, Any]]
    ) -> List[SemanticScore]:
        """Score multiple dimensions in parallel."""

        max_concurrent = getattr(settings, "LLM_MAX_CONCURRENT", 3)
        semaphore = asyncio.Semaphore(max_concurrent)

        async def score_single(request):
            async with semaphore:
                return await self.score_dimension_semantic(**request)

        tasks = [score_single(req) for req in scoring_requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions and return results
        scores = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Semantic scoring failed for request {i}", error=str(result))
                # Create fallback score
                req = scoring_requests[i]
                scores.append(
                    SemanticScore(
                        dimension_name=req["dimension"],
                        semantic_score=req["rule_based_score"],
                        rule_based_score=req["rule_based_score"],
                        hybrid_score=req["rule_based_score"],
                        llm_reasoning="Batch scoring failed",
                        key_evidence=["Analysis unavailable"],
                        confidence=0.3,
                    )
                )
            else:
                scores.append(result)

        return scores

    def get_service_status(self) -> Dict[str, Any]:
        """Get current LLM service status."""
        return {
            "enabled": self.enabled,
            "primary_provider": self.primary_client.provider.value if self.primary_client else None,
            "has_fallback": True,
            "mock_calls": self.fallback_client.call_count
            if hasattr(self.fallback_client, "call_count")
            else 0,
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on LLM services."""
        health_status = {
            "service_enabled": self.enabled,
            "primary_client": "unavailable",
            "fallback_client": "available",
        }

        if self.primary_client:
            try:
                # Test with a simple completion
                response = await self.primary_client.complete("Test connection", max_tokens=10)
                health_status["primary_client"] = "available" if response.success else "error"
            except Exception as e:
                health_status["primary_client"] = f"error: {str(e)}"

        # Test fallback
        try:
            await self.fallback_client.complete("Test", max_tokens=10)
            health_status["fallback_client"] = "available"
        except Exception:
            health_status["fallback_client"] = "error"

        return health_status


# Global LLM service instance
llm_service = LLMService()
