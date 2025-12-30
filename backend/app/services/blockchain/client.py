"""
ChainShield Blockchain Provider Client

Multi-provider Ethereum client with:
- Alchemy as primary provider
- Infura as secondary
- Public RPC as fallback
- Automatic failover
- Retry with exponential backoff
- Response caching
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.utils.retry import CircuitBreaker
from app.utils.cache import cached

logger = get_logger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class WalletBalance:
    """Wallet balance information."""
    address: str
    chain: str
    balance_wei: int
    balance_eth: Decimal
    balance_usd: Optional[Decimal] = None
    fetched_at: datetime = None
    
    def __post_init__(self):
        if self.fetched_at is None:
            self.fetched_at = datetime.utcnow()


@dataclass
class TokenBalance:
    """ERC-20 token balance."""
    contract_address: str
    symbol: str
    name: str
    decimals: int
    balance: Decimal
    balance_usd: Optional[Decimal] = None


@dataclass
class TransactionData:
    """Normalized transaction data."""
    tx_hash: str
    chain: str
    block_number: int
    timestamp: datetime
    from_address: str
    to_address: Optional[str]
    value_wei: int
    value_eth: Decimal
    gas_used: int
    gas_price: int
    is_success: bool
    input_data: str
    method_id: Optional[str] = None
    
    @property
    def gas_cost_eth(self) -> Decimal:
        return Decimal(self.gas_used * self.gas_price) / Decimal(10**18)


@dataclass
class TransactionReceipt:
    """Transaction receipt with logs."""
    tx_hash: str
    status: bool
    block_number: int
    gas_used: int
    logs: List[Dict[str, Any]]
    contract_address: Optional[str] = None


# =============================================================================
# Provider Interface
# =============================================================================

class BlockchainProvider(ABC):
    """Abstract base class for blockchain providers."""
    
    def __init__(self, name: str, base_url: str, api_key: Optional[str] = None):
        self.name = name
        self.base_url = base_url
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=settings.circuit_breaker_failure_threshold,
            recovery_timeout=settings.circuit_breaker_recovery_timeout,
        )
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=settings.blockchain_timeout,
                headers={"Content-Type": "application/json"}
            )
        return self._client
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    @abstractmethod
    async def get_balance(self, address: str) -> int:
        """Get wallet balance in wei."""
        pass
    
    @abstractmethod
    async def get_transaction(self, tx_hash: str) -> Dict[str, Any]:
        """Get transaction details."""
        pass
    
    @abstractmethod
    async def get_transaction_receipt(self, tx_hash: str) -> Dict[str, Any]:
        """Get transaction receipt."""
        pass
    
    @abstractmethod
    async def get_block_number(self) -> int:
        """Get latest block number."""
        pass
    
    async def _json_rpc_call(
        self,
        method: str,
        params: List[Any],
        request_id: int = 1
    ) -> Any:
        """Make a JSON-RPC call to the provider."""
        client = await self._get_client()
        
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id
        }
        
        try:
            response = await client.post(self.base_url, json=payload)
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                error = result["error"]
                logger.error(
                    "rpc_error",
                    provider=self.name,
                    method=method,
                    error=error
                )
                raise Exception(f"RPC Error: {error.get('message', 'Unknown error')}")
            
            return result.get("result")
            
        except httpx.HTTPError as e:
            logger.error(
                "rpc_http_error",
                provider=self.name,
                method=method,
                error=str(e)
            )
            raise


# =============================================================================
# Ethereum JSON-RPC Provider
# =============================================================================

class EthereumProvider(BlockchainProvider):
    """Standard Ethereum JSON-RPC provider."""
    
    async def get_balance(self, address: str) -> int:
        """Get wallet balance in wei."""
        result = await self._json_rpc_call(
            "eth_getBalance",
            [address, "latest"]
        )
        return int(result, 16) if result else 0
    
    async def get_transaction(self, tx_hash: str) -> Dict[str, Any]:
        """Get transaction details."""
        return await self._json_rpc_call(
            "eth_getTransactionByHash",
            [tx_hash]
        )
    
    async def get_transaction_receipt(self, tx_hash: str) -> Dict[str, Any]:
        """Get transaction receipt."""
        return await self._json_rpc_call(
            "eth_getTransactionReceipt",
            [tx_hash]
        )
    
    async def get_block_number(self) -> int:
        """Get latest block number."""
        result = await self._json_rpc_call("eth_blockNumber", [])
        return int(result, 16) if result else 0
    
    async def get_block(self, block_number: Union[int, str], full_tx: bool = False) -> Dict[str, Any]:
        """Get block by number."""
        if isinstance(block_number, int):
            block_param = hex(block_number)
        else:
            block_param = block_number  # "latest", "pending", etc.
        
        return await self._json_rpc_call(
            "eth_getBlockByNumber",
            [block_param, full_tx]
        )
    
    async def get_transaction_count(self, address: str) -> int:
        """Get transaction count (nonce) for address."""
        result = await self._json_rpc_call(
            "eth_getTransactionCount",
            [address, "latest"]
        )
        return int(result, 16) if result else 0
    
    async def get_code(self, address: str) -> str:
        """Get contract code at address."""
        return await self._json_rpc_call(
            "eth_getCode",
            [address, "latest"]
        )
    
    async def call(self, tx: Dict[str, Any], block: str = "latest") -> str:
        """Execute a read-only contract call."""
        return await self._json_rpc_call(
            "eth_call",
            [tx, block]
        )


# =============================================================================
# Provider Factory
# =============================================================================

def create_alchemy_provider() -> Optional[EthereumProvider]:
    """Create Alchemy provider if API key is configured."""
    if not settings.alchemy_api_key:
        return None
    
    return EthereumProvider(
        name="alchemy",
        base_url=settings.alchemy_url,
        api_key=settings.alchemy_api_key
    )


def create_infura_provider() -> Optional[EthereumProvider]:
    """Create Infura provider if API key is configured."""
    if not settings.infura_api_key:
        return None
    
    return EthereumProvider(
        name="infura",
        base_url=settings.infura_url,
        api_key=settings.infura_api_key
    )


def create_public_provider() -> EthereumProvider:
    """Create public RPC provider (always available as fallback)."""
    return EthereumProvider(
        name="public",
        base_url=settings.public_rpc_url
    )


# =============================================================================
# Multi-Provider Client
# =============================================================================

class BlockchainClient:
    """
    Multi-provider blockchain client with automatic failover.
    
    Priority order:
    1. Alchemy (if configured)
    2. Infura (if configured)
    3. Public RPC (fallback)
    """
    
    def __init__(self):
        self._providers: List[EthereumProvider] = []
        self._current_provider_index = 0
        self._initialized = False
    
    async def initialize(self):
        """Initialize providers in priority order."""
        if self._initialized:
            return
        
        # Add providers in priority order
        alchemy = create_alchemy_provider()
        if alchemy:
            self._providers.append(alchemy)
            logger.info("blockchain_provider_added", provider="alchemy")
        
        infura = create_infura_provider()
        if infura:
            self._providers.append(infura)
            logger.info("blockchain_provider_added", provider="infura")
        
        # Always add public RPC as fallback
        self._providers.append(create_public_provider())
        logger.info("blockchain_provider_added", provider="public")
        
        self._initialized = True
        logger.info(
            "blockchain_client_initialized",
            providers=[p.name for p in self._providers]
        )
    
    async def close(self):
        """Close all provider connections."""
        for provider in self._providers:
            await provider.close()
        self._providers = []
        self._initialized = False
    
    @property
    def current_provider(self) -> EthereumProvider:
        """Get current active provider."""
        if not self._providers:
            raise RuntimeError("BlockchainClient not initialized")
        return self._providers[self._current_provider_index]
    
    def _rotate_provider(self):
        """Rotate to next available provider."""
        if len(self._providers) <= 1:
            return
        
        prev = self.current_provider.name
        self._current_provider_index = (
            self._current_provider_index + 1
        ) % len(self._providers)
        
        logger.warning(
            "provider_rotated",
            from_provider=prev,
            to_provider=self.current_provider.name
        )
    
    async def _call_with_failover(self, method_name: str, *args, **kwargs):
        """Execute method with automatic failover to next provider."""
        last_error = None
        
        for attempt in range(len(self._providers)):
            provider = self.current_provider
            method = getattr(provider, method_name)
            
            try:
                result = await method(*args, **kwargs)
                return result
            except Exception as e:
                last_error = e
                logger.warning(
                    "provider_call_failed",
                    provider=provider.name,
                    method=method_name,
                    error=str(e),
                    attempt=attempt + 1
                )
                self._rotate_provider()
        
        # All providers failed
        raise Exception(
            f"All providers failed for {method_name}: {last_error}"
        )
    
    # ==========================================================================
    # Public API
    # ==========================================================================
    
    @cached(ttl=30)  # Cache for 30 seconds
    async def get_wallet_balance(self, address: str) -> WalletBalance:
        """Get wallet balance with caching."""
        await self.initialize()
        
        balance_wei = await self._call_with_failover("get_balance", address)
        balance_eth = Decimal(balance_wei) / Decimal(10**18)
        
        return WalletBalance(
            address=address.lower(),
            chain="ethereum",
            balance_wei=balance_wei,
            balance_eth=balance_eth
        )
    
    async def get_transaction_data(self, tx_hash: str) -> Optional[TransactionData]:
        """Get normalized transaction data."""
        await self.initialize()
        
        tx = await self._call_with_failover("get_transaction", tx_hash)
        if not tx:
            return None
        
        receipt = await self._call_with_failover("get_transaction_receipt", tx_hash)
        block = await self._call_with_failover("get_block", tx["blockNumber"])
        
        timestamp = datetime.fromtimestamp(int(block["timestamp"], 16))
        
        return TransactionData(
            tx_hash=tx_hash.lower(),
            chain="ethereum",
            block_number=int(tx["blockNumber"], 16),
            timestamp=timestamp,
            from_address=tx["from"].lower(),
            to_address=tx.get("to", "").lower() if tx.get("to") else None,
            value_wei=int(tx["value"], 16),
            value_eth=Decimal(int(tx["value"], 16)) / Decimal(10**18),
            gas_used=int(receipt["gasUsed"], 16),
            gas_price=int(tx["gasPrice"], 16),
            is_success=receipt["status"] == "0x1",
            input_data=tx.get("input", "0x"),
            method_id=tx.get("input", "")[:10] if len(tx.get("input", "")) >= 10 else None
        )
    
    async def get_transaction_receipt_data(self, tx_hash: str) -> Optional[TransactionReceipt]:
        """Get transaction receipt with logs."""
        await self.initialize()
        
        receipt = await self._call_with_failover("get_transaction_receipt", tx_hash)
        if not receipt:
            return None
        
        return TransactionReceipt(
            tx_hash=tx_hash.lower(),
            status=receipt["status"] == "0x1",
            block_number=int(receipt["blockNumber"], 16),
            gas_used=int(receipt["gasUsed"], 16),
            logs=receipt.get("logs", []),
            contract_address=receipt.get("contractAddress")
        )
    
    @cached(ttl=10)
    async def get_latest_block_number(self) -> int:
        """Get latest block number with short cache."""
        await self.initialize()
        return await self._call_with_failover("get_block_number")
    
    async def is_contract(self, address: str) -> bool:
        """Check if address is a smart contract."""
        await self.initialize()
        code = await self._call_with_failover("get_code", address)
        return code and code != "0x"
    
    async def get_transaction_count(self, address: str) -> int:
        """Get total transaction count for address."""
        await self.initialize()
        return await self._call_with_failover("get_transaction_count", address)


# =============================================================================
# Global Client Instance
# =============================================================================

blockchain_client = BlockchainClient()


# =============================================================================
# Public Exports
# =============================================================================

__all__ = [
    "WalletBalance",
    "TokenBalance",
    "TransactionData",
    "TransactionReceipt",
    "BlockchainProvider",
    "EthereumProvider",
    "BlockchainClient",
    "blockchain_client",
]
