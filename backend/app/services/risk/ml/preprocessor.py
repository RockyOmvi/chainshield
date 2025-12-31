"""
ChainShield Feature Preprocessor

Normalizes and transforms features for ML model input.
Handles missing values, scaling, and encoding.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import math
import structlog

logger = structlog.get_logger()


@dataclass
class ScalerStats:
    """Statistics for a single feature used in scaling."""
    mean: float = 0.0
    std: float = 1.0
    min_val: float = 0.0
    max_val: float = 1.0


class FeaturePreprocessor:
    """
    Preprocesses features for ML model consumption.
    
    Operations:
    1. Handle missing values (imputation)
    2. Log transform skewed features
    3. Standard scaling (z-score normalization)
    4. Clipping outliers
    
    Design: Stateless for inference, but can fit statistics from training data.
    """
    
    # Features that should be log-transformed (highly skewed)
    LOG_TRANSFORM_FEATURES = [
        "balance_eth",
        "total_received_eth",
        "total_sent_eth",
        "volume_24h_eth",
        "volume_7d_eth",
        "max_tx_value_eth",
    ]
    
    # Features that are already ratios [0, 1]
    RATIO_FEATURES = [
        "in_out_ratio",
        "self_transfer_ratio",
        "contract_interaction_ratio",
        "failed_tx_ratio",
        "counterparty_concentration",
        "active_hours_entropy",
        "weekend_tx_ratio",
        "night_tx_ratio",
        "burst_score",
        "round_number_tx_ratio",
        "dust_tx_ratio",
    ]
    
    # Default imputation values for missing features
    DEFAULT_VALUES = {
        "age_hours": 0.0,
        "age_days": 0.0,
        "balance_eth": 0.0,
        "tx_count_total": 0.0,
        "total_received_eth": 0.0,
        "total_sent_eth": 0.0,
        "in_out_ratio": 0.5,  # Neutral
        "active_hours_entropy": 0.5,  # Neutral
    }
    
    def __init__(self):
        self.logger = logger.bind(module="preprocessor")
        self.scaler_stats: Dict[str, ScalerStats] = {}
        self.feature_names: List[str] = []
        self.is_fitted = False
    
    def fit(
        self, 
        feature_matrix: List[Dict[str, float]],
        feature_names: List[str]
    ) -> None:
        """
        Fit scaler statistics from training data.
        
        Args:
            feature_matrix: List of feature dictionaries
            feature_names: Ordered list of feature names
        """
        self.feature_names = feature_names
        
        for name in feature_names:
            values = [f.get(name, 0.0) for f in feature_matrix]
            
            # Apply log transform before calculating stats
            if name in self.LOG_TRANSFORM_FEATURES:
                values = [math.log1p(v) for v in values]
            
            if values:
                mean_val = sum(values) / len(values)
                variance = sum((x - mean_val) ** 2 for x in values) / len(values)
                std_val = math.sqrt(variance) if variance > 0 else 1.0
                
                self.scaler_stats[name] = ScalerStats(
                    mean=mean_val,
                    std=std_val,
                    min_val=min(values),
                    max_val=max(values)
                )
            else:
                self.scaler_stats[name] = ScalerStats()
        
        self.is_fitted = True
        self.logger.info("preprocessor_fitted", feature_count=len(feature_names))
    
    def transform(
        self, 
        features: Dict[str, float],
        feature_names: Optional[List[str]] = None
    ) -> List[float]:
        """
        Transform features to normalized array.
        
        Args:
            features: Raw feature dictionary
            feature_names: Feature order (uses fitted order if not provided)
            
        Returns:
            Normalized feature array
        """
        names = feature_names or self.feature_names
        result = []
        
        for name in names:
            # Get value with default imputation
            value = features.get(name, self.DEFAULT_VALUES.get(name, 0.0))
            
            # Apply log transform if needed
            if name in self.LOG_TRANSFORM_FEATURES:
                value = math.log1p(value)
            
            # Apply scaling if fitted
            if self.is_fitted and name in self.scaler_stats:
                stats = self.scaler_stats[name]
                if stats.std > 0:
                    value = (value - stats.mean) / stats.std
                # Clip to prevent extreme outliers
                value = max(-5.0, min(5.0, value))
            elif name in self.RATIO_FEATURES:
                # Ratios are already [0, 1], just clip
                value = max(0.0, min(1.0, value))
            
            result.append(value)
        
        return result
    
    def inverse_transform(
        self, 
        values: List[float],
        feature_names: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """
        Convert normalized array back to feature dictionary.
        
        Useful for explainability.
        """
        names = feature_names or self.feature_names
        result = {}
        
        for name, value in zip(names, values):
            # Reverse scaling
            if self.is_fitted and name in self.scaler_stats:
                stats = self.scaler_stats[name]
                value = value * stats.std + stats.mean
            
            # Reverse log transform
            if name in self.LOG_TRANSFORM_FEATURES:
                value = math.expm1(value)
            
            result[name] = value
        
        return result
    
    def get_feature_importance_names(self, importances: List[float]) -> List[Tuple[str, float]]:
        """
        Pair feature importances with names, sorted by importance.
        """
        paired = list(zip(self.feature_names, importances))
        return sorted(paired, key=lambda x: abs(x[1]), reverse=True)
    
    def save(self, path: str) -> None:
        """Save preprocessor state."""
        import json
        
        state = {
            "feature_names": self.feature_names,
            "scaler_stats": {
                name: {
                    "mean": stats.mean,
                    "std": stats.std,
                    "min_val": stats.min_val,
                    "max_val": stats.max_val
                }
                for name, stats in self.scaler_stats.items()
            },
            "is_fitted": self.is_fitted
        }
        
        with open(path, "w") as f:
            json.dump(state, f, indent=2)
    
    @classmethod
    def load(cls, path: str) -> "FeaturePreprocessor":
        """Load preprocessor from saved state."""
        import json
        
        with open(path, "r") as f:
            state = json.load(f)
        
        preprocessor = cls()
        preprocessor.feature_names = state["feature_names"]
        preprocessor.scaler_stats = {
            name: ScalerStats(**stats)
            for name, stats in state["scaler_stats"].items()
        }
        preprocessor.is_fitted = state["is_fitted"]
        
        return preprocessor
