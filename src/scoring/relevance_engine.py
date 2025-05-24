from datetime import datetime
from typing import Any, Dict

import structlog

from src.models.content import ProcessedContent
from src.models.scoring import ScoringResult
from src.scoring.dimensions import (
    DirectImpactScorer,
    IndustryRelevanceScorer,
    GeographicRelevanceScorer,
    TemporalUrgencyScorer,
    StrategicAlignmentScorer
)
from src.scoring.confidence import ConfidenceCalculator
from src.scoring.justification import JustificationGenerator
from src.config import settings

logger = structlog.get_logger()


class RelevanceEngine:
    """Main scoring orchestration engine."""
    
    def __init__(self, context: Dict[str, Any]):
        self.context = context
        self.scorers = {
            "direct_impact": DirectImpactScorer(context),
            "industry_relevance": IndustryRelevanceScorer(context),
            "geographic_relevance": GeographicRelevanceScorer(context),
            "temporal_urgency": TemporalUrgencyScorer(context),
            "strategic_alignment": StrategicAlignmentScorer(context)
        }
        self.weights = settings.dimension_weights
        
    async def score_document(self, document: ProcessedContent) -> ScoringResult:
        """Score a document across all dimensions."""
        try:
            logger.debug("Scoring document", document_id=document.id)
            
            # Score across all dimensions
            dimension_scores = {}
            for dimension_name, scorer in self.scorers.items():
                dimension_score = scorer.score(document)
                dimension_scores[dimension_name] = dimension_score
            
            # Calculate master score using weighted sum
            master_score = sum(
                score.score * score.weight
                for score in dimension_scores.values()
            )
            
            # Calculate confidence
            confidence_calculator = ConfidenceCalculator()
            confidence_score = confidence_calculator.calculate_confidence(
                document, dimension_scores
            )
            
            # Generate justifications
            justification_generator = JustificationGenerator()
            overall_justification = justification_generator.generate_overall_justification(
                dimension_scores, master_score, confidence_score
            )
            key_factors = justification_generator.generate_key_factors(dimension_scores)
            
            # Create scoring result
            result = ScoringResult(
                document_id=document.id,
                master_score=round(master_score, 1),
                dimension_scores=dimension_scores,
                confidence_score=round(confidence_score, 3),
                confidence_level="high",  # Will be auto-calculated by Pydantic
                priority_level="medium",  # Will be auto-calculated by Pydantic
                topic_clusters=[],  # Will be populated by clustering stage
                scoring_timestamp=datetime.now(),
                processing_time_ms=0.0,  # Will be set by caller
                overall_justification=overall_justification,
                key_factors=key_factors
            )
            
            logger.debug("Document scored successfully", 
                        document_id=document.id, 
                        master_score=result.master_score,
                        confidence=result.confidence_score)
            
            return result
            
        except Exception as e:
            logger.error("Failed to score document", 
                        document_id=document.id, 
                        error=str(e))
            raise
    
    def get_scoring_summary(self) -> Dict[str, Any]:
        """Get summary of scoring configuration."""
        return {
            "dimensions": list(self.scorers.keys()),
            "weights": self.weights,
            "context_summary": {
                "company_terms": len(self.context.get('company_terms', [])),
                "core_industries": len(self.context.get('core_industries', [])),
                "primary_markets": len(self.context.get('primary_markets', [])),
                "strategic_themes": len(self.context.get('strategic_themes', []))
            }
        }