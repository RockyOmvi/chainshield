"""
ChainShield Risk Rule Base Classes

Abstract base class for all risk rules.
Ensures consistent interface and explainability.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger()


class RuleSeverity(str, Enum):
    """Severity levels for rule matches."""
    CRITICAL = "critical"  # Immediate block, no further analysis
    HIGH = "high"          # Strong risk indicator
    MEDIUM = "medium"      # Moderate concern
    LOW = "low"            # Minor flag
    INFO = "info"          # Informational only
    
    @property
    def weight(self) -> int:
        """Numeric weight for proper severity comparison."""
        weights = {
            "critical": 5,
            "high": 4,
            "medium": 3,
            "low": 2,
            "info": 1
        }
        return weights[self.value]
    
    def __gt__(self, other: "RuleSeverity") -> bool:
        return self.weight > other.weight
    
    def __ge__(self, other: "RuleSeverity") -> bool:
        return self.weight >= other.weight
    
    def __lt__(self, other: "RuleSeverity") -> bool:
        return self.weight < other.weight
    
    def __le__(self, other: "RuleSeverity") -> bool:
        return self.weight <= other.weight


@dataclass
class RuleResult:
    """
    Result from a rule evaluation.
    
    Attributes:
        rule_name: Name of the rule that produced this result
        triggered: Whether the rule was triggered
        severity: How severe is the match
        score: Numeric contribution to risk score (0-100)
        message: Human-readable explanation
        details: Additional data for debugging/audit
        factors: List of contributing factors for explainability
    """
    rule_name: str
    triggered: bool
    severity: RuleSeverity = RuleSeverity.INFO
    score: float = 0.0
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    factors: List[str] = field(default_factory=list)
    
    @property
    def is_blocking(self) -> bool:
        """Whether this result should block further processing."""
        return self.triggered and self.severity == RuleSeverity.CRITICAL
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "rule": self.rule_name,
            "triggered": self.triggered,
            "severity": self.severity.value,
            "score": self.score,
            "message": self.message,
            "factors": self.factors,
        }


class RiskRule(ABC):
    """
    Abstract base class for all risk rules.
    
    Design Contract:
    1. Rules must be deterministic (same input = same output)
    2. Rules must be fast (<1ms typical)
    3. Rules must be explainable (return human-readable factors)
    4. Rules must handle missing data gracefully
    """
    
    def __init__(self, name: str, enabled: bool = True, weight: float = 1.0):
        """
        Initialize a risk rule.
        
        Args:
            name: Unique identifier for this rule
            enabled: Whether the rule is active
            weight: Relative weight for score aggregation
        """
        self.name = name
        self.enabled = enabled
        self.weight = weight
        self.logger = logger.bind(rule=name)
    
    @abstractmethod
    def evaluate(
        self, 
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> RuleResult:
        """
        Evaluate the rule against provided data.
        
        Args:
            data: The wallet or transaction data to evaluate
            context: Optional additional context (features, history, etc.)
            
        Returns:
            RuleResult with evaluation outcome
        """
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this rule checks."""
        pass
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, enabled={self.enabled})>"
    
    def _make_result(
        self,
        triggered: bool,
        severity: RuleSeverity = RuleSeverity.INFO,
        score: float = 0.0,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
        factors: Optional[List[str]] = None
    ) -> RuleResult:
        """Helper to create consistent RuleResult objects."""
        return RuleResult(
            rule_name=self.name,
            triggered=triggered,
            severity=severity,
            score=score,
            message=message,
            details=details or {},
            factors=factors or []
        )


class CompositeRule(RiskRule):
    """
    A rule that combines multiple sub-rules.
    
    Useful for complex conditions that require multiple checks.
    """
    
    def __init__(
        self, 
        name: str, 
        rules: List[RiskRule],
        require_all: bool = False,
        enabled: bool = True,
        weight: float = 1.0
    ):
        """
        Initialize composite rule.
        
        Args:
            name: Name for this composite rule
            rules: List of sub-rules to evaluate
            require_all: If True, all rules must trigger. If False, any trigger.
            enabled: Whether this rule is active
            weight: Weight for score aggregation
        """
        super().__init__(name, enabled, weight)
        self.rules = rules
        self.require_all = require_all
    
    @property
    def description(self) -> str:
        mode = "all" if self.require_all else "any"
        rule_names = [r.name for r in self.rules]
        return f"Composite rule ({mode} of {rule_names})"
    
    def evaluate(
        self, 
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> RuleResult:
        """Evaluate all sub-rules and combine results."""
        if not self.enabled:
            return self._make_result(triggered=False)
        
        results = []
        for rule in self.rules:
            if rule.enabled:
                results.append(rule.evaluate(data, context))
        
        triggered_results = [r for r in results if r.triggered]
        
        if self.require_all:
            # All must trigger
            triggered = len(triggered_results) == len(self.rules)
        else:
            # Any trigger is enough
            triggered = len(triggered_results) > 0
        
        if not triggered:
            return self._make_result(triggered=False)
        
        # Combine scores and factors from triggered rules
        combined_score = sum(r.score for r in triggered_results) / len(triggered_results)
        combined_factors = []
        for r in triggered_results:
            combined_factors.extend(r.factors)
        
        # Highest severity wins
        max_severity = max(r.severity for r in triggered_results)
        
        return self._make_result(
            triggered=True,
            severity=max_severity,
            score=combined_score,
            message=f"{len(triggered_results)} sub-rules triggered",
            factors=combined_factors[:5]  # Limit factors
        )
