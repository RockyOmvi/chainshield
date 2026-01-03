"""
ChainShield Real-time Monitoring

Prometheus-compatible metrics for production monitoring.

Metrics exposed:
- Request rate, latency, error rate
- Risk assessment counts by level
- Chain activity metrics
- Cache hit rates

Endpoint: GET /metrics
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
import structlog

logger = structlog.get_logger()


@dataclass
class MetricValue:
    """Single metric value with labels."""
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: str = "gauge"  # gauge, counter, histogram
    help_text: str = ""


class MetricsCollector:
    """
    Prometheus-compatible metrics collector.
    
    Usage:
        metrics = get_metrics_collector()
        
        # Increment counter
        metrics.increment("requests_total", labels={"endpoint": "/wallet"})
        
        # Record timing
        with metrics.timer("request_duration_seconds"):
            await process_request()
        
        # Get Prometheus format
        output = metrics.export_prometheus()
    """
    
    def __init__(self):
        self.logger = logger.bind(module="metrics")
        
        # Counters (monotonically increasing)
        self._counters: Dict[str, float] = defaultdict(float)
        self._counter_labels: Dict[str, Dict[str, str]] = {}
        
        # Gauges (can go up or down)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._gauge_labels: Dict[str, Dict[str, str]] = {}
        
        # Histograms (for latency)
        self._histogram_buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        
        # Metadata
        self._help_texts: Dict[str, str] = {}
        self._metric_types: Dict[str, str] = {}
        
        # Start time for uptime
        self._start_time = time.time()
        
        # Initialize default metrics
        self._init_default_metrics()
    
    def _init_default_metrics(self):
        """Initialize default application metrics."""
        self.register("chainshield_requests_total", "counter", 
                     "Total number of API requests")
        self.register("chainshield_request_duration_seconds", "histogram",
                     "Request duration in seconds")
        self.register("chainshield_risk_assessments_total", "counter",
                     "Total risk assessments performed")
        self.register("chainshield_blocked_addresses_total", "counter",
                     "Total addresses blocked (sanctions)")
        self.register("chainshield_active_chains", "gauge",
                     "Number of active blockchain connections")
        self.register("chainshield_cache_hits_total", "counter",
                     "Cache hit count")
        self.register("chainshield_cache_misses_total", "counter",
                     "Cache miss count")
        self.register("chainshield_uptime_seconds", "gauge",
                     "Application uptime in seconds")
        self.register("chainshield_error_total", "counter",
                     "Total error count")
    
    def register(self, name: str, metric_type: str, help_text: str):
        """Register a metric with type and help text."""
        self._metric_types[name] = metric_type
        self._help_texts[name] = help_text
    
    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """Create unique key for metric with labels."""
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def increment(self, name: str, value: float = 1, labels: Dict[str, str] = None):
        """Increment a counter."""
        key = self._make_key(name, labels)
        self._counters[key] += value
        if labels:
            self._counter_labels[key] = labels
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge value."""
        key = self._make_key(name, labels)
        self._gauges[key] = value
        if labels:
            self._gauge_labels[key] = labels
    
    def observe(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram observation."""
        key = self._make_key(name, labels)
        self._histograms[key].append(value)
        # Keep last 1000 observations
        if len(self._histograms[key]) > 1000:
            self._histograms[key] = self._histograms[key][-1000:]
    
    class Timer:
        """Context manager for timing."""
        def __init__(self, collector, name: str, labels: Dict[str, str] = None):
            self.collector = collector
            self.name = name
            self.labels = labels
            self.start = None
        
        def __enter__(self):
            self.start = time.time()
            return self
        
        def __exit__(self, *args):
            duration = time.time() - self.start
            self.collector.observe(self.name, duration, self.labels)
    
    def timer(self, name: str, labels: Dict[str, str] = None):
        """Create a timer context manager."""
        return self.Timer(self, name, labels)
    
    def record_request(self, endpoint: str, method: str, status: int, duration: float):
        """Record an API request with all metrics."""
        labels = {"endpoint": endpoint, "method": method, "status": str(status)}
        self.increment("chainshield_requests_total", labels=labels)
        self.observe("chainshield_request_duration_seconds", duration, 
                    labels={"endpoint": endpoint})
        
        if status >= 500:
            self.increment("chainshield_error_total", labels={"type": "server"})
        elif status >= 400:
            self.increment("chainshield_error_total", labels={"type": "client"})
    
    def record_assessment(self, risk_level: str, blocked: bool):
        """Record a risk assessment."""
        self.increment("chainshield_risk_assessments_total", 
                      labels={"level": risk_level})
        if blocked:
            self.increment("chainshield_blocked_addresses_total")
    
    def _compute_histogram_buckets(self, values: List[float]) -> Dict[str, float]:
        """Compute histogram bucket counts."""
        result = {}
        for bucket in self._histogram_buckets:
            count = sum(1 for v in values if v <= bucket)
            result[str(bucket)] = count
        result["+Inf"] = len(values)
        return result
    
    def export_prometheus(self) -> str:
        """Export all metrics in Prometheus text format."""
        lines = []
        
        # Update uptime
        self._gauges["chainshield_uptime_seconds"] = time.time() - self._start_time
        
        # Export counters
        for key, value in sorted(self._counters.items()):
            name = key.split("{")[0] if "{" in key else key
            if name in self._help_texts:
                lines.append(f"# HELP {name} {self._help_texts[name]}")
                lines.append(f"# TYPE {name} counter")
            lines.append(f"{key} {value}")
        
        # Export gauges
        for key, value in sorted(self._gauges.items()):
            name = key.split("{")[0] if "{" in key else key
            if name in self._help_texts:
                lines.append(f"# HELP {name} {self._help_texts[name]}")
                lines.append(f"# TYPE {name} gauge")
            lines.append(f"{key} {value}")
        
        # Export histograms
        for key, values in sorted(self._histograms.items()):
            name = key.split("{")[0] if "{" in key else key
            if name in self._help_texts:
                lines.append(f"# HELP {name} {self._help_texts[name]}")
                lines.append(f"# TYPE {name} histogram")
            
            if values:
                buckets = self._compute_histogram_buckets(values)
                for le, count in buckets.items():
                    lines.append(f'{name}_bucket{{le="{le}"}} {count}')
                lines.append(f"{name}_sum {sum(values)}")
                lines.append(f"{name}_count {len(values)}")
        
        return "\n".join(lines)
    
    def get_summary(self) -> Dict:
        """Get metrics summary as dictionary."""
        return {
            "uptime_seconds": time.time() - self._start_time,
            "total_requests": sum(v for k, v in self._counters.items() 
                                 if "requests_total" in k),
            "total_assessments": sum(v for k, v in self._counters.items() 
                                    if "risk_assessments" in k),
            "total_blocked": self._counters.get("chainshield_blocked_addresses_total", 0),
            "total_errors": sum(v for k, v in self._counters.items() 
                               if "error_total" in k),
        }


# Singleton
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create metrics collector singleton."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
