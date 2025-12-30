"""
Rate Limiter Tests

Tests for rate limiting functionality.
"""

import pytest
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
        rule = RateLimitRule(requests=10, window=60)
        allowed, info = await rate_limiter.is_allowed(
            key="test_user_1",
            rule=rule
        )
        
        assert allowed is True
        assert info["remaining"] == 9
    
    @pytest.mark.asyncio
    async def test_rate_limit_exhausted(self, rate_limiter):
        """Test rate limit is enforced after exhaustion."""
        key = "test_user_2"
        rule = RateLimitRule(requests=3, window=60)
        
        # Make requests up to limit
        for i in range(3):
            allowed, info = await rate_limiter.is_allowed(key=key, rule=rule)
            assert allowed is True
            assert info["remaining"] == 2 - i
        
        # Next request should be denied
        allowed, info = await rate_limiter.is_allowed(key=key, rule=rule)
        
        assert allowed is False
        assert info["remaining"] == 0
    
    @pytest.mark.asyncio
    async def test_different_keys_independent(self, rate_limiter):
        """Test different keys have independent limits."""
        rule = RateLimitRule(requests=3, window=60)
        
        # Exhaust limit for key1
        for _ in range(3):
            await rate_limiter.is_allowed("key1", rule=rule)
        
        allowed1, _ = await rate_limiter.is_allowed("key1", rule=rule)
        allowed2, _ = await rate_limiter.is_allowed("key2", rule=rule)
        
        assert allowed1 is False  # key1 exhausted
        assert allowed2 is True   # key2 still has quota


class TestRateLimitRule:
    """Test rate limit rule configuration."""
    
    def test_default_rule(self):
        """Test rate limit rule creation."""
        rule = RateLimitRule(requests=100, window=60)
        
        assert rule.requests == 100
        assert rule.window == 60
    
    def test_window_name(self):
        """Test window name property."""
        minute_rule = RateLimitRule(requests=60, window=60)
        hour_rule = RateLimitRule(requests=1000, window=3600)
        
        assert minute_rule.window_name == "minute"
        assert hour_rule.window_name == "hour"
