"""
ChainShield Wallet Service

Business logic for wallet analysis including:
- Balance fetching
- Transaction history
- Contract detection
- Risk scoring integration
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List

from app.core.logging import get_logger
from app.services.blockchain.client import (
    blockchain_client,
    WalletBalance,
)
from app.schemas import (
    WalletAnalyzeRequest,
    WalletAnalyzeResponse,
    WalletProfile,
    WalletRiskScore,
    RiskLevel,
    Chain,
)

logger = get_logger(__name__)


class WalletService:
    """
    Service layer for wallet operations.
    
    Handles:
    - Fetching wallet data from blockchain
    - Enriching with on-chain metrics
    - Preparing data for risk analysis
    """
    
    def __init__(self):
        self._client = blockchain_client
    
    async def analyze_wallet(
        self,
        request: WalletAnalyzeRequest
    ) -> WalletAnalyzeResponse:
        """
        Analyze a wallet address.
        
        1. Fetch balance from blockchain
        2. Check if contract
        3. Get transaction count
        4. Calculate preliminary risk score
        5. Generate explanation (placeholder for Phase 4)
        """
        address = request.address.lower()
        chain = request.chain
        
        logger.info(
            "wallet_analysis_started",
            address=address[:10] + "...",
            chain=chain.value
        )
        
        # Fetch blockchain data
        try:
            balance = await self._client.get_wallet_balance(address)
            is_contract = await self._client.is_contract(address)
            tx_count = await self._client.get_transaction_count(address)
        except Exception as e:
            logger.error(
                "wallet_analysis_blockchain_error",
                address=address[:10] + "...",
                error=str(e)
            )
            # Return with unknown risk if blockchain fetch fails
            return WalletAnalyzeResponse(
                address=address,
                chain=chain,
                risk=WalletRiskScore(
                    score=0,
                    level=RiskLevel.UNKNOWN,
                    confidence=0.0,
                    tags=["blockchain_error"]
                ),
                profile=None,
                explanation="Unable to fetch blockchain data. Please try again later.",
                analyzed_at=datetime.utcnow()
            )
        
        # Build profile if requested
        profile = None
        if request.include_history:
            profile = WalletProfile(
                address=address,
                chain=chain,
                balance_eth=float(balance.balance_eth),
                total_tx_count=tx_count,
                is_contract=is_contract,
                first_seen_at=None,  # Would require historical data
                last_seen_at=datetime.utcnow(),
            )
        
        # Calculate preliminary risk score
        # This is a simple heuristic - Phase 3 will add ML model
        risk_score, risk_tags = self._calculate_preliminary_risk(
            balance=balance,
            is_contract=is_contract,
            tx_count=tx_count
        )
        
        risk_level = self._score_to_level(risk_score)
        confidence = 0.6  # Lower confidence without ML model
        
        risk = WalletRiskScore(
            score=risk_score,
            level=risk_level,
            confidence=confidence,
            tags=risk_tags
        )
        
        # Generate explanation if requested
        explanation = None
        if request.include_explanation:
            explanation = self._generate_explanation(
                address=address,
                balance=balance,
                is_contract=is_contract,
                tx_count=tx_count,
                risk_score=risk_score,
                risk_tags=risk_tags
            )
        
        logger.info(
            "wallet_analysis_completed",
            address=address[:10] + "...",
            risk_score=risk_score,
            risk_level=risk_level.value
        )
        
        return WalletAnalyzeResponse(
            address=address,
            chain=chain,
            risk=risk,
            profile=profile,
            explanation=explanation,
            analyzed_at=datetime.utcnow()
        )
    
    async def get_wallet_profile(
        self,
        address: str,
        chain: Chain = Chain.ETHEREUM
    ) -> Optional[WalletProfile]:
        """Get wallet profile with on-chain data."""
        address = address.lower()
        
        try:
            balance = await self._client.get_wallet_balance(address)
            is_contract = await self._client.is_contract(address)
            tx_count = await self._client.get_transaction_count(address)
            
            return WalletProfile(
                address=address,
                chain=chain,
                balance_eth=float(balance.balance_eth),
                total_tx_count=tx_count,
                is_contract=is_contract,
                last_seen_at=datetime.utcnow(),
            )
        except Exception as e:
            logger.error(
                "wallet_profile_fetch_error",
                address=address[:10] + "...",
                error=str(e)
            )
            return None
    
    async def get_wallet_risk(
        self,
        address: str,
        chain: Chain = Chain.ETHEREUM
    ) -> WalletRiskScore:
        """Get just the risk score for a wallet."""
        address = address.lower()
        
        try:
            balance = await self._client.get_wallet_balance(address)
            is_contract = await self._client.is_contract(address)
            tx_count = await self._client.get_transaction_count(address)
            
            risk_score, risk_tags = self._calculate_preliminary_risk(
                balance=balance,
                is_contract=is_contract,
                tx_count=tx_count
            )
            
            return WalletRiskScore(
                score=risk_score,
                level=self._score_to_level(risk_score),
                confidence=0.6,
                tags=risk_tags
            )
        except Exception as e:
            logger.error(
                "wallet_risk_fetch_error",
                address=address[:10] + "...",
                error=str(e)
            )
            return WalletRiskScore(
                score=0,
                level=RiskLevel.UNKNOWN,
                confidence=0.0,
                tags=["error"]
            )
    
    def _calculate_preliminary_risk(
        self,
        balance: WalletBalance,
        is_contract: bool,
        tx_count: int
    ) -> tuple[int, List[str]]:
        """
        Calculate preliminary risk score based on heuristics.
        
        This is a simple scoring system. Phase 3 will add ML-based scoring.
        """
        score = 20  # Base score
        tags = []
        
        # New wallet with no transactions
        if tx_count == 0:
            score += 15
            tags.append("new_wallet")
        
        # Very few transactions
        elif tx_count < 5:
            score += 10
            tags.append("low_activity")
        
        # Contract address
        if is_contract:
            score += 5
            tags.append("contract")
        
        # Large balance (potential target)
        if balance.balance_eth > 100:
            score += 10
            tags.append("high_value")
        
        # Empty wallet with transactions (drained?)
        if balance.balance_eth < 0.001 and tx_count > 10:
            score += 20
            tags.append("potentially_drained")
        
        # Cap score at 100
        score = min(score, 100)
        
        return score, tags
    
    def _score_to_level(self, score: int) -> RiskLevel:
        """Convert numeric score to risk level."""
        if score >= settings.risk_high_threshold:
            return RiskLevel.HIGH
        elif score >= settings.risk_medium_threshold:
            return RiskLevel.MEDIUM
        elif score > 0:
            return RiskLevel.LOW
        else:
            return RiskLevel.UNKNOWN
    
    def _generate_explanation(
        self,
        address: str,
        balance: WalletBalance,
        is_contract: bool,
        tx_count: int,
        risk_score: int,
        risk_tags: List[str]
    ) -> str:
        """
        Generate human-readable explanation.
        
        This is a placeholder. Phase 4 will add AI-powered explanations.
        """
        parts = [f"Analysis of wallet {address[:10]}...{address[-6:]}:"]
        
        # Balance info
        parts.append(f"• Balance: {balance.balance_eth:.4f} ETH")
        
        # Transaction count
        parts.append(f"• Transaction count: {tx_count}")
        
        # Contract status
        if is_contract:
            parts.append("• This is a smart contract address")
        
        # Risk assessment
        level = self._score_to_level(risk_score)
        parts.append(f"• Risk assessment: {level.value.upper()} ({risk_score}/100)")
        
        # Tags explanation
        if risk_tags:
            parts.append(f"• Flags: {', '.join(risk_tags)}")
        
        return "\n".join(parts)


# Import settings for risk thresholds
from app.core.config import settings

# Global service instance
wallet_service = WalletService()

__all__ = ["WalletService", "wallet_service"]
