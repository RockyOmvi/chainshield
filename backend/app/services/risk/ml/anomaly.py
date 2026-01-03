"""
ChainShield Anomaly Detector

Isolation Forest for detecting novel/unknown threats.
No labeled data required - finds outliers automatically.

Key Use Cases:
- New attack patterns not in training data
- Unusual wallet behavior
- Novel transaction patterns
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import structlog

from app.services.risk.config import risk_config
from app.services.risk.features import FeatureVector
from app.services.risk.ml.preprocessor import FeaturePreprocessor

logger = structlog.get_logger()


class AnomalyDetector:
    """
    Isolation Forest anomaly detector.
    
    Isolation Forest works by:
    1. Randomly selecting a feature
    2. Randomly selecting a split value
    3. Recursively partitioning data
    4. Anomalies are isolated quickly (fewer splits)
    
    Advantages:
    - No labeled data needed
    - Fast training and inference
    - Works well with high-dimensional data
    - Linear time complexity
    """
    
    # Anomaly score thresholds
    THRESHOLD_CRITICAL = -0.5  # Very unusual
    THRESHOLD_HIGH = -0.3
    THRESHOLD_MEDIUM = -0.1
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        contamination: float = 0.1
    ):
        """
        Initialize anomaly detector.
        
        Args:
            model_path: Path to serialized model
            contamination: Expected proportion of outliers (for threshold)
        """
        self.logger = logger.bind(module="anomaly_detector")
        self.model = None
        self.contamination = contamination
        self.is_loaded = False
        
        # Try to load model
        model_path = model_path or risk_config.ml_config.isolation_forest_path
        self._load_model(model_path)
    
    def _load_model(self, path: str) -> bool:
        """Load trained Isolation Forest from file."""
        try:
            model_file = Path(path)
            if model_file.exists():
                import joblib
                self.model = joblib.load(path)
                self.is_loaded = True
                self.logger.info("anomaly_model_loaded", path=path)
                return True
            else:
                self.logger.warning(
                    "anomaly_model_not_found",
                    path=path,
                    using_fallback=True
                )
                return False
        except Exception as e:
            self.logger.error("anomaly_model_load_failed", error=str(e))
            return False
    
    def detect(
        self, 
        features: FeatureVector,
        preprocessor: Optional[FeaturePreprocessor] = None
    ) -> Tuple[float, str, List[str]]:
        """
        Detect if the sample is anomalous.
        
        Args:
            features: Extracted feature vector
            preprocessor: Optional preprocessor for normalization
            
        Returns:
            Tuple of:
            - anomaly_score: 0-100 (higher = more anomalous)
            - severity: CRITICAL/HIGH/MEDIUM/LOW
            - factors: Explanation factors
        """
        if self.model is None:
            return self._detect_fallback(features)
        
        try:
            # Get expected feature count from model
            n_features_model = getattr(self.model, 'n_features_in_', None)
            
            # Prepare features
            if preprocessor:
                X = [preprocessor.transform(features.features)]
            else:
                # Check if we need Kaggle adapter (model expects 45 features)
                if n_features_model == 45:
                    from app.services.risk.ml.kaggle_adapter import get_kaggle_adapter
                    adapter = get_kaggle_adapter()
                    X = [adapter.transform(features.features)]
                    self.logger.debug("using_kaggle_adapter", 
                                     input_features=len(features.features),
                                     output_features=45)
                else:
                    X = [list(features.features.values())]
            
            n_features_input = len(X[0])
            
            # Get anomaly score
            # Isolation Forest returns negative scores for outliers
            raw_score = self.model.decision_function(X)[0]
            
            # Convert to 0-100 scale (more anomalous = higher)
            # Raw score typically ranges from -0.5 (outlier) to 0.5 (normal)
            anomaly_score = max(0, min(100, (0.5 - raw_score) * 100))
            
            # Determine severity
            if raw_score < self.THRESHOLD_CRITICAL:
                severity = "CRITICAL"
            elif raw_score < self.THRESHOLD_HIGH:
                severity = "HIGH"
            elif raw_score < self.THRESHOLD_MEDIUM:
                severity = "MEDIUM"
            else:
                severity = "LOW"
            
            # Get factors
            factors = self._get_anomaly_factors(features.features, raw_score)
            
            return anomaly_score, severity, factors
            
        except Exception as e:
            self.logger.error("anomaly_detection_failed", error=str(e))
            return self._detect_fallback(features)
    
    def _detect_fallback(
        self, 
        features: FeatureVector
    ) -> Tuple[float, str, List[str]]:
        """
        Fallback anomaly detection using simple statistics.
        
        Used when model is unavailable.
        """
        f = features.features
        score = 0.0
        factors = []
        
        # Check for statistical outliers in key metrics
        
        # Extreme transaction velocity
        tx_per_hour = f.get("tx_per_hour_avg", 0)
        if tx_per_hour > 50:
            score += 25
            factors.append(f"Extreme velocity: {tx_per_hour:.1f} tx/hour")
        
        # Very high volume
        volume_24h = f.get("volume_24h_eth", 0)
        if volume_24h > 100:
            score += 20
            factors.append(f"High 24h volume: {volume_24h:.1f} ETH")
        
        # Bot-like behavior (low entropy)
        entropy = f.get("active_hours_entropy", 0.5)
        if entropy < 0.2:
            score += 15
            factors.append(f"Low time entropy: {entropy:.2f} (bot-like)")
        
        # Extreme counterparty concentration
        concentration = f.get("counterparty_concentration", 0)
        if concentration > 0.8:
            score += 15
            factors.append(f"High counterparty concentration: {concentration:.0%}")
        
        # Very new with high activity
        age_hours = f.get("age_hours", 0)
        tx_count = f.get("tx_count_total", 0)
        if age_hours < 24 and tx_count > 20:
            score += 20
            factors.append(f"New account high activity: {tx_count} tx in {age_hours:.1f}h")
        
        # Determine severity
        if score >= 60:
            severity = "CRITICAL"
        elif score >= 40:
            severity = "HIGH"
        elif score >= 20:
            severity = "MEDIUM"
        else:
            severity = "LOW"
        
        return score, severity, factors
    
    def _get_anomaly_factors(
        self,
        features: Dict[str, float],
        raw_score: float
    ) -> List[str]:
        """
        Identify which features contribute most to anomaly.
        
        Since Isolation Forest doesn't provide per-feature importance,
        we identify features that deviate most from typical values.
        """
        factors = []
        
        # Define typical ranges for key features
        typical_ranges = {
            "tx_per_hour_avg": (0, 5),
            "volume_24h_eth": (0, 10),
            "active_hours_entropy": (0.4, 0.8),
            "counterparty_concentration": (0, 0.5),
            "mixer_interaction_count": (0, 0),
            "failed_tx_ratio": (0, 0.1),
        }
        
        for name, (low, high) in typical_ranges.items():
            value = features.get(name, 0)
            if value < low or value > high:
                deviation = "above" if value > high else "below"
                factors.append(f"{name} {deviation} normal: {value:.2f}")
        
        return factors[:5]  # Limit to top 5
    
    def fit(self, feature_matrix: List[List[float]]) -> None:
        """
        Fit Isolation Forest on feature matrix.
        
        This is typically done offline during training.
        """
        try:
            from sklearn.ensemble import IsolationForest
            
            self.model = IsolationForest(
                n_estimators=100,
                contamination=self.contamination,
                random_state=42,
                n_jobs=-1
            )
            self.model.fit(feature_matrix)
            self.is_loaded = True
            
            self.logger.info(
                "isolation_forest_fitted",
                n_samples=len(feature_matrix)
            )
            
        except ImportError:
            self.logger.error("sklearn_not_available")
    
    def save(self, path: str) -> None:
        """Save model to file."""
        if self.model is None:
            self.logger.warning("no_model_to_save")
            return
        
        import joblib
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, path)
        self.logger.info("anomaly_model_saved", path=path)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        if self.model is None:
            return {
                "type": "fallback_heuristic",
                "is_loaded": False
            }
        
        return {
            "type": "IsolationForest",
            "is_loaded": self.is_loaded,
            "n_estimators": getattr(self.model, "n_estimators", None),
            "contamination": getattr(self.model, "contamination", None),
        }
