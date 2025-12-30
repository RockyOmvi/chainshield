"""
ChainShield Retry Utilities

Robust retry logic with:
- Exponential backoff with jitter
- Circuit breaker pattern
- Configurable per-operation
"""

import asyncio
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, Set, Type, TypeVar, Union

from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

__all__ = [
    "RetryConfig",
    "CircuitState",
    "CircuitBreakerConfig",
    "CircuitBreaker",
    "CircuitBreakerRegistry",
    "with_retry",
    "with_fallback",
    "retry_async",
]


# =============================================================================
# Retry Configuration
# =============================================================================

@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    
    max_retries: int = 5
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_range: tuple[float, float] = (0.0, 1.0)
    
    # Exceptions that trigger retry
    retryable_exceptions: tuple[Type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
    )
    
    # Exceptions that should NOT be retried
    non_retryable_exceptions: tuple[Type[Exception], ...] = (
        ValueError,
        TypeError,
        KeyError,
    )
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt number."""
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        
        if self.jitter:
            jitter_value = random.uniform(*self.jitter_range)
            delay += jitter_value
        
        return delay


# =============================================================================
# Circuit Breaker
# =============================================================================

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_requests: int = 2
    
    # Exceptions that count as failures
    failure_exceptions: tuple[Type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
    )


class CircuitBreaker:
    """
    Circuit breaker implementation.
    
    Prevents cascading failures by failing fast when a service is down.
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_successes = 0
    
    @property
    def is_available(self) -> bool:
        """Check if the circuit allows requests."""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time is None:
                return False
            
            elapsed = time.time() - self.last_failure_time
            if elapsed >= self.config.recovery_timeout:
                self._transition_to_half_open()
                return True
            return False
        
        # Half-open: allow limited requests
        return self.half_open_successes < self.config.half_open_requests
    
    def record_success(self) -> None:
        """Record a successful request."""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_successes += 1
            if self.half_open_successes >= self.config.half_open_requests:
                self._transition_to_closed()
        else:
            self.success_count += 1
            # Reset failure count on success in closed state
            if self.state == CircuitState.CLOSED:
                self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self, exception: Exception) -> None:
        """Record a failed request."""
        if not isinstance(exception, self.config.failure_exceptions):
            return
        
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            # Any failure in half-open goes back to open
            self._transition_to_open()
        elif self.failure_count >= self.config.failure_threshold:
            self._transition_to_open()
    
    def _transition_to_open(self) -> None:
        """Transition to open state."""
        logger.warning(
            "circuit_breaker_opened",
            name=self.name,
            failure_count=self.failure_count
        )
        self.state = CircuitState.OPEN
    
    def _transition_to_half_open(self) -> None:
        """Transition to half-open state."""
        logger.info(
            "circuit_breaker_half_open",
            name=self.name
        )
        self.state = CircuitState.HALF_OPEN
        self.half_open_successes = 0
    
    def _transition_to_closed(self) -> None:
        """Transition to closed state."""
        logger.info(
            "circuit_breaker_closed",
            name=self.name
        )
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0


# =============================================================================
# Circuit Breaker Registry
# =============================================================================

class CircuitBreakerRegistry:
    """Registry for circuit breakers."""
    
    _instances: dict[str, CircuitBreaker] = {}
    
    @classmethod
    def get(
        cls,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in cls._instances:
            cls._instances[name] = CircuitBreaker(name, config)
        return cls._instances[name]
    
    @classmethod
    def reset(cls, name: Optional[str] = None) -> None:
        """Reset circuit breakers."""
        if name:
            if name in cls._instances:
                cls._instances[name] = CircuitBreaker(
                    name,
                    cls._instances[name].config
                )
        else:
            for cb_name in list(cls._instances.keys()):
                cls._instances[cb_name] = CircuitBreaker(
                    cb_name,
                    cls._instances[cb_name].config
                )


# =============================================================================
# Retry Decorators
# =============================================================================

def with_retry(
    config: Optional[RetryConfig] = None,
    circuit_breaker: Optional[str] = None
):
    """
    Decorator for async functions with retry and circuit breaker.
    
    Usage:
        @with_retry(config=RetryConfig(max_retries=3))
        async def fetch_data():
            ...
    """
    retry_config = config or RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # Check circuit breaker
            cb = None
            if circuit_breaker:
                cb = CircuitBreakerRegistry.get(circuit_breaker)
                if not cb.is_available:
                    raise ConnectionError(
                        f"Circuit breaker '{circuit_breaker}' is open"
                    )
            
            last_exception: Optional[Exception] = None
            
            for attempt in range(retry_config.max_retries + 1):
                try:
                    result = await func(*args, **kwargs)
                    
                    if cb:
                        cb.record_success()
                    
                    if attempt > 0:
                        logger.info(
                            "retry_succeeded",
                            function=func.__name__,
                            attempt=attempt + 1
                        )
                    
                    return result
                    
                except retry_config.non_retryable_exceptions as e:
                    # Don't retry these
                    raise
                    
                except retry_config.retryable_exceptions as e:
                    last_exception = e
                    
                    if cb:
                        cb.record_failure(e)
                    
                    if attempt < retry_config.max_retries:
                        delay = retry_config.calculate_delay(attempt)
                        logger.warning(
                            "retry_attempt",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_retries=retry_config.max_retries,
                            delay=delay,
                            error=str(e)
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "retry_exhausted",
                            function=func.__name__,
                            attempts=attempt + 1,
                            error=str(e)
                        )
                        raise
                        
                except Exception as e:
                    # Unknown exception - don't retry
                    if cb:
                        cb.record_failure(e)
                    raise
            
            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError("Retry logic error")
        
        return wrapper
    return decorator


def with_fallback(
    *fallback_funcs: Callable[..., T],
    catch: tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator for async functions with fallback chain.
    
    Usage:
        @with_fallback(fallback_provider_1, fallback_provider_2)
        async def get_data():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            all_funcs = [func] + list(fallback_funcs)
            last_exception: Optional[Exception] = None
            
            for i, f in enumerate(all_funcs):
                try:
                    result = await f(*args, **kwargs)
                    if i > 0:
                        logger.info(
                            "fallback_succeeded",
                            primary=func.__name__,
                            fallback=f.__name__,
                            fallback_index=i
                        )
                    return result
                except catch as e:
                    last_exception = e
                    logger.warning(
                        "fallback_triggered",
                        function=f.__name__,
                        fallback_index=i,
                        remaining=len(all_funcs) - i - 1,
                        error=str(e)
                    )
                    continue
            
            # All fallbacks failed
            logger.error(
                "all_fallbacks_failed",
                primary=func.__name__,
                total_attempts=len(all_funcs)
            )
            if last_exception:
                raise last_exception
            raise RuntimeError("All fallbacks failed")
        
        return wrapper
    return decorator


# =============================================================================
# Utility Functions
# =============================================================================

async def retry_async(
    func: Callable[..., T],
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> T:
    """
    Retry an async function with exponential backoff.
    
    Usage:
        result = await retry_async(fetch_data, url, config=RetryConfig(max_retries=3))
    """
    retry_config = config or RetryConfig()
    
    @with_retry(config=retry_config)
    async def _wrapper():
        return await func(*args, **kwargs)
    
    return await _wrapper()
