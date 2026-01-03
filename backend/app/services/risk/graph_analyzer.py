"""
ChainShield Transaction Graph Analyzer

Analyzes transaction graphs to detect:
- Layering patterns (A -> B -> C -> D -> exchange)
- Counterparty clustering
- Mixer paths
- Hub-and-spoke structures

Uses free RPC data, no external API required.
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
import structlog

logger = structlog.get_logger()


@dataclass
class TransactionNode:
    """Node in transaction graph."""
    address: str
    tx_count: int = 0
    total_value: float = 0.0
    is_contract: bool = False
    label: Optional[str] = None  # Exchange, mixer, etc.


@dataclass
class TransactionEdge:
    """Edge (transaction) between two addresses."""
    from_address: str
    to_address: str
    value: float
    timestamp: datetime
    tx_hash: str


@dataclass
class LayeringResult:
    """Result of layering pattern detection."""
    detected: bool
    confidence: float
    pattern_type: str  # simple, fan-out, fan-in, complex
    depth: int
    path: List[str]
    total_value: float
    time_span_hours: float
    risk_score: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClusterResult:
    """Result of counterparty clustering."""
    center_address: str
    cluster_size: int
    cluster_addresses: Set[str]
    total_incoming: float
    total_outgoing: float
    concentration_score: float


class TransactionGraphAnalyzer:
    """
    Analyzes transaction graphs for suspicious patterns.
    
    Patterns detected:
    1. Layering: Funds move through multiple hops quickly
    2. Fan-out: One address sends to many (distribution)
    3. Fan-in: Many addresses send to one (consolidation)
    4. Circular: Funds return to origin
    5. Mixer paths: Transactions to/from known mixers
    
    Usage:
        analyzer = TransactionGraphAnalyzer()
        
        # Check for layering
        result = await analyzer.detect_layering(
            address="0x...",
            transactions=[...],
            depth=3
        )
        
        # Get counterparty cluster
        cluster = analyzer.build_cluster(transactions)
    """
    
    # Known mixer addresses
    KNOWN_MIXERS = {
        "0x8589427373d6d84e98730d7795d8f6f8731fda16",  # Tornado Cash
        "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b",  # Tornado 1 ETH
        "0x47ce0c6ed5b0ce3d3a51fdb1c52dc66a7c3c2936",  # Tornado 0.1 ETH
    }
    
    # Known exchange deposit addresses (simplified)
    KNOWN_EXCHANGES = {
        "0x28c6c06298d514db089934071355e5743bf21d60",  # Binance
        "0x21a31ee1afc51d94c2efccaa2092ad1028285549",  # Binance
        "0x71660c4005ba85c37ccec55d0c4493e66fe775d3",  # Coinbase
    }
    
    def __init__(self):
        """Initialize graph analyzer."""
        self.logger = logger.bind(module="graph_analyzer")
    
    def detect_layering(
        self,
        address: str,
        transactions: List[Dict[str, Any]],
        depth: int = 3,
        time_window_hours: int = 24
    ) -> LayeringResult:
        """
        Detect layering patterns in transaction history.
        
        Layering: Funds rapidly move through multiple addresses
        to obscure their origin.
        
        Args:
            address: Starting address
            transactions: Transaction history
            depth: Maximum hop depth to analyze
            time_window_hours: Time window for pattern
            
        Returns:
            LayeringResult with detection details
        """
        address_lower = address.lower()
        
        if not transactions:
            return LayeringResult(
                detected=False,
                confidence=0.0,
                pattern_type="none",
                depth=0,
                path=[],
                total_value=0.0,
                time_span_hours=0.0,
                risk_score=0.0
            )
        
        # Build transaction graph
        outgoing = defaultdict(list)  # from -> [(to, value, time)]
        incoming = defaultdict(list)  # to -> [(from, value, time)]
        
        for tx in transactions:
            from_addr = tx.get("from", "").lower()
            to_addr = tx.get("to", "").lower()
            value = float(tx.get("value", 0))
            timestamp = tx.get("timestamp", datetime.utcnow())
            
            if isinstance(timestamp, (int, float)):
                timestamp = datetime.fromtimestamp(timestamp)
            elif isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            
            outgoing[from_addr].append((to_addr, value, timestamp))
            incoming[to_addr].append((from_addr, value, timestamp))
        
        # Find layering paths starting from this address
        paths = self._find_layering_paths(
            address_lower, 
            outgoing, 
            depth, 
            timedelta(hours=time_window_hours)
        )
        
        if not paths:
            return LayeringResult(
                detected=False,
                confidence=0.0,
                pattern_type="none",
                depth=0,
                path=[],
                total_value=0.0,
                time_span_hours=0.0,
                risk_score=0.0
            )
        
        # Find the longest/most suspicious path
        best_path = max(paths, key=lambda p: len(p["path"]))
        
        # Calculate risk score
        risk_score = self._calculate_layering_risk(best_path)
        
        # Determine pattern type
        if len(set(best_path["path"])) < len(best_path["path"]):
            pattern_type = "circular"
        elif self._ends_at_exchange(best_path["path"]):
            pattern_type = "exchange_exit"
        elif self._ends_at_mixer(best_path["path"]):
            pattern_type = "mixer_exit"
        else:
            pattern_type = "simple"
        
        return LayeringResult(
            detected=True,
            confidence=min(risk_score / 100, 1.0),
            pattern_type=pattern_type,
            depth=len(best_path["path"]) - 1,
            path=best_path["path"],
            total_value=best_path["total_value"],
            time_span_hours=best_path["time_span"].total_seconds() / 3600,
            risk_score=risk_score,
            details={
                "paths_found": len(paths),
                "ends_at_exchange": self._ends_at_exchange(best_path["path"]),
                "ends_at_mixer": self._ends_at_mixer(best_path["path"])
            }
        )
    
    def _find_layering_paths(
        self,
        start: str,
        graph: Dict[str, List[Tuple]],
        max_depth: int,
        time_window: timedelta
    ) -> List[Dict[str, Any]]:
        """Find all layering paths from starting address."""
        paths = []
        
        def dfs(current: str, path: List[str], total_value: float, 
                start_time: Optional[datetime], end_time: Optional[datetime],
                depth: int):
            if depth >= max_depth:
                return
            
            for to_addr, value, timestamp in graph.get(current, []):
                # Check time window
                if start_time:
                    if timestamp < start_time:
                        continue
                    if timestamp - start_time > time_window:
                        continue
                
                new_path = path + [to_addr]
                new_start = start_time or timestamp
                new_end = timestamp
                
                # Record path if significant
                if len(new_path) >= 3:
                    paths.append({
                        "path": new_path,
                        "total_value": total_value + value,
                        "time_span": new_end - new_start
                    })
                
                # Continue DFS
                dfs(to_addr, new_path, total_value + value, 
                    new_start, new_end, depth + 1)
        
        dfs(start, [start], 0, None, None, 0)
        return paths
    
    def _calculate_layering_risk(self, path_info: Dict[str, Any]) -> float:
        """Calculate risk score for a layering path."""
        score = 0.0
        path = path_info["path"]
        
        # Longer paths = higher risk
        score += min(len(path) * 10, 40)
        
        # Faster = higher risk
        time_span_hours = path_info["time_span"].total_seconds() / 3600
        if time_span_hours < 1:
            score += 30
        elif time_span_hours < 6:
            score += 20
        elif time_span_hours < 24:
            score += 10
        
        # Ends at mixer = very high risk
        if self._ends_at_mixer(path):
            score += 40
        
        # Ends at exchange = moderate risk (could be cashing out)
        if self._ends_at_exchange(path):
            score += 15
        
        return min(score, 100)
    
    def _ends_at_mixer(self, path: List[str]) -> bool:
        """Check if path ends at a known mixer."""
        if not path:
            return False
        return path[-1].lower() in self.KNOWN_MIXERS
    
    def _ends_at_exchange(self, path: List[str]) -> bool:
        """Check if path ends at a known exchange."""
        if not path:
            return False
        return path[-1].lower() in self.KNOWN_EXCHANGES
    
    def build_cluster(
        self,
        transactions: List[Dict[str, Any]],
        center_address: str
    ) -> ClusterResult:
        """
        Build counterparty cluster around an address.
        
        Args:
            transactions: Transaction list
            center_address: Address to cluster around
            
        Returns:
            ClusterResult with cluster details
        """
        center_lower = center_address.lower()
        
        counterparties: Set[str] = set()
        total_incoming = 0.0
        total_outgoing = 0.0
        counterparty_volumes: Dict[str, float] = defaultdict(float)
        
        for tx in transactions:
            from_addr = tx.get("from", "").lower()
            to_addr = tx.get("to", "").lower()
            value = float(tx.get("value", 0))
            
            if from_addr == center_lower:
                counterparties.add(to_addr)
                total_outgoing += value
                counterparty_volumes[to_addr] += value
            elif to_addr == center_lower:
                counterparties.add(from_addr)
                total_incoming += value
                counterparty_volumes[from_addr] += value
        
        # Calculate concentration (how much volume goes to top counterparty)
        total_volume = total_incoming + total_outgoing
        if counterparty_volumes and total_volume > 0:
            max_volume = max(counterparty_volumes.values())
            concentration = max_volume / total_volume
        else:
            concentration = 0.0
        
        return ClusterResult(
            center_address=center_address,
            cluster_size=len(counterparties),
            cluster_addresses=counterparties,
            total_incoming=total_incoming,
            total_outgoing=total_outgoing,
            concentration_score=concentration
        )
    
    def detect_fan_pattern(
        self,
        transactions: List[Dict[str, Any]],
        address: str,
        threshold: int = 5
    ) -> Dict[str, Any]:
        """
        Detect fan-out or fan-in patterns.
        
        Fan-out: One address sends to many (distribution)
        Fan-in: Many addresses send to one (consolidation)
        """
        address_lower = address.lower()
        
        sent_to: Set[str] = set()
        received_from: Set[str] = set()
        
        for tx in transactions:
            from_addr = tx.get("from", "").lower()
            to_addr = tx.get("to", "").lower()
            
            if from_addr == address_lower:
                sent_to.add(to_addr)
            if to_addr == address_lower:
                received_from.add(from_addr)
        
        is_fan_out = len(sent_to) >= threshold
        is_fan_in = len(received_from) >= threshold
        
        return {
            "fan_out": is_fan_out,
            "fan_out_count": len(sent_to),
            "fan_in": is_fan_in,
            "fan_in_count": len(received_from),
            "pattern_type": (
                "both" if is_fan_out and is_fan_in
                else "fan_out" if is_fan_out
                else "fan_in" if is_fan_in
                else "none"
            )
        }
    
    def find_mixer_paths(
        self,
        transactions: List[Dict[str, Any]],
        address: str
    ) -> List[Dict[str, Any]]:
        """
        Find transaction paths that lead to or from known mixers.
        
        Args:
            transactions: Transaction history
            address: Address to analyze
            
        Returns:
            List of paths involving mixers
        """
        address_lower = address.lower()
        mixer_paths = []
        
        for tx in transactions:
            from_addr = tx.get("from", "").lower()
            to_addr = tx.get("to", "").lower()
            value = float(tx.get("value", 0))
            
            # Direct interaction with mixer
            if from_addr == address_lower and to_addr in self.KNOWN_MIXERS:
                mixer_paths.append({
                    "type": "deposit_to_mixer",
                    "mixer": to_addr,
                    "value": value,
                    "tx_hash": tx.get("hash", "")
                })
            
            if from_addr in self.KNOWN_MIXERS and to_addr == address_lower:
                mixer_paths.append({
                    "type": "withdrawal_from_mixer",
                    "mixer": from_addr,
                    "value": value,
                    "tx_hash": tx.get("hash", "")
                })
        
        return mixer_paths


# Singleton
_graph_analyzer: Optional[TransactionGraphAnalyzer] = None


def get_graph_analyzer() -> TransactionGraphAnalyzer:
    """Get or create graph analyzer singleton."""
    global _graph_analyzer
    if _graph_analyzer is None:
        _graph_analyzer = TransactionGraphAnalyzer()
    return _graph_analyzer
