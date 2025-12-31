"""
ChainShield Risk Classifier

Main ML classifier for fraud detection.
Uses Random Forest for robustness and explainability.

Design:
- Trained offline on labeled fraud/legit data
- Loaded at startup for fast inference
- Provides probability scores and feature importance
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import structlog

from app.services.risk.config import risk_config
from app.services.risk.features import FeatureVector, WalletFeatureExtractor
from app.services.risk.ml.preprocessor import FeaturePreprocessor

logger = structlog.get_logger()


class RiskClassifier:
    """
    Random Forest classifier for blockchain risk assessment.
    
    Features:
    - Binary classification: fraud (1) vs legit (0)
    - Outputs probability of fraud [0, 1]
    - Provides feature importance for explainability
    - Graceful fallback when model unavailable
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        preprocessor: Optional[FeaturePreprocessor] = None
    ):
        """
        Initialize classifier.
        
        Args:
            model_path: Path to serialized model file
            preprocessor: Optional custom preprocessor
        """
        self.logger = logger.bind(module="risk_classifier")
        self.model = None
        self.preprocessor = preprocessor or FeaturePreprocessor()
        self.feature_extractor = WalletFeatureExtractor()
        self.is_loaded = False
        self.feature_names = WalletFeatureExtractor.FEATURE_NAMES
        
        # Try to load model
        model_path = model_path or risk_config.ml_config.classifier_path
        self._load_model(model_path)
    
    def _load_model(self, path: str) -> bool:
        """
        Load trained model from file.
        
        Returns True if successful, False otherwise.
        """
        try:
            model_file = Path(path)
            if model_file.exists():
                import joblib
                self.model = joblib.load(path)
                self.is_loaded = True
                self.logger.info("model_loaded", path=path)
                return True
            else:
                self.logger.warning(
                    "model_file_not_found",
                    path=path,
                    using_fallback=True
                )
                self._init_fallback_model()
                return False
        except Exception as e:
            self.logger.error("model_load_failed", error=str(e))
            self._init_fallback_model()
            return False
    
    def _init_fallback_model(self) -> None:
        """
        Initialize a simple fallback model.
        
        Uses heuristic scoring when ML model is unavailable.
        This ensures the system keeps working.
        """
        self.model = None
        self.is_loaded = True  # Mark as ready (using fallback)
        self.logger.info("fallback_model_initialized")
    
    def predict(
        self, 
        features: FeatureVector
    ) -> Tuple[float, List[Tuple[str, float]]]:
        """
        Predict risk score from features.
        
        Args:
            features: Extracted feature vector
            
        Returns:
            Tuple of (risk_score [0-100], top_factors)
        """
        if self.model is not None:
            return self._predict_with_model(features)
        else:
            return self._predict_fallback(features)
    
    def _predict_with_model(
        self, 
        features: FeatureVector
    ) -> Tuple[float, List[Tuple[str, float]]]:
        """Predict using trained model."""
        try:
            # Convert to array
            X = self.preprocessor.transform(features.features, self.feature_names)
            
            # Get probability
            proba = self.model.predict_proba([X])[0]
            fraud_prob = proba[1] if len(proba) > 1 else proba[0]
            
            # Convert to 0-100 scale
            risk_score = fraud_prob * 100
            
            # Get feature importance
            if hasattr(self.model, 'feature_importances_'):
                importances = self.model.feature_importances_
                top_factors = self._get_top_factors(
                    features.features, 
                    importances,
                    top_n=5
                )
            else:
                top_factors = []
            
            return risk_score, top_factors
            
        except Exception as e:
            self.logger.error("prediction_failed", error=str(e))
            return self._predict_fallback(features)
    
    def _predict_fallback(
        self, 
        features: FeatureVector
    ) -> Tuple[float, List[Tuple[str, float]]]:
        """
        Fallback prediction using simple heuristics.
        
        Used when ML model is unavailable.
        """
        score = risk_config.ml_config.fallback_score
        top_factors = []
        
        f = features.features
        
        # Age penalty
        age_hours = f.get("age_hours", 0)
        if age_hours < 24:
            age_penalty = 20 * (1 - age_hours / 24)
            score += age_penalty
            top_factors.append(("age_hours", age_penalty))
        
        # Mixer interaction penalty
        mixer_count = f.get("mixer_interaction_count", 0)
        if mixer_count > 0:
            mixer_penalty = min(mixer_count * 15, 40)
            score += mixer_penalty
            top_factors.append(("mixer_interaction_count", mixer_penalty))
        
        # High velocity penalty
        tx_per_hour = f.get("tx_per_hour_avg", 0)
        if tx_per_hour > 10:
            velocity_penalty = min(tx_per_hour * 2, 30)
            score += velocity_penalty
            top_factors.append(("tx_per_hour_avg", velocity_penalty))
        
        # Low entropy (bot behavior) penalty
        entropy = f.get("active_hours_entropy", 0.5)
        if entropy < 0.3:
            entropy_penalty = (0.3 - entropy) * 50
            score += entropy_penalty
            top_factors.append(("active_hours_entropy", entropy_penalty))
        
        # Cap score
        score = min(score, 100)
        
        return score, sorted(top_factors, key=lambda x: x[1], reverse=True)[:5]
    
    def _get_top_factors(
        self,
        features: Dict[str, float],
        importances: List[float],
        top_n: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Get top contributing factors for explainability.
        
        Combines feature importance with actual feature values.
        """
        paired = list(zip(self.feature_names, importances))
        sorted_features = sorted(paired, key=lambda x: x[1], reverse=True)
        
        result = []
        for name, importance in sorted_features[:top_n]:
            # Score contribution = importance * normalized value
            contribution = importance * 100
            result.append((name, round(contribution, 2)))
        
        return result
    
    def predict_batch(
        self, 
        feature_vectors: List[FeatureVector]
    ) -> List[Tuple[float, List[Tuple[str, float]]]]:
        """
        Batch prediction for efficiency.
        """
        return [self.predict(fv) for fv in feature_vectors]
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        if self.model is None:
            return {
                "type": "fallback_heuristic",
                "is_loaded": self.is_loaded,
                "feature_count": len(self.feature_names)
            }
        
        return {
            "type": type(self.model).__name__,
            "is_loaded": self.is_loaded,
            "feature_count": len(self.feature_names),
            "n_estimators": getattr(self.model, "n_estimators", None),
            "max_depth": getattr(self.model, "max_depth", None),
        }


def create_dummy_model(output_path: str) -> None:
    """
    Create a dummy model for testing.
    
    This is called during development/testing when no real model exists.
    The model predicts based on simple feature thresholds.
    """
    try:
        from sklearn.ensemble import RandomForestClassifier
        import numpy as np
        import joblib
        
        # Generate synthetic training data
        np.random.seed(42)
        n_samples = 1000
        n_features = len(WalletFeatureExtractor.FEATURE_NAMES)
        
        # Features: random with some structure
        X = np.random.randn(n_samples, n_features)
        
        # Labels: fraud if certain conditions met
        # This creates a learnable pattern
        y = (
            (X[:, 0] < -1) |  # Very new account
            (X[:, 5] > 2) |   # High volume spike
            (X[:, -4] > 0)    # Mixer interaction
        ).astype(int)
        
        # Train simple model
        model = RandomForestClassifier(
            n_estimators=50,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        model.fit(X, y)
        
        # Save
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, output_path)
        
        logger.info("dummy_model_created", path=output_path)
        
    except ImportError:
        logger.warning("sklearn_not_available", msg="Cannot create dummy model")
