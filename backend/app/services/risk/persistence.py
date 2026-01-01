"""
ChainShield Risk Assessment Persistence

Database models and repository for storing risk assessments.
Provides audit trail for compliance and analysis.
"""

from datetime import datetime
from typing import Any, Dict, List
from sqlalchemy import Column, String, Float, Boolean, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.core.database import Base


class RiskAssessmentRecord(Base):
    """
    Database model for risk assessments.
    
    Stores every risk assessment for audit trail.
    """
    
    __tablename__ = "risk_assessments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Request info
    wallet_address = Column(String(42), nullable=False, index=True)
    request_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    request_source = Column(String(50))  # "api", "internal", "batch"
    api_key_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Assessment results
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String(20), nullable=False)  # low, medium, high, critical
    blocked = Column(Boolean, default=False)
    
    # Layer scores
    rule_score = Column(Float, default=0.0)
    heuristic_score = Column(Float, default=0.0)
    ml_score = Column(Float, default=0.0)
    
    # Details (JSON)
    risk_factors = Column(JSON, default=list)
    features_used = Column(JSON, default=dict)
    model_version = Column(String(20))
    
    # Performance
    processing_time_ms = Column(Float)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "wallet_address": self.wallet_address,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "blocked": self.blocked,
            "rule_score": self.rule_score,
            "heuristic_score": self.heuristic_score,
            "ml_score": self.ml_score,
            "risk_factors": self.risk_factors,
            "model_version": self.model_version,
            "processing_time_ms": self.processing_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RiskAssessmentRepository:
    """
    Repository for risk assessment persistence.
    
    Handles saving and querying assessments.
    """
    
    def __init__(self, db_session):
        """
        Initialize repository.
        
        Args:
            db_session: SQLAlchemy async session
        """
        self.db = db_session
    
    async def save(
        self,
        assessment: Any,  # RiskAssessment dataclass
        wallet_address: str,
        source: str = "api",
        api_key_id: str = None
    ) -> RiskAssessmentRecord:
        """
        Save a risk assessment.
        
        Args:
            assessment: RiskAssessment dataclass
            wallet_address: Wallet that was assessed
            source: Where the request came from
            api_key_id: API key used (if any)
            
        Returns:
            Created record
        """
        record = RiskAssessmentRecord(
            wallet_address=wallet_address.lower(),
            request_source=source,
            api_key_id=uuid.UUID(api_key_id) if api_key_id else None,
            risk_score=assessment.risk_score,
            risk_level=assessment.risk_level,
            blocked=assessment.blocked,
            rule_score=assessment.rule_score,
            heuristic_score=assessment.heuristic_score,
            ml_score=assessment.ml_score,
            risk_factors=[
                {"name": f.factor_name, "score": f.score, "description": f.description}
                for f in assessment.factors
            ],
            model_version=assessment.model_version,
            processing_time_ms=assessment.processing_time_ms,
        )
        
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        
        return record
    
    async def get_by_wallet(
        self,
        wallet_address: str,
        limit: int = 10
    ) -> List[RiskAssessmentRecord]:
        """Get assessments for a wallet."""
        from sqlalchemy import select
        
        query = (
            select(RiskAssessmentRecord)
            .where(RiskAssessmentRecord.wallet_address == wallet_address.lower())
            .order_by(RiskAssessmentRecord.created_at.desc())
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_recent(self, limit: int = 100) -> List[RiskAssessmentRecord]:
        """Get most recent assessments."""
        from sqlalchemy import select
        
        query = (
            select(RiskAssessmentRecord)
            .order_by(RiskAssessmentRecord.created_at.desc())
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_high_risk(self, limit: int = 50) -> List[RiskAssessmentRecord]:
        """Get high-risk assessments."""
        from sqlalchemy import select
        
        query = (
            select(RiskAssessmentRecord)
            .where(RiskAssessmentRecord.risk_level.in_(["high", "critical"]))
            .order_by(RiskAssessmentRecord.created_at.desc())
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get assessment statistics."""
        from sqlalchemy import func, select
        
        # Total count
        total_query = select(func.count(RiskAssessmentRecord.id))
        total = await self.db.execute(total_query)
        total_count = total.scalar() or 0
        
        # Blocked count
        blocked_query = (
            select(func.count(RiskAssessmentRecord.id))
            .where(RiskAssessmentRecord.blocked.is_(True))
        )
        blocked = await self.db.execute(blocked_query)
        blocked_count = blocked.scalar() or 0
        
        # Average score
        avg_query = select(func.avg(RiskAssessmentRecord.risk_score))
        avg = await self.db.execute(avg_query)
        avg_score = avg.scalar() or 0.0
        
        return {
            "total_assessments": total_count,
            "blocked_count": blocked_count,
            "block_rate": blocked_count / max(total_count, 1),
            "average_score": round(avg_score, 2),
        }
