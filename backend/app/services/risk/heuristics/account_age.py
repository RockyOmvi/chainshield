"""
Account Age Heuristic

Risk scoring based on account age and activity relative to age.
New accounts with high activity are more suspicious.
"""

from dataclasses import dataclass
from typing import Any, Dict
import structlog

logger = structlog.get_logger()


@dataclass
class HeuristicResult:
    """Result from a heuristic evaluation."""
    name: str
    score: float  # 0-100
    confidence: float  # 0-1
    factors: list
    details: Dict[str, Any]


class AccountAgeHeuristic:
    """
    Scores risk based on account age and age-relative behavior.
    
    Heuristics:
    1. Very new accounts (< 24 hours) = higher base risk
    2. New accounts with high activity = suspicious
    3. New accounts with high volume = suspicious
    4. Age-normalized velocity scoring
    """
    
    # Age thresholds in hours
    VERY_NEW_THRESHOLD = 24       # 1 day
    NEW_THRESHOLD = 168           # 1 week
    ESTABLISHED_THRESHOLD = 720   # 30 days
    MATURE_THRESHOLD = 4320       # 180 days
    
    def __init__(self, weight: float = 1.0):
        """Initialize heuristic."""
        self.name = "account_age"
        self.weight = weight
        self.logger = logger.bind(module="age_heuristic")
    
    def evaluate(
        self, 
        features: Dict[str, float],
        context: Dict[str, Any] = None
    ) -> HeuristicResult:
        """
        Evaluate account age risk.
        
        Args:
            features: Extracted feature dictionary
            context: Optional additional context
            
        Returns:
            HeuristicResult with score and factors
        """
        factors = []
        score = 0.0
        details = {}
        
        # Get age
        age_hours = features.get("age_hours", 0)
        age_days = features.get("age_days", 0)
        details["age_hours"] = age_hours
        details["age_days"] = age_days
        
        # Base age score
        if age_hours < self.VERY_NEW_THRESHOLD:
            base_score = 30  # High base risk
            factors.append(f"Very new account ({age_hours:.1f} hours)")
        elif age_hours < self.NEW_THRESHOLD:
            base_score = 20
            factors.append(f"New account ({age_days:.1f} days)")
        elif age_hours < self.ESTABLISHED_THRESHOLD:
            base_score = 10
        else:
            base_score = 0  # Mature accounts start at 0
        
        score += base_score
        details["base_age_score"] = base_score
        
        # Age-normalized activity check
        tx_count = features.get("tx_count_total", 0)
        expected_tx = age_days * 2  # Expect ~2 tx per day for normal usage
        
        if age_hours > 0 and tx_count > expected_tx * 3:
            activity_penalty = min(20, (tx_count / max(expected_tx, 1)) * 5)
            score += activity_penalty
            factors.append(f"High activity for age: {tx_count:.0f} tx in {age_days:.1f} days")
            details["activity_penalty"] = activity_penalty
        
        # Age-normalized volume check
        volume_24h = features.get("volume_24h_eth", 0)
        balance = features.get("balance_eth", 1)
        
        if age_hours < self.NEW_THRESHOLD and volume_24h > balance * 5:
            volume_penalty = min(15, volume_24h / balance * 3)
            score += volume_penalty
            factors.append(f"High volume for new account: {volume_24h:.2f} ETH in 24h")
            details["volume_penalty"] = volume_penalty
        
        # Velocity for new accounts
        tx_per_hour = features.get("tx_per_hour_avg", 0)
        if age_hours < self.ESTABLISHED_THRESHOLD and tx_per_hour > 5:
            velocity_penalty = min(15, tx_per_hour * 2)
            score += velocity_penalty
            factors.append(f"High velocity for new account: {tx_per_hour:.1f} tx/hour")
            details["velocity_penalty"] = velocity_penalty
        
        # Cap score
        score = min(100, score)
        
        # Confidence based on data quality
        confidence = 0.9 if age_hours > 0 else 0.5
        
        return HeuristicResult(
            name=self.name,
            score=round(score, 2),
            confidence=confidence,
            factors=factors,
            details=details
        )
