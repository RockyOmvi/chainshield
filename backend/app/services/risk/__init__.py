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

from app.services.risk.engine import RiskEngine
from app.services.risk.features import (
    WalletFeatureExtractor,
    TransactionFeatureExtractor,
    FeatureVector,
)
from app.services.risk.config import RiskConfig

__all__ = [
    "RiskEngine",
    "WalletFeatureExtractor",
    "TransactionFeatureExtractor",
    "FeatureVector",
    "RiskConfig",
]
