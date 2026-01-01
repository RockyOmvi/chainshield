"""
ChainShield Multi-Chain Provider

Supports multiple blockchains for cross-chain analysis:
- Ethereum (mainnet, Goerli)
- Polygon
- Arbitrum
- BSC (Binance Smart Chain)
- Optimism
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger()


class Chain(str, Enum):
    """Supported blockchain networks."""
    ETHEREUM = "ethereum"
    POLYGON = "polygon"
    ARBITRUM = "arbitrum"
    BSC = "bsc"
    OPTIMISM = "optimism"
    BASE = "base"
    
    @property
    def chain_id(self) -> int:
        """Get numeric chain ID."""
        return {
            Chain.ETHEREUM: 1,
            Chain.POLYGON: 137,
            Chain.ARBITRUM: 42161,
            Chain.BSC: 56,
            Chain.OPTIMISM: 10,
            Chain.BASE: 8453,
        }.get(self, 1)
    
    @property
    def explorer_url(self) -> str:
        """Get block explorer URL."""
        return {
            Chain.ETHEREUM: "https://etherscan.io",
            Chain.POLYGON: "https://polygonscan.com",
            Chain.ARBITRUM: "https://arbiscan.io",
            Chain.BSC: "https://bscscan.com",
            Chain.OPTIMISM: "https://optimistic.etherscan.io",
            Chain.BASE: "https://basescan.org",
        }.get(self, "https://etherscan.io")


@dataclass
class ChainConfig:
    """Configuration for a blockchain."""
    chain: Chain
    rpc_url: str
    api_key: Optional[str] = None
    is_active: bool = True


class MultiChainProvider:
    """
    Provider for multiple blockchain networks.
    
    Enables cross-chain transaction tracking and analysis.
    """
    
    # Default RPC endpoints (public, rate-limited)
    DEFAULT_RPCS = {
        Chain.ETHEREUM: "https://eth.llamarpc.com",
        Chain.POLYGON: "https://polygon-rpc.com",
        Chain.ARBITRUM: "https://arb1.arbitrum.io/rpc",
        Chain.BSC: "https://bsc-dataseed.binance.org",
        Chain.OPTIMISM: "https://mainnet.optimism.io",
        Chain.BASE: "https://mainnet.base.org",
    }
    
    def __init__(self, configs: Optional[List[ChainConfig]] = None):
        """
        Initialize multi-chain provider.
        
        Args:
            configs: Optional custom chain configurations
        """
        self.logger = logger.bind(module="multichain")
        self.chains: Dict[Chain, ChainConfig] = {}
        
        # Initialize default chains
        for chain, rpc in self.DEFAULT_RPCS.items():
            self.chains[chain] = ChainConfig(chain=chain, rpc_url=rpc)
        
        # Override with custom configs
        if configs:
            for config in configs:
                self.chains[config.chain] = config
        
        self.logger.info(
            "multichain_initialized",
            chains=[c.value for c in self.chains.keys()]
        )
    
    def get_chain(self, chain: Chain) -> Optional[ChainConfig]:
        """Get configuration for a specific chain."""
        return self.chains.get(chain)
    
    def list_active_chains(self) -> List[Chain]:
        """List all active chains."""
        return [c for c, cfg in self.chains.items() if cfg.is_active]
    
    async def get_address_activity(
        self,
        address: str,
        chains: Optional[List[Chain]] = None
    ) -> Dict[Chain, Dict[str, Any]]:
        """
        Get address activity across multiple chains.
        
        Args:
            address: Wallet address to check
            chains: Specific chains to check (default: all)
            
        Returns:
            Dictionary mapping chain to activity data
        """
        target_chains = chains or self.list_active_chains()
        results = {}
        
        for chain in target_chains:
            try:
                activity = await self._get_chain_activity(address, chain)
                if activity:
                    results[chain] = activity
            except Exception as e:
                self.logger.warning(
                    "chain_activity_failed",
                    chain=chain.value,
                    error=str(e)
                )
        
        return results
    
    async def _get_chain_activity(
        self,
        address: str,
        chain: Chain
    ) -> Optional[Dict[str, Any]]:
        """Get activity on a specific chain (placeholder)."""
        # In production, this would call the chain's RPC
        # For now, return mock structure
        return {
            "chain": chain.value,
            "address": address,
            "has_activity": False,
            "tx_count": 0,
            "balance": 0.0,
        }
    
    def get_chain_stats(self) -> Dict[str, Any]:
        """Get statistics about chain coverage."""
        return {
            "total_chains": len(self.chains),
            "active_chains": len(self.list_active_chains()),
            "chains": [
                {
                    "name": chain.value,
                    "chain_id": chain.chain_id,
                    "active": cfg.is_active,
                }
                for chain, cfg in self.chains.items()
            ]
        }
