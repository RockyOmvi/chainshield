"""
Heuristics Aggregator

Combines scores from all heuristics into a single Layer 2 score.
Uses weighted averaging with confidence adjustment.
"""

from typing import Any, Dict, List
import structlog

from app.services.risk.heuristics.account_age import AccountAgeHeuristic, HeuristicResult
from app.services.risk.heuristics.transaction_flow import TransactionFlowHeuristic
from app.services.risk.heuristics.temporal_patterns import TemporalPatternHeuristic

logger = structlog.get_logger()


class HeuristicsAggregator:
    """
    Aggregates all heuristic scores.
    
    Combines:
    1. Account Age Heuristic
    2. Transaction Flow Heuristic
    3. Temporal Pattern Heuristic
    
    Uses confidence-weighted averaging.
    """
    
    def __init__(self):
        """Initialize aggregator with all heuristics."""
        self.heuristics = [
            AccountAgeHeuristic(weight=1.0),
            TransactionFlowHeuristic(weight=1.2),  # Slightly more important
            TemporalPatternHeuristic(weight=0.8),
        ]
        self.logger = logger.bind(module="heuristics_aggregator")
    
    def evaluate_all(
        self, 
        features: Dict[str, float],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Evaluate all heuristics and aggregate.
        
        Args:
            features: Feature dictionary
            context: Optional context
            
        Returns:
            Dictionary with:
            - combined_score: Weighted average score
            - confidence: Overall confidence
            - results: Individual heuristic results
            - factors: Combined list of factors
        """
        results: List[HeuristicResult] = []
        all_factors = []
        
        for heuristic in self.heuristics:
            try:
                result = heuristic.evaluate(features, context)
                results.append(result)
                all_factors.extend(result.factors)
            except Exception as e:
                self.logger.error(
                    "heuristic_failed",
                    heuristic=heuristic.name,
                    error=str(e)
                )
        
        # Calculate weighted score
        combined_score, overall_confidence = self._aggregate_scores(results)
        
        return {
            "combined_score": combined_score,
            "confidence": overall_confidence,
            "results": [
                {
                    "name": r.name,
                    "score": r.score,
                    "confidence": r.confidence,
                    "factors": r.factors,
                }
                for r in results
            ],
            "factors": all_factors[:10],  # Limit to top 10
            "heuristics_evaluated": len(results),
        }
    
    def _aggregate_scores(
        self, 
        results: List[HeuristicResult]
    ) -> tuple:
        """
        Calculate weighted average score.
        
        Uses both heuristic weight and confidence.
        """
        if not results:
            return 0.0, 0.0
        
        total_weight = 0.0
        weighted_sum = 0.0
        confidence_sum = 0.0
        
        for result in results:
            # Find the heuristic to get its weight
            heuristic_weight = 1.0
            for h in self.heuristics:
                if h.name == result.name:
                    heuristic_weight = h.weight
                    break
            
            # Effective weight = heuristic weight * confidence
            effective_weight = heuristic_weight * result.confidence
            
            weighted_sum += result.score * effective_weight
            total_weight += effective_weight
            confidence_sum += result.confidence
        
        if total_weight > 0:
            combined_score = weighted_sum / total_weight
        else:
            combined_score = 0.0
        
        # Overall confidence is average of individual confidences
        overall_confidence = confidence_sum / len(results)
        
        return round(combined_score, 2), round(overall_confidence, 2)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregator statistics."""
        return {
            "heuristics_count": len(self.heuristics),
            "heuristics": [
                {"name": h.name, "weight": h.weight}
                for h in self.heuristics
            ]
        }
