"""
ChainShield OpenTelemetry Tracing

Distributed tracing for observability:
- Request tracing across services
- Span creation for key operations
- Context propagation
- Export to OTLP backends (Jaeger, Tempo, etc.)
"""

from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# OpenTelemetry imports (optional - graceful degradation if not installed)
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.semconv.resource import ResourceAttributes
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    logger.info("opentelemetry_not_installed", message="Running without distributed tracing")


# =============================================================================
# Tracer Setup
# =============================================================================

_tracer: Optional[Any] = None


def setup_tracing(app=None, enable_instrumentations: bool = True):
    """
    Set up OpenTelemetry tracing.
    
    Call this during application startup.
    """
    global _tracer
    
    if not OTEL_AVAILABLE:
        logger.warning("tracing_disabled", reason="opentelemetry not installed")
        return
    
    if not settings.otel_enabled:
        logger.info("tracing_disabled", reason="OTEL_ENABLED=false")
        return
    
    # Create resource with service info
    resource = Resource.create({
        ResourceAttributes.SERVICE_NAME: settings.app_name,
        ResourceAttributes.SERVICE_VERSION: "0.1.0",
        ResourceAttributes.DEPLOYMENT_ENVIRONMENT: settings.app_env,
    })
    
    # Set up tracer provider
    provider = TracerProvider(resource=resource)
    
    # Configure exporter based on settings
    if settings.otel_exporter_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            
            exporter = OTLPSpanExporter(
                endpoint=settings.otel_exporter_endpoint,
                insecure=not settings.is_production
            )
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info(
                "tracing_exporter_configured",
                endpoint=settings.otel_exporter_endpoint
            )
        except ImportError:
            logger.warning("otlp_exporter_not_installed")
    
    # Set global tracer provider
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(__name__)
    
    # Auto-instrument libraries
    if enable_instrumentations and app:
        _setup_instrumentations(app)
    
    logger.info("tracing_initialized", service=settings.app_name)


def _setup_instrumentations(app):
    """Set up automatic instrumentations."""
    try:
        # FastAPI (HTTP requests)
        FastAPIInstrumentor.instrument_app(app)
        logger.debug("instrumented_fastapi")
    except Exception as e:
        logger.warning("instrumentation_failed", lib="fastapi", error=str(e))
    
    try:
        # HTTPX (outgoing HTTP requests)
        HTTPXClientInstrumentor().instrument()
        logger.debug("instrumented_httpx")
    except Exception as e:
        logger.warning("instrumentation_failed", lib="httpx", error=str(e))
    
    try:
        # Redis
        RedisInstrumentor().instrument()
        logger.debug("instrumented_redis")
    except Exception as e:
        logger.warning("instrumentation_failed", lib="redis", error=str(e))


def get_tracer():
    """Get the configured tracer or a no-op tracer."""
    global _tracer
    if _tracer:
        return _tracer
    
    if OTEL_AVAILABLE:
        return trace.get_tracer(__name__)
    
    # Return no-op tracer
    return NoOpTracer()


# =============================================================================
# No-Op Tracer (Fallback when OTEL not installed)
# =============================================================================

class NoOpSpan:
    """No-op span for when tracing is disabled."""
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass
    
    def set_attribute(self, key: str, value: Any):
        pass
    
    def set_status(self, status):
        pass
    
    def record_exception(self, exception):
        pass
    
    def add_event(self, name: str, attributes: dict = None):
        pass


class NoOpTracer:
    """No-op tracer for when OpenTelemetry is not installed."""
    
    def start_as_current_span(self, name: str, **kwargs):
        return NoOpSpan()
    
    def start_span(self, name: str, **kwargs):
        return NoOpSpan()


# =============================================================================
# Span Decorators
# =============================================================================

def traced(
    name: Optional[str] = None,
    attributes: Optional[dict] = None
):
    """
    Decorator to create a span for a function.
    
    Usage:
        @traced("wallet.analyze")
        async def analyze_wallet(address: str):
            ...
    """
    def decorator(func: Callable):
        span_name = name or f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


@contextmanager
def span(name: str, attributes: Optional[dict] = None):
    """
    Context manager for creating a span.
    
    Usage:
        with span("blockchain.fetch", {"address": address}):
            result = await fetch_data()
    """
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as s:
        if attributes:
            for key, value in attributes.items():
                s.set_attribute(key, value)
        yield s


def add_span_attribute(key: str, value: Any):
    """Add an attribute to the current span."""
    if OTEL_AVAILABLE:
        current_span = trace.get_current_span()
        if current_span:
            current_span.set_attribute(key, value)


def add_span_event(name: str, attributes: Optional[dict] = None):
    """Add an event to the current span."""
    if OTEL_AVAILABLE:
        current_span = trace.get_current_span()
        if current_span:
            current_span.add_event(name, attributes or {})


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "setup_tracing",
    "get_tracer",
    "traced",
    "span",
    "add_span_attribute",
    "add_span_event",
    "OTEL_AVAILABLE",
]
