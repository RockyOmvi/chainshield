"""
ChainShield Cache Utilities

Redis-based caching with:
- Automatic serialization
- TTL support
- Cache decorators
- Graceful degradation to in-memory
"""

import asyncio
import hashlib
import json
import time
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

__all__ = [
    "CacheBackend",
    "InMemoryCache",
    "RedisCache",
    "HybridCache",
    "cache",
    "build_cache_key",
    "hash_key",
    "cached",
    "cached_with_stale",
]


# =============================================================================
# Cache Backend Interface
# =============================================================================

class CacheBackend:
    """Abstract cache backend interface."""
    
    async def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        raise NotImplementedError
    
    async def delete(self, key: str) -> None:
        raise NotImplementedError
    
    async def exists(self, key: str) -> bool:
        raise NotImplementedError
    
    async def clear_prefix(self, prefix: str) -> int:
        raise NotImplementedError


# =============================================================================
# In-Memory Cache (Fallback)
# =============================================================================

class InMemoryCache(CacheBackend):
    """
    In-memory LRU cache for fallback.
    Limited to prevent memory issues.
    """
    
    def __init__(self, max_size: int = 1000):
        self._cache: dict[str, tuple[Any, float]] = {}
        self._max_size = max_size
    
    async def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        
        value, expires_at = self._cache[key]
        
        if expires_at > 0 and time.time() > expires_at:
            del self._cache[key]
            return None
        
        return value
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        # Evict oldest if at capacity
        if len(self._cache) >= self._max_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        expires_at = time.time() + ttl if ttl else 0
        self._cache[key] = (value, expires_at)
    
    async def delete(self, key: str) -> None:
        self._cache.pop(key, None)
    
    async def exists(self, key: str) -> bool:
        return key in self._cache
    
    async def clear_prefix(self, prefix: str) -> int:
        keys_to_delete = [
            k for k in self._cache
            if k.startswith(prefix)
        ]
        for key in keys_to_delete:
            del self._cache[key]
        return len(keys_to_delete)
    
    def cleanup(self) -> int:
        """Remove expired entries."""
        now = time.time()
        expired = [
            k for k, (_, expires_at) in self._cache.items()
            if expires_at > 0 and now > expires_at
        ]
        for key in expired:
            del self._cache[key]
        return len(expired)


# =============================================================================
# Redis Cache
# =============================================================================

class RedisCache(CacheBackend):
    """Redis-backed cache implementation."""
    
    def __init__(self, redis_client=None, prefix: str = "cache:"):
        self.redis = redis_client
        self.prefix = prefix
    
    async def set_redis(self, redis_client) -> None:
        """Set Redis client (for lazy initialization)."""
        self.redis = redis_client
    
    def _key(self, key: str) -> str:
        """Prefix the key."""
        return f"{self.prefix}{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        if not self.redis:
            return None
        
        try:
            data = await self.redis.get(self._key(key))
            if data is None:
                return None
            return json.loads(data)
        except Exception as e:
            logger.warning("cache_get_failed", key=key, error=str(e))
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        if not self.redis:
            return
        
        try:
            data = json.dumps(value, default=str)
            if ttl:
                await self.redis.setex(self._key(key), ttl, data)
            else:
                await self.redis.set(self._key(key), data)
        except Exception as e:
            logger.warning("cache_set_failed", key=key, error=str(e))
    
    async def delete(self, key: str) -> None:
        if not self.redis:
            return
        
        try:
            await self.redis.delete(self._key(key))
        except Exception as e:
            logger.warning("cache_delete_failed", key=key, error=str(e))
    
    async def exists(self, key: str) -> bool:
        if not self.redis:
            return False
        
        try:
            return await self.redis.exists(self._key(key))
        except Exception as e:
            logger.warning("cache_exists_failed", key=key, error=str(e))
            return False
    
    async def clear_prefix(self, prefix: str) -> int:
        if not self.redis:
            return 0
        
        try:
            pattern = f"{self.prefix}{prefix}*"
            cursor = 0
            deleted = 0
            
            while True:
                cursor, keys = await self.redis.scan(
                    cursor,
                    match=pattern,
                    count=100
                )
                if keys:
                    await self.redis.delete(*keys)
                    deleted += len(keys)
                if cursor == 0:
                    break
            
            return deleted
        except Exception as e:
            logger.warning("cache_clear_failed", prefix=prefix, error=str(e))
            return 0


# =============================================================================
# Hybrid Cache (Redis with In-Memory Fallback)
# =============================================================================

class HybridCache(CacheBackend):
    """
    Cache with Redis as primary and in-memory as fallback.
    Uses in-memory for frequently accessed items.
    """
    
    def __init__(self, redis_client=None):
        self.redis_cache = RedisCache(redis_client)
        self.local_cache = InMemoryCache(max_size=500)
        self._redis_available = True
    
    async def set_redis(self, redis_client) -> None:
        """Set Redis client."""
        await self.redis_cache.set_redis(redis_client)
        self._redis_available = redis_client is not None
    
    async def get(self, key: str) -> Optional[Any]:
        # Try local cache first (hot data)
        local_value = await self.local_cache.get(key)
        if local_value is not None:
            return local_value
        
        # Try Redis
        if self._redis_available:
            try:
                redis_value = await self.redis_cache.get(key)
                if redis_value is not None:
                    # Promote to local cache
                    await self.local_cache.set(key, redis_value, ttl=60)
                    return redis_value
            except Exception:
                self._redis_available = False
        
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        # Always set in local cache
        local_ttl = min(ttl, 300) if ttl else 300  # Max 5 min local
        await self.local_cache.set(key, value, ttl=local_ttl)
        
        # Try Redis
        if self._redis_available:
            try:
                await self.redis_cache.set(key, value, ttl=ttl)
            except Exception:
                self._redis_available = False
    
    async def delete(self, key: str) -> None:
        await self.local_cache.delete(key)
        if self._redis_available:
            try:
                await self.redis_cache.delete(key)
            except Exception:
                pass
    
    async def exists(self, key: str) -> bool:
        if await self.local_cache.exists(key):
            return True
        if self._redis_available:
            try:
                return await self.redis_cache.exists(key)
            except Exception:
                self._redis_available = False
        return False
    
    async def clear_prefix(self, prefix: str) -> int:
        local_count = await self.local_cache.clear_prefix(prefix)
        redis_count = 0
        if self._redis_available:
            try:
                redis_count = await self.redis_cache.clear_prefix(prefix)
            except Exception:
                pass
        return local_count + redis_count


# =============================================================================
# Global Cache Instance
# =============================================================================

cache = HybridCache()


# =============================================================================
# Cache Key Builders
# =============================================================================

def build_cache_key(*args, prefix: str = "") -> str:
    """
    Build a cache key from arguments.
    
    Usage:
        key = build_cache_key("wallet", address, prefix="risk")
        # Result: "risk:wallet:0x123..."
    """
    parts = [str(arg) for arg in args]
    base_key = ":".join(parts)
    
    if prefix:
        return f"{prefix}:{base_key}"
    return base_key


def hash_key(data: Any) -> str:
    """Create a hash key from complex data."""
    if isinstance(data, dict):
        data = json.dumps(data, sort_keys=True)
    return hashlib.sha256(str(data).encode()).hexdigest()[:16]


# =============================================================================
# Cache Decorators
# =============================================================================

def cached(
    ttl: int = 3600,
    prefix: str = "fn",
    key_builder: Optional[Callable[..., str]] = None
):
    """
    Decorator to cache async function results.
    
    Usage:
        @cached(ttl=300, prefix="wallet")
        async def get_wallet_info(address: str):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = build_cache_key(*key_parts, prefix=prefix)
            
            # Check cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                logger.debug(
                    "cache_hit",
                    function=func.__name__,
                    key=cache_key
                )
                return cached_value
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Cache result
            await cache.set(cache_key, result, ttl=ttl)
            logger.debug(
                "cache_miss",
                function=func.__name__,
                key=cache_key
            )
            
            return result
        
        # Add cache control methods
        wrapper.cache_clear = lambda: cache.clear_prefix(f"{prefix}:{func.__name__}")
        
        return wrapper
    return decorator


def cached_with_stale(
    ttl: int = 3600,
    stale_ttl: int = 86400,
    prefix: str = "fn"
):
    """
    Cache with stale-while-revalidate pattern.
    Returns stale data while refreshing in background.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            cache_key = build_cache_key(*key_parts, prefix=prefix)
            meta_key = f"{cache_key}:meta"
            
            # Check cache
            cached_value = await cache.get(cache_key)
            cached_meta = await cache.get(meta_key)
            
            if cached_value is not None:
                # Check if fresh
                if cached_meta and time.time() < cached_meta.get("fresh_until", 0):
                    return cached_value
                
                # Stale - refresh in background
                asyncio.create_task(_refresh_cache(
                    func, args, kwargs, cache_key, meta_key, ttl, stale_ttl
                ))
                return cached_value
            
            # No cache - fetch and cache
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl=stale_ttl)
            await cache.set(meta_key, {
                "fresh_until": time.time() + ttl,
                "cached_at": time.time()
            }, ttl=stale_ttl)
            
            return result
        
        return wrapper
    
    async def _refresh_cache(func, args, kwargs, cache_key, meta_key, ttl, stale_ttl):
        """Background task to refresh cache."""
        try:
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl=stale_ttl)
            await cache.set(meta_key, {
                "fresh_until": time.time() + ttl,
                "cached_at": time.time()
            }, ttl=stale_ttl)
        except Exception as e:
            logger.warning(
                "background_cache_refresh_failed",
                function=func.__name__,
                error=str(e)
            )
    
    return decorator
