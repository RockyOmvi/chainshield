"""
ChainShield Bridge Registry

Tracks known bridge contracts for cross-chain transaction detection.
Bridges enable moving assets between chains, often used for laundering.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set
import structlog

from app.blockchain.multichain import Chain

logger = structlog.get_logger()


@dataclass
class Bridge:
    """A cross-chain bridge protocol."""
    name: str
    contracts: Dict[Chain, Set[str]]  # Chain -> contract addresses
    risk_level: str  # "low", "medium", "high"
    description: str = ""


class BridgeRegistry:
    """
    Registry of known cross-chain bridges.
    
    Used to detect bridge interactions and track cross-chain flows.
    """
    
    def __init__(self):
        """Initialize bridge registry with known bridges."""
        self.logger = logger.bind(module="bridge_registry")
        self.bridges: Dict[str, Bridge] = {}
        self._load_default_bridges()
    
    def _load_default_bridges(self) -> None:
        """Load known bridge contracts."""
        
        # Stargate Finance (LayerZero)
        self.register_bridge(Bridge(
            name="stargate",
            contracts={
                Chain.ETHEREUM: {"0x8731d54e9d02c286767d56ac03e8037c07e01e98"},
                Chain.POLYGON: {"0x45a01e4e04f14f7a4a6702c74187c5f6222033cd"},
                Chain.ARBITRUM: {"0x53bf833a5d6c4dda888f69c22c88c9f356a41614"},
                Chain.BSC: {"0x4a364f8c717caad9a442737eb7b8a55cc6cf18d8"},
                Chain.OPTIMISM: {"0xb0d502e938ed5f4df2e681fe6e419ff29631d62b"},
            },
            risk_level="medium",
            description="LayerZero-based cross-chain bridge"
        ))
        
        # Hop Protocol
        self.register_bridge(Bridge(
            name="hop",
            contracts={
                Chain.ETHEREUM: {"0x3666f603cc164936c1b87e207f36beba4ac5f18a"},
                Chain.POLYGON: {"0x76b22b8c1079a44f1211f0a8c7b8b1a4b6b5c5c5"},
                Chain.ARBITRUM: {"0x33ceb27b39d2bb7d2e61f7564d3df29344020417"},
                Chain.OPTIMISM: {"0x83f6244bd87662118d96d9a6d44f09dfff14b30e"},
            },
            risk_level="low",
            description="Fast cross-chain transfers"
        ))
        
        # Wormhole
        self.register_bridge(Bridge(
            name="wormhole",
            contracts={
                Chain.ETHEREUM: {"0x98f3c9e6e3face36baad05fe09d375ef1464288b"},
                Chain.POLYGON: {"0x7a4b5a56256163f0163b9a7d4a5c5c5c5c5c5c5c"},
                Chain.BSC: {"0x98f3c9e6e3face36baad05fe09d375ef1464288b"},
            },
            risk_level="medium",
            description="Multi-chain messaging and asset bridge"
        ))
        
        # Multichain (formerly Anyswap) - HIGH RISK (was hacked)
        self.register_bridge(Bridge(
            name="multichain",
            contracts={
                Chain.ETHEREUM: {"0x6b7a87899490ece95443e979ca9485cbe7e71522"},
                Chain.POLYGON: {"0x6b7a87899490ece95443e979ca9485cbe7e71521"},
                Chain.BSC: {"0xd1c5966f9f5ee6881ff6b261bbeda45972b81b54"},
            },
            risk_level="high",
            description="DEPRECATED - Was compromised in 2023"
        ))
        
        # Synapse Protocol
        self.register_bridge(Bridge(
            name="synapse",
            contracts={
                Chain.ETHEREUM: {"0x2796317b0ff8538f253012862c06787adfb8ceb6"},
                Chain.POLYGON: {"0x8f5bbb2bb8c2ee94639e55d5f41de9b4839c1280"},
                Chain.ARBITRUM: {"0x6f4e8eba4d337f874ab57478acc2cb5bacdc19c9"},
                Chain.BSC: {"0xd123f70ae324d34a9e76b67a27bf77593ba8749f"},
            },
            risk_level="medium",
            description="Cross-chain liquidity protocol"
        ))
        
        self.logger.info(
            "bridges_loaded",
            count=len(self.bridges)
        )
    
    def register_bridge(self, bridge: Bridge) -> None:
        """Register a bridge in the registry."""
        self.bridges[bridge.name] = bridge
    
    def detect_bridge(
        self,
        address: str,
        chain: Optional[Chain] = None
    ) -> Optional[Bridge]:
        """
        Check if an address is a known bridge.
        
        Args:
            address: Contract address to check
            chain: Optional specific chain to check
            
        Returns:
            Bridge if found, None otherwise
        """
        address_lower = address.lower()
        
        for bridge in self.bridges.values():
            for bridge_chain, contracts in bridge.contracts.items():
                if chain and bridge_chain != chain:
                    continue
                if address_lower in {c.lower() for c in contracts}:
                    return bridge
        
        return None
    
    def is_bridge_transaction(
        self,
        to_address: str,
        chain: Optional[Chain] = None
    ) -> tuple:
        """
        Check if a transaction is to a bridge.
        
        Returns:
            Tuple of (is_bridge, bridge_name, risk_level)
        """
        bridge = self.detect_bridge(to_address, chain)
        if bridge:
            return True, bridge.name, bridge.risk_level
        return False, None, None
    
    def get_bridge_risk(self, bridge_name: str) -> str:
        """Get risk level for a bridge."""
        bridge = self.bridges.get(bridge_name)
        return bridge.risk_level if bridge else "unknown"
    
    def list_bridges(self) -> List[Dict[str, Any]]:
        """List all registered bridges."""
        return [
            {
                "name": b.name,
                "risk_level": b.risk_level,
                "chains": [c.value for c in b.contracts.keys()],
                "description": b.description,
            }
            for b in self.bridges.values()
        ]
    
    def get_high_risk_bridges(self) -> List[str]:
        """Get names of high-risk bridges."""
        return [
            name for name, bridge in self.bridges.items()
            if bridge.risk_level == "high"
        ]


# Singleton instance
_bridge_registry: Optional[BridgeRegistry] = None


def get_bridge_registry() -> BridgeRegistry:
    """Get or create the bridge registry singleton."""
    global _bridge_registry
    if _bridge_registry is None:
        _bridge_registry = BridgeRegistry()
    return _bridge_registry
