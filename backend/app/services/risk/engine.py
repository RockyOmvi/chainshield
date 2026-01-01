"""
ChainShield Risk Engine

The main orchestrator that combines all risk assessment layers.

Architecture:
┌─────────────────────────────────────────────────────────────────┐
│                      RISK ENGINE                                │
├─────────────────────────────────────────────────────────────────┤
│  Input: Wallet/Transaction Data                                 │
│         ↓                                                       │
│  ┌─────────────────┐                                           │
│  │ Feature Extract │ → 30+ features                            │
│  └────────┬────────┘                                           │
│           ↓                                                     │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ LAYER 1: Rules      │ Blacklist, Velocity, Patterns    │    │
│  │ LAYER 2: Heuristics │ Not implemented yet              │    │
│  │ LAYER 3: ML         │ Classifier + Anomaly Detector    │    │
│  └────────────────────────────────────────────────────────┘    │
│           ↓                                                     │
│  ┌─────────────────┐                                           │
│  │ Score Aggregator│ → Weighted combination                    │
│  └────────┬────────┘                                           │
│           ↓                                                     │
│  Output: RiskAssessment (score, level, factors)                │
└─────────────────────────────────────────────────────────────────┘
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import structlog

from app.services.risk.config import RiskConfig, risk_config
from app.services.risk.features import (
    WalletFeatureExtractor,
    TransactionFeatureExtractor,
    FeatureVector,
)
from app.services.risk.rules import rule_registry
from app.services.risk.ml.model import RiskClassifier
from app.services.risk.ml.anomaly import AnomalyDetector
from app.services.risk.heuristics import HeuristicsAggregator

logger = structlog.get_logger()


@dataclass
class RiskFactor:
    """A single risk factor contributing to the score."""
    name: str
    description: str
    score_contribution: float
    source: str  # "rule", "heuristic", or "ml"


@dataclass
class RiskAssessment:
    """
    Complete risk assessment result.
    
    This is what gets returned to the API.
    """
    # Core results
    risk_score: float  # 0-100
    risk_level: str    # LOW/MEDIUM/HIGH/CRITICAL
    confidence: float  # 0-1, how confident in the assessment
    
    # Explainability
    risk_factors: List[RiskFactor] = field(default_factory=list)
    summary: str = ""
    
    # Layer breakdown
    rule_score: float = 0.0
    heuristic_score: float = 0.0
    ml_score: float = 0.0
    anomaly_score: float = 0.0
    
    # Metadata
    processing_time_ms: float = 0.0
    layers_evaluated: List[str] = field(default_factory=list)
    blocked: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to API response format."""
        return {
            "risk_score": round(self.risk_score, 2),
            "risk_level": self.risk_level,
            "confidence": round(self.confidence, 2),
            "blocked": self.blocked,
            "summary": self.summary,
            "risk_factors": [
                {
                    "name": f.name,
                    "description": f.description,
                    "contribution": round(f.score_contribution, 2),
                    "source": f.source,
                }
                for f in self.risk_factors[:10]
            ],
            "layer_scores": {
                "rules": round(self.rule_score, 2),
                "heuristics": round(self.heuristic_score, 2),
                "ml": round(self.ml_score, 2),
                "anomaly": round(self.anomaly_score, 2),
            },
            "metadata": {
                "processing_time_ms": round(self.processing_time_ms, 2),
                "layers_evaluated": self.layers_evaluated,
            }
        }


class RiskEngine:
    """
    Main risk assessment engine.
    
    Orchestrates:
    1. Feature extraction
    2. Rule evaluation
    3. ML prediction
    4. Score aggregation
    5. Result formatting
    """
    
    def __init__(self, config: Optional[RiskConfig] = None):
        """
        Initialize the risk engine.
        
        Args:
            config: Optional custom configuration
        """
        self.config = config or risk_config
        self.logger = logger.bind(module="risk_engine")
        
        # Initialize components
        self.wallet_extractor = WalletFeatureExtractor()
        self.tx_extractor = TransactionFeatureExtractor()
        
        # Initialize rule registry
        rule_registry.initialize_defaults()
        
        # Initialize ML models (with graceful fallback)
        self.classifier = RiskClassifier()
        self.anomaly_detector = AnomalyDetector()
        
        # Initialize heuristics aggregator (Layer 2)
        self.heuristics = HeuristicsAggregator()
        
        self.logger.info("risk_engine_initialized")
    
    async def assess_wallet(
        self, 
        wallet_data: Dict[str, Any]
    ) -> RiskAssessment:
        """
        Perform full risk assessment on a wallet.
        
        Args:
            wallet_data: Dictionary containing:
                - address: Wallet address
                - balance: Current balance
                - transactions: List of transactions
                - first_seen: First activity timestamp
                
        Returns:
            Complete RiskAssessment
        """
        start_time = datetime.utcnow()
        layers_evaluated = []
        risk_factors = []
        
        try:
            # Step 1: Extract features
            features = self.wallet_extractor.extract(wallet_data)
            context = {"features": features.features}
            
            # Step 2: Evaluate rules (Layer 1)
            rule_result = rule_registry.evaluate_all(wallet_data, context)
            rule_score = rule_result["combined_score"]
            layers_evaluated.append("rules")
            
            # Add rule factors
            rule_factors = rule_result.get("factors") or []
            for factor in rule_factors:
                risk_factors.append(RiskFactor(
                    name="rule_match",
                    description=factor,
                    score_contribution=rule_score / max(len(rule_factors), 1),
                    source="rule"
                ))
            
            # Check for blocking rule
            if rule_result.get("blocked"):
                return self._create_blocked_assessment(
                    rule_result, features, start_time, layers_evaluated
                )
            
            # Step 3: Heuristics evaluation (Layer 2)
            heuristic_result = self.heuristics.evaluate_all(features.features)
            heuristic_score = heuristic_result["combined_score"]
            layers_evaluated.append("heuristics")
            
            for factor in heuristic_result.get("factors", []):
                risk_factors.append(RiskFactor(
                    name="heuristic_match",
                    description=factor,
                    score_contribution=heuristic_score / max(len(heuristic_result.get("factors", [])), 1),
                    source="heuristic"
                ))
            
            # Step 4: ML prediction (Layer 3)
            ml_score, ml_factors = self.classifier.predict(features)
            layers_evaluated.append("ml")
            
            for name, contribution in ml_factors:
                risk_factors.append(RiskFactor(
                    name=name,
                    description=f"ML feature: {name}",
                    score_contribution=contribution,
                    source="ml"
                ))
            
            # Step 5: Anomaly detection
            anomaly_score, anomaly_severity, anomaly_factors = self.anomaly_detector.detect(
                features
            )
            layers_evaluated.append("anomaly")
            
            for factor in anomaly_factors:
                risk_factors.append(RiskFactor(
                    name="anomaly",
                    description=factor,
                    score_contribution=anomaly_score / max(len(anomaly_factors), 1),
                    source="ml"
                ))
            
            # Step 6: Graph Analysis (if transactions available)
            graph_score = 0.0
            try:
                from app.services.risk.graph.metrics import GraphMetricsExtractor
                from app.services.risk.graph.builder import TransactionGraphBuilder
                
                transactions = wallet_data.get("transactions", [])
                if transactions and len(transactions) >= 3:
                    # Build transaction graph
                    builder = TransactionGraphBuilder()
                    builder.build_from_transactions(transactions)
                    
                    # Extract graph features
                    extractor = GraphMetricsExtractor()
                    graph_features = extractor.extract_metrics(builder, wallet_data.get("address", ""))
                    
                    # Calculate graph risk score
                    if graph_features:
                        # High centrality = potential hub = higher risk
                        centrality = graph_features.get("degree_centrality", 0)
                        clustering = graph_features.get("clustering_coefficient", 0)
                        
                        # High centrality with low clustering = suspicious
                        if centrality > 0.5 and clustering < 0.2:
                            graph_score = 20.0
                            risk_factors.append(RiskFactor(
                                name="high_centrality_hub",
                                description=f"Hub wallet with {centrality:.1%} centrality",
                                score_contribution=graph_score,
                                source="graph"
                            ))
                        
                        layers_evaluated.append("graph")
            except ImportError:
                pass  # Graph modules optional
            except Exception as e:
                self.logger.debug("graph_analysis_skipped", reason=str(e))
            
            # Step 7: Cross-Chain Analysis
            crosschain_score = 0.0
            try:
                from app.blockchain.bridges import get_bridge_registry
                
                transactions = wallet_data.get("transactions", [])
                
                # Check bridge interactions
                bridge_registry = get_bridge_registry()
                bridge_txs = 0
                high_risk_bridges = 0
                
                for tx in transactions:
                    to_addr = tx.get("to", "")
                    is_bridge, bridge_name, risk_level = bridge_registry.is_bridge_transaction(to_addr)
                    if is_bridge:
                        bridge_txs += 1
                        if risk_level == "high":
                            high_risk_bridges += 1
                
                if bridge_txs > 0:
                    # Bridge usage adds risk
                    crosschain_score = min(bridge_txs * 2 + high_risk_bridges * 10, 30.0)
                    risk_factors.append(RiskFactor(
                        name="bridge_usage",
                        description=f"{bridge_txs} bridge transactions ({high_risk_bridges} high-risk)",
                        score_contribution=crosschain_score,
                        source="crosschain"
                    ))
                    layers_evaluated.append("crosschain")
            except ImportError:
                pass  # Cross-chain modules optional
            except Exception as e:
                self.logger.debug("crosschain_analysis_skipped", reason=str(e))
            
            # Step 8: Aggregate scores (including new layers)
            final_score, confidence = self._aggregate_scores(
                rule_score=rule_score,
                heuristic_score=heuristic_score,
                ml_score=ml_score,
                anomaly_score=anomaly_score,
                graph_score=graph_score,
                crosschain_score=crosschain_score
            )
            
            # Step 6: Determine risk level
            risk_level = self.config.thresholds.get_level(final_score)
            
            # Step 7: Generate summary
            summary = self._generate_summary(
                risk_level, final_score, risk_factors
            )
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return RiskAssessment(
                risk_score=final_score,
                risk_level=risk_level,
                confidence=confidence,
                risk_factors=sorted(
                    risk_factors, 
                    key=lambda x: x.score_contribution, 
                    reverse=True
                )[:self.config.max_risk_factors],
                summary=summary,
                rule_score=rule_score,
                heuristic_score=heuristic_score,
                ml_score=ml_score,
                anomaly_score=anomaly_score,
                processing_time_ms=processing_time,
                layers_evaluated=layers_evaluated,
                blocked=False
            )
            
        except Exception as e:
            self.logger.error(
                "risk_assessment_failed",
                error=str(e),
                address=wallet_data.get("address")
            )
            return self._create_error_assessment(str(e), start_time)
    
    async def assess_transaction(
        self, 
        tx_data: Dict[str, Any],
        sender_data: Optional[Dict[str, Any]] = None,
        receiver_data: Optional[Dict[str, Any]] = None
    ) -> RiskAssessment:
        """
        Perform risk assessment on a transaction.
        
        Similar to wallet assessment but transaction-focused.
        """
        start_time = datetime.utcnow()
        layers_evaluated = []
        risk_factors = []
        
        try:
            # Extract transaction features
            features = self.tx_extractor.extract(
                tx_data, sender_data, receiver_data
            )
            
            # Build context for rules
            context = {
                "features": features.features,
                "sender": sender_data,
                "receiver": receiver_data,
            }
            
            # Wrap tx as single-transaction wallet for rule evaluation
            tx_wallet_data = {
                "address": tx_data.get("from", ""),
                "transactions": [tx_data],
            }
            
            # Evaluate rules
            rule_result = rule_registry.evaluate_all(tx_wallet_data, context)
            rule_score = rule_result["combined_score"]
            layers_evaluated.append("rules")
            
            # ML prediction using transaction features
            ml_score = self.config.ml_config.fallback_score
            if sender_data:
                sender_features = self.wallet_extractor.extract(sender_data)
                ml_score, _ = self.classifier.predict(sender_features)
            layers_evaluated.append("ml")
            
            # Aggregate
            final_score, confidence = self._aggregate_scores(
                rule_score=rule_score,
                heuristic_score=0.0,
                ml_score=ml_score,
                anomaly_score=0.0
            )
            
            risk_level = self.config.thresholds.get_level(final_score)
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return RiskAssessment(
                risk_score=final_score,
                risk_level=risk_level,
                confidence=confidence,
                risk_factors=risk_factors,
                summary=f"Transaction risk: {risk_level}",
                rule_score=rule_score,
                ml_score=ml_score,
                processing_time_ms=processing_time,
                layers_evaluated=layers_evaluated,
                blocked=rule_result.get("blocked", False)
            )
            
        except Exception as e:
            self.logger.error("tx_risk_assessment_failed", error=str(e))
            return self._create_error_assessment(str(e), start_time)
    
    def _aggregate_scores(
        self,
        rule_score: float,
        heuristic_score: float,
        ml_score: float,
        anomaly_score: float,
        graph_score: float = 0.0,
        crosschain_score: float = 0.0
    ) -> Tuple[float, float]:
        """
        Aggregate layer scores into final score.
        
        Returns:
            Tuple of (final_score, confidence)
        """
        weights = self.config.layer_weights
        
        # Calculate weighted score
        total_weight = 0.0
        weighted_sum = 0.0
        
        if rule_score > 0:
            weighted_sum += weights["rules"] * rule_score
            total_weight += weights["rules"]
        
        if heuristic_score > 0:
            weighted_sum += weights["heuristics"] * heuristic_score
            total_weight += weights["heuristics"]
        
        if ml_score > 0:
            weighted_sum += weights["ml"] * ml_score
            total_weight += weights["ml"]
        
        # Anomaly adds on top (not averaged in)
        anomaly_boost = min(anomaly_score * 0.3, 20)  # Max 20 point boost
        
        # Graph score adds on top
        graph_boost = min(graph_score, 20)  # Max 20 point boost
        
        # Cross-chain score adds on top
        crosschain_boost = min(crosschain_score, 30)  # Max 30 point boost
        
        if total_weight > 0:
            base_score = weighted_sum / total_weight
        else:
            base_score = (rule_score + ml_score) / 2
        
        final_score = min(base_score + anomaly_boost + graph_boost + crosschain_boost, 100)
        
        # Confidence based on agreement between layers
        scores = [s for s in [rule_score, ml_score, anomaly_score] if s > 0]
        if len(scores) >= 2:
            avg = sum(scores) / len(scores)
            variance = sum((s - avg) ** 2 for s in scores) / len(scores)
            # Lower variance = higher confidence
            confidence = max(0.5, 1 - (variance / 1000))
        else:
            confidence = 0.6  # Lower confidence with fewer layers
        
        return round(final_score, 2), round(confidence, 2)
    
    def _generate_summary(
        self,
        risk_level: str,
        score: float,
        factors: List[RiskFactor]
    ) -> str:
        """Generate human-readable risk summary."""
        if risk_level == "CRITICAL":
            return f"CRITICAL RISK ({score:.0f}/100): Immediate attention required. {len(factors)} risk indicators found."
        elif risk_level == "HIGH":
            return f"High risk ({score:.0f}/100): Multiple risk factors detected. Review recommended."
        elif risk_level == "MEDIUM":
            return f"Medium risk ({score:.0f}/100): Some risk indicators present. Monitor activity."
        else:
            return f"Low risk ({score:.0f}/100): No significant risk factors detected."
    
    def _create_blocked_assessment(
        self,
        rule_result: Dict[str, Any],
        features: FeatureVector,
        start_time: datetime,
        layers_evaluated: List[str]
    ) -> RiskAssessment:
        """Create assessment for a blocked request."""
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        factors = rule_result.get("factors", ["Blocked by rule"])[:3]
        risk_factors = [
            RiskFactor(
                name="blocking_rule",
                description=f,
                score_contribution=100.0 / len(factors),
                source="rule"
            )
            for f in factors
        ]
        
        return RiskAssessment(
            risk_score=100.0,
            risk_level="CRITICAL",
            confidence=1.0,
            risk_factors=risk_factors,
            summary=f"BLOCKED: {factors[0] if factors else 'Unknown'}",
            rule_score=100.0,
            processing_time_ms=processing_time,
            layers_evaluated=layers_evaluated,
            blocked=True
        )
    
    def _create_error_assessment(
        self,
        error: str,
        start_time: datetime
    ) -> RiskAssessment:
        """Create assessment when an error occurs."""
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Return conservative score on error
        return RiskAssessment(
            risk_score=50.0,  # Medium risk on error
            risk_level="MEDIUM",
            confidence=0.0,  # Zero confidence
            summary=f"Error during assessment: {error}",
            processing_time_ms=processing_time,
            layers_evaluated=["error"]
        )
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """Get engine statistics and health."""
        return {
            "rule_registry": rule_registry.get_stats(),
            "classifier": self.classifier.get_model_info(),
            "anomaly_detector": self.anomaly_detector.get_model_info(),
            "config": {
                "layer_weights": self.config.layer_weights,
                "thresholds": {
                    "critical": self.config.thresholds.critical,
                    "high": self.config.thresholds.high,
                    "medium": self.config.thresholds.medium,
                }
            }
        }


# Lazy initialization to avoid import-time model loading
_risk_engine: Optional[RiskEngine] = None


def get_risk_engine() -> RiskEngine:
    """Get the global risk engine instance (lazy initialization)."""
    global _risk_engine
    if _risk_engine is None:
        _risk_engine = RiskEngine()
    return _risk_engine
