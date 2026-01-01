"""
ChainShield Auto-Rollback Monitor

Monitors model performance in production and automatically
rolls back to previous version if degradation detected.
"""

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger()


@dataclass
class RollbackEvent:
    """A rollback event record."""
    timestamp: float
    from_version: str
    to_version: str
    reason: str
    metrics_before: Dict[str, float]
    metrics_after: Dict[str, float] = field(default_factory=dict)


class AutoRollbackMonitor:
    """
    Monitors model performance and triggers automatic rollback.
    
    Features:
    - Tracks prediction accuracy via feedback
    - Detects sudden accuracy drops
    - Automatically rolls back to previous version
    - Configurable thresholds
    """
    
    # Thresholds
    WINDOW_SIZE = 100  # Predictions to track
    DEGRADATION_THRESHOLD = 0.15  # 15% accuracy drop triggers rollback
    MIN_SAMPLES_FOR_ROLLBACK = 50  # Minimum samples before checking
    
    def __init__(self, version_manager=None):
        """
        Initialize rollback monitor.
        
        Args:
            version_manager: ModelVersionManager instance
        """
        self.logger = logger.bind(module="auto_rollback")
        self.version_manager = version_manager
        
        # Tracking
        self.predictions: deque = deque(maxlen=self.WINDOW_SIZE)
        self.feedback: Dict[str, int] = {}  # prediction_id -> actual_label
        
        # State
        self.current_version: Optional[str] = None
        self.baseline_accuracy: float = 0.9  # Will be updated
        self.current_accuracy: float = 0.0
        self.rollback_events: List[RollbackEvent] = []
        
        # Control
        self.auto_rollback_enabled: bool = True
        self.last_check_time: float = 0
        self.check_interval_seconds: float = 60
    
    def set_version_manager(self, manager) -> None:
        """Set the version manager."""
        self.version_manager = manager
        self.logger.info("version_manager_attached")
    
    def set_baseline(self, accuracy: float, version: str) -> None:
        """
        Set baseline performance for current model.
        
        Args:
            accuracy: Expected accuracy
            version: Model version
        """
        self.baseline_accuracy = accuracy
        self.current_version = version
        self.logger.info(
            "baseline_set",
            accuracy=f"{accuracy:.2%}",
            version=version
        )
    
    def record_prediction(
        self,
        prediction_id: str,
        predicted_label: int,
        confidence: float
    ) -> None:
        """Record a prediction for tracking."""
        self.predictions.append({
            "id": prediction_id,
            "predicted": predicted_label,
            "confidence": confidence,
            "timestamp": time.time(),
        })
    
    def record_feedback(
        self,
        prediction_id: str,
        actual_label: int
    ) -> None:
        """
        Record actual label for a prediction.
        
        This triggers accuracy calculation and potential rollback.
        """
        self.feedback[prediction_id] = actual_label
        
        # Check for rollback
        self._check_for_degradation()
    
    def _calculate_accuracy(self) -> Optional[float]:
        """Calculate current accuracy from predictions with feedback."""
        matched = 0
        total = 0
        
        for pred in self.predictions:
            pred_id = pred["id"]
            if pred_id in self.feedback:
                actual = self.feedback[pred_id]
                if pred["predicted"] == actual:
                    matched += 1
                total += 1
        
        if total < self.MIN_SAMPLES_FOR_ROLLBACK:
            return None
        
        return matched / total
    
    def _check_for_degradation(self) -> None:
        """Check if model has degraded and needs rollback."""
        # Rate limit checks
        now = time.time()
        if now - self.last_check_time < self.check_interval_seconds:
            return
        self.last_check_time = now
        
        if not self.auto_rollback_enabled:
            return
        
        accuracy = self._calculate_accuracy()
        if accuracy is None:
            return
        
        self.current_accuracy = accuracy
        
        # Check for degradation
        drop = self.baseline_accuracy - accuracy
        
        if drop >= self.DEGRADATION_THRESHOLD:
            self.logger.warning(
                "degradation_detected",
                current=f"{accuracy:.2%}",
                baseline=f"{self.baseline_accuracy:.2%}",
                drop=f"{drop:.2%}"
            )
            self._trigger_rollback(accuracy, drop)
    
    def _trigger_rollback(self, current_accuracy: float, drop: float) -> bool:
        """
        Trigger automatic rollback to previous version.
        
        Returns:
            True if rollback successful
        """
        if not self.version_manager:
            self.logger.error("no_version_manager_for_rollback")
            return False
        
        # Get previous version
        versions = self.version_manager.list_versions()
        if len(versions) < 2:
            self.logger.error("no_previous_version_available")
            return False
        
        current_idx = None
        for i, v in enumerate(versions):
            if v.get("version") == self.current_version:
                current_idx = i
                break
        
        if current_idx is None or current_idx >= len(versions) - 1:
            self.logger.error("cannot_find_rollback_target")
            return False
        
        previous_version = versions[current_idx + 1]["version"]
        
        # Record event
        event = RollbackEvent(
            timestamp=time.time(),
            from_version=self.current_version,
            to_version=previous_version,
            reason=f"Accuracy dropped {drop:.2%} below baseline",
            metrics_before={
                "accuracy": current_accuracy,
                "baseline": self.baseline_accuracy,
            }
        )
        
        # Perform rollback
        try:
            success = self.version_manager.rollback_to_version(previous_version)
            
            if success:
                self.logger.info(
                    "auto_rollback_complete",
                    from_version=self.current_version,
                    to_version=previous_version
                )
                
                self.current_version = previous_version
                self.rollback_events.append(event)
                
                # Reset tracking
                self.predictions.clear()
                self.feedback.clear()
                
                return True
            else:
                self.logger.error("rollback_failed")
                return False
                
        except Exception as e:
            self.logger.error("rollback_exception", error=str(e))
            return False
    
    def force_rollback(self, to_version: str, reason: str = "manual") -> bool:
        """
        Force a rollback to specific version.
        
        Args:
            to_version: Target version
            reason: Reason for rollback
            
        Returns:
            True if successful
        """
        if not self.version_manager:
            return False
        
        event = RollbackEvent(
            timestamp=time.time(),
            from_version=self.current_version or "unknown",
            to_version=to_version,
            reason=reason,
            metrics_before={"accuracy": self.current_accuracy}
        )
        
        try:
            success = self.version_manager.rollback_to_version(to_version)
            if success:
                self.current_version = to_version
                self.rollback_events.append(event)
            return success
        except Exception:
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        return {
            "auto_rollback_enabled": self.auto_rollback_enabled,
            "current_version": self.current_version,
            "baseline_accuracy": round(self.baseline_accuracy, 4),
            "current_accuracy": round(self.current_accuracy, 4),
            "predictions_tracked": len(self.predictions),
            "feedback_received": len(self.feedback),
            "rollback_events": len(self.rollback_events),
            "degradation_threshold": self.DEGRADATION_THRESHOLD,
        }
    
    def get_rollback_history(self) -> List[Dict[str, Any]]:
        """Get history of rollback events."""
        return [
            {
                "timestamp": e.timestamp,
                "from_version": e.from_version,
                "to_version": e.to_version,
                "reason": e.reason,
            }
            for e in self.rollback_events
        ]


# Singleton
_auto_rollback_monitor: Optional[AutoRollbackMonitor] = None


def get_auto_rollback_monitor() -> AutoRollbackMonitor:
    """Get or create auto-rollback monitor singleton."""
    global _auto_rollback_monitor
    if _auto_rollback_monitor is None:
        _auto_rollback_monitor = AutoRollbackMonitor()
    return _auto_rollback_monitor
