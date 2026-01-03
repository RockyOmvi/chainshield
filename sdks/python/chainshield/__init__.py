"""
ChainShield Python SDK

Official Python SDK for the ChainShield Risk Assessment API.

Usage:
    from chainshield import ChainShield
    
    client = ChainShield(api_key="cs_your_api_key")
    result = client.analyze("0x742d35Cc6634C0532925a3b844Bc9e7595f2B5Fb")
    
    if result.is_high_risk:
        print(f"High risk wallet: {result.risk_score}")
"""

from chainshield.client import ChainShield
from chainshield.models import (
    RiskAssessment,
    RiskLevel,
    Chain,
    WebhookConfig,
    AlertType,
)
from chainshield.exceptions import (
    ChainShieldError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
)

__version__ = "1.0.0"
__author__ = "ChainShield Team"

__all__ = [
    "ChainShield",
    "RiskAssessment",
    "RiskLevel",
    "Chain",
    "WebhookConfig",
    "AlertType",
    "ChainShieldError",
    "AuthenticationError",
    "RateLimitError",
    "ValidationError",
]
