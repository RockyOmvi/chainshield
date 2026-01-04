"""
ChainShield Database Models

SQLAlchemy models for persistent storage.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, 
    ForeignKey, Text, JSON, Enum as SQLEnum, Index
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

Base = declarative_base()


class UserTier(str, enum.Enum):
    """User subscription tiers."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class UserStatus(str, enum.Enum):
    """User account status."""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class User(Base):
    """User account model."""
    
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(255))
    
    # Account status
    status = Column(SQLEnum(UserStatus), default=UserStatus.PENDING)
    email_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime(timezone=True))
    
    # Subscription
    tier = Column(SQLEnum(UserTier), default=UserTier.FREE)
    stripe_customer_id = Column(String(255), index=True)
    stripe_subscription_id = Column(String(255))
    
    # Admin
    is_admin = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime(timezone=True))
    
    # Relationships
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecord", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.email}>"


class ApiKey(Base):
    """API key model for programmatic access."""
    
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Key info
    key_id = Column(String(32), unique=True, nullable=False, index=True)  # cs_xxx prefix
    key_hash = Column(String(255), nullable=False)  # SHA256 hash of full key
    name = Column(String(255), default="Default Key")
    
    # Permissions
    scopes = Column(JSON, default=list)  # ["read", "write", "admin"]
    
    # Status
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime(timezone=True))
    
    # Rate limits (override user tier)
    rate_limit_override = Column(Integer)  # requests per minute
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    __table_args__ = (
        Index("ix_api_keys_user_active", "user_id", "is_active"),
    )
    
    def __repr__(self):
        return f"<ApiKey {self.key_id}>"


class UsageRecord(Base):
    """API usage tracking for billing."""
    
    __tablename__ = "usage_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Usage period
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Counts
    requests_count = Column(Integer, default=0)
    assessments_count = Column(Integer, default=0)
    blocked_count = Column(Integer, default=0)
    
    # Billing
    tier = Column(SQLEnum(UserTier), nullable=False)
    overage_count = Column(Integer, default=0)
    
    # Relationships
    user = relationship("User", back_populates="usage_records")
    
    __table_args__ = (
        Index("ix_usage_user_period", "user_id", "period_start"),
    )
    
    def __repr__(self):
        return f"<UsageRecord {self.user_id} {self.period_start}>"


class Assessment(Base):
    """Risk assessment log for audit trail."""
    
    __tablename__ = "assessments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Request info
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"))
    
    # Address info
    address = Column(String(255), nullable=False, index=True)
    chain = Column(String(50), default="ethereum")
    
    # Results
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String(20), nullable=False)
    blocked = Column(Boolean, default=False)
    
    # Details
    factors = Column(JSON, default=list)
    entity_match = Column(String(255))
    
    # Performance
    response_time_ms = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index("ix_assessments_address_chain", "address", "chain"),
        Index("ix_assessments_blocked", "blocked", "created_at"),
    )
    
    def __repr__(self):
        return f"<Assessment {self.address} {self.risk_level}>"


class BlocklistEntry(Base):
    """Custom blocklist entries."""
    
    __tablename__ = "blocklist"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    address = Column(String(255), unique=True, nullable=False, index=True)
    chain = Column(String(50), default="all")
    reason = Column(Text)
    source = Column(String(100))  # "ofac", "manual", "ml"
    
    # Who added it
    added_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True))
    
    def __repr__(self):
        return f"<BlocklistEntry {self.address}>"


class WebhookSubscription(Base):
    """Webhook subscription for alerts."""
    
    __tablename__ = "webhook_subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    url = Column(String(500), nullable=False)
    secret = Column(String(255))  # For HMAC signing
    
    events = Column(JSON, default=list)  # ["high_risk", "blocked"]
    
    # Status
    is_active = Column(Boolean, default=True)
    failure_count = Column(Integer, default=0)
    last_triggered_at = Column(DateTime(timezone=True))
    last_failed_at = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    def __repr__(self):
        return f"<WebhookSubscription {self.url}>"
