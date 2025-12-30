"""
ChainShield Transaction API Endpoints

Transaction analysis endpoints connected to real blockchain data.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_api_key_user
from app.core.logging import get_logger
from app.schemas import (
    TransactionAnalyzeRequest,
    TransactionAnalyzeResponse,
    TransactionSummary,
    TransactionRiskScore,
    BaseResponse,
    ResponseMeta,
    RiskLevel,
    Chain,
)
from app.schemas.base import validate_tx_hash
from app.services.blockchain import transaction_service

logger = get_logger(__name__)

router = APIRouter(prefix="/transaction", tags=["Transaction"])


@router.post(
    "/analyze",
    response_model=BaseResponse[TransactionAnalyzeResponse],
    summary="Analyze transaction risk",
    description="Analyze a transaction for risk factors using real blockchain data."
)
async def analyze_transaction(
    request: Request,
    body: TransactionAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_api_key_user),
):
    """
    Analyze a transaction for risk.
    
    - **tx_hash**: Transaction hash (0x...)
    - **chain**: Blockchain network (default: ethereum)
    - **include_details**: Include full transaction details
    - **include_explanation**: Include human-readable explanation
    """
    correlation_id = getattr(request.state, "correlation_id", None)
    
    logger.info(
        "transaction_analyze_started",
        tx_hash=body.tx_hash[:10] + "...",
        chain=body.chain.value,
        correlation_id=correlation_id
    )
    
    # Call transaction service for real blockchain analysis
    response_data = await transaction_service.analyze_transaction(body)
    
    logger.info(
        "transaction_analyze_completed",
        tx_hash=body.tx_hash[:10] + "...",
        risk_score=response_data.risk.score,
        risk_level=response_data.risk.level.value,
        correlation_id=correlation_id
    )
    
    return BaseResponse(
        data=response_data,
        meta=ResponseMeta(
            correlation_id=correlation_id,
            cached=False,
            model_version="v1.0-heuristic",
        )
    )


@router.get(
    "/{tx_hash}",
    response_model=BaseResponse[TransactionSummary],
    summary="Get transaction details",
    description="Get transaction details from the blockchain."
)
async def get_transaction(
    request: Request,
    tx_hash: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_api_key_user),
):
    """Get transaction details by hash."""
    correlation_id = getattr(request.state, "correlation_id", None)
    
    # Validate hash format
    tx_hash = validate_tx_hash(tx_hash)
    
    # Fetch from blockchain
    transaction = await transaction_service.get_transaction_details(tx_hash)
    
    if not transaction:
        # Return minimal response if not found
        from app.core.errors import NotFoundError
        raise NotFoundError(f"Transaction {tx_hash[:10]}... not found")
    
    return BaseResponse(
        data=transaction,
        meta=ResponseMeta(
            correlation_id=correlation_id,
            cached=False
        )
    )
