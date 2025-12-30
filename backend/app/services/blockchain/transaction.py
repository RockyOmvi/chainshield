"""
ChainShield Transaction Service

Business logic for transaction analysis including:
- Transaction fetching and normalization
- Receipt and logs parsing
- Risk assessment
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from app.core.config import settings
from app.core.logging import get_logger
from app.services.blockchain.client import (
    blockchain_client,
    TransactionData,
    TransactionReceipt,
)
from app.schemas import (
    TransactionAnalyzeRequest,
    TransactionAnalyzeResponse,
    TransactionSummary,
    TransactionRiskScore,
    RiskLevel,
    Chain,
)

logger = get_logger(__name__)


class TransactionService:
    """
    Service layer for transaction operations.
    
    Handles:
    - Fetching transaction data from blockchain
    - Parsing transaction receipts and logs
    - Risk assessment
    """
    
    def __init__(self):
        self._client = blockchain_client
    
    async def analyze_transaction(
        self,
        request: TransactionAnalyzeRequest
    ) -> TransactionAnalyzeResponse:
        """
        Analyze a transaction.
        
        1. Fetch transaction from blockchain
        2. Get receipt and logs
        3. Calculate risk score
        4. Generate explanation (placeholder)
        """
        tx_hash = request.tx_hash.lower()
        chain = request.chain
        
        logger.info(
            "transaction_analysis_started",
            tx_hash=tx_hash[:10] + "...",
            chain=chain.value
        )
        
        # Fetch transaction data
        try:
            tx_data = await self._client.get_transaction_data(tx_hash)
            
            if not tx_data:
                logger.warning(
                    "transaction_not_found",
                    tx_hash=tx_hash[:10] + "..."
                )
                return TransactionAnalyzeResponse(
                    tx_hash=tx_hash,
                    chain=chain,
                    risk=TransactionRiskScore(
                        score=0,
                        level=RiskLevel.UNKNOWN,
                        confidence=0.0,
                        flags=["not_found"]
                    ),
                    transaction=None,
                    explanation="Transaction not found on the blockchain.",
                    analyzed_at=datetime.utcnow()
                )
        except Exception as e:
            logger.error(
                "transaction_analysis_blockchain_error",
                tx_hash=tx_hash[:10] + "...",
                error=str(e)
            )
            return TransactionAnalyzeResponse(
                tx_hash=tx_hash,
                chain=chain,
                risk=TransactionRiskScore(
                    score=0,
                    level=RiskLevel.UNKNOWN,
                    confidence=0.0,
                    flags=["blockchain_error"]
                ),
                transaction=None,
                explanation="Unable to fetch transaction data. Please try again later.",
                analyzed_at=datetime.utcnow()
            )
        
        # Build transaction summary
        transaction = None
        if request.include_details:
            transaction = TransactionSummary(
                tx_hash=tx_data.tx_hash,
                chain=chain,
                block_number=tx_data.block_number,
                timestamp=tx_data.timestamp,
                from_address=tx_data.from_address,
                to_address=tx_data.to_address,
                value=float(tx_data.value_eth),
                gas_used=tx_data.gas_used,
                gas_price=float(Decimal(tx_data.gas_price) / Decimal(10**9)),  # Convert to Gwei
                is_success=tx_data.is_success,
                tx_type=self._detect_tx_type(tx_data)
            )
        
        # Calculate risk score
        risk_score, risk_flags = self._calculate_risk(tx_data)
        risk_level = self._score_to_level(risk_score)
        
        risk = TransactionRiskScore(
            score=risk_score,
            level=risk_level,
            confidence=0.65,
            flags=risk_flags
        )
        
        # Generate explanation
        explanation = None
        if request.include_explanation:
            explanation = self._generate_explanation(tx_data, risk_score, risk_flags)
        
        logger.info(
            "transaction_analysis_completed",
            tx_hash=tx_hash[:10] + "...",
            risk_score=risk_score,
            risk_level=risk_level.value
        )
        
        return TransactionAnalyzeResponse(
            tx_hash=tx_hash,
            chain=chain,
            risk=risk,
            transaction=transaction,
            explanation=explanation,
            analyzed_at=datetime.utcnow()
        )
    
    async def get_transaction_details(
        self,
        tx_hash: str,
        chain: Chain = Chain.ETHEREUM
    ) -> Optional[TransactionSummary]:
        """Get transaction details."""
        tx_hash = tx_hash.lower()
        
        try:
            tx_data = await self._client.get_transaction_data(tx_hash)
            if not tx_data:
                return None
            
            return TransactionSummary(
                tx_hash=tx_data.tx_hash,
                chain=chain,
                block_number=tx_data.block_number,
                timestamp=tx_data.timestamp,
                from_address=tx_data.from_address,
                to_address=tx_data.to_address,
                value=float(tx_data.value_eth),
                gas_used=tx_data.gas_used,
                gas_price=float(Decimal(tx_data.gas_price) / Decimal(10**9)),
                is_success=tx_data.is_success,
                tx_type=self._detect_tx_type(tx_data)
            )
        except Exception as e:
            logger.error(
                "transaction_details_fetch_error",
                tx_hash=tx_hash[:10] + "...",
                error=str(e)
            )
            return None
    
    def _detect_tx_type(self, tx_data: TransactionData) -> str:
        """Detect transaction type from input data."""
        if not tx_data.to_address:
            return "contract_creation"
        
        if tx_data.input_data == "0x" or len(tx_data.input_data) <= 2:
            return "transfer"
        
        # Check common method signatures
        method_id = tx_data.method_id
        if method_id:
            # Common ERC-20 methods
            known_methods = {
                "0xa9059cbb": "erc20_transfer",
                "0x23b872dd": "erc20_transferFrom",
                "0x095ea7b3": "erc20_approve",
                # Uniswap
                "0x7ff36ab5": "swap_exact_eth_for_tokens",
                "0x38ed1739": "swap_exact_tokens_for_tokens",
                # NFT
                "0x42842e0e": "erc721_safeTransferFrom",
                "0xb88d4fde": "erc721_safeTransferFrom_data",
            }
            if method_id in known_methods:
                return known_methods[method_id]
        
        return "contract_call"
    
    def _calculate_risk(self, tx_data: TransactionData) -> tuple[int, List[str]]:
        """
        Calculate transaction risk score.
        
        Simple heuristics - Phase 3 will add ML model.
        """
        score = 15  # Base score
        flags = []
        
        # Failed transaction
        if not tx_data.is_success:
            score += 10
            flags.append("failed")
        
        # Contract creation
        if not tx_data.to_address:
            score += 5
            flags.append("contract_creation")
        
        # Large value transfer
        if tx_data.value_eth > 10:
            score += 10
            flags.append("high_value")
        
        if tx_data.value_eth > 100:
            score += 15
            flags.append("very_high_value")
        
        # Zero value with data (potential contract interaction)
        if tx_data.value_eth == 0 and len(tx_data.input_data) > 10:
            score += 5
            flags.append("contract_interaction")
        
        # High gas usage (complex operation)
        if tx_data.gas_used > 500000:
            score += 10
            flags.append("complex_operation")
        
        # Cap at 100
        score = min(score, 100)
        
        return score, flags
    
    def _score_to_level(self, score: int) -> RiskLevel:
        """Convert score to risk level."""
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
        tx_data: TransactionData,
        risk_score: int,
        risk_flags: List[str]
    ) -> str:
        """Generate human-readable explanation."""
        parts = [f"Analysis of transaction {tx_data.tx_hash[:10]}...{tx_data.tx_hash[-6:]}:"]
        
        # Basic info
        parts.append(f"• Block: {tx_data.block_number}")
        parts.append(f"• Value: {tx_data.value_eth:.6f} ETH")
        parts.append(f"• From: {tx_data.from_address[:10]}...{tx_data.from_address[-6:]}")
        
        if tx_data.to_address:
            parts.append(f"• To: {tx_data.to_address[:10]}...{tx_data.to_address[-6:]}")
        else:
            parts.append("• Contract Creation")
        
        parts.append(f"• Status: {'Success' if tx_data.is_success else 'Failed'}")
        
        # Risk
        level = self._score_to_level(risk_score)
        parts.append(f"• Risk: {level.value.upper()} ({risk_score}/100)")
        
        if risk_flags:
            parts.append(f"• Flags: {', '.join(risk_flags)}")
        
        return "\n".join(parts)


# Global service instance
transaction_service = TransactionService()

__all__ = ["TransactionService", "transaction_service"]
