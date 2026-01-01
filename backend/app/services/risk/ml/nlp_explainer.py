"""
ChainShield Natural Language Explanations

Converts ML risk scores and SHAP values into human-readable explanations.
Makes risk decisions understandable for analysts and compliance.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
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
        
        # Extract additional data for narrative
        tx_count_total = wallet_data.get("tx_count_total", tx_count)
        total_received = wallet_data.get("total_received", 0)
        total_sent = wallet_data.get("total_sent", 0)
        
        # Build narrative summary based on behavior patterns
        narrative_parts = []
        
        # 1. Transaction Volume Analysis
        if tx_count_total > 10000:
            narrative_parts.append(
                f"This wallet shows extremely high activity with {tx_count_total:,} transactions, "
                "which is unusual for a personal wallet and may indicate automated trading, "
                "exchange operations, or potential laundering activity"
            )
        elif tx_count_total > 1000:
            narrative_parts.append(
                f"This wallet has processed {tx_count_total:,} transactions, "
                "indicating significant activity that warrants monitoring"
            )
        
        # 2. Fund Flow Analysis
        if total_received > 0 and total_sent > 0:
            pass_through_ratio = total_sent / max(total_received, 0.001)
            if pass_through_ratio > 0.95 and balance < total_received * 0.05:
                narrative_parts.append(
                    f"The wallet received {total_received:.2f} units but only {balance:.4f} remains. "
                    f"Over 95% of funds were moved out, which is a classic pass-through/laundering pattern"
                )
        
        # 3. Check for bridge/cross-chain patterns from risk factors
        bridge_detected = False
        mixer_detected = False
        graph_hub = False
        
        if risk_factors:
            for factor in risk_factors:
                factor_name = str(factor.get("name", "")).lower()
                factor_source = str(factor.get("source", "")).lower()
                
                if "bridge" in factor_name or factor_source == "crosschain":
                    bridge_detected = True
                if "mixer" in factor_name or "tornado" in factor_name:
                    mixer_detected = True
                if "hub" in factor_name or "centrality" in factor_name:
                    graph_hub = True
        
        if bridge_detected:
            narrative_parts.append(
                "This wallet has interacted with cross-chain bridge protocols, "
                "which can be used to move funds across different blockchains "
                "and obscure the transaction trail"
            )
        
        if mixer_detected:
            narrative_parts.append(
                "⚠️ CRITICAL: This wallet has interacted with known mixer/tumbler services "
                "(like Tornado Cash), which are commonly used for money laundering"
            )
        
        if graph_hub:
            narrative_parts.append(
                "Graph analysis shows this wallet acts as a hub, connecting many other wallets. "
                "This could indicate a collection point for funds from multiple sources"
            )
        
        # Build final summary
        if risk_level == "low":
            summary = (
                f"Wallet {address} shows normal activity patterns. "
                f"Risk score: {risk_score:.0f}/100. "
                f"No significant risk factors detected."
            )
            confidence = "High"
        
        elif risk_level == "medium":
            if narrative_parts:
                summary = f"Wallet {address} has concerning indicators. " + ". ".join(narrative_parts[:2]) + "."
            else:
                summary = (
                    f"Wallet {address} has some concerning indicators. "
                    f"Risk score: {risk_score:.0f}/100. "
                    f"Enhanced monitoring recommended."
                )
            confidence = "Medium"
        
        elif risk_level == "high":
            if narrative_parts:
                summary = f"⚠️ HIGH RISK: Wallet {address} - " + ". ".join(narrative_parts[:3]) + "."
            else:
                summary = (
                    f"Wallet {address} shows multiple high-risk patterns. "
                    f"Risk score: {risk_score:.0f}/100. "
                    f"Manual review strongly recommended."
                )
            confidence = "High"
        
        else:  # critical
            if narrative_parts:
                summary = f"🚨 CRITICAL ALERT: Wallet {address} - " + ". ".join(narrative_parts) + "."
            else:
                summary = (
                    f"ALERT: Wallet {address} has critical risk indicators. "
                    f"Risk score: {risk_score:.0f}/100. "
                    f"Immediate action required."
                )
            confidence = "High"
        
        # Extract key factors with better narratives
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
        
        # Add cross-chain narrative factors
        if bridge_detected:
            key_factors.append(
                "Cross-chain bridge usage detected - funds may be moving between blockchains"
            )
        
        if mixer_detected:
            key_factors.append(
                "Connected to mixer/tumbler services - high probability of laundering"
            )
        
        # Add from risk_factors if provided
        if risk_factors:
            for factor in risk_factors[:3]:
                factor_name = factor.get("factor_name", factor.get("name", ""))
                score = factor.get("score", factor.get("score_contribution", 0))
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
