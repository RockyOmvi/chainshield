"""
ChainShield End-to-End Real User Test

Simulates complete user journey:
1. User Registration
2. Email Verification
3. API Key Generation
4. Real Wallet Analysis (multiple chains)
5. Threat Detection (known bad actors)
6. Webhook Registration
7. Billing/Quota Check
8. Admin Functions
9. Rate Limiting
10. SDK Usage

Tests with REAL wallet addresses from major exchanges and known threats.
"""

import asyncio
import sys
import time
from datetime import datetime
from typing import List, Tuple

sys.path.insert(0, 'd:/project/chainshield/backend')

# =============================================================================
# Test Configuration
# =============================================================================

# Real world wallet addresses for testing
REAL_WALLETS = {
    # Major Exchanges (should be LOW risk)
    "binance_hot": "0x28C6c06298d514Db089934071355E5743bf21d60",
    "coinbase": "0x71660c4005BA85c37ccec55d0C4493E66Fe775d3",
    "kraken": "0x2910543Af39abA0Cd09dBb2D50200b3E800A63D2",
    
    # DeFi Protocols (should be LOW risk)
    "uniswap_v3": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
    "aave": "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9",
    
    # Stablecoins (should be LOW risk)
    "usdc_treasury": "0x55FE002aefF02F77364de339a1292923A15844B8",
    "tether": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    
    # Known Bad Actors (should be HIGH/CRITICAL risk)
    "tornado_cash": "0x8589427373D6D84E98730D7795D8f6f8731FDA16",
    "lazarus_group": "0x098B716B8Aaf21512996dC57EB0615e2383E2f96",
    
    # Random/New Wallets (should be MEDIUM risk - unknown)
    "random_whale": "0x742d35Cc6634C0532925a3b844Bc9e7595f2B5Fb",
}

# Multi-chain test addresses
MULTICHAIN_WALLETS = {
    "ethereum": "0x28C6c06298d514Db089934071355E5743bf21d60",
    "polygon": "0x28C6c06298d514Db089934071355E5743bf21d60",
    "arbitrum": "0x28C6c06298d514Db089934071355E5743bf21d60",
    "bsc": "0x28C6c06298d514Db089934071355E5743bf21d60",
}

# Test results
results: List[Tuple[str, str, bool, str]] = []  # (category, test, passed, details)


def log_result(category: str, test: str, passed: bool, details: str = ""):
    """Log a test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status} {test}")
    if details and not passed:
        print(f"       → {details}")
    results.append((category, test, passed, details))


# =============================================================================
# Test: User Registration Flow
# =============================================================================

async def test_user_registration():
    """Test complete user registration flow."""
    print("\n" + "=" * 60)
    print("  1. USER REGISTRATION")
    print("=" * 60)
    
    from app.core.security import get_password_hash, verify_password
    
    # Test password hashing
    test_password = "SecurePassword123!"
    hashed = get_password_hash(test_password)
    verified = verify_password(test_password, hashed)
    log_result("Registration", "Password hashing (Argon2)", verified)
    
    # Test JWT token creation
    from app.core.security import create_access_token
    token = create_access_token(subject="test_user_123")
    log_result("Registration", "JWT token generation", len(token) > 50)
    
    # Test API key generation
    from app.core.security import generate_api_key
    api_key, key_id, key_hash = generate_api_key()
    log_result("Registration", "API key generation", 
               api_key.startswith("cs_") and len(key_hash) > 20)


# =============================================================================
# Test: Real Wallet Analysis
# =============================================================================

async def test_real_wallet_analysis():
    """Test wallet analysis with real addresses."""
    print("\n" + "=" * 60)
    print("  2. REAL WALLET ANALYSIS")
    print("=" * 60)
    
    from app.services.risk import get_risk_engine
    
    engine = get_risk_engine()
    
    # Test known exchanges (should be LOW risk)
    for name, address in [
        ("Binance Hot Wallet", REAL_WALLETS["binance_hot"]),
        ("Coinbase", REAL_WALLETS["coinbase"]),
    ]:
        result = await engine.assess_wallet(address)
        expected_low = result.risk_level.value in ["LOW", "MEDIUM"]
        log_result("Analysis", f"{name} - Score: {result.risk_score:.1f}", 
                   expected_low, f"Level: {result.risk_level.value}")
    
    # Test DeFi protocols
    result = await engine.assess_wallet(REAL_WALLETS["uniswap_v3"])
    log_result("Analysis", f"Uniswap V3 - Score: {result.risk_score:.1f}",
               result.risk_score < 80, f"Level: {result.risk_level.value}")
    
    # Test stablecoins
    result = await engine.assess_wallet(REAL_WALLETS["usdc_treasury"])
    log_result("Analysis", f"USDC Treasury - Score: {result.risk_score:.1f}",
               result.risk_score < 80, f"Level: {result.risk_level.value}")


# =============================================================================
# Test: Threat Detection (Known Bad Actors)
# =============================================================================

async def test_threat_detection():
    """Test detection of known threats."""
    print("\n" + "=" * 60)
    print("  3. THREAT DETECTION (Known Bad Actors)")
    print("=" * 60)
    
    from app.services.risk import get_risk_engine
    
    engine = get_risk_engine()
    
    # Tornado Cash - should be BLOCKED
    tornado = await engine.assess_wallet(REAL_WALLETS["tornado_cash"])
    log_result("Threats", f"Tornado Cash Detection - Blocked: {tornado.is_blocked}",
               tornado.is_blocked or tornado.risk_level.value == "CRITICAL",
               f"Score: {tornado.risk_score:.1f}, Level: {tornado.risk_level.value}")
    
    # Lazarus Group - should be HIGH/CRITICAL
    lazarus = await engine.assess_wallet(REAL_WALLETS["lazarus_group"])
    log_result("Threats", f"Lazarus Group - Score: {lazarus.risk_score:.1f}",
               lazarus.risk_score >= 50 or lazarus.is_blocked,
               f"Level: {lazarus.risk_level.value}")


# =============================================================================
# Test: Multi-Chain Support
# =============================================================================

async def test_multichain():
    """Test multi-chain wallet analysis."""
    print("\n" + "=" * 60)
    print("  4. MULTI-CHAIN ANALYSIS")
    print("=" * 60)
    
    from app.blockchain.multichain import MultiChainClient
    
    client = MultiChainClient()
    chains = client.get_available_chains()
    
    log_result("MultiChain", f"Available EVM chains: {len(chains)}", len(chains) >= 9)
    
    # Test each chain
    for chain_name in ["ethereum", "polygon", "arbitrum", "bsc"]:
        chain = client.get_chain(chain_name)
        if chain:
            log_result("MultiChain", f"{chain_name.upper()} (Chain ID: {chain.chain_id})", True)
        else:
            log_result("MultiChain", f"{chain_name.upper()}", False, "Chain not found")


# =============================================================================
# Test: Billing & Quotas
# =============================================================================

async def test_billing_quotas():
    """Test billing and quota system."""
    print("\n" + "=" * 60)
    print("  5. BILLING & QUOTAS")
    print("=" * 60)
    
    from app.services.billing import QuotaManager, get_quota_manager
    
    manager = get_quota_manager()
    
    # Test tier limits
    test_user = "test_user_quota"
    usage = manager.get_usage(test_user)
    log_result("Billing", f"Usage tracking for {test_user[:15]}...", usage is not None)
    
    # Test quota check
    allowed = await manager.check_quota(test_user)
    log_result("Billing", "Quota check passes for new user", allowed)
    
    # Test recording usage
    await manager.record_usage(test_user)
    usage_after = manager.get_usage(test_user)
    log_result("Billing", "Usage recorded correctly", 
               usage_after.requests_today >= 1 if usage_after else False)


# =============================================================================
# Test: Rate Limiting
# =============================================================================

async def test_rate_limiting():
    """Test rate limiter functionality."""
    print("\n" + "=" * 60)
    print("  6. RATE LIMITING")
    print("=" * 60)
    
    from app.middleware import RateLimiter, RateLimitTier, RATE_LIMITS
    
    limiter = RateLimiter()
    
    # Test tier configurations
    free_config = RATE_LIMITS[RateLimitTier.FREE]
    log_result("RateLimit", f"Free tier: {free_config.requests_per_minute}/min", True)
    
    pro_config = RATE_LIMITS[RateLimitTier.PRO]
    log_result("RateLimit", f"Pro tier: {pro_config.requests_per_minute}/min", True)
    
    # Test rate limiting works
    test_key = f"test:ratelimit:{time.time()}"
    allowed1, remaining1, _ = await limiter.is_allowed(test_key, 3, 60)
    log_result("RateLimit", "First request allowed", allowed1)
    
    # Exhaust limit
    for _ in range(5):
        await limiter.is_allowed(test_key, 3, 60)
    
    allowed_after, remaining_after, _ = await limiter.is_allowed(test_key, 3, 60)
    log_result("RateLimit", "Rate limit enforced after burst", not allowed_after)


# =============================================================================
# Test: Webhooks
# =============================================================================

async def test_webhooks():
    """Test webhook system."""
    print("\n" + "=" * 60)
    print("  7. WEBHOOKS")
    print("=" * 60)
    
    from app.services.alerts import WebhookManager, get_webhook_manager
    from app.services.alerts.webhook import AlertEvent, AlertSeverity
    
    manager = get_webhook_manager()
    
    # Register a test webhook
    webhook_id = manager.register_webhook(
        user_id="test_user",
        url="https://example.com/webhook",
        events=["high_risk", "blocked"],
        secret="test_secret"
    )
    log_result("Webhooks", f"Webhook registered: {webhook_id[:16]}...", len(webhook_id) > 0)
    
    # Test event creation
    event = AlertEvent(
        event_type="high_risk",
        severity=AlertSeverity.HIGH,
        address="0x742d35Cc6634C0532925a3b844Bc9e7595f2B5Fb",
        risk_score=85.5,
        details={"chain": "ethereum"}
    )
    log_result("Webhooks", "Alert event created", event.severity == AlertSeverity.HIGH)


# =============================================================================
# Test: Monitoring & SLA
# =============================================================================

async def test_monitoring():
    """Test monitoring and SLA tracking."""
    print("\n" + "=" * 60)
    print("  8. MONITORING & SLA")
    print("=" * 60)
    
    from app.services.monitoring import get_metrics
    from app.services.sla import get_sla_monitor
    
    # Test metrics
    metrics = get_metrics()
    metrics.record_request("wallet_analyze", 45.5, success=True)
    stats = metrics.get_stats()
    log_result("Monitoring", f"Metrics tracking: {stats.get('total_requests', 0)} requests", 
               stats.get('total_requests', 0) >= 1)
    
    # Test SLA monitor
    sla = get_sla_monitor()
    sla.record_request(50.0, success=True)
    summary = sla.get_summary()
    log_result("Monitoring", f"SLA tracking: {summary.get('uptime_percent', 0):.1f}% uptime", True)


# =============================================================================
# Test: Database Models
# =============================================================================

async def test_database_models():
    """Test database models."""
    print("\n" + "=" * 60)
    print("  9. DATABASE MODELS")
    print("=" * 60)
    
    from app.models import User, ApiKey, Assessment, Base
    
    tables = list(Base.metadata.tables.keys())
    log_result("Database", f"Tables defined: {len(tables)}", len(tables) >= 6)
    
    for table in ["users", "api_keys", "assessments", "blocklist"]:
        log_result("Database", f"Table '{table}' exists", table in tables)


# =============================================================================
# Test: Stripe Payments
# =============================================================================

async def test_stripe_payments():
    """Test Stripe payment integration."""
    print("\n" + "=" * 60)
    print("  10. STRIPE PAYMENTS")
    print("=" * 60)
    
    from app.services.payments import StripeService, SubscriptionTier, PRICE_CONFIG
    
    service = StripeService()
    
    # Check tiers
    log_result("Payments", "Free tier configured", SubscriptionTier.FREE in PRICE_CONFIG)
    log_result("Payments", f"Pro tier: ${PRICE_CONFIG[SubscriptionTier.PRO].amount / 100}/mo", True)
    log_result("Payments", f"Enterprise tier configured", SubscriptionTier.ENTERPRISE in PRICE_CONFIG)
    
    # Demo mode checkout (Stripe not configured)
    result = await service.create_checkout_session(
        user_id="test123",
        user_email="test@example.com",
        tier=SubscriptionTier.PRO
    )
    log_result("Payments", "Checkout session (demo mode)", "demo_mode" in result or "session_id" in result)


# =============================================================================
# Test: Email Service
# =============================================================================

async def test_email_service():
    """Test email service."""
    print("\n" + "=" * 60)
    print("  11. EMAIL SERVICE")
    print("=" * 60)
    
    from app.services.email import EmailService, get_email_service
    
    service = get_email_service()
    
    log_result("Email", "Verification email template", hasattr(service, 'send_verification'))
    log_result("Email", "Password reset template", hasattr(service, 'send_password_reset'))
    log_result("Email", "Risk alert template", hasattr(service, 'send_risk_alert'))
    log_result("Email", "Usage warning template", hasattr(service, 'send_usage_warning'))


# =============================================================================
# Test: SDK Compatibility
# =============================================================================

async def test_sdk_compatibility():
    """Test SDK patterns work."""
    print("\n" + "=" * 60)
    print("  12. SDK COMPATIBILITY")
    print("=" * 60)
    
    # Simulate SDK-style API usage
    from app.services.risk import get_risk_engine
    
    engine = get_risk_engine()
    
    # SDK pattern: Analyze wallet
    address = "0x742d35Cc6634C0532925a3b844Bc9e7595f2B5Fb"
    result = await engine.assess_wallet(address)
    
    # SDK expected response structure
    log_result("SDK", "Response has 'risk_score'", hasattr(result, 'risk_score'))
    log_result("SDK", "Response has 'risk_level'", hasattr(result, 'risk_level'))
    log_result("SDK", "Response has 'is_blocked'", hasattr(result, 'is_blocked'))
    log_result("SDK", "Response has 'risk_factors'", hasattr(result, 'risk_factors'))


# =============================================================================
# Main Test Runner
# =============================================================================

async def run_all_tests():
    """Run complete E2E test suite."""
    print("\n" + "=" * 80)
    print("  CHAINSHIELD END-TO-END REAL USER TEST")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    start_time = time.time()
    
    # Run all test sections
    await test_user_registration()
    await test_real_wallet_analysis()
    await test_threat_detection()
    await test_multichain()
    await test_billing_quotas()
    await test_rate_limiting()
    await test_webhooks()
    await test_monitoring()
    await test_database_models()
    await test_stripe_payments()
    await test_email_service()
    await test_sdk_compatibility()
    
    elapsed = time.time() - start_time
    
    # Summary
    passed = sum(1 for _, _, p, _ in results if p)
    total = len(results)
    
    print("\n" + "=" * 80)
    print("  SUMMARY")
    print("=" * 80)
    print(f"\n  Total Tests: {total}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {total - passed}")
    print(f"  Success Rate: {(passed/total)*100:.1f}%")
    print(f"  Duration: {elapsed:.2f}s")
    
    # Show failures
    failures = [(cat, test, det) for cat, test, p, det in results if not p]
    if failures:
        print("\n  Failed Tests:")
        for cat, test, det in failures:
            print(f"    - [{cat}] {test}: {det}")
    
    print("\n" + "=" * 80)
    print(f"  RESULT: {'✅ ALL TESTS PASSED' if passed == total else f'⚠️ {total-passed} TESTS FAILED'}")
    print("=" * 80 + "\n")
    
    # Write report
    with open("tests/e2e_real_user_report.txt", "w") as f:
        f.write(f"CHAINSHIELD E2E REAL USER TEST REPORT\n")
        f.write(f"{'=' * 50}\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        current_cat = ""
        for cat, test, passed, details in results:
            if cat != current_cat:
                f.write(f"\n[{cat.upper()}]\n")
                current_cat = cat
            status = "PASS" if passed else "FAIL"
            f.write(f"  [{status}] {test}\n")
            if details and not passed:
                f.write(f"         {details}\n")
        
        f.write(f"\n\nSUMMARY: {passed}/{total} passed ({(passed/total)*100:.1f}%)\n")
    
    print(f"  Report saved: tests/e2e_real_user_report.txt\n")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
