"""
ChainShield Alert Model

Alert and notification models for:
- Risk alerts
- Compliance events
- User notifications
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Alert(Base):
    """Risk alert model for suspicious activity detection."""
    
    __tablename__ = "alerts"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    # Alert identity
    alert_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        index=True
    )
    
    # Owner
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True
    )
    
    # Target
    target_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False  # wallet, transaction
    )
    target_address: Mapped[str] = mapped_column(
        String(66),
        nullable=False,
        index=True
    )
    target_hash: Mapped[Optional[str]] = mapped_column(
        String(66),
        nullable=True
    )
    chain: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ethereum"
    )
    
    # Alert details
    alert_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False  # high_risk, mixer_detected, blacklist_match, etc.
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="medium"  # low, medium, high, critical
    )
    risk_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    
    # Description
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    
    # AI explanation
    ai_explanation: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Additional data (renamed from 'metadata' to avoid SQLAlchemy conflict)
    extra_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True
    )
    
    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="new"  # new, reviewed, dismissed, resolved
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    
    # Actions taken
    action_taken: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True  # blocked, flagged, reported, etc.
    )
    action_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    action_by: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True
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
    
    __table_args__ = (
        # User + status queries
        Index(
            "idx_alert_user_status",
            "user_id",
            "status",
            "created_at"
        ),
        # Severity-based queries
        Index(
            "idx_alert_severity",
            "severity",
            "created_at"
        ),
        # Unread alerts (partial index)
        Index(
            "idx_alert_unread",
            "user_id",
            "is_read",
            postgresql_where=text("is_read = false")
        ),
    )
    
    def __repr__(self) -> str:
        return f"<Alert {self.alert_id[:8]}... {self.alert_type}>"


class AlertRule(Base):
    """Custom alert rules defined by users."""
    
    __tablename__ = "alert_rules"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    # Owner
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True
    )
    
    # Rule definition
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Conditions (JSON for flexibility)
    conditions: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False
        # Example: {"risk_score": {"gte": 80}, "chain": "ethereum"}
    )
    
    # Actions
    actions: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False
        # Example: {"notify": ["email", "webhook"], "auto_block": true}
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )
    
    # Statistics
    trigger_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
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


class AuditLog(Base):
    """Audit log for compliance and security tracking."""
    
    __tablename__ = "audit_logs"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    # Actor
    user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        index=True
    )
    api_key_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True
    )
    
    # Action
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False  # login, logout, analyze, export, etc.
    )
    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False  # wallet, transaction, alert, user, etc.
    )
    resource_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    
    # Details
    details: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True
    )
    
    # Result
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="success"  # success, failure, error
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True
    )
    
    __table_args__ = (
        # User activity queries
        Index(
            "idx_audit_user_time",
            "user_id",
            "created_at"
        ),
        # Action-based queries
        Index(
            "idx_audit_action",
            "action",
            "created_at"
        ),
    )
