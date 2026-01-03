"""
Transaction Flow Heuristic

Analyzes in/out transaction patterns to detect anomalies:
- Rug pull patterns (many in, few out to single address)
- Honeypot patterns (many in, almost no out)
- Wash trading (self-transfers)
"""

from typing import Any, Dict
import structlog

from app.services.risk.heuristics.account_age import HeuristicResult

logger = structlog.get_logger()


class TransactionFlowHeuristic:
    """
    Analyzes transaction flow patterns.
    
    Key patterns detected:
    1. Rug pull: Many receivers → wallet → single exit address
    2. Honeypot: Many in, almost no out
    3. Wash trading: High self-transfer ratio
    4. Concentration: Most volume to/from few addresses
    """
    
    def __init__(self, weight: float = 1.0):
        """Initialize heuristic."""
        self.name = "transaction_flow"
        self.weight = weight
        self.logger = logger.bind(module="flow_heuristic")
    
    def evaluate(
        self, 
        features: Dict[str, float],
        context: Dict[str, Any] = None
    ) -> HeuristicResult:
        """
        Evaluate transaction flow patterns.
        
        Args:
            features: Extracted feature dictionary
            context: Optional additional context
            
        Returns:
            HeuristicResult with score and factors
        """
        factors = []
        score = 0.0
        details = {}
        
        # Get flow metrics
        in_out_ratio = features.get("in_out_ratio", 0.5)
        total_received = features.get("total_received_eth", 0)
        total_sent = features.get("total_sent_eth", 0)
        balance = features.get("balance_eth", 0)
        
        # Calculate pass-through ratio from pre-calculated totals
        # This is total_sent / total_received which shows what % of funds moved out
        pass_through_ratio = 0.0
        if total_received > 0:
            pass_through_ratio = total_sent / total_received
        
        details["in_out_ratio"] = in_out_ratio
        details["total_received"] = total_received
        details["total_sent"] = total_sent
        details["pass_through_ratio"] = pass_through_ratio
        
        # Check 1: Pass-through pattern detection
        # If most received funds have been sent out, this is classic laundering
        if pass_through_ratio > 0.90 and total_received > 5:
            # Near-100% pass through = very suspicious
            penalty = min(60, pass_through_ratio * 60)  # Strong penalty
            score += penalty
            factors.append(f"Pass-through: {pass_through_ratio:.0%} of received funds moved out")
            details["pass_through_penalty"] = penalty
        
        # Check 2: Honeypot pattern (almost no outflow)
        if in_out_ratio < 0.1 and total_received > 5:
            penalty = min(25, (0.5 - in_out_ratio) * 50)
            score += penalty
            factors.append(f"Very low outflow: only {in_out_ratio:.0%} sent")
            details["honeypot_penalty"] = penalty
        
        # Check 3: Self-transfer ratio
        self_transfer_ratio = features.get("self_transfer_ratio", 0)
        if self_transfer_ratio > 0.2:
            penalty = min(15, self_transfer_ratio * 50)
            score += penalty
            factors.append(f"High self-transfer: {self_transfer_ratio:.0%}")
            details["self_transfer_penalty"] = penalty
        
        # Check 4: Counterparty concentration (single exit)
        concentration = features.get("counterparty_concentration", 0)
        unique_receivers = features.get("unique_receivers", 10)
        
        if concentration > 0.7 and unique_receivers < 5:
            penalty = min(20, concentration * 25)
            score += penalty
            factors.append(f"High concentration: {concentration:.0%} to {unique_receivers} addresses")
            details["concentration_penalty"] = penalty
        
        # Check 5: Imbalanced sender/receiver counts
        unique_senders = features.get("unique_senders", 1)
        if unique_senders > 10 and unique_receivers < 3:
            ratio = unique_senders / max(unique_receivers, 1)
            penalty = min(15, ratio * 2)
            score += penalty
            factors.append(f"Many senders ({unique_senders}), few receivers ({unique_receivers})")
            details["sender_receiver_imbalance"] = penalty
        
        # Check 6: Rapid divestment / Pass-through pattern (balance much lower than received)
        # Classic laundering: receive funds and immediately move them out
        if total_received > 0:
            retention_ratio = balance / total_received
            if retention_ratio < 0.10 and total_received > 5:  # Less than 10% retained
                # Strong penalty for pass-through - this is classic laundering
                penalty = min(40, (1 - retention_ratio) * 40)
                score += penalty
                factors.append(f"Pass-through pattern: {(1-retention_ratio)*100:.0f}% moved out, only {retention_ratio*100:.2f}% retained")
                details["divestment_penalty"] = penalty
        
        # Cap score
        score = min(100, score)
        
        # Confidence based on volume
        has_meaningful_volume = total_received > 1 or total_sent > 1
        confidence = 0.85 if has_meaningful_volume else 0.5
        
        return HeuristicResult(
            name=self.name,
            score=round(score, 2),
            confidence=confidence,
            factors=factors,
            details=details
        )
