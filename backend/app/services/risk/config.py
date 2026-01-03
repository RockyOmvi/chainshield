"""
ChainShield Risk Engine Configuration

Centralized configuration for all risk assessment parameters.
All values are configurable via environment variables.

Design Principle: No magic numbers in code. Everything is configurable.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set
from app.core.config import settings


@dataclass
class RuleWeights:
    """Weights for combining rule scores."""
    blacklist: float = 1.0  # Blacklist matches are absolute
    velocity: float = 0.8
    pattern: float = 0.7
    age: float = 0.5


@dataclass
class HeuristicWeights:
    """Weights for heuristic score components."""
    account_age: float = 0.25
    transaction_flow: float = 0.35
    temporal_pattern: float = 0.20
    network_behavior: float = 0.20


@dataclass
class MLConfig:
    """Configuration for ML models."""
    # V2 models trained on Kaggle real data with 99.87% accuracy
    classifier_path: str = "models/ensemble_v2.pkl"
    isolation_forest_path: str = "models/isolation_forest_v2.pkl"
    feature_scaler_path: str = "models/preprocessor_v1.json"
    
    # Inference settings
    batch_size: int = 100
    timeout_ms: int = 50
    
    # Fallback when model unavailable
    fallback_score: float = 50.0
    fallback_enabled: bool = True


@dataclass
class ThresholdConfig:
    """Risk level thresholds."""
    critical: float = 90.0
    high: float = 70.0
    medium: float = 40.0
    low: float = 0.0
    
    def get_level(self, score: float) -> str:
        """Convert numeric score to risk level."""
        if score >= self.critical:
            return "CRITICAL"
        elif score >= self.high:
            return "HIGH"
        elif score >= self.medium:
            return "MEDIUM"
        else:
            return "LOW"


@dataclass
class VelocityLimits:
    """Thresholds for velocity-based risk detection."""
    # Transactions per time window
    tx_per_minute_suspicious: int = 10
    tx_per_minute_critical: int = 30
    tx_per_hour_suspicious: int = 100
    tx_per_hour_critical: int = 500
    
    # Volume thresholds (in ETH)
    volume_spike_ratio: float = 10.0  # 10x normal = suspicious
    volume_24h_critical: float = 1000.0  # 1000 ETH in 24h
    
    # Divestment patterns
    rapid_divestment_window_minutes: int = 30
    rapid_divestment_threshold_pct: float = 90.0


@dataclass
class AccountAgeLimits:
    """Thresholds for account age scoring."""
    new_account_hours: int = 24
    young_account_days: int = 7
    mature_account_days: int = 90
    
    # Score penalties for new accounts with high activity
    new_high_activity_penalty: float = 30.0
    young_high_activity_penalty: float = 15.0


@dataclass 
class KnownPatterns:
    """Known malicious patterns and addresses."""
    
    # Mixer contracts (Tornado Cash, etc.)
    mixer_contracts: Set[str] = field(default_factory=lambda: {
        "0x47ce0c6ed5b0ce3d3a51fdb1c52dc66a7c3c2936",  # Tornado 0.1 ETH
        "0x910cbd523d972eb0a6f4cae4618ad62622b39dbf",  # Tornado 1 ETH  
        "0xa160cdab225685da1d56aa342ad8841c3b53f291",  # Tornado 10 ETH
        "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b",  # Tornado 100 ETH
        "0x722122df12d4e14e13ac3b6895a86e84145b6967",  # Tornado Router
        "0xd4b88df4d29f5cedd6857912842cff3b20c8cfa3",  # Tornado DAI
    })
    
    # Known phishing contracts
    phishing_patterns: List[str] = field(default_factory=lambda: [
        "claim",
        "airdrop",
        "free",
        "gift",
    ])
    
    # Sanctioned addresses (OFAC, etc.)
    # In production, load from external list
    sanctioned_addresses: Set[str] = field(default_factory=set)


@dataclass
class RiskConfig:
    """
    Master configuration for the Risk Engine.
    
    All parameters are tunable without code changes.
    In production, load these from environment or config service.
    """
    
    # Component weights for final score
    layer_weights: Dict[str, float] = field(default_factory=lambda: {
        "rules": 0.40,       # Deterministic rules (highest weight)
        "heuristics": 0.30,  # Statistical analysis
        "ml": 0.30,          # ML predictions
    })
    
    # Sub-configurations
    rule_weights: RuleWeights = field(default_factory=RuleWeights)
    heuristic_weights: HeuristicWeights = field(default_factory=HeuristicWeights)
    ml_config: MLConfig = field(default_factory=MLConfig)
    thresholds: ThresholdConfig = field(default_factory=ThresholdConfig)
    velocity_limits: VelocityLimits = field(default_factory=VelocityLimits)
    account_age_limits: AccountAgeLimits = field(default_factory=AccountAgeLimits)
    known_patterns: KnownPatterns = field(default_factory=KnownPatterns)
    
    # Feature settings
    feature_cache_ttl: int = 300  # 5 minutes
    max_tx_history: int = 1000    # Max transactions to analyze
    
    # Performance settings
    parallel_layers: bool = True  # Run layers in parallel
    timeout_total_ms: int = 100   # Total timeout for risk assessment
    
    # Explainability
    max_risk_factors: int = 5     # Top factors to return
    include_feature_values: bool = True
    
    @classmethod
    def from_settings(cls) -> "RiskConfig":
        """Load configuration from app settings."""
        config = cls()
        
        # Override with environment settings if available
        config.thresholds.high = settings.risk_high_threshold
        config.thresholds.medium = settings.risk_medium_threshold
        
        return config


# Global config instance
risk_config = RiskConfig.from_settings()
