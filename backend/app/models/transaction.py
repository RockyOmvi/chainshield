"""
ChainShield Transaction Model

Transaction database model with:
- Partitioning support (by timestamp)
- Optimized indexes for common queries
- Risk tracking
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
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Transaction(Base):
    """
    Transaction model for storing blockchain transactions.
    
    Designed for partitioning by timestamp for efficient data retention.
    """
    
    __tablename__ = "transactions"
    
    # Primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    # Transaction identity
    tx_hash: Mapped[str] = mapped_column(
        String(66),
        unique=True,
        nullable=False,
        index=True
    )
    chain: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ethereum"
    )
    
    # Block info
    block_number: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True
    )
    block_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    
    # Addresses
    from_address: Mapped[str] = mapped_column(
        String(66),
        nullable=False,
        index=True
    )
    to_address: Mapped[Optional[str]] = mapped_column(
        String(66),
        nullable=True,
        index=True
    )
    
    # Value
    value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    value_usd: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    
    # Gas
    gas_used: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0
    )
    gas_price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    
    # Token transfer (if applicable)
    token_address: Mapped[Optional[str]] = mapped_column(
        String(66),
        nullable=True
    )
    token_symbol: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True
    )
    token_amount: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    
    # Transaction type
    tx_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="transfer"  # transfer, swap, mint, contract_call, etc.
    )
    method_id: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True
    )
    
    # Risk assessment
    risk_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    risk_flags: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=list
    )
    
    # Status
    is_success: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )
    is_internal: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    is_analyzed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    
    # Raw data (for debugging/reprocessing)
    raw_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # Composite indexes for common queries
    __table_args__ = (
        # Address + time queries
        Index(
            "idx_tx_from_time",
            "from_address",
            "block_timestamp"
        ),
        Index(
            "idx_tx_to_time",
            "to_address",
            "block_timestamp"
        ),
        # Risk-based queries
        Index(
            "idx_tx_risk",
            "risk_score",
            postgresql_where=text("risk_score > 50")
        ),
        # Chain + block for syncing
        Index(
            "idx_tx_chain_block",
            "chain",
            "block_number"
        ),
        # Unanalyzed transactions
        Index(
            "idx_tx_unanalyzed",
            "is_analyzed",
            postgresql_where=text("is_analyzed = false")
        ),
    )
    
    def __repr__(self) -> str:
        return f"<Transaction {self.tx_hash[:10]}... risk={self.risk_score}>"


class TransactionEdge(Base):
    """
    Transaction edge for graph analysis.
    Stores relationships between wallets based on transactions.
    """
    
    __tablename__ = "transaction_edges"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    from_address: Mapped[str] = mapped_column(
        String(66),
        nullable=False,
        index=True
    )
    to_address: Mapped[str] = mapped_column(
        String(66),
        nullable=False,
        index=True
    )
    chain: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )
    
    # Aggregated metrics
    tx_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1
    )
    total_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    first_tx_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    last_tx_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
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
        # Unique edge per address pair
        Index(
            "idx_edge_addresses",
            "from_address",
            "to_address",
            "chain",
            unique=True
        ),
    )
