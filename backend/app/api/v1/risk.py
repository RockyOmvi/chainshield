"""
ChainShield Risk Assessment API

API endpoints for blockchain address and transaction risk assessment.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from fastapi import APIRouter, Depends, HTTPException, status
import structlog

from app.api.deps import get_api_key_user
from app.services.risk import get_risk_engine


router = APIRouter(prefix="/risk", tags=["risk"])
logger = structlog.get_logger()


# Request/Response Schemas

class WalletRiskRequest(BaseModel):
    """Request for wallet risk assessment."""
    address: str = Field(..., description="Ethereum address to assess")
    chain: str = Field(default="ethereum", description="Blockchain network")
    include_transactions: bool = Field(default=True, description="Include transaction history in analysis")
    
    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        """Validate Ethereum address format."""
        v = v.strip().lower()
        if not v.startswith("0x"):
            raise ValueError("Address must start with 0x")
        if len(v) != 42:
            raise ValueError("Address must be 42 characters (including 0x)")
        # Check hex characters
        try:
            int(v, 16)
        except ValueError:
            raise ValueError("Address must be valid hexadecimal")
        return v


class TransactionRiskRequest(BaseModel):
    """Request for transaction risk assessment."""
    tx_hash: Optional[str] = Field(None, description="Transaction hash to assess")
    from_address: str = Field(..., description="Sender address")
    to_address: str = Field(..., description="Recipient address")
    value: float = Field(..., description="Transaction value in ETH")
    chain: str = Field(default="ethereum", description="Blockchain network")


class RiskFactorResponse(BaseModel):
    """A single risk factor."""
    name: str
    description: str
    contribution: float
    source: str


class LayerScoresResponse(BaseModel):
    """Scores from each risk layer."""
    rules: float
    heuristics: float
    ml: float
    anomaly: float


class RiskMetadataResponse(BaseModel):
    """Assessment metadata."""
    processing_time_ms: float
    layers_evaluated: List[str]


class RiskAssessmentResponse(BaseModel):
    """Risk assessment result."""
    risk_score: float = Field(..., ge=0, le=100, description="Risk score 0-100")
    risk_level: str = Field(..., description="Risk level: LOW/MEDIUM/HIGH/CRITICAL")
    confidence: float = Field(..., ge=0, le=1, description="Confidence in assessment")
    blocked: bool = Field(default=False, description="Whether request is blocked")
    summary: str = Field(..., description="Human-readable summary")
    risk_factors: List[RiskFactorResponse] = Field(default=[], description="Contributing factors")
    layer_scores: LayerScoresResponse
    metadata: RiskMetadataResponse


class EngineStatsResponse(BaseModel):
    """Risk engine statistics."""
    rule_count: int
    classifier_type: str
    anomaly_detector_type: str


# API Endpoints

@router.post(
    "/assess/wallet",
    response_model=RiskAssessmentResponse,
    summary="Assess wallet risk",
    description="Perform comprehensive risk assessment on an Ethereum wallet address."
)
async def assess_wallet_risk(
    request: WalletRiskRequest,
    user: dict = Depends(get_api_key_user)
) -> RiskAssessmentResponse:
    """
    Assess the risk of a wallet address.
    
    This endpoint performs:
    - Blacklist checking against known malicious addresses
    - Velocity analysis for transaction patterns
    - Pattern detection for phishing/honeypot behavior
    - ML-based risk classification
    - Anomaly detection for novel threats
    
    Returns a comprehensive risk assessment with explainability.
    """
    try:
        engine = get_risk_engine()
        
        # Build wallet data for assessment
        # In production, this would fetch real blockchain data
        wallet_data = {
            "address": request.address,
            "balance": 0.0,  # Would be fetched from blockchain
            "transactions": [],  # Would be fetched from blockchain
            "first_seen": None,
        }
        
        # Perform assessment
        result = await engine.assess_wallet(wallet_data)
        
        logger.info(
            "wallet_risk_assessed",
            address=request.address[:10] + "...",
            risk_score=result.risk_score,
            risk_level=result.risk_level
        )
        
        return RiskAssessmentResponse(
            risk_score=result.risk_score,
            risk_level=result.risk_level,
            confidence=result.confidence,
            blocked=result.blocked,
            summary=result.summary,
            risk_factors=[
                RiskFactorResponse(
                    name=f.name,
                    description=f.description,
                    contribution=f.score_contribution,
                    source=f.source
                )
                for f in result.risk_factors
            ],
            layer_scores=LayerScoresResponse(
                rules=result.rule_score,
                heuristics=result.heuristic_score,
                ml=result.ml_score,
                anomaly=result.anomaly_score
            ),
            metadata=RiskMetadataResponse(
                processing_time_ms=result.processing_time_ms,
                layers_evaluated=result.layers_evaluated
            )
        )
        
    except Exception as e:
        logger.error("wallet_risk_assessment_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Risk assessment failed: {str(e)}"
        )


@router.post(
    "/assess/transaction",
    response_model=RiskAssessmentResponse,
    summary="Assess transaction risk",
    description="Assess risk for a specific transaction or proposed transfer."
)
async def assess_transaction_risk(
    request: TransactionRiskRequest,
    user: dict = Depends(get_api_key_user)
) -> RiskAssessmentResponse:
    """
    Assess the risk of a transaction.
    
    Can be used for:
    - Pre-transaction screening (before sending)
    - Post-transaction analysis
    """
    try:
        engine = get_risk_engine()
        
        # Build transaction data
        tx_data = {
            "hash": request.tx_hash,
            "from": request.from_address,
            "to": request.to_address,
            "value": request.value,
        }
        
        # Perform assessment
        result = await engine.assess_transaction(tx_data)
        
        logger.info(
            "transaction_risk_assessed",
            from_addr=request.from_address[:10] + "...",
            to_addr=request.to_address[:10] + "...",
            risk_score=result.risk_score
        )
        
        return RiskAssessmentResponse(
            risk_score=result.risk_score,
            risk_level=result.risk_level,
            confidence=result.confidence,
            blocked=result.blocked,
            summary=result.summary,
            risk_factors=[
                RiskFactorResponse(
                    name=f.name,
                    description=f.description,
                    contribution=f.score_contribution,
                    source=f.source
                )
                for f in result.risk_factors
            ],
            layer_scores=LayerScoresResponse(
                rules=result.rule_score,
                heuristics=result.heuristic_score,
                ml=result.ml_score,
                anomaly=result.anomaly_score
            ),
            metadata=RiskMetadataResponse(
                processing_time_ms=result.processing_time_ms,
                layers_evaluated=result.layers_evaluated
            )
        )
        
    except Exception as e:
        logger.error("transaction_risk_assessment_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Risk assessment failed: {str(e)}"
        )


@router.get(
    "/engine/stats",
    summary="Get engine statistics",
    description="Get risk engine health and configuration statistics."
)
async def get_engine_stats(
    user: dict = Depends(get_api_key_user)
) -> Dict[str, Any]:
    """Get risk engine statistics and health information."""
    engine = get_risk_engine()
    return engine.get_engine_stats()


@router.get(
    "/health",
    summary="Risk engine health",
    description="Check if the risk engine is operational."
)
async def risk_engine_health() -> Dict[str, Any]:
    """Quick health check for risk engine."""
    try:
        engine = get_risk_engine()
        return {
            "status": "healthy",
            "engine_initialized": True,
            "classifier": engine.classifier.get_model_info().get("type", "unknown"),
            "anomaly_detector": engine.anomaly_detector.get_model_info().get("type", "unknown"),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
