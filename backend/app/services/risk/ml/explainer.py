"""
ChainShield SHAP Explainer

Provides Model-Agnostic Explanations using SHAP (SHapley Additive exPlanations).
SHAP values tell us how much each feature contributed to the prediction.

Why SHAP:
1. Mathematically grounded (game theory)
2. Works with any ML model
3. Provides both global and local explanations
4. Required for regulatory compliance
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import structlog

logger = structlog.get_logger()


@dataclass
class FeatureExplanation:
    """Explanation for a single feature's contribution."""
    feature_name: str
    feature_value: float
    shap_value: float
    contribution: str  # "increases" or "decreases" risk
    importance_rank: int


@dataclass
class PredictionExplanation:
    """Complete explanation for a prediction."""
    risk_score: float
    base_score: float  # Expected value (average)
    top_factors: List[FeatureExplanation]
    summary: str


class SHAPExplainer:
    """
    SHAP-based model explainer.
    
    Provides:
    - Local explanations (why this specific prediction)
    - Global explanations (what features matter most overall)
    - Natural language summaries
    """
    
    def __init__(self, model=None, feature_names: Optional[List[str]] = None):
        """
        Initialize explainer.
        
        Args:
            model: The trained model to explain
            feature_names: Names of features
        """
        self.model = model
        self.feature_names = feature_names or []
        self.explainer = None
        self.logger = logger.bind(module="shap_explainer")
        
        if model is not None:
            self._init_explainer()
    
    def _init_explainer(self) -> None:
        """Initialize SHAP explainer for the model."""
        try:
            import shap
            
            # Use TreeExplainer for tree-based models (fast)
            if hasattr(self.model, 'estimators_'):
                self.explainer = shap.TreeExplainer(self.model)
                self.logger.info("tree_explainer_initialized")
            else:
                # Fallback to KernelExplainer (slower, any model)
                self.logger.info("using_fallback_explainer")
                
        except ImportError:
            self.logger.warning("shap_not_available", msg="Using fallback explanations")
    
    def explain(
        self, 
        features: Dict[str, float],
        top_n: int = 5
    ) -> PredictionExplanation:
        """
        Explain a single prediction.
        
        Args:
            features: Feature dictionary
            top_n: Number of top factors to return
            
        Returns:
            PredictionExplanation with top contributing features
        """
        if self.explainer is not None:
            return self._explain_with_shap(features, top_n)
        else:
            return self._explain_fallback(features, top_n)
    
    def _explain_with_shap(
        self, 
        features: Dict[str, float],
        top_n: int
    ) -> PredictionExplanation:
        """Explain using SHAP values."""
        import shap
        import numpy as np
        
        # Convert to array
        X = np.array([[features.get(name, 0) for name in self.feature_names]])
        
        # Get SHAP values
        shap_values = self.explainer.shap_values(X)
        
        # For binary classification, use positive class
        if isinstance(shap_values, list):
            shap_values = shap_values[1]
        
        base_value = self.explainer.expected_value
        if isinstance(base_value, list):
            base_value = base_value[1]
        
        # Create explanations
        values = shap_values[0]
        feature_explanations = []
        
        # Sort by absolute contribution
        sorted_indices = np.argsort(np.abs(values))[::-1]
        
        for rank, idx in enumerate(sorted_indices[:top_n], 1):
            name = self.feature_names[idx]
            value = features.get(name, 0)
            shap_val = values[idx]
            
            feature_explanations.append(FeatureExplanation(
                feature_name=name,
                feature_value=value,
                shap_value=round(shap_val, 4),
                contribution="increases" if shap_val > 0 else "decreases",
                importance_rank=rank
            ))
        
        # Calculate risk score
        risk_score = (base_value + sum(values)) * 100
        risk_score = max(0, min(100, risk_score))
        
        # Generate summary
        summary = self._generate_summary(feature_explanations, risk_score)
        
        return PredictionExplanation(
            risk_score=round(risk_score, 2),
            base_score=round(base_value * 100, 2),
            top_factors=feature_explanations,
            summary=summary
        )
    
    def _explain_fallback(
        self, 
        features: Dict[str, float],
        top_n: int
    ) -> PredictionExplanation:
        """
        Fallback explanation using feature importance.
        
        Used when SHAP is not available.
        """
        explanations = []
        
        # Use model's feature importance if available
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            
            for rank, (name, importance) in enumerate(
                sorted(zip(self.feature_names, importances), 
                       key=lambda x: x[1], reverse=True)[:top_n], 1
            ):
                value = features.get(name, 0)
                
                # Estimate contribution based on value deviation
                contribution = "increases" if value > 0.5 else "decreases"
                
                explanations.append(FeatureExplanation(
                    feature_name=name,
                    feature_value=value,
                    shap_value=round(importance, 4),
                    contribution=contribution,
                    importance_rank=rank
                ))
        else:
            # No importance available, use heuristics
            risk_features = [
                ("mixer_interaction_count", "increases"),
                ("tx_per_hour_avg", "increases"),
                ("age_hours", "decreases"),
                ("active_hours_entropy", "decreases"),
                ("counterparty_concentration", "increases"),
            ]
            
            for rank, (name, contribution) in enumerate(risk_features[:top_n], 1):
                value = features.get(name, 0)
                explanations.append(FeatureExplanation(
                    feature_name=name,
                    feature_value=value,
                    shap_value=0.0,
                    contribution=contribution,
                    importance_rank=rank
                ))
        
        summary = self._generate_summary(explanations, 50.0)
        
        return PredictionExplanation(
            risk_score=50.0,  # Default
            base_score=30.0,
            top_factors=explanations,
            summary=summary
        )
    
    def _generate_summary(
        self, 
        explanations: List[FeatureExplanation],
        risk_score: float
    ) -> str:
        """Generate natural language summary."""
        if not explanations:
            return "No significant risk factors identified."
        
        # Build summary
        parts = []
        
        if risk_score >= 70:
            parts.append(f"HIGH RISK ({risk_score:.0f}/100).")
        elif risk_score >= 40:
            parts.append(f"MEDIUM RISK ({risk_score:.0f}/100).")
        else:
            parts.append(f"LOW RISK ({risk_score:.0f}/100).")
        
        # Top factor
        top = explanations[0]
        if top.contribution == "increases":
            parts.append(f"Primary concern: {self._humanize_feature(top.feature_name)} ({top.feature_value:.2f}).")
        else:
            parts.append(f"Positive factor: {self._humanize_feature(top.feature_name)} ({top.feature_value:.2f}).")
        
        # Other significant factors
        increasing = [e for e in explanations[1:] if e.contribution == "increases"]
        if increasing:
            names = [self._humanize_feature(e.feature_name) for e in increasing[:2]]
            parts.append(f"Also concerning: {', '.join(names)}.")
        
        return " ".join(parts)
    
    def _humanize_feature(self, name: str) -> str:
        """Convert feature name to human-readable format."""
        translations = {
            "mixer_interaction_count": "mixer usage",
            "tx_per_hour_avg": "transaction velocity",
            "age_hours": "account age",
            "active_hours_entropy": "activity pattern regularity",
            "counterparty_concentration": "counterparty concentration",
            "in_out_ratio": "in/out flow balance",
            "failed_tx_ratio": "failed transaction rate",
            "dust_tx_ratio": "dust transaction rate",
            "round_number_tx_ratio": "round number preference",
            "volume_velocity": "volume velocity",
        }
        return translations.get(name, name.replace("_", " "))
    
    def get_global_importance(self) -> List[Tuple[str, float]]:
        """
        Get global feature importance.
        
        Returns features ranked by overall impact.
        """
        if not hasattr(self.model, 'feature_importances_'):
            return []
        
        importances = self.model.feature_importances_
        paired = list(zip(self.feature_names, importances))
        return sorted(paired, key=lambda x: x[1], reverse=True)
    
    def to_dict(self, explanation: PredictionExplanation) -> Dict[str, Any]:
        """Convert explanation to dictionary for API response."""
        return {
            "risk_score": explanation.risk_score,
            "base_score": explanation.base_score,
            "summary": explanation.summary,
            "top_factors": [
                {
                    "feature": e.feature_name,
                    "value": e.feature_value,
                    "shap_value": e.shap_value,
                    "contribution": e.contribution,
                    "rank": e.importance_rank,
                }
                for e in explanation.top_factors
            ]
        }
