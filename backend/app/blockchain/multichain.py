"""
ChainShield Multi-Chain Provider

Supports multiple blockchains for cross-chain analysis:
- Ethereum (mainnet, Goerli)
- Polygon
- Arbitrum
- BSC (Binance Smart Chain)
- Optimism

PRODUCTION FEATURES:
- Retry with exponential backoff
- Multiple fallback RPC endpoints
- Circuit breaker pattern
"""

import asyncio
from dataclasses import dataclass, field
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
    AVALANCHE = "avalanche"
    FANTOM = "fantom"
    ZKSYNC = "zksync"
    
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
            Chain.AVALANCHE: 43114,
            Chain.FANTOM: 250,
            Chain.ZKSYNC: 324,
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
            Chain.AVALANCHE: "https://snowtrace.io",
            Chain.FANTOM: "https://ftmscan.com",
            Chain.ZKSYNC: "https://explorer.zksync.io",
        }.get(self, "https://etherscan.io")


@dataclass
class ChainConfig:
    """Configuration for a blockchain."""
    chain: Chain
    rpc_url: str
    fallback_rpcs: List[str] = field(default_factory=list)
    api_key: Optional[str] = None
    is_active: bool = True
    
    # Circuit breaker state
    failure_count: int = 0
    last_failure_time: float = 0


# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 0.5
MAX_BACKOFF_SECONDS = 8.0
CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_RESET_SECONDS = 60


class MultiChainProvider:
    """
    Provider for multiple blockchain networks.
    
    Production Features:
    - Retry with exponential backoff
    - Multiple fallback RPC endpoints
    - Circuit breaker pattern
    """
    
    # Default RPC endpoints with fallbacks
    DEFAULT_RPCS = {
        Chain.ETHEREUM: [
            "https://eth.llamarpc.com",
            "https://rpc.ankr.com/eth",
            "https://ethereum.publicnode.com",
        ],
        Chain.POLYGON: [
            "https://polygon-rpc.com",
            "https://rpc.ankr.com/polygon",
            "https://polygon-bor-rpc.publicnode.com",
        ],
        Chain.ARBITRUM: [
            "https://arb1.arbitrum.io/rpc",
            "https://rpc.ankr.com/arbitrum",
        ],
        Chain.BSC: [
            "https://bsc-dataseed.binance.org",
            "https://bsc-dataseed1.ninicoin.io",
            "https://bsc-dataseed1.defibit.io",
        ],
        Chain.OPTIMISM: [
            "https://mainnet.optimism.io",
            "https://rpc.ankr.com/optimism",
        ],
        Chain.BASE: [
            "https://mainnet.base.org",
            "https://base.publicnode.com",
        ],
        Chain.AVALANCHE: [
            "https://api.avax.network/ext/bc/C/rpc",
            "https://rpc.ankr.com/avalanche",
        ],
        Chain.FANTOM: [
            "https://rpc.ftm.tools",
            "https://rpc.ankr.com/fantom",
        ],
        Chain.ZKSYNC: [
            "https://mainnet.era.zksync.io",
            "https://zksync-era.blockpi.network/v1/rpc/public",
        ],
    }
    
    def __init__(self, configs: Optional[List[ChainConfig]] = None):
        """
        Initialize multi-chain provider with retry support.
        
        Args:
            configs: Optional custom chain configurations
        """
        self.logger = logger.bind(module="multichain")
        self.chains: Dict[Chain, ChainConfig] = {}
        
        # Initialize default chains with fallbacks
        for chain, rpcs in self.DEFAULT_RPCS.items():
            self.chains[chain] = ChainConfig(
                chain=chain,
                rpc_url=rpcs[0],
                fallback_rpcs=rpcs[1:] if len(rpcs) > 1 else []
            )
        
        # Override with custom configs
        if configs:
            for config in configs:
                self.chains[config.chain] = config
        
        self.logger.info(
            "multichain_initialized_with_retry",
            chains=[c.value for c in self.chains.keys()]
        )
    
    def get_chain(self, chain: Chain) -> Optional[ChainConfig]:
        """Get configuration for a specific chain."""
        return self.chains.get(chain)
    
    def list_active_chains(self) -> List[Chain]:
        """List all active chains."""
        return [c for c, cfg in self.chains.items() if cfg.is_active]
    
    def _is_circuit_open(self, config: ChainConfig) -> bool:
        """Check if circuit breaker is open (too many failures)."""
        import time
        
        if config.failure_count >= CIRCUIT_BREAKER_THRESHOLD:
            # Check if enough time has passed to reset
            elapsed = time.time() - config.last_failure_time
            if elapsed < CIRCUIT_BREAKER_RESET_SECONDS:
                return True
            else:
                # Reset circuit breaker
                config.failure_count = 0
                self.logger.info(
                    "circuit_breaker_reset",
                    chain=config.chain.value
                )
        return False
    
    def _record_failure(self, config: ChainConfig) -> None:
        """Record a failure for circuit breaker."""
        import time
        config.failure_count += 1
        config.last_failure_time = time.time()
    
    def _record_success(self, config: ChainConfig) -> None:
        """Record success, reset failure count."""
        config.failure_count = 0
    
    async def _call_rpc_with_retry(
        self,
        config: ChainConfig,
        address: str
    ) -> Optional[Dict[str, Any]]:
        """
        Call RPC with retry and fallback logic.
        
        Uses exponential backoff and tries fallback RPCs.
        """
        # Check circuit breaker
        if self._is_circuit_open(config):
            self.logger.warning(
                "circuit_breaker_open",
                chain=config.chain.value
            )
            return None
        
        # Build list of RPCs to try
        rpcs_to_try = [config.rpc_url] + config.fallback_rpcs
        
        for rpc_index, rpc_url in enumerate(rpcs_to_try):
            backoff = INITIAL_BACKOFF_SECONDS
            
            for attempt in range(MAX_RETRIES):
                try:
                    result = await self._make_rpc_call(rpc_url, address)
                    self._record_success(config)
                    return result
                    
                except Exception as e:
                    self.logger.debug(
                        "rpc_attempt_failed",
                        chain=config.chain.value,
                        rpc_index=rpc_index,
                        attempt=attempt + 1,
                        error=str(e)
                    )
                    
                    # Exponential backoff
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(backoff)
                        backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)
            
            # All retries failed for this RPC, try next fallback
            self.logger.warning(
                "rpc_all_retries_failed",
                chain=config.chain.value,
                rpc_url=rpc_url[:30]
            )
        
        # All RPCs failed
        self._record_failure(config)
        return None
    
    async def _make_rpc_call(
        self,
        rpc_url: str,
        address: str
    ) -> Dict[str, Any]:
        """
        Make actual RPC call using BlockchainRPCClient.
        
        Uses real JSON-RPC calls to blockchain nodes.
        """
        from app.blockchain.rpc_client import BlockchainRPCClient
        
        client = BlockchainRPCClient(rpc_url, timeout=self.timeout)
        try:
            result = await client.get_address_activity(address)
            return result
        finally:
            await client.close()
    
    async def get_address_activity(
        self,
        address: str,
        chains: Optional[List[Chain]] = None
    ) -> Dict[Chain, Dict[str, Any]]:
        """
        Get address activity across multiple chains with retry.
        
        Args:
            address: Wallet address to check
            chains: Specific chains to check (default: all)
            
        Returns:
            Dictionary mapping chain to activity data
        """
        target_chains = chains or self.list_active_chains()
        results = {}
        
        for chain in target_chains:
            config = self.chains.get(chain)
            if not config:
                continue
            
            try:
                activity = await self._call_rpc_with_retry(config, address)
                if activity:
                    activity["chain"] = chain.value
                    results[chain] = activity
            except Exception as e:
                self.logger.error(
                    "chain_activity_error",
                    chain=chain.value,
                    error=str(e)
                )
        
        return results
    
    async def _get_chain_activity(
        self,
        address: str,
        chain: Chain
    ) -> Optional[Dict[str, Any]]:
        """Get activity on a specific chain with retry."""
        config = self.chains.get(chain)
        if not config:
            return None
        
        return await self._call_rpc_with_retry(config, address)
    
    def get_chain_stats(self) -> Dict[str, Any]:
        """Get statistics about chain coverage."""
        return {
            "total_chains": len(self.chains),
            "active_chains": len(self.list_active_chains()),
            "retry_config": {
                "max_retries": MAX_RETRIES,
                "initial_backoff_seconds": INITIAL_BACKOFF_SECONDS,
                "circuit_breaker_threshold": CIRCUIT_BREAKER_THRESHOLD,
            },
            "chains": [
                {
                    "name": chain.value,
                    "chain_id": chain.chain_id,
                    "active": cfg.is_active,
                    "failure_count": cfg.failure_count,
                    "fallback_count": len(cfg.fallback_rpcs),
                }
                for chain, cfg in self.chains.items()
            ]
        }
