"""
ChainShield Rate Limiting Module

Multi-layer rate limiting with:
- Sliding window algorithm
- Per-IP, per-user, per-endpoint limits
- Redis-backed for distributed systems
- Graceful degradation when Redis is down
"""

import time
from dataclasses import dataclass
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.errors import RateLimitError
from app.core.logging import get_logger

logger = get_logger(__name__)

__all__ = [
    "RateLimitRule",
    "RateLimiter",
    "rate_limiter",
    "RateLimitRules",
    "RateLimitMiddleware",
    "rate_limit",
    "get_client_ip",
    "get_rate_limit_key",
]


# =============================================================================
# Rate Limit Configuration
# =============================================================================

@dataclass
class RateLimitRule:
    """Configuration for a rate limit rule."""
    
    requests: int  # Max requests allowed
    window: int    # Time window in seconds
    
    @property
    def window_name(self) -> str:
        """Human-readable window name."""
        if self.window == 60:
            return "minute"
        elif self.window == 3600:
            return "hour"
        elif self.window == 86400:
            return "day"
        return f"{self.window}s"


# =============================================================================
# Rate Limiter (Redis-backed)
# =============================================================================

class RateLimiter:
    """
    Redis-backed rate limiter using sliding window algorithm.
    
    Supports:
    - Multiple rules per key
    - Distributed rate limiting
    - Graceful degradation with bounded local cache
    """
    
    MAX_LOCAL_CACHE_SIZE = 10000  # Prevent unbounded memory growth
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self._local_cache: dict[str, list[float]] = {}
        self._use_local = False
    
    async def set_redis(self, redis_client) -> None:
        """Set Redis client (for lazy initialization)."""
        self.redis = redis_client
        self._use_local = False
    
    async def is_allowed(
        self,
        key: str,
        rule: RateLimitRule
    ) -> tuple[bool, dict]:
        """
        Check if a request is allowed under the rate limit.
        
        Returns:
            (allowed, info) where info contains remaining, reset_at, etc.
        """
        try:
            if self.redis and not self._use_local:
                return await self._check_redis(key, rule)
            else:
                return self._check_local(key, rule)
        except Exception as e:
            logger.warning(
                "rate_limit_check_failed",
                key=key,
                error=str(e)
            )
            # Graceful degradation: allow request but log
            return True, {"remaining": -1, "degraded": True}
    
    async def _check_redis(
        self,
        key: str,
        rule: RateLimitRule
    ) -> tuple[bool, dict]:
        """Check rate limit using Redis sorted sets."""
        now = time.time()
        window_start = now - rule.window
        
        redis_key = f"{settings.redis_rate_limit_prefix}{key}"
        
        # Use pipeline for atomicity
        pipe = self.redis.pipeline()
        
        # Remove old entries
        pipe.zremrangebyscore(redis_key, 0, window_start)
        
        # Count current entries
        pipe.zcard(redis_key)
        
        # Add new entry
        pipe.zadd(redis_key, {str(now): now})
        
        # Set expiry
        pipe.expire(redis_key, rule.window)
        
        results = await pipe.execute()
        current_count = results[1]
        
        allowed = current_count < rule.requests
        remaining = max(0, rule.requests - current_count - 1)
        reset_at = int(now + rule.window)
        
        if not allowed:
            # Remove the entry we just added
            await self.redis.zrem(redis_key, str(now))
        
        return allowed, {
            "remaining": remaining,
            "limit": rule.requests,
            "reset_at": reset_at,
            "retry_after": rule.window if not allowed else 0
        }
    
    def _check_local(
        self,
        key: str,
        rule: RateLimitRule
    ) -> tuple[bool, dict]:
        """Fallback to local in-memory rate limiting."""
        now = time.time()
        window_start = now - rule.window
        
        # Get or create request timestamps
        if key not in self._local_cache:
            self._local_cache[key] = []
        
        # Remove old entries
        self._local_cache[key] = [
            ts for ts in self._local_cache[key]
            if ts > window_start
        ]
        
        current_count = len(self._local_cache[key])
        allowed = current_count < rule.requests
        
        if allowed:
            self._local_cache[key].append(now)
            
            # Evict oldest entries if cache is too large
            if len(self._local_cache) > self.MAX_LOCAL_CACHE_SIZE:
                # Remove oldest keys (LRU eviction)
                keys_to_remove = list(self._local_cache.keys())[:100]
                for k in keys_to_remove:
                    del self._local_cache[k]
        
        remaining = max(0, rule.requests - current_count - 1)
        reset_at = int(now + rule.window)
        
        return allowed, {
            "remaining": remaining,
            "limit": rule.requests,
            "reset_at": reset_at,
            "retry_after": rule.window if not allowed else 0,
            "local": True
        }
    
    def cleanup_local_cache(self) -> None:
        """Remove expired entries from local cache."""
        now = time.time()
        # Keep entries from last hour max
        cutoff = now - 3600
        
        for key in list(self._local_cache.keys()):
            self._local_cache[key] = [
                ts for ts in self._local_cache[key]
                if ts > cutoff
            ]
            if not self._local_cache[key]:
                del self._local_cache[key]


# =============================================================================
# Global Rate Limiter Instance
# =============================================================================

rate_limiter = RateLimiter()


# =============================================================================
# Rate Limit Rules Registry
# =============================================================================

class RateLimitRules:
    """Registry of rate limit rules for different endpoints."""
    
    # Global limits
    GLOBAL_PER_MINUTE = RateLimitRule(
        requests=settings.rate_limit_requests_per_minute,
        window=60
    )
    GLOBAL_PER_HOUR = RateLimitRule(
        requests=settings.rate_limit_requests_per_hour,
        window=3600
    )
    
    # Endpoint-specific limits
    WALLET_ANALYZE = RateLimitRule(
        requests=settings.rate_limit_wallet_analyze,
        window=3600
    )
    TX_ANALYZE = RateLimitRule(
        requests=settings.rate_limit_tx_analyze,
        window=3600
    )
    AI_EXPLAIN = RateLimitRule(
        requests=settings.rate_limit_ai_explain,
        window=3600
    )
    
    @classmethod
    def get_for_endpoint(cls, path: str) -> Optional[RateLimitRule]:
        """Get rate limit rule for an endpoint."""
        endpoint_rules = {
            "/api/v1/wallet/analyze": cls.WALLET_ANALYZE,
            "/api/v1/transaction/analyze": cls.TX_ANALYZE,
            "/api/v1/explain": cls.AI_EXPLAIN,
        }
        return endpoint_rules.get(path)


# =============================================================================
# Helper Functions
# =============================================================================

def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies."""
    # Check for forwarded headers (behind proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP (original client)
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Direct connection
    if request.client:
        return request.client.host
    
    return "unknown"


def get_rate_limit_key(
    request: Request,
    key_type: str = "ip"
) -> str:
    """
    Generate rate limit key based on type.
    
    Types:
    - ip: Per IP address
    - user: Per authenticated user
    - api_key: Per API key
    - endpoint: Per endpoint + IP
    """
    if key_type == "ip":
        return f"ip:{get_client_ip(request)}"
    
    elif key_type == "user":
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"
        return f"ip:{get_client_ip(request)}"
    
    elif key_type == "api_key":
        api_key = request.headers.get(settings.api_key_header)
        if api_key:
            # Use prefix of API key for privacy
            return f"key:{api_key[:12]}"
        return f"ip:{get_client_ip(request)}"
    
    elif key_type == "endpoint":
        ip = get_client_ip(request)
        path = request.url.path
        return f"endpoint:{ip}:{path}"
    
    return f"ip:{get_client_ip(request)}"


# =============================================================================
# Rate Limit Middleware
# =============================================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting requests."""
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting if disabled
        if not settings.rate_limit_enabled:
            return await call_next(request)
        
        # Skip health endpoints
        if request.url.path in ["/health", "/ready"]:
            return await call_next(request)
        
        # Check global rate limit (per IP)
        ip_key = get_rate_limit_key(request, "ip")
        allowed, info = await rate_limiter.is_allowed(
            ip_key,
            RateLimitRules.GLOBAL_PER_MINUTE
        )
        
        if not allowed:
            logger.warning(
                "rate_limit_exceeded",
                key=ip_key,
                rule="global_per_minute"
            )
            raise RateLimitError(
                limit=RateLimitRules.GLOBAL_PER_MINUTE.requests,
                window="minute",
                retry_after=info.get("retry_after", 60)
            )
        
        # Check API key rate limit (if API key present)
        api_key = request.headers.get(settings.api_key_header)
        if api_key:
            api_key_key = get_rate_limit_key(request, "api_key")
            allowed, api_info = await rate_limiter.is_allowed(
                api_key_key,
                RateLimitRules.GLOBAL_PER_HOUR
            )
            
            if not allowed:
                logger.warning(
                    "rate_limit_exceeded",
                    key=api_key_key,
                    rule="api_key_per_hour"
                )
                raise RateLimitError(
                    limit=RateLimitRules.GLOBAL_PER_HOUR.requests,
                    window="hour",
                    retry_after=api_info.get("retry_after", 3600)
                )
            # Use API key info for headers
            info = api_info
        
        # Check endpoint-specific limit
        endpoint_rule = RateLimitRules.get_for_endpoint(request.url.path)
        if endpoint_rule:
            # Use API key for endpoint limit if available, otherwise IP
            key_type = "api_key" if api_key else "endpoint"
            endpoint_key = get_rate_limit_key(request, key_type)
            if key_type == "api_key":
                endpoint_key = f"{endpoint_key}:{request.url.path}"
            
            allowed, endpoint_info = await rate_limiter.is_allowed(
                endpoint_key,
                endpoint_rule
            )
            
            if not allowed:
                logger.warning(
                    "rate_limit_exceeded",
                    key=endpoint_key,
                    rule="endpoint_specific"
                )
                raise RateLimitError(
                    limit=endpoint_rule.requests,
                    window=endpoint_rule.window_name,
                    retry_after=endpoint_info.get("retry_after", 60)
                )
        
        # Add rate limit headers to response
        response = await call_next(request)
        
        if not info.get("degraded"):
            response.headers["X-RateLimit-Limit"] = str(info.get("limit", 0))
            response.headers["X-RateLimit-Remaining"] = str(info.get("remaining", 0))
            response.headers["X-RateLimit-Reset"] = str(info.get("reset_at", 0))
        
        return response


# =============================================================================
# Rate Limit Decorator
# =============================================================================

def rate_limit(rule: RateLimitRule, key_type: str = "ip"):
    """
    Decorator for rate limiting specific endpoints.
    
    Usage:
        @rate_limit(RateLimitRule(requests=10, window=60))
        async def my_endpoint():
            ...
    """
    def decorator(func):
        from functools import wraps
        
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            key = get_rate_limit_key(request, key_type)
            allowed, info = await rate_limiter.is_allowed(key, rule)
            
            if not allowed:
                raise RateLimitError(
                    limit=rule.requests,
                    window=rule.window_name,
                    retry_after=info.get("retry_after", 60)
                )
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator
