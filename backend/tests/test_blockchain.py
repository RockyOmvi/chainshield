"""
Blockchain Client Tests

Tests for blockchain client functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.utils.retry import CircuitBreaker, CircuitBreakerConfig, CircuitState


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    def test_circuit_breaker_creation(self):
        """Test circuit breaker creation."""
        cb = CircuitBreaker("test")
        
        assert cb.name == "test"
        assert cb.state == CircuitState.CLOSED
    
    def test_circuit_breaker_with_config(self):
        """Test circuit breaker with custom config."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=10.0
        )
        cb = CircuitBreaker("test", config=config)
        
        assert cb.config.failure_threshold == 3
        assert cb.config.recovery_timeout == 10.0
    
    def test_circuit_breaker_initially_available(self):
        """Test circuit breaker is initially available."""
        cb = CircuitBreaker("test")
        
        assert cb.is_available is True
    
    def test_record_success(self):
        """Test recording successful request."""
        cb = CircuitBreaker("test")
        cb.record_success()
        
        assert cb.success_count == 1
    
    def test_record_failure(self):
        """Test recording failed request."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            failure_exceptions=(ConnectionError,)
        )
        cb = CircuitBreaker("test", config=config)
        
        cb.record_failure(ConnectionError("test"))
        
        assert cb.failure_count == 1
    
    def test_circuit_opens_after_threshold(self):
        """Test circuit opens after failure threshold."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            failure_exceptions=(ConnectionError,)
        )
        cb = CircuitBreaker("test", config=config)
        
        # Record failures up to threshold
        cb.record_failure(ConnectionError("fail 1"))
        cb.record_failure(ConnectionError("fail 2"))
        
        assert cb.state == CircuitState.OPEN


class TestCircuitBreakerConfig:
    """Test circuit breaker configuration."""
    
    def test_default_config(self):
        """Test default circuit breaker config."""
        config = CircuitBreakerConfig()
        
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 30.0
        assert config.half_open_requests == 2
    
    def test_custom_config(self):
        """Test custom circuit breaker config."""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            recovery_timeout=60.0,
            half_open_requests=5
        )
        
        assert config.failure_threshold == 10
        assert config.recovery_timeout == 60.0
        assert config.half_open_requests == 5
