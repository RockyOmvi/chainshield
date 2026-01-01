"""
ChainShield Community Detection

Detects fraud rings and suspicious clusters in transaction graphs.
Uses community detection algorithms to find coordinated activity.
"""

from dataclasses import dataclass
from typing import List, Optional, Set
import structlog

from app.services.risk.graph.builder import TransactionGraphBuilder

logger = structlog.get_logger()


@dataclass
class Community:
    """A detected community/cluster."""
    id: int
    members: Set[str]
    size: int
    density: float
    total_value: float
    is_suspicious: bool
    suspicion_reasons: List[str]


class CommunityDetector:
    """
    Detects communities and fraud rings in transaction graphs.
    
    Uses Louvain algorithm for community detection.
    Flags suspicious communities based on patterns.
    """
    
    # Thresholds for suspicion
    MIN_SIZE_FOR_RING = 3
    MAX_DAYS_ACTIVE = 7  # Suspiciously short activity
    HIGH_INTERNAL_TX_RATIO = 0.7  # Most tx within community
    
    def __init__(self):
        """Initialize detector."""
        self.logger = logger.bind(module="community_detector")
        
        try:
            import networkx as nx
            self.nx = nx
            self.has_networkx = True
        except ImportError:
            self.has_networkx = False
    
    def detect_communities(
        self,
        graph_builder: TransactionGraphBuilder
    ) -> List[Community]:
        """
        Detect communities in the transaction graph.
        
        Args:
            graph_builder: Built transaction graph
            
        Returns:
            List of detected communities
        """
        if not self.has_networkx:
            return []
        
        graph = graph_builder.get_networkx_graph()
        if not graph or len(graph) < 3:
            return []
        
        try:
            # Use Louvain community detection
            from networkx.algorithms import community as nx_community
            
            # Convert to undirected for community detection
            undirected = graph.to_undirected()
            
            # Detect communities
            communities = list(nx_community.louvain_communities(undirected))
            
            results = []
            for idx, members in enumerate(communities):
                if len(members) >= self.MIN_SIZE_FOR_RING:
                    community = self._analyze_community(
                        graph, members, idx
                    )
                    results.append(community)
            
            self.logger.info(
                "communities_detected",
                total=len(communities),
                suspicious=sum(1 for c in results if c.is_suspicious)
            )
            
            return results
            
        except Exception as e:
            self.logger.error("community_detection_failed", error=str(e))
            return []
    
    def _analyze_community(
        self,
        graph,
        members: Set[str],
        community_id: int
    ) -> Community:
        """Analyze a community for suspicious patterns."""
        suspicion_reasons = []
        
        # Calculate density
        subgraph = graph.subgraph(members)
        density = self.nx.density(subgraph)
        
        # Calculate total value
        total_value = sum(
            data.get("weight", 0)
            for _, _, data in subgraph.edges(data=True)
        )
        
        # Check 1: High density (everyone transacts with everyone)
        if density > 0.5 and len(members) > 3:
            suspicion_reasons.append(f"High density: {density:.2f}")
        
        # Check 2: High internal transaction ratio
        internal_edges = subgraph.number_of_edges()
        external_in = sum(1 for u, v in graph.in_edges(members) if u not in members)
        external_out = sum(1 for u, v in graph.out_edges(members) if v not in members)
        total_edges = internal_edges + external_in + external_out
        
        if total_edges > 0:
            internal_ratio = internal_edges / total_edges
            if internal_ratio > self.HIGH_INTERNAL_TX_RATIO:
                suspicion_reasons.append(f"High internal ratio: {internal_ratio:.0%}")
        
        # Check 3: Cycle pattern (A -> B -> C -> A)
        try:
            cycles = list(self.nx.simple_cycles(subgraph))
            if len(cycles) > 2:
                suspicion_reasons.append(f"Circular transactions: {len(cycles)} cycles")
        except Exception:
            pass
        
        # Check 4: Single entry/exit points (coordinated)
        in_nodes = [n for n in members if graph.in_degree(n) > 0 and 
                   any(u not in members for u, _ in graph.in_edges(n))]
        out_nodes = [n for n in members if graph.out_degree(n) > 0 and
                    any(v not in members for _, v in graph.out_edges(n))]
        
        if len(in_nodes) <= 2 and len(out_nodes) <= 2 and len(members) > 5:
            suspicion_reasons.append("Limited entry/exit points")
        
        is_suspicious = len(suspicion_reasons) >= 2
        
        return Community(
            id=community_id,
            members=members,
            size=len(members),
            density=round(density, 4),
            total_value=round(total_value, 4),
            is_suspicious=is_suspicious,
            suspicion_reasons=suspicion_reasons
        )
    
    def find_address_community(
        self,
        graph_builder: TransactionGraphBuilder,
        address: str
    ) -> Optional[Community]:
        """
        Find which community an address belongs to.
        
        Args:
            graph_builder: Built graph
            address: Target address
            
        Returns:
            Community if found
        """
        communities = self.detect_communities(graph_builder)
        addr = address.lower()
        
        for community in communities:
            if addr in community.members:
                return community
        
        return None
    
    def get_suspicious_communities(
        self,
        graph_builder: TransactionGraphBuilder
    ) -> List[Community]:
        """Get only suspicious communities."""
        communities = self.detect_communities(graph_builder)
        return [c for c in communities if c.is_suspicious]
