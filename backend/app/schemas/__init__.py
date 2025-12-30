"""
ChainShield Schemas Package
"""

from app.schemas.base import (
    # Enums
    RiskLevel,
    AlertSeverity,
    AlertStatus,
    Chain,
    # Base schemas
    BaseResponse,
    PaginatedResponse,
    ErrorDetail,
    ErrorResponse,
    ResponseMeta,
    # Wallet schemas
    WalletAnalyzeRequest,
    WalletAnalyzeResponse,
    WalletProfile,
    WalletRiskScore,
    # Transaction schemas
    TransactionAnalyzeRequest,
    TransactionAnalyzeResponse,
    TransactionSummary,
    TransactionRiskScore,
    # AI schemas
    ExplainRequest,
    ExplainResponse,
    # Auth schemas
    LoginRequest,
    TokenResponse,
    APIKeyCreate,
    APIKeyResponse,
    # Alert schemas
    AlertCreate,
    AlertResponse,
)

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
    "ErrorResponse",
    "ResponseMeta",
    # Wallet schemas
    "WalletAnalyzeRequest",
    "WalletAnalyzeResponse",
    "WalletProfile",
    "WalletRiskScore",
    # Transaction schemas
    "TransactionAnalyzeRequest",
    "TransactionAnalyzeResponse",
    "TransactionSummary",
    "TransactionRiskScore",
    # AI schemas
    "ExplainRequest",
    "ExplainResponse",
    # Auth schemas
    "LoginRequest",
    "TokenResponse",
    "APIKeyCreate",
    "APIKeyResponse",
    # Alert schemas
    "AlertCreate",
    "AlertResponse",
]
