"""Demo of enhanced NLP explainer with narrative explanations."""

from app.services.risk.ml.nlp_explainer import get_nlp_explainer

explainer = get_nlp_explainer()

# Test Case 1: High-risk wallet with bridge/cross-chain activity
print("=" * 70)
print("TEST CASE 1: SUSPICIOUS WALLET (Bridge + High Volume)")
print("=" * 70)

wallet_data = {
    "address": "1F1tAaz5x1HUXrCNLbtMDqcw6o5GNn4xqX",
    "balance": 0.33,
    "tx_count_total": 3512,
    "total_received": 29679.67,
    "total_sent": 29679.34,
    "transactions": []
}

risk_factors = [
    {
        "name": "bridge_usage",
        "source": "crosschain",
        "score_contribution": 25,
        "description": "5 bridge transactions detected"
    },
    {
        "name": "high_centrality_hub",
        "source": "graph",
        "score_contribution": 20,
        "description": "Hub wallet with 75% centrality"
    },
]

result = explainer.generate_summary(
    risk_score=75.0,
    risk_level="high",
    wallet_data=wallet_data,
    risk_factors=risk_factors
)

print()
print("📝 NARRATIVE SUMMARY:")
print("-" * 50)
print(result.summary)
print()
print("🔍 KEY FACTORS:")
for i, factor in enumerate(result.key_factors, 1):
    print(f"   {i}. {factor}")
print()
print("💡 RECOMMENDATION:", result.recommendation)
print("=" * 70)
