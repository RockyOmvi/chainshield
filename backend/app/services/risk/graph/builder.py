"""
ChainShield Transaction Graph Builder

Builds a directed graph of wallet transactions.
Edges represent value transfers between addresses.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set
import structlog

logger = structlog.get_logger()


@dataclass
class GraphEdge:
    """An edge in the transaction graph."""
    from_address: str
    to_address: str
    value: float
    tx_count: int = 1
    timestamps: List[str] = None
    
    def __post_init__(self):
        if self.timestamps is None:
            self.timestamps = []


class TransactionGraphBuilder:
    """
    Builds transaction graphs from wallet data.
    
    Creates a directed weighted graph where:
    - Nodes = wallet addresses
    - Edges = value transfers
    - Edge weights = total value transferred
    
    Memory Protection:
    - MAX_NODES: 10,000 nodes limit
    - MAX_EDGES: 50,000 edges limit
    """
    
    # Memory protection limits
    MAX_NODES = 10_000
    MAX_EDGES = 50_000
    
    def __init__(self, max_nodes: int = None, max_edges: int = None):
        """
        Initialize graph builder with optional custom limits.
        
        Args:
            max_nodes: Maximum number of nodes (default: 10,000)
            max_edges: Maximum number of edges (default: 50,000)
        """
        self.logger = logger.bind(module="graph_builder")
        self.nodes: Set[str] = set()
        self.edges: Dict[str, GraphEdge] = {}  # "from->to" -> edge
        
        # Apply limits
        self.max_nodes = max_nodes or self.MAX_NODES
        self.max_edges = max_edges or self.MAX_EDGES
        self.limit_reached = False
        
        try:
            import networkx as nx
            self.nx = nx
            self.graph = nx.DiGraph()
            self.has_networkx = True
        except ImportError:
            self.logger.warning("networkx_not_available")
            self.has_networkx = False
            self.graph = None
    
    def add_transaction(
        self,
        from_address: str,
        to_address: str,
        value: float,
        timestamp: Optional[str] = None
    ) -> bool:
        """
        Add a transaction to the graph.
        
        Args:
            from_address: Sender address
            to_address: Receiver address
            value: Transaction value
            timestamp: Optional timestamp
            
        Returns:
            True if added, False if limit reached
        """
        # Check limits before adding
        if len(self.edges) >= self.max_edges:
            if not self.limit_reached:
                self.logger.warning(
                    "graph_edge_limit_reached",
                    max_edges=self.max_edges
                )
                self.limit_reached = True
            return False
        
        from_addr = from_address.lower()
        to_addr = to_address.lower()
        
        # Check node limit for new nodes
        edge_key = f"{from_addr}->{to_addr}"
        new_nodes_needed = sum([
            from_addr not in self.nodes,
            to_addr not in self.nodes
        ])
        
        if len(self.nodes) + new_nodes_needed > self.max_nodes:
            if not self.limit_reached:
                self.logger.warning(
                    "graph_node_limit_reached",
                    max_nodes=self.max_nodes
                )
                self.limit_reached = True
            return False
        
        # Add nodes
        self.nodes.add(from_addr)
        self.nodes.add(to_addr)
        
        # Add or update edge
        if edge_key in self.edges:
            edge = self.edges[edge_key]
            edge.value += value
            edge.tx_count += 1
            if timestamp:
                edge.timestamps.append(timestamp)
        else:
            self.edges[edge_key] = GraphEdge(
                from_address=from_addr,
                to_address=to_addr,
                value=value,
                timestamps=[timestamp] if timestamp else []
            )
        
        # Update NetworkX graph if available
        if self.has_networkx:
            if self.graph.has_edge(from_addr, to_addr):
                self.graph[from_addr][to_addr]["weight"] += value
                self.graph[from_addr][to_addr]["count"] += 1
            else:
                self.graph.add_edge(
                    from_addr, to_addr,
                    weight=value,
                    count=1
                )
        
        return True
    
    def build_from_transactions(
        self,
        transactions: List[Dict[str, Any]]
    ) -> None:
        """
        Build graph from list of transactions.
        
        Args:
            transactions: List of transaction dicts with from, to, value
        """
        for tx in transactions:
            self.add_transaction(
                from_address=tx.get("from", ""),
                to_address=tx.get("to", ""),
                value=float(tx.get("value", 0)),
                timestamp=tx.get("timestamp")
            )
        
        self.logger.info(
            "graph_built",
            nodes=len(self.nodes),
            edges=len(self.edges)
        )
    
    def get_neighbors(self, address: str) -> Dict[str, List[str]]:
        """
        Get neighbors of an address.
        
        Returns:
            Dict with "incoming" and "outgoing" neighbors
        """
        addr = address.lower()
        incoming = []
        outgoing = []
        
        for edge_key, edge in self.edges.items():
            if edge.to_address == addr:
                incoming.append(edge.from_address)
            if edge.from_address == addr:
                outgoing.append(edge.to_address)
        
        return {
            "incoming": incoming,
            "outgoing": outgoing,
            "total": len(set(incoming + outgoing))
        }
    
    def get_subgraph(self, address: str, depth: int = 2) -> "TransactionGraphBuilder":
        """
        Extract subgraph around an address.
        
        Args:
            address: Center address
            depth: How many hops to include
            
        Returns:
            New TransactionGraphBuilder with subgraph
        """
        subgraph = TransactionGraphBuilder()
        visited = set()
        to_visit = [(address.lower(), 0)]
        
        while to_visit:
            addr, current_depth = to_visit.pop(0)
            if addr in visited or current_depth > depth:
                continue
            
            visited.add(addr)
            neighbors = self.get_neighbors(addr)
            
            # Add edges
            for edge_key, edge in self.edges.items():
                if edge.from_address == addr or edge.to_address == addr:
                    subgraph.add_transaction(
                        edge.from_address,
                        edge.to_address,
                        edge.value
                    )
            
            # Queue neighbors
            for neighbor in neighbors["incoming"] + neighbors["outgoing"]:
                if neighbor not in visited:
                    to_visit.append((neighbor, current_depth + 1))
        
        return subgraph
    
    def get_networkx_graph(self):
        """Get the underlying NetworkX graph."""
        return self.graph if self.has_networkx else None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        stats = {
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "total_value": sum(e.value for e in self.edges.values()),
            "total_tx_count": sum(e.tx_count for e in self.edges.values()),
        }
        
        if self.has_networkx and self.graph:
            stats["density"] = self.nx.density(self.graph)
            stats["is_weakly_connected"] = self.nx.is_weakly_connected(self.graph) if len(self.graph) > 0 else False
        
        return stats
