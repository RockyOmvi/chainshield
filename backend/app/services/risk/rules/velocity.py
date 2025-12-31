"""
ChainShield Velocity Rule

Detects abnormal transaction velocity and volume patterns.
Catches pump-and-dump, rug pulls, and wash trading.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import structlog

from app.services.risk.rules.base import RiskRule, RuleResult, RuleSeverity
from app.services.risk.config import risk_config

logger = structlog.get_logger()


class VelocityRule(RiskRule):
    """
    Rule that checks transaction velocity and volume anomalies.
    
    Checks:
    - Transactions per time window (minute, hour, day)
    - Volume spikes relative to history
    - Rapid divestment (quick exit after receiving funds)
    - New account high activity
    """
    
    def __init__(
        self,
        name: str = "velocity_check",
        enabled: bool = True,
        weight: float = 0.8
    ):
        super().__init__(name, enabled, weight)
        self.limits = risk_config.velocity_limits
    
    @property
    def description(self) -> str:
        return "Detects abnormal transaction velocity and volume patterns"
    
    def evaluate(
        self, 
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> RuleResult:
        """
        Evaluate velocity patterns.
        
        Uses features from context if available,
        otherwise calculates from raw transaction data.
        """
        if not self.enabled:
            return self._make_result(triggered=False)
        
        factors = []
        details = {}
        max_severity = RuleSeverity.INFO
        total_score = 0.0
        checks_triggered = 0
        
        # Get features or calculate
        features = context.get("features", {}) if context else {}
        transactions = data.get("transactions", [])
        
        # Check 1: Transaction velocity
        velocity_result = self._check_velocity(data, features)
        if velocity_result["triggered"]:
            factors.extend(velocity_result["factors"])
            total_score += velocity_result["score"]
            max_severity = max(max_severity, velocity_result["severity"])
            checks_triggered += 1
        
        # Check 2: Volume spike
        volume_result = self._check_volume_spike(data, features)
        if volume_result["triggered"]:
            factors.extend(volume_result["factors"])
            total_score += volume_result["score"]
            max_severity = max(max_severity, volume_result["severity"])
            checks_triggered += 1
        
        # Check 3: Rapid divestment
        divestment_result = self._check_rapid_divestment(data, transactions)
        if divestment_result["triggered"]:
            factors.extend(divestment_result["factors"])
            total_score += divestment_result["score"]
            max_severity = max(max_severity, divestment_result["severity"])
            checks_triggered += 1
        
        # Check 4: New account high activity
        new_account_result = self._check_new_account_activity(data, features)
        if new_account_result["triggered"]:
            factors.extend(new_account_result["factors"])
            total_score += new_account_result["score"]
            max_severity = max(max_severity, new_account_result["severity"])
            checks_triggered += 1
        
        if checks_triggered == 0:
            return self._make_result(triggered=False)
        
        # Average the scores from triggered checks
        final_score = min(total_score / max(checks_triggered, 1), 100)
        
        return self._make_result(
            triggered=True,
            severity=max_severity,
            score=final_score,
            message=f"{checks_triggered} velocity anomalies detected",
            details=details,
            factors=factors[:5]
        )
    
    def _check_velocity(
        self, 
        data: Dict[str, Any],
        features: Dict[str, float]
    ) -> Dict[str, Any]:
        """Check transaction velocity against thresholds."""
        result = {
            "triggered": False,
            "factors": [],
            "score": 0.0,
            "severity": RuleSeverity.INFO
        }
        
        # Get velocity from features or calculate
        tx_per_hour = features.get("tx_per_hour_avg", 0)
        if tx_per_hour == 0:
            # Calculate from transactions
            transactions = data.get("transactions", [])
            age_hours = features.get("age_hours", 1)
            if age_hours > 0 and transactions:
                tx_per_hour = len(transactions) / age_hours
        
        # Check thresholds
        if tx_per_hour >= self.limits.tx_per_hour_critical:
            result["triggered"] = True
            result["factors"].append(
                f"Critical velocity: {tx_per_hour:.1f} tx/hour (threshold: {self.limits.tx_per_hour_critical})"
            )
            result["score"] = 80.0
            result["severity"] = RuleSeverity.CRITICAL
        elif tx_per_hour >= self.limits.tx_per_hour_suspicious:
            result["triggered"] = True
            result["factors"].append(
                f"High velocity: {tx_per_hour:.1f} tx/hour (threshold: {self.limits.tx_per_hour_suspicious})"
            )
            result["score"] = 50.0
            result["severity"] = RuleSeverity.MEDIUM
        
        return result
    
    def _check_volume_spike(
        self, 
        data: Dict[str, Any],
        features: Dict[str, float]
    ) -> Dict[str, Any]:
        """Check for unusual volume spikes."""
        result = {
            "triggered": False,
            "factors": [],
            "score": 0.0,
            "severity": RuleSeverity.INFO
        }
        
        volume_24h = features.get("volume_24h_eth", 0)
        volume_7d = features.get("volume_7d_eth", 0)
        
        # Check absolute threshold
        if volume_24h >= self.limits.volume_24h_critical:
            result["triggered"] = True
            result["factors"].append(
                f"Extreme 24h volume: {volume_24h:.2f} ETH (threshold: {self.limits.volume_24h_critical})"
            )
            result["score"] = 70.0
            result["severity"] = RuleSeverity.HIGH
        
        # Check relative spike
        if volume_7d > 0:
            daily_avg = volume_7d / 7
            if daily_avg > 0:
                spike_ratio = volume_24h / daily_avg
                if spike_ratio >= self.limits.volume_spike_ratio:
                    result["triggered"] = True
                    result["factors"].append(
                        f"Volume spike: {spike_ratio:.1f}x normal (threshold: {self.limits.volume_spike_ratio}x)"
                    )
                    result["score"] = max(result["score"], 60.0)
                    result["severity"] = max(result["severity"], RuleSeverity.MEDIUM)
        
        return result
    
    def _check_rapid_divestment(
        self, 
        data: Dict[str, Any],
        transactions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check for rapid divestment pattern.
        
        This catches rug pulls: receive large amount, immediately send it all out.
        """
        result = {
            "triggered": False,
            "factors": [],
            "score": 0.0,
            "severity": RuleSeverity.INFO
        }
        
        if len(transactions) < 2:
            return result
        
        address = data.get("address", "").lower()
        window_minutes = self.limits.rapid_divestment_window_minutes
        threshold_pct = self.limits.rapid_divestment_threshold_pct
        
        # Sort by timestamp
        sorted_txs = sorted(
            transactions,
            key=lambda x: x.get("timestamp", "") or "",
            reverse=False
        )
        
        # Look for rapid divestment patterns
        for i, tx in enumerate(sorted_txs):
            # Find incoming transactions
            if tx.get("to", "").lower() != address:
                continue
            
            incoming_value = float(tx.get("value", 0))
            if incoming_value < 1.0:  # Ignore small amounts
                continue
            
            tx_time = tx.get("timestamp")
            if not tx_time:
                continue
            
            if isinstance(tx_time, str):
                tx_time = datetime.fromisoformat(tx_time.replace("Z", "+00:00"))
            
            # Check subsequent outgoing transactions
            outgoing_total = 0.0
            window_end = tx_time + timedelta(minutes=window_minutes)
            
            for j in range(i + 1, len(sorted_txs)):
                out_tx = sorted_txs[j]
                out_time = out_tx.get("timestamp")
                
                if not out_time:
                    continue
                
                if isinstance(out_time, str):
                    out_time = datetime.fromisoformat(out_time.replace("Z", "+00:00"))
                
                if out_time > window_end:
                    break
                
                if out_tx.get("from", "").lower() == address:
                    outgoing_total += float(out_tx.get("value", 0))
            
            # Check if divested threshold percentage
            if incoming_value > 0:
                divested_pct = (outgoing_total / incoming_value) * 100
                if divested_pct >= threshold_pct:
                    result["triggered"] = True
                    result["factors"].append(
                        f"Rapid divestment: {divested_pct:.1f}% of {incoming_value:.2f} ETH within {window_minutes}min"
                    )
                    result["score"] = 75.0
                    result["severity"] = RuleSeverity.HIGH
                    break  # One match is enough
        
        return result
    
    def _check_new_account_activity(
        self, 
        data: Dict[str, Any],
        features: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Check for high activity from new accounts.
        
        New accounts with high transaction volume are suspicious.
        """
        result = {
            "triggered": False,
            "factors": [],
            "score": 0.0,
            "severity": RuleSeverity.INFO
        }
        
        age_hours = features.get("age_hours", 0)
        tx_count = features.get("tx_count_total", 0)
        
        limits = risk_config.account_age_limits
        
        # New account (< 24h) with high activity
        if age_hours < limits.new_account_hours and tx_count > 10:
            result["triggered"] = True
            result["factors"].append(
                f"New account ({age_hours:.1f}h old) with {int(tx_count)} transactions"
            )
            result["score"] = limits.new_high_activity_penalty
            result["severity"] = RuleSeverity.MEDIUM
        
        # Young account (< 7 days) with very high activity
        elif age_hours < limits.young_account_days * 24 and tx_count > 50:
            result["triggered"] = True
            result["factors"].append(
                f"Young account ({age_hours/24:.1f} days old) with {int(tx_count)} transactions"
            )
            result["score"] = limits.young_high_activity_penalty
            result["severity"] = RuleSeverity.LOW
        
        return result
