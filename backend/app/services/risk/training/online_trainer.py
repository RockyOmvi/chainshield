"""
ChainShield Online Training Pipeline

Real-time/incremental model training from production feedback.
Uses SGDClassifier for partial_fit capability.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import structlog

logger = structlog.get_logger()


@dataclass
class FeedbackSample:
    """A labeled sample from production."""
    features: List[float]
    label: int  # 0=legit, 1=fraud
    source: str  # "user_report", "analyst_review", "automated"
    prediction_id: str
    timestamp: str
    confidence: float = 1.0  # How confident in the label


class OnlineTrainer:
    """
    Incremental model trainer using SGDClassifier.
    
    Features:
    - partial_fit for incremental learning
    - Batch accumulation before updates
    - Automatic model swap when improved
    - Fallback to full model if online degrades
    """
    
    MIN_BATCH_SIZE = 50  # Minimum samples before update
    IMPROVEMENT_THRESHOLD = 0.02  # 2% improvement required to swap
    
    def __init__(self, model_dir: str = "models"):
        """Initialize online trainer."""
        self.logger = logger.bind(module="online_trainer")
        self.model_dir = Path(model_dir)
        
        self.online_model = None
        self.pending_samples: List[FeedbackSample] = []
        self.baseline_accuracy = 0.9  # Will be updated from main model
        self.current_accuracy = 0.0
        self.update_count = 0
        
        self._initialize_online_model()
    
    def _initialize_online_model(self) -> None:
        """Initialize SGD classifier for online learning."""
        try:
            from sklearn.linear_model import SGDClassifier
            from sklearn.preprocessing import StandardScaler
            
            self.online_model = SGDClassifier(
                loss="log_loss",  # Logistic regression
                penalty="l2",
                alpha=0.0001,
                max_iter=1,
                warm_start=True,
                random_state=42,
            )
            self.scaler = StandardScaler()
            self.is_initialized = False
            
            self.logger.info("online_model_initialized")
            
        except ImportError:
            self.logger.error("sklearn_not_available")
            self.online_model = None
    
    def add_feedback(self, sample: FeedbackSample) -> None:
        """
        Add a feedback sample to the pending queue.
        
        Args:
            sample: Labeled sample from production
        """
        self.pending_samples.append(sample)
        
        self.logger.debug(
            "feedback_added",
            label=sample.label,
            source=sample.source,
            pending=len(self.pending_samples)
        )
        
        # Check if we have enough for an update
        if len(self.pending_samples) >= self.MIN_BATCH_SIZE:
            self._perform_update()
    
    def _perform_update(self) -> None:
        """Perform incremental model update."""
        if not self.online_model or not self.pending_samples:
            return
        
        # Extract features and labels
        X = np.array([s.features for s in self.pending_samples])
        y = np.array([s.label for s in self.pending_samples])
        
        # Apply sample weights based on confidence
        sample_weights = np.array([s.confidence for s in self.pending_samples])
        
        try:
            # Scale features
            if not self.is_initialized:
                X_scaled = self.scaler.fit_transform(X)
                # Warm start with initial data
                self.online_model.fit(X_scaled, y, sample_weight=sample_weights)
                self.is_initialized = True
            else:
                X_scaled = self.scaler.transform(X)
                # Incremental update
                self.online_model.partial_fit(
                    X_scaled, y,
                    classes=[0, 1],
                    sample_weight=sample_weights
                )
            
            self.update_count += 1
            
            # Evaluate on recent samples
            accuracy = self.online_model.score(X_scaled, y)
            self.current_accuracy = accuracy
            
            self.logger.info(
                "online_update_complete",
                samples=len(self.pending_samples),
                accuracy=f"{accuracy:.3f}",
                update_count=self.update_count
            )
            
            # Clear pending samples
            self.pending_samples = []
            
        except Exception as e:
            self.logger.error("online_update_failed", error=str(e))
    
    def predict(self, features: List[float]) -> tuple:
        """
        Make prediction with online model.
        
        Returns:
            Tuple of (prediction, probability)
        """
        if not self.online_model or not self.is_initialized:
            return None, 0.0
        
        X = np.array([features])
        X_scaled = self.scaler.transform(X)
        
        prediction = self.online_model.predict(X_scaled)[0]
        probability = self.online_model.predict_proba(X_scaled)[0][1]
        
        return int(prediction), float(probability)
    
    def should_swap_model(self) -> bool:
        """Check if online model is better than baseline."""
        if self.current_accuracy <= 0:
            return False
        
        improvement = self.current_accuracy - self.baseline_accuracy
        return improvement > self.IMPROVEMENT_THRESHOLD
    
    def save_model(self, path: Optional[str] = None) -> str:
        """Save online model to disk."""
        import joblib
        
        if path is None:
            path = str(self.model_dir / "online_model.pkl")
        
        if self.online_model and self.is_initialized:
            joblib.dump({
                "model": self.online_model,
                "scaler": self.scaler,
                "accuracy": self.current_accuracy,
                "update_count": self.update_count,
                "timestamp": datetime.utcnow().isoformat(),
            }, path)
            
            self.logger.info("online_model_saved", path=path)
            return path
        
        return ""
    
    def load_model(self, path: Optional[str] = None) -> bool:
        """Load online model from disk."""
        import joblib
        
        if path is None:
            path = str(self.model_dir / "online_model.pkl")
        
        try:
            data = joblib.load(path)
            self.online_model = data["model"]
            self.scaler = data["scaler"]
            self.current_accuracy = data["accuracy"]
            self.update_count = data["update_count"]
            self.is_initialized = True
            
            self.logger.info("online_model_loaded", path=path)
            return True
            
        except Exception as e:
            self.logger.warning("online_model_load_failed", error=str(e))
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get training statistics."""
        return {
            "is_initialized": self.is_initialized,
            "pending_samples": len(self.pending_samples),
            "update_count": self.update_count,
            "current_accuracy": round(self.current_accuracy, 4),
            "baseline_accuracy": round(self.baseline_accuracy, 4),
            "should_swap": self.should_swap_model(),
        }


# Singleton instance
_online_trainer: Optional[OnlineTrainer] = None


def get_online_trainer() -> OnlineTrainer:
    """Get or create the online trainer singleton."""
    global _online_trainer
    if _online_trainer is None:
        _online_trainer = OnlineTrainer()
    return _online_trainer
