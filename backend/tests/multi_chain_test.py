"""
ChainShield Multi-Chain Test

Tests the same wallet address on multiple EVM-compatible mainnets.
"""

import asyncio
import time


# Free public RPC endpoints for major chains
CHAINS = {
    "Ethereum": "https://eth.llamarpc.com",
    "Polygon": "https://polygon-rpc.com",
    "BNB Chain": "https://bsc-dataseed.binance.org",
    "Arbitrum": "https://arb1.arbitrum.io/rpc",
    "Optimism": "https://mainnet.optimism.io",
    "Avalanche": "https://api.avax.network/ext/bc/C/rpc",
    "Fantom": "https://rpc.ftm.tools",
    "Base": "https://mainnet.base.org",
}


async def test_chain(chain_name: str, rpc_url: str, address: str):
    """Test a wallet on a specific chain."""
    from app.blockchain.rpc_client import BlockchainRPCClient
    
    rpc = BlockchainRPCClient(rpc_url, timeout=15)
    
    try:
        start = time.time()
        activity = await rpc.get_address_activity(address)
        elapsed = (time.time() - start) * 1000
        
        balance = activity["balance_eth"]
        tx_count = activity["transaction_count"]
        
        return {
            "chain": chain_name,
            "balance": balance,
            "tx_count": tx_count,
            "time_ms": elapsed,
            "status": "OK"
        }
    except Exception as e:
        return {
            "chain": chain_name,
            "error": str(e)[:30],
            "status": "ERROR"
        }
    finally:
        await rpc.close()


async def multi_chain_test():
    # Test address (works on all EVM chains - same address format)
    address = "0x4838B106FCe9647Bdf1E7877BF73cE8B0BAD5f97"
    
    print("="*70)
    print("  CHAINSHIELD MULTI-CHAIN TEST")
    print(f"  Address: {address}")
    print("="*70)
    print()
    print(f"  {'Chain':<15} {'Balance':>15} {'TX Count':>12} {'Time':>10} {'Status':>10}")
    print("  " + "-"*62)
    
    results = []
    for chain_name, rpc_url in CHAINS.items():
        result = await test_chain(chain_name, rpc_url, address)
        results.append(result)
        
        if result["status"] == "OK":
            bal = result["balance"]
            tx = result["tx_count"]
            time_ms = result["time_ms"]
            print(f"  {chain_name:<15} {bal:>15.6f} {tx:>12,} {time_ms:>8.0f}ms {'OK':>10}")
        else:
            print(f"  {chain_name:<15} {'--':>15} {'--':>12} {'--':>10} {'ERROR':>10}")
        
        await asyncio.sleep(0.5)  # Rate limit
    
    # Summary
    success = sum(1 for r in results if r["status"] == "OK")
    
    print()
    print("="*70)
    print(f"  RESULT: {success}/{len(CHAINS)} chains tested successfully")
    print("="*70)
    
    # Run risk assessment on chains with activity
    print("\n  RISK ASSESSMENTS:")
    print("  " + "-"*40)
    
    from app.services.risk.engine import get_risk_engine
    engine = get_risk_engine()
    
    for r in results:
        if r["status"] == "OK" and r["tx_count"] > 0:
            wallet_data = {
                "address": address,
                "balance": r["balance"],
                "first_seen": "2022-01-01T00:00:00Z",
                "transactions": []
            }
            
            assessment = await engine.assess_wallet(wallet_data)
            print(f"  {r['chain']:<15} Score: {assessment.risk_score:>5.1f}/100  Level: {assessment.risk_level}")
    
    print("="*70)


if __name__ == "__main__":
    asyncio.run(multi_chain_test())
