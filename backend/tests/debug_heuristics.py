"""Debug heuristics detection."""
import asyncio
from app.blockchain.bitcoin_client import BitcoinClient
from app.services.risk.features import WalletFeatureExtractor
from app.services.risk.heuristics import HeuristicsAggregator

ADDRESS = '1F1tAaz5x1HUXrCNLbtMDqcw6o5GNn4xqX'

async def test():
    btc = BitcoinClient(timeout=30)
    activity = await btc.get_address_activity(ADDRESS)
    await btc.close()
    
    wallet_data = {
        'address': ADDRESS,
        'balance': activity.get('balance_native', 0),
        'chain': 'bitcoin',
        'tx_count_total': activity.get('transaction_count', 0),
        'total_received': activity.get('total_received', 0),
        'total_sent': activity.get('total_sent', 0),
        'first_seen': '2014-03-01T00:00:00Z',
        'transactions': []
    }
    
    extractor = WalletFeatureExtractor()
    features = extractor.extract(wallet_data)
    
    print('VOLUME FEATURES:')
    print(f"  total_received_eth: {features.features.get('total_received_eth', 0):,.2f}")
    print(f"  total_sent_eth:     {features.features.get('total_sent_eth', 0):,.2f}")
    print(f"  balance_eth:        {features.features.get('balance_eth', 0):.4f}")
    
    # Calculate retention ratio
    total_received = features.features.get('total_received_eth', 0)
    balance = features.features.get('balance_eth', 0)
    if total_received > 0:
        retention = balance / total_received
        print(f"  RETENTION RATIO:    {retention:.6%}")
        print(f"  PASS-THROUGH:       {100 - retention*100:.2f}%")
    
    heuristics = HeuristicsAggregator()
    result = heuristics.evaluate_all(features.features)
    
    print()
    print('HEURISTIC RESULT:')
    print(f"  Score: {result['combined_score']}")
    print(f"  Factors detected:")
    for f in result.get('factors', []):
        print(f"    - {f}")
    
    print()
    print('INDIVIDUAL HEURISTICS:')
    for r in result['results']:
        print(f"  {r['name']}: {r['score']} (conf: {r['confidence']})")
        for f in r.get('factors', []):
            print(f"    -> {f}")

asyncio.run(test())
