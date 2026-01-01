"""
ChainShield Token Transfer Feature Extractor

Enhanced feature extraction for ERC-20/ERC-721 token activity.
Adds 15+ new features for better fraud detection.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import math
import structlog

logger = structlog.get_logger()


@dataclass
class TokenFeatures:
    """Extracted token-related features."""
    features: Dict[str, float]
    feature_names: List[str]
    token_count: int
    nft_count: int


class TokenFeatureExtractor:
    """
    Extracts features from token transfer activity.
    
    Features extracted:
    - ERC-20 token diversity
    - NFT activity patterns
    - Token concentration (Herfindahl index)
    - Spam token interaction
    - DEX activity signals
    - Airdrop/farming patterns
    """
    
    # Known spam token patterns
    SPAM_PATTERNS = [
        "airdrop", "free", "claim", "bonus", "reward",
        ".com", ".io", ".xyz", "visit", "http"
    ]
    
    # Known DEX routers
    DEX_ROUTERS = {
        "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",  # Uniswap V2
        "0xe592427a0aece92de3edee1f18e0157c05861564",  # Uniswap V3
        "0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f",  # SushiSwap
        "0x1111111254fb6c44bac0bed2854e76f90643097d",  # 1inch V3
    }
    
    def __init__(self):
        """Initialize token feature extractor."""
        self.logger = logger.bind(module="token_features")
    
    def extract(self, wallet_data: Dict[str, Any]) -> TokenFeatures:
        """
        Extract token-related features from wallet data.
        
        Args:
            wallet_data: Wallet data with token_transfers field
            
        Returns:
            TokenFeatures with extracted features
        """
        token_transfers = wallet_data.get("token_transfers", [])
        transactions = wallet_data.get("transactions", [])
        
        features = {}
        
        # Basic token counts
        features["token_transfer_count"] = len(token_transfers)
        
        # Token diversity
        unique_tokens = set()
        token_values = {}  # token -> total value
        
        for transfer in token_transfers:
            token_addr = transfer.get("token_address", "").lower()
            token_name = transfer.get("token_name", "").lower()
            value = float(transfer.get("value", 0))
            
            unique_tokens.add(token_addr)
            token_values[token_addr] = token_values.get(token_addr, 0) + value
        
        features["unique_token_count"] = len(unique_tokens)
        features["token_diversity_ratio"] = (
            len(unique_tokens) / max(len(token_transfers), 1)
        )
        
        # Token concentration (Herfindahl-Hirschman Index)
        total_value = sum(token_values.values())
        if total_value > 0:
            shares = [v / total_value for v in token_values.values()]
            hhi = sum(s ** 2 for s in shares)
            features["token_concentration_hhi"] = hhi
        else:
            features["token_concentration_hhi"] = 1.0
        
        # NFT detection (ERC-721/ERC-1155)
        nft_transfers = [
            t for t in token_transfers
            if t.get("token_type") in ["ERC-721", "ERC-1155", "nft"]
            or t.get("value", 0) == 1  # Single token often = NFT
        ]
        features["nft_transfer_count"] = len(nft_transfers)
        features["nft_ratio"] = len(nft_transfers) / max(len(token_transfers), 1)
        
        # Spam token detection
        spam_count = 0
        for transfer in token_transfers:
            token_name = transfer.get("token_name", "").lower()
            if any(pattern in token_name for pattern in self.SPAM_PATTERNS):
                spam_count += 1
        
        features["spam_token_count"] = spam_count
        features["spam_token_ratio"] = spam_count / max(len(token_transfers), 1)
        
        # DEX activity
        dex_interactions = 0
        for tx in transactions:
            to_addr = tx.get("to", "").lower()
            if to_addr in self.DEX_ROUTERS:
                dex_interactions += 1
        
        features["dex_interaction_count"] = dex_interactions
        features["dex_activity_ratio"] = dex_interactions / max(len(transactions), 1)
        
        # Airdrop farming patterns
        # (many small incoming transfers from unique sources)
        incoming = [t for t in token_transfers if t.get("direction") == "in"]
        unique_senders = set(t.get("from", "").lower() for t in incoming)
        
        features["incoming_token_count"] = len(incoming)
        features["unique_token_senders"] = len(unique_senders)
        features["airdrop_farming_score"] = (
            len(unique_senders) / max(len(incoming), 1) 
            if len(incoming) > 10 else 0
        )
        
        # Token velocity (transfers per day)
        timestamps = [t.get("timestamp") for t in token_transfers if t.get("timestamp")]
        if len(timestamps) >= 2:
            try:
                from datetime import datetime
                times = [datetime.fromisoformat(ts.replace("Z", "+00:00")) for ts in timestamps]
                time_span = (max(times) - min(times)).total_seconds() / 86400
                features["token_velocity"] = len(token_transfers) / max(time_span, 0.1)
            except Exception:
                features["token_velocity"] = 0.0
        else:
            features["token_velocity"] = 0.0
        
        # Wash trading signals (same tokens going back and forth)
        in_tokens = set(t.get("token_address", "").lower() for t in token_transfers if t.get("direction") == "in")
        out_tokens = set(t.get("token_address", "").lower() for t in token_transfers if t.get("direction") == "out")
        overlap = in_tokens & out_tokens
        
        features["wash_trading_score"] = (
            len(overlap) / max(len(unique_tokens), 1)
            if len(unique_tokens) > 5 else 0
        )
        
        feature_names = list(features.keys())
        
        self.logger.debug(
            "token_features_extracted",
            feature_count=len(features),
            token_count=len(unique_tokens),
            nft_count=len(nft_transfers)
        )
        
        return TokenFeatures(
            features=features,
            feature_names=feature_names,
            token_count=len(unique_tokens),
            nft_count=len(nft_transfers)
        )
    
    def get_feature_names(self) -> List[str]:
        """Get list of all token feature names."""
        return [
            "token_transfer_count",
            "unique_token_count",
            "token_diversity_ratio",
            "token_concentration_hhi",
            "nft_transfer_count",
            "nft_ratio",
            "spam_token_count",
            "spam_token_ratio",
            "dex_interaction_count",
            "dex_activity_ratio",
            "incoming_token_count",
            "unique_token_senders",
            "airdrop_farming_score",
            "token_velocity",
            "wash_trading_score",
        ]


# Singleton
_token_extractor: Optional[TokenFeatureExtractor] = None


def get_token_feature_extractor() -> TokenFeatureExtractor:
    """Get or create token feature extractor singleton."""
    global _token_extractor
    if _token_extractor is None:
        _token_extractor = TokenFeatureExtractor()
    return _token_extractor
