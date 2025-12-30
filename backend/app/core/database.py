"""
ChainShield Database Module

Async PostgreSQL with:
- Connection pooling
- Session management
- Health checks
- Graceful shutdown
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Base Model
# =============================================================================

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


# =============================================================================
# Database Engine
# =============================================================================

class DatabaseManager:
    """
    Manages database connections and sessions.
    
    Features:
    - Async connection pooling
    - Automatic session cleanup
    - Health checks
    """
    
    def __init__(self):
        self._engine = None
        self._session_factory = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize database engine and session factory."""
        if self._initialized:
            return
        
        logger.info("database_initializing", url=settings.database_url[:30] + "...")
        
        self._engine = create_async_engine(
            settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout,
            pool_pre_ping=True,  # Verify connections before use
            echo=settings.debug and settings.app_env == "development",
        )
        
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        
        self._initialized = True
        logger.info("database_initialized")
    
    async def close(self) -> None:
        """Close database connections gracefully."""
        if self._engine:
            logger.info("database_closing")
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            self._initialized = False
            logger.info("database_closed")
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session with automatic cleanup.
        
        Usage:
            async with db.session() as session:
                result = await session.execute(query)
        """
        if not self._initialized:
            await self.initialize()
        
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    async def health_check(self) -> bool:
        """Check if database is accessible."""
        if not self._initialized:
            return False
        
        try:
            async with self.session() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error("database_health_check_failed", error=str(e))
            return False
    
    async def get_pool_status(self) -> dict:
        """Get connection pool status."""
        if not self._engine:
            return {"status": "not_initialized"}
        
        pool = self._engine.pool
        return {
            "status": "active",
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
        }


# =============================================================================
# Global Database Instance
# =============================================================================

db = DatabaseManager()


# =============================================================================
# Dependency Injection
# =============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.
    
    Usage:
        @app.get("/items")
        async def get_items(session: AsyncSession = Depends(get_db)):
            ...
    """
    async with db.session() as session:
        yield session


# =============================================================================
# Database Lifecycle
# =============================================================================

async def init_db() -> None:
    """
    Initialize database connection.
    
    Tables should be created via Alembic migrations.
    Auto-create is only for quick development testing.
    """
    await db.initialize()
    
    # Import all models to register them with Base.metadata
    from app.models import (  # noqa
        Wallet, Transaction, TransactionEdge,
        User, APIKey, RefreshToken,
        Alert, AlertRule, AuditLog,
    )
    
    # Don't auto-create tables - use Alembic migrations instead
    # This avoids sync/async conflicts with asyncpg
    logger.info(
        "database_models_registered",
        models_count=len(Base.metadata.tables)
    )


async def close_db() -> None:
    """Close database connections."""
    await db.close()
