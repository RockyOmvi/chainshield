"""
ChainShield Bitcoin Client

Uses Blockstream's free API for Bitcoin blockchain data.
No API key required.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional
import structlog

logger = structlog.get_logger()


@dataclass
class BitcoinAddressInfo:
    """Bitcoin address information."""
    address: str
    funded_txo_count: int
    spent_txo_count: int
    funded_txo_sum: int  # satoshis
    spent_txo_sum: int   # satoshis
    
    @property
    def balance_btc(self) -> float:
        """Get balance in BTC."""
        return (self.funded_txo_sum - self.spent_txo_sum) / 100_000_000
    
    @property
    def total_received_btc(self) -> float:
        """Get total received in BTC."""
        return self.funded_txo_sum / 100_000_000
    
    @property
    def total_sent_btc(self) -> float:
        """Get total sent in BTC."""
        return self.spent_txo_sum / 100_000_000
    
    @property
    def transaction_count(self) -> int:
        """Get total transaction count."""
        return self.funded_txo_count + self.spent_txo_count


class BitcoinClient:
    """
    Bitcoin blockchain client using Blockstream API.
    
    API Docs: https://github.com/Blockstream/esplora/blob/master/API.md
    No API key required.
    """
    
    # Blockstream API endpoints
    MAINNET_URL = "https://blockstream.info/api"
    TESTNET_URL = "https://blockstream.info/testnet/api"
    
    def __init__(self, testnet: bool = False, timeout: float = 15.0):
        """Initialize Bitcoin client."""
        self.logger = logger.bind(module="bitcoin_client")
        self.base_url = self.TESTNET_URL if testnet else self.MAINNET_URL
        self.timeout = timeout
        self._client = None
    
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
    
    async def get_address_info(self, address: str) -> Optional[BitcoinAddressInfo]:
        """
        Get Bitcoin address information.
        
        Args:
            address: Bitcoin address (1..., 3..., bc1...)
            
        Returns:
            BitcoinAddressInfo or None on error
        """
        client = await self._get_client()
        
        try:
            response = await client.get(f"{self.base_url}/address/{address}")
            response.raise_for_status()
            data = response.json()
            
            chain_stats = data.get("chain_stats", {})
            mempool_stats = data.get("mempool_stats", {})
            
            return BitcoinAddressInfo(
                address=address,
                funded_txo_count=chain_stats.get("funded_txo_count", 0) + mempool_stats.get("funded_txo_count", 0),
                spent_txo_count=chain_stats.get("spent_txo_count", 0) + mempool_stats.get("spent_txo_count", 0),
                funded_txo_sum=chain_stats.get("funded_txo_sum", 0) + mempool_stats.get("funded_txo_sum", 0),
                spent_txo_sum=chain_stats.get("spent_txo_sum", 0) + mempool_stats.get("spent_txo_sum", 0),
            )
            
        except Exception as e:
            self.logger.warning("bitcoin_address_fetch_failed", address=address[:10], error=str(e))
            return None
    
    async def get_address_activity(self, address: str) -> Dict[str, Any]:
        """
        Get address activity in standard format.
        
        Compatible with EVM client interface.
        """
        info = await self.get_address_info(address)
        
        if info:
            return {
                "chain": "bitcoin",
                "address": address,
                "balance_native": info.balance_btc,
                "balance_usd": None,  # Would need price API
                "transaction_count": info.transaction_count,
                "total_received": info.total_received_btc,
                "total_sent": info.total_sent_btc,
                "is_contract": False,  # Bitcoin doesn't have contracts
                "has_activity": info.transaction_count > 0,
            }
        
        return {
            "chain": "bitcoin",
            "address": address,
            "balance_native": 0.0,
            "transaction_count": 0,
            "has_activity": False,
            "error": "Failed to fetch"
        }
    
    async def get_transactions(self, address: str, limit: int = 25) -> list:
        """Get recent transactions for an address."""
        client = await self._get_client()
        
        try:
            response = await client.get(f"{self.base_url}/address/{address}/txs")
            response.raise_for_status()
            txs = response.json()
            return txs[:limit]
        except Exception as e:
            self.logger.warning("bitcoin_txs_fetch_failed", error=str(e))
            return []
    
    async def get_utxos(self, address: str) -> list:
        """Get unspent transaction outputs for an address."""
        client = await self._get_client()
        
        try:
            response = await client.get(f"{self.base_url}/address/{address}/utxo")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.warning("bitcoin_utxo_fetch_failed", error=str(e))
            return []
    
    async def health_check(self) -> bool:
        """Check if API is healthy."""
        client = await self._get_client()
        
        try:
            response = await client.get(f"{self.base_url}/blocks/tip/height")
            return response.status_code == 200
        except Exception:
            return False


# Factory
def create_bitcoin_client(testnet: bool = False) -> BitcoinClient:
    """Create a Bitcoin client."""
    return BitcoinClient(testnet=testnet)
