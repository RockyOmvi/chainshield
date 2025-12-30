"""
ChainShield Core Package
"""

from app.core.config import settings, get_settings
from app.core.database import db, get_db, Base
from app.core.errors import (
    ChainShieldError,
    ValidationError,
    NotFoundError,
    RateLimitError,
    UnauthorizedError,
    ForbiddenError,
    BlockchainError,
    AIProviderError,
    DatabaseError,
    ServiceUnavailableError,
    ErrorCode,
)
from app.core.logging import get_logger, configure_logging

__all__ = [
    # Config
    "settings",
    "get_settings",
    # Database
    "db",
    "get_db",
    "Base",
    # Errors
    "ChainShieldError",
    "ValidationError",
    "NotFoundError",
    "RateLimitError",
    "UnauthorizedError",
    "ForbiddenError",
    "BlockchainError",
    "AIProviderError",
    "DatabaseError",
    "ServiceUnavailableError",
    "ErrorCode",
    # Logging
    "get_logger",
    "configure_logging",
]
