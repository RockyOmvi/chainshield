"""
ChainShield Risk Engine Package

A 3-layer defense system for blockchain risk assessment:
- Layer 1: Deterministic Rules (fast, known patterns)
- Layer 2: Statistical Heuristics (behavioral analysis)
- Layer 3: ML Classification (novel threat detection)

This is the core intellectual property of ChainShield.
All components are designed for:
- Sub-100ms total latency
- Full explainability
- Graceful degradation
"""


def get_risk_engine():
    """Get risk engine singleton (lazy import)."""
    from app.services.risk.engine import get_risk_engine as _get
    return _get()


def get_feature_extractor():
    """Get feature extractor (lazy import)."""
    from app.services.risk.features import WalletFeatureExtractor
    return WalletFeatureExtractor()


def get_config():
    """Get risk config (lazy import)."""
    from app.services.risk.config import RiskConfig
    return RiskConfig()


__all__ = [
    "get_risk_engine",
    "get_feature_extractor",
    "get_config",
]

