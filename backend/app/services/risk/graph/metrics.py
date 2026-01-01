"""
ChainShield Graph Metrics Extractor

Extracts graph-based features from transaction networks.
Uses centrality, clustering, and connectivity metrics.
"""

from typing import Dict, List
import structlog

from app.services.risk.graph.builder import TransactionGraphBuilder

logger = structlog.get_logger()


class GraphMetricsExtractor:
    """
    Extracts graph metrics for risk assessment.
    
    Computed metrics:
    - Degree centrality (how connected)
    - PageRank (importance in flow)
    - Clustering coefficient (neighborhood density)
    - Betweenness centrality (bridge node)
    """
    
    def __init__(self):
        """Initialize metrics extractor."""
        self.logger = logger.bind(module="graph_metrics")
        
        try:
            import networkx as nx
            self.nx = nx
            self.has_networkx = True
        except ImportError:
            self.has_networkx = False
    
    def extract_metrics(
        self,
        graph_builder: TransactionGraphBuilder,
        target_address: str
    ) -> Dict[str, float]:
        """
        Extract graph metrics for a specific address.
        
        Args:
            graph_builder: Built transaction graph
            target_address: Address to analyze
            
        Returns:
            Dictionary of graph-based features
        """
        if not self.has_networkx:
            return self._fallback_metrics(graph_builder, target_address)
        
        graph = graph_builder.get_networkx_graph()
        if not graph or len(graph) == 0:
            return self._empty_metrics()
        
        addr = target_address.lower()
        if addr not in graph:
            return self._empty_metrics()
        
        metrics = {}
        
        # Degree centrality
        try:
            in_degree = graph.in_degree(addr)
            out_degree = graph.out_degree(addr)
            metrics["in_degree"] = float(in_degree)
            metrics["out_degree"] = float(out_degree)
            metrics["total_degree"] = float(in_degree + out_degree)
            metrics["degree_ratio"] = out_degree / max(in_degree, 1)
        except Exception:
            metrics.update({"in_degree": 0, "out_degree": 0, "total_degree": 0, "degree_ratio": 0})
        
        # PageRank (importance in transaction flow)
        try:
            pagerank = self.nx.pagerank(graph, max_iter=100)
            metrics["pagerank"] = pagerank.get(addr, 0.0)
        except Exception:
            metrics["pagerank"] = 0.0
        
        # Clustering coefficient
        try:
            # Convert to undirected for clustering
            undirected = graph.to_undirected()
            clustering = self.nx.clustering(undirected, addr)
            metrics["clustering_coefficient"] = float(clustering)
        except Exception:
            metrics["clustering_coefficient"] = 0.0
        
        # Betweenness centrality (expensive, sample for large graphs)
        try:
            if len(graph) < 500:
                betweenness = self.nx.betweenness_centrality(graph)
                metrics["betweenness_centrality"] = betweenness.get(addr, 0.0)
            else:
                metrics["betweenness_centrality"] = 0.0
        except Exception:
            metrics["betweenness_centrality"] = 0.0
        
        # HITS scores (hub and authority)
        try:
            hubs, authorities = self.nx.hits(graph, max_iter=100)
            metrics["hub_score"] = hubs.get(addr, 0.0)
            metrics["authority_score"] = authorities.get(addr, 0.0)
        except Exception:
            metrics["hub_score"] = 0.0
            metrics["authority_score"] = 0.0
        
        # Average neighbor degree
        try:
            avg_neighbor = self.nx.average_neighbor_degree(graph)
            metrics["avg_neighbor_degree"] = avg_neighbor.get(addr, 0.0)
        except Exception:
            metrics["avg_neighbor_degree"] = 0.0
        
        # Flow concentration (what % of value to/from top counterparty)
        try:
            in_edges = list(graph.in_edges(addr, data=True))
            out_edges = list(graph.out_edges(addr, data=True))
            
            if in_edges:
                in_values = [e[2].get("weight", 0) for e in in_edges]
                total_in = sum(in_values)
                max_in = max(in_values) if in_values else 0
                metrics["in_concentration"] = max_in / max(total_in, 1)
            else:
                metrics["in_concentration"] = 0.0
                
            if out_edges:
                out_values = [e[2].get("weight", 0) for e in out_edges]
                total_out = sum(out_values)
                max_out = max(out_values) if out_values else 0
                metrics["out_concentration"] = max_out / max(total_out, 1)
            else:
                metrics["out_concentration"] = 0.0
                
        except Exception:
            metrics["in_concentration"] = 0.0
            metrics["out_concentration"] = 0.0
        
        self.logger.debug(
            "metrics_extracted",
            address=addr[:10],
            pagerank=f"{metrics.get('pagerank', 0):.6f}"
        )
        
        return metrics
    
    def _fallback_metrics(
        self,
        graph_builder: TransactionGraphBuilder,
        target_address: str
    ) -> Dict[str, float]:
        """Fallback when NetworkX not available."""
        neighbors = graph_builder.get_neighbors(target_address)
        
        return {
            "in_degree": float(len(neighbors["incoming"])),
            "out_degree": float(len(neighbors["outgoing"])),
            "total_degree": float(neighbors["total"]),
            "degree_ratio": len(neighbors["outgoing"]) / max(len(neighbors["incoming"]), 1),
            "pagerank": 0.0,
            "clustering_coefficient": 0.0,
            "betweenness_centrality": 0.0,
            "hub_score": 0.0,
            "authority_score": 0.0,
            "avg_neighbor_degree": 0.0,
            "in_concentration": 0.0,
            "out_concentration": 0.0,
        }
    
    def _empty_metrics(self) -> Dict[str, float]:
        """Return empty metrics."""
        return {
            "in_degree": 0.0,
            "out_degree": 0.0,
            "total_degree": 0.0,
            "degree_ratio": 0.0,
            "pagerank": 0.0,
            "clustering_coefficient": 0.0,
            "betweenness_centrality": 0.0,
            "hub_score": 0.0,
            "authority_score": 0.0,
            "avg_neighbor_degree": 0.0,
            "in_concentration": 0.0,
            "out_concentration": 0.0,
        }
    
    def get_feature_names(self) -> List[str]:
        """Get list of feature names."""
        return [
            "in_degree",
            "out_degree",
            "total_degree",
            "degree_ratio",
            "pagerank",
            "clustering_coefficient",
            "betweenness_centrality",
            "hub_score",
            "authority_score",
            "avg_neighbor_degree",
            "in_concentration",
            "out_concentration",
        ]
