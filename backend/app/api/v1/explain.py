"""
ChainShield AI Explanation API Endpoints

AI-powered explanation endpoints with fallback to template-based explanations.
Ready for Phase 4 AI provider integration.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_api_key_user
from app.core.logging import get_logger
from app.schemas import (
    ExplainRequest,
    ExplainResponse,
    BaseResponse,
    ResponseMeta,
)
from app.services.blockchain import wallet_service, transaction_service

logger = get_logger(__name__)

router = APIRouter(prefix="/explain", tags=["AI Explanation"])


async def generate_wallet_explanation(address: str, context: dict = None) -> dict:
    """
    Generate explanation for a wallet.
    
    Uses blockchain data and heuristic analysis.
    Phase 4 will add AI-powered explanations.
    """
    # Fetch wallet data
    from app.schemas import Chain
    profile = await wallet_service.get_wallet_profile(address, Chain.ETHEREUM)
    risk = await wallet_service.get_wallet_risk(address, Chain.ETHEREUM)
    
    # Build explanation parts
    factors = []
    recommendations = []
    
    if profile:
        if profile.is_contract:
            factors.append("This is a smart contract address, not a regular wallet")
        
        if profile.total_tx_count == 0:
            factors.append("No transaction history found - this is a new or unused wallet")
            recommendations.append("Wait for transaction activity before trusting this address")
        elif profile.total_tx_count < 5:
            factors.append(f"Low activity: only {profile.total_tx_count} transactions")
        
        if profile.balance_eth and profile.balance_eth > 100:
            factors.append(f"High value wallet holding {profile.balance_eth:.4f} ETH")
    
    if risk:
        for tag in risk.tags:
            if tag == "new_wallet":
                factors.append("Recently created wallet with no history")
            elif tag == "low_activity":
                factors.append("Minimal transaction activity detected")
            elif tag == "high_value":
                factors.append("Contains significant ETH balance")
            elif tag == "potentially_drained":
                factors.append("Wallet appears to have been drained recently")
                recommendations.append("Exercise extreme caution - possible compromised wallet")
    
    if not factors:
        factors.append("No significant risk factors detected")
    
    if not recommendations:
        recommendations.append("Standard verification recommended for any transaction")
    
    explanation = f"""
## Wallet Analysis: {address[:10]}...{address[-6:]}

### Risk Assessment
- **Risk Score**: {risk.score if risk else 'Unknown'}/100
- **Risk Level**: {risk.level.value.upper() if risk else 'UNKNOWN'}
- **Confidence**: {risk.confidence * 100:.0f}% if risk else 0%

### Key Findings
{chr(10).join(f"- {f}" for f in factors)}

### Recommendations
{chr(10).join(f"- {r}" for r in recommendations)}

*Analysis performed using on-chain data. AI-powered deep analysis coming in Phase 4.*
""".strip()
    
    return {
        "explanation": explanation,
        "confidence": risk.confidence if risk else 0.0,
        "factors": factors,
        "recommendations": recommendations,
    }


async def generate_transaction_explanation(tx_hash: str, context: dict = None) -> dict:
    """
    Generate explanation for a transaction.
    
    Uses blockchain data and heuristic analysis.
    Phase 4 will add AI-powered explanations.
    """
    from app.schemas import Chain
    details = await transaction_service.get_transaction_details(tx_hash, Chain.ETHEREUM)
    
    factors = []
    recommendations = []
    
    if not details:
        return {
            "explanation": f"Transaction {tx_hash[:10]}... not found on the blockchain.",
            "confidence": 0.0,
            "factors": ["Transaction not found"],
            "recommendations": ["Verify the transaction hash is correct"],
        }
    
    # Analyze transaction
    if not details.is_success:
        factors.append("Transaction FAILED - the operation was not completed")
        recommendations.append("Review transaction logs for error details")
    
    if details.value > 0:
        factors.append(f"Value transfer of {details.value:.6f} ETH")
        if details.value > 10:
            factors.append("Large value transfer detected")
            recommendations.append("Verify recipient address before similar transactions")
    
    if details.tx_type == "contract_creation":
        factors.append("This transaction created a new smart contract")
    elif details.tx_type != "transfer":
        factors.append(f"Contract interaction detected: {details.tx_type}")
    
    if not factors:
        factors.append("Standard ETH transfer with no unusual patterns")
    
    if not recommendations:
        recommendations.append("No specific concerns identified")
    
    explanation = f"""
## Transaction Analysis: {tx_hash[:10]}...{tx_hash[-6:]}

### Transaction Details
- **Block**: {details.block_number}
- **From**: {details.from_address[:10]}...{details.from_address[-6:]}
- **To**: {details.to_address[:10] if details.to_address else 'Contract Creation'}...{details.to_address[-6:] if details.to_address else ''}
- **Value**: {details.value:.6f} ETH
- **Status**: {'SUCCESS' if details.is_success else 'FAILED'}
- **Type**: {details.tx_type}

### Key Findings
{chr(10).join(f"- {f}" for f in factors)}

### Recommendations
{chr(10).join(f"- {r}" for r in recommendations)}

*Analysis performed using on-chain data. AI-powered deep analysis coming in Phase 4.*
""".strip()
    
    return {
        "explanation": explanation,
        "confidence": 0.7,
        "factors": factors,
        "recommendations": recommendations,
    }


@router.post(
    "",
    response_model=BaseResponse[ExplainResponse],
    summary="Get AI explanation",
    description="Get detailed explanation for a wallet or transaction risk assessment."
)
async def get_explanation(
    request: Request,
    body: ExplainRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_api_key_user),
):
    """
    Get explanation for risk analysis.
    
    - **target_type**: "wallet" or "transaction"
    - **target_id**: Address or transaction hash
    - **chain**: Blockchain network
    - **context**: Optional additional context
    """
    correlation_id = getattr(request.state, "correlation_id", None)
    
    logger.info(
        "explanation_requested",
        target_type=body.target_type,
        target_id=body.target_id[:20] + "...",
        correlation_id=correlation_id
    )
    
    # Generate explanation based on target type
    if body.target_type == "wallet":
        result = await generate_wallet_explanation(
            body.target_id, 
            body.context
        )
    else:
        result = await generate_transaction_explanation(
            body.target_id,
            body.context
        )
    
    explanation = ExplainResponse(
        target_type=body.target_type,
        target_id=body.target_id,
        explanation=result["explanation"],
        confidence=result["confidence"],
        key_factors=result["factors"],
        recommendations=result["recommendations"],
        generated_at=datetime.utcnow(),
    )
    
    logger.info(
        "explanation_generated",
        target_type=body.target_type,
        confidence=result["confidence"],
        correlation_id=correlation_id
    )
    
    return BaseResponse(
        data=explanation,
        meta=ResponseMeta(
            correlation_id=correlation_id,
            cached=False,
            model_version="v1.0-heuristic",
        )
    )
