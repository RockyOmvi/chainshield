"""
Error Handling Tests

Tests for custom error classes and exception handlers.
"""

import pytest

from app.core.errors import (
    ChainShieldError,
    ValidationError,
    NotFoundError,
    UnauthorizedError,
    ForbiddenError,
    RateLimitError,
    BlockchainError,
    AIProviderError,
    DatabaseError,
    ServiceUnavailableError,
    ErrorCode,
    ErrorResponse,
)


class TestErrorClasses:
    """Test custom error classes."""
    
    def test_chainshield_error_base(self):
        """Test base ChainShieldError."""
        error = ChainShieldError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Test error"
        )
        
        assert str(error) == "Test error"
        assert error.code == ErrorCode.INTERNAL_ERROR
        assert error.status_code == 500
    
    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError("Invalid input")
        
        assert error.status_code == 400
        assert error.code == ErrorCode.VALIDATION_ERROR
    
    def test_not_found_error(self):
        """Test NotFoundError."""
        error = NotFoundError("Wallet", "0x123")
        
        assert error.status_code == 404
        assert error.code == ErrorCode.NOT_FOUND
        assert "Wallet" in str(error)
    
    def test_unauthorized_error(self):
        """Test UnauthorizedError."""
        error = UnauthorizedError("Invalid token")
        
        assert error.status_code == 401
        assert error.code == ErrorCode.UNAUTHORIZED
    
    def test_forbidden_error(self):
        """Test ForbiddenError."""
        error = ForbiddenError("Access denied")
        
        assert error.status_code == 403
        assert error.code == ErrorCode.FORBIDDEN
    
    def test_rate_limit_error(self):
        """Test RateLimitError with retry_after."""
        error = RateLimitError(limit=100, window="minute", retry_after=60)
        
        assert error.status_code == 429
        assert error.code == ErrorCode.RATE_LIMITED
        assert error.details["retry_after"] == 60
    
    def test_blockchain_error(self):
        """Test BlockchainError."""
        error = BlockchainError(message="RPC failed")
        
        assert error.status_code == 503
        assert error.code == ErrorCode.BLOCKCHAIN_CONNECTION_FAILED
    
    def test_ai_provider_error(self):
        """Test AIProviderError."""
        error = AIProviderError(message="LLM timeout")
        
        assert error.status_code == 503
        assert error.code == ErrorCode.AI_PROVIDER_ERROR
    
    def test_database_error(self):
        """Test DatabaseError."""
        error = DatabaseError(message="Connection lost")
        
        assert error.status_code == 503
        assert error.code == ErrorCode.DATABASE_ERROR
    
    def test_service_unavailable_error(self):
        """Test ServiceUnavailableError."""
        error = ServiceUnavailableError(service="redis", retry_after=30)
        
        assert error.status_code == 503
        assert error.code == ErrorCode.SERVICE_UNAVAILABLE
        assert error.details["retry_after"] == 30


class TestErrorResponse:
    """Test error response formatting."""
    
    def test_error_response_create(self):
        """Test ErrorResponse.create creates proper format."""
        response = ErrorResponse.create(
            code=ErrorCode.VALIDATION_ERROR,
            message="Invalid address format",
            field="address",
            correlation_id="test-123"
        )
        
        assert response.success is False
        assert response.error.code == "E1001"
        assert response.error.message == "Invalid address format"
        assert response.error.field == "address"
        assert response.meta["correlation_id"] == "test-123"


class TestErrorCodes:
    """Test ErrorCode enum."""
    
    def test_error_codes_exist(self):
        """Test all error codes are defined."""
        codes = [
            ErrorCode.INTERNAL_ERROR,
            ErrorCode.VALIDATION_ERROR,
            ErrorCode.NOT_FOUND,
            ErrorCode.UNAUTHORIZED,
            ErrorCode.FORBIDDEN,
            ErrorCode.RATE_LIMITED,
            ErrorCode.BLOCKCHAIN_CONNECTION_FAILED,
            ErrorCode.AI_PROVIDER_ERROR,
        ]
        
        for code in codes:
            assert code.value is not None
    
    def test_error_code_values_unique(self):
        """Test error code values are unique."""
        values = [code.value for code in ErrorCode]
        assert len(values) == len(set(values))
