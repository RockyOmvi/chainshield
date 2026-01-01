"""Final live wallet test with fixed RPC client."""
import asyncio

async def main():
    from app.blockchain.rpc_client import BlockchainRPCClient
    
    address = "0x4838B106FCe9647Bdf1E7877BF73cE8B0BAD5f97"
    rpc = BlockchainRPCClient("https://eth.llamarpc.com", timeout=30)
    
    try:
        activity = await rpc.get_address_activity(address)
        balance = activity["balance_eth"]
        tx_count = activity["transaction_count"]
        is_contract = activity["is_contract"]
        
        print("TITAN BUILDER WALLET - LIVE RPC DATA:")
        print("="*50)
        print(f"  Balance:     {balance:.6f} ETH")
        print(f"  TX Count:    {tx_count:,}")
        print(f"  Is Contract: {is_contract}")
        print("="*50)
        
        # Run risk assessment
        from app.services.risk.engine import get_risk_engine
        
        engine = get_risk_engine()
        result = await engine.assess_wallet({
            "address": address,
            "balance": balance,
            "first_seen": "2022-07-01T00:00:00Z",
            "transactions": []
        })
        
        print("\nRISK ASSESSMENT:")
        print("="*50)
        print(f"  Score:   {result.risk_score:.1f}/100")
        print(f"  Level:   {result.risk_level}")
        print(f"  Blocked: {result.blocked}")
        print("="*50)
        
    finally:
        await rpc.close()

if __name__ == "__main__":
    asyncio.run(main())
