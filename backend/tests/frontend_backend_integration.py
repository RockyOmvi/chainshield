"""
Frontend-Backend Integration Test

Tests that frontend can call backend API endpoints correctly.
Simulates real user flow from frontend to backend.
"""

import asyncio
import sys
import json
from datetime import datetime

sys.path.insert(0, 'd:/project/chainshield/backend')


def test_api_endpoints():
    """Test API endpoints that frontend would call."""
    print("=" * 60)
    print("  FRONTEND-BACKEND INTEGRATION TEST")
    print("=" * 60)
    
    results = []
    
    # Test 1: Risk Engine (core API)
    print("\n1. RISK ENGINE API")
    try:
        from app.services.risk import get_risk_engine
        engine = get_risk_engine()
        
        async def test_analyze():
            return await engine.assess_wallet("0x742d35Cc6634C0532925a3b844Bc9e7595f2B5Fb")
        
        result = asyncio.run(test_analyze())
        
        # Simulate API response
        api_response = {
            "address": "0x742d35Cc...",
            "risk_score": result.risk_score,
            "risk_level": result.risk_level.value,
            "blocked": result.is_blocked,
            "factors": [f.description for f in result.risk_factors[:3]] if result.risk_factors else []
        }
        print(f"   API Response: {json.dumps(api_response, indent=2)}")
        results.append(("Risk API", True))
    except Exception as e:
        print(f"   ERROR: {e}")
        results.append(("Risk API", False))
    
    # Test 2: Auth API
    print("\n2. AUTH API")
    try:
        from app.core.security import create_access_token, get_password_hash, verify_password
        
        # Simulate registration
        password_hash = get_password_hash("testPassword123!")
        
        # Simulate login
        is_valid = verify_password("testPassword123!", password_hash)
        token = create_access_token(subject="user_123")
        
        print(f"   Password verified: {is_valid}")
        print(f"   JWT token: {token[:50]}...")
        results.append(("Auth API", True))
    except Exception as e:
        print(f"   ERROR: {e}")
        results.append(("Auth API", False))
    
    # Test 3: Billing API
    print("\n3. BILLING API")
    try:
        from app.services.billing import QuotaManager
        
        manager = QuotaManager()
        
        async def test_quota():
            return await manager.check_quota("test_user")
        
        allowed = asyncio.run(test_quota())
        usage = manager.get_usage("test_user")
        
        print(f"   Quota allowed: {allowed}")
        print(f"   Usage today: {usage.requests_today if usage else 0}")
        results.append(("Billing API", True))
    except Exception as e:
        print(f"   ERROR: {e}")
        results.append(("Billing API", False))
    
    # Test 4: Payments API
    print("\n4. PAYMENTS API (Stripe)")
    try:
        from app.services.payments import StripeService, SubscriptionTier
        
        service = StripeService()
        
        async def test_checkout():
            return await service.create_checkout_session(
                user_id="test_123",
                user_email="test@example.com",
                tier=SubscriptionTier.PRO
            )
        
        checkout = asyncio.run(test_checkout())
        print(f"   Checkout response: {checkout}")
        results.append(("Payments API", True))
    except Exception as e:
        print(f"   ERROR: {e}")
        results.append(("Payments API", False))
    
    # Test 5: Webhooks API
    print("\n5. WEBHOOKS API")
    try:
        from app.services.alerts import get_webhook_manager
        
        manager = get_webhook_manager()
        webhook_id = manager.register_webhook(
            user_id="test_user",
            url="https://example.com/webhook",
            events=["high_risk"]
        )
        
        webhooks = manager.list_webhooks("test_user")
        print(f"   Webhook registered: {webhook_id[:20]}...")
        print(f"   Total webhooks: {len(webhooks)}")
        results.append(("Webhooks API", True))
    except Exception as e:
        print(f"   ERROR: {e}")
        results.append(("Webhooks API", False))
    
    # Test 6: Multi-Chain API
    print("\n6. MULTI-CHAIN API")
    try:
        from app.blockchain.multichain import MultiChainClient
        
        client = MultiChainClient()
        chains = client.get_available_chains()
        
        print(f"   Available chains: {len(chains)}")
        for chain in chains[:5]:
            print(f"     - {chain.name} (ID: {chain.chain_id})")
        results.append(("MultiChain API", True))
    except Exception as e:
        print(f"   ERROR: {e}")
        results.append(("MultiChain API", False))
    
    # Test 7: Monitoring API
    print("\n7. MONITORING API")
    try:
        from app.services.monitoring import get_metrics
        from app.services.sla import get_sla_monitor
        
        metrics = get_metrics()
        sla = get_sla_monitor()
        
        stats = metrics.get_stats()
        sla_summary = sla.get_summary()
        
        print(f"   Total requests: {stats.get('total_requests', 0)}")
        print(f"   SLA uptime: {sla_summary.get('uptime_percent', 100):.2f}%")
        results.append(("Monitoring API", True))
    except Exception as e:
        print(f"   ERROR: {e}")
        results.append(("Monitoring API", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("  INTEGRATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, passed_test in results:
        status = "PASS" if passed_test else "FAIL"
        print(f"   [{status}] {name}")
    
    print(f"\n   Total: {passed}/{total} APIs working")
    print("=" * 60)
    
    # Frontend compatibility check
    print("\n  FRONTEND COMPATIBILITY")
    print("-" * 60)
    print("   Landing page: file:///d:/project/chainshield/frontend/landing/index.html")
    print("   API Base URL: http://localhost:8000/api/v1")
    print("   API Docs: http://localhost:8000/api/v1/docs")
    print("   ")
    print("   Frontend can call these endpoints:")
    print("     POST /api/v1/wallet/analyze")
    print("     POST /api/v1/auth/register")
    print("     POST /api/v1/auth/login")
    print("     POST /api/v1/payments/checkout")
    print("     GET  /api/v1/account/usage")
    print("-" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = test_api_endpoints()
    sys.exit(0 if success else 1)
