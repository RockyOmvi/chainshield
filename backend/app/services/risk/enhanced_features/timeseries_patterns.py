"""
ChainShield Time-Series Pattern Detector

Detects temporal fraud patterns in transaction sequences.
Identifies suspicious timing patterns that indicate fraud.
"""

import numpy as np
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger()


class TimeSeriesPatternDetector:
    """
    Detects temporal patterns in transaction sequences.
    
    Patterns detected:
    - Burst activity (rapid transactions)
    - Time-of-day anomalies
    - Periodicity (automated behavior)
    - Velocity spikes
    - Late-night activity
    """
    
    def __init__(self):
        """Initialize time-series detector."""
        self.logger = logger.bind(module="timeseries_patterns")
    
    def _parse_timestamp(self, ts: str) -> Optional[datetime]:
        """Parse timestamp string."""
        if not ts:
            return None
        try:
            # Handle various formats
            ts = ts.replace("Z", "+00:00")
            return datetime.fromisoformat(ts)
        except Exception:
            return None
    
    def _calculate_intervals(
        self,
        timestamps: List[datetime]
    ) -> np.ndarray:
        """Calculate intervals between transactions."""
        if len(timestamps) < 2:
            return np.array([])
        
        sorted_ts = sorted(timestamps)
        intervals = []
        for i in range(1, len(sorted_ts)):
            delta = (sorted_ts[i] - sorted_ts[i-1]).total_seconds()
            intervals.append(delta)
        
        return np.array(intervals)
    
    def detect_burst_pattern(
        self,
        timestamps: List[datetime],
        threshold_seconds: float = 60
    ) -> Dict[str, Any]:
        """
        Detect burst activity (many transactions in short time).
        
        Args:
            timestamps: Transaction timestamps
            threshold_seconds: Max interval for burst
            
        Returns:
            Burst pattern analysis
        """
        intervals = self._calculate_intervals(timestamps)
        
        if len(intervals) == 0:
            return {
                "burst_detected": False,
                "burst_score": 0.0,
                "max_burst_length": 0,
            }
        
        # Find burst sequences
        burst_lengths = []
        current_burst = 1
        
        for interval in intervals:
            if interval <= threshold_seconds:
                current_burst += 1
            else:
                if current_burst > 1:
                    burst_lengths.append(current_burst)
                current_burst = 1
        
        if current_burst > 1:
            burst_lengths.append(current_burst)
        
        max_burst = max(burst_lengths) if burst_lengths else 0
        burst_ratio = len([i for i in intervals if i <= threshold_seconds]) / len(intervals)
        
        return {
            "burst_detected": max_burst >= 3,
            "burst_score": burst_ratio,
            "max_burst_length": max_burst,
            "rapid_tx_ratio": burst_ratio,
        }
    
    def detect_time_of_day_anomaly(
        self,
        timestamps: List[datetime]
    ) -> Dict[str, Any]:
        """
        Detect unusual time-of-day patterns.
        
        Most fraud happens at unusual hours.
        """
        if len(timestamps) < 3:
            return {
                "late_night_ratio": 0.0,
                "entropy": 0.0,
            }
        
        hours = [ts.hour for ts in timestamps]
        
        # Late night activity (2 AM - 6 AM)
        late_night = [h for h in hours if 2 <= h <= 6]
        late_night_ratio = len(late_night) / len(hours)
        
        # Hour distribution entropy
        hour_counts = Counter(hours)
        total = len(hours)
        probabilities = [count / total for count in hour_counts.values()]
        entropy = -sum(p * np.log2(p + 1e-10) for p in probabilities)
        max_entropy = np.log2(24)  # Uniform distribution
        normalized_entropy = entropy / max_entropy
        
        # Peak activity concentration
        peak_hours = hour_counts.most_common(3)
        peak_concentration = sum(c for _, c in peak_hours) / total
        
        return {
            "late_night_ratio": late_night_ratio,
            "entropy": normalized_entropy,
            "peak_concentration": peak_concentration,
            "primary_active_hour": hour_counts.most_common(1)[0][0] if hour_counts else 0,
        }
    
    def detect_periodicity(
        self,
        timestamps: List[datetime]
    ) -> Dict[str, Any]:
        """
        Detect periodic/automated behavior.
        
        Automated bots often show regular intervals.
        """
        intervals = self._calculate_intervals(timestamps)
        
        if len(intervals) < 5:
            return {
                "is_periodic": False,
                "periodicity_score": 0.0,
            }
        
        # Calculate coefficient of variation
        mean_interval = np.mean(intervals)
        std_interval = np.std(intervals)
        
        if mean_interval == 0:
            return {"is_periodic": False, "periodicity_score": 0.0}
        
        cv = std_interval / mean_interval
        
        # Low CV = regular intervals = likely automated
        periodicity_score = max(0, 1 - cv)
        
        # Check for exact matches (very suspicious)
        rounded_intervals = [round(i, -1) for i in intervals]  # Round to 10s
        mode_count = Counter(rounded_intervals).most_common(1)
        exact_match_ratio = mode_count[0][1] / len(intervals) if mode_count else 0
        
        return {
            "is_periodic": periodicity_score > 0.7,
            "periodicity_score": periodicity_score,
            "interval_cv": cv,
            "exact_interval_ratio": exact_match_ratio,
            "mean_interval_seconds": mean_interval,
        }
    
    def detect_velocity_spikes(
        self,
        timestamps: List[datetime],
        window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Detect sudden velocity spikes.
        
        Fraudsters often show sudden activity increases.
        """
        if len(timestamps) < 10:
            return {
                "spike_detected": False,
                "max_spike_ratio": 0.0,
            }
        
        sorted_ts = sorted(timestamps)
        
        # Calculate tx count per window
        windows = []
        window_delta = timedelta(hours=window_hours)
        
        i = 0
        while i < len(sorted_ts):
            window_end = sorted_ts[i] + window_delta
            count = 0
            while i < len(sorted_ts) and sorted_ts[i] <= window_end:
                count += 1
                i += 1
            windows.append(count)
        
        if len(windows) < 2:
            return {"spike_detected": False, "max_spike_ratio": 0.0}
        
        # Find max spike (ratio of consecutive windows)
        spike_ratios = []
        for i in range(1, len(windows)):
            if windows[i-1] > 0:
                ratio = windows[i] / windows[i-1]
                spike_ratios.append(ratio)
        
        max_spike = max(spike_ratios) if spike_ratios else 1.0
        
        return {
            "spike_detected": max_spike > 5,
            "max_spike_ratio": max_spike,
            "window_count": len(windows),
            "max_window_tx": max(windows),
        }
    
    def extract_all_patterns(
        self,
        transactions: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Extract all time-series features.
        
        Args:
            transactions: List of transaction dicts with timestamps
            
        Returns:
            Dict of feature name to value
        """
        # Parse timestamps
        timestamps = []
        for tx in transactions:
            ts = tx.get("timestamp")
            parsed = self._parse_timestamp(ts)
            if parsed:
                timestamps.append(parsed)
        
        if len(timestamps) < 2:
            # Return default values for insufficient data
            return {
                "ts_burst_score": 0.0,
                "ts_max_burst_length": 0.0,
                "ts_rapid_tx_ratio": 0.0,
                "ts_late_night_ratio": 0.0,
                "ts_entropy": 0.0,
                "ts_peak_concentration": 0.0,
                "ts_periodicity_score": 0.0,
                "ts_interval_cv": 0.0,
                "ts_exact_interval_ratio": 0.0,
                "ts_spike_detected": 0.0,
                "ts_max_spike_ratio": 0.0,
            }
        
        # Run all detectors
        burst = self.detect_burst_pattern(timestamps)
        time_of_day = self.detect_time_of_day_anomaly(timestamps)
        periodicity = self.detect_periodicity(timestamps)
        velocity = self.detect_velocity_spikes(timestamps)
        
        # Combine into feature dict
        return {
            "ts_burst_score": burst.get("burst_score", 0.0),
            "ts_max_burst_length": float(burst.get("max_burst_length", 0)),
            "ts_rapid_tx_ratio": burst.get("rapid_tx_ratio", 0.0),
            "ts_late_night_ratio": time_of_day.get("late_night_ratio", 0.0),
            "ts_entropy": time_of_day.get("entropy", 0.0),
            "ts_peak_concentration": time_of_day.get("peak_concentration", 0.0),
            "ts_periodicity_score": periodicity.get("periodicity_score", 0.0),
            "ts_interval_cv": periodicity.get("interval_cv", 0.0),
            "ts_exact_interval_ratio": periodicity.get("exact_interval_ratio", 0.0),
            "ts_spike_detected": float(velocity.get("spike_detected", False)),
            "ts_max_spike_ratio": min(velocity.get("max_spike_ratio", 0.0), 100),
        }
    
    def get_feature_names(self) -> List[str]:
        """Get list of time-series feature names."""
        return [
            "ts_burst_score",
            "ts_max_burst_length",
            "ts_rapid_tx_ratio",
            "ts_late_night_ratio",
            "ts_entropy",
            "ts_peak_concentration",
            "ts_periodicity_score",
            "ts_interval_cv",
            "ts_exact_interval_ratio",
            "ts_spike_detected",
            "ts_max_spike_ratio",
        ]


# Singleton
_ts_detector: Optional[TimeSeriesPatternDetector] = None


def get_timeseries_detector() -> TimeSeriesPatternDetector:
    """Get or create time-series detector singleton."""
    global _ts_detector
    if _ts_detector is None:
        _ts_detector = TimeSeriesPatternDetector()
    return _ts_detector
