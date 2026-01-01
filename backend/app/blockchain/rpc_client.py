"""
ChainShield Real Blockchain RPC Client

Production-grade blockchain RPC client using httpx.
Supports Ethereum JSON-RPC API for real blockchain data.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger()


@dataclass
class RPCResponse:
    """Response from an RPC call."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class BlockchainRPCClient:
    """
    Real blockchain RPC client.
    
    Makes actual JSON-RPC calls to blockchain nodes.
    Supports Ethereum and EVM-compatible chains.
    """
    
    def __init__(self, rpc_url: str, timeout: float = 10.0):
        """
        Initialize RPC client.
        
        Args:
            rpc_url: RPC endpoint URL
            timeout: Request timeout in seconds
        """
        self.logger = logger.bind(module="rpc_client")
        self.rpc_url = rpc_url
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
                self.logger.error("httpx_not_installed")
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
    
    async def _call(self, method: str, params: List = None) -> RPCResponse:
        """
        Make a JSON-RPC call.
        
        Args:
            method: RPC method name
            params: Method parameters
            
        Returns:
            RPCResponse with result or error
        """
        client = await self._get_client()
        
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or [],
            "id": self._next_id(),
        }
        
        try:
            response = await client.post(self.rpc_url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            if "error" in data:
                return RPCResponse(
                    success=False,
                    error=data["error"].get("message", "Unknown error")
                )
            
            return RPCResponse(success=True, data=data.get("result"))
            
        except Exception as e:
            self.logger.warning("rpc_call_failed", method=method, error=str(e))
            return RPCResponse(success=False, error=str(e))
    
    async def get_balance(self, address: str) -> Optional[float]:
        """
        Get ETH balance of an address.
        
        Args:
            address: Wallet address
            
        Returns:
            Balance in ETH or None on error
        """
        response = await self._call("eth_getBalance", [address, "latest"])
        
        if response.success and response.data:
            # Convert hex wei to ETH
            wei = int(response.data, 16)
            return wei / 1e18
        
        return None
    
    async def get_transaction_count(self, address: str) -> Optional[int]:
        """
        Get transaction count (nonce) for an address.
        
        Args:
            address: Wallet address
            
        Returns:
            Transaction count or None on error
        """
        response = await self._call("eth_getTransactionCount", [address, "latest"])
        
        if response.success and response.data:
            return int(response.data, 16)
        
        return None
    
    async def get_block_number(self) -> Optional[int]:
        """Get current block number."""
        response = await self._call("eth_blockNumber", [])
        
        if response.success and response.data:
            return int(response.data, 16)
        
        return None
    
    async def get_transaction(self, tx_hash: str) -> Optional[Dict]:
        """Get transaction by hash."""
        response = await self._call("eth_getTransactionByHash", [tx_hash])
        return response.data if response.success else None
    
    async def get_address_activity(self, address: str) -> Dict[str, Any]:
        """
        Get comprehensive activity for an address.
        
        Returns:
            Dict with balance, tx_count, and activity status
        """
        balance = await self.get_balance(address)
        tx_count = await self.get_transaction_count(address)
        
        return {
            "address": address,
            "balance": balance or 0.0,
            "tx_count": tx_count or 0,
            "has_activity": (tx_count or 0) > 0,
        }
    
    async def is_contract(self, address: str) -> bool:
        """Check if address is a contract."""
        response = await self._call("eth_getCode", [address, "latest"])
        
        if response.success and response.data:
            # Contracts have code, EOAs return "0x"
            return response.data != "0x" and len(response.data) > 2
        
        return False
    
    async def health_check(self) -> bool:
        """Check if RPC endpoint is healthy."""
        try:
            block = await self.get_block_number()
            return block is not None and block > 0
        except Exception:
            return False


# Factory function
def create_rpc_client(rpc_url: str, timeout: float = 10.0) -> BlockchainRPCClient:
    """Create a new RPC client."""
    return BlockchainRPCClient(rpc_url, timeout)
