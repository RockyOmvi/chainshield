"""
Live Ethereum Wallet Test - Multiple Famous Wallets

Tests real wallets with transaction history.
"""

import asyncio
import time


async def test_wallet(address: str, name: str):
    """Test a single wallet."""
    print(f"\n{'='*60}")
    print(f"  Testing: {name}")
    print(f"  Address: {address}")
    print("="*60)
    
    from app.blockchain.rpc_client import BlockchainRPCClient
    from app.services.risk.engine import get_risk_engine
    
    rpc = BlockchainRPCClient("https://eth.llamarpc.com", timeout=30)
    
    try:
        # Fetch data
        start = time.time()
        activity = await rpc.get_address_activity(address)
        fetch_time = (time.time() - start) * 1000
        
        balance = activity.get("balance_eth", 0)
        tx_count = activity.get("transaction_count", 0)
        is_contract = activity.get("is_contract", False)
        
        print(f"   Balance:     {balance:.4f} ETH")
        print(f"   TX Count:    {tx_count}")
        print(f"   Is Contract: {is_contract}")
        
        # Assess
        wallet_data = {
            "address": address,
            "balance": balance,
            "first_seen": "2020-01-01T00:00:00Z",
            "transactions": []
        }
        
        engine = get_risk_engine()
        result = await engine.assess_wallet(wallet_data)
        
        print(f"\n   RESULT:")
        print(f"   Risk Score: {result.risk_score:.1f}/100")
        print(f"   Risk Level: {result.risk_level}")
        print(f"   Blocked:    {result.blocked}")
        
        return {
            "name": name,
            "balance": balance,
            "tx_count": tx_count,
            "score": result.risk_score,
            "level": result.risk_level,
        }
        
    except Exception as e:
        print(f"   Error: {e}")
        return {"name": name, "error": str(e)}
    finally:
        await rpc.close()


async def main():
    print("\n" + "="*60)
    print("  CHAINSHIELD - LIVE MULTI-WALLET TEST")
    print("  Testing Famous Ethereum Wallets with REAL RPC")
    print("="*60)
    
    wallets = [
        # Vitalik Buterin - huge balance, many transactions
        ("0xd8da6bf26964af9d7eed9e03e53415d37aa96045", "Vitalik Buterin"),
        
        # Uniswap V2 Router - contract with massive activity
        ("0x7a250d5630b4cf539739df2c5dacb4c659f2488d", "Uniswap V2 Router"),
        
        # Binance Hot Wallet - exchange wallet
        ("0x28C6c06298d514Db089934071355E5743bf21d60", "Binance Hot Wallet"),
    ]
    
    results = []
    for address, name in wallets:
        result = await test_wallet(address, name)
        results.append(result)
        await asyncio.sleep(1)  # Rate limit
    
    # Summary
    print("\n" + "="*60)
    print("  SUMMARY")
    print("="*60)
    print(f"  {'Wallet':<25} {'Balance':>12} {'TX Count':>10} {'Score':>8} {'Level':>10}")
    print("  " + "-"*55)
    
    for r in results:
        if "error" in r:
            print(f"  {r['name']:<25} ERROR")
        else:
            print(f"  {r['name']:<25} {r['balance']:>12.4f} {r['tx_count']:>10} {r['score']:>8.1f} {r['level']:>10}")
    
    print("\n  LIVE WALLET TESTS COMPLETE!")


if __name__ == "__main__":
    asyncio.run(main())
