"""
LangChain-based LLM service with standardized interfaces and observability.
"""

import json
import os
import re
from typing import Any, Optional

import structlog
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from langfuse import Langfuse
from langfuse.callback import CallbackHandler
from langfuse.decorators import langfuse_context, observe

from src.config import settings

# Ensure Langfuse environment variables are set for decorators
if settings.LANGFUSE_PUBLIC_KEY and not os.getenv("LANGFUSE_PUBLIC_KEY"):
    os.environ["LANGFUSE_PUBLIC_KEY"] = settings.LANGFUSE_PUBLIC_KEY
if settings.LANGFUSE_SECRET_KEY and not os.getenv("LANGFUSE_SECRET_KEY"):
    os.environ["LANGFUSE_SECRET_KEY"] = settings.LANGFUSE_SECRET_KEY
if settings.LANGFUSE_HOST and not os.getenv("LANGFUSE_HOST"):
    os.environ["LANGFUSE_HOST"] = settings.LANGFUSE_HOST

from src.llm.models import (
    DocumentInsight,
    LLMProvider,
    LLMReportInsights,
    SemanticScore,
    TopicAnalysis,
)

# Using @observe decorators for automatic Langfuse integration
from src.prompts.prompt_manager import prompt_manager

logger = structlog.get_logger()

# Initialize global Langfuse client and callback handler
try:
    # Initialize Langfuse client (prompt management)
    langfuse = Langfuse()

    # Initialize Langfuse CallbackHandler for Langchain (tracing)
    langfuse_callback_handler = CallbackHandler()

    # Verify that Langfuse is configured correctly
    assert langfuse.auth_check()
    assert langfuse_callback_handler.auth_check()

    logger.info("Langfuse client and CallbackHandler initialized and authenticated successfully")
except Exception as e:
    langfuse = None
    langfuse_callback_handler = None
    logger.warning(f"Failed to initialize Langfuse: {e}")


class LangChainLLMService:
    """LangChain-based LLM service with multiple provider support."""

    def __init__(self):
        self.primary_llm: Optional[BaseChatModel] = None
        self.fallback_llm: Optional[BaseChatModel] = None
        self.enabled = False
        self.current_provider = LLMProvider.MOCK
        self._setup_llms()
        self._setup_chains()

    def _setup_llms(self) -> None:
        """Initialize LangChain LLM instances based on configuration."""
        try:
            if not getattr(settings, "LLM_ENABLED", False):
                logger.info("LLM integration disabled in configuration")
                return

            # Setup Anthropic Claude as primary if available
            anthropic_key = getattr(settings, "ANTHROPIC_API_KEY", None)
            if anthropic_key:
                try:
                    self.primary_llm = ChatAnthropic(
                        api_key=anthropic_key,
                        model=getattr(settings, "ANTHROPIC_MODEL", "claude-3-haiku-20240307"),
                        temperature=0.3,
                        max_tokens=2000,
                        timeout=getattr(settings, "LLM_TIMEOUT_SECONDS", 30),
                    )
                    self.current_provider = LLMProvider.ANTHROPIC
                    self.enabled = True
                    logger.info("Initialized Anthropic Claude via LangChain")
                except Exception as e:
                    logger.warning("Failed to initialize Anthropic LLM", error=str(e))

            # Setup OpenAI as fallback or primary
            openai_key = getattr(settings, "OPENAI_API_KEY", None)
            if openai_key:
                try:
                    openai_llm = ChatOpenAI(
                        api_key=openai_key,
                        model=getattr(settings, "OPENAI_MODEL", "gpt-4"),
                        temperature=0.3,
                        max_tokens=2000,
                        timeout=getattr(settings, "LLM_TIMEOUT_SECONDS", 30),
                    )

                    if self.primary_llm is None:
                        self.primary_llm = openai_llm
                        self.current_provider = LLMProvider.OPENAI
                        self.enabled = True
                        logger.info("Initialized OpenAI as primary LLM via LangChain")
                    else:
                        self.fallback_llm = openai_llm
                        logger.info("Initialized OpenAI as fallback LLM via LangChain")

                except Exception as e:
                    logger.warning("Failed to initialize OpenAI LLM", error=str(e))

            if not self.enabled:
                logger.info("No LLM providers configured, using mock responses")

        except Exception as e:
            logger.error("Failed to setup LLMs", error=str(e))

    def _setup_chains(self) -> None:
        """Setup LangChain chains for different operations."""
        # Note: Prompts will be loaded dynamically from prompt manager
        # This reduces startup time and allows runtime prompt updates

        pass  # Prompts loaded dynamically via prompt manager

    async def _execute_with_fallback(self, operation_name: str, chain_func, mock_response) -> Any:
        """Execute LangChain operation with fallback to mock."""
        if not self.enabled:
            logger.debug(f"LLM disabled, returning mock response for {operation_name}")
            return mock_response

        try:
            # Try primary LLM
            if self.primary_llm:
                result = await chain_func(self.primary_llm)
                logger.debug(
                    f"Successfully executed {operation_name} with {self.current_provider.value}"
                )
                return result

        except Exception as e:
            logger.warning(f"Primary LLM failed for {operation_name}", error=str(e))

            # Try fallback LLM
            if self.fallback_llm:
                try:
                    result = await chain_func(self.fallback_llm)
                    logger.info(f"Fallback LLM succeeded for {operation_name}")
                    return result
                except Exception as e2:
                    logger.warning(f"Fallback LLM also failed for {operation_name}", error=str(e2))

        # Return mock response as final fallback
        logger.info(f"Using mock response for {operation_name}")
        return mock_response

    @observe()
    async def analyze_document(
        self, text: str, context: dict[str, Any], session_id: Optional[str] = None
    ) -> DocumentInsight:
        """Analyze document using LangChain with structured output."""

        # Update trace with session and meaningful tags
        langfuse_context.update_current_trace(
            name="Document Analysis Session",
            session_id=session_id,
            tags=["document-analysis"],
            metadata={
                "text_length": len(text),
                "context_keys": list(context.keys()),
                "provider": self.current_provider.value,
            },
        )

        @observe(as_type="generation")
        async def execute_analysis(llm: BaseChatModel) -> DocumentInsight:
            # Load prompt and config from prompt manager
            prompt_data = await prompt_manager.get_prompt_with_config(
                "document_analysis",
                variables={
                    "company_terms": context.get("company_terms", []),
                    "core_industries": context.get("core_industries", []),
                    "primary_markets": context.get("primary_markets", []),
                    "strategic_themes": context.get("strategic_themes", []),
                    "document_text": text,
                },
            )
            prompt_text = prompt_data["prompt"]
            prompt_config = prompt_data["config"]

            # Get Langfuse prompt object for generation tracking
            langfuse_prompt = None
            try:
                if langfuse:
                    langfuse_prompt = langfuse.get_prompt(
                        name="document_analysis", label="production"
                    )
                    # Update current observation with the prompt object for generation tracking
                    langfuse_context.update_current_observation(prompt=langfuse_prompt)
                    logger.info("Updated observation with Langfuse prompt for document_analysis")
            except Exception as e:
                logger.warning(f"Could not get Langfuse prompt for generation tracking: {e}")
                langfuse_prompt = None

            # Log full config for debugging
            logger.info(f"Document analysis Langfuse config: {prompt_config}")

            # Use temperature from Langfuse config if available
            llm_kwargs = {}
            if prompt_config.get("temperature") is not None:
                llm_kwargs["temperature"] = prompt_config["temperature"]
                logger.info(
                    f"Using temperature {prompt_config['temperature']} from Langfuse prompt config"
                )
            if prompt_config.get("max_tokens"):
                llm_kwargs["max_tokens"] = prompt_config["max_tokens"]

            # Update current observation with detailed context
            langfuse_context.update_current_observation(
                name=f"Document Analysis - {self.current_provider.value}",
                input={
                    "prompt_length": len(prompt_text),
                    "text_snippet": text[:200] + "..." if len(text) > 200 else text,
                    "context_summary": {
                        "company_terms_count": len(context.get("company_terms", [])),
                        "industries_count": len(context.get("core_industries", [])),
                        "markets_count": len(context.get("primary_markets", [])),
                    },
                },
                model=getattr(settings, "ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
                if self.current_provider.value == "anthropic"
                else getattr(settings, "OPENAI_MODEL", "gpt-4"),
                metadata={
                    "operation": "document_analysis",
                    "provider": self.current_provider.value,
                    "text_length": len(text),
                },
            )

            # Setup output parser
            parser = PydanticOutputParser(pydantic_object=DocumentInsight)

            # Create a new LLM instance with config from Langfuse if needed
            if llm_kwargs:
                if hasattr(llm, "bind"):
                    configured_llm = llm.bind(**llm_kwargs)
                else:
                    configured_llm = llm
                    logger.warning("LLM doesn't support parameter binding, using default config")
            else:
                configured_llm = llm

            # Use the LLM without conflicting callback handlers
            # The @observe decorator handles Langfuse tracking
            llm_response = await configured_llm.ainvoke([HumanMessage(content=prompt_text)])
            result = parser.parse(llm_response.content)

            # Update observation with structured output
            langfuse_context.update_current_observation(
                output={
                    "key_topics": result.key_topics,
                    "sentiment": result.sentiment,
                    "urgency_level": result.urgency_level,
                    "confidence": result.confidence,
                    "summary_length": len(result.summary),
                }
            )

            return result

        # Mock response for fallback
        mock_response = DocumentInsight(
            provider=LLMProvider.MOCK,
            key_topics=self._extract_mock_topics(text, context),
            sentiment="neutral",
            urgency_level="medium",
            confidence=0.65,
            summary=f"Mock analysis of document ({len(text)} characters)",
        )

        return await self._execute_with_fallback(
            "document_analysis", execute_analysis, mock_response
        )

    @observe()
    async def score_dimension_semantic(
        self,
        text: str,
        dimension: str,
        context: dict[str, Any],
        rule_based_score: float,
        session_id: Optional[str] = None,
    ) -> SemanticScore:
        """Generate semantic score using LangChain."""

        # Update trace with session and meaningful tags for semantic scoring
        langfuse_context.update_current_trace(
            name="Semantic Scoring Session",
            session_id=session_id,
            tags=["semantic-scoring", f"dimension-{dimension}"],
            metadata={
                "dimension": dimension,
                "rule_based_score": rule_based_score,
                "text_length": len(text),
                "provider": self.current_provider.value,
            },
        )

        @observe(as_type="generation")
        async def execute_scoring(llm: BaseChatModel) -> SemanticScore:
            # Load prompt and config from prompt manager
            prompt_data = await prompt_manager.get_prompt_with_config(
                "semantic_scoring",
                variables={
                    "company_terms": context.get("company_terms", []),
                    "core_industries": context.get("core_industries", []),
                    "primary_markets": context.get("primary_markets", []),
                    "strategic_themes": context.get("strategic_themes", []),
                    "dimension": dimension,
                    "rule_based_score": rule_based_score,
                    "document_text": text,
                },
            )
            prompt_text = prompt_data["prompt"]
            prompt_config = prompt_data["config"]

            # Get Langfuse prompt object for generation tracking
            langfuse_prompt = None
            try:
                if langfuse:
                    langfuse_prompt = langfuse.get_prompt(
                        name="semantic_scoring", label="production"
                    )
                    # Update current observation with the prompt object for generation tracking
                    langfuse_context.update_current_observation(prompt=langfuse_prompt)
                    logger.info("Updated observation with Langfuse prompt for semantic_scoring")
            except Exception as e:
                logger.warning(f"Could not get Langfuse prompt for generation tracking: {e}")
                langfuse_prompt = None

            # Log full config for debugging
            logger.info(f"Semantic scoring Langfuse config: {prompt_config}")

            # Use temperature from Langfuse config if available
            llm_kwargs = {}
            if prompt_config.get("temperature") is not None:
                llm_kwargs["temperature"] = prompt_config["temperature"]
                logger.info(
                    f"Using temperature {prompt_config['temperature']} from Langfuse prompt config for semantic scoring"
                )
            if prompt_config.get("max_tokens"):
                llm_kwargs["max_tokens"] = prompt_config["max_tokens"]

            # Update current observation with detailed context
            langfuse_context.update_current_observation(
                name=f"Semantic Scoring: {dimension} - {self.current_provider.value}",
                input={
                    "dimension": dimension,
                    "rule_based_score": rule_based_score,
                    "prompt_length": len(prompt_text),
                    "text_snippet": text[:150] + "..." if len(text) > 150 else text,
                    "context_summary": {
                        "company_terms_count": len(context.get("company_terms", [])),
                        "industries_count": len(context.get("core_industries", [])),
                    },
                },
                model=getattr(settings, "ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
                if self.current_provider.value == "anthropic"
                else getattr(settings, "OPENAI_MODEL", "gpt-4"),
                metadata={
                    "operation": "semantic_scoring",
                    "dimension": dimension,
                    "provider": self.current_provider.value,
                    "rule_based_score": rule_based_score,
                },
            )

            # Setup output parser
            parser = PydanticOutputParser(pydantic_object=SemanticScore)

            # Create a new LLM instance with config from Langfuse if needed
            if llm_kwargs:
                if hasattr(llm, "bind"):
                    configured_llm = llm.bind(**llm_kwargs)
                else:
                    configured_llm = llm
                    logger.warning("LLM doesn't support parameter binding, using default config")
            else:
                configured_llm = llm

            # Use the LLM without conflicting callback handlers
            # The @observe decorator handles Langfuse tracking
            llm_response = await configured_llm.ainvoke([HumanMessage(content=prompt_text)])
            result = parser.parse(llm_response.content)

            # Update observation with structured output
            langfuse_context.update_current_observation(
                output={
                    "semantic_score": result.semantic_score,
                    "confidence": result.confidence,
                    "reasoning_length": len(result.reasoning),
                    "key_factors_count": len(result.key_factors),
                    "score_improvement": result.semantic_score - rule_based_score,
                }
            )

            return result

        # Mock response
        mock_response = SemanticScore(
            provider=LLMProvider.MOCK,
            semantic_score=max(
                0.0, min(100.0, rule_based_score + (hash(text + dimension) % 21 - 10))
            ),
            confidence=0.6,
            reasoning=f"Mock semantic analysis for {dimension}",
            key_factors=[f"mock_factor_{dimension}", "text_analysis"],
        )

        return await self._execute_with_fallback("semantic_scoring", execute_scoring, mock_response)

    @observe()
    async def analyze_topics_batch(
        self, documents: list[str], context: dict[str, Any], session_id: Optional[str] = None
    ) -> list[TopicAnalysis]:
        """Analyze topics across multiple documents using LangChain with Langfuse integration."""

        # Update trace with session and meaningful tags
        langfuse_context.update_current_trace(
            name="Topic Clustering Session",
            session_id=session_id,
            tags=["topic-clustering"],
            metadata={
                "document_count": len(documents),
                "context_keys": list(context.keys()),
                "provider": self.current_provider.value,
            },
        )

        @observe(as_type="generation")
        async def execute_topic_analysis(llm: BaseChatModel) -> list[TopicAnalysis]:
            # Load prompt and config from prompt manager (FIRST - correct order!)
            # Truncate documents for analysis to avoid token limits
            truncated_docs = [doc[:500] + "..." if len(doc) > 500 else doc for doc in documents]

            prompt_data = await prompt_manager.get_prompt_with_config(
                "topic_clustering",
                variables={
                    "company_terms": context.get("company_terms", []),
                    "core_industries": context.get("core_industries", []),
                    "primary_markets": context.get("primary_markets", []),
                    "strategic_themes": context.get("strategic_themes", []),
                    "documents": str(truncated_docs),
                },
            )
            prompt_text = prompt_data["prompt"]
            prompt_config = prompt_data["config"]

            # Get Langfuse prompt object for generation tracking (AFTER prompt_manager!)
            try:
                if langfuse:
                    langfuse_prompt = langfuse.get_prompt(
                        name="topic_clustering", label="production"
                    )
                    # Update current observation with the prompt object for generation tracking
                    langfuse_context.update_current_observation(prompt=langfuse_prompt)
                    logger.info("Updated observation with Langfuse prompt for topic_clustering")
            except Exception as e:
                logger.warning(f"Could not get Langfuse prompt for generation tracking: {e}")

            # Log config for debugging
            logger.info(f"Topic clustering Langfuse config: {prompt_config}")

            # Use temperature from Langfuse config if available
            llm_kwargs = {}
            if prompt_config.get("temperature") is not None:
                llm_kwargs["temperature"] = prompt_config["temperature"]
                logger.info(
                    f"Using temperature {prompt_config['temperature']} from Langfuse prompt config for topic clustering"
                )
            if prompt_config.get("max_tokens"):
                llm_kwargs["max_tokens"] = prompt_config["max_tokens"]

            # Update current observation with detailed context
            langfuse_context.update_current_observation(
                name=f"Topic Clustering - {self.current_provider.value}",
                input={
                    "document_count": len(documents),
                    "prompt_length": len(prompt_text),
                    "total_text_length": sum(len(doc) for doc in documents),
                    "context_summary": {
                        "company_terms_count": len(context.get("company_terms", [])),
                        "industries_count": len(context.get("core_industries", [])),
                    },
                },
                model=getattr(settings, "ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
                if self.current_provider.value == "anthropic"
                else getattr(settings, "OPENAI_MODEL", "gpt-4"),
                metadata={
                    "operation": "topic_clustering",
                    "provider": self.current_provider.value,
                    "document_count": len(documents),
                },
            )

            # Setup output parser for list of topic analyses
            # Note: We'll parse as a list manually since PydanticOutputParser expects a single class

            class TopicAnalysisListParser:
                def parse(self, text: str) -> list[TopicAnalysis]:
                    try:
                        # Try to parse as JSON first
                        if text.strip().startswith("["):
                            data = json.loads(text)
                        else:
                            # Extract JSON from markdown code blocks
                            json_match = re.search(
                                r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL
                            )
                            if json_match:
                                data = json.loads(json_match.group(1))
                            else:
                                raise ValueError("No valid JSON array found")

                        return [TopicAnalysis(**item) for item in data]
                    except Exception as e:
                        logger.warning(f"Failed to parse topic analysis: {e}")
                        # Return empty list on parse error
                        return []

            parser = TopicAnalysisListParser()

            # Create a new LLM instance with config from Langfuse if needed
            if llm_kwargs:
                if hasattr(llm, "bind"):
                    configured_llm = llm.bind(**llm_kwargs)
                else:
                    configured_llm = llm
                    logger.warning("LLM doesn't support parameter binding, using default config")
            else:
                configured_llm = llm

            # Use the LLM without conflicting callback handlers
            # The @observe decorator handles Langfuse tracking
            llm_response = await configured_llm.ainvoke([HumanMessage(content=prompt_text)])
            result = parser.parse(llm_response.content)

            # Update observation with structured output
            langfuse_context.update_current_observation(
                output={
                    "topics_found": len(result),
                    "avg_confidence": sum(t.confidence for t in result) / len(result)
                    if result
                    else 0,
                    "topic_names": [t.topic_name for t in result],
                }
            )

            return result

        # Mock response
        mock_topics = [
            TopicAnalysis(
                topic_name="Policy Analysis",
                document_indices=list(range(min(len(documents), 3))),
                confidence=0.7,
                description="Mock topic cluster analysis",
            )
        ]

        return await self._execute_with_fallback(
            "topic_analysis", execute_topic_analysis, mock_topics
        )

    @observe()
    async def generate_report_insights(
        self,
        scoring_results: list[dict[str, Any]],
        context: dict[str, Any],
        session_id: Optional[str] = None,
    ) -> LLMReportInsights:
        """Generate report insights using LangChain with Langfuse integration."""

        # Update trace with session and meaningful tags
        langfuse_context.update_current_trace(
            name="Report Insights Generation Session",
            session_id=session_id,
            tags=["report-insights"],
            metadata={
                "results_count": len(scoring_results),
                "context_keys": list(context.keys()),
                "provider": self.current_provider.value,
            },
        )

        @observe(as_type="generation")
        async def execute_insights(llm: BaseChatModel) -> LLMReportInsights:
            # Prepare results summary for the prompt
            total_docs = len(scoring_results)
            high_priority = sum(1 for r in scoring_results if r.get("master_score", 0) >= 75)
            medium_priority = sum(1 for r in scoring_results if 50 <= r.get("master_score", 0) < 75)
            low_priority = sum(1 for r in scoring_results if r.get("master_score", 0) < 50)

            avg_score = (
                sum(r.get("master_score", 0) for r in scoring_results) / total_docs
                if total_docs > 0
                else 0
            )
            avg_confidence = (
                sum(r.get("confidence_score", 0) for r in scoring_results) / total_docs
                if total_docs > 0
                else 0
            )

            # Top findings
            top_results = sorted(
                scoring_results, key=lambda x: x.get("master_score", 0), reverse=True
            )[:5]
            top_findings = []
            for result in top_results:
                top_findings.append(
                    {
                        "score": result.get("master_score", 0),
                        "justification": result.get("overall_justification", "")[:200] + "..."
                        if len(result.get("overall_justification", "")) > 200
                        else result.get("overall_justification", ""),
                    }
                )

            high_pct = (high_priority / total_docs * 100) if total_docs > 0 else 0
            medium_pct = (medium_priority / total_docs * 100) if total_docs > 0 else 0
            low_pct = (low_priority / total_docs * 100) if total_docs > 0 else 0

            findings_text = "\n".join(
                [
                    f"{i+1}. Score {finding['score']}: {finding['justification']}"
                    for i, finding in enumerate(top_findings)
                ]
            )

            results_summary = f"""
Analysis Summary:
- Total Documents: {total_docs}
- High Priority (75+): {high_priority} ({high_pct:.1f}%)
- Medium Priority (50-74): {medium_priority} ({medium_pct:.1f}%)
- Low Priority (<50): {low_priority} ({low_pct:.1f}%)
- Average Score: {avg_score:.1f}
- Average Confidence: {avg_confidence:.2f}

Top 5 Findings:
{findings_text}"""

            # Load prompt and config from prompt manager (FIRST - correct order!)
            prompt_data = await prompt_manager.get_prompt_with_config(
                "report_insights",
                variables={
                    "company_terms": context.get("company_terms", []),
                    "core_industries": context.get("core_industries", []),
                    "primary_markets": context.get("primary_markets", []),
                    "strategic_themes": context.get("strategic_themes", []),
                    "results_summary": results_summary,
                },
            )
            prompt_text = prompt_data["prompt"]
            prompt_config = prompt_data["config"]

            # Get Langfuse prompt object for generation tracking (AFTER prompt_manager!)
            try:
                if langfuse:
                    langfuse_prompt = langfuse.get_prompt(
                        name="report_insights", label="production"
                    )
                    # Update current observation with the prompt object for generation tracking
                    langfuse_context.update_current_observation(prompt=langfuse_prompt)
                    logger.info("Updated observation with Langfuse prompt for report_insights")
            except Exception as e:
                logger.warning(f"Could not get Langfuse prompt for generation tracking: {e}")

            # Log config for debugging
            logger.info(f"Report insights Langfuse config: {prompt_config}")

            # Use temperature from Langfuse config if available
            llm_kwargs = {}
            if prompt_config.get("temperature") is not None:
                llm_kwargs["temperature"] = prompt_config["temperature"]
                logger.info(
                    f"Using temperature {prompt_config['temperature']} from Langfuse prompt config for report insights"
                )
            if prompt_config.get("max_tokens"):
                llm_kwargs["max_tokens"] = prompt_config["max_tokens"]

            # Update current observation with detailed context
            langfuse_context.update_current_observation(
                name=f"Report Insights - {self.current_provider.value}",
                input={
                    "results_count": len(scoring_results),
                    "prompt_length": len(prompt_text),
                    "high_priority_count": high_priority,
                    "avg_relevance_score": avg_score,
                },
                model=getattr(settings, "ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
                if self.current_provider.value == "anthropic"
                else getattr(settings, "OPENAI_MODEL", "gpt-4"),
                metadata={
                    "operation": "report_insights",
                    "provider": self.current_provider.value,
                    "results_count": len(scoring_results),
                },
            )

            # Setup custom output parser for report insights
            class ReportInsightsParser:
                def parse(self, text: str) -> LLMReportInsights:
                    try:
                        # Try to parse as JSON first
                        if text.strip().startswith("{"):
                            data = json.loads(text)
                        else:
                            # Extract JSON from markdown code blocks
                            json_match = re.search(
                                r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL
                            )
                            if json_match:
                                data = json.loads(json_match.group(1))
                            else:
                                raise ValueError("No valid JSON object found")

                        # Handle risk_assessment if it's an object
                        if isinstance(data.get("risk_assessment"), dict):
                            risk_data = data["risk_assessment"]
                            if "level" in risk_data and "primary_concerns" in risk_data:
                                data[
                                    "risk_assessment"
                                ] = f"{risk_data['level']}: {'; '.join(risk_data['primary_concerns'])}"
                            else:
                                data["risk_assessment"] = str(risk_data)

                        return LLMReportInsights(**data)
                    except Exception as e:
                        logger.warning(f"Failed to parse report insights: {e}")
                        # Return mock response on parse error
                        return LLMReportInsights(
                            executive_summary="Analysis completed with mixed results",
                            key_findings=["Default finding"],
                            recommendations=["Review analysis"],
                            risk_assessment="Medium",
                            confidence=0.6,
                        )

            parser = ReportInsightsParser()

            # Create a new LLM instance with config from Langfuse if needed
            if llm_kwargs:
                if hasattr(llm, "bind"):
                    configured_llm = llm.bind(**llm_kwargs)
                else:
                    configured_llm = llm
                    logger.warning("LLM doesn't support parameter binding, using default config")
            else:
                configured_llm = llm

            # Use the LLM without conflicting callback handlers
            # The @observe decorator handles Langfuse tracking
            llm_response = await configured_llm.ainvoke([HumanMessage(content=prompt_text)])
            result = parser.parse(llm_response.content)

            # Update observation with structured output
            langfuse_context.update_current_observation(
                output={
                    "executive_summary_length": len(result.executive_summary),
                    "key_findings_count": len(result.key_findings),
                    "recommendations_count": len(result.recommendations),
                    "confidence": result.confidence,
                }
            )

            return result

        mock_response = LLMReportInsights(
            provider=LLMProvider.MOCK,
            executive_summary="Mock executive summary of monitoring results.",
            key_findings=["Mock finding 1", "Mock finding 2"],
            recommendations=["Mock recommendation 1", "Mock recommendation 2"],
            risk_assessment="Mock risk assessment",
            confidence=0.6,
        )

        # Execute directly without fallback wrapper to maintain Langfuse context
        if not self.enabled:
            logger.debug("LLM disabled, returning mock response for report_insights")
            return mock_response

        try:
            # Try primary LLM
            if self.primary_llm:
                result = await execute_insights(self.primary_llm)
                logger.debug(
                    f"Successfully executed report_insights with {self.current_provider.value}"
                )
                return result
        except Exception as e:
            logger.warning("Primary LLM failed for report_insights", error=str(e))

            # Try fallback LLM
            if self.fallback_llm:
                try:
                    result = await execute_insights(self.fallback_llm)
                    logger.info("Fallback LLM succeeded for report_insights")
                    return result
                except Exception as e2:
                    logger.warning("Fallback LLM also failed for report_insights", error=str(e2))

        # Return mock response as final fallback
        logger.info("Using mock response for report_insights")
        return mock_response

    def _extract_mock_topics(self, text: str, context: dict[str, Any]) -> list[str]:
        """Extract mock topics based on context and text."""
        topics = []

        # Check for context terms in text
        company_terms = context.get("company_terms", [])
        for term in company_terms:
            if term.lower() in text.lower():
                topics.append(term.lower())

        # Add some generic topics
        generic_topics = ["policy", "regulation", "government"]
        for topic in generic_topics:
            if topic in text.lower():
                topics.append(topic)

        return topics[:5]  # Limit to 5 topics

    async def health_check(self) -> dict[str, Any]:
        """Check health of LLM services."""
        status = {
            "enabled": self.enabled,
            "primary_provider": self.current_provider.value if self.enabled else "none",
            "fallback_available": self.fallback_llm is not None,
            "langchain_version": "0.2.16",
        }

        if self.enabled and self.primary_llm:
            try:
                # Test with simple message
                test_message = HumanMessage(content="Health check")
                response = await self.primary_llm.ainvoke([test_message])
                status["primary_status"] = "healthy"
                status["test_response_length"] = len(response.content)
            except Exception as e:
                status["primary_status"] = "unhealthy"
                status["primary_error"] = str(e)

        return status


# Global instance
langchain_llm_service = LangChainLLMService()
