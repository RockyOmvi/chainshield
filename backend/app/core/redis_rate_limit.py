"""
ChainShield Redis Rate Limiter

Production-grade distributed rate limiting using Redis.
Uses sliding window algorithm with Redis sorted sets.
"""

import time
from typing import Any, Dict, Optional, Tuple
import structlog

logger = structlog.get_logger()


class RedisRateLimiter:
    """
    Distributed rate limiter using Redis.
    
    Uses sorted sets for efficient sliding window implementation.
    Falls back to in-memory if Redis unavailable.
    """
    
    KEY_PREFIX = "chainshield:ratelimit:"
    
    def __init__(
        self,
        redis_client=None,
        window_seconds: int = 3600,
        cleanup_probability: float = 0.1
    ):
        """
        Initialize Redis rate limiter.
        
        Args:
            redis_client: Redis async client (None for in-memory fallback)
            window_seconds: Sliding window size in seconds
            cleanup_probability: Probability of cleanup on each request
        """
        self.logger = logger.bind(module="redis_rate_limiter")
        self.redis = redis_client
        self.window_seconds = window_seconds
        self.cleanup_probability = cleanup_probability
        
        # In-memory fallback
        self._memory_store: Dict[str, list] = {}
    
    async def set_redis(self, redis_client) -> None:
        """Set Redis client (for lazy initialization)."""
        self.redis = redis_client
        self.logger.info("redis_rate_limiter_connected")
    
    def _get_key(self, identifier: str) -> str:
        """Get Redis key for identifier."""
        return f"{self.KEY_PREFIX}{identifier}"
    
    async def check_and_record(
        self,
        identifier: str,
        limit: int
    ) -> Tuple[bool, int, int]:
        """
        Check if request is allowed and record it.
        
        Args:
            identifier: Unique identifier (user_id, ip, etc.)
            limit: Maximum requests per window
            
        Returns:
            Tuple of (allowed, current_count, reset_in_seconds)
        """
        if self.redis:
            return await self._redis_check_and_record(identifier, limit)
        else:
            return self._memory_check_and_record(identifier, limit)
    
    async def _redis_check_and_record(
        self,
        identifier: str,
        limit: int
    ) -> Tuple[bool, int, int]:
        """Check using Redis sorted set."""
        now = time.time()
        key = self._get_key(identifier)
        window_start = now - self.window_seconds
        
        try:
            # Use pipeline for atomic operations
            pipe = self.redis.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current entries
            pipe.zcard(key)
            
            # Get oldest entry for reset time
            pipe.zrange(key, 0, 0, withscores=True)
            
            results = await pipe.execute()
            
            current_count = results[1]
            oldest_entries = results[2]
            
            allowed = current_count < limit
            
            if allowed:
                # Add this request
                await self.redis.zadd(key, {str(now): now})
                await self.redis.expire(key, self.window_seconds + 60)
                current_count += 1
            
            # Calculate reset time
            if oldest_entries:
                oldest_time = oldest_entries[0][1]
                reset_in = int((oldest_time + self.window_seconds) - now)
            else:
                reset_in = 0
            
            return allowed, current_count, max(reset_in, 0)
            
        except Exception as e:
            self.logger.warning("redis_rate_limit_error", error=str(e))
            # Fallback to memory
            return self._memory_check_and_record(identifier, limit)
    
    def _memory_check_and_record(
        self,
        identifier: str,
        limit: int
    ) -> Tuple[bool, int, int]:
        """Check using in-memory storage (fallback)."""
        now = time.time()
        window_start = now - self.window_seconds
        
        # Get or create list
        if identifier not in self._memory_store:
            self._memory_store[identifier] = []
        
        # Filter to window
        self._memory_store[identifier] = [
            ts for ts in self._memory_store[identifier]
            if ts > window_start
        ]
        
        current_count = len(self._memory_store[identifier])
        allowed = current_count < limit
        
        if allowed:
            self._memory_store[identifier].append(now)
            current_count += 1
        
        # Calculate reset
        if self._memory_store[identifier]:
            oldest = min(self._memory_store[identifier])
            reset_in = int((oldest + self.window_seconds) - now)
        else:
            reset_in = 0
        
        return allowed, current_count, max(reset_in, 0)
    
    async def get_usage(self, identifier: str) -> Dict[str, Any]:
        """Get current usage for an identifier."""
        now = time.time()
        
        if self.redis:
            key = self._get_key(identifier)
            window_start = now - self.window_seconds
            
            try:
                count = await self.redis.zcount(key, window_start, now)
                return {
                    "identifier": identifier,
                    "current_count": count,
                    "window_seconds": self.window_seconds,
                    "backend": "redis",
                }
            except Exception:
                pass
        
        # Memory fallback
        count = len([
            ts for ts in self._memory_store.get(identifier, [])
            if ts > now - self.window_seconds
        ])
        
        return {
            "identifier": identifier,
            "current_count": count,
            "window_seconds": self.window_seconds,
            "backend": "memory",
        }
    
    async def reset(self, identifier: str) -> None:
        """Reset rate limit for an identifier."""
        if self.redis:
            try:
                await self.redis.delete(self._get_key(identifier))
            except Exception:
                pass
        
        if identifier in self._memory_store:
            del self._memory_store[identifier]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        return {
            "backend": "redis" if self.redis else "memory",
            "window_seconds": self.window_seconds,
            "memory_identifiers": len(self._memory_store),
        }


# Singleton
_redis_rate_limiter: Optional[RedisRateLimiter] = None


def get_redis_rate_limiter() -> RedisRateLimiter:
    """Get or create Redis rate limiter singleton."""
    global _redis_rate_limiter
    if _redis_rate_limiter is None:
        _redis_rate_limiter = RedisRateLimiter()
    return _redis_rate_limiter
