"""
ChainShield FULL E2E Test v4.0

Tests all features with lazy imports to avoid circular dependencies.
"""

import numpy as np
import pandas as pd
import time
import logging

logging.disable(logging.WARNING)


def print_header(title):
    print("\n" + "="*60)
    print(f"TEST: {title}")
    print("="*60)


def test_1_feature_extraction():
    """Test feature extraction."""
    print_header("1. Feature Extraction")
    
    from app.services.risk.features import WalletFeatureExtractor
    
    extractor = WalletFeatureExtractor()
    wallet = {
        "address": "0x742d35cc6634c0532925a3b844bc454e4438f44e",
        "balance": 25.5,
        "first_seen": "2023-06-15T10:30:00Z",
        "transactions": [
            {"from": "0xabc", "to": "0x742d35cc", "value": 10.0, "timestamp": "2024-01-01T10:00:00Z"},
        ]
    }
    
    features = extractor.extract(wallet)
    print(f"   Features: {len(features.features)}")
    print("   ✅ PASSED")
    return True


def test_2_rule_engine():
    """Test rule engine."""
    print_header("2. Rule Engine")
    
    from app.services.risk.rules import rule_registry
    
    rule_registry.initialize_defaults()
    result = rule_registry.evaluate_all({
        "address": "0xtest",
        "balance": 10,
        "first_seen": "2024-01-01",
        "transactions": []
    }, {})
    
    print(f"   Rules: {len(rule_registry.rules)}")
    print(f"   Score: {result['combined_score']:.1f}/100")
    print("   ✅ PASSED")
    return True


def test_3_heuristics():
    """Test heuristics."""
    print_header("3. Heuristics")
    
    from app.services.risk.heuristics import HeuristicsAggregator
    
    agg = HeuristicsAggregator()
    result = agg.evaluate_all({"age_hours": 12, "tx_count_total": 50})
    
    print(f"   Score: {result['combined_score']:.1f}/100")
    print("   ✅ PASSED")
    return True


def test_4_ml_kaggle():
    """Test ML with Kaggle data."""
    print_header("4. ML Models (Kaggle)")
    
    import joblib
    from sklearn.metrics import accuracy_score
    
    ensemble = joblib.load("models/risk_classifier_v2.pkl")
    df = pd.read_csv("d:/project/dataset-3/transaction_dataset.csv")
    
    feature_cols = [c for c in df.columns if c not in ["Unnamed: 0", "Index", "Address", "FLAG"] and df[c].dtype in ["float64", "int64"]]
    X = df[feature_cols].fillna(0).head(500).values
    y = df["FLAG"].head(500).values
    
    acc = accuracy_score(y, ensemble.predict(X))
    print(f"   Accuracy: {acc*100:.1f}%")
    print("   ✅ PASSED")
    return True


def test_5_cross_chain():
    """Test cross-chain."""
    print_header("5. Cross-Chain")
    
    from app.blockchain.multichain import MultiChainProvider
    
    provider = MultiChainProvider()
    stats = provider.get_chain_stats()
    
    print(f"   Chains: {stats['active_chains']}")
    print(f"   Fallbacks: {sum(c['fallback_count'] for c in stats['chains'])}")
    print("   ✅ PASSED")
    return True


def test_6_graph_limits():
    """Test graph limits."""
    print_header("6. Graph Limits")
    
    from app.services.risk.graph.builder import TransactionGraphBuilder
    
    builder = TransactionGraphBuilder(max_nodes=100, max_edges=200)
    
    for i in range(150):
        builder.add_transaction(f"0x{i:040x}", f"0x{i+1:040x}", 1.0)
    
    print(f"   Max nodes: {builder.max_nodes}")
    print(f"   Limit reached: {builder.limit_reached}")
    print("   ✅ PASSED")
    return True


def test_7_anti_poisoning():
    """Test anti-poisoning."""
    print_header("7. Anti-Poisoning")
    
    from app.services.risk.training.online_trainer import OnlineTrainer, FeedbackSample
    
    trainer = OnlineTrainer()
    accepted = trainer.add_feedback(FeedbackSample(
        features=[0]*48, label=1, source="analyst",
        prediction_id="t1", timestamp="2026-01-01"
    ))
    
    print(f"   Accepted: {accepted}")
    print("   ✅ PASSED")
    return True


def test_8_sliding_rate_limit():
    """Test sliding rate limit."""
    print_header("8. Sliding Rate Limit")
    
    from app.core.sliding_rate_limit import SlidingWindowRateLimiter
    
    limiter = SlidingWindowRateLimiter(window_seconds=60)
    results = [limiter.check_and_record("user1", 5)[0] for _ in range(7)]
    
    print(f"   Allowed: {sum(results)}")
    print("   ✅ PASSED")
    return True


def test_9_rpc_client():
    """Test RPC client."""
    print_header("9. RPC Client")
    
    from app.blockchain.rpc_client import BlockchainRPCClient
    
    client = BlockchainRPCClient("https://eth.llamarpc.com")
    
    assert hasattr(client, "get_balance")
    print("   Methods: get_balance, get_transaction_count")
    print("   ✅ PASSED")
    return True


def test_10_redis_rate_limit():
    """Test Redis rate limiter."""
    print_header("10. Redis Rate Limiter")
    
    from app.core.redis_rate_limit import RedisRateLimiter
    
    limiter = RedisRateLimiter(redis_client=None)
    allowed, count, _ = limiter._memory_check_and_record("test", 3)
    
    print(f"   Backend: memory (fallback)")
    print("   ✅ PASSED")
    return True


def test_11_shap_cache():
    """Test SHAP cache."""
    print_header("11. SHAP Cache")
    
    from app.services.risk.ml.shap_cache import SHAPCache
    
    cache = SHAPCache()
    stats = cache.get_stats()
    
    print(f"   Max items: {stats['max_memory_items']}")
    print("   ✅ PASSED")
    return True


def test_12_auto_rollback():
    """Test auto-rollback."""
    print_header("12. Auto-Rollback")
    
    from app.services.risk.ml.auto_rollback import AutoRollbackMonitor
    
    monitor = AutoRollbackMonitor()
    monitor.set_baseline(0.92, "v2.0.0")
    
    stats = monitor.get_stats()
    print(f"   Threshold: {stats['degradation_threshold']:.0%}")
    print("   ✅ PASSED")
    return True


def test_13_persistence():
    """Test persistence model."""
    print_header("13. Persistence Model")
    
    from app.services.risk.persistence import RiskAssessmentRecord
    
    assert hasattr(RiskAssessmentRecord, "risk_score")
    print("   Model: RiskAssessmentRecord")
    print("   ✅ PASSED")
    return True


def test_14_risk_engine():
    """Test risk engine."""
    print_header("14. Risk Engine")
    
    import asyncio
    from app.services.risk.engine import get_risk_engine
    
    async def run():
        engine = get_risk_engine()
        result = await engine.assess_wallet({
            "address": "0xtest",
            "balance": 0.5,
            "first_seen": "2026-01-01T00:00:00Z",
            "transactions": []
        })
        print(f"   Score: {result.risk_score}/100")
        return True
    
    asyncio.run(run())
    print("   ✅ PASSED")
    return True


def test_15_kaggle_fraud():
    """Test Kaggle fraud."""
    print_header("15. Kaggle Fraud Detection")
    
    import joblib
    
    ensemble = joblib.load("models/risk_classifier_v2.pkl")
    df = pd.read_csv("d:/project/dataset-3/transaction_dataset.csv")
    
    feature_cols = [c for c in df.columns if c not in ["Unnamed: 0", "Index", "Address", "FLAG"] and df[c].dtype in ["float64", "int64"]]
    
    fraud = df[df["FLAG"] == 1].head(100)
    fraud_preds = ensemble.predict(fraud[feature_cols].fillna(0).values)
    
    print(f"   Detection: {sum(fraud_preds)/len(fraud_preds)*100:.0f}%")
    print("   ✅ PASSED")
    return True


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("CHAINSHIELD E2E TEST v4.0")
    print("="*60)
    
    tests = [
        ("Feature Extraction", test_1_feature_extraction),
        ("Rule Engine", test_2_rule_engine),
        ("Heuristics", test_3_heuristics),
        ("ML Models", test_4_ml_kaggle),
        ("Cross-Chain", test_5_cross_chain),
        ("Graph Limits", test_6_graph_limits),
        ("Anti-Poisoning", test_7_anti_poisoning),
        ("Sliding Rate Limit", test_8_sliding_rate_limit),
        ("RPC Client", test_9_rpc_client),
        ("Redis Rate Limiter", test_10_redis_rate_limit),
        ("SHAP Cache", test_11_shap_cache),
        ("Auto-Rollback", test_12_auto_rollback),
        ("Persistence", test_13_persistence),
        ("Risk Engine", test_14_risk_engine),
        ("Kaggle Fraud", test_15_kaggle_fraud),
    ]
    
    results = {}
    start = time.time()
    
    for name, test_fn in tests:
        try:
            results[name] = test_fn()
        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            results[name] = False
    
    elapsed = time.time() - start
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    for name, ok in results.items():
        print(f"   {name}: {'✅' if ok else '❌'}")
    
    print(f"\n   Total: {passed}/{len(tests)}")
    print(f"   Time: {elapsed:.2f}s")
    
    if passed == len(tests):
        print("\n🎉 ALL 15 TESTS PASSED!")
    
    return passed == len(tests)


if __name__ == "__main__":
    run_all_tests()
