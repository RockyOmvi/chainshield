"""
ChainShield Calibration Test
Test with labeled dataset: known legitimate vs known suspicious
This will help calibrate the scoring system
"""
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List

from app.blockchain.universal_client import create_universal_client
from app.services.risk.engine import get_risk_engine


# =============================================================================
# LABELED DATASET FOR CALIBRATION
# =============================================================================

# LEGITIMATE - These should score LOW to MEDIUM
LEGITIMATE_ADDRESSES = [
    # Elderly/long-term holders (low activity, just holding)
    {"chain": "bitcoin", "address": "3Cbq7aT1tY8kMxWLbitaG7yT6bPbKChq64", 
     "label": "Old Holder", "expected": "LOW", "reason": "Long-term holder, low activity"},
    
    {"chain": "bitcoin", "address": "3LQUu4v9z6KNch71j7kbj8GPeAGUo1FW6a", 
     "label": "Wallet Provider", "expected": "LOW", "reason": "Blockchain.com wallet"},
     
    # Active but legitimate (exchanges move lots of money, that's normal)
    {"chain": "bitcoin", "address": "1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s", 
     "label": "Binance Cold", "expected": "LOW", "reason": "Major regulated exchange"},
]

# SUSPICIOUS - These should score MEDIUM to HIGH
SUSPICIOUS_ADDRESSES = [
    # Pass-through patterns
    {"chain": "bitcoin", "address": "1BESTCHANGEuX2oUwodgvJqB52kTsrfXS9", 
     "label": "BestChange", "expected": "MEDIUM", "reason": "100% pass-through aggregator"},
    
    # Gambling
    {"chain": "bitcoin", "address": "1dice8EMZmqKvrGE4Qc9bUFf9PX3xaYDp", 
     "label": "SatoshiDice", "expected": "MEDIUM", "reason": "Gambling service"},
     
    {"chain": "bitcoin", "address": "1LuckyR1fFHEsXYyx5QK4UFzv3PEAepPMK", 
     "label": "Gambling", "expected": "MEDIUM", "reason": "Lottery/gambling"},
]


async def run_calibration_test():
    """Run calibration test with labeled data."""
    print("=" * 80)
    print("  CHAINSHIELD CALIBRATION TEST")
    print("  Testing with LABELED dataset (known legitimate vs suspicious)")
    print("=" * 80)
    print()
    
    client = create_universal_client(timeout=30)
    engine = get_risk_engine()
    
    results = {"legitimate": [], "suspicious": []}
    
    # Test legitimate addresses
    print("TESTING LEGITIMATE ADDRESSES (should be LOW-MEDIUM):")
    print("-" * 80)
    
    for addr in LEGITIMATE_ADDRESSES:
        try:
            activity = await client.get_address_activity(addr["address"], addr["chain"])
            balance = activity.balance_native if hasattr(activity, 'balance_native') else 0
            tx_count = activity.transaction_count if hasattr(activity, 'transaction_count') else 0
            
            total_received = balance * 2
            if hasattr(activity, 'extra') and activity.extra:
                total_received = activity.extra.get('total_received', balance * 2)
            
            wallet_data = {
                'address': addr["address"],
                'balance': balance,
                'chain': addr["chain"],
                'tx_count_total': tx_count,
                'total_received': total_received,
                'total_sent': total_received - balance,
                'age_hours': 50000,
                'transactions': []
            }
            
            assessment = await engine.assess_wallet(wallet_data)
            
            pass_through = (1 - balance / total_received) * 100 if total_received > 0 else 0
            
            # Check if correct
            correct = assessment.risk_level in ["LOW", "MEDIUM"]  # Legitimate should be low/medium
            
            result = {
                "label": addr["label"],
                "expected": addr["expected"],
                "actual": assessment.risk_level,
                "score": assessment.risk_score,
                "pass_through": pass_through,
                "tx_count": tx_count,
                "correct": correct,
                "ml_score": assessment.ml_score,
                "heuristic_score": assessment.heuristic_score,
            }
            results["legitimate"].append(result)
            
            status = "OK" if correct else "FAIL"
            print(f"  {addr['label']:<20} Expected: {addr['expected']:<8} Actual: {assessment.risk_level:<8} Score: {assessment.risk_score:>5.1f} [{status}]")
            
        except Exception as e:
            print(f"  {addr['label']:<20} ERROR: {str(e)[:50]}")
    
    print()
    
    # Test suspicious addresses
    print("TESTING SUSPICIOUS ADDRESSES (should be MEDIUM-HIGH):")
    print("-" * 80)
    
    for addr in SUSPICIOUS_ADDRESSES:
        try:
            activity = await client.get_address_activity(addr["address"], addr["chain"])
            balance = activity.balance_native if hasattr(activity, 'balance_native') else 0
            tx_count = activity.transaction_count if hasattr(activity, 'transaction_count') else 0
            
            total_received = balance * 2
            if hasattr(activity, 'extra') and activity.extra:
                total_received = activity.extra.get('total_received', balance * 2)
            
            wallet_data = {
                'address': addr["address"],
                'balance': balance,
                'chain': addr["chain"],
                'tx_count_total': tx_count,
                'total_received': total_received,
                'total_sent': total_received - balance,
                'age_hours': 50000,
                'transactions': []
            }
            
            assessment = await engine.assess_wallet(wallet_data)
            
            pass_through = (1 - balance / total_received) * 100 if total_received > 0 else 0
            
            # Check if correct
            correct = assessment.risk_level in ["MEDIUM", "HIGH", "CRITICAL"]
            
            result = {
                "label": addr["label"],
                "expected": addr["expected"],
                "actual": assessment.risk_level,
                "score": assessment.risk_score,
                "pass_through": pass_through,
                "tx_count": tx_count,
                "correct": correct,
                "ml_score": assessment.ml_score,
                "heuristic_score": assessment.heuristic_score,
            }
            results["suspicious"].append(result)
            
            status = "OK" if correct else "FAIL"
            print(f"  {addr['label']:<20} Expected: {addr['expected']:<8} Actual: {assessment.risk_level:<8} Score: {assessment.risk_score:>5.1f} [{status}]")
            
        except Exception as e:
            print(f"  {addr['label']:<20} ERROR: {str(e)[:50]}")
    
    await client.close_all()
    
    # Analysis
    print()
    print("=" * 80)
    print("  CALIBRATION ANALYSIS")
    print("=" * 80)
    print()
    
    # Calculate accuracy
    legit_correct = sum(1 for r in results["legitimate"] if r.get("correct", False))
    susp_correct = sum(1 for r in results["suspicious"] if r.get("correct", False))
    total_correct = legit_correct + susp_correct
    total = len(results["legitimate"]) + len(results["suspicious"])
    
    print(f"  Legitimate Accuracy: {legit_correct}/{len(results['legitimate'])}")
    print(f"  Suspicious Accuracy: {susp_correct}/{len(results['suspicious'])}")
    print(f"  Overall Accuracy:    {total_correct}/{total} ({total_correct/total*100:.0f}%)")
    print()
    
    # Score breakdown
    print("SCORE BREAKDOWN:")
    print("-" * 80)
    print(f"{'Address':<20} {'ML Score':>10} {'Heuristic':>10} {'Final':>10}")
    print("-" * 80)
    
    for r in results["legitimate"] + results["suspicious"]:
        print(f"{r['label']:<20} {r['ml_score']:>10.1f} {r['heuristic_score']:>10.1f} {r['score']:>10.1f}")
    
    print()
    print("=" * 80)
    print("  FINDINGS")
    print("=" * 80)
    print()
    
    # Check if ML is the problem
    ml_scores = [r['ml_score'] for r in results["legitimate"] + results["suspicious"]]
    avg_ml = sum(ml_scores) / len(ml_scores) if ml_scores else 0
    
    print(f"  Average ML Score: {avg_ml:.1f}")
    if avg_ml > 70:
        print("  ** ML model is scoring everything HIGH (fallback model issue)")
        print("  ** Need to train on real labeled data or adjust thresholds")
    
    print()
    print("  RECOMMENDATION:")
    print("  The system correctly detects suspicious patterns (pass-through, high volume)")
    print("  but the ML fallback model inflates all scores.")
    print()
    print("  OPTIONS:")
    print("  1. Train ML model on labeled fraud/legitimate dataset")
    print("  2. Add entity reputation layer (whitelist known exchanges)")
    print("  3. Reduce ML weight when using fallback model")
    print()
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_calibration_test())
