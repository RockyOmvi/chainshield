"""
ChainShield - AI-Powered Crypto Security Platform

Main FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.errors import register_exception_handlers
from app.core.rate_limit import RateLimitMiddleware
from app.middleware import RequestTracingMiddleware, SecurityHeadersMiddleware
from app.api.health import router as health_router
from app.api.v1 import api_v1_router


# =============================================================================
# Application Lifespan
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    from app.core.logging import get_logger
    logger = get_logger("main")
    
    logger.info(
        "application_starting",
        app=settings.app_name,
        env=settings.app_env,
        debug=settings.debug
    )
    
    # Initialize database (graceful fallback if not available)
    db_connected = False
    try:
        await init_db()
        db_connected = True
        logger.info("database_connected")
    except Exception as e:
        logger.warning(
            "database_connection_failed",
            error=str(e),
            fallback="in_memory_mode"
        )
    
    app.state.db_connected = db_connected
    
    # Initialize Redis for cache and rate limiting
    redis_client = None
    try:
        import redis.asyncio as aioredis
        redis_client = await aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        await redis_client.ping()
        
        # Set Redis client for cache and rate limiter
        from app.utils.cache import cache
        from app.core.rate_limit import rate_limiter
        await cache.set_redis(redis_client)
        await rate_limiter.set_redis(redis_client)
        
        logger.info("redis_connected", url=settings.redis_url[:20] + "...")
    except Exception as e:
        logger.warning(
            "redis_connection_failed",
            error=str(e),
            fallback="local_memory"
        )
    
    # Store redis client in app state for cleanup
    app.state.redis = redis_client
    
    # Initialize OpenTelemetry tracing
    if settings.otel_enabled:
        try:
            from app.core.tracing import setup_tracing
            setup_tracing(app, enable_instrumentations=True)
            logger.info("opentelemetry_initialized", endpoint=settings.otel_exporter_endpoint)
        except Exception as e:
            logger.warning("opentelemetry_init_failed", error=str(e))
    
    logger.info("application_started")
    
    yield
    
    # Shutdown
    logger.info("application_stopping")
    
    # Close Redis
    if app.state.redis:
        await app.state.redis.close()
        logger.info("redis_closed")
    
    # Close database
    await close_db()
    
    logger.info("application_stopped")


# =============================================================================
# Application Factory
# =============================================================================

def create_app() -> FastAPI:
    """
    Application factory.
    
    Creates and configures the FastAPI application.
    """
    
    # OpenAPI metadata for Swagger documentation
    openapi_tags = [
        {
            "name": "Health",
            "description": "System health and readiness checks",
        },
        {
            "name": "Risk Assessment",
            "description": "AI-powered wallet and transaction risk scoring",
        },
        {
            "name": "Wallets",
            "description": "Wallet analysis and profiling",
        },
        {
            "name": "Transactions",
            "description": "Transaction monitoring and analysis",
        },
        {
            "name": "Auth",
            "description": "Authentication and API key management",
        },
    ]
    
    app = FastAPI(
        title="ChainShield API",
        description="""
# ChainShield - AI-Powered Crypto Security Platform

## Overview
ChainShield provides enterprise-grade blockchain security through:
- 🔒 **Risk Assessment**: Real-time wallet and transaction risk scoring
- 🤖 **ML Models**: Ensemble of Random Forest + XGBoost trained on 478K samples
- 📊 **3-Layer Defense**: Rules → Heuristics → Machine Learning
- 🔍 **Explainability**: SHAP-based feature contribution analysis

## Authentication
All endpoints require an API key passed in the `X-API-Key` header.

```bash
curl -H "X-API-Key: your_api_key" https://api.chainshield.io/api/v1/risk/assess/wallet
```

## Rate Limits
- Standard tier: 100 requests/minute
- Premium tier: 1000 requests/minute

## Response Format
All responses follow the structure:
```json
{
    "success": true,
    "data": { ... },
    "error": null
}
```
        """,
        version="2.0.0",
        docs_url=f"{settings.api_v1_prefix}/docs",
        redoc_url=f"{settings.api_v1_prefix}/redoc",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        openapi_tags=openapi_tags,
        contact={
            "name": "ChainShield Support",
            "email": "support@chainshield.io",
            "url": "https://chainshield.io",
        },
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
        lifespan=lifespan,
    )
    
    # -------------------------------------------------------------------------
    # Middleware (order matters - first added = last executed)
    # -------------------------------------------------------------------------
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Rate limiting
    if settings.rate_limit_enabled:
        app.add_middleware(RateLimitMiddleware)
    
    # Request tracing (should be first to capture all requests)
    app.add_middleware(RequestTracingMiddleware)
    
    # -------------------------------------------------------------------------
    # Exception Handlers
    # -------------------------------------------------------------------------
    register_exception_handlers(app)
    
    # -------------------------------------------------------------------------
    # Routers
    # -------------------------------------------------------------------------
    
    # Health endpoints (no prefix)
    app.include_router(health_router)
    
    # API v1 endpoints
    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)
    
    return app


# =============================================================================
# Application Instance
# =============================================================================

app = create_app()


# =============================================================================
# Development: Run with uvicorn
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=1 if settings.reload else settings.workers,
        log_level=settings.log_level.lower(),
    )
