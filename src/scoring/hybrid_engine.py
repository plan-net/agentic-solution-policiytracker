"""Hybrid scoring engine combining rule-based and LLM semantic scoring."""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

import structlog

from src.models.content import ProcessedContent
from src.models.scoring import ScoringResult
from src.scoring.relevance_engine import RelevanceEngine
from src.llm.langchain_service import langchain_llm_service
from src.llm.models import SemanticScore, DocumentInsight
from src.config import settings

logger = structlog.get_logger()


class HybridScoringEngine:
    """Enhanced scoring engine with LLM semantic analysis."""

    def __init__(self, context: Dict[str, Any]):
        self.context = context
        self.rule_based_engine = RelevanceEngine(context)
        self.llm_enabled = settings.LLM_ENABLED and settings.LLM_FALLBACK_ENABLED

    async def score_document_hybrid(self, document: ProcessedContent, job_id: Optional[str] = None) -> ScoringResult:
        """Score document using hybrid rule-based + LLM approach."""
        try:
            logger.debug(
                "Starting hybrid scoring", document_id=document.id, llm_enabled=self.llm_enabled
            )

            # Step 1: Get rule-based scores (always run for fallback)
            rule_based_result = await self.rule_based_engine.score_document(document)

            if not self.llm_enabled:
                logger.debug("LLM disabled, using rule-based scores only", document_id=document.id)
                return rule_based_result

            # Step 2: Get LLM document insights in parallel with semantic scoring
            insights_task = asyncio.create_task(
                langchain_llm_service.analyze_document(document.raw_text, self.context, session_id=job_id)
            )

            # Step 3: Get LLM semantic scores for each dimension in parallel
            semantic_scoring_tasks = []
            for dim_name, dim_score in rule_based_result.dimension_scores.items():
                task = asyncio.create_task(
                    langchain_llm_service.score_dimension_semantic(
                        document.raw_text, dim_name, self.context, dim_score.score, session_id=job_id
                    )
                )
                semantic_scoring_tasks.append(task)

            # Wait for all LLM operations to complete
            all_tasks = [insights_task] + semantic_scoring_tasks
            results = await asyncio.gather(*all_tasks, return_exceptions=True)

            insights = results[0]
            semantic_scores = results[1:]

            # Handle exceptions in LLM operations
            if isinstance(insights, Exception):
                logger.warning(
                    "LLM insights failed, using fallback",
                    document_id=document.id,
                    error=str(insights),
                )
                insights = DocumentInsight(
                    key_topics=["LLM analysis unavailable"],
                    sentiment="unknown",
                    urgency_level="low",
                    confidence=0.1,
                    summary="LLM insights failed",
                )

            # Handle individual semantic score exceptions
            valid_semantic_scores = []
            for i, score in enumerate(semantic_scores):
                if isinstance(score, Exception):
                    logger.warning(
                        "Individual semantic scoring failed",
                        document_id=document.id,
                        dimension=list(rule_based_result.dimension_scores.keys())[i],
                        error=str(score),
                    )
                else:
                    valid_semantic_scores.append(score)
            semantic_scores = valid_semantic_scores

            # Step 4: Combine rule-based and semantic scores
            enhanced_result = self._create_hybrid_result(
                rule_based_result, semantic_scores, insights, document
            )

            logger.debug(
                "Hybrid scoring completed",
                document_id=document.id,
                rule_score=rule_based_result.master_score,
                hybrid_score=enhanced_result.master_score,
            )

            return enhanced_result

        except Exception as e:
            logger.error(
                "Hybrid scoring failed, falling back to rule-based",
                document_id=document.id,
                error=str(e),
            )
            return rule_based_result

    def _create_hybrid_result(
        self,
        rule_based_result: ScoringResult,
        semantic_scores: list[SemanticScore],
        insights: DocumentInsight,
        document: ProcessedContent,
    ) -> ScoringResult:
        """Create enhanced scoring result combining rule-based and LLM analysis."""

        # Create map of semantic scores by dimension
        dimension_names = list(rule_based_result.dimension_scores.keys())
        semantic_score_map = {}
        for i, semantic_score in enumerate(semantic_scores):
            if i < len(dimension_names):
                semantic_score_map[dimension_names[i]] = semantic_score

        # Update dimension scores with semantic analysis
        enhanced_dimension_scores = {}
        total_weighted_score = 0.0
        total_weight = 0.0

        for dim_name, rule_dim_score in rule_based_result.dimension_scores.items():
            semantic_score = semantic_score_map.get(dim_name)

            if semantic_score:
                # Create hybrid score (weighted combination)
                semantic_weight = 0.7  # Give more weight to LLM when available
                rule_weight = 0.3
                final_score = (
                    semantic_score.semantic_score * semantic_weight
                    + rule_dim_score.score * rule_weight
                )

                # Enhanced justification combining rule-based and LLM reasoning
                enhanced_justification = self._combine_justifications(
                    rule_dim_score.justification, semantic_score.reasoning
                )

                # Enhanced evidence combining both sources
                enhanced_evidence = list(
                    set(rule_dim_score.evidence_snippets + semantic_score.key_factors)
                )[:3]  # Keep max 3 unique pieces of evidence

            else:
                # Fallback to rule-based score
                final_score = rule_dim_score.score
                enhanced_justification = (
                    rule_dim_score.justification + " (LLM analysis unavailable)"
                )
                enhanced_evidence = rule_dim_score.evidence_snippets

            # Update dimension score
            enhanced_dimension_scores[dim_name] = type(rule_dim_score)(
                dimension_name=dim_name,
                score=final_score,
                weight=rule_dim_score.weight,
                justification=enhanced_justification,
                evidence_snippets=enhanced_evidence,
            )

            # Accumulate for master score calculation
            total_weighted_score += final_score * rule_dim_score.weight
            total_weight += rule_dim_score.weight

        # Calculate hybrid master score
        hybrid_master_score = total_weighted_score / total_weight if total_weight > 0 else 0

        # Enhanced overall justification incorporating LLM insights
        enhanced_justification = self._create_enhanced_justification(
            rule_based_result.overall_justification, insights, hybrid_master_score
        )

        # Enhanced key factors incorporating LLM themes
        enhanced_key_factors = self._create_enhanced_key_factors(
            rule_based_result.key_factors, insights
        )

        # Calculate enhanced confidence (consider LLM confidence)
        enhanced_confidence = self._calculate_enhanced_confidence(
            rule_based_result.confidence_score,
            insights.confidence,
            len([s for s in semantic_scores if s.confidence > 0.7]),
        )

        # Create hybrid result
        return ScoringResult(
            document_id=document.id,
            master_score=round(hybrid_master_score, 1),
            dimension_scores=enhanced_dimension_scores,
            confidence_score=enhanced_confidence,
            topic_clusters=self._extract_topic_clusters(insights),
            scoring_timestamp=datetime.now(),
            processing_time_ms=rule_based_result.processing_time_ms,  # Will be updated by caller
            overall_justification=enhanced_justification,
            key_factors=enhanced_key_factors,
        )

    def _combine_justifications(self, rule_based: str, llm_reasoning: str) -> str:
        """Combine rule-based and LLM justifications."""
        if not llm_reasoning or "unavailable" in llm_reasoning.lower():
            return rule_based

        return f"{rule_based}. LLM analysis: {llm_reasoning}"

    def _create_enhanced_justification(
        self, rule_justification: str, insights: DocumentInsight, hybrid_score: float
    ) -> str:
        """Create enhanced overall justification."""

        base_justification = rule_justification

        if insights.confidence > 0.5:
            # Add LLM insights to justification
            llm_additions = []

            if insights.key_topics:
                themes_str = ", ".join(insights.key_topics[:3])
                llm_additions.append(f"key themes: {themes_str}")

            if insights.sentiment and insights.sentiment != "neutral":
                llm_additions.append(f"sentiment analysis: {insights.sentiment}")

            if insights.urgency_level and insights.urgency_level != "medium":
                llm_additions.append("time-sensitive elements detected")

            if llm_additions:
                base_justification += f". Enhanced analysis reveals {'; '.join(llm_additions)}"

        return base_justification

    def _create_enhanced_key_factors(
        self, rule_factors: list[str], insights: DocumentInsight
    ) -> list[str]:
        """Create enhanced key factors list."""

        enhanced_factors = rule_factors.copy()

        # Add LLM-identified themes as factors
        if insights.confidence > 0.6:
            for theme in insights.key_topics[:2]:  # Add top 2 themes
                factor = f"LLM-identified theme: {theme}"
                if factor not in enhanced_factors:
                    enhanced_factors.append(factor)

            # Add urgency indicators
            if insights.urgency_level == "high":
                factor = "High urgency level identified by LLM analysis"
                enhanced_factors.append(factor)

        return enhanced_factors[:5]  # Keep max 5 factors

    def _calculate_enhanced_confidence(
        self, rule_confidence: float, llm_confidence: float, high_confidence_semantic_scores: int
    ) -> float:
        """Calculate enhanced confidence score."""

        if llm_confidence < 0.3:  # Low LLM confidence
            return rule_confidence * 0.9  # Slight reduction

        # Weighted combination of confidences
        base_enhanced = (rule_confidence * 0.6) + (llm_confidence * 0.4)

        # Boost if multiple semantic scores have high confidence
        semantic_boost = min(0.1, high_confidence_semantic_scores * 0.02)

        return min(1.0, base_enhanced + semantic_boost)

    def _extract_topic_clusters(self, insights: DocumentInsight) -> list[str]:
        """Extract topic clusters from LLM insights."""
        clusters = []

        # Use key themes as topic clusters
        for theme in insights.key_topics[:3]:  # Max 3 clusters
            # Clean and standardize theme names
            clean_theme = theme.lower().replace(" ", "_")
            clusters.append(clean_theme)

        return clusters

    async def batch_score_hybrid(self, documents: list[ProcessedContent]) -> list[ScoringResult]:
        """Score multiple documents using hybrid approach."""

        # Limit concurrent scoring to avoid overwhelming LLM APIs
        max_concurrent = getattr(settings, "LLM_MAX_CONCURRENT", 3)
        semaphore = asyncio.Semaphore(max_concurrent)

        async def score_single(doc):
            async with semaphore:
                return await self.score_document_hybrid(doc)

        tasks = [score_single(doc) for doc in documents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        scoring_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Hybrid scoring failed for document {i}", error=str(result))
                # Fallback to rule-based scoring
                try:
                    fallback_result = await self.rule_based_engine.score_document(documents[i])
                    scoring_results.append(fallback_result)
                except Exception as e:
                    logger.error(f"Fallback scoring also failed for document {i}", error=str(e))
                    # Skip this document
                    continue
            else:
                scoring_results.append(result)

        return scoring_results
