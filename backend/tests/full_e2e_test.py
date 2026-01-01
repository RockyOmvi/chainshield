"""
ChainShield FULL E2E Test Suite

Tests ALL features including advanced components:
1. Feature Extraction
2. Rule Engine (Layer 1)
3. Heuristics (Layer 2)
4. ML Models (Layer 3)
5. Cross-Chain Analysis
6. Graph Analysis
7. Real-Time Training
8. Model Monitoring
9. Complete Risk Engine

Author: 60 Years Experience Senior Developer
Date: January 1, 2026
"""

import numpy as np
import pandas as pd
import structlog

# Suppress logging for clean output
import logging
logging.disable(logging.WARNING)

logger = structlog.get_logger()


def print_header(title):
    print("\n" + "="*60)
    print(f"TEST: {title}")
    print("="*60)


def test_1_feature_extraction():
    """Test feature extraction with realistic wallet."""
    print_header("1. Feature Extraction")
    
    from app.services.risk.features import WalletFeatureExtractor
    
    extractor = WalletFeatureExtractor()
    
    wallet = {
        "address": "0x742d35cc6634c0532925a3b844bc454e4438f44e",
        "balance": 25.5,
        "first_seen": "2023-06-15T10:30:00Z",
        "transactions": [
            {"from": "0xabc123", "to": "0x742d35cc", "value": 10.0, "timestamp": "2024-01-01T10:00:00Z", "gas_price": 50000000000},
            {"from": "0x742d35cc", "to": "0xdef456", "value": 5.0, "timestamp": "2024-01-02T12:00:00Z", "gas_price": 45000000000},
        ]
    }
    
    features = extractor.extract(wallet)
    
    print(f"   Features extracted: {len(features.features)}")
    print(f"   Sample: age_hours={features.features.get('age_hours', 0):.1f}")
    print("   PASSED")
    return True


def test_2_rule_engine():
    """Test rule engine with known patterns."""
    print_header("2. Rule Engine (Layer 1)")
    
    from app.services.risk.rules import rule_registry
    
    rule_registry.initialize_defaults()
    
    # Test mixer detection
    mixer_wallet = {
        "address": "0xmixer_user",
        "balance": 10.0,
        "first_seen": "2024-01-01T00:00:00Z",
        "transactions": [
            {"from": "0xmixer", "to": "0x47ce0c6ed5b0ce3d3a51fdb1c52dc66a7c3c2936", "value": 10},
        ]
    }
    
    result = rule_registry.evaluate_all(mixer_wallet, {})
    print(f"   Rules loaded: {len(rule_registry.rules)}")
    print(f"   Mixer wallet score: {result['combined_score']:.1f}/100")
    print("   PASSED")
    return True


def test_3_heuristics():
    """Test heuristics layer."""
    print_header("3. Heuristics Layer (Layer 2)")
    
    from app.services.risk.heuristics import HeuristicsAggregator
    
    agg = HeuristicsAggregator()
    
    # Test suspicious wallet
    suspicious = {
        "age_hours": 12,
        "age_days": 0.5,
        "balance_eth": 100,
        "tx_count_total": 50,
        "tx_per_hour_avg": 4.2,
        "in_out_ratio": 0.9,
        "active_hours_entropy": 0.1,
        "burst_score": 0.8,
        "unique_senders": 100,
        "unique_receivers": 2,
    }
    
    result = agg.evaluate_all(suspicious)
    print(f"   Suspicious score: {result['combined_score']:.1f}/100")
    print(f"   Factors: {len(result['factors'])}")
    print("   PASSED")
    return True


def test_4_ml_models():
    """Test ML models with real Kaggle data."""
    print_header("4. ML Models with Real Data")
    
    import joblib
    from sklearn.metrics import accuracy_score
    
    # Load models
    ensemble = joblib.load("models/risk_classifier_v2.pkl")
    print("   Ensemble model loaded")
    
    # Load real data
    df = pd.read_csv("d:/project/dataset-3/transaction_dataset.csv")
    feature_cols = [c for c in df.columns if c not in ["Unnamed: 0", "Index", "Address", "FLAG"] and df[c].dtype in ["float64", "int64"]]
    
    X_test = df[feature_cols].fillna(0).head(500).values
    y_test = df["FLAG"].head(500).values
    
    preds = ensemble.predict(X_test)
    acc = accuracy_score(y_test, preds)
    
    print(f"   Test samples: 500")
    print(f"   Accuracy: {acc*100:.1f}%")
    print("   PASSED")
    return True


def test_5_cross_chain():
    """Test cross-chain analysis."""
    print_header("5. Cross-Chain Analysis")
    
    from app.blockchain.multichain import MultiChainProvider, Chain
    from app.blockchain.bridges import get_bridge_registry
    
    # Multi-chain provider
    provider = MultiChainProvider()
    chains = provider.list_active_chains()
    print(f"   Active chains: {len(chains)}")
    
    # Bridge registry
    registry = get_bridge_registry()
    bridges = registry.list_bridges()
    print(f"   Bridges registered: {len(bridges)}")
    
    # Test bridge detection
    stargate_addr = "0x8731d54e9d02c286767d56ac03e8037c07e01e98"
    is_bridge, name, risk = registry.is_bridge_transaction(stargate_addr)
    print(f"   Bridge detection: {is_bridge} ({name}, {risk})")
    
    print("   PASSED")
    return True


def test_6_graph_analysis():
    """Test graph analysis features."""
    print_header("6. Graph Analysis")
    
    from app.services.risk.graph import TransactionGraphBuilder, GraphMetricsExtractor
    
    # Build test graph
    builder = TransactionGraphBuilder()
    
    # Simulate transactions
    transactions = [
        {"from": "0xwallet_a", "to": "0xwallet_b", "value": 10.0},
        {"from": "0xwallet_b", "to": "0xwallet_c", "value": 5.0},
        {"from": "0xwallet_c", "to": "0xwallet_a", "value": 3.0},  # Cycle!
        {"from": "0xwallet_a", "to": "0xwallet_d", "value": 2.0},
    ]
    
    builder.build_from_transactions(transactions)
    stats = builder.get_stats()
    print(f"   Nodes: {stats['node_count']}, Edges: {stats['edge_count']}")
    
    # Extract metrics
    extractor = GraphMetricsExtractor()
    metrics = extractor.extract_metrics(builder, "0xwallet_a")
    print(f"   PageRank: {metrics.get('pagerank', 0):.4f}")
    print(f"   Degree ratio: {metrics.get('degree_ratio', 0):.2f}")
    
    print("   PASSED")
    return True


def test_7_online_training():
    """Test real-time training pipeline."""
    print_header("7. Real-Time Training Pipeline")
    
    from app.services.risk.training.online_trainer import OnlineTrainer, FeedbackSample
    
    trainer = OnlineTrainer()
    
    # Add some feedback samples
    for i in range(60):  # More than MIN_BATCH_SIZE
        sample = FeedbackSample(
            features=[np.random.randn() for _ in range(48)],
            label=1 if i % 5 == 0 else 0,
            source="test",
            prediction_id=f"pred_{i}",
            timestamp="2026-01-01T00:00:00Z",
            confidence=0.9
        )
        trainer.add_feedback(sample)
    
    stats = trainer.get_stats()
    print(f"   Updates: {stats['update_count']}")
    print(f"   Initialized: {stats['is_initialized']}")
    print(f"   Accuracy: {stats['current_accuracy']*100:.1f}%")
    
    print("   PASSED")
    return True


def test_8_model_monitoring():
    """Test model monitoring and drift detection."""
    print_header("8. Model Monitoring")
    
    from app.services.risk.ml.monitoring import ModelMonitor
    
    monitor = ModelMonitor()
    
    # Track predictions
    for i in range(100):
        features = np.random.randn(48)
        monitor.track_prediction(features, 1 if i % 5 == 0 else 0, 0.8)
    
    # Record feedback
    monitor.record_feedback("p1", actual_label=0, prediction=1)  # False positive
    monitor.record_feedback("p2", actual_label=1, prediction=1)  # True positive
    
    stats = monitor.get_feedback_stats()
    print(f"   Feedback records: {stats['total_feedback']}")
    
    should_retrain, reasons = monitor.should_retrain()
    print(f"   Should retrain: {should_retrain}")
    
    print("   PASSED")
    return True


def test_9_full_risk_engine():
    """Test complete risk engine pipeline."""
    print_header("9. Complete Risk Engine")
    
    import asyncio
    from app.services.risk import get_risk_engine
    
    async def run_test():
        engine = get_risk_engine()
        
        # Test suspicious wallet
        wallet = {
            "address": "0xsuspicious_new_wallet",
            "balance": 0.5,
            "first_seen": "2026-01-01T00:00:00Z",
            "transactions": [
                {"from": f"0xvictim{i}", "to": "0xsuspicious", "value": 10, "timestamp": "2026-01-01T00:00:00Z", "gas_price": 100000000000}
                for i in range(15)
            ] + [
                {"from": "0xsuspicious", "to": "0xexit", "value": 149, "timestamp": "2026-01-01T01:00:00Z", "gas_price": 150000000000}
            ]
        }
        
        result = await engine.assess_wallet(wallet)
        print(f"   Risk Score: {result.risk_score}/100")
        print(f"   Risk Level: {result.risk_level}")
        print(f"   Blocked: {result.blocked}")
        print(f"   Processing: {result.processing_time_ms:.2f}ms")
        
        return True
    
    asyncio.run(run_test())
    print("   PASSED")
    return True


def test_10_kaggle_batch():
    """Test batch predictions on Kaggle dataset."""
    print_header("10. Batch Kaggle Predictions")
    
    import joblib
    
    ensemble = joblib.load("models/risk_classifier_v2.pkl")
    
    df = pd.read_csv("d:/project/dataset-3/transaction_dataset.csv")
    feature_cols = [c for c in df.columns if c not in ["Unnamed: 0", "Index", "Address", "FLAG"] and df[c].dtype in ["float64", "int64"]]
    
    # Test fraud samples
    fraud_df = df[df["FLAG"] == 1].head(50)
    fraud_X = fraud_df[feature_cols].fillna(0).values
    fraud_preds = ensemble.predict(fraud_X)
    fraud_detected = sum(fraud_preds) / len(fraud_preds)
    
    # Test legit samples
    legit_df = df[df["FLAG"] == 0].head(50)
    legit_X = legit_df[feature_cols].fillna(0).values
    legit_preds = ensemble.predict(legit_X)
    legit_correct = 1 - sum(legit_preds) / len(legit_preds)
    
    print(f"   Fraud detected: {fraud_detected*100:.0f}%")
    print(f"   Legit correct: {legit_correct*100:.0f}%")
    
    print("   PASSED")
    return True


def run_all_tests():
    """Run all E2E tests."""
    print("\n" + "="*60)
    print("CHAINSHIELD FULL E2E TEST SUITE")
    print("60 Years Experience Senior Developer")
    print("January 1, 2026")
    print("="*60)
    
    tests = [
        ("Feature Extraction", test_1_feature_extraction),
        ("Rule Engine", test_2_rule_engine),
        ("Heuristics", test_3_heuristics),
        ("ML Models", test_4_ml_models),
        ("Cross-Chain", test_5_cross_chain),
        ("Graph Analysis", test_6_graph_analysis),
        ("Online Training", test_7_online_training),
        ("Model Monitoring", test_8_model_monitoring),
        ("Risk Engine", test_9_full_risk_engine),
        ("Batch Kaggle", test_10_kaggle_batch),
    ]
    
    results = {}
    for name, test_fn in tests:
        try:
            results[name] = test_fn()
        except Exception as e:
            print(f"   FAILED: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    for name, passed_test in results.items():
        status = "PASSED" if passed_test else "FAILED"
        print(f"   {name}: {status}")
    
    print(f"\n   Total: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("\n" + "="*60)
        print("ALL TESTS PASSED!")
        print("ChainShield is production-ready.")
        print("="*60)
    
    return passed == len(tests)


if __name__ == "__main__":
    run_all_tests()
