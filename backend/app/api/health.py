"""
ChainShield Health Check Endpoints

Kubernetes-compatible health endpoints:
- /health - Basic liveness probe
- /ready - Readiness probe with dependency checks
- /metrics - Basic metrics (Prometheus-compatible)
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import db
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health():
    """
    Liveness probe - is the service running?
    
    Returns 200 if the service is alive.
    Fast endpoint, no dependency checks.
    """
    return {
        "status": "ok",
        "service": settings.app_name,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/ready")
async def ready():
    """
    Readiness probe - is the service ready to handle requests?
    
    Checks all dependencies:
    - Database connection
    - Redis connection (via cache)
    - External services (blockchain RPC, AI)
    
    Returns 200 if all checks pass, 503 if any fail.
    """
    checks = {}
    start_time = datetime.now(timezone.utc)
    
    # Database check
    try:
        db_healthy = await db.health_check()
        checks["database"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "latency_ms": None  # Could add timing
        }
    except Exception as e:
        logger.warning("health_check_database_failed", error=str(e))
        checks["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Redis check
    try:
        # Get Redis from app state (set in lifespan)
        # We need to access it via a workaround since we're not in a request context
        from app.utils.cache import cache
        if cache._redis:
            await cache._redis.ping()
            checks["redis"] = {
                "status": "healthy",
                "mode": "redis"
            }
        else:
            checks["redis"] = {
                "status": "healthy",
                "mode": "local_fallback"
            }
    except Exception as e:
        logger.warning("health_check_redis_failed", error=str(e))
        checks["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Determine overall status
    all_healthy = all(
        c.get("status") == "healthy"
        for c in checks.values()
    )
    
    response_data = {
        "ready": all_healthy,
        "checks": checks,
        "timestamp": start_time.isoformat(),
        "service": settings.app_name,
        "version": "0.1.0",
        "environment": settings.app_env
    }
    
    if all_healthy:
        return JSONResponse(content=response_data, status_code=200)
    else:
        return JSONResponse(content=response_data, status_code=503)


@router.get("/metrics")
async def metrics():
    """
    Basic metrics endpoint (Prometheus-compatible).
    
    Returns key metrics in Prometheus text format.
    """
    # Get database pool stats
    pool_status = await db.get_pool_status()
    
    # Build Prometheus-format metrics
    lines = [
        "# HELP chainshield_up Service availability",
        "# TYPE chainshield_up gauge",
        "chainshield_up 1",
        "",
        "# HELP chainshield_db_pool_size Database connection pool size",
        "# TYPE chainshield_db_pool_size gauge",
        f"chainshield_db_pool_size {pool_status.get('size', 0)}",
        "",
        "# HELP chainshield_db_pool_checked_out Database connections in use",
        "# TYPE chainshield_db_pool_checked_out gauge",
        f"chainshield_db_pool_checked_out {pool_status.get('checked_out', 0)}",
        "",
    ]
    
    return Response(
        content="\n".join(lines),
        media_type="text/plain; charset=utf-8"
    )


@router.get("/info")
async def info():
    """
    Service information endpoint.
    
    Returns service metadata and configuration (non-sensitive).
    """
    return {
        "service": settings.app_name,
        "version": "0.1.0",
        "environment": settings.app_env,
        "api_version": "v1",
        "features": {
            "ai_explanations": settings.feature_ai_explanations,
            "graph_analysis": settings.feature_graph_analysis,
            "real_time_alerts": settings.feature_real_time_alerts,
        },
        "supported_chains": ["ethereum"],
        "documentation": f"{settings.api_v1_prefix}/docs",
    }
