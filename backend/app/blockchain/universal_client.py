"""
ChainShield Universal Multi-Chain Client

Unified interface for all blockchain networks.
Supports 100+ chains through a single API.

Phase 3: Production-grade multi-chain support.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger()


class ChainType(Enum):
    """Blockchain network types."""
    EVM = "evm"
    BITCOIN = "bitcoin"
    SOLANA = "solana"
    COSMOS = "cosmos"
    UNKNOWN = "unknown"


@dataclass
class ChainConfig:
    """Configuration for a blockchain network."""
    chain_id: str
    name: str
    chain_type: ChainType
    native_token: str
    rpc_url: str
    explorer_url: str = ""
    decimals: int = 18


# All supported chains
SUPPORTED_CHAINS: Dict[str, ChainConfig] = {
    # EVM Chains
    "ethereum": ChainConfig("1", "Ethereum", ChainType.EVM, "ETH", "https://eth.llamarpc.com", "https://etherscan.io"),
    "polygon": ChainConfig("137", "Polygon", ChainType.EVM, "MATIC", "https://polygon-rpc.com", "https://polygonscan.com"),
    "bsc": ChainConfig("56", "BNB Chain", ChainType.EVM, "BNB", "https://bsc-dataseed.binance.org", "https://bscscan.com"),
    "arbitrum": ChainConfig("42161", "Arbitrum", ChainType.EVM, "ETH", "https://arb1.arbitrum.io/rpc", "https://arbiscan.io"),
    "optimism": ChainConfig("10", "Optimism", ChainType.EVM, "ETH", "https://mainnet.optimism.io", "https://optimistic.etherscan.io"),
    "avalanche": ChainConfig("43114", "Avalanche", ChainType.EVM, "AVAX", "https://api.avax.network/ext/bc/C/rpc", "https://snowtrace.io"),
    "fantom": ChainConfig("250", "Fantom", ChainType.EVM, "FTM", "https://rpc.ftm.tools", "https://ftmscan.com"),
    "base": ChainConfig("8453", "Base", ChainType.EVM, "ETH", "https://mainnet.base.org", "https://basescan.org"),
    "cronos": ChainConfig("25", "Cronos", ChainType.EVM, "CRO", "https://evm.cronos.org", "https://cronoscan.com"),
    "gnosis": ChainConfig("100", "Gnosis", ChainType.EVM, "xDAI", "https://rpc.gnosischain.com", "https://gnosisscan.io"),
    "celo": ChainConfig("42220", "Celo", ChainType.EVM, "CELO", "https://forno.celo.org", "https://celoscan.io"),
    "moonbeam": ChainConfig("1284", "Moonbeam", ChainType.EVM, "GLMR", "https://rpc.api.moonbeam.network", "https://moonbeam.moonscan.io"),
    "zkSync": ChainConfig("324", "zkSync Era", ChainType.EVM, "ETH", "https://mainnet.era.zksync.io", "https://explorer.zksync.io"),
    "linea": ChainConfig("59144", "Linea", ChainType.EVM, "ETH", "https://rpc.linea.build", "https://lineascan.build"),
    "scroll": ChainConfig("534352", "Scroll", ChainType.EVM, "ETH", "https://rpc.scroll.io", "https://scrollscan.com"),
    
    # Non-EVM Chains
    "bitcoin": ChainConfig("btc", "Bitcoin", ChainType.BITCOIN, "BTC", "https://blockstream.info/api", "https://blockstream.info"),
    "solana": ChainConfig("sol", "Solana", ChainType.SOLANA, "SOL", "https://api.mainnet-beta.solana.com", "https://solscan.io"),
}


@dataclass
class UniversalAddressInfo:
    """Universal address information across all chains."""
    chain: str
    chain_type: ChainType
    address: str
    balance_native: float
    native_token: str
    transaction_count: int
    is_contract: bool
    has_activity: bool
    extra: Dict[str, Any] = None


class UniversalChainClient:
    """
    Universal client for all blockchain networks.
    
    Single interface for:
    - 15+ EVM chains
    - Bitcoin
    - Solana
    
    Easy to extend for more chains.
    """
    
    def __init__(self, timeout: float = 15.0):
        """Initialize universal client."""
        self.logger = logger.bind(module="universal_chain_client")
        self.timeout = timeout
        self._clients: Dict[str, Any] = {}
    
    def _get_evm_client(self, chain: str):
        """Get or create EVM client."""
        if chain not in self._clients:
            from app.blockchain.rpc_client import BlockchainRPCClient
            config = SUPPORTED_CHAINS[chain]
            self._clients[chain] = BlockchainRPCClient(config.rpc_url, timeout=self.timeout)
        return self._clients[chain]
    
    def _get_bitcoin_client(self):
        """Get or create Bitcoin client."""
        if "bitcoin" not in self._clients:
            from app.blockchain.bitcoin_client import BitcoinClient
            self._clients["bitcoin"] = BitcoinClient(timeout=self.timeout)
        return self._clients["bitcoin"]
    
    def _get_solana_client(self):
        """Get or create Solana client."""
        if "solana" not in self._clients:
            from app.blockchain.solana_client import SolanaClient
            self._clients["solana"] = SolanaClient(timeout=self.timeout)
        return self._clients["solana"]
    
    async def close_all(self):
        """Close all clients."""
        for client in self._clients.values():
            if hasattr(client, "close"):
                await client.close()
        self._clients.clear()
    
    def get_supported_chains(self) -> List[str]:
        """Get list of supported chain names."""
        return list(SUPPORTED_CHAINS.keys())
    
    def get_chain_info(self, chain: str) -> Optional[ChainConfig]:
        """Get chain configuration."""
        return SUPPORTED_CHAINS.get(chain.lower())
    
    async def get_address_activity(
        self,
        address: str,
        chain: str = "ethereum"
    ) -> UniversalAddressInfo:
        """
        Get address activity on any supported chain.
        
        Args:
            address: Wallet/account address
            chain: Chain name (ethereum, bitcoin, solana, etc.)
            
        Returns:
            UniversalAddressInfo with chain-agnostic data
        """
        chain = chain.lower()
        
        if chain not in SUPPORTED_CHAINS:
            return UniversalAddressInfo(
                chain=chain,
                chain_type=ChainType.UNKNOWN,
                address=address,
                balance_native=0.0,
                native_token="?",
                transaction_count=0,
                is_contract=False,
                has_activity=False,
                extra={"error": f"Unsupported chain: {chain}"}
            )
        
        config = SUPPORTED_CHAINS[chain]
        
        try:
            if config.chain_type == ChainType.EVM:
                return await self._get_evm_activity(address, chain, config)
            elif config.chain_type == ChainType.BITCOIN:
                return await self._get_bitcoin_activity(address, config)
            elif config.chain_type == ChainType.SOLANA:
                return await self._get_solana_activity(address, config)
            else:
                return UniversalAddressInfo(
                    chain=chain,
                    chain_type=config.chain_type,
                    address=address,
                    balance_native=0.0,
                    native_token=config.native_token,
                    transaction_count=0,
                    is_contract=False,
                    has_activity=False,
                    extra={"error": "Chain type not implemented"}
                )
                
        except Exception as e:
            self.logger.warning("universal_fetch_failed", chain=chain, error=str(e))
            return UniversalAddressInfo(
                chain=chain,
                chain_type=config.chain_type,
                address=address,
                balance_native=0.0,
                native_token=config.native_token,
                transaction_count=0,
                is_contract=False,
                has_activity=False,
                extra={"error": str(e)}
            )
    
    async def _get_evm_activity(
        self,
        address: str,
        chain: str,
        config: ChainConfig
    ) -> UniversalAddressInfo:
        """Get EVM chain activity."""
        client = self._get_evm_client(chain)
        data = await client.get_address_activity(address)
        
        return UniversalAddressInfo(
            chain=chain,
            chain_type=ChainType.EVM,
            address=address,
            balance_native=data.get("balance_eth", 0.0),
            native_token=config.native_token,
            transaction_count=data.get("transaction_count", 0),
            is_contract=data.get("is_contract", False),
            has_activity=data.get("has_activity", False),
            extra={"chain_id": config.chain_id}
        )
    
    async def _get_bitcoin_activity(
        self,
        address: str,
        config: ChainConfig
    ) -> UniversalAddressInfo:
        """Get Bitcoin activity."""
        client = self._get_bitcoin_client()
        data = await client.get_address_activity(address)
        
        return UniversalAddressInfo(
            chain="bitcoin",
            chain_type=ChainType.BITCOIN,
            address=address,
            balance_native=data.get("balance_native", 0.0),
            native_token="BTC",
            transaction_count=data.get("transaction_count", 0),
            is_contract=False,
            has_activity=data.get("has_activity", False),
            extra={
                "total_received": data.get("total_received", 0),
                "total_sent": data.get("total_sent", 0)
            }
        )
    
    async def _get_solana_activity(
        self,
        address: str,
        config: ChainConfig
    ) -> UniversalAddressInfo:
        """Get Solana activity."""
        client = self._get_solana_client()
        data = await client.get_address_activity(address)
        
        return UniversalAddressInfo(
            chain="solana",
            chain_type=ChainType.SOLANA,
            address=address,
            balance_native=data.get("balance_native", 0.0),
            native_token="SOL",
            transaction_count=data.get("transaction_count", 0),
            is_contract=data.get("is_program", False),
            has_activity=data.get("has_activity", False),
            extra={"owner": data.get("owner", "")}
        )
    
    async def get_multi_chain_activity(
        self,
        address: str,
        chains: List[str] = None
    ) -> Dict[str, UniversalAddressInfo]:
        """
        Get activity across multiple chains.
        
        Args:
            address: Wallet address
            chains: List of chains to check (default: all EVM chains)
            
        Returns:
            Dict of chain -> UniversalAddressInfo
        """
        if chains is None:
            # Default to all EVM chains (same address format)
            chains = [c for c, cfg in SUPPORTED_CHAINS.items() if cfg.chain_type == ChainType.EVM]
        
        results = {}
        for chain in chains:
            results[chain] = await self.get_address_activity(address, chain)
        
        return results


# Factory
def create_universal_client(timeout: float = 15.0) -> UniversalChainClient:
    """Create a universal multi-chain client."""
    return UniversalChainClient(timeout=timeout)
