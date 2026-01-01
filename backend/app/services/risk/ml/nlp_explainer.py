"""
ChainShield Natural Language Explanations

Converts ML risk scores and SHAP values into human-readable explanations.
Makes risk decisions understandable for analysts and compliance.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import structlog

logger = structlog.get_logger()


@dataclass
class RiskExplanation:
    """A human-readable risk explanation."""
    summary: str
    risk_level: str
    key_factors: List[str]
    recommendation: str
    confidence: str


class NaturalLanguageExplainer:
    """
    Generates natural language explanations for risk decisions.
    
    Converts:
    - SHAP values → Human-readable factor descriptions
    - Risk scores → Plain English summary
    - Risk factors → Actionable recommendations
    """
    
    # Feature name to human-readable mapping
    FEATURE_DESCRIPTIONS = {
        # Balance features
        "balance_eth": "wallet balance",
        "balance_usd": "wallet value",
        "balance_log": "wallet balance",
        
        # Age features
        "age_hours": "account age",
        "age_days": "account age",
        "first_seen": "account creation date",
        
        # Transaction features
        "tx_count_total": "total transactions",
        "tx_count_in": "incoming transactions",
        "tx_count_out": "outgoing transactions",
        "tx_per_hour_avg": "transaction frequency",
        "tx_value_total": "total transaction volume",
        "tx_value_avg": "average transaction size",
        "tx_value_max": "largest transaction",
        
        # Counterparty features
        "unique_senders": "unique incoming counterparties",
        "unique_receivers": "unique outgoing counterparties",
        "counterparty_concentration": "counterparty concentration",
        
        # Flow features
        "in_out_ratio": "inflow/outflow ratio",
        "net_flow": "net fund flow",
        "flow_velocity": "flow rate",
        
        # Temporal features
        "active_hours_entropy": "activity time distribution",
        "burst_score": "burst transaction pattern",
        "late_night_ratio": "late-night activity",
        
        # Token features
        "token_transfer_count": "token transfers",
        "unique_token_count": "unique tokens used",
        "nft_transfer_count": "NFT transfers",
        "spam_token_ratio": "spam token interaction",
        "dex_activity_ratio": "DEX activity",
        "wash_trading_score": "wash trading indicators",
        
        # Graph features
        "pagerank": "network influence",
        "in_degree_centrality": "incoming connections",
        "out_degree_centrality": "outgoing connections",
        "flow_concentration": "fund concentration",
        
        # Bridge/cross-chain
        "bridge_use_count": "cross-chain bridge usage",
    }
    
    # Risk factor templates
    RISK_FACTOR_TEMPLATES = {
        "new_account": "This is a newly created account ({age} old), which is common for fraud.",
        "high_volume": "The wallet has processed unusually high volume (${volume:,.0f}) for its age.",
        "many_senders": "Received funds from {count} unique addresses, indicating possible aggregation.",
        "mixer_use": "Connected to known mixer or tumbler services.",
        "burst_activity": "Shows burst transaction patterns ({burst_count} transactions in short period).",
        "late_night": "{percent:.0%} of activity occurs during late-night hours.",
        "high_concentration": "Funds are concentrated to/from just {count} counterparties.",
        "spam_tokens": "Interacted with {count} suspected spam tokens.",
        "wash_trading": "Shows wash trading patterns (same tokens cycling in and out).",
        "bridge_usage": "Used cross-chain bridges {count} times, potentially to obscure origin.",
        "low_balance": "Very low balance (${balance:.2f}) after high activity.",
        "automated": "Shows automated/bot-like regular interval patterns.",
    }
    
    # Recommendations by risk level
    RECOMMENDATIONS = {
        "low": "This wallet appears to be legitimate. No action required.",
        "medium": "Monitor this wallet for additional suspicious activity.",
        "high": "Enhanced due diligence recommended. Review transaction history.",
        "critical": "Block this wallet immediately. Report to compliance team.",
    }
    
    def __init__(self):
        """Initialize explainer."""
        self.logger = logger.bind(module="nlp_explainer")
    
    def _get_feature_description(self, feature_name: str) -> str:
        """Get human-readable description for a feature."""
        # Try exact match
        if feature_name in self.FEATURE_DESCRIPTIONS:
            return self.FEATURE_DESCRIPTIONS[feature_name]
        
        # Try partial match
        for key, desc in self.FEATURE_DESCRIPTIONS.items():
            if key in feature_name:
                return desc
        
        # Default: clean up the feature name
        return feature_name.replace("_", " ").replace("ts ", "").replace("gnn ", "")
    
    def explain_shap_values(
        self,
        shap_values: Dict[str, float],
        top_k: int = 5
    ) -> List[str]:
        """
        Convert SHAP values to human-readable explanations.
        
        Args:
            shap_values: Dict of feature name to SHAP value
            top_k: Number of top factors to explain
            
        Returns:
            List of factor explanations
        """
        # Sort by absolute SHAP value
        sorted_features = sorted(
            shap_values.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )[:top_k]
        
        explanations = []
        for feature, value in sorted_features:
            if abs(value) < 0.01:
                continue
            
            desc = self._get_feature_description(feature)
            
            if value > 0:
                direction = "increases"
            else:
                direction = "decreases"
            
            magnitude = "significantly" if abs(value) > 0.1 else "slightly"
            
            explanations.append(
                f"The {desc} {magnitude} {direction} the risk score."
            )
        
        return explanations
    
    def generate_summary(
        self,
        risk_score: float,
        risk_level: str,
        wallet_data: Dict[str, Any],
        risk_factors: List[Dict[str, Any]] = None
    ) -> RiskExplanation:
        """
        Generate a complete natural language explanation.
        
        Args:
            risk_score: Risk score (0-100)
            risk_level: Risk level (low/medium/high/critical)
            wallet_data: Wallet data dict
            risk_factors: List of detected risk factors
            
        Returns:
            RiskExplanation with summary and recommendations
        """
        address = wallet_data.get("address", "Unknown")[:10] + "..."
        balance = float(wallet_data.get("balance", 0))
        tx_count = len(wallet_data.get("transactions", []))
        
        # Build summary based on risk level
        if risk_level == "low":
            summary = (
                f"Wallet {address} shows normal activity patterns. "
                f"Risk score: {risk_score:.0f}/100. "
                f"No significant risk factors detected."
            )
            confidence = "High"
        
        elif risk_level == "medium":
            summary = (
                f"Wallet {address} has some concerning indicators. "
                f"Risk score: {risk_score:.0f}/100. "
                f"Enhanced monitoring recommended."
            )
            confidence = "Medium"
        
        elif risk_level == "high":
            summary = (
                f"Wallet {address} shows multiple high-risk patterns. "
                f"Risk score: {risk_score:.0f}/100. "
                f"Manual review strongly recommended."
            )
            confidence = "High"
        
        else:  # critical
            summary = (
                f"ALERT: Wallet {address} has critical risk indicators. "
                f"Risk score: {risk_score:.0f}/100. "
                f"Immediate action required."
            )
            confidence = "High"
        
        # Extract key factors
        key_factors = []
        
        # Check wallet data for specific patterns
        age_hours = wallet_data.get("age_hours", 0)
        if age_hours < 24:
            key_factors.append(
                self.RISK_FACTOR_TEMPLATES["new_account"].format(
                    age=f"{age_hours:.0f} hours" if age_hours > 1 else "less than an hour"
                )
            )
        
        if tx_count > 50 and age_hours < 48:
            key_factors.append(
                f"High transaction velocity: {tx_count} transactions in {age_hours:.0f} hours."
            )
        
        if balance < 0.1 and tx_count > 10:
            key_factors.append(
                self.RISK_FACTOR_TEMPLATES["low_balance"].format(balance=balance)
            )
        
        # Add from risk_factors if provided
        if risk_factors:
            for factor in risk_factors[:3]:
                factor_name = factor.get("factor_name", factor.get("name", ""))
                score = factor.get("score", 0)
                if score > 20:
                    desc = factor.get("description", factor_name.replace("_", " "))
                    key_factors.append(f"{desc} (impact: {score:.0f})")
        
        if not key_factors:
            key_factors = ["No specific high-risk factors identified."]
        
        recommendation = self.RECOMMENDATIONS.get(risk_level, self.RECOMMENDATIONS["medium"])
        
        return RiskExplanation(
            summary=summary,
            risk_level=risk_level,
            key_factors=key_factors[:5],
            recommendation=recommendation,
            confidence=confidence
        )
    
    def explain_for_analyst(
        self,
        risk_score: float,
        risk_level: str,
        wallet_data: Dict[str, Any],
        shap_values: Dict[str, float] = None,
        risk_factors: List[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a full explanation for analysts.
        
        Returns:
            Multi-line explanation string
        """
        explanation = self.generate_summary(
            risk_score, risk_level, wallet_data, risk_factors
        )
        
        lines = [
            "="*50,
            "RISK ASSESSMENT EXPLANATION",
            "="*50,
            "",
            f"📊 SUMMARY: {explanation.summary}",
            "",
            f"⚠️ RISK LEVEL: {explanation.risk_level.upper()}",
            f"📈 CONFIDENCE: {explanation.confidence}",
            "",
            "🔍 KEY FACTORS:",
        ]
        
        for i, factor in enumerate(explanation.key_factors, 1):
            lines.append(f"   {i}. {factor}")
        
        if shap_values:
            lines.append("")
            lines.append("📉 FEATURE IMPACT (SHAP):")
            shap_explanations = self.explain_shap_values(shap_values, top_k=3)
            for exp in shap_explanations:
                lines.append(f"   • {exp}")
        
        lines.extend([
            "",
            f"💡 RECOMMENDATION: {explanation.recommendation}",
            "="*50,
        ])
        
        return "\n".join(lines)


# Singleton
_nlp_explainer: Optional[NaturalLanguageExplainer] = None


def get_nlp_explainer() -> NaturalLanguageExplainer:
    """Get or create NLP explainer singleton."""
    global _nlp_explainer
    if _nlp_explainer is None:
        _nlp_explainer = NaturalLanguageExplainer()
    return _nlp_explainer
