"""
ChainShield Wallet Model

Wallet database model with:
- Risk scoring fields
- Optimized indexes
- Activity tracking
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
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


class Wallet(Base):
    """
    Wallet model for storing wallet information and risk scores.
    
    Indexes are optimized for:
    - Address lookups (most common)
    - Risk-based queries
    - Time-based queries
    """
    
    __tablename__ = "wallets"
    
    # Primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    # Wallet identity
    address: Mapped[str] = mapped_column(
        String(66),
        unique=True,
        nullable=False,
        index=True
    )
    chain: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ethereum",
        index=True
    )
    
    # Risk assessment
    risk_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    risk_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="unknown"
    )
    risk_confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    
    # Risk tags (e.g., ["mixer", "scam", "phishing"])
    risk_tags: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=list
    )
    
    # AI explanation (cached)
    ai_explanation: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    ai_explanation_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Activity metrics
    total_tx_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    total_value_in: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    total_value_out: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    unique_counterparties: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    
    # Wallet age
    first_seen_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Flags
    is_contract: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    is_exchange: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    is_mixer: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    is_blacklisted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True
    )
    
    # Labels (e.g., {"entity": "Binance", "category": "exchange"})
    labels: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True
    )
    
    # Raw features for ML (cached)
    ml_features: Mapped[Optional[dict]] = mapped_column(
        JSONB,
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
    
    # Composite indexes for common queries
    __table_args__ = (
        # Fast risk lookups (partial index for high risk only)
        Index(
            "idx_wallet_risk_score",
            "risk_score",
            postgresql_where=text("risk_score > 70")
        ),
        # Chain + address for multi-chain support
        Index(
            "idx_wallet_chain_address",
            "chain",
            "address"
        ),
        # Time-based queries
        Index(
            "idx_wallet_last_seen",
            "last_seen_at"
        ),
        # Flag-based lookups
        Index(
            "idx_wallet_flags",
            "is_contract",
            "is_exchange",
            "is_mixer"
        ),
    )
    
    def __repr__(self) -> str:
        return f"<Wallet {self.address[:10]}... risk={self.risk_score}>"
    
    @property
    def is_high_risk(self) -> bool:
        """Check if wallet is high risk."""
        return self.risk_score >= 70
    
    @property
    def is_medium_risk(self) -> bool:
        """Check if wallet is medium risk."""
        return 40 <= self.risk_score < 70
    
    @property
    def age_days(self) -> Optional[int]:
        """Calculate wallet age in days."""
        if not self.first_seen_at:
            return None
        delta = datetime.utcnow() - self.first_seen_at.replace(tzinfo=None)
        return delta.days
