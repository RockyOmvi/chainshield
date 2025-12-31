"""
Temporal Pattern Heuristic

Analyzes timing patterns to detect bot-like behavior:
- Low entropy = predictable timing (bots)
- Burst activity = rapid fire transactions
- Off-hours activity = unusual timing for region
"""

from typing import Any, Dict
import structlog

from app.services.risk.heuristics.account_age import HeuristicResult

logger = structlog.get_logger()


class TemporalPatternHeuristic:
    """
    Analyzes temporal/timing patterns in transactions.
    
    Key patterns detected:
    1. Low entropy = bot-like predictable timing
    2. Burst patterns = concentrated activity periods
    3. Night/weekend anomalies = unusual human behavior
    4. Time-based velocity spikes
    """
    
    def __init__(self, weight: float = 1.0):
        """Initialize heuristic."""
        self.name = "temporal_pattern"
        self.weight = weight
        self.logger = logger.bind(module="temporal_heuristic")
    
    def evaluate(
        self, 
        features: Dict[str, float],
        context: Dict[str, Any] = None
    ) -> HeuristicResult:
        """
        Evaluate temporal patterns.
        
        Args:
            features: Extracted feature dictionary
            context: Optional additional context
            
        Returns:
            HeuristicResult with score and factors
        """
        factors = []
        score = 0.0
        details = {}
        
        # Check 1: Activity entropy (low = bot-like)
        entropy = features.get("active_hours_entropy", 0.5)
        details["entropy"] = entropy
        
        if entropy < 0.2:
            penalty = min(30, (0.5 - entropy) * 60)
            score += penalty
            factors.append(f"Very low timing entropy: {entropy:.2f} (bot-like)")
            details["entropy_penalty"] = penalty
        elif entropy < 0.35:
            penalty = min(15, (0.5 - entropy) * 30)
            score += penalty
            factors.append(f"Low timing entropy: {entropy:.2f}")
            details["entropy_penalty"] = penalty
        
        # Check 2: Burst activity
        burst_score = features.get("burst_score", 0)
        details["burst_score"] = burst_score
        
        if burst_score > 0.7:
            penalty = min(20, burst_score * 25)
            score += penalty
            factors.append(f"High burst activity: {burst_score:.0%}")
            details["burst_penalty"] = penalty
        
        # Check 3: Night activity (unusual for most users)
        night_ratio = features.get("night_tx_ratio", 0.2)
        details["night_ratio"] = night_ratio
        
        if night_ratio > 0.6:
            penalty = min(10, (night_ratio - 0.3) * 20)
            score += penalty
            factors.append(f"High night activity: {night_ratio:.0%} of transactions")
            details["night_penalty"] = penalty
        
        # Check 4: Weekend concentration (unusual for business wallets)
        weekend_ratio = features.get("weekend_tx_ratio", 0.3)
        details["weekend_ratio"] = weekend_ratio
        
        # This is less suspicious on its own, but combined with other factors...
        if weekend_ratio > 0.7 and entropy < 0.4:
            penalty = 5
            score += penalty
            factors.append(f"Weekend-focused bot pattern: {weekend_ratio:.0%}")
            details["weekend_penalty"] = penalty
        
        # Check 5: Velocity spikes
        tx_per_hour_avg = features.get("tx_per_hour_avg", 0)
        tx_per_hour_max = features.get("tx_per_hour_max", 0)
        
        if tx_per_hour_max > 0 and tx_per_hour_avg > 0:
            spike_ratio = tx_per_hour_max / tx_per_hour_avg
            if spike_ratio > 10:
                penalty = min(15, spike_ratio)
                score += penalty
                factors.append(f"Velocity spike: max {tx_per_hour_max:.1f} vs avg {tx_per_hour_avg:.1f}")
                details["spike_penalty"] = penalty
        
        # Check 6: 24h activity concentration
        tx_count_24h = features.get("tx_count_24h", 0)
        tx_count_total = features.get("tx_count_total", 1)
        
        if tx_count_total > 10:
            recent_ratio = tx_count_24h / tx_count_total
            if recent_ratio > 0.5:
                penalty = min(10, recent_ratio * 15)
                score += penalty
                factors.append(f"Recent activity spike: {recent_ratio:.0%} in last 24h")
                details["recent_spike_penalty"] = penalty
        
        # Cap score
        score = min(100, score)
        
        # Confidence
        has_pattern_data = entropy > 0 or burst_score > 0
        confidence = 0.8 if has_pattern_data else 0.4
        
        return HeuristicResult(
            name=self.name,
            score=round(score, 2),
            confidence=confidence,
            factors=factors,
            details=details
        )
