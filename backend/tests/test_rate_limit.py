"""
Rate Limiter Tests

Tests for rate limiting functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.core.rate_limit import RateLimiter, RateLimitRule


class TestRateLimiter:
    """Test rate limiter functionality."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create a rate limiter for testing."""
        return RateLimiter()
    
    @pytest.mark.asyncio
    async def test_first_request_allowed(self, rate_limiter):
        """Test first request is always allowed."""
        allowed, remaining, reset = await rate_limiter.check_rate_limit(
            key="test_user_1",
            limit=10,
            window=60
        )
        
        assert allowed is True
        assert remaining == 9
    
    @pytest.mark.asyncio
    async def test_rate_limit_exhausted(self, rate_limiter):
        """Test rate limit is enforced after exhaustion."""
        key = "test_user_2"
        limit = 3
        
        # Make requests up to limit
        for i in range(limit):
            allowed, remaining, _ = await rate_limiter.check_rate_limit(
                key=key,
                limit=limit,
                window=60
            )
            assert allowed is True
            assert remaining == limit - i - 1
        
        # Next request should be denied
        allowed, remaining, reset = await rate_limiter.check_rate_limit(
            key=key,
            limit=limit,
            window=60
        )
        
        assert allowed is False
        assert remaining == 0
        assert reset > 0
    
    @pytest.mark.asyncio
    async def test_different_keys_independent(self, rate_limiter):
        """Test different keys have independent limits."""
        # Exhaust limit for key1
        for _ in range(3):
            await rate_limiter.check_rate_limit("key1", limit=3, window=60)
        
        allowed1, _, _ = await rate_limiter.check_rate_limit("key1", limit=3, window=60)
        allowed2, _, _ = await rate_limiter.check_rate_limit("key2", limit=3, window=60)
        
        assert allowed1 is False  # key1 exhausted
        assert allowed2 is True   # key2 still has quota
    
    @pytest.mark.asyncio
    async def test_local_cache_size_limit(self, rate_limiter):
        """Test local cache doesn't grow unbounded."""
        # Make many requests with different keys
        for i in range(100):
            await rate_limiter.check_rate_limit(
                key=f"user_{i}",
                limit=10,
                window=60
            )
        
        # Check cache size is bounded (MAX_LOCAL_CACHE_SIZE = 10000)
        # We made 100 requests, so cache should have 100 entries
        assert len(rate_limiter._local_cache) <= 100


class TestRateLimitRule:
    """Test rate limit rule configuration."""
    
    def test_default_rule(self):
        """Test default rate limit rule."""
        rule = RateLimitRule(
            requests=100,
            window=60,
            key_type="ip"
        )
        
        assert rule.requests == 100
        assert rule.window == 60
        assert rule.key_type == "ip"
    
    def test_custom_rule(self):
        """Test custom rate limit rule."""
        rule = RateLimitRule(
            requests=30,
            window=3600,
            key_type="api_key"
        )
        
        assert rule.requests == 30
        assert rule.window == 3600
        assert rule.key_type == "api_key"
