"""
Unit Tests for Final Polish Features

Tests for:
- Rate limiter middleware
- Stripe payments
- Database models
- Email service
"""

import asyncio
import time
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

import sys
sys.path.insert(0, 'd:/project/chainshield/backend')


# =============================================================================
# Rate Limiter Tests
# =============================================================================

class TestRateLimiter:
    """Tests for rate limiter middleware."""
    
    def test_rate_limiter_import(self):
        """Test rate limiter can be imported."""
        from app.middleware.rate_limit import (
            RateLimiter,
            RateLimitMiddleware,
            RateLimitTier,
            RATE_LIMITS
        )
        assert RateLimiter is not None
        assert RateLimitMiddleware is not None
        print("  [PASS] Rate limiter imports")
    
    def test_rate_limit_tiers(self):
        """Test rate limit tiers are configured."""
        from app.middleware.rate_limit import RATE_LIMITS, RateLimitTier
        
        assert RateLimitTier.FREE in RATE_LIMITS
        assert RateLimitTier.PRO in RATE_LIMITS
        assert RateLimitTier.ENTERPRISE in RATE_LIMITS
        
        free_config = RATE_LIMITS[RateLimitTier.FREE]
        assert free_config.requests_per_minute == 10
        assert free_config.requests_per_day == 1000
        print("  [PASS] Rate limit tiers configured correctly")
    
    @pytest.mark.asyncio
    async def test_rate_limiter_memory(self):
        """Test in-memory rate limiter."""
        from app.middleware.rate_limit import RateLimiter
        
        limiter = RateLimiter()
        
        # First request should be allowed
        allowed, remaining, reset = await limiter.is_allowed("test:key", 5, 60)
        assert allowed == True
        assert remaining >= 4
        
        # Make multiple requests
        for _ in range(5):
            await limiter.is_allowed("test:key", 5, 60)
        
        # Should be rate limited now
        allowed, remaining, reset = await limiter.is_allowed("test:key", 5, 60)
        assert allowed == False
        assert remaining == 0
        print("  [PASS] In-memory rate limiter works")


# =============================================================================
# Database Model Tests
# =============================================================================

class TestDatabaseModels:
    """Tests for SQLAlchemy models."""
    
    def test_model_imports(self):
        """Test all models can be imported."""
        from app.models import (
            User,
            ApiKey,
            UsageRecord,
            Assessment,
            BlocklistEntry,
            WebhookSubscription,
            Base
        )
        assert User is not None
        assert ApiKey is not None
        assert Assessment is not None
        print("  [PASS] All models import correctly")
    
    def test_user_model(self):
        """Test User model fields."""
        from app.models import User, UserTier, UserStatus
        
        # Check table name
        assert User.__tablename__ == "users"
        
        # Check enums
        assert UserTier.FREE.value == "free"
        assert UserTier.PRO.value == "pro"
        assert UserStatus.ACTIVE.value == "active"
        print("  [PASS] User model configured correctly")
    
    def test_base_metadata(self):
        """Test Base has all tables."""
        from app.models import Base
        
        tables = Base.metadata.tables
        assert "users" in tables
        assert "api_keys" in tables
        assert "usage_records" in tables
        assert "assessments" in tables
        assert "blocklist" in tables
        assert "webhook_subscriptions" in tables
        print("  [PASS] Base metadata has 6 tables")


# =============================================================================
# Stripe Payment Tests
# =============================================================================

class TestStripePayments:
    """Tests for Stripe payment service."""
    
    def test_stripe_import(self):
        """Test Stripe service can be imported."""
        from app.services.payments import (
            StripeService,
            get_stripe_service,
            SubscriptionTier,
            PRICE_CONFIG
        )
        assert StripeService is not None
        assert get_stripe_service is not None
        print("  [PASS] Stripe service imports")
    
    def test_subscription_tiers(self):
        """Test subscription tier configuration."""
        from app.services.payments import SubscriptionTier, PRICE_CONFIG
        
        assert SubscriptionTier.FREE.value == "free"
        assert SubscriptionTier.PRO.value == "pro"
        assert SubscriptionTier.ENTERPRISE.value == "enterprise"
        
        pro_config = PRICE_CONFIG[SubscriptionTier.PRO]
        assert pro_config.amount == 9900  # $99 in cents
        print("  [PASS] Subscription tiers configured")
    
    def test_stripe_service_demo_mode(self):
        """Test Stripe service works in demo mode."""
        from app.services.payments import StripeService
        
        service = StripeService()
        
        # Not configured - should be in demo mode
        assert not service.is_configured
        print("  [PASS] Stripe service handles missing config")


# =============================================================================
# Email Service Tests
# =============================================================================

class TestEmailService:
    """Tests for email service."""
    
    def test_email_import(self):
        """Test email service can be imported."""
        from app.services.email import EmailService, get_email_service
        
        assert EmailService is not None
        assert get_email_service is not None
        print("  [PASS] Email service imports")
    
    def test_email_templates(self):
        """Test email service has required methods."""
        from app.services.email import EmailService
        
        service = EmailService()
        
        # Check methods exist
        assert hasattr(service, 'send_verification')
        assert hasattr(service, 'send_password_reset')
        assert hasattr(service, 'send_risk_alert')
        assert hasattr(service, 'send_usage_warning')
        print("  [PASS] Email templates available")


# =============================================================================
# API Router Tests
# =============================================================================

class TestAPIRouters:
    """Tests for API routers."""
    
    def test_all_routers_registered(self):
        """Test all routers are included in v1."""
        from app.api.v1 import api_v1_router
        
        routes = [r.path for r in api_v1_router.routes]
        
        # Check key endpoints exist
        assert any('/wallet' in r for r in routes)
        assert any('/auth' in r for r in routes)
        assert any('/admin' in r for r in routes)
        assert any('/payments' in r for r in routes)
        print("  [PASS] All routers registered")


# =============================================================================
# Middleware Tests
# =============================================================================

class TestMiddleware:
    """Tests for middleware."""
    
    def test_middleware_import(self):
        """Test middleware can be imported."""
        from app.middleware import (
            RateLimiter,
            RateLimitMiddleware,
            get_rate_limiter
        )
        assert RateLimiter is not None
        print("  [PASS] Middleware imports correctly")


# =============================================================================
# Run all tests
# =============================================================================

def run_all_tests():
    """Run all unit tests."""
    print("=" * 60)
    print("  UNIT TESTS FOR POLISH FEATURES")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    test_classes = [
        TestRateLimiter(),
        TestDatabaseModels(),
        TestStripePayments(),
        TestEmailService(),
        TestAPIRouters(),
        TestMiddleware(),
    ]
    
    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        print(f"\n{class_name}:")
        
        for method_name in dir(test_class):
            if method_name.startswith('test_'):
                try:
                    method = getattr(test_class, method_name)
                    
                    # Handle async tests
                    if asyncio.iscoroutinefunction(method):
                        asyncio.get_event_loop().run_until_complete(method())
                    else:
                        method()
                    
                    passed += 1
                except Exception as e:
                    print(f"  [FAIL] {method_name}: {e}")
                    failed += 1
    
    print("\n" + "=" * 60)
    print(f"  RESULT: {passed}/{passed + failed} tests passed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
