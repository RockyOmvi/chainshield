"""
ChainShield Rule Registry

Manages all rules and executes them in the correct order.
Provides aggregation of rule results.
"""

from typing import Any, Dict, List, Optional, Type
import structlog

from app.services.risk.rules.base import RiskRule, RuleResult, RuleSeverity

logger = structlog.get_logger()


class RuleRegistry:
    """
    Registry and executor for all risk rules.
    
    Responsibilities:
    1. Register and manage rules
    2. Execute rules in priority order
    3. Aggregate results
    4. Handle rule failures gracefully
    """
    
    def __init__(self):
        self.rules: List[RiskRule] = []
        self.logger = logger.bind(module="rule_registry")
        self._initialized = False
    
    def register(self, rule: RiskRule) -> None:
        """Register a rule with the registry."""
        self.rules.append(rule)
        self.logger.info("rule_registered", rule=rule.name, enabled=rule.enabled)
    
    def register_many(self, rules: List[RiskRule]) -> None:
        """Register multiple rules."""
        for rule in rules:
            self.register(rule)
    
    def get_rule(self, name: str) -> Optional[RiskRule]:
        """Get a rule by name."""
        for rule in self.rules:
            if rule.name == name:
                return rule
        return None
    
    def enable_rule(self, name: str) -> bool:
        """Enable a rule by name."""
        rule = self.get_rule(name)
        if rule:
            rule.enabled = True
            return True
        return False
    
    def disable_rule(self, name: str) -> bool:
        """Disable a rule by name."""
        rule = self.get_rule(name)
        if rule:
            rule.enabled = False
            return True
        return False
    
    def evaluate_all(
        self, 
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        stop_on_critical: bool = True
    ) -> Dict[str, Any]:
        """
        Evaluate all registered rules against data.
        
        Args:
            data: Wallet or transaction data
            context: Additional context (features, etc.)
            stop_on_critical: If True, stop on first CRITICAL result
            
        Returns:
            Aggregated result with:
            - combined_score: Weighted average of all scores
            - max_severity: Highest severity found
            - results: List of individual rule results
            - factors: Combined list of risk factors
            - blocked: Whether a blocking rule was triggered
        """
        results: List[RuleResult] = []
        all_factors: List[str] = []
        max_severity = RuleSeverity.INFO
        blocked = False
        
        enabled_rules = [r for r in self.rules if r.enabled]
        
        for rule in enabled_rules:
            try:
                result = rule.evaluate(data, context)
                results.append(result)
                
                if result.triggered:
                    all_factors.extend(result.factors)
                    if result.severity.value > max_severity.value:
                        max_severity = result.severity
                    
                    if result.is_blocking:
                        blocked = True
                        self.logger.warning(
                            "blocking_rule_triggered",
                            rule=rule.name,
                            severity=result.severity.value
                        )
                        if stop_on_critical:
                            break
                            
            except Exception as e:
                self.logger.error(
                    "rule_execution_failed",
                    rule=rule.name,
                    error=str(e)
                )
                # Continue with other rules even if one fails
        
        # Calculate combined score
        combined_score = self._calculate_combined_score(results)
        
        return {
            "combined_score": combined_score,
            "max_severity": max_severity.value,
            "results": [r.to_dict() for r in results if r.triggered],
            "factors": all_factors[:10],  # Limit to top 10
            "blocked": blocked,
            "rules_evaluated": len(enabled_rules),
            "rules_triggered": sum(1 for r in results if r.triggered),
        }
    
    def _calculate_combined_score(self, results: List[RuleResult]) -> float:
        """
        Calculate weighted combined score from rule results.
        
        Uses weighted average based on rule weights.
        """
        triggered = [r for r in results if r.triggered]
        
        if not triggered:
            return 0.0
        
        # Get rule weights
        total_weight = 0.0
        weighted_sum = 0.0
        
        for result in triggered:
            rule = self.get_rule(result.rule_name)
            weight = rule.weight if rule else 1.0
            weighted_sum += result.score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return round(weighted_sum / total_weight, 2)
    
    def initialize_defaults(self) -> None:
        """Initialize with default rules."""
        if self._initialized:
            return
        
        from app.services.risk.rules.blacklist import BlacklistRule
        from app.services.risk.rules.velocity import VelocityRule
        from app.services.risk.rules.patterns import PatternRule, HoneypotRule
        
        default_rules = [
            BlacklistRule(),
            VelocityRule(),
            PatternRule(),
            HoneypotRule(),
        ]
        
        self.register_many(default_rules)
        self._initialized = True
        
        self.logger.info(
            "default_rules_initialized",
            rule_count=len(self.rules)
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for r in self.rules if r.enabled),
            "disabled_rules": sum(1 for r in self.rules if not r.enabled),
            "rules": [
                {
                    "name": r.name,
                    "enabled": r.enabled,
                    "weight": r.weight,
                    "description": r.description
                }
                for r in self.rules
            ]
        }


# Global registry instance
rule_registry = RuleRegistry()
