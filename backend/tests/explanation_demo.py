"""
ChainShield Full Explanation Demo
Shows the complete NLP explanation for each address - the real value of the system
"""
import asyncio
from datetime import datetime

from app.blockchain.universal_client import create_universal_client
from app.services.risk.engine import get_risk_engine
from app.services.risk.ml.nlp_explainer import get_nlp_explainer


# Test a mix of known and unknown addresses
TEST_ADDRESSES = [
    # Known trusted entity
    {"chain": "ethereum", "address": "0x28C6c06298d514Db089934071355E5743bf21d60", "label": "Binance Hot Wallet"},
    
    # Stablecoin
    {"chain": "ethereum", "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "label": "USDC Contract"},
    
    # Unknown pass-through (aggregator)
    {"chain": "bitcoin", "address": "1BESTCHANGEuX2oUwodgvJqB52kTsrfXS9", "label": "BestChange (Aggregator)"},
    
    # Gambling
    {"chain": "bitcoin", "address": "1dice8EMZmqKvrGE4Qc9bUFf9PX3xaYDp", "label": "SatoshiDice Gambling"},
]


async def run_explanation_demo():
    """Generate full explanations for each address."""
    print("=" * 80)
    print("  CHAINSHIELD FULL EXPLANATION DEMO")
    print("  Showing complete NLP explanations for risk decisions")
    print("=" * 80)
    print()
    
    client = create_universal_client(timeout=30)
    engine = get_risk_engine()
    explainer = get_nlp_explainer()
    
    for addr_info in TEST_ADDRESSES:
        print("=" * 80)
        print(f"  ADDRESS: {addr_info['label']}")
        print(f"  Chain: {addr_info['chain'].upper()}")
        print(f"  Address: {addr_info['address'][:30]}...")
        print("=" * 80)
        print()
        
        try:
            # Fetch data
            activity = await client.get_address_activity(addr_info["address"], addr_info["chain"])
            
            balance = activity.balance_native if hasattr(activity, 'balance_native') else 0
            tx_count = activity.transaction_count if hasattr(activity, 'transaction_count') else 0
            
            total_received = balance * 2
            if hasattr(activity, 'extra') and activity.extra:
                total_received = activity.extra.get('total_received', balance * 2)
            
            # Build wallet data
            wallet_data = {
                'address': addr_info["address"],
                'balance': balance,
                'chain': addr_info["chain"],
                'tx_count_total': tx_count,
                'total_received': total_received,
                'total_sent': total_received - balance,
                'age_hours': 50000,
                'transactions': []
            }
            
            # Run risk assessment
            assessment = await engine.assess_wallet(wallet_data)
            
            # Convert risk factors to dict format
            risk_factors = [
                {
                    "name": f.name,
                    "description": f.description,
                    "contribution": f.score_contribution,
                    "source": f.source
                }
                for f in assessment.risk_factors
            ]
            
            # Generate NLP explanation (matching the actual API signature)
            summary = explainer.generate_summary(
                risk_score=assessment.risk_score,
                risk_level=assessment.risk_level,
                wallet_data=wallet_data,
                risk_factors=risk_factors
            )
            
            # Generate analyst report
            analyst_report = explainer.explain_for_analyst(
                risk_score=assessment.risk_score,
                risk_level=assessment.risk_level,
                wallet_data=wallet_data,
                shap_values=None,  # Would require trained model
                risk_factors=risk_factors
            )
            
            # Print results
            print("RISK ANALYSIS:")
            print("-" * 80)
            print(f"  Risk Score:    {assessment.risk_score:.1f}/100")
            print(f"  Risk Level:    {assessment.risk_level}")
            print(f"  Confidence:    {assessment.confidence:.0%}")
            print()
            
            print("LAYER BREAKDOWN:")
            print("-" * 80)
            print(f"  Rules:         {assessment.rule_score:.1f}")
            print(f"  Heuristics:    {assessment.heuristic_score:.1f}")
            print(f"  ML:            {assessment.ml_score:.1f}")
            print(f"  Anomaly:       {assessment.anomaly_score:.1f}")
            print()
            
            print("RISK FACTORS DETECTED:")
            print("-" * 80)
            for f in assessment.risk_factors[:5]:
                print(f"  [{f.source:^15}] {f.description} (+{f.score_contribution:.1f})")
            print()
            
            print("NLP SUMMARY:")
            print("-" * 80)
            print(summary.summary)
            print()
            print("KEY FACTORS:")
            for factor in summary.key_factors[:5]:
                print(f"  - {factor}")
            print()
            print(f"RECOMMENDATION: {summary.recommendation}")
            print()
            
            print("FULL ANALYST REPORT:")
            print("-" * 80)
            print(analyst_report)
            print()
            
        except Exception as e:
            import traceback
            print(f"ERROR: {str(e)}")
            traceback.print_exc()
            print()
    
    await client.close_all()
    print("=" * 80)
    print("  END OF DEMO")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_explanation_demo())
