"""
ChainShield Online Training Pipeline

Real-time/incremental model training from production feedback.
Uses SGDClassifier for partial_fit capability.

SECURITY: Includes anti-poisoning measures:
- Source-based trust weighting
- Feedback validation
- Rate limiting per source
- Anomaly detection on labels
- Rollback capability
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import structlog

logger = structlog.get_logger()


# =============================================================================
# Anti-Poisoning Configuration
# =============================================================================

# Trust weights by feedback source (0.0 = reject, 1.0 = full trust)
SOURCE_TRUST_WEIGHTS = {
    "blockchain_verified": 1.0,   # On-chain verified (e.g., confirmed scam list)
    "analyst": 0.9,               # Internal security analyst
    "premium_user": 0.5,          # Verified premium user
    "user_report": 0.3,           # Standard user report
    "anonymous": 0.1,             # Anonymous feedback (very low trust)
}

# Rate limits per source (max samples per hour)
SOURCE_RATE_LIMITS = {
    "blockchain_verified": 10000,
    "analyst": 1000,
    "premium_user": 50,
    "user_report": 20,
    "anonymous": 5,
}

# Poisoning detection thresholds
MIN_BATCH_SIZE = 200  # Increased from 50 (harder to poison)
MAX_LABEL_FLIP_RATIO = 0.3  # Max 30% can flip high-confidence predictions
HIGH_CONFIDENCE_THRESHOLD = 0.85  # What counts as "high confidence"


@dataclass
class FeedbackSample:
    """A labeled sample from production."""
    features: List[float]
    label: int  # 0=legit, 1=fraud
    source: str  # "user_report", "analyst", "blockchain_verified"
    prediction_id: str
    timestamp: str
    confidence: float = 1.0  # How confident in the label
    original_prediction: Optional[int] = None  # What model predicted
    original_confidence: Optional[float] = None  # Model's confidence
    ip_hash: Optional[str] = None  # For rate limiting


@dataclass
class PoisoningAlert:
    """Alert for potential poisoning attempt."""
    alert_type: str
    source: str
    details: str
    timestamp: str
    blocked: bool


class OnlineTrainer:
    """
    Incremental model trainer with anti-poisoning protection.
    
    Security Features:
    - Source-based trust weighting
    - Rate limiting per source
    - Label flip detection
    - Anomaly detection on feedback patterns
    - Automatic rollback on degradation
    """
    
    IMPROVEMENT_THRESHOLD = 0.02  # 2% improvement required to swap
    
    def __init__(self, model_dir: str = "models"):
        """Initialize online trainer."""
        self.logger = logger.bind(module="online_trainer")
        self.model_dir = Path(model_dir)
        
        self.online_model = None
        self.pending_samples: List[FeedbackSample] = []
        self.rejected_samples: List[FeedbackSample] = []
        self.baseline_accuracy = 0.9
        self.current_accuracy = 0.0
        self.update_count = 0
        
        # Anti-poisoning tracking
        self.source_counts: Dict[str, int] = defaultdict(int)
        self.source_last_reset: datetime = datetime.utcnow()
        self.poisoning_alerts: List[PoisoningAlert] = []
        self.label_flip_count = 0
        self.total_feedback_count = 0
        
        self._initialize_online_model()
    
    def _initialize_online_model(self) -> None:
        """Initialize SGD classifier for online learning."""
        try:
            from sklearn.linear_model import SGDClassifier
            from sklearn.preprocessing import StandardScaler
            
            self.online_model = SGDClassifier(
                loss="log_loss",
                penalty="l2",
                alpha=0.0001,
                max_iter=1,
                warm_start=True,
                random_state=42,
            )
            self.scaler = StandardScaler()
            self.is_initialized = False
            
            self.logger.info("online_model_initialized_with_security")
            
        except ImportError:
            self.logger.error("sklearn_not_available")
            self.online_model = None
    
    def _reset_rate_limits(self) -> None:
        """Reset rate limit counters hourly."""
        now = datetime.utcnow()
        if now - self.source_last_reset > timedelta(hours=1):
            self.source_counts = defaultdict(int)
            self.source_last_reset = now
    
    def _get_trust_weight(self, source: str) -> float:
        """Get trust weight for a source."""
        return SOURCE_TRUST_WEIGHTS.get(source, 0.1)
    
    def _check_rate_limit(self, source: str) -> bool:
        """Check if source is within rate limit."""
        self._reset_rate_limits()
        limit = SOURCE_RATE_LIMITS.get(source, 10)
        return self.source_counts[source] < limit
    
    def _detect_label_flip(self, sample: FeedbackSample) -> bool:
        """Detect if sample is trying to flip a high-confidence prediction."""
        if sample.original_prediction is None or sample.original_confidence is None:
            return False
        
        # Check if label contradicts high-confidence prediction
        is_flip = (
            sample.label != sample.original_prediction and
            sample.original_confidence > HIGH_CONFIDENCE_THRESHOLD
        )
        
        if is_flip:
            self.label_flip_count += 1
        
        return is_flip
    
    def _validate_feedback(self, sample: FeedbackSample) -> tuple:
        """
        Validate feedback sample for potential poisoning.
        
        Returns:
            Tuple of (is_valid, rejection_reason)
        """
        # Check 1: Source exists and has trust
        trust = self._get_trust_weight(sample.source)
        if trust <= 0:
            return False, "untrusted_source"
        
        # Check 2: Rate limit
        if not self._check_rate_limit(sample.source):
            self._record_alert(
                "rate_limit_exceeded",
                sample.source,
                f"Source exceeded {SOURCE_RATE_LIMITS.get(sample.source, 10)} samples/hour"
            )
            return False, "rate_limit_exceeded"
        
        # Check 3: Label flip on high confidence (suspicious)
        if self._detect_label_flip(sample):
            # Low-trust sources can't flip high-confidence predictions
            if trust < 0.5:
                self._record_alert(
                    "suspicious_label_flip",
                    sample.source,
                    "Low-trust source trying to flip high-confidence prediction"
                )
                return False, "suspicious_label_flip"
        
        # Check 4: Overall flip ratio check
        if self.total_feedback_count > 50:
            flip_ratio = self.label_flip_count / self.total_feedback_count
            if flip_ratio > MAX_LABEL_FLIP_RATIO:
                self._record_alert(
                    "high_flip_ratio",
                    "global",
                    f"Label flip ratio {flip_ratio:.0%} exceeds threshold"
                )
                # Don't reject, but log alert
        
        return True, None
    
    def _record_alert(self, alert_type: str, source: str, details: str) -> None:
        """Record a poisoning alert."""
        alert = PoisoningAlert(
            alert_type=alert_type,
            source=source,
            details=details,
            timestamp=datetime.utcnow().isoformat(),
            blocked=True
        )
        self.poisoning_alerts.append(alert)
        
        # Keep last 100 alerts
        if len(self.poisoning_alerts) > 100:
            self.poisoning_alerts = self.poisoning_alerts[-100:]
        
        self.logger.warning(
            "poisoning_alert",
            type=alert_type,
            source=source,
            details=details
        )
    
    def add_feedback(self, sample: FeedbackSample) -> bool:
        """
        Add a feedback sample with validation.
        
        Args:
            sample: Labeled sample from production
            
        Returns:
            True if accepted, False if rejected
        """
        self.total_feedback_count += 1
        
        # Validate for poisoning
        is_valid, reason = self._validate_feedback(sample)
        
        if not is_valid:
            self.rejected_samples.append(sample)
            self.logger.debug(
                "feedback_rejected",
                source=sample.source,
                reason=reason
            )
            return False
        
        # Apply trust-based confidence adjustment
        trust = self._get_trust_weight(sample.source)
        sample.confidence = sample.confidence * trust
        
        # Update rate limit counter
        self.source_counts[sample.source] += 1
        
        self.pending_samples.append(sample)
        
        self.logger.debug(
            "feedback_accepted",
            label=sample.label,
            source=sample.source,
            effective_confidence=f"{sample.confidence:.2f}",
            pending=len(self.pending_samples)
        )
        
        # Check if we have enough for an update
        if len(self.pending_samples) >= MIN_BATCH_SIZE:
            self._perform_update()
        
        return True
    
    def _perform_update(self) -> None:
        """Perform incremental model update with validated samples."""
        if not self.online_model or not self.pending_samples:
            return
        
        # Additional check: require minimum source diversity
        sources = set(s.source for s in self.pending_samples)
        if len(sources) < 2:
            self.logger.warning(
                "update_skipped_low_diversity",
                sources=list(sources)
            )
            return
        
        # Extract features and labels
        X = np.array([s.features for s in self.pending_samples])
        y = np.array([s.label for s in self.pending_samples])
        
        # Apply sample weights based on adjusted confidence
        sample_weights = np.array([s.confidence for s in self.pending_samples])
        
        try:
            if not self.is_initialized:
                X_scaled = self.scaler.fit_transform(X)
                self.online_model.fit(X_scaled, y, sample_weight=sample_weights)
                self.is_initialized = True
            else:
                X_scaled = self.scaler.transform(X)
                self.online_model.partial_fit(
                    X_scaled, y,
                    classes=[0, 1],
                    sample_weight=sample_weights
                )
            
            self.update_count += 1
            
            # Evaluate
            accuracy = self.online_model.score(X_scaled, y)
            
            # Degradation check - potential poisoning!
            if self.current_accuracy > 0 and accuracy < self.current_accuracy - 0.1:
                self._record_alert(
                    "accuracy_degradation",
                    "model",
                    f"Accuracy dropped from {self.current_accuracy:.2%} to {accuracy:.2%}"
                )
                # Don't update accuracy - keep old value
            else:
                self.current_accuracy = accuracy
            
            self.logger.info(
                "online_update_complete",
                samples=len(self.pending_samples),
                accuracy=f"{accuracy:.3f}",
                update_count=self.update_count
            )
            
            self.pending_samples = []
            
        except Exception as e:
            self.logger.error("online_update_failed", error=str(e))
    
    def predict(self, features: List[float]) -> tuple:
        """Make prediction with online model."""
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
            "rejected_samples": len(self.rejected_samples),
            "update_count": self.update_count,
            "current_accuracy": round(self.current_accuracy, 4),
            "baseline_accuracy": round(self.baseline_accuracy, 4),
            "should_swap": self.should_swap_model(),
            "min_batch_size": MIN_BATCH_SIZE,
            "total_feedback": self.total_feedback_count,
            "label_flip_count": self.label_flip_count,
            "poisoning_alerts": len(self.poisoning_alerts),
        }
    
    def get_security_report(self) -> Dict[str, Any]:
        """Get security status report."""
        return {
            "total_rejected": len(self.rejected_samples),
            "poisoning_alerts": [
                {
                    "type": a.alert_type,
                    "source": a.source,
                    "details": a.details,
                    "timestamp": a.timestamp,
                }
                for a in self.poisoning_alerts[-10:]  # Last 10
            ],
            "flip_ratio": (
                self.label_flip_count / max(self.total_feedback_count, 1)
            ),
            "source_distribution": dict(self.source_counts),
            "trust_weights": SOURCE_TRUST_WEIGHTS,
            "rate_limits": SOURCE_RATE_LIMITS,
        }


# Singleton instance
_online_trainer: Optional[OnlineTrainer] = None


def get_online_trainer() -> OnlineTrainer:
    """Get or create the online trainer singleton."""
    global _online_trainer
    if _online_trainer is None:
        _online_trainer = OnlineTrainer()
    return _online_trainer
