"""
ChainShield Model Monitoring

Monitors model performance in production:
1. Feature drift detection
2. Prediction distribution monitoring
3. Performance degradation alerts
4. Feedback loop integration
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import structlog

logger = structlog.get_logger()


@dataclass
class DriftReport:
    """Report on feature drift."""
    feature_name: str
    baseline_mean: float
    current_mean: float
    baseline_std: float
    current_std: float
    drift_score: float  # 0-1, higher = more drift
    is_drifted: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MonitoringReport:
    """Complete monitoring report."""
    timestamp: str
    samples_analyzed: int
    features_monitored: int
    features_drifted: int
    overall_drift_score: float
    prediction_distribution: Dict[str, int]
    drift_details: List[Dict[str, Any]]
    alerts: List[str]


class ModelMonitor:
    """
    Monitors model health and data drift.
    
    Detects when incoming data differs significantly
    from training data, indicating model may need retraining.
    """
    
    # Drift thresholds
    DRIFT_THRESHOLD = 0.3  # Mean shift > 30% is concerning
    CRITICAL_THRESHOLD = 0.5  # Mean shift > 50% is critical
    
    def __init__(self, baseline_path: str = "models/drift_baseline.json"):
        """
        Initialize monitor.
        
        Args:
            baseline_path: Path to baseline statistics
        """
        self.baseline_path = Path(baseline_path)
        self.baseline = self._load_baseline()
        self.logger = logger.bind(module="model_monitor")
        
        # Tracking
        self.recent_predictions = []
        self.recent_features = []
        self.feedback_records = []
    
    def _load_baseline(self) -> Dict[str, Any]:
        """Load baseline statistics from training."""
        if self.baseline_path.exists():
            with open(self.baseline_path, "r") as f:
                return json.load(f)
        return {}
    
    def track_prediction(
        self, 
        features: np.ndarray,
        prediction: int,
        probability: float
    ) -> None:
        """
        Track a prediction for monitoring.
        
        Call this for each prediction in production.
        """
        self.recent_predictions.append({
            "prediction": prediction,
            "probability": probability,
            "timestamp": datetime.utcnow().isoformat()
        })
        self.recent_features.append(features)
        
        # Keep last 1000
        if len(self.recent_predictions) > 1000:
            self.recent_predictions = self.recent_predictions[-1000:]
            self.recent_features = self.recent_features[-1000:]
    
    def record_feedback(
        self,
        prediction_id: str,
        actual_label: int,
        prediction: int,
        user_feedback: Optional[str] = None
    ) -> None:
        """
        Record user feedback on a prediction.
        
        Used to track false positives/negatives.
        """
        self.feedback_records.append({
            "prediction_id": prediction_id,
            "actual": actual_label,
            "predicted": prediction,
            "correct": actual_label == prediction,
            "feedback": user_feedback,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Log errors
        if actual_label != prediction:
            self.logger.warning(
                "prediction_error_recorded",
                actual=actual_label,
                predicted=prediction,
                feedback=user_feedback
            )
    
    def check_drift(self, feature_names: List[str]) -> MonitoringReport:
        """
        Check for feature drift.
        
        Compares recent feature distributions to training baseline.
        
        Returns:
            MonitoringReport with drift analysis
        """
        if not self.recent_features or not self.baseline:
            return self._empty_report()
        
        # Stack recent features
        X = np.vstack(self.recent_features)
        
        drift_details = []
        drifted_count = 0
        total_drift = 0.0
        alerts = []
        
        for i, name in enumerate(feature_names):
            if i >= X.shape[1]:
                break
            
            # Get current stats
            current_mean = float(X[:, i].mean())
            current_std = float(X[:, i].std())
            
            # Get baseline stats
            baseline_mean = self.baseline.get("mean", [])[i] if i < len(self.baseline.get("mean", [])) else 0
            baseline_std = self.baseline.get("std", [])[i] if i < len(self.baseline.get("std", [])) else 1
            
            # Calculate drift score
            if baseline_std > 0:
                drift_score = abs(current_mean - baseline_mean) / baseline_std
            else:
                drift_score = 0.0
            
            drift_score = min(drift_score, 1.0)  # Cap at 1
            total_drift += drift_score
            
            is_drifted = drift_score > self.DRIFT_THRESHOLD
            if is_drifted:
                drifted_count += 1
            
            # Check for critical drift
            if drift_score > self.CRITICAL_THRESHOLD:
                alerts.append(f"CRITICAL: Feature '{name}' has drifted {drift_score*100:.0f}%")
            
            drift_details.append(DriftReport(
                feature_name=name,
                baseline_mean=round(baseline_mean, 4),
                current_mean=round(current_mean, 4),
                baseline_std=round(baseline_std, 4),
                current_std=round(current_std, 4),
                drift_score=round(drift_score, 4),
                is_drifted=is_drifted
            ).to_dict())
        
        # Prediction distribution
        pred_dist = {
            "fraud": sum(1 for p in self.recent_predictions if p["prediction"] == 1),
            "legit": sum(1 for p in self.recent_predictions if p["prediction"] == 0),
        }
        
        # Check prediction balance
        if pred_dist["fraud"] > pred_dist["legit"] * 0.5:
            alerts.append(f"WARNING: High fraud rate ({pred_dist['fraud']}/{len(self.recent_predictions)})")
        
        # Overall drift
        overall_drift = total_drift / max(len(feature_names), 1)
        
        if overall_drift > self.DRIFT_THRESHOLD:
            alerts.append(f"WARNING: Overall drift score is {overall_drift*100:.0f}%, consider retraining")
        
        return MonitoringReport(
            timestamp=datetime.utcnow().isoformat(),
            samples_analyzed=len(self.recent_features),
            features_monitored=len(feature_names),
            features_drifted=drifted_count,
            overall_drift_score=round(overall_drift, 4),
            prediction_distribution=pred_dist,
            drift_details=drift_details[:10],  # Top 10
            alerts=alerts
        )
    
    def _empty_report(self) -> MonitoringReport:
        """Return empty report when no data."""
        return MonitoringReport(
            timestamp=datetime.utcnow().isoformat(),
            samples_analyzed=0,
            features_monitored=0,
            features_drifted=0,
            overall_drift_score=0.0,
            prediction_distribution={"fraud": 0, "legit": 0},
            drift_details=[],
            alerts=["No data to analyze"]
        )
    
    def get_feedback_stats(self) -> Dict[str, Any]:
        """Get statistics from user feedback."""
        if not self.feedback_records:
            return {"total_feedback": 0}
        
        correct = sum(1 for r in self.feedback_records if r["correct"])
        false_positives = sum(1 for r in self.feedback_records 
                             if r["predicted"] == 1 and r["actual"] == 0)
        false_negatives = sum(1 for r in self.feedback_records 
                             if r["predicted"] == 0 and r["actual"] == 1)
        
        return {
            "total_feedback": len(self.feedback_records),
            "correct_predictions": correct,
            "accuracy": round(correct / len(self.feedback_records), 4),
            "false_positives": false_positives,
            "false_negatives": false_negatives,
        }
    
    def should_retrain(self) -> Tuple[bool, List[str]]:
        """
        Determine if model should be retrained.
        
        Returns:
            Tuple of (should_retrain, reasons)
        """
        reasons = []
        
        # Check feedback accuracy
        stats = self.get_feedback_stats()
        if stats.get("total_feedback", 0) >= 100:
            if stats.get("accuracy", 1.0) < 0.7:
                reasons.append(f"Low accuracy from feedback: {stats['accuracy']*100:.0f}%")
        
        # Check drift (need feature names)
        if len(self.recent_features) > 100 and self.baseline:
            # Simplified check
            X = np.vstack(self.recent_features)
            baseline_means = np.array(self.baseline.get("mean", []))
            if len(baseline_means) == X.shape[1]:
                current_means = X.mean(axis=0)
                drift = np.abs(current_means - baseline_means).mean()
                if drift > 0.3:
                    reasons.append(f"High feature drift detected: {drift:.2f}")
        
        return len(reasons) > 0, reasons


# Singleton for global access
_monitor: Optional[ModelMonitor] = None

def get_monitor() -> ModelMonitor:
    """Get or create the global model monitor."""
    global _monitor
    if _monitor is None:
        _monitor = ModelMonitor()
    return _monitor
