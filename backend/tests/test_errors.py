"""
Error Handling Tests

Tests for custom error classes and exception handlers.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import (
    ChainShieldError,
    ValidationError,
    NotFoundError,
    UnauthorizedError,
    ForbiddenError,
    RateLimitError,
    BlockchainError,
    AIServiceError,
    ErrorCode,
    error_response,
)


class TestErrorClasses:
    """Test custom error classes."""
    
    def test_chainshield_error_base(self):
        """Test base ChainShieldError."""
        error = ChainShieldError(
            message="Test error",
            code=ErrorCode.INTERNAL_ERROR
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
        error = NotFoundError("Wallet not found")
        
        assert error.status_code == 404
        assert error.code == ErrorCode.NOT_FOUND
    
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
        error = RateLimitError("Too many requests", retry_after=60)
        
        assert error.status_code == 429
        assert error.code == ErrorCode.RATE_LIMIT_EXCEEDED
        assert error.retry_after == 60
    
    def test_blockchain_error(self):
        """Test BlockchainError."""
        error = BlockchainError("RPC failed")
        
        assert error.status_code == 503
        assert error.code == ErrorCode.BLOCKCHAIN_ERROR
    
    def test_ai_service_error(self):
        """Test AIServiceError."""
        error = AIServiceError("LLM timeout")
        
        assert error.status_code == 503
        assert error.code == ErrorCode.AI_SERVICE_ERROR


class TestErrorResponse:
    """Test error response formatting."""
    
    def test_error_response_format(self):
        """Test error_response creates proper format."""
        response = error_response(
            code=ErrorCode.VALIDATION_ERROR,
            message="Invalid address format",
            details={"field": "address"}
        )
        
        assert response["success"] is False
        assert response["error"]["code"] == "VALIDATION_ERROR"
        assert response["error"]["message"] == "Invalid address format"
        assert response["error"]["details"]["field"] == "address"


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
            ErrorCode.RATE_LIMIT_EXCEEDED,
            ErrorCode.BLOCKCHAIN_ERROR,
            ErrorCode.AI_SERVICE_ERROR,
        ]
        
        for code in codes:
            assert code.value is not None
    
    def test_error_code_values_unique(self):
        """Test error code values are unique."""
        values = [code.value for code in ErrorCode]
        assert len(values) == len(set(values))
