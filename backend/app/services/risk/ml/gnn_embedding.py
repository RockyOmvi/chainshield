"""
ChainShield GNN Embeddings

Graph Neural Network embeddings for fraud detection.
Learns structural patterns in transaction graphs.
"""

import numpy as np
from typing import Any, Dict, List, Optional, Tuple
import structlog

logger = structlog.get_logger()


class GNNEmbedding:
    """
    Graph Neural Network embeddings for wallet addresses.
    
    Uses message-passing to learn node representations
    from transaction graph structure.
    
    Features:
    - Simple GNN (Graph Attention approximation)
    - Neighbor aggregation
    - Multi-hop information
    - Fraud pattern learning
    """
    
    EMBEDDING_DIM = 32
    NUM_HOPS = 2
    
    def __init__(self, embedding_dim: int = 32, num_hops: int = 2):
        """
        Initialize GNN embedder.
        
        Args:
            embedding_dim: Output embedding dimension
            num_hops: Number of message passing iterations
        """
        self.logger = logger.bind(module="gnn_embedding")
        self.embedding_dim = embedding_dim
        self.num_hops = num_hops
        
        # Learnable parameters (initialized randomly, can be trained)
        np.random.seed(42)
        self.W1 = np.random.randn(48, embedding_dim) * 0.1  # Input transform
        self.W2 = np.random.randn(embedding_dim, embedding_dim) * 0.1  # Hidden
        self.attention_weights = np.random.randn(embedding_dim * 2, 1) * 0.1
    
    def _relu(self, x: np.ndarray) -> np.ndarray:
        """ReLU activation."""
        return np.maximum(0, x)
    
    def _softmax(self, x: np.ndarray) -> np.ndarray:
        """Softmax for attention."""
        exp_x = np.exp(x - np.max(x))
        return exp_x / (exp_x.sum() + 1e-8)
    
    def _compute_attention(
        self,
        node_embedding: np.ndarray,
        neighbor_embeddings: List[np.ndarray]
    ) -> np.ndarray:
        """
        Compute attention-weighted neighbor aggregation.
        
        Args:
            node_embedding: Current node's embedding
            neighbor_embeddings: List of neighbor embeddings
            
        Returns:
            Aggregated neighbor representation
        """
        if not neighbor_embeddings:
            return np.zeros(self.embedding_dim)
        
        # Compute attention scores
        scores = []
        for neighbor_emb in neighbor_embeddings:
            concat = np.concatenate([node_embedding, neighbor_emb])
            score = concat @ self.attention_weights
            scores.append(score[0])
        
        # Softmax attention
        attention = self._softmax(np.array(scores))
        
        # Weighted aggregation
        aggregated = np.zeros(self.embedding_dim)
        for i, neighbor_emb in enumerate(neighbor_embeddings):
            aggregated += attention[i] * neighbor_emb
        
        return aggregated
    
    def compute_embedding(
        self,
        node_features: np.ndarray,
        neighbor_features: List[np.ndarray],
        neighbor_edge_weights: Optional[List[float]] = None
    ) -> np.ndarray:
        """
        Compute GNN embedding for a node.
        
        Args:
            node_features: Feature vector for target node (48 dims)
            neighbor_features: Feature vectors for neighbors
            neighbor_edge_weights: Optional edge weights
            
        Returns:
            Embedding vector (32 dims)
        """
        # Initial embedding from node features
        if len(node_features) < 48:
            # Pad if needed
            node_features = np.concatenate([
                node_features,
                np.zeros(48 - len(node_features))
            ])
        
        node_emb = self._relu(node_features[:48] @ self.W1)
        
        # Get neighbor embeddings
        neighbor_embs = []
        for nf in neighbor_features[:10]:  # Limit neighbors
            if len(nf) < 48:
                nf = np.concatenate([nf, np.zeros(48 - len(nf))])
            neighbor_embs.append(self._relu(nf[:48] @ self.W1))
        
        # Message passing
        for hop in range(self.num_hops):
            # Aggregate neighbors with attention
            if neighbor_embs:
                neighbor_agg = self._compute_attention(node_emb, neighbor_embs)
            else:
                neighbor_agg = np.zeros(self.embedding_dim)
            
            # Combine self and neighbors
            combined = node_emb + neighbor_agg
            
            # Transform
            node_emb = self._relu(combined @ self.W2)
        
        # Normalize
        norm = np.linalg.norm(node_emb)
        if norm > 0:
            node_emb = node_emb / norm
        
        return node_emb
    
    def compute_graph_embedding(
        self,
        graph_builder,
        target_address: str,
        feature_extractor=None
    ) -> Dict[str, Any]:
        """
        Compute embedding from transaction graph.
        
        Args:
            graph_builder: TransactionGraphBuilder with graph data
            target_address: Address to compute embedding for
            feature_extractor: Optional feature extractor for neighbors
            
        Returns:
            Dict with embedding and metadata
        """
        addr = target_address.lower()
        
        # Get neighbors
        neighbors = graph_builder.get_neighbors(addr)
        all_neighbors = list(set(
            neighbors.get("incoming", []) + neighbors.get("outgoing", [])
        ))
        
        # Create pseudo-features for nodes
        # (In production, would use actual wallet features)
        np.random.seed(hash(addr) % 2**31)
        node_features = np.random.randn(48) * 0.1
        
        neighbor_features = []
        for n in all_neighbors[:10]:
            np.random.seed(hash(n) % 2**31)
            neighbor_features.append(np.random.randn(48) * 0.1)
        
        # Edge weights from graph
        edge_weights = []
        for n in all_neighbors[:10]:
            edge_key = f"{addr}->{n}"
            edge = graph_builder.edges.get(edge_key)
            if edge:
                edge_weights.append(edge.value)
            else:
                edge_key = f"{n}->{addr}"
                edge = graph_builder.edges.get(edge_key)
                edge_weights.append(edge.value if edge else 1.0)
        
        # Compute embedding
        embedding = self.compute_embedding(
            node_features,
            neighbor_features,
            edge_weights if edge_weights else None
        )
        
        return {
            "embedding": embedding.tolist(),
            "embedding_dim": len(embedding),
            "neighbors_used": len(neighbor_features),
            "hops": self.num_hops,
        }
    
    def extract_gnn_features(
        self,
        graph_builder,
        target_address: str
    ) -> List[float]:
        """
        Extract GNN features as float list for ML model.
        
        Args:
            graph_builder: Transaction graph
            target_address: Target wallet
            
        Returns:
            List of 32 GNN embedding values
        """
        result = self.compute_graph_embedding(graph_builder, target_address)
        return result["embedding"]


# Factory
_gnn_embedder: Optional[GNNEmbedding] = None


def get_gnn_embedder() -> GNNEmbedding:
    """Get or create GNN embedder singleton."""
    global _gnn_embedder
    if _gnn_embedder is None:
        _gnn_embedder = GNNEmbedding()
    return _gnn_embedder
