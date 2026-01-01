"""
ChainShield SHAP Result Caching

Caches SHAP explanations for performance.
Uses Redis with in-memory LRU fallback.
"""

import hashlib
import json
from collections import OrderedDict
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger()


class SHAPCache:
    """
    Cache for SHAP explanation results.
    
    SHAP is expensive to compute. This cache stores results
    to avoid recomputing for the same or similar inputs.
    """
    
    KEY_PREFIX = "chainshield:shap:"
    TTL_SECONDS = 3600  # 1 hour cache
    MAX_MEMORY_ITEMS = 1000
    
    def __init__(self, redis_client=None):
        """
        Initialize SHAP cache.
        
        Args:
            redis_client: Redis async client (None for memory-only)
        """
        self.logger = logger.bind(module="shap_cache")
        self.redis = redis_client
        
        # LRU memory cache
        self._memory_cache: OrderedDict = OrderedDict()
        
        # Stats
        self._hits = 0
        self._misses = 0
    
    async def set_redis(self, redis_client) -> None:
        """Set Redis client."""
        self.redis = redis_client
    
    def _make_key(self, features: List[float], model_version: str) -> str:
        """
        Create cache key from features.
        
        Rounds features to reduce cache fragmentation.
        """
        # Round features to 4 decimal places
        rounded = [round(f, 4) for f in features]
        
        # Create hash
        content = f"{model_version}:{json.dumps(rounded)}"
        hash_val = hashlib.md5(content.encode()).hexdigest()[:16]
        
        return f"{self.KEY_PREFIX}{model_version}:{hash_val}"
    
    async def get(
        self,
        features: List[float],
        model_version: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached SHAP result.
        
        Args:
            features: Input features
            model_version: Model version
            
        Returns:
            Cached result or None
        """
        key = self._make_key(features, model_version)
        
        # Try Redis first
        if self.redis:
            try:
                data = await self.redis.get(key)
                if data:
                    self._hits += 1
                    return json.loads(data)
            except Exception as e:
                self.logger.debug("redis_cache_error", error=str(e))
        
        # Try memory cache
        if key in self._memory_cache:
            # Move to end (LRU)
            self._memory_cache.move_to_end(key)
            self._hits += 1
            return self._memory_cache[key]
        
        self._misses += 1
        return None
    
    async def set(
        self,
        features: List[float],
        model_version: str,
        result: Dict[str, Any]
    ) -> None:
        """
        Cache a SHAP result.
        
        Args:
            features: Input features
            model_version: Model version
            result: SHAP explanation result
        """
        key = self._make_key(features, model_version)
        
        # Store in Redis
        if self.redis:
            try:
                await self.redis.setex(
                    key,
                    self.TTL_SECONDS,
                    json.dumps(result)
                )
            except Exception as e:
                self.logger.debug("redis_cache_set_error", error=str(e))
        
        # Store in memory
        self._memory_cache[key] = result
        self._memory_cache.move_to_end(key)
        
        # Evict if over limit
        while len(self._memory_cache) > self.MAX_MEMORY_ITEMS:
            self._memory_cache.popitem(last=False)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / max(total, 1)
        
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 4),
            "memory_items": len(self._memory_cache),
            "max_memory_items": self.MAX_MEMORY_ITEMS,
            "redis_enabled": self.redis is not None,
        }
    
    async def clear(self) -> None:
        """Clear all cached items."""
        self._memory_cache.clear()
        self._hits = 0
        self._misses = 0
        
        if self.redis:
            try:
                # Delete all SHAP keys
                keys = await self.redis.keys(f"{self.KEY_PREFIX}*")
                if keys:
                    await self.redis.delete(*keys)
            except Exception:
                pass


# Singleton
_shap_cache: Optional[SHAPCache] = None


def get_shap_cache() -> SHAPCache:
    """Get or create SHAP cache singleton."""
    global _shap_cache
    if _shap_cache is None:
        _shap_cache = SHAPCache()
    return _shap_cache
