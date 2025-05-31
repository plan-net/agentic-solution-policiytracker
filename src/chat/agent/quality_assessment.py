"""
Response quality assessment and improvement system for multi-agent orchestrator.
Implements comprehensive quality metrics and feedback mechanisms.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class QualityDimension(Enum):
    """Quality assessment dimensions."""
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy" 
    RELEVANCE = "relevance"
    CLARITY = "clarity"
    COHERENCE = "coherence"
    TIMELINESS = "timeliness"
    ACTIONABILITY = "actionability"
    SOURCE_QUALITY = "source_quality"


@dataclass
class QualityMetrics:
    """Container for quality assessment metrics."""
    overall_score: float
    dimension_scores: Dict[QualityDimension, float]
    confidence_level: float
    improvement_suggestions: List[str]
    quality_indicators: Dict[str, Any]
    assessment_metadata: Dict[str, Any]


class ResponseQualityAssessment:
    """Comprehensive response quality assessment system."""
    
    def __init__(self):
        self.quality_thresholds = {
            QualityDimension.COMPLETENESS: 0.75,
            QualityDimension.ACCURACY: 0.80,
            QualityDimension.RELEVANCE: 0.85,
            QualityDimension.CLARITY: 0.70,
            QualityDimension.COHERENCE: 0.75,
            QualityDimension.TIMELINESS: 0.70,
            QualityDimension.ACTIONABILITY: 0.65,
            QualityDimension.SOURCE_QUALITY: 0.80
        }
        
        self.quality_weights = {
            QualityDimension.COMPLETENESS: 0.20,
            QualityDimension.ACCURACY: 0.20,
            QualityDimension.RELEVANCE: 0.15,
            QualityDimension.CLARITY: 0.10,
            QualityDimension.COHERENCE: 0.10,
            QualityDimension.TIMELINESS: 0.10,
            QualityDimension.ACTIONABILITY: 0.10,
            QualityDimension.SOURCE_QUALITY: 0.05
        }
    
    async def assess_response_quality(
        self,
        response: str,
        query: str,
        query_analysis: Dict[str, Any],
        tool_results: List[Dict[str, Any]],
        execution_metadata: Dict[str, Any],
        response_metadata: Dict[str, Any]
    ) -> QualityMetrics:
        """Comprehensive quality assessment of agent response."""
        
        try:
            # Assess each quality dimension
            dimension_scores = {}
            
            dimension_scores[QualityDimension.COMPLETENESS] = await self._assess_completeness(
                response, query, query_analysis, tool_results
            )
            
            dimension_scores[QualityDimension.ACCURACY] = await self._assess_accuracy(
                response, tool_results, response_metadata
            )
            
            dimension_scores[QualityDimension.RELEVANCE] = await self._assess_relevance(
                response, query, query_analysis
            )
            
            dimension_scores[QualityDimension.CLARITY] = await self._assess_clarity(
                response, query_analysis
            )
            
            dimension_scores[QualityDimension.COHERENCE] = await self._assess_coherence(
                response
            )
            
            dimension_scores[QualityDimension.TIMELINESS] = await self._assess_timeliness(
                response, tool_results, execution_metadata
            )
            
            dimension_scores[QualityDimension.ACTIONABILITY] = await self._assess_actionability(
                response, query, query_analysis
            )
            
            dimension_scores[QualityDimension.SOURCE_QUALITY] = await self._assess_source_quality(
                response, tool_results
            )
            
            # Calculate overall score
            overall_score = sum(
                score * self.quality_weights[dimension]
                for dimension, score in dimension_scores.items()
            )
            
            # Generate improvement suggestions
            improvement_suggestions = await self._generate_improvement_suggestions(
                dimension_scores, response, query_analysis
            )
            
            # Calculate confidence level
            confidence_level = self._calculate_confidence_level(
                dimension_scores, execution_metadata, response_metadata
            )
            
            # Generate quality indicators
            quality_indicators = await self._generate_quality_indicators(
                response, tool_results, execution_metadata
            )
            
            # Create assessment metadata
            assessment_metadata = {
                "assessment_timestamp": datetime.now().isoformat(),
                "quality_version": "1.0",
                "dimensions_assessed": len(dimension_scores),
                "threshold_violations": sum(
                    1 for dim, score in dimension_scores.items()
                    if score < self.quality_thresholds[dim]
                )
            }
            
            return QualityMetrics(
                overall_score=overall_score,
                dimension_scores=dimension_scores,
                confidence_level=confidence_level,
                improvement_suggestions=improvement_suggestions,
                quality_indicators=quality_indicators,
                assessment_metadata=assessment_metadata
            )
            
        except Exception as e:
            logger.error(f"Quality assessment failed: {e}")
            return self._create_fallback_metrics()
    
    async def _assess_completeness(
        self,
        response: str,
        query: str,
        query_analysis: Dict[str, Any],
        tool_results: List[Dict[str, Any]]
    ) -> float:
        """Assess response completeness against query requirements."""
        
        score = 0.5  # Base score
        
        # Check if response addresses primary entity
        primary_entity = query_analysis.get("primary_entity", "")
        if primary_entity and primary_entity.lower() in response.lower():
            score += 0.2
        
        # Check coverage of secondary entities
        secondary_entities = query_analysis.get("secondary_entities", [])
        if secondary_entities:
            entity_coverage = sum(
                1 for entity in secondary_entities
                if entity.lower() in response.lower()
            ) / len(secondary_entities)
            score += 0.15 * entity_coverage
        
        # Check if expected information types are covered
        expected_types = query_analysis.get("expected_information_types", [])
        if expected_types:
            # Simple keyword-based assessment
            type_coverage = 0
            for info_type in expected_types:
                if any(keyword in response.lower() for keyword in info_type.split("_")):
                    type_coverage += 1
            score += 0.15 * (type_coverage / len(expected_types))
        
        # Response length assessment (comprehensive responses should be substantial)
        if len(response) > 800:
            score += 0.1
        elif len(response) > 400:
            score += 0.05
        
        return min(1.0, score)
    
    async def _assess_accuracy(
        self,
        response: str,
        tool_results: List[Dict[str, Any]],
        response_metadata: Dict[str, Any]
    ) -> float:
        """Assess response accuracy based on source quality and consistency."""
        
        score = 0.6  # Base score for AI-generated content
        
        # Source quality assessment
        source_count = response_metadata.get("source_count", 0)
        if source_count >= 5:
            score += 0.2
        elif source_count >= 3:
            score += 0.15
        elif source_count >= 1:
            score += 0.1
        
        # Tool result quality assessment
        if tool_results:
            avg_tool_quality = sum(
                result.get("quality_score", 0.5) for result in tool_results
            ) / len(tool_results)
            score += 0.2 * avg_tool_quality
        
        # Consistency with tool results
        if tool_results:
            consistency_score = self._assess_tool_consistency(response, tool_results)
            score += 0.1 * consistency_score
        
        return min(1.0, score)
    
    async def _assess_relevance(
        self,
        response: str,
        query: str,
        query_analysis: Dict[str, Any]
    ) -> float:
        """Assess response relevance to the original query."""
        
        score = 0.5  # Base score
        
        # Intent matching
        intent = query_analysis.get("intent", "")
        if intent == "information_seeking" and any(
            keyword in response.lower() 
            for keyword in ["provides", "explains", "describes", "details"]
        ):
            score += 0.2
        elif intent == "analysis" and any(
            keyword in response.lower()
            for keyword in ["analysis", "assessment", "evaluation", "comparison"]
        ):
            score += 0.2
        
        # Query keyword coverage
        query_words = set(query.lower().split())
        response_words = set(response.lower().split())
        keyword_overlap = len(query_words.intersection(response_words)) / len(query_words)
        score += 0.2 * keyword_overlap
        
        # Topic focus assessment
        primary_entity = query_analysis.get("primary_entity", "")
        if primary_entity:
            entity_mentions = response.lower().count(primary_entity.lower())
            if entity_mentions >= 3:
                score += 0.1
            elif entity_mentions >= 1:
                score += 0.05
        
        return min(1.0, score)
    
    async def _assess_clarity(self, response: str, query_analysis: Dict[str, Any]) -> float:
        """Assess response clarity and readability."""
        
        score = 0.6  # Base score
        
        # Structure assessment
        if "##" in response or "###" in response:  # Has headings
            score += 0.15
        
        if response.count("\n") >= 5:  # Well-structured paragraphs
            score += 0.1
        
        # Sentence length assessment (avoid overly complex sentences)
        sentences = re.split(r'[.!?]+', response)
        if sentences:
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
            if 10 <= avg_sentence_length <= 25:  # Optimal range
                score += 0.1
            elif avg_sentence_length <= 35:  # Acceptable
                score += 0.05
        
        # Complexity assessment based on user preferences
        complexity = query_analysis.get("complexity", "medium")
        if complexity == "simple" and len(response) < 600:
            score += 0.1
        elif complexity == "complex" and len(response) > 800:
            score += 0.05
        
        return min(1.0, score)
    
    async def _assess_coherence(self, response: str) -> float:
        """Assess response coherence and logical flow."""
        
        score = 0.7  # Base score
        
        # Transition words assessment
        transition_words = [
            "however", "therefore", "furthermore", "additionally", "moreover",
            "consequently", "nevertheless", "meanwhile", "subsequently"
        ]
        
        transition_count = sum(
            1 for word in transition_words
            if word in response.lower()
        )
        
        if transition_count >= 3:
            score += 0.15
        elif transition_count >= 1:
            score += 0.1
        
        # Paragraph coherence (simple assessment)
        paragraphs = response.split("\n\n")
        if len(paragraphs) >= 3:
            score += 0.1
        
        # Conclusion presence
        if any(
            keyword in response.lower()
            for keyword in ["conclusion", "summary", "in summary", "overall"]
        ):
            score += 0.05
        
        return min(1.0, score)
    
    async def _assess_timeliness(
        self,
        response: str,
        tool_results: List[Dict[str, Any]],
        execution_metadata: Dict[str, Any]
    ) -> float:
        """Assess response timeliness and currency of information."""
        
        score = 0.6  # Base score
        
        # Check for temporal indicators
        current_year = datetime.now().year
        if str(current_year) in response or str(current_year - 1) in response:
            score += 0.2
        
        # Tool result freshness
        if tool_results:
            temporal_info = []
            for result in tool_results:
                temporal_aspects = result.get("temporal_aspects", [])
                temporal_info.extend(temporal_aspects)
            
            if temporal_info:
                score += 0.15
        
        # Execution time efficiency
        execution_time = execution_metadata.get("total_execution_time", 0)
        if execution_time <= 10:
            score += 0.05
        elif execution_time <= 20:
            score += 0.03
        
        return min(1.0, score)
    
    async def _assess_actionability(
        self,
        response: str,
        query: str,
        query_analysis: Dict[str, Any]
    ) -> float:
        """Assess response actionability and practical value."""
        
        score = 0.5  # Base score
        
        # Action word presence
        action_words = [
            "should", "must", "need to", "recommend", "suggest", "consider",
            "implement", "ensure", "compliance", "steps", "requirements"
        ]
        
        action_count = sum(
            1 for word in action_words
            if word in response.lower()
        )
        
        if action_count >= 5:
            score += 0.2
        elif action_count >= 3:
            score += 0.15
        elif action_count >= 1:
            score += 0.1
        
        # Specific guidance presence
        if any(
            keyword in response.lower()
            for keyword in ["steps", "process", "procedure", "guide", "instructions"]
        ):
            score += 0.15
        
        # Context-specific actionability
        intent = query_analysis.get("intent", "")
        if intent in ["compliance", "implementation", "how_to"]:
            if any(
                keyword in response.lower()
                for keyword in ["compliance", "implementation", "timeline", "deadline"]
            ):
                score += 0.15
        
        return min(1.0, score)
    
    async def _assess_source_quality(
        self,
        response: str,
        tool_results: List[Dict[str, Any]]
    ) -> float:
        """Assess quality and credibility of sources."""
        
        score = 0.6  # Base score
        
        # Source citations in response
        if any(
            keyword in response.lower()
            for keyword in ["source", "according to", "based on", "official", "regulation"]
        ):
            score += 0.2
        
        # Tool result source quality
        if tool_results:
            source_quality_scores = []
            for result in tool_results:
                citations = result.get("source_citations", [])
                if citations:
                    # Assess citation quality (simple heuristic)
                    official_sources = sum(
                        1 for citation in citations
                        if any(keyword in citation.lower() for keyword in [
                            "official", "government", "regulation", "directive", "commission"
                        ])
                    )
                    citation_quality = official_sources / len(citations) if citations else 0
                    source_quality_scores.append(citation_quality)
            
            if source_quality_scores:
                avg_source_quality = sum(source_quality_scores) / len(source_quality_scores)
                score += 0.2 * avg_source_quality
        
        return min(1.0, score)
    
    def _assess_tool_consistency(self, response: str, tool_results: List[Dict[str, Any]]) -> float:
        """Assess consistency between response and tool results."""
        
        if not tool_results:
            return 0.5
        
        consistency_score = 0.0
        
        for result in tool_results:
            if result.get("success", False):
                # Check if tool insights are reflected in response
                insights = result.get("insights", [])
                for insight in insights:
                    if any(word in response.lower() for word in insight.lower().split()):
                        consistency_score += 0.1
                
                # Check entity consistency
                entities = result.get("entities_found", [])
                for entity in entities:
                    entity_name = entity.get("name", "")
                    if entity_name.lower() in response.lower():
                        consistency_score += 0.05
        
        return min(1.0, consistency_score)
    
    async def _generate_improvement_suggestions(
        self,
        dimension_scores: Dict[QualityDimension, float],
        response: str,
        query_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate specific improvement suggestions based on quality assessment."""
        
        suggestions = []
        
        # Check each dimension against thresholds
        for dimension, score in dimension_scores.items():
            threshold = self.quality_thresholds[dimension]
            
            if score < threshold:
                if dimension == QualityDimension.COMPLETENESS:
                    suggestions.append(
                        "Expand response to cover more secondary entities and expected information types"
                    )
                elif dimension == QualityDimension.ACCURACY:
                    suggestions.append(
                        "Include more authoritative sources and verify consistency with tool results"
                    )
                elif dimension == QualityDimension.RELEVANCE:
                    suggestions.append(
                        "Focus more directly on the specific query intent and primary entities"
                    )
                elif dimension == QualityDimension.CLARITY:
                    suggestions.append(
                        "Improve response structure with clear headings and shorter sentences"
                    )
                elif dimension == QualityDimension.COHERENCE:
                    suggestions.append(
                        "Add more transition words and logical flow between sections"
                    )
                elif dimension == QualityDimension.TIMELINESS:
                    suggestions.append(
                        "Include more current information and recent developments"
                    )
                elif dimension == QualityDimension.ACTIONABILITY:
                    suggestions.append(
                        "Add more specific guidance, steps, or actionable recommendations"
                    )
                elif dimension == QualityDimension.SOURCE_QUALITY:
                    suggestions.append(
                        "Include more official sources and regulatory citations"
                    )
        
        # Global improvement suggestions
        if len(response) < 300:
            suggestions.append("Provide more comprehensive analysis and detail")
        
        if not any(char in response for char in ["#", "*", "-"]):
            suggestions.append("Use formatting elements to improve readability")
        
        return suggestions[:5]  # Limit to top 5 suggestions
    
    def _calculate_confidence_level(
        self,
        dimension_scores: Dict[QualityDimension, float],
        execution_metadata: Dict[str, Any],
        response_metadata: Dict[str, Any]
    ) -> float:
        """Calculate confidence level for the quality assessment."""
        
        # Base confidence from dimension score variance
        scores = list(dimension_scores.values())
        avg_score = sum(scores) / len(scores)
        variance = sum((score - avg_score) ** 2 for score in scores) / len(scores)
        base_confidence = max(0.5, 1.0 - variance)
        
        # Adjust based on execution quality
        tools_successful = execution_metadata.get("tools_successful", 0)
        tools_failed = execution_metadata.get("tools_failed", 0)
        total_tools = tools_successful + tools_failed
        
        if total_tools > 0:
            tool_success_rate = tools_successful / total_tools
            base_confidence = (base_confidence + tool_success_rate) / 2
        
        # Adjust based on response metadata
        source_count = response_metadata.get("source_count", 0)
        if source_count >= 3:
            base_confidence += 0.1
        elif source_count >= 1:
            base_confidence += 0.05
        
        return min(1.0, base_confidence)
    
    async def _generate_quality_indicators(
        self,
        response: str,
        tool_results: List[Dict[str, Any]],
        execution_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate quality indicators and metrics."""
        
        return {
            "response_length": len(response),
            "word_count": len(response.split()),
            "paragraph_count": len(response.split("\n\n")),
            "has_structure": "##" in response or "###" in response,
            "tool_results_count": len(tool_results),
            "successful_tools": execution_metadata.get("tools_successful", 0),
            "execution_time": execution_metadata.get("total_execution_time", 0),
            "contains_citations": any(
                keyword in response.lower()
                for keyword in ["source", "according to", "based on"]
            ),
            "has_actionable_content": any(
                keyword in response.lower()
                for keyword in ["should", "recommend", "steps", "ensure"]
            ),
            "complexity_indicators": {
                "avg_sentence_length": self._calculate_avg_sentence_length(response),
                "technical_terms": self._count_technical_terms(response),
                "structure_depth": response.count("###") + response.count("##")
            }
        }
    
    def _calculate_avg_sentence_length(self, response: str) -> float:
        """Calculate average sentence length."""
        sentences = re.split(r'[.!?]+', response)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return 0.0
        
        return sum(len(s.split()) for s in sentences) / len(sentences)
    
    def _count_technical_terms(self, response: str) -> int:
        """Count technical terms in response."""
        technical_terms = [
            "regulation", "directive", "compliance", "implementation", "enforcement",
            "legislation", "authority", "framework", "provision", "requirement",
            "standard", "guideline", "procedure", "assessment", "monitoring"
        ]
        
        return sum(
            1 for term in technical_terms
            if term in response.lower()
        )
    
    def _create_fallback_metrics(self) -> QualityMetrics:
        """Create fallback metrics when assessment fails."""
        return QualityMetrics(
            overall_score=0.5,
            dimension_scores={dim: 0.5 for dim in QualityDimension},
            confidence_level=0.3,
            improvement_suggestions=["Quality assessment failed - manual review recommended"],
            quality_indicators={"assessment_failed": True},
            assessment_metadata={
                "assessment_timestamp": datetime.now().isoformat(),
                "quality_version": "1.0",
                "status": "failed"
            }
        )


class QualityOptimizer:
    """System for optimizing response quality based on assessments."""
    
    def __init__(self, quality_assessor: ResponseQualityAssessment):
        self.assessor = quality_assessor
        self.optimization_strategies = {
            QualityDimension.COMPLETENESS: self._optimize_completeness,
            QualityDimension.ACCURACY: self._optimize_accuracy,
            QualityDimension.RELEVANCE: self._optimize_relevance,
            QualityDimension.CLARITY: self._optimize_clarity,
            QualityDimension.COHERENCE: self._optimize_coherence,
            QualityDimension.TIMELINESS: self._optimize_timeliness,
            QualityDimension.ACTIONABILITY: self._optimize_actionability,
            QualityDimension.SOURCE_QUALITY: self._optimize_source_quality
        }
    
    async def suggest_optimizations(
        self,
        quality_metrics: QualityMetrics,
        query_analysis: Dict[str, Any],
        tool_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Suggest specific optimizations based on quality assessment."""
        
        optimizations = {
            "priority_improvements": [],
            "strategy_adjustments": {},
            "tool_recommendations": [],
            "response_enhancements": []
        }
        
        # Identify priority improvements
        low_scoring_dimensions = [
            dim for dim, score in quality_metrics.dimension_scores.items()
            if score < self.assessor.quality_thresholds[dim]
        ]
        
        # Sort by importance (weight)
        low_scoring_dimensions.sort(
            key=lambda dim: self.assessor.quality_weights[dim],
            reverse=True
        )
        
        optimizations["priority_improvements"] = low_scoring_dimensions[:3]
        
        # Generate specific optimization strategies
        for dimension in optimizations["priority_improvements"]:
            if dimension in self.optimization_strategies:
                strategy = await self.optimization_strategies[dimension](
                    quality_metrics, query_analysis, tool_results
                )
                optimizations["strategy_adjustments"][dimension.value] = strategy
        
        return optimizations
    
    async def _optimize_completeness(
        self,
        quality_metrics: QualityMetrics,
        query_analysis: Dict[str, Any],
        tool_results: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Optimize response completeness."""
        return {
            "strategy": "expand_coverage",
            "description": "Include more comprehensive coverage of secondary entities and information types",
            "specific_actions": [
                "Add analysis of secondary entities",
                "Include more context and background information",
                "Address additional aspects mentioned in query"
            ]
        }
    
    async def _optimize_accuracy(
        self,
        quality_metrics: QualityMetrics,
        query_analysis: Dict[str, Any],
        tool_results: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Optimize response accuracy."""
        return {
            "strategy": "enhance_verification",
            "description": "Improve accuracy through better source verification and consistency checks",
            "specific_actions": [
                "Cross-reference multiple authoritative sources",
                "Verify consistency with tool results",
                "Include confidence indicators for claims"
            ]
        }
    
    async def _optimize_relevance(
        self,
        quality_metrics: QualityMetrics,
        query_analysis: Dict[str, Any],
        tool_results: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Optimize response relevance."""
        return {
            "strategy": "focus_intent",
            "description": "Better align response with specific query intent and priorities",
            "specific_actions": [
                "Prioritize primary entity discussion",
                "Align content with user intent",
                "Remove tangential information"
            ]
        }
    
    async def _optimize_clarity(
        self,
        quality_metrics: QualityMetrics,
        query_analysis: Dict[str, Any],
        tool_results: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Optimize response clarity."""
        return {
            "strategy": "improve_structure",
            "description": "Enhance readability through better structure and formatting",
            "specific_actions": [
                "Add clear section headings",
                "Use bullet points and lists",
                "Simplify complex sentences"
            ]
        }
    
    async def _optimize_coherence(
        self,
        quality_metrics: QualityMetrics,
        query_analysis: Dict[str, Any],
        tool_results: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Optimize response coherence."""
        return {
            "strategy": "logical_flow",
            "description": "Improve logical flow and connections between ideas",
            "specific_actions": [
                "Add transition sentences",
                "Organize content logically",
                "Include summary/conclusion"
            ]
        }
    
    async def _optimize_timeliness(
        self,
        quality_metrics: QualityMetrics,
        query_analysis: Dict[str, Any],
        tool_results: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Optimize response timeliness."""
        return {
            "strategy": "current_information",
            "description": "Include more current and timely information",
            "specific_actions": [
                "Emphasize recent developments",
                "Include current status information",
                "Reference recent dates and events"
            ]
        }
    
    async def _optimize_actionability(
        self,
        quality_metrics: QualityMetrics,
        query_analysis: Dict[str, Any],
        tool_results: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Optimize response actionability."""
        return {
            "strategy": "practical_guidance",
            "description": "Add more practical and actionable guidance",
            "specific_actions": [
                "Include specific steps or procedures",
                "Add implementation recommendations",
                "Provide practical examples"
            ]
        }
    
    async def _optimize_source_quality(
        self,
        quality_metrics: QualityMetrics,
        query_analysis: Dict[str, Any],
        tool_results: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Optimize source quality."""
        return {
            "strategy": "authoritative_sources",
            "description": "Use more authoritative and credible sources",
            "specific_actions": [
                "Prioritize official government sources",
                "Include regulatory body citations",
                "Reference primary legal documents"
            ]
        }