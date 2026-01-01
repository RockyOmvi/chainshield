"""Demo of enhanced NLP explainer with comprehensive report."""

from app.services.risk.ml.nlp_explainer import get_nlp_explainer

explainer = get_nlp_explainer()

# Test Case: High-risk wallet with bridge/cross-chain activity
wallet_data = {
    "address": "0x1F1tAaz5x1HUXrCNLbtMDqcw6o5GNn4xqX",
    "chain": "bitcoin",
    "balance": 0.33,
    "tx_count_total": 3512,
    "total_received": 29679.67,
    "total_sent": 29679.34,
    "age_hours": 720,  # 30 days
    "transactions": []
}

risk_factors = [
    {
        "name": "bridge_usage",
        "source": "crosschain",
        "score_contribution": 25,
        "description": "5 cross-chain bridge transactions detected"
    },
    {
        "name": "high_centrality_hub",
        "source": "graph",
        "score_contribution": 20,
        "description": "Hub wallet with 75% network centrality"
    },
]

shap_values = {
    "tx_count_total": 0.35,
    "balance_log": -0.12,
    "in_out_ratio": 0.28,
    "bridge_use_count": 0.45,
    "flow_concentration": 0.22,
}

# Generate comprehensive report
report = explainer.explain_for_analyst(
    risk_score=75.0,
    risk_level="high",
    wallet_data=wallet_data,
    shap_values=shap_values,
    risk_factors=risk_factors
)

print(report)
