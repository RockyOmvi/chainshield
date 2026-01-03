"""Test BestChange address."""
import asyncio
from datetime import datetime, timezone
from app.blockchain.bitcoin_client import BitcoinClient
from app.services.risk.features import WalletFeatureExtractor
from app.services.risk.heuristics import HeuristicsAggregator
from app.services.risk.engine import get_risk_engine

ADDRESS = '1BESTCHANGEuX2oUwodgvJqB52kTsrfXS9'

async def test():
    print('='*60)
    print(f'  TESTING: {ADDRESS}')
    print('='*60)
    
    btc = BitcoinClient(timeout=30)
    activity = await btc.get_address_activity(ADDRESS)
    await btc.close()
    
    print()
    print('BLOCKCHAIN DATA:')
    balance = activity.get("balance_native", 0)
    tx_count = activity.get("transaction_count", 0)
    total_received = activity.get("total_received", 0)
    total_sent = activity.get("total_sent", 0)
    
    print(f'  Balance:        {balance:.8f} BTC')
    print(f'  TX Count:       {tx_count:,}')
    print(f'  Total Received: {total_received:,.4f} BTC')
    print(f'  Total Sent:     {total_sent:,.4f} BTC')
    
    # BestChange address was created around 2018
    # Note: Blockchain API doesn't return first_seen, so we estimate
    first_seen = datetime(2018, 1, 1, tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - first_seen
    age_hours = age.total_seconds() / 3600
    age_days = age.days
    
    print(f'  First Seen:     ~{first_seen.strftime("%Y-%m-%d")} (estimated)')
    print(f'  Account Age:    {age_days:,} days')
    
    wallet_data = {
        'address': ADDRESS,
        'balance': balance,
        'chain': 'bitcoin',
        'tx_count_total': tx_count,
        'total_received': total_received,
        'total_sent': total_sent,
        'first_seen': first_seen.isoformat(),  # Already has timezone
        'age_hours': age_hours,  # Now properly set!
        'transactions': []
    }
    
    # Calculate pass-through
    if total_received > 0:
        retention = balance / total_received * 100
        print(f'  RETENTION:      {retention:.4f}%')
        print(f'  PASS-THROUGH:   {100-retention:.2f}%')
    
    # Run full risk engine
    engine = get_risk_engine()
    assessment = await engine.assess_wallet(wallet_data)
    
    print()
    print('RISK ASSESSMENT:')
    print(f'  Risk Score:     {assessment.risk_score:.1f}/100')
    print(f'  Risk Level:     {assessment.risk_level.upper()}')
    print(f'  ML Score:       {assessment.ml_score:.1f}')
    print(f'  Confidence:     {assessment.confidence:.0%}')
    
    # Show risk factors
    if assessment.risk_factors:
        print()
        print('RISK FACTORS:')
        for rf in assessment.risk_factors[:5]:
            print(f'  - {rf.name}: {rf.description}')
    
    # Generate NLP Explainer Report
    print()
    print('='*60)
    print('  HUMAN-READABLE EXPLANATION')
    print('='*60)
    
    from app.services.risk.ml.nlp_explainer import get_nlp_explainer
    
    explainer = get_nlp_explainer()
    
    # Convert risk factors to dicts
    risk_factor_dicts = []
    if assessment.risk_factors:
        for rf in assessment.risk_factors:
            risk_factor_dicts.append({
                "name": rf.name,
                "description": rf.description,
                "score_contribution": rf.score_contribution,
                "source": rf.source,
            })
    
    # Generate comprehensive report
    report = explainer.explain_for_analyst(
        risk_score=assessment.risk_score,
        risk_level=assessment.risk_level,
        wallet_data=wallet_data,
        shap_values=None,
        risk_factors=risk_factor_dicts
    )
    
    print(report)
    
    print()
    print('='*60)

asyncio.run(test())
