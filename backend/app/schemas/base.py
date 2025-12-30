"""
ChainShield Pydantic Schemas

Request/Response schemas for API validation with:
- Ethereum address validation
- Risk score constraints
- Consistent response formats
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Generic, TypeVar

from pydantic import BaseModel, Field, field_validator, ConfigDict

__all__ = [
    # Enums
    "RiskLevel",
    "AlertSeverity",
    "AlertStatus",
    "Chain",
    # Base schemas
    "BaseResponse",
    "PaginatedResponse",
    "ErrorDetail",
    # Wallet schemas
    "WalletAnalyzeRequest",
    "WalletAnalyzeResponse",
    "WalletProfile",
    "WalletRiskScore",
    # Transaction schemas
    "TransactionAnalyzeRequest",
    "TransactionAnalyzeResponse",
    "TransactionSummary",
    # AI schemas
    "ExplainRequest",
    "ExplainResponse",
    # Auth schemas
    "LoginRequest",
    "TokenResponse",
    "APIKeyCreate",
    "APIKeyResponse",
]

T = TypeVar("T")


# =============================================================================
# Enums
# =============================================================================

class RiskLevel(str, Enum):
    """Risk level classification."""
    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert status values."""
    NEW = "new"
    REVIEWED = "reviewed"
    DISMISSED = "dismissed"
    RESOLVED = "resolved"


class Chain(str, Enum):
    """Supported blockchain networks."""
    ETHEREUM = "ethereum"
    POLYGON = "polygon"
    BSC = "bsc"
    ARBITRUM = "arbitrum"


# =============================================================================
# Validators
# =============================================================================

ETHEREUM_ADDRESS_REGEX = re.compile(r"^0x[a-fA-F0-9]{40}$")
TX_HASH_REGEX = re.compile(r"^0x[a-fA-F0-9]{64}$")


def validate_ethereum_address(address: str) -> str:
    """Validate Ethereum address format."""
    if not ETHEREUM_ADDRESS_REGEX.match(address):
        raise ValueError(
            "Invalid Ethereum address format. "
            "Must be 0x followed by 40 hex characters."
        )
    return address.lower()  # Normalize to lowercase


def validate_tx_hash(tx_hash: str) -> str:
    """Validate transaction hash format."""
    if not TX_HASH_REGEX.match(tx_hash):
        raise ValueError(
            "Invalid transaction hash format. "
            "Must be 0x followed by 64 hex characters."
        )
    return tx_hash.lower()


# =============================================================================
# Base Response Schemas
# =============================================================================

class ResponseMeta(BaseModel):
    """Metadata included in all responses."""
    correlation_id: Optional[str] = None
    cached: bool = False
    model_version: Optional[str] = None
    latency_ms: Optional[float] = None


class BaseResponse(BaseModel, Generic[T]):
    """Standard response wrapper."""
    success: bool = True
    data: T
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "data": {},
                "meta": {"correlation_id": "abc-123"}
            }
        }
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""
    success: bool = True
    data: List[T]
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    pagination: Dict[str, Any] = Field(default_factory=dict)


class ErrorDetail(BaseModel):
    """Error detail for error responses."""
    code: str
    message: str
    field: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    error: ErrorDetail
    meta: ResponseMeta = Field(default_factory=ResponseMeta)


# =============================================================================
# Wallet Schemas
# =============================================================================

class WalletAnalyzeRequest(BaseModel):
    """Request to analyze a wallet."""
    address: str = Field(..., description="Ethereum wallet address")
    chain: Chain = Field(default=Chain.ETHEREUM, description="Blockchain network")
    include_history: bool = Field(default=False, description="Include transaction history")
    include_explanation: bool = Field(default=True, description="Include AI explanation")
    
    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        return validate_ethereum_address(v)


class WalletRiskScore(BaseModel):
    """Wallet risk assessment result."""
    score: int = Field(..., ge=0, le=100, description="Risk score 0-100")
    level: RiskLevel = Field(..., description="Risk level classification")
    confidence: float = Field(..., ge=0, le=1, description="Confidence 0-1")
    tags: List[str] = Field(default_factory=list, description="Risk tags")


class WalletProfile(BaseModel):
    """Wallet profile information."""
    address: str
    chain: Chain
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    total_tx_count: int = 0
    total_value_in: float = 0.0
    total_value_out: float = 0.0
    unique_counterparties: int = 0
    is_contract: bool = False
    is_exchange: bool = False
    is_mixer: bool = False
    is_blacklisted: bool = False
    labels: Dict[str, str] = Field(default_factory=dict)


class WalletAnalyzeResponse(BaseModel):
    """Response from wallet analysis."""
    address: str
    chain: Chain
    risk: WalletRiskScore
    profile: Optional[WalletProfile] = None
    explanation: Optional[str] = None
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Transaction Schemas
# =============================================================================

class TransactionAnalyzeRequest(BaseModel):
    """Request to analyze a transaction."""
    tx_hash: str = Field(..., description="Transaction hash")
    chain: Chain = Field(default=Chain.ETHEREUM, description="Blockchain network")
    include_explanation: bool = Field(default=True, description="Include AI explanation")
    
    @field_validator("tx_hash")
    @classmethod
    def validate_hash(cls, v: str) -> str:
        return validate_tx_hash(v)


class TransactionSummary(BaseModel):
    """Transaction summary information."""
    tx_hash: str
    chain: Chain
    block_number: int
    timestamp: datetime
    from_address: str
    to_address: Optional[str]
    value: float
    value_usd: Optional[float] = None
    gas_used: int
    gas_price: float
    tx_type: str = "transfer"
    is_success: bool = True


class TransactionRiskScore(BaseModel):
    """Transaction risk assessment."""
    score: int = Field(..., ge=0, le=100)
    level: RiskLevel
    confidence: float = Field(..., ge=0, le=1)
    flags: List[str] = Field(default_factory=list)


class TransactionAnalyzeResponse(BaseModel):
    """Response from transaction analysis."""
    tx_hash: str
    chain: Chain
    risk: TransactionRiskScore
    transaction: Optional[TransactionSummary] = None
    explanation: Optional[str] = None
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# AI Explanation Schemas
# =============================================================================

class ExplainRequest(BaseModel):
    """Request for AI explanation."""
    target_type: str = Field(..., pattern="^(wallet|transaction)$")
    target_id: str = Field(..., description="Address or tx hash")
    chain: Chain = Field(default=Chain.ETHEREUM)
    context: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional context (max 10KB)"
    )
    
    @field_validator("context")
    @classmethod
    def validate_context_size(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Limit context size to prevent memory exhaustion attacks."""
        if v is not None:
            import json
            context_str = json.dumps(v, default=str)
            if len(context_str) > 10240:  # 10KB limit
                raise ValueError("Context exceeds 10KB limit")
        return v
    
    @field_validator("target_id")
    @classmethod
    def validate_target_format(cls, v: str) -> str:
        """Basic format validation - normalized to lowercase."""
        if v.startswith("0x") and len(v) == 42:
            return validate_ethereum_address(v)
        elif v.startswith("0x") and len(v) == 66:
            return validate_tx_hash(v)
        return v
    
    def model_post_init(self, __context) -> None:
        """Validate target_id matches target_type after all fields are set."""
        if self.target_type == "wallet" and len(self.target_id) != 42:
            raise ValueError("Wallet address must be 42 characters (0x + 40 hex)")
        elif self.target_type == "transaction" and len(self.target_id) != 66:
            raise ValueError("Transaction hash must be 66 characters (0x + 64 hex)")


class ExplainResponse(BaseModel):
    """AI explanation response."""
    target_type: str
    target_id: str
    explanation: str
    confidence: float = Field(..., ge=0, le=1)
    key_factors: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Authentication Schemas
# =============================================================================

class LoginRequest(BaseModel):
    """Login request."""
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=100)


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # 30 minutes


class APIKeyCreate(BaseModel):
    """Request to create an API key."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    scopes: List[str] = Field(default_factory=list)
    expires_in_days: Optional[int] = Field(None, ge=1, le=365)


class APIKeyResponse(BaseModel):
    """API key response (key only shown once on creation)."""
    key_id: str
    key_prefix: str
    name: str
    scopes: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None
    # Only included on creation
    key: Optional[str] = Field(None, description="Full key, only shown once")


# =============================================================================
# Alert Schemas
# =============================================================================

class AlertCreate(BaseModel):
    """Create a new alert (internal use)."""
    target_type: str
    target_address: str
    alert_type: str
    severity: AlertSeverity
    risk_score: int = Field(..., ge=0, le=100)
    title: str
    description: str


class AlertResponse(BaseModel):
    """Alert response."""
    alert_id: str
    target_type: str
    target_address: str
    chain: Chain
    alert_type: str
    severity: AlertSeverity
    risk_score: int
    title: str
    description: str
    ai_explanation: Optional[str] = None
    status: AlertStatus
    is_read: bool
    created_at: datetime
    updated_at: datetime
