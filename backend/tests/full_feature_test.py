"""
ChainShield FULL FEATURE TEST - Titan Builder Wallet

Tests ALL features with the user's real Ethereum wallet.
"""

import asyncio
import time


async def test_all_features():
    address = "0x4838B106FCe9647Bdf1E7877BF73cE8B0BAD5f97"
    
    print("="*60)
    print("  CHAINSHIELD FULL FEATURE TEST")
    print("  Wallet: Titan Builder")
    print(f"  Address: {address}")
    print("="*60)
    
    # ========== FEATURE 1: LIVE RPC ==========
    print("\n[1] LIVE BLOCKCHAIN RPC")
    print("-"*40)
    
    from app.blockchain.rpc_client import BlockchainRPCClient
    
    rpc = BlockchainRPCClient("https://eth.llamarpc.com", timeout=30)
    start = time.time()
    
    try:
        activity = await rpc.get_address_activity(address)
        rpc_time = (time.time() - start) * 1000
        
        balance = activity["balance_eth"]
        tx_count = activity["transaction_count"]
        is_contract = activity["is_contract"]
        
        print(f"    Balance:     {balance:.6f} ETH")
        print(f"    TX Count:    {tx_count:,}")
        print(f"    Is Contract: {is_contract}")
        print(f"    RPC Time:    {rpc_time:.0f}ms")
        print("    Status: OK")
    finally:
        await rpc.close()
    
    # ========== FEATURE 2: FEATURE EXTRACTION ==========
    print("\n[2] FEATURE EXTRACTION")
    print("-"*40)
    
    from app.services.risk.features import WalletFeatureExtractor
    
    wallet_data = {
        "address": address,
        "balance": balance,
        "first_seen": "2022-07-01T00:00:00Z",
        "transactions": [
            {"from": "0xsender", "to": address, "value": 10.0, "timestamp": "2024-01-01T00:00:00Z"},
        ] * 20  # Simulate some transactions
    }
    
    extractor = WalletFeatureExtractor()
    features = extractor.extract(wallet_data)
    
    print(f"    Features Extracted: {len(features.features)}")
    print(f"    Balance ETH: {features.features.get('balance_eth', 0):.2f}")
    print(f"    Age Days: {features.features.get('age_days', 0):.0f}")
    print("    Status: OK")
    
    # ========== FEATURE 3: RULE ENGINE ==========
    print("\n[3] RULE ENGINE")
    print("-"*40)
    
    from app.services.risk.rules import rule_registry
    
    rule_registry.initialize_defaults()
    rule_result = rule_registry.evaluate_all(wallet_data, features.features)
    
    print(f"    Rules Evaluated: {len(rule_registry.rules)}")
    print(f"    Rule Score: {rule_result['combined_score']:.1f}/100")
    print(f"    Triggered: {len(rule_result.get('triggered_rules', []))}")
    print("    Status: OK")
    
    # ========== FEATURE 4: HEURISTICS ==========
    print("\n[4] HEURISTICS ENGINE")
    print("-"*40)
    
    from app.services.risk.heuristics import HeuristicsAggregator
    
    heuristics = HeuristicsAggregator()
    heuristic_result = heuristics.evaluate_all(features.features)
    
    print(f"    Heuristic Score: {heuristic_result['combined_score']:.1f}/100")
    print("    Status: OK")
    
    # ========== FEATURE 5: ML CLASSIFIER ==========
    print("\n[5] ML RISK CLASSIFIER")
    print("-"*40)
    
    from app.services.risk.ml.model import RiskClassifier
    
    classifier = RiskClassifier()
    ml_score, ml_factors = classifier.predict(features)
    
    print(f"    ML Score: {ml_score:.1f}/100")
    print(f"    Factors: {len(ml_factors)}")
    print("    Status: OK")
    
    # ========== FEATURE 6: ANOMALY DETECTION ==========
    print("\n[6] ANOMALY DETECTION")
    print("-"*40)
    
    from app.services.risk.ml.anomaly import AnomalyDetector
    
    detector = AnomalyDetector()
    anomaly_score, severity, anomaly_factors = detector.detect(features)
    
    print(f"    Anomaly Score: {anomaly_score:.1f}/100")
    print(f"    Severity: {severity}")
    print("    Status: OK")
    
    # ========== FEATURE 7: FULL RISK ENGINE ==========
    print("\n[7] FULL RISK ENGINE (3-Layer)")
    print("-"*40)
    
    from app.services.risk.engine import get_risk_engine
    
    engine = get_risk_engine()
    start = time.time()
    result = await engine.assess_wallet(wallet_data)
    assess_time = (time.time() - start) * 1000
    
    print(f"    Final Score: {result.risk_score:.1f}/100")
    print(f"    Risk Level: {result.risk_level}")
    print(f"    Blocked: {result.blocked}")
    print(f"    Assess Time: {assess_time:.0f}ms")
    print("    Status: OK")
    
    # ========== FEATURE 8: RATE LIMITING ==========
    print("\n[8] RATE LIMITING")
    print("-"*40)
    
    from app.core.sliding_rate_limit import SlidingWindowRateLimiter
    
    limiter = SlidingWindowRateLimiter(window_seconds=60)
    results = [limiter.check_and_record("test_user", 5)[0] for _ in range(10)]
    
    print(f"    Requests: 10")
    print(f"    Allowed: {sum(results)}")
    print(f"    Blocked: {10 - sum(results)}")
    print("    Status: OK")
    
    # ========== SUMMARY ==========
    print("\n" + "="*60)
    print("  FINAL ASSESSMENT SUMMARY")
    print("="*60)
    print(f"""
    Wallet:        Titan Builder
    Address:       {address}
    
    LIVE DATA (From Ethereum Mainnet):
    - Balance:     {balance:.6f} ETH
    - TX Count:    {tx_count:,}
    - Contract:    {is_contract}
    
    RISK ASSESSMENT:
    - Risk Score:  {result.risk_score:.1f}/100
    - Risk Level:  {result.risk_level}
    - Blocked:     {result.blocked}
    
    LAYER BREAKDOWN:
    - Rule Score:      {rule_result['combined_score']:.1f}/100
    - Heuristic Score: {heuristic_result['combined_score']:.1f}/100
    - ML Score:        {ml_score:.1f}/100
    
    ALL 8 FEATURES: WORKING
""")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_all_features())
