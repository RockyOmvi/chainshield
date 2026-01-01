"""
ChainShield Cross-Chain Entity Resolution

Resolves wallet entities across multiple blockchains.
Identifies when the same entity controls wallets on different chains.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
import structlog

logger = structlog.get_logger()


@dataclass
class CrossChainEntity:
    """An entity with presence on multiple chains."""
    entity_id: str
    addresses: Dict[str, Set[str]]  # chain -> set of addresses
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    risk_score: float = 0.0
    tags: List[str] = field(default_factory=list)
    
    @property
    def chain_count(self) -> int:
        """Number of chains this entity is on."""
        return len([c for c, addrs in self.addresses.items() if addrs])
    
    @property
    def address_count(self) -> int:
        """Total addresses across all chains."""
        return sum(len(addrs) for addrs in self.addresses.values())
    
    def add_address(self, chain: str, address: str):
        """Add an address for this entity."""
        if chain not in self.addresses:
            self.addresses[chain] = set()
        self.addresses[chain].add(address.lower())
    
    def get_addresses(self, chain: str = None) -> List[str]:
        """Get addresses, optionally filtered by chain."""
        if chain:
            return list(self.addresses.get(chain, set()))
        return [addr for addrs in self.addresses.values() for addr in addrs]


class CrossChainResolver:
    """
    Resolves entities across multiple blockchains.
    
    Uses multiple signals to link addresses:
    - Same address on EVM chains (deterministic)
    - Bridge transaction patterns
    - Timing correlations
    - Label/tag matching
    """
    
    def __init__(self):
        """Initialize resolver."""
        self.logger = logger.bind(module="crosschain_resolver")
        self.entities: Dict[str, CrossChainEntity] = {}
        self._address_to_entity: Dict[str, str] = {}
    
    def resolve_evm_address(self, address: str) -> CrossChainEntity:
        """
        Resolve an EVM address to a cross-chain entity.
        
        On EVM chains, the same private key generates the same address.
        This is deterministic resolution.
        """
        address_lower = address.lower()
        
        # Check if already tracked
        if address_lower in self._address_to_entity:
            entity_id = self._address_to_entity[address_lower]
            return self.entities[entity_id]
        
        # Create new entity with this address on all EVM chains
        entity_id = f"entity_{address_lower[:16]}"
        
        evm_chains = [
            "ethereum", "polygon", "bsc", "arbitrum", "optimism",
            "avalanche", "fantom", "base", "cronos", "gnosis",
            "celo", "moonbeam", "zksync", "linea", "scroll"
        ]
        
        entity = CrossChainEntity(
            entity_id=entity_id,
            addresses={chain: {address_lower} for chain in evm_chains},
            first_seen=datetime.utcnow()
        )
        
        self.entities[entity_id] = entity
        self._address_to_entity[address_lower] = entity_id
        
        self.logger.debug(
            "entity_resolved",
            entity_id=entity_id,
            chains=entity.chain_count
        )
        
        return entity
    
    def link_addresses(
        self,
        address1: str,
        chain1: str,
        address2: str,
        chain2: str,
        confidence: float = 1.0
    ) -> Optional[CrossChainEntity]:
        """
        Link two addresses as belonging to the same entity.
        
        Used for non-deterministic linking (e.g., Bitcoin <-> Ethereum).
        """
        addr1_lower = address1.lower()
        addr2_lower = address2.lower()
        
        entity1 = self._address_to_entity.get(addr1_lower)
        entity2 = self._address_to_entity.get(addr2_lower)
        
        if entity1 and entity2:
            if entity1 == entity2:
                # Already linked
                return self.entities[entity1]
            else:
                # Merge entities
                return self._merge_entities(entity1, entity2)
        
        elif entity1:
            # Add address2 to entity1
            self.entities[entity1].add_address(chain2, addr2_lower)
            self._address_to_entity[addr2_lower] = entity1
            return self.entities[entity1]
        
        elif entity2:
            # Add address1 to entity2
            self.entities[entity2].add_address(chain1, addr1_lower)
            self._address_to_entity[addr1_lower] = entity2
            return self.entities[entity2]
        
        else:
            # Create new entity with both addresses
            entity_id = f"entity_{addr1_lower[:8]}_{addr2_lower[:8]}"
            entity = CrossChainEntity(
                entity_id=entity_id,
                addresses={
                    chain1: {addr1_lower},
                    chain2: {addr2_lower}
                },
                first_seen=datetime.utcnow()
            )
            
            self.entities[entity_id] = entity
            self._address_to_entity[addr1_lower] = entity_id
            self._address_to_entity[addr2_lower] = entity_id
            
            return entity
    
    def _merge_entities(
        self,
        entity_id1: str,
        entity_id2: str
    ) -> CrossChainEntity:
        """Merge two entities into one."""
        entity1 = self.entities[entity_id1]
        entity2 = self.entities[entity_id2]
        
        # Merge addresses into entity1
        for chain, addresses in entity2.addresses.items():
            for addr in addresses:
                entity1.add_address(chain, addr)
                self._address_to_entity[addr] = entity_id1
        
        # Merge tags
        entity1.tags = list(set(entity1.tags + entity2.tags))
        
        # Update risk score (take max)
        entity1.risk_score = max(entity1.risk_score, entity2.risk_score)
        
        # Remove entity2
        del self.entities[entity_id2]
        
        self.logger.info(
            "entities_merged",
            kept=entity_id1,
            removed=entity_id2
        )
        
        return entity1
    
    def get_entity_by_address(
        self,
        address: str
    ) -> Optional[CrossChainEntity]:
        """Get entity for an address."""
        entity_id = self._address_to_entity.get(address.lower())
        if entity_id:
            return self.entities.get(entity_id)
        return None
    
    def analyze_cross_chain_activity(
        self,
        address: str,
        chain_balances: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Analyze cross-chain activity patterns.
        
        Returns risk signals based on cross-chain behavior.
        """
        entity = self.resolve_evm_address(address)
        
        # Calculate cross-chain metrics
        total_balance = sum(chain_balances.values())
        active_chains = len([b for b in chain_balances.values() if b > 0])
        
        # Risk signals
        signals = []
        
        # High chain diversification
        if active_chains >= 5:
            signals.append({
                "signal": "high_chain_diversification",
                "severity": "medium",
                "description": f"Active on {active_chains} chains"
            })
        
        # Balance fragmentation
        if active_chains > 1 and total_balance > 0:
            max_balance = max(chain_balances.values())
            fragmentation = 1 - (max_balance / total_balance)
            
            if fragmentation > 0.7:
                signals.append({
                    "signal": "high_balance_fragmentation",
                    "severity": "medium",
                    "description": f"Balance spread across chains ({fragmentation:.0%})"
                })
        
        return {
            "entity_id": entity.entity_id,
            "chain_count": active_chains,
            "total_balance": total_balance,
            "signals": signals,
            "risk_adjustment": len(signals) * 5  # Add 5 points per signal
        }
    
    def detect_bridge_pattern(
        self,
        transactions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Detect bridge usage patterns from transactions.
        
        Looks for:
        - Multiple bridge interactions
        - Rapid cross-chain movement
        - Split-and-merge patterns
        """
        from app.blockchain.bridges import get_bridge_registry
        
        registry = get_bridge_registry()
        bridge_txs = []
        
        for tx in transactions:
            to_addr = tx.get("to", "")
            bridge = registry.detect_bridge(to_addr)
            
            if bridge:
                bridge_txs.append({
                    "bridge": bridge.name,
                    "risk_level": bridge.risk_level,
                    "timestamp": tx.get("timestamp"),
                    "value": tx.get("value", 0)
                })
        
        # Analyze patterns
        high_risk_bridges = [t for t in bridge_txs if t["risk_level"] == "high"]
        
        return {
            "bridge_tx_count": len(bridge_txs),
            "high_risk_bridge_count": len(high_risk_bridges),
            "bridges_used": list(set(t["bridge"] for t in bridge_txs)),
            "is_frequent_bridger": len(bridge_txs) >= 5,
            "uses_high_risk_bridge": len(high_risk_bridges) > 0,
            "risk_adjustment": len(high_risk_bridges) * 10 + len(bridge_txs) * 2
        }


# Singleton
_resolver: Optional[CrossChainResolver] = None


def get_crosschain_resolver() -> CrossChainResolver:
    """Get cross-chain resolver singleton."""
    global _resolver
    if _resolver is None:
        _resolver = CrossChainResolver()
    return _resolver
