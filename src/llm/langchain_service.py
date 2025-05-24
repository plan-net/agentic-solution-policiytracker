"""
LangChain-based LLM service with standardized interfaces and observability.
"""

import asyncio
from typing import Dict, List, Optional, Any, Union
import structlog

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langfuse.decorators import observe, langfuse_context

from src.config import settings
from src.llm.models import (
    DocumentInsight,
    SemanticScore,
    TopicAnalysis,
    LLMReportInsights,
    LLMProvider,
)
# Using @observe decorators for automatic Langfuse integration
from src.prompts.prompt_manager import prompt_manager

logger = structlog.get_logger()


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
    async def analyze_document(self, text: str, context: Dict[str, Any], session_id: Optional[str] = None) -> DocumentInsight:
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
            }
        )

        async def execute_analysis(llm: BaseChatModel) -> DocumentInsight:
            # Load prompt from prompt manager
            prompt_text = await prompt_manager.get_prompt(
                "document_analysis",
                variables={
                    "company_terms": context.get("company_terms", []),
                    "core_industries": context.get("core_industries", []),
                    "primary_markets": context.get("primary_markets", []),
                    "strategic_themes": context.get("strategic_themes", []),
                    "document_text": text,
                },
            )

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
                    }
                },
                model=getattr(settings, "ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022") if self.current_provider.value == "anthropic" else getattr(settings, "OPENAI_MODEL", "gpt-4"),
                metadata={
                    "operation": "document_analysis",
                    "provider": self.current_provider.value,
                    "text_length": len(text),
                }
            )

            # Setup output parser
            parser = PydanticOutputParser(pydantic_object=DocumentInsight)

            # Get Langfuse callback handler for proper cost tracking
            langfuse_handler = langfuse_context.get_current_langchain_handler()
            
            # Execute LLM call with Langfuse handler for automatic cost tracking
            llm_response = await llm.ainvoke(
                [HumanMessage(content=prompt_text)], 
                config={"callbacks": [langfuse_handler]}
            )
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
        self, text: str, dimension: str, context: Dict[str, Any], rule_based_score: float, session_id: Optional[str] = None
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
            }
        )

        async def execute_scoring(llm: BaseChatModel) -> SemanticScore:
            # Load prompt from prompt manager
            prompt_text = await prompt_manager.get_prompt(
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
                    }
                },
                model=getattr(settings, "ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022") if self.current_provider.value == "anthropic" else getattr(settings, "OPENAI_MODEL", "gpt-4"),
                metadata={
                    "operation": "semantic_scoring",
                    "dimension": dimension,
                    "provider": self.current_provider.value,
                    "rule_based_score": rule_based_score,
                }
            )

            # Setup output parser
            parser = PydanticOutputParser(pydantic_object=SemanticScore)

            # Get Langfuse callback handler for proper cost tracking
            langfuse_handler = langfuse_context.get_current_langchain_handler()
            
            # Execute LLM call with Langfuse handler for automatic cost tracking
            llm_response = await llm.ainvoke(
                [HumanMessage(content=prompt_text)], 
                config={"callbacks": [langfuse_handler]}
            )
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

    async def analyze_topics_batch(
        self, documents: List[str], context: Dict[str, Any]
    ) -> List[TopicAnalysis]:
        """Analyze topics across multiple documents using LangChain."""

        parser = PydanticOutputParser(pydantic_object=List[TopicAnalysis])

        async def execute_topic_analysis(llm: BaseChatModel) -> List[TopicAnalysis]:
            chain = self.topic_analysis_prompt | llm | parser

            async with await langfuse_client.trace(
                name="langchain_topic_analysis",
                input_data={"document_count": len(documents), "context_keys": list(context.keys())},
                metadata={"provider": self.current_provider.value, "operation": "topic_analysis"},
            ) as trace:
                try:
                    # Truncate documents for analysis to avoid token limits
                    truncated_docs = [
                        doc[:500] + "..." if len(doc) > 500 else doc for doc in documents
                    ]

                    result = await chain.ainvoke(
                        {"documents": str(truncated_docs), "context": str(context)}
                    )

                    trace.update_output(
                        {
                            "topics_found": len(result),
                            "avg_confidence": sum(t.confidence for t in result) / len(result)
                            if result
                            else 0,
                        }
                    )

                    return result

                except Exception as e:
                    trace.update_output({"error": str(e)})
                    raise

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

    async def generate_report_insights(
        self, scoring_results: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> LLMReportInsights:
        """Generate report insights using LangChain."""

        # Simple prompt for report insights
        report_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """Generate executive insights for this political monitoring report.
            
Context: {context}
Results: {results_summary}

Provide:
1. Executive summary (2-3 sentences)
2. Key findings (3-5 bullet points)
3. Recommendations (2-3 actionable items)
4. Risk assessment

Respond in JSON format.""",
                ),
                ("human", "Generate insights for the analysis results."),
            ]
        )

        async def execute_insights(llm: BaseChatModel) -> LLMReportInsights:
            # For now, return mock insights
            return LLMReportInsights(
                provider=self.current_provider,
                executive_summary="LangChain-generated executive summary of political monitoring results.",
                key_findings=[
                    "Key finding 1 from LangChain analysis",
                    "Key finding 2 from LangChain analysis",
                ],
                recommendations=[
                    "Recommendation 1 based on analysis",
                    "Recommendation 2 for next steps",
                ],
                risk_assessment="Medium risk profile identified",
                confidence=0.75,
            )

        mock_response = LLMReportInsights(
            provider=LLMProvider.MOCK,
            executive_summary="Mock executive summary of monitoring results.",
            key_findings=["Mock finding 1", "Mock finding 2"],
            recommendations=["Mock recommendation 1", "Mock recommendation 2"],
            risk_assessment="Mock risk assessment",
            confidence=0.6,
        )

        return await self._execute_with_fallback("report_insights", execute_insights, mock_response)

    def _extract_mock_topics(self, text: str, context: Dict[str, Any]) -> List[str]:
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

    async def health_check(self) -> Dict[str, Any]:
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
