"""
ChainShield User Model

User and API key management with:
- JWT authentication
- API key generation
- Role-based access
"""

import secrets
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.config import settings


class User(Base):
    """User model for authentication and authorization."""
    
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    # Identity
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    
    # Profile
    name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    company: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    
    # Role-based access
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="user"  # user, admin, enterprise
    )
    permissions: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict
    )
    
    # Subscription/Plan
    plan: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="free"  # free, starter, pro, enterprise
    )
    plan_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Usage tracking
    api_calls_today: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    api_calls_month: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    last_api_call_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    def __repr__(self) -> str:
        return f"<User {self.email}>"
    
    @property
    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.role == "admin"
    
    @property
    def is_enterprise(self) -> bool:
        """Check if user has enterprise plan."""
        return self.plan == "enterprise"


class APIKey(Base):
    """API key model for programmatic access."""
    
    __tablename__ = "api_keys"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    # Key identity
    key_id: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
        index=True
    )
    key_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    key_prefix: Mapped[str] = mapped_column(
        String(12),
        nullable=False  # First 8 chars for identification
    )
    
    # Owner
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True
    )
    
    # Metadata
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    
    # Permissions
    scopes: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=list  # ["read:wallet", "write:alert", etc.]
    )
    
    # Rate limits (overrides user plan)
    rate_limit_override: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    
    # Usage
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    usage_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    __table_args__ = (
        Index(
            "idx_api_key_user",
            "user_id",
            "is_active"
        ),
    )
    
    def __repr__(self) -> str:
        return f"<APIKey {self.key_prefix}...>"
    
    @classmethod
    def generate_key(cls) -> tuple[str, str]:
        """
        Generate a new API key.
        
        Returns:
            (full_key, key_hash) - only return full_key to user once
        """
        import hashlib
        
        # Generate random key
        random_part = secrets.token_hex(24)
        full_key = f"{settings.api_key_prefix}{random_part}"
        
        # Hash for storage
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        
        return full_key, key_hash
    
    @classmethod
    def verify_key(cls, key: str, key_hash: str) -> bool:
        """Verify an API key against its hash."""
        import hashlib
        return hashlib.sha256(key.encode()).hexdigest() == key_hash
    
    @property
    def is_expired(self) -> bool:
        """Check if key is expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at.replace(tzinfo=None)


class RefreshToken(Base):
    """Refresh token model for JWT token rotation."""
    
    __tablename__ = "refresh_tokens"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    token_hash: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True
    )
    
    # Metadata
    device_info: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True
    )
    
    # Status
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
