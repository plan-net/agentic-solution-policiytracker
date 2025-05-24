from typing import Dict, List

from src.models.scoring import DimensionScore


class JustificationGenerator:
    """Generate human-readable justifications for scoring decisions."""
    
    @staticmethod
    def generate_overall_justification(
        dimension_scores: Dict[str, DimensionScore],
        master_score: float,
        confidence_score: float
    ) -> str:
        """Generate overall justification for the master score."""
        
        # Find the highest scoring dimension
        highest_dim = max(dimension_scores.items(), key=lambda x: x[1].score)
        highest_name = highest_dim[0].replace('_', ' ').title()
        highest_score = highest_dim[1].score
        
        # Find contributing factors
        significant_dims = [
            (name.replace('_', ' ').title(), score.score)
            for name, score in dimension_scores.items()
            if score.score >= 50
        ]
        
        # Build justification
        parts = []
        
        # Lead with strongest factor
        if highest_score >= 80:
            parts.append(f"Primarily driven by {highest_name} (score: {highest_score:.0f})")
        elif highest_score >= 60:
            parts.append(f"Moderately influenced by {highest_name} (score: {highest_score:.0f})")
        else:
            parts.append(f"Limited relevance across dimensions")
        
        # Add other significant factors
        if len(significant_dims) > 1:
            other_dims = [f"{name} ({score:.0f})" for name, score in significant_dims[1:]]
            if len(other_dims) == 1:
                parts.append(f"with additional relevance in {other_dims[0]}")
            else:
                parts.append(f"with supporting factors: {', '.join(other_dims)}")
        
        # Add confidence qualifier
        if confidence_score >= 0.8:
            parts.append("(high confidence)")
        elif confidence_score >= 0.6:
            parts.append("(medium confidence)")
        else:
            parts.append("(low confidence)")
        
        return ". ".join(parts) + "."
    
    @staticmethod
    def generate_key_factors(dimension_scores: Dict[str, DimensionScore]) -> List[str]:
        """Extract key factors from dimension justifications."""
        
        factors = []
        
        for name, score in dimension_scores.items():
            if score.score >= 50:  # Only include significant factors
                # Extract the main factor from justification
                justification = score.justification
                if ":" in justification:
                    factor_desc = justification.split(":")[0]
                    factors.append(f"{name.replace('_', ' ').title()}: {factor_desc}")
                else:
                    factors.append(f"{name.replace('_', ' ').title()}: {justification}")
        
        # Sort by score (highest first)
        factor_scores = [(factor, dimension_scores[name].score) 
                        for factor in factors 
                        for name in dimension_scores.keys() 
                        if name.replace('_', ' ').title() in factor]
        
        factor_scores.sort(key=lambda x: x[1], reverse=True)
        
        return [factor for factor, _ in factor_scores[:5]]  # Top 5 factors
    
    @staticmethod
    def generate_summary_insights(
        all_scores: List[Dict[str, DimensionScore]],
        master_scores: List[float]
    ) -> Dict[str, str]:
        """Generate insights across all documents in a batch."""
        
        if not all_scores or not master_scores:
            return {"summary": "No documents processed successfully"}
        
        insights = {}
        
        # Overall score distribution
        high_scores = len([s for s in master_scores if s >= 75])
        medium_scores = len([s for s in master_scores if 50 <= s < 75])
        low_scores = len([s for s in master_scores if s < 50])
        
        insights["score_distribution"] = (
            f"{high_scores} high-priority, {medium_scores} medium-priority, "
            f"{low_scores} low-priority documents"
        )
        
        # Most impactful dimension
        dimension_totals = {}
        for scores in all_scores:
            for dim_name, dim_score in scores.items():
                if dim_name not in dimension_totals:
                    dimension_totals[dim_name] = []
                dimension_totals[dim_name].append(dim_score.score)
        
        dimension_averages = {
            name: sum(scores) / len(scores)
            for name, scores in dimension_totals.items()
        }
        
        top_dimension = max(dimension_averages.items(), key=lambda x: x[1])
        insights["primary_factor"] = (
            f"{top_dimension[0].replace('_', ' ').title()} is the primary relevance factor "
            f"(average score: {top_dimension[1]:.1f})"
        )
        
        # Common themes in evidence
        all_evidence = []
        for scores in all_scores:
            for dim_score in scores.values():
                all_evidence.extend(dim_score.evidence_snippets)
        
        # Simple keyword frequency analysis
        common_words = {}
        for evidence in all_evidence:
            words = evidence.lower().split()
            for word in words:
                if len(word) > 4:  # Skip short words
                    common_words[word] = common_words.get(word, 0) + 1
        
        if common_words:
            top_words = sorted(common_words.items(), key=lambda x: x[1], reverse=True)[:5]
            insights["common_themes"] = (
                f"Recurring themes: {', '.join([word for word, _ in top_words])}"
            )
        
        return insights