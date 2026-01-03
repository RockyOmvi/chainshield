"""
ChainShield SLA Monitoring

Tracks and enforces Service Level Agreements:
- Uptime (target: 99.9%)
- Response time (P95 < 500ms)
- Error rate (target: < 0.1%)

Alerts on SLA violations.
"""

import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Deque, Dict, List, Optional, Tuple
import structlog

logger = structlog.get_logger()


@dataclass
class SLATarget:
    """SLA target configuration."""
    name: str
    description: str
    target_value: float
    unit: str
    warning_threshold: float  # Alert at this level
    critical_threshold: float  # Escalate at this level


# Default SLA Targets
DEFAULT_SLAS = {
    "uptime": SLATarget(
        name="uptime",
        description="Service availability",
        target_value=99.9,
        unit="percent",
        warning_threshold=99.5,
        critical_threshold=99.0
    ),
    "response_time_p95": SLATarget(
        name="response_time_p95",
        description="95th percentile response time",
        target_value=500,
        unit="ms",
        warning_threshold=750,
        critical_threshold=1000
    ),
    "error_rate": SLATarget(
        name="error_rate",
        description="Error rate percentage",
        target_value=0.1,
        unit="percent",
        warning_threshold=0.5,
        critical_threshold=1.0
    ),
    "assessment_accuracy": SLATarget(
        name="assessment_accuracy",
        description="Risk assessment accuracy",
        target_value=99.0,
        unit="percent",
        warning_threshold=95.0,
        critical_threshold=90.0
    )
}


@dataclass
class SLAStatus:
    """Current SLA status for a metric."""
    sla_name: str
    current_value: float
    target_value: float
    unit: str
    status: str  # "ok", "warning", "critical", "unknown"
    last_updated: datetime
    
    @property
    def is_met(self) -> bool:
        return self.status == "ok"


@dataclass
class UptimeRecord:
    """Record of uptime check."""
    timestamp: datetime
    is_up: bool
    response_time_ms: Optional[float] = None


class SLAMonitor:
    """
    Monitors SLA compliance and tracks service health.
    
    Usage:
        monitor = get_sla_monitor()
        
        # Record a request
        monitor.record_request(duration_ms=150, success=True)
        
        # Check SLA status
        status = monitor.get_all_sla_status()
    """
    
    # Keep last N records for calculation
    MAX_RECORDS = 10000
    
    # Uptime check interval
    UPTIME_CHECK_INTERVAL = 60  # seconds
    
    def __init__(self, sla_targets: Dict[str, SLATarget] = None):
        self.logger = logger.bind(module="sla_monitor")
        self.sla_targets = sla_targets or DEFAULT_SLAS
        
        # Metrics storage
        self._response_times: Deque[float] = deque(maxlen=self.MAX_RECORDS)
        self._request_results: Deque[bool] = deque(maxlen=self.MAX_RECORDS)
        self._uptime_records: Deque[UptimeRecord] = deque(maxlen=self.MAX_RECORDS)
        
        # Counters
        self._total_requests = 0
        self._total_errors = 0
        self._start_time = time.time()
        self._last_check_time = time.time()
        
        # Status tracking
        self._is_healthy = True
        self._last_downtime: Optional[datetime] = None
        
        self.logger.info("sla_monitor_initialized", 
                        targets=list(self.sla_targets.keys()))
    
    def record_request(
        self, 
        duration_ms: float, 
        success: bool,
        endpoint: str = None
    ) -> None:
        """Record a single request for SLA tracking."""
        self._total_requests += 1
        self._response_times.append(duration_ms)
        self._request_results.append(success)
        
        if not success:
            self._total_errors += 1
    
    def record_uptime_check(self, is_up: bool, response_time_ms: float = None) -> None:
        """Record an uptime check result."""
        record = UptimeRecord(
            timestamp=datetime.now(timezone.utc),
            is_up=is_up,
            response_time_ms=response_time_ms
        )
        self._uptime_records.append(record)
        
        if not is_up and self._is_healthy:
            self._is_healthy = False
            self._last_downtime = datetime.now(timezone.utc)
            self.logger.warning("service_down_detected")
        elif is_up and not self._is_healthy:
            self._is_healthy = True
            self.logger.info("service_recovered")
    
    def _calculate_uptime_percent(self) -> float:
        """Calculate uptime percentage from records."""
        if not self._uptime_records:
            return 100.0
        
        up_count = sum(1 for r in self._uptime_records if r.is_up)
        return (up_count / len(self._uptime_records)) * 100
    
    def _calculate_p95_response_time(self) -> float:
        """Calculate 95th percentile response time."""
        if not self._response_times:
            return 0.0
        
        sorted_times = sorted(self._response_times)
        p95_index = int(len(sorted_times) * 0.95)
        return sorted_times[min(p95_index, len(sorted_times) - 1)]
    
    def _calculate_error_rate(self) -> float:
        """Calculate error rate percentage."""
        if self._total_requests == 0:
            return 0.0
        return (self._total_errors / self._total_requests) * 100
    
    def _get_status(self, value: float, target: SLATarget) -> str:
        """Determine SLA status based on thresholds."""
        # For uptime and accuracy, higher is better
        if target.name in ["uptime", "assessment_accuracy"]:
            if value >= target.target_value:
                return "ok"
            elif value >= target.warning_threshold:
                return "warning"
            else:
                return "critical"
        # For response time and error rate, lower is better
        else:
            if value <= target.target_value:
                return "ok"
            elif value <= target.warning_threshold:
                return "warning"
            else:
                return "critical"
    
    def get_sla_status(self, sla_name: str) -> Optional[SLAStatus]:
        """Get status for a specific SLA."""
        target = self.sla_targets.get(sla_name)
        if not target:
            return None
        
        # Calculate current value based on SLA type
        if sla_name == "uptime":
            current = self._calculate_uptime_percent()
        elif sla_name == "response_time_p95":
            current = self._calculate_p95_response_time()
        elif sla_name == "error_rate":
            current = self._calculate_error_rate()
        else:
            current = 0.0
        
        status = self._get_status(current, target)
        
        return SLAStatus(
            sla_name=sla_name,
            current_value=round(current, 2),
            target_value=target.target_value,
            unit=target.unit,
            status=status,
            last_updated=datetime.now(timezone.utc)
        )
    
    def get_all_sla_status(self) -> List[SLAStatus]:
        """Get status for all configured SLAs."""
        return [
            self.get_sla_status(name)
            for name in self.sla_targets.keys()
            if self.get_sla_status(name) is not None
        ]
    
    def get_sla_violations(self) -> List[SLAStatus]:
        """Get list of current SLA violations."""
        return [
            status for status in self.get_all_sla_status()
            if status.status in ["warning", "critical"]
        ]
    
    def get_summary(self) -> Dict:
        """Get summary of SLA status."""
        all_status = self.get_all_sla_status()
        violations = self.get_sla_violations()
        
        return {
            "overall_healthy": len(violations) == 0,
            "uptime_seconds": time.time() - self._start_time,
            "total_requests": self._total_requests,
            "total_errors": self._total_errors,
            "sla_status": [
                {
                    "name": s.sla_name,
                    "value": s.current_value,
                    "target": s.target_value,
                    "status": s.status,
                    "unit": s.unit
                }
                for s in all_status
            ],
            "violations": [
                {
                    "name": v.sla_name,
                    "value": v.current_value,
                    "target": v.target_value,
                    "severity": v.status
                }
                for v in violations
            ]
        }
    
    def export_for_dashboard(self) -> Dict:
        """Export data formatted for dashboard display."""
        summary = self.get_summary()
        
        # Add time series data (last 100 points)
        response_times = list(self._response_times)[-100:]
        
        return {
            **summary,
            "response_time_history": response_times,
            "is_healthy": self._is_healthy,
            "last_downtime": self._last_downtime.isoformat() if self._last_downtime else None
        }


# Singleton
_sla_monitor: Optional[SLAMonitor] = None


def get_sla_monitor() -> SLAMonitor:
    """Get or create SLA monitor singleton."""
    global _sla_monitor
    if _sla_monitor is None:
        _sla_monitor = SLAMonitor()
    return _sla_monitor
