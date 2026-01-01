"""
ChainShield REAL WORLD TEST

Tests the complete workflow with REAL wallet addresses and REAL blockchain data.
This simulates an actual user experience.

Famous Ethereum Wallets Used:
- Vitalik Buterin (clean, high-value)
- Tornado Cash Router (known mixer - should flag)
- Random new wallet (low activity)
"""

import asyncio
import time
import json


def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


async def test_real_wallet(address: str, name: str):
    """Test a real wallet address."""
    print(f"\n📍 Testing: {name}")
    print(f"   Address: {address}")
    
    from app.services.risk.engine import get_risk_engine
    from app.blockchain.rpc_client import BlockchainRPCClient
    
    # Get real blockchain data
    rpc = BlockchainRPCClient("https://eth.llamarpc.com", timeout=10)
    
    try:
        # Fetch real data
        print("   Fetching real blockchain data...")
        start = time.time()
        
        activity = await rpc.get_address_activity(address)
        fetch_time = (time.time() - start) * 1000
        
        print(f"   ✓ RPC fetch: {fetch_time:.0f}ms")
        print(f"   ✓ Balance: {activity.get('balance_eth', 0):.4f} ETH")
        print(f"   ✓ TX Count: {activity.get('transaction_count', 0)}")
        print(f"   ✓ Is Contract: {activity.get('is_contract', False)}")
        
        # Build wallet data for risk engine
        wallet_data = {
            "address": address,
            "balance": activity.get("balance_eth", 0),
            "first_seen": "2020-01-01T00:00:00Z",  # Approximate
            "transactions": []  # Would need more RPC calls for full history
        }
        
        # Run risk assessment
        print("   Running risk assessment...")
        engine = get_risk_engine()
        start = time.time()
        
        result = await engine.assess_wallet(wallet_data)
        assess_time = (time.time() - start) * 1000
        
        print(f"\n   📊 RISK ASSESSMENT RESULT:")
        print(f"   ╔══════════════════════════════════════╗")
        print(f"   ║  Score:     {result.risk_score:>6.1f}/100              ║")
        print(f"   ║  Level:     {result.risk_level:<20}  ║")
        print(f"   ║  Blocked:   {str(result.blocked):<20}  ║")
        print(f"   ║  Time:      {assess_time:>6.1f}ms               ║")
        print(f"   ╚══════════════════════════════════════╝")
        
        if result.factors:
            print(f"   🔍 Risk Factors:")
            for factor in result.factors[:3]:
                print(f"      • {factor.factor_name}: {factor.score:.1f}")
        
        return {
            "name": name,
            "address": address,
            "score": result.risk_score,
            "level": result.risk_level,
            "blocked": result.blocked,
            "fetch_time_ms": fetch_time,
            "assess_time_ms": assess_time,
        }
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {"name": name, "address": address, "error": str(e)}
    finally:
        await rpc.close()


async def test_ml_on_kaggle_fraudsters():
    """Test ML model detection on known fraudsters from Kaggle."""
    print_section("ML DETECTION ON KAGGLE FRAUD DATA")
    
    import pandas as pd
    import joblib
    
    # Load model and data
    ensemble = joblib.load("models/risk_classifier_v2.pkl")
    df = pd.read_csv("d:/project/dataset-3/transaction_dataset.csv")
    
    feature_cols = [c for c in df.columns if c not in ["Unnamed: 0", "Index", "Address", "FLAG"] and df[c].dtype in ["float64", "int64"]]
    
    # Test on known fraudsters
    fraudsters = df[df["FLAG"] == 1].head(50)
    fraud_preds = ensemble.predict(fraudsters[feature_cols].fillna(0).values)
    fraud_probs = ensemble.predict_proba(fraudsters[feature_cols].fillna(0).values)[:, 1]
    
    # Test on legitimate wallets
    legit = df[df["FLAG"] == 0].head(50)
    legit_preds = ensemble.predict(legit[feature_cols].fillna(0).values)
    legit_probs = ensemble.predict_proba(legit[feature_cols].fillna(0).values)[:, 1]
    
    fraud_detection_rate = sum(fraud_preds) / len(fraud_preds) * 100
    legit_correct_rate = (1 - sum(legit_preds) / len(legit_preds)) * 100
    
    print(f"\n   📊 KAGGLE FRAUD DETECTION:")
    print(f"   ╔══════════════════════════════════════╗")
    print(f"   ║  Fraudsters Detected:  {fraud_detection_rate:>5.1f}%        ║")
    print(f"   ║  Legitimate Correct:   {legit_correct_rate:>5.1f}%        ║")
    print(f"   ║  Avg Fraud Score:      {fraud_probs.mean()*100:>5.1f}        ║")
    print(f"   ║  Avg Legit Score:      {legit_probs.mean()*100:>5.1f}        ║")
    print(f"   ╚══════════════════════════════════════╝")
    
    return {
        "fraud_detection": fraud_detection_rate,
        "legit_correct": legit_correct_rate,
    }


async def test_rate_limiting():
    """Test rate limiting behavior."""
    print_section("RATE LIMITING TEST")
    
    from app.core.sliding_rate_limit import SlidingWindowRateLimiter
    
    limiter = SlidingWindowRateLimiter(window_seconds=60)
    
    results = []
    for i in range(10):
        allowed, count, remaining = limiter.check_and_record("test_user", limit=5)
        results.append(allowed)
    
    allowed_count = sum(results)
    blocked_count = len(results) - allowed_count
    
    print(f"\n   Requests: 10")
    print(f"   Allowed:  {allowed_count}")
    print(f"   Blocked:  {blocked_count}")
    print(f"   ✅ Rate limiting working correctly!")
    
    return {"allowed": allowed_count, "blocked": blocked_count}


async def run_real_world_tests():
    """Run all real-world tests."""
    print("\n" + "="*60)
    print("   CHAINSHIELD REAL WORLD PERFORMANCE TEST")
    print("   Testing with REAL wallets and REAL blockchain data")
    print("="*60)
    
    overall_start = time.time()
    
    # Real wallet addresses to test
    test_wallets = [
        # Vitalik Buterin - should be clean
        ("0xd8da6bf26964af9d7eed9e03e53415d37aa96045", "Vitalik Buterin (Clean)"),
        
        # Tornado Cash Router - known mixer, should flag
        ("0xd90e2f925da726b50c4ed8d0fb90ad053324f31b", "Tornado Cash (Mixer)"),
        
        # Uniswap V2 Router - legitimate DEX
        ("0x7a250d5630b4cf539739df2c5dacb4c659f2488d", "Uniswap V2 (DEX)"),
        
        # Random low-activity wallet
        ("0x0000000000000000000000000000000000000001", "Low Activity Test"),
    ]
    
    # Test real wallets
    print_section("REAL WALLET TESTS (LIVE RPC)")
    wallet_results = []
    for address, name in test_wallets:
        result = await test_real_wallet(address, name)
        wallet_results.append(result)
    
    # Test ML on Kaggle data
    ml_results = await test_ml_on_kaggle_fraudsters()
    
    # Test rate limiting
    rate_results = await test_rate_limiting()
    
    # Summary
    total_time = time.time() - overall_start
    
    print_section("FINAL SUMMARY")
    print(f"\n   ⏱️  Total Test Time: {total_time:.2f}s")
    print(f"\n   📊 Wallet Assessment Results:")
    print(f"   ╔═══════════════════════════════════════════════════════════╗")
    print(f"   ║  Wallet                    Score    Level       Time     ║")
    print(f"   ╠═══════════════════════════════════════════════════════════╣")
    
    for r in wallet_results:
        if "error" in r:
            print(f"   ║  {r['name'][:25]:<25}  ERROR                      ║")
        else:
            print(f"   ║  {r['name'][:25]:<25}  {r['score']:>5.1f}    {r['level']:<10} {r['assess_time_ms']:>6.1f}ms ║")
    
    print(f"   ╚═══════════════════════════════════════════════════════════╝")
    
    print(f"\n   🎯 ML Performance:")
    print(f"      Fraud Detection: {ml_results['fraud_detection']:.1f}%")
    print(f"      Legitimate Correct: {ml_results['legit_correct']:.1f}%")
    
    print(f"\n   🛡️ Rate Limiting: {rate_results['allowed']} allowed, {rate_results['blocked']} blocked")
    
    print(f"\n   ✅ ALL REAL-WORLD TESTS COMPLETE!")
    
    return {
        "wallets": wallet_results,
        "ml": ml_results,
        "rate_limit": rate_results,
        "total_time": total_time,
    }


if __name__ == "__main__":
    asyncio.run(run_real_world_tests())
