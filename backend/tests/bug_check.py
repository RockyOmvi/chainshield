"""Bug check script for ChainShield."""
import sys

print("="*60)
print("BUG CHECK: Testing critical edge cases")
print("="*60)

errors = []

# Test 1: All imports work
try:
    from app.services.risk import get_risk_engine
    print("1. Risk engine import: OK")
except Exception as e:
    errors.append(f"Risk engine import: {e}")
    print(f"1. Risk engine import: FAIL - {e}")

# Test 2: Feature extraction handles empty
try:
    from app.services.risk.features import WalletFeatureExtractor
    extractor = WalletFeatureExtractor()
    result = extractor.extract({"address": "0x123", "balance": 0, "first_seen": "2024-01-01", "transactions": []})
    print(f"2. Empty wallet features: OK ({len(result.features)} features)")
except Exception as e:
    errors.append(f"Empty wallet: {e}")
    print(f"2. Empty wallet features: FAIL - {e}")

# Test 3: Division by zero in heuristics
try:
    from app.services.risk.heuristics import HeuristicsAggregator
    agg = HeuristicsAggregator()
    result = agg.evaluate_all({"age_hours": 0, "tx_count_total": 0})
    score = result["combined_score"]
    print(f"3. Division by zero handling: OK (score: {score:.1f})")
except Exception as e:
    errors.append(f"Division by zero: {e}")
    print(f"3. Division by zero handling: FAIL - {e}")

# Test 4: Model loading
try:
    import joblib
    model = joblib.load("models/risk_classifier_v2.pkl")
    print("4. Model loading: OK")
except Exception as e:
    errors.append(f"Model loading: {e}")
    print(f"4. Model loading: FAIL - {e}")

# Test 5: Graph with no edges
try:
    from app.services.risk.graph import TransactionGraphBuilder, GraphMetricsExtractor
    builder = TransactionGraphBuilder()
    extractor = GraphMetricsExtractor()
    metrics = extractor.extract_metrics(builder, "0xtest")
    print("5. Empty graph handling: OK")
except Exception as e:
    errors.append(f"Empty graph: {e}")
    print(f"5. Empty graph handling: FAIL - {e}")

# Test 6: Bridge detection with invalid address
try:
    from app.blockchain.bridges import get_bridge_registry
    registry = get_bridge_registry()
    result = registry.is_bridge_transaction("")
    print("6. Empty address bridge check: OK")
except Exception as e:
    errors.append(f"Bridge check: {e}")
    print(f"6. Empty address bridge check: FAIL - {e}")

# Test 7: Online trainer with bad source
try:
    from app.services.risk.training.online_trainer import OnlineTrainer, FeedbackSample
    trainer = OnlineTrainer()
    sample = FeedbackSample(
        features=[0]*48,
        label=1,
        source="malicious_attacker",
        prediction_id="test",
        timestamp="2026-01-01"
    )
    accepted = trainer.add_feedback(sample)
    print(f"7. Unknown source handling: OK (accepted={accepted})")
except Exception as e:
    errors.append(f"Online trainer: {e}")
    print(f"7. Unknown source handling: FAIL - {e}")

print()
print("="*60)
if errors:
    print(f"FOUND {len(errors)} ISSUES:")
    for e in errors:
        print(f"  - {e}")
else:
    print("ALL CHECKS PASSED - NO BUGS FOUND")
print("="*60)
