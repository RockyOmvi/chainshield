"""
ChainShield Error Handling Module

Standardized error handling with:
- Custom exception classes
- Error codes registry
- Consistent error responses
- Graceful degradation support
"""

from enum import Enum
from typing import Any, Dict, Optional
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()

__all__ = [
    "ErrorCode",
    "ErrorDetail",
    "ErrorResponse",
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
    "chainshield_exception_handler",
    "http_exception_handler",
    "generic_exception_handler",
    "register_exception_handlers",
]


# =============================================================================
# Error Codes Registry
# =============================================================================

class ErrorCode(str, Enum):
    """Standardized error codes for the API."""
    
    # General errors (1xxx)
    INTERNAL_ERROR = "E1000"
    VALIDATION_ERROR = "E1001"
    NOT_FOUND = "E1002"
    RATE_LIMITED = "E1003"
    UNAUTHORIZED = "E1004"
    FORBIDDEN = "E1005"
    SERVICE_UNAVAILABLE = "E1006"
    
    # Blockchain errors (2xxx)
    BLOCKCHAIN_CONNECTION_FAILED = "E2000"
    BLOCKCHAIN_TIMEOUT = "E2001"
    INVALID_ADDRESS = "E2002"
    INVALID_TX_HASH = "E2003"
    CHAIN_NOT_SUPPORTED = "E2004"
    ALL_PROVIDERS_FAILED = "E2005"
    
    # Risk engine errors (3xxx)
    RISK_MODEL_ERROR = "E3000"
    INSUFFICIENT_DATA = "E3001"
    ANALYSIS_FAILED = "E3002"
    
    # AI errors (4xxx)
    AI_PROVIDER_ERROR = "E4000"
    AI_RATE_LIMITED = "E4001"
    AI_CONTEXT_TOO_LONG = "E4002"
    ALL_AI_PROVIDERS_FAILED = "E4003"
    
    # Database errors (5xxx)
    DATABASE_ERROR = "E5000"
    DATABASE_CONNECTION_FAILED = "E5001"
    DATABASE_TIMEOUT = "E5002"
    
    # Cache errors (6xxx)
    CACHE_ERROR = "E6000"
    CACHE_CONNECTION_FAILED = "E6001"


# =============================================================================
# Error Response Model
# =============================================================================

class ErrorDetail(BaseModel):
    """Structured error detail."""
    code: str
    message: str
    field: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response format."""
    success: bool = False
    error: ErrorDetail
    meta: Dict[str, Any] = {}
    
    @classmethod
    def create(
        cls,
        code: ErrorCode,
        message: str,
        field: Optional[str] = None,
        correlation_id: Optional[str] = None,
        **meta
    ) -> "ErrorResponse":
        """Create a standard error response."""
        response_meta = {}
        if correlation_id:
            response_meta["correlation_id"] = correlation_id
        response_meta.update(meta)
        
        return cls(
            error=ErrorDetail(
                code=code.value,
                message=message,
                field=field
            ),
            meta=response_meta
        )


# =============================================================================
# Custom Exceptions
# =============================================================================

class ChainShieldError(Exception):
    """Base exception for ChainShield."""
    
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = 500,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.field = field
        self.details = details or {}
        super().__init__(message)


class ValidationError(ChainShieldError):
    """Validation error."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            message=message,
            status_code=400,
            field=field
        )


class NotFoundError(ChainShieldError):
    """Resource not found error."""
    
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            code=ErrorCode.NOT_FOUND,
            message=f"{resource} not found: {identifier}",
            status_code=404
        )


class RateLimitError(ChainShieldError):
    """Rate limit exceeded error."""
    
    def __init__(self, limit: int, window: str, retry_after: int = 60):
        super().__init__(
            code=ErrorCode.RATE_LIMITED,
            message=f"Rate limit exceeded: {limit} requests per {window}",
            status_code=429,
            details={"retry_after": retry_after}
        )


class UnauthorizedError(ChainShieldError):
    """Authentication error."""
    
    def __init__(self, message: str = "Invalid or missing authentication"):
        super().__init__(
            code=ErrorCode.UNAUTHORIZED,
            message=message,
            status_code=401
        )


class ForbiddenError(ChainShieldError):
    """Authorization error."""
    
    def __init__(self, message: str = "Access denied"):
        super().__init__(
            code=ErrorCode.FORBIDDEN,
            message=message,
            status_code=403
        )


class BlockchainError(ChainShieldError):
    """Blockchain-related error."""
    
    def __init__(
        self,
        code: ErrorCode = ErrorCode.BLOCKCHAIN_CONNECTION_FAILED,
        message: str = "Blockchain operation failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            code=code,
            message=message,
            status_code=503,
            details=details
        )


class AIProviderError(ChainShieldError):
    """AI provider error."""
    
    def __init__(
        self,
        code: ErrorCode = ErrorCode.AI_PROVIDER_ERROR,
        message: str = "AI provider operation failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            code=code,
            message=message,
            status_code=503,
            details=details
        )


class DatabaseError(ChainShieldError):
    """Database error."""
    
    def __init__(
        self,
        message: str = "Database operation failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            code=ErrorCode.DATABASE_ERROR,
            message=message,
            status_code=503,
            details=details
        )


class ServiceUnavailableError(ChainShieldError):
    """Service unavailable error with retry-after."""
    
    def __init__(
        self,
        service: str,
        retry_after: int = 30,
        message: Optional[str] = None
    ):
        super().__init__(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message=message or f"Service temporarily unavailable: {service}",
            status_code=503,
            details={"service": service, "retry_after": retry_after}
        )


# =============================================================================
# Exception Handlers
# =============================================================================

async def chainshield_exception_handler(
    request: Request,
    exc: ChainShieldError
) -> JSONResponse:
    """Handle ChainShield exceptions."""
    correlation_id = getattr(request.state, "correlation_id", None)
    
    logger.error(
        "chainshield_error",
        error_code=exc.code.value,
        message=exc.message,
        status_code=exc.status_code,
        correlation_id=correlation_id,
        details=exc.details
    )
    
    response = ErrorResponse.create(
        code=exc.code,
        message=exc.message,
        field=exc.field,
        correlation_id=correlation_id,
        **exc.details
    )
    
    headers = {}
    if exc.code == ErrorCode.RATE_LIMITED and "retry_after" in exc.details:
        headers["Retry-After"] = str(exc.details["retry_after"])
    if exc.code == ErrorCode.SERVICE_UNAVAILABLE and "retry_after" in exc.details:
        headers["Retry-After"] = str(exc.details["retry_after"])
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump(),
        headers=headers
    )


async def http_exception_handler(
    request: Request,
    exc: HTTPException
) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    correlation_id = getattr(request.state, "correlation_id", None)
    
    # Map HTTP status codes to error codes
    status_to_code = {
        400: ErrorCode.VALIDATION_ERROR,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.NOT_FOUND,
        429: ErrorCode.RATE_LIMITED,
        500: ErrorCode.INTERNAL_ERROR,
        503: ErrorCode.SERVICE_UNAVAILABLE,
    }
    
    error_code = status_to_code.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
    
    response = ErrorResponse.create(
        code=error_code,
        message=str(exc.detail),
        correlation_id=correlation_id
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump()
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """Handle unexpected exceptions."""
    correlation_id = getattr(request.state, "correlation_id", None)
    
    logger.exception(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        correlation_id=correlation_id
    )
    
    response = ErrorResponse.create(
        code=ErrorCode.INTERNAL_ERROR,
        message="An unexpected error occurred",
        correlation_id=correlation_id
    )
    
    return JSONResponse(
        status_code=500,
        content=response.model_dump()
    )


# =============================================================================
# Register Exception Handlers
# =============================================================================

def register_exception_handlers(app):
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(ChainShieldError, chainshield_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
