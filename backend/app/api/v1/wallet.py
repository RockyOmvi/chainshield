"""
ChainShield Wallet API Endpoints

Wallet analysis and risk scoring endpoints.
Connected to real blockchain data via service layer.
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_api_key_user
from app.core.logging import get_logger
from app.schemas import (
    WalletAnalyzeRequest,
    WalletAnalyzeResponse,
    WalletRiskScore,
    WalletProfile,
    BaseResponse,
    ResponseMeta,
    Chain,
)
from app.schemas.base import validate_ethereum_address
from app.services.blockchain import wallet_service

logger = get_logger(__name__)

router = APIRouter(prefix="/wallet", tags=["Wallet"])


@router.post(
    "/analyze",
    response_model=BaseResponse[WalletAnalyzeResponse],
    summary="Analyze wallet risk",
    description="Analyze a wallet address for risk factors using real blockchain data."
)
async def analyze_wallet(
    request: Request,
    body: WalletAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_api_key_user),
):
    """
    Analyze a wallet for risk factors.
    
    - **address**: Ethereum wallet address (0x...)
    - **chain**: Blockchain network (default: ethereum)
    - **include_history**: Include wallet profile with balance and tx count
    - **include_explanation**: Include human-readable explanation
    """
    correlation_id = getattr(request.state, "correlation_id", None)
    
    logger.info(
        "wallet_analyze_started",
        address=body.address[:10] + "...",
        chain=body.chain.value,
        correlation_id=correlation_id
    )
    
    # Call the wallet service for real blockchain analysis
    response_data = await wallet_service.analyze_wallet(body)
    
    logger.info(
        "wallet_analyze_completed",
        address=body.address[:10] + "...",
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
    "/{address}",
    response_model=BaseResponse[WalletProfile],
    summary="Get wallet profile",
    description="Get wallet profile with real blockchain data including balance and transaction count."
)
async def get_wallet(
    request: Request,
    address: str,
    chain: Chain = Query(default=Chain.ETHEREUM),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_api_key_user),
):
    """Get wallet profile by address with real blockchain data."""
    correlation_id = getattr(request.state, "correlation_id", None)
    
    # Validate address format
    address = validate_ethereum_address(address)
    
    # Fetch profile from blockchain
    profile = await wallet_service.get_wallet_profile(address, chain)
    
    if not profile:
        # Return empty profile if fetch failed
        profile = WalletProfile(
            address=address,
            chain=chain,
            total_tx_count=0,
            is_contract=False,
        )
    
    return BaseResponse(
        data=profile,
        meta=ResponseMeta(
            correlation_id=correlation_id,
            cached=False
        )
    )


@router.get(
    "/{address}/risk",
    response_model=BaseResponse[WalletRiskScore],
    summary="Get wallet risk score",
    description="Get just the risk score for a wallet based on blockchain data."
)
async def get_wallet_risk(
    request: Request,
    address: str,
    chain: Chain = Query(default=Chain.ETHEREUM),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_api_key_user),
):
    """Get wallet risk score from blockchain analysis."""
    correlation_id = getattr(request.state, "correlation_id", None)
    
    # Validate address format
    address = validate_ethereum_address(address)
    
    # Get risk score from service
    risk = await wallet_service.get_wallet_risk(address, chain)
    
    return BaseResponse(
        data=risk,
        meta=ResponseMeta(
            correlation_id=correlation_id,
            cached=False
        )
    )
