"""
ChainShield Comprehensive Scenario Test
Tests ALL risk factor combinations with synthetic data

This demonstrates the full detection capabilities:
1. Account age (new vs old)
2. Transaction patterns (normal vs suspicious)
3. Blacklist interactions (Tornado Cash, Lazarus Group)
4. Pass-through patterns (laundering)
5. High volume anomalies
6. Entity reputation (known vs unknown)
7. Mixer interactions
8. Bot-like behavior patterns
"""
import asyncio
from datetime import datetime

from app.services.risk.engine import get_risk_engine
from app.services.risk.ml.nlp_explainer import get_nlp_explainer


# =============================================================================
# SYNTHETIC TEST SCENARIOS
# =============================================================================

SCENARIOS = [
    # -------------------------------------------------------------------------
    # LEGITIMATE SCENARIOS (Should be LOW risk)
    # -------------------------------------------------------------------------
    {
        "name": "Legitimate Long-term Holder",
        "description": "Old account, low activity, just holding",
        "expected_level": "LOW",
        "wallet_data": {
            "address": "0xLEGIT_HOLDER_123456789",
            "balance": 10.5,
            "chain": "ethereum",
            "tx_count_total": 50,
            "total_received": 12.0,
            "total_sent": 1.5,
            "age_hours": 8760 * 3,  # 3 years old
            "transactions": []
        }
    },
    {
        "name": "Known Exchange (Binance)",
        "description": "High volume but known trusted entity",
        "expected_level": "LOW",
        "wallet_data": {
            "address": "0x28C6c06298d514Db089934071355E5743bf21d60",  # Real Binance
            "balance": 100000.0,
            "chain": "ethereum",
            "tx_count_total": 1000000,
            "total_received": 5000000.0,
            "total_sent": 4900000.0,
            "age_hours": 8760 * 5,  # 5 years
            "transactions": []
        }
    },
    {
        "name": "Stablecoin Contract (USDC)",
        "description": "Token contract, high activity is normal",
        "expected_level": "LOW",
        "wallet_data": {
            "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # Real USDC
            "balance": 0.0,
            "chain": "ethereum",
            "tx_count_total": 100000000,
            "total_received": 500000000000.0,
            "total_sent": 500000000000.0,
            "age_hours": 8760 * 4,
            "transactions": []
        }
    },
    
    # -------------------------------------------------------------------------
    # SUSPICIOUS SCENARIOS (Should be MEDIUM risk)
    # -------------------------------------------------------------------------
    {
        "name": "Pass-through Pattern",
        "description": "100% funds moved out - classic laundering",
        "expected_level": "MEDIUM",
        "wallet_data": {
            "address": "0xPASS_THROUGH_SUSPICIOUS",
            "balance": 0.001,
            "chain": "ethereum",
            "tx_count_total": 500,
            "total_received": 1000.0,
            "total_sent": 999.999,
            "age_hours": 8760,  # 1 year
            "transactions": []
        }
    },
    {
        "name": "High Volume Unknown Wallet",
        "description": "Million+ transactions but not a known entity",
        "expected_level": "MEDIUM",
        "wallet_data": {
            "address": "0xUNKNOWN_HIGH_VOLUME",
            "balance": 50000.0,
            "chain": "ethereum",
            "tx_count_total": 2000000,
            "total_received": 10000000.0,
            "total_sent": 9950000.0,
            "age_hours": 8760 * 2,
            "transactions": []
        }
    },
    
    # -------------------------------------------------------------------------
    # HIGH RISK SCENARIOS (Should be HIGH/CRITICAL)
    # -------------------------------------------------------------------------
    {
        "name": "New Account + High Volume",
        "description": "Brand new account moving large amounts",
        "expected_level": "HIGH",
        "wallet_data": {
            "address": "0xNEW_HIGH_VOLUME_SUSPICIOUS",
            "balance": 0.1,
            "chain": "ethereum",
            "tx_count_total": 500,
            "total_received": 50000.0,
            "total_sent": 49999.9,
            "age_hours": 24,  # Only 1 day old
            "transactions": []
        }
    },
    {
        "name": "Tornado Cash User",
        "description": "Interacted with sanctioned mixer",
        "expected_level": "HIGH",
        "wallet_data": {
            "address": "0xTORNADO_USER_SUSPICIOUS",
            "balance": 5.0,
            "chain": "ethereum",
            "tx_count_total": 20,
            "total_received": 100.0,
            "total_sent": 95.0,
            "age_hours": 720,  # 1 month
            "transactions": [
                {"from": "0xTORNADO_USER_SUSPICIOUS", "to": "0x722122df12d4e14e13ac3b6895a86e84145b6967", "value": 10.0},  # Tornado Cash
            ]
        }
    },
    {
        "name": "Multiple Mixer Interactions",
        "description": "Repeated transactions with mixers",
        "expected_level": "HIGH",
        "wallet_data": {
            "address": "0xMULTIPLE_MIXER_USER",
            "balance": 2.0,
            "chain": "ethereum",
            "tx_count_total": 30,
            "total_received": 200.0,
            "total_sent": 198.0,
            "age_hours": 168,  # 1 week
            "transactions": [
                {"from": "0xMULTIPLE_MIXER_USER", "to": "0x722122df12d4e14e13ac3b6895a86e84145b6967", "value": 10.0},
                {"from": "0xMULTIPLE_MIXER_USER", "to": "0xdd4c48c0b24039969fc16d1cdf626eab821d3384", "value": 20.0},
                {"from": "0xMULTIPLE_MIXER_USER", "to": "0x910cbd523d972eb0a6f4cae4618ad62622b39dbf", "value": 30.0},
            ]
        }
    },
    
    # -------------------------------------------------------------------------
    # CRITICAL RISK SCENARIOS (Should be CRITICAL - BLOCKED)
    # -------------------------------------------------------------------------
    {
        "name": "Sanctioned Address (Tornado Cash)",
        "description": "Address is on OFAC sanctions list",
        "expected_level": "CRITICAL",
        "wallet_data": {
            "address": "0x722122df12d4e14e13ac3b6895a86e84145b6967",  # Real Tornado Cash
            "balance": 1000.0,
            "chain": "ethereum",
            "tx_count_total": 100000,
            "total_received": 5000000.0,
            "total_sent": 4999000.0,
            "age_hours": 8760 * 2,
            "transactions": []
        }
    },
    {
        "name": "Lazarus Group (North Korea)",
        "description": "DPRK state-sponsored hacker group",
        "expected_level": "CRITICAL",
        "wallet_data": {
            "address": "0x098b716b8aaf21512996dc57eb0615e2383e2f96",  # Known Lazarus
            "balance": 5000.0,
            "chain": "ethereum",
            "tx_count_total": 500,
            "total_received": 100000.0,
            "total_sent": 95000.0,
            "age_hours": 8760,
            "transactions": []
        }
    },
    {
        "name": "New + Pass-through + Mixer",
        "description": "Combines ALL red flags",
        "expected_level": "CRITICAL",
        "wallet_data": {
            "address": "0xALL_RED_FLAGS_COMBINED",
            "balance": 0.001,
            "chain": "ethereum",
            "tx_count_total": 100,
            "total_received": 50000.0,
            "total_sent": 49999.999,
            "age_hours": 12,  # 12 hours old
            "transactions": [
                {"from": "0xALL_RED_FLAGS_COMBINED", "to": "0x722122df12d4e14e13ac3b6895a86e84145b6967", "value": 10.0},
                {"from": "0x722122df12d4e14e13ac3b6895a86e84145b6967", "to": "0xALL_RED_FLAGS_COMBINED", "value": 9.9},
                {"from": "0xALL_RED_FLAGS_COMBINED", "to": "0xdd4c48c0b24039969fc16d1cdf626eab821d3384", "value": 20.0},
            ]
        }
    },
]


async def run_comprehensive_test():
    """Run comprehensive scenario test."""
    print("=" * 90)
    print("  CHAINSHIELD COMPREHENSIVE SCENARIO TEST")
    print("  Testing ALL risk factor combinations")
    print("=" * 90)
    print()
    
    engine = get_risk_engine()
    explainer = get_nlp_explainer()
    
    results = []
    
    for scenario in SCENARIOS:
        print("=" * 90)
        print(f"  SCENARIO: {scenario['name']}")
        print(f"  Description: {scenario['description']}")
        print(f"  Expected: {scenario['expected_level']}")
        print("=" * 90)
        print()
        
        wallet_data = scenario["wallet_data"]
        
        try:
            # Run assessment
            assessment = await engine.assess_wallet(wallet_data)
            
            # Check if correct
            expected = scenario["expected_level"]
            actual = assessment.risk_level
            
            # Allow some flexibility
            if expected == "HIGH" and actual in ["HIGH", "CRITICAL"]:
                correct = True
            elif expected == "CRITICAL" and actual in ["HIGH", "CRITICAL"]:
                correct = True
            elif expected == "MEDIUM" and actual in ["MEDIUM", "HIGH"]:
                correct = True
            elif expected == "LOW" and actual in ["LOW", "MEDIUM"]:
                correct = True
            else:
                correct = expected == actual
            
            status = "[PASS]" if correct else "[FAIL]"
            
            # Calculate pass-through
            total_received = wallet_data.get("total_received", 0)
            balance = wallet_data.get("balance", 0)
            pass_through = (1 - balance / total_received) * 100 if total_received > 0 else 0
            
            # Print results
            print("ANALYSIS RESULT:")
            print("-" * 90)
            print(f"  Risk Score:      {assessment.risk_score:.1f}/100")
            print(f"  Risk Level:      {actual} (expected: {expected}) {status}")
            print(f"  Confidence:      {assessment.confidence:.0%}")
            print(f"  Blocked:         {assessment.blocked}")
            print()
            
            print("WALLET METRICS:")
            print("-" * 90)
            print(f"  Address:         {wallet_data['address'][:30]}...")
            print(f"  Balance:         {wallet_data['balance']:,.4f}")
            print(f"  TX Count:        {wallet_data['tx_count_total']:,}")
            print(f"  Total Received:  {wallet_data['total_received']:,.2f}")
            print(f"  Age:             {wallet_data['age_hours']:,} hours ({wallet_data['age_hours']/24:.0f} days)")
            print(f"  Pass-Through:    {pass_through:.1f}%")
            print()
            
            print("LAYER SCORES:")
            print("-" * 90)
            print(f"  Rules:           {assessment.rule_score:.1f}")
            print(f"  Heuristics:      {assessment.heuristic_score:.1f}")
            print(f"  ML:              {assessment.ml_score:.1f}")
            print(f"  Anomaly:         {assessment.anomaly_score:.1f}")
            print()
            
            print("RISK FACTORS DETECTED:")
            print("-" * 90)
            for i, f in enumerate(assessment.risk_factors[:8], 1):
                print(f"  {i}. [{f.source:^15}] {f.description[:60]} (+{f.score_contribution:.1f})")
            print()
            
            # Generate NLP explanation
            risk_factors = [
                {"name": f.name, "description": f.description, "contribution": f.score_contribution, "source": f.source}
                for f in assessment.risk_factors
            ]
            
            summary = explainer.generate_summary(
                risk_score=assessment.risk_score,
                risk_level=assessment.risk_level,
                wallet_data=wallet_data,
                risk_factors=risk_factors
            )
            
            print("NLP EXPLANATION:")
            print("-" * 90)
            print(f"  {summary.summary[:200]}...")
            print()
            print("  KEY FACTORS:")
            for factor in summary.key_factors[:3]:
                print(f"    - {factor}")
            print()
            print(f"  RECOMMENDATION: {summary.recommendation}")
            print()
            
            results.append({
                "name": scenario["name"],
                "expected": expected,
                "actual": actual,
                "score": assessment.risk_score,
                "correct": correct,
                "blocked": assessment.blocked
            })
            
        except Exception as e:
            import traceback
            print(f"ERROR: {str(e)}")
            traceback.print_exc()
            results.append({
                "name": scenario["name"],
                "expected": scenario["expected_level"],
                "actual": "ERROR",
                "correct": False
            })
        
        print()
    
    # Summary
    print("=" * 90)
    print("  TEST SUMMARY")
    print("=" * 90)
    print()
    
    correct = sum(1 for r in results if r.get("correct", False))
    total = len(results)
    
    print(f"  Accuracy: {correct}/{total} ({correct/total*100:.0f}%)")
    print()
    
    print(f"  {'Scenario':<35} {'Expected':>10} {'Actual':>10} {'Score':>8} {'Status':>8}")
    print("  " + "-" * 80)
    
    for r in results:
        status = "PASS" if r.get("correct") else "FAIL"
        score = f"{r.get('score', 0):.1f}" if "score" in r else "N/A"
        blocked = " [BLOCKED]" if r.get("blocked") else ""
        print(f"  {r['name']:<35} {r['expected']:>10} {r['actual']:>10} {score:>8} {status:>8}{blocked}")
    
    print()
    print("=" * 90)
    print("  END OF COMPREHENSIVE TEST")
    print("=" * 90)


if __name__ == "__main__":
    asyncio.run(run_comprehensive_test())
