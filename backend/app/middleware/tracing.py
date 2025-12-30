"""
ChainShield Middleware Package

Request processing middleware for:
- Request tracing (correlation IDs)
- Request timing
- Error handling
"""

import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import (
    correlation_id_var,
    get_logger,
    log_request_start,
    log_request_end,
)

logger = get_logger(__name__)


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request tracing with correlation IDs.
    
    Adds:
    - X-Correlation-ID header (uses existing or generates new)
    - X-Request-ID header (always new)
    - Request timing
    """
    
    async def dispatch(self, request: Request, call_next):
        # Get or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Generate request ID
        request_id = str(uuid.uuid4())[:8]
        
        # Set in context for logging
        correlation_id_var.set(correlation_id)
        
        # Store in request state
        request.state.correlation_id = correlation_id
        request.state.request_id = request_id
        request.state.start_time = time.perf_counter()
        
        # Log request start
        client_ip = self._get_client_ip(request)
        user_id = getattr(request.state, "user_id", None)
        
        log_request_start(
            method=request.method,
            path=request.url.path,
            client_ip=client_ip,
            user_id=user_id
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate latency
        latency_ms = (time.perf_counter() - request.state.start_time) * 1000
        
        # Log request end
        log_request_end(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            latency_ms=latency_ms
        )
        
        # Add tracing headers to response
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{latency_ms:.2f}ms"
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        if request.client:
            return request.client.host
        
        return "unknown"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding security headers.
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Remove server header
        if "server" in response.headers:
            del response.headers["server"]
        
        return response
