"""
ChainShield SDK Data Models

Type-safe models for API responses.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime


class RiskLevel(str, Enum):
    """Risk level categories."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Chain(str, Enum):
    """Supported blockchain networks."""
    ETHEREUM = "ethereum"
    POLYGON = "polygon"
    ARBITRUM = "arbitrum"
    BSC = "bsc"
    OPTIMISM = "optimism"
    BASE = "base"
    AVALANCHE = "avalanche"
    FANTOM = "fantom"
    ZKSYNC = "zksync"
    BITCOIN = "bitcoin"
    SOLANA = "solana"


class AlertType(str, Enum):
    """Webhook alert types."""
    HIGH_RISK = "high_risk"
    CRITICAL_RISK = "critical_risk"
    BLOCKED = "blocked"
    MIXER_DETECTED = "mixer_detected"
    SANCTIONS_HIT = "sanctions_hit"


@dataclass
class RiskAssessment:
    """
    Risk assessment result for a wallet or transaction.
    
    Attributes:
        address: The analyzed address
        chain: Blockchain network
        risk_score: Numeric risk score (0-100)
        risk_level: Categorical risk level
        blocked: Whether the address is blocked
        factors: List of risk factors found
        entity: Known entity info if recognized
        timestamp: When the assessment was made
    """
    address: str
    chain: Chain
    risk_score: float
    risk_level: RiskLevel
    blocked: bool
    factors: List[str]
    entity: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    
    @property
    def is_high_risk(self) -> bool:
        """Check if wallet is high or critical risk."""
        return self.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
    
    @property
    def is_sanctioned(self) -> bool:
        """Check if wallet is sanctioned/blocked."""
        return self.blocked
    
    @property
    def is_safe(self) -> bool:
        """Check if wallet is considered safe."""
        return self.risk_level == RiskLevel.LOW and not self.blocked
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskAssessment":
        """Create from API response dictionary."""
        return cls(
            address=data["address"],
            chain=Chain(data.get("chain", "ethereum")),
            risk_score=data["risk_score"],
            risk_level=RiskLevel(data["risk_level"]),
            blocked=data.get("blocked", False),
            factors=data.get("factors", []) or data.get("risk_factors", []),
            entity=data.get("entity"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else None
        )


@dataclass
class WebhookConfig:
    """Webhook configuration."""
    url: str
    events: List[AlertType]
    secret: Optional[str] = None
    enabled: bool = True


@dataclass
class UsageInfo:
    """API usage information."""
    tier: str
    requests_today: int
    requests_month: int
    limit_day: int
    limit_month: int
    
    @property
    def usage_percent(self) -> float:
        """Get monthly usage percentage."""
        if self.limit_month == 0:
            return 0
        return (self.requests_month / self.limit_month) * 100
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UsageInfo":
        return cls(
            tier=data["tier"],
            requests_today=data["requests_today"],
            requests_month=data["requests_this_month"],
            limit_day=data["limits"]["per_day"],
            limit_month=data["limits"]["per_month"]
        )
