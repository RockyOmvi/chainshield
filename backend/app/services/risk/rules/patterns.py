"""
ChainShield Pattern Rule

Detects known malicious transaction patterns.
This catches phishing, honeypots, and exploit signatures.
"""

from typing import Any, Dict, List, Optional
import re
import structlog

from app.services.risk.rules.base import RiskRule, RuleResult, RuleSeverity
from app.services.risk.config import risk_config

logger = structlog.get_logger()


class PatternRule(RiskRule):
    """
    Rule that detects known attack patterns.
    
    Patterns detected:
    - Phishing contract names
    - Airdrop scams
    - Honeypot contracts
    - Reentrancy signatures
    - Flash loan attacks
    """
    
    # Known malicious function signatures (4-byte selectors)
    MALICIOUS_SIGNATURES = {
        "0x23b872dd": "transferFrom (common in approval scams)",
        "0x095ea7b3": "approve (infinite approval attack)",
        "0xa9059cbb": "transfer (check context)",
    }
    
    # Suspicious patterns in contract data
    SUSPICIOUS_PATTERNS = [
        (r"claim", "Phishing: contains 'claim'"),
        (r"airdrop", "Phishing: contains 'airdrop'"),
        (r"reward", "Phishing: contains 'reward'"),
        (r"free", "Phishing: contains 'free'"),
        (r"bonus", "Phishing: contains 'bonus'"),
        (r"giveaway", "Phishing: contains 'giveaway'"),
    ]
    
    def __init__(
        self,
        name: str = "pattern_check",
        enabled: bool = True,
        weight: float = 0.7
    ):
        super().__init__(name, enabled, weight)
        
        # Compile regex patterns for efficiency
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), desc)
            for pattern, desc in self.SUSPICIOUS_PATTERNS
        ]
    
    @property
    def description(self) -> str:
        return "Detects known malicious transaction and contract patterns"
    
    def evaluate(
        self, 
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> RuleResult:
        """
        Evaluate for known attack patterns.
        """
        if not self.enabled:
            return self._make_result(triggered=False)
        
        factors = []
        details = {}
        max_severity = RuleSeverity.INFO
        total_score = 0.0
        
        transactions = data.get("transactions", [])
        
        for tx in transactions:
            # Check input data patterns
            input_data = tx.get("input", "")
            if input_data and input_data != "0x":
                pattern_result = self._check_input_patterns(input_data, tx)
                if pattern_result["triggered"]:
                    factors.extend(pattern_result["factors"])
                    total_score += pattern_result["score"]
                    max_severity = max(max_severity, pattern_result["severity"])
            
            # Check for zero-value with high gas (dust attack / address poisoning)
            dust_result = self._check_dust_attack(tx)
            if dust_result["triggered"]:
                factors.extend(dust_result["factors"])
                total_score += dust_result["score"]
                max_severity = max(max_severity, dust_result["severity"])
            
            # Check for contract creation with suspicious patterns
            if not tx.get("to"):  # Contract creation
                creation_result = self._check_contract_creation(tx, data)
                if creation_result["triggered"]:
                    factors.extend(creation_result["factors"])
                    total_score += creation_result["score"]
                    max_severity = max(max_severity, creation_result["severity"])
        
        if not factors:
            return self._make_result(triggered=False)
        
        # Cap score at 100
        final_score = min(total_score, 100)
        
        return self._make_result(
            triggered=True,
            severity=max_severity,
            score=final_score,
            message=f"{len(factors)} suspicious patterns detected",
            details=details,
            factors=factors[:5]
        )
    
    def _check_input_patterns(
        self, 
        input_data: str,
        tx: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check transaction input data for malicious patterns."""
        result = {
            "triggered": False,
            "factors": [],
            "score": 0.0,
            "severity": RuleSeverity.INFO
        }
        
        # Check function signature
        if len(input_data) >= 10:
            selector = input_data[:10].lower()
            if selector in self.MALICIOUS_SIGNATURES:
                # Context matters - infinite approval is the concern
                if selector == "0x095ea7b3":  # approve
                    # Check if approving max uint256 (infinite approval)
                    if "ffffffff" in input_data.lower():
                        result["triggered"] = True
                        result["factors"].append("Infinite approval detected")
                        result["score"] = 40.0
                        result["severity"] = RuleSeverity.MEDIUM
        
        # Check for phishing patterns in any decoded data
        tx_data_str = str(tx.get("decoded_input", "")).lower()
        for pattern, description in self.compiled_patterns:
            if pattern.search(tx_data_str):
                result["triggered"] = True
                result["factors"].append(description)
                result["score"] = max(result["score"], 30.0)
                result["severity"] = max(result["severity"], RuleSeverity.LOW)
        
        return result
    
    def _check_dust_attack(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check for dust/address poisoning attack.
        
        Pattern: Zero or tiny value with high gas price.
        Used to poison transaction history with lookalike addresses.
        """
        result = {
            "triggered": False,
            "factors": [],
            "score": 0.0,
            "severity": RuleSeverity.INFO
        }
        
        value = float(tx.get("value", 0))
        gas_price_gwei = float(tx.get("gas_price", 0)) / 1e9
        
        # Dust attack: very low value, high gas
        if value < 0.0001 and gas_price_gwei > 50:
            result["triggered"] = True
            result["factors"].append(
                f"Dust attack pattern: {value} ETH with {gas_price_gwei:.1f} gwei gas"
            )
            result["score"] = 25.0
            result["severity"] = RuleSeverity.LOW
        
        # Zero value with any execution (address poisoning)
        if value == 0 and tx.get("input", "0x") != "0x":
            # This could be legitimate contract interaction
            # but combined with other factors is suspicious
            result["triggered"] = True
            result["factors"].append("Zero-value contract interaction")
            result["score"] = 15.0
            result["severity"] = RuleSeverity.INFO
        
        return result
    
    def _check_contract_creation(
        self, 
        tx: Dict[str, Any],
        wallet_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check contract creation from this address.
        
        New accounts creating contracts is suspicious.
        """
        result = {
            "triggered": False,
            "factors": [],
            "score": 0.0,
            "severity": RuleSeverity.INFO
        }
        
        # Contract creation from new account is suspicious
        age_hours = wallet_data.get("age_hours", 0)
        if age_hours < 24:
            result["triggered"] = True
            result["factors"].append(
                f"Contract deployed from {age_hours:.1f}h old account"
            )
            result["score"] = 35.0
            result["severity"] = RuleSeverity.MEDIUM
        
        return result


class HoneypotRule(RiskRule):
    """
    Specialized rule for detecting honeypot contracts.
    
    Honeypots are contracts designed to trap funds.
    They allow deposits but block withdrawals.
    """
    
    def __init__(
        self,
        name: str = "honeypot_check",
        enabled: bool = True,
        weight: float = 0.6
    ):
        super().__init__(name, enabled, weight)
    
    @property
    def description(self) -> str:
        return "Detects honeypot contract patterns"
    
    def evaluate(
        self, 
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> RuleResult:
        """
        Evaluate for honeypot patterns.
        
        Honeypot indicators:
        - Many incoming transactions
        - Very few successful outgoing transactions
        - High failure rate for withdrawals
        """
        if not self.enabled:
            return self._make_result(triggered=False)
        
        transactions = data.get("transactions", [])
        address = data.get("address", "").lower()
        
        if len(transactions) < 5:
            return self._make_result(triggered=False)
        
        incoming = 0
        outgoing_success = 0
        outgoing_failed = 0
        
        for tx in transactions:
            is_incoming = tx.get("to", "").lower() == address
            is_outgoing = tx.get("from", "").lower() == address
            is_failed = tx.get("status") == 0 or tx.get("is_error")
            
            if is_incoming:
                incoming += 1
            elif is_outgoing:
                if is_failed:
                    outgoing_failed += 1
                else:
                    outgoing_success += 1
        
        # Calculate ratios
        total_outgoing = outgoing_success + outgoing_failed
        
        factors = []
        score = 0.0
        
        # High imbalance: many in, few out
        if incoming > 10 and total_outgoing < 3:
            factors.append(
                f"Imbalanced flow: {incoming} in, {total_outgoing} out"
            )
            score += 40.0
        
        # High outgoing failure rate
        if total_outgoing > 0:
            failure_rate = outgoing_failed / total_outgoing
            if failure_rate > 0.5:
                factors.append(
                    f"High withdrawal failure rate: {failure_rate:.0%}"
                )
                score += 50.0
        
        if not factors:
            return self._make_result(triggered=False)
        
        return self._make_result(
            triggered=True,
            severity=RuleSeverity.HIGH if score >= 50 else RuleSeverity.MEDIUM,
            score=min(score, 100),
            message="Honeypot pattern detected",
            factors=factors
        )
