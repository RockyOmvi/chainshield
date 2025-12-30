"""
ChainShield Logging Module

Structured logging with:
- JSON format for production
- Correlation ID tracking
- Performance metrics
- Error context preservation
"""

import sys
import time
from contextvars import ContextVar
from typing import Any, Dict, Optional
from functools import wraps
import structlog
from structlog.types import Processor

from app.core.config import settings


# =============================================================================
# Context Variables
# =============================================================================

# Correlation ID for request tracing
correlation_id_var: ContextVar[Optional[str]] = ContextVar(
    "correlation_id", default=None
)

# Request start time for latency tracking
request_start_time_var: ContextVar[Optional[float]] = ContextVar(
    "request_start_time", default=None
)


# =============================================================================
# Custom Processors
# =============================================================================

def add_correlation_id(
    logger: Any,
    method_name: str,
    event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Add correlation ID to log events."""
    correlation_id = correlation_id_var.get()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    return event_dict


def add_app_context(
    logger: Any,
    method_name: str,
    event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Add application context to log events."""
    event_dict["app"] = settings.app_name
    event_dict["env"] = settings.app_env
    return event_dict


def add_timestamp(
    logger: Any,
    method_name: str,
    event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Add ISO timestamp to log events."""
    from datetime import datetime, timezone
    event_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
    return event_dict


# =============================================================================
# Logger Configuration
# =============================================================================

def configure_logging() -> None:
    """Configure structured logging for the application."""
    
    # Determine processors based on environment
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        add_timestamp,
        add_app_context,
        add_correlation_id,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]
    
    if settings.log_format == "json":
        # JSON format for production
        shared_processors.append(
            structlog.processors.format_exc_info
        )
        renderer = structlog.processors.JSONRenderer()
    else:
        # Pretty console format for development
        shared_processors.append(
            structlog.dev.set_exc_info
        )
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    
    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """
    Get a configured logger instance.
    
    Args:
        name: Optional logger name for context
        
    Returns:
        Configured structlog logger
    """
    logger = structlog.get_logger()
    if name:
        logger = logger.bind(module=name)
    return logger


# =============================================================================
# Logging Decorators
# =============================================================================

def log_execution_time(
    logger: Optional[structlog.stdlib.BoundLogger] = None,
    level: str = "info"
):
    """
    Decorator to log function execution time.
    
    Usage:
        @log_execution_time()
        async def my_function():
            ...
    """
    def decorator(func):
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                elapsed = (time.perf_counter() - start) * 1000
                getattr(logger, level)(
                    "function_executed",
                    function=func.__name__,
                    latency_ms=round(elapsed, 2),
                    status="success"
                )
                return result
            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                logger.error(
                    "function_failed",
                    function=func.__name__,
                    latency_ms=round(elapsed, 2),
                    status="error",
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed = (time.perf_counter() - start) * 1000
                getattr(logger, level)(
                    "function_executed",
                    function=func.__name__,
                    latency_ms=round(elapsed, 2),
                    status="success"
                )
                return result
            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                logger.error(
                    "function_failed",
                    function=func.__name__,
                    latency_ms=round(elapsed, 2),
                    status="error",
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# =============================================================================
# Logging Context Managers
# =============================================================================

class LogContext:
    """
    Context manager for adding temporary context to logs.
    
    Usage:
        with LogContext(user_id="123", action="analyze"):
            logger.info("Processing request")
    """
    
    def __init__(self, **context):
        self.context = context
        self._token = None
    
    def __enter__(self):
        structlog.contextvars.bind_contextvars(**self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        structlog.contextvars.unbind_contextvars(*self.context.keys())


# =============================================================================
# Utility Functions
# =============================================================================

def log_request_start(
    method: str,
    path: str,
    client_ip: str,
    user_id: Optional[str] = None
) -> None:
    """Log the start of an HTTP request."""
    logger = get_logger("http")
    logger.info(
        "request_started",
        method=method,
        path=path,
        client_ip=client_ip,
        user_id=user_id
    )


def log_request_end(
    method: str,
    path: str,
    status_code: int,
    latency_ms: float
) -> None:
    """Log the end of an HTTP request."""
    logger = get_logger("http")
    log_method = logger.info if status_code < 400 else logger.warning
    log_method(
        "request_completed",
        method=method,
        path=path,
        status_code=status_code,
        latency_ms=round(latency_ms, 2)
    )


def log_external_call(
    service: str,
    operation: str,
    success: bool,
    latency_ms: float,
    error: Optional[str] = None
) -> None:
    """Log an external service call (blockchain, AI, etc.)."""
    logger = get_logger("external")
    if success:
        logger.info(
            "external_call_success",
            service=service,
            operation=operation,
            latency_ms=round(latency_ms, 2)
        )
    else:
        logger.warning(
            "external_call_failed",
            service=service,
            operation=operation,
            latency_ms=round(latency_ms, 2),
            error=error
        )


# =============================================================================
# Initialize Logging on Import
# =============================================================================

configure_logging()
