"""
ChainShield Rate Limiter Middleware

Redis-based rate limiting with per-user and per-endpoint limits.
"""

import asyncio
import hashlib
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, Dict, Any
import os

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger()


class RateLimitTier(str, Enum):
    """Rate limit tiers matching subscription levels."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    UNLIMITED = "unlimited"


@dataclass
class RateLimitConfig:
    """Rate limit configuration per tier."""
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_size: int = 10


# Default rate limits by tier
RATE_LIMITS = {
    RateLimitTier.FREE: RateLimitConfig(
        requests_per_minute=10,
        requests_per_hour=100,
        requests_per_day=1000,
        burst_size=5
    ),
    RateLimitTier.PRO: RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=1000,
        requests_per_day=10000,
        burst_size=20
    ),
    RateLimitTier.ENTERPRISE: RateLimitConfig(
        requests_per_minute=300,
        requests_per_hour=5000,
        requests_per_day=100000,
        burst_size=50
    ),
    RateLimitTier.UNLIMITED: RateLimitConfig(
        requests_per_minute=10000,
        requests_per_hour=100000,
        requests_per_day=1000000,
        burst_size=100
    ),
}


class RateLimiter:
    """
    Rate limiter using sliding window algorithm.
    
    Supports both Redis and in-memory backends.
    """
    
    def __init__(self):
        self._redis = None
        self._memory_store: Dict[str, list] = {}
        self._init_redis()
        self.logger = logger.bind(component="rate_limiter")
    
    def _init_redis(self):
        """Initialize Redis connection if available."""
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(redis_url)
                self.logger.info("rate_limiter_redis_connected")
            except Exception as e:
                self.logger.warning("rate_limiter_redis_failed", error=str(e))
    
    async def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int
    ) -> tuple[bool, int, int]:
        """
        Check if request is allowed under rate limit.
        
        Args:
            key: Rate limit key (user_id:endpoint)
            limit: Maximum requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            (allowed, remaining, reset_time)
        """
        if self._redis:
            return await self._check_redis(key, limit, window_seconds)
        return await self._check_memory(key, limit, window_seconds)
    
    async def _check_redis(
        self,
        key: str,
        limit: int,
        window_seconds: int
    ) -> tuple[bool, int, int]:
        """Redis-based rate limiting with sliding window."""
        now = time.time()
        window_start = now - window_seconds
        
        pipe = self._redis.pipeline()
        
        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)
        # Add current request
        pipe.zadd(key, {str(now): now})
        # Count requests in window
        pipe.zcard(key)
        # Set expiry
        pipe.expire(key, window_seconds)
        
        results = await pipe.execute()
        request_count = results[2]
        
        remaining = max(0, limit - request_count)
        reset_time = int(now + window_seconds)
        allowed = request_count <= limit
        
        return allowed, remaining, reset_time
    
    async def _check_memory(
        self,
        key: str,
        limit: int,
        window_seconds: int
    ) -> tuple[bool, int, int]:
        """In-memory rate limiting (fallback)."""
        now = time.time()
        window_start = now - window_seconds
        
        # Initialize if needed
        if key not in self._memory_store:
            self._memory_store[key] = []
        
        # Clean old entries
        self._memory_store[key] = [
            t for t in self._memory_store[key]
            if t > window_start
        ]
        
        # Add current request
        self._memory_store[key].append(now)
        
        request_count = len(self._memory_store[key])
        remaining = max(0, limit - request_count)
        reset_time = int(now + window_seconds)
        allowed = request_count <= limit
        
        return allowed, remaining, reset_time
    
    async def get_usage(self, key: str, window_seconds: int) -> int:
        """Get current usage count for a key."""
        if self._redis:
            now = time.time()
            window_start = now - window_seconds
            await self._redis.zremrangebyscore(key, 0, window_start)
            return await self._redis.zcard(key)
        
        if key in self._memory_store:
            now = time.time()
            window_start = now - window_seconds
            return len([t for t in self._memory_store[key] if t > window_start])
        
        return 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.
    
    Applies rate limits based on:
    - User tier (from JWT or API key)
    - Endpoint (some endpoints have stricter limits)
    - IP address (for unauthenticated requests)
    """
    
    # Endpoints with custom limits
    ENDPOINT_LIMITS = {
        "/api/v1/wallet/analyze": 100,      # per minute
        "/api/v1/wallet/analyze/batch": 10, # per minute
        "/api/v1/auth/login": 5,            # per minute
        "/api/v1/auth/register": 3,         # per minute
    }
    
    # Endpoints to skip
    SKIP_ENDPOINTS = [
        "/health",
        "/api/v1/docs",
        "/api/v1/redoc",
        "/api/v1/openapi.json",
    ]
    
    def __init__(self, app, limiter: Optional[RateLimiter] = None):
        super().__init__(app)
        self.limiter = limiter or RateLimiter()
        self.logger = logger.bind(middleware="rate_limit")
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Process request with rate limiting."""
        path = request.url.path
        
        # Skip certain endpoints
        if any(path.startswith(skip) for skip in self.SKIP_ENDPOINTS):
            return await call_next(request)
        
        # Get rate limit key
        key = self._get_rate_key(request)
        tier = self._get_tier(request)
        
        # Get limits
        config = RATE_LIMITS.get(tier, RATE_LIMITS[RateLimitTier.FREE])
        
        # Check custom endpoint limit
        endpoint_limit = self.ENDPOINT_LIMITS.get(path)
        if endpoint_limit:
            allowed, remaining, reset = await self.limiter.is_allowed(
                f"{key}:{path}:min",
                endpoint_limit,
                60
            )
            if not allowed:
                return self._rate_limit_response(remaining, reset)
        
        # Check per-minute limit
        allowed, remaining, reset = await self.limiter.is_allowed(
            f"{key}:min",
            config.requests_per_minute,
            60
        )
        if not allowed:
            self.logger.warning(
                "rate_limit_exceeded",
                key=key,
                tier=tier.value,
                limit="per_minute"
            )
            return self._rate_limit_response(remaining, reset)
        
        # Check per-hour limit
        allowed, remaining_hr, reset_hr = await self.limiter.is_allowed(
            f"{key}:hr",
            config.requests_per_hour,
            3600
        )
        if not allowed:
            self.logger.warning(
                "rate_limit_exceeded",
                key=key,
                tier=tier.value,
                limit="per_hour"
            )
            return self._rate_limit_response(remaining_hr, reset_hr)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(config.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset)
        
        return response
    
    def _get_rate_key(self, request: Request) -> str:
        """Get rate limit key for request."""
        # Try to get user ID from request state
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"
        
        # Try API key
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            return f"apikey:{hashlib.sha256(api_key.encode()).hexdigest()[:16]}"
        
        # Fall back to IP
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"
    
    def _get_tier(self, request: Request) -> RateLimitTier:
        """Get rate limit tier from request."""
        tier = getattr(request.state, "tier", None)
        if tier:
            try:
                return RateLimitTier(tier)
            except ValueError:
                pass
        return RateLimitTier.FREE
    
    def _rate_limit_response(self, remaining: int, reset: int) -> Response:
        """Create rate limit exceeded response."""
        from fastapi.responses import JSONResponse
        
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Rate limit exceeded",
                "remaining": remaining,
                "reset": reset
            },
            headers={
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset),
                "Retry-After": str(max(1, reset - int(time.time())))
            }
        )


# Singleton instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create rate limiter singleton."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
