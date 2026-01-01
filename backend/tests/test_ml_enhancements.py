"""
Test for 5 ML Enhancements (Simplified)
"""

import numpy as np


def test_token_features():
    """Test token feature extractor."""
    print("TEST 1: Token Features")
    
    # Import directly to avoid chain
    import sys
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "token_features",
        "app/services/risk/features/token_features.py"
    )
    module = importlib.util.module_from_spec(spec)
    
    # Create mock for structlog
    class MockLogger:
        def bind(self, **kw): return self
        def debug(self, *a, **kw): pass
        def info(self, *a, **kw): pass
        
    sys.modules['structlog'] = type('structlog', (), {'get_logger': lambda: MockLogger()})()
    
    spec.loader.exec_module(module)
    
    extractor = module.TokenFeatureExtractor()
    
    wallet = {
        "token_transfers": [
            {"token_address": "0xtoken1", "value": 100, "direction": "in"},
        ],
        "transactions": []
    }
    
    features = extractor.extract(wallet)
    
    print(f"   Features: {len(features.features)}")
    assert len(features.features) >= 10
    print("   ✅ PASSED")
    return True


def test_smote_trainer():
    """Test SMOTE trainer structure."""
    print("\nTEST 2: SMOTE Trainer")
    
    # Simple check that class exists
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "smote",
        "app/services/risk/training/smote_trainer.py"
    )
    module = importlib.util.module_from_spec(spec)
    
    class MockLogger:
        def bind(self, **kw): return self
        def info(self, *a, **kw): pass
        def warning(self, *a, **kw): pass
        def error(self, *a, **kw): pass
        
    import sys
    sys.modules['structlog'] = type('structlog', (), {'get_logger': lambda: MockLogger()})()
    
    spec.loader.exec_module(module)
    
    trainer = module.SMOTETrainer()
    
    assert hasattr(trainer, "train_with_smote")
    print("   SMOTE class: OK")
    print("   ✅ PASSED")
    return True


def test_gnn_embeddings():
    """Test GNN embedding extractor."""
    print("\nTEST 3: GNN Embeddings")
    
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "gnn",
        "app/services/risk/ml/gnn_embedding.py"
    )
    module = importlib.util.module_from_spec(spec)
    
    class MockLogger:
        def bind(self, **kw): return self
        def debug(self, *a, **kw): pass
        
    import sys
    sys.modules['structlog'] = type('structlog', (), {'get_logger': lambda: MockLogger()})()
    
    spec.loader.exec_module(module)
    
    gnn = module.GNNEmbedding(embedding_dim=32, num_hops=2)
    
    node_features = np.random.randn(48)
    neighbor_features = [np.random.randn(48) for _ in range(5)]
    
    embedding = gnn.compute_embedding(node_features, neighbor_features)
    
    print(f"   Embedding dim: {len(embedding)}")
    assert len(embedding) == 32
    print("   ✅ PASSED")
    return True


def test_timeseries_patterns():
    """Test time-series pattern detector."""
    print("\nTEST 4: Time-Series Patterns")
    
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ts",
        "app/services/risk/features/timeseries_patterns.py"
    )
    module = importlib.util.module_from_spec(spec)
    
    class MockLogger:
        def bind(self, **kw): return self
        def debug(self, *a, **kw): pass
        
    import sys
    sys.modules['structlog'] = type('structlog', (), {'get_logger': lambda: MockLogger()})()
    
    spec.loader.exec_module(module)
    
    detector = module.TimeSeriesPatternDetector()
    
    transactions = [
        {"timestamp": "2024-01-01T03:00:00Z"},
        {"timestamp": "2024-01-01T03:01:00Z"},
        {"timestamp": "2024-01-01T04:00:00Z"},
    ]
    
    features = detector.extract_all_patterns(transactions)
    
    print(f"   Features: {len(features)}")
    assert len(features) >= 10
    print("   ✅ PASSED")
    return True


def test_nlp_explainer():
    """Test NLP explainer."""
    print("\nTEST 5: NLP Explainer")
    
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "nlp",
        "app/services/risk/ml/nlp_explainer.py"
    )
    module = importlib.util.module_from_spec(spec)
    
    class MockLogger:
        def bind(self, **kw): return self
        def debug(self, *a, **kw): pass
        
    import sys
    sys.modules['structlog'] = type('structlog', (), {'get_logger': lambda: MockLogger()})()
    
    spec.loader.exec_module(module)
    
    explainer = module.NaturalLanguageExplainer()
    
    wallet = {
        "address": "0x742d35cc6634c0532925a3b844bc454e4438f44e",
        "balance": 0.05,
        "age_hours": 12,
        "transactions": [{}] * 30,
    }
    
    explanation = explainer.generate_summary(
        risk_score=75,
        risk_level="high",
        wallet_data=wallet
    )
    
    print(f"   Summary length: {len(explanation.summary)}")
    assert len(explanation.summary) > 20
    print("   ✅ PASSED")
    return True


def run_all_tests():
    """Run all enhancement tests."""
    print("="*60)
    print("ML ENHANCEMENT TESTS (Simplified)")
    print("="*60)
    
    tests = [
        test_token_features,
        test_smote_trainer,
        test_gnn_embeddings,
        test_timeseries_patterns,
        test_nlp_explainer,
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"   ❌ FAILED: {e}")
    
    print("\n" + "="*60)
    print(f"RESULT: {passed}/5 tests passed")
    print("="*60)
    
    if passed == 5:
        print("🎉 ALL ML ENHANCEMENTS WORKING!")
    
    return passed == 5


if __name__ == "__main__":
    run_all_tests()
