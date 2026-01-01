"""
ChainShield Solana Client

Uses Solana's native JSON-RPC API for blockchain data.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger()


@dataclass
class SolanaAccountInfo:
    """Solana account information."""
    address: str
    balance_lamports: int
    is_executable: bool  # Is it a program?
    owner: str
    rent_epoch: int
    
    @property
    def balance_sol(self) -> float:
        """Get balance in SOL."""
        return self.balance_lamports / 1_000_000_000


class SolanaClient:
    """
    Solana blockchain client using native JSON-RPC.
    
    API Docs: https://solana.com/docs/rpc
    """
    
    # Public RPC endpoints
    MAINNET_URLS = [
        "https://api.mainnet-beta.solana.com",
        "https://solana-mainnet.g.alchemy.com/v2/demo",  # Alchemy demo
    ]
    
    DEVNET_URL = "https://api.devnet.solana.com"
    
    def __init__(self, rpc_url: str = None, timeout: float = 15.0):
        """Initialize Solana client."""
        self.logger = logger.bind(module="solana_client")
        self.rpc_url = rpc_url or self.MAINNET_URLS[0]
        self.timeout = timeout
        self._client = None
        self._request_id = 0
    
    async def _get_client(self):
        """Get or create httpx client."""
        if self._client is None:
            try:
                import httpx
                self._client = httpx.AsyncClient(timeout=self.timeout)
            except ImportError:
                raise ImportError("httpx required: pip install httpx")
        return self._client
    
    async def close(self):
        """Close the client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _next_id(self) -> int:
        """Get next request ID."""
        self._request_id += 1
        return self._request_id
    
    async def _call(self, method: str, params: List = None) -> Optional[Any]:
        """Make a JSON-RPC call."""
        client = await self._get_client()
        
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params or []
        }
        
        try:
            response = await client.post(self.rpc_url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            if "error" in data:
                self.logger.warning("solana_rpc_error", error=data["error"])
                return None
            
            return data.get("result")
            
        except Exception as e:
            self.logger.warning("solana_rpc_failed", method=method, error=str(e))
            return None
    
    async def get_balance(self, address: str) -> Optional[int]:
        """
        Get SOL balance in lamports.
        
        Args:
            address: Solana address (base58)
            
        Returns:
            Balance in lamports or None
        """
        result = await self._call("getBalance", [address])
        if result and "value" in result:
            return result["value"]
        return None
    
    async def get_account_info(self, address: str) -> Optional[SolanaAccountInfo]:
        """Get detailed account information."""
        result = await self._call("getAccountInfo", [
            address,
            {"encoding": "base58"}
        ])
        
        if result and result.get("value"):
            value = result["value"]
            return SolanaAccountInfo(
                address=address,
                balance_lamports=value.get("lamports", 0),
                is_executable=value.get("executable", False),
                owner=value.get("owner", ""),
                rent_epoch=value.get("rentEpoch", 0)
            )
        
        # Account might not exist or have 0 balance
        balance = await self.get_balance(address)
        return SolanaAccountInfo(
            address=address,
            balance_lamports=balance or 0,
            is_executable=False,
            owner="",
            rent_epoch=0
        )
    
    async def get_transaction_count(self, address: str) -> int:
        """
        Get transaction count (signatures).
        
        Note: Solana RPC limits to 1000 signatures by default.
        """
        result = await self._call("getSignaturesForAddress", [
            address,
            {"limit": 1000}
        ])
        
        if result:
            return len(result)
        return 0
    
    async def get_address_activity(self, address: str) -> Dict[str, Any]:
        """
        Get address activity in standard format.
        
        Compatible with EVM client interface.
        """
        account = await self.get_account_info(address)
        tx_count = await self.get_transaction_count(address)
        
        if account:
            return {
                "chain": "solana",
                "address": address,
                "balance_native": account.balance_sol,
                "balance_lamports": account.balance_lamports,
                "transaction_count": tx_count,
                "is_program": account.is_executable,
                "is_contract": account.is_executable,  # Compatibility
                "owner": account.owner,
                "has_activity": tx_count > 0,
            }
        
        return {
            "chain": "solana",
            "address": address,
            "balance_native": 0.0,
            "transaction_count": 0,
            "has_activity": False,
            "error": "Failed to fetch"
        }
    
    async def get_recent_transactions(self, address: str, limit: int = 10) -> list:
        """Get recent transaction signatures."""
        result = await self._call("getSignaturesForAddress", [
            address,
            {"limit": limit}
        ])
        return result or []
    
    async def get_token_accounts(self, address: str) -> list:
        """Get SPL token accounts owned by address."""
        result = await self._call("getTokenAccountsByOwner", [
            address,
            {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
            {"encoding": "jsonParsed"}
        ])
        
        if result and "value" in result:
            return result["value"]
        return []
    
    async def get_slot(self) -> Optional[int]:
        """Get current slot number."""
        return await self._call("getSlot")
    
    async def health_check(self) -> bool:
        """Check if RPC is healthy."""
        try:
            slot = await self.get_slot()
            return slot is not None and slot > 0
        except Exception:
            return False


# Factory
def create_solana_client(rpc_url: str = None) -> SolanaClient:
    """Create a Solana client."""
    return SolanaClient(rpc_url=rpc_url)
