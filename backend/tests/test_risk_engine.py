"""
Risk Engine Tests

Tests for the ML Risk Engine (Phase 3).
"""

import pytest
from datetime import datetime, timedelta

from app.services.risk import RiskEngine, WalletFeatureExtractor, FeatureVector
from app.services.risk.rules import BlacklistRule, VelocityRule, PatternRule
from app.services.risk.rules.base import RuleResult, RuleSeverity
from app.services.risk.ml.model import RiskClassifier
from app.services.risk.ml.anomaly import AnomalyDetector


class TestWalletFeatureExtractor:
    """Test wallet feature extraction."""
    
    @pytest.fixture
    def extractor(self):
        """Create feature extractor."""
        return WalletFeatureExtractor()
    
    @pytest.fixture
    def sample_wallet_data(self):
        """Sample wallet data for testing."""
        now = datetime.utcnow()
        return {
            "address": "0xd8da6bf26964af9d7eed9e03e53415d37aa96045",
            "balance": 10.5,
            "first_seen": (now - timedelta(days=30)).isoformat(),
            "transactions": [
                {
                    "hash": "0x" + "a" * 64,
                    "from": "0x1234567890abcdef" * 2 + "12345678",
                    "to": "0xd8da6bf26964af9d7eed9e03e53415d37aa96045",
                    "value": 5.0,
                    "gas_price": 50000000000,  # 50 gwei
                    "timestamp": (now - timedelta(hours=1)).isoformat(),
                },
                {
                    "hash": "0x" + "b" * 64,
                    "from": "0xd8da6bf26964af9d7eed9e03e53415d37aa96045",
                    "to": "0x9876543210fedcba" * 2 + "98765432",
                    "value": 2.0,
                    "gas_price": 45000000000,
                    "timestamp": now.isoformat(),
                },
            ]
        }
    
    def test_extract_basic_features(self, extractor, sample_wallet_data):
        """Test basic feature extraction."""
        result = extractor.extract(sample_wallet_data)
        
        assert isinstance(result, FeatureVector)
        assert result.features["balance_eth"] == 10.5
        assert result.features["tx_count_total"] == 2.0
    
    def test_extract_volume_features(self, extractor, sample_wallet_data):
        """Test volume feature extraction."""
        result = extractor.extract(sample_wallet_data)
        
        assert result.features["total_received_eth"] == 5.0
        assert result.features["total_sent_eth"] == 2.0
    
    def test_extract_age_features(self, extractor, sample_wallet_data):
        """Test age-related features."""
        result = extractor.extract(sample_wallet_data)
        
        # Should be approximately 30 days old
        assert result.features["age_days"] >= 29
        assert result.features["age_hours"] >= 700  # 30 days * 24


class TestBlacklistRule:
    """Test blacklist rule."""
    
    @pytest.fixture
    def rule(self):
        """Create blacklist rule."""
        return BlacklistRule()
    
    def test_clean_address_not_triggered(self, rule):
        """Test clean address doesn't trigger."""
        data = {
            "address": "0xd8da6bf26964af9d7eed9e03e53415d37aa96045",
            "transactions": []
        }
        
        result = rule.evaluate(data)
        
        assert result.triggered is False
    
    def test_mixer_interaction_triggers(self, rule):
        """Test mixer interaction triggers rule."""
        data = {
            "address": "0xd8da6bf26964af9d7eed9e03e53415d37aa96045",
            "transactions": [
                {
                    "from": "0xd8da6bf26964af9d7eed9e03e53415d37aa96045",
                    "to": "0x47ce0c6ed5b0ce3d3a51fdb1c52dc66a7c3c2936",  # Tornado
                    "value": 0.1
                }
            ]
        }
        
        result = rule.evaluate(data)
        
        assert result.triggered is True
        assert result.severity in [RuleSeverity.MEDIUM, RuleSeverity.HIGH]


class TestVelocityRule:
    """Test velocity rule."""
    
    @pytest.fixture
    def rule(self):
        """Create velocity rule."""
        return VelocityRule()
    
    def test_normal_velocity_not_triggered(self, rule):
        """Test normal activity doesn't trigger."""
        now = datetime.utcnow()
        data = {
            "address": "0xtest",
            "transactions": [
                {"timestamp": (now - timedelta(hours=i)).isoformat(), "value": 1.0}
                for i in range(5)
            ]
        }
        context = {"features": {"tx_per_hour_avg": 0.2, "volume_24h_eth": 5.0}}
        
        result = rule.evaluate(data, context)
        
        # Low velocity should not trigger
        assert result.score < 50


class TestRiskClassifier:
    """Test ML classifier."""
    
    @pytest.fixture
    def classifier(self):
        """Create classifier (uses fallback)."""
        return RiskClassifier()
    
    @pytest.fixture
    def sample_features(self):
        """Sample feature vector."""
        return FeatureVector(
            features={
                "age_hours": 720,  # 30 days
                "balance_eth": 10.0,
                "tx_count_total": 50,
                "mixer_interaction_count": 0,
                "tx_per_hour_avg": 2.0,
                "active_hours_entropy": 0.7,
            }
        )
    
    def test_predict_returns_score(self, classifier, sample_features):
        """Test prediction returns valid score."""
        score, factors = classifier.predict(sample_features)
        
        assert 0 <= score <= 100
        assert isinstance(factors, list)
    
    def test_fallback_mode(self, classifier):
        """Test fallback mode when model unavailable."""
        info = classifier.get_model_info()
        
        assert info["is_loaded"] is True


class TestAnomalyDetector:
    """Test anomaly detector."""
    
    @pytest.fixture
    def detector(self):
        """Create detector (uses fallback)."""
        return AnomalyDetector()
    
    @pytest.fixture
    def sample_features(self):
        """Sample feature vector."""
        return FeatureVector(
            features={
                "tx_per_hour_avg": 2.0,
                "volume_24h_eth": 5.0,
                "active_hours_entropy": 0.6,
                "counterparty_concentration": 0.3,
                "age_hours": 720,
                "tx_count_total": 50,
            }
        )
    
    def test_detect_returns_score_and_severity(self, detector, sample_features):
        """Test detection returns valid results."""
        score, severity, factors = detector.detect(sample_features)
        
        assert 0 <= score <= 100
        assert severity in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        assert isinstance(factors, list)


class TestRiskEngine:
    """Test main risk engine."""
    
    @pytest.fixture
    def engine(self):
        """Create risk engine."""
        return RiskEngine()
    
    @pytest.fixture
    def sample_wallet(self):
        """Sample wallet for testing."""
        now = datetime.utcnow()
        return {
            "address": "0xd8da6bf26964af9d7eed9e03e53415d37aa96045",
            "balance": 10.5,
            "first_seen": (now - timedelta(days=30)).isoformat(),
            "transactions": [
                {
                    "hash": "0x" + "a" * 64,
                    "from": "0x1234567890abcdef" * 2 + "12345678",
                    "to": "0xd8da6bf26964af9d7eed9e03e53415d37aa96045",
                    "value": 5.0,
                    "gas_price": 50000000000,
                    "timestamp": (now - timedelta(hours=1)).isoformat(),
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_assess_wallet_returns_assessment(self, engine, sample_wallet):
        """Test wallet assessment returns valid result."""
        result = await engine.assess_wallet(sample_wallet)
        
        assert result is not None
        assert 0 <= result.risk_score <= 100
        assert result.risk_level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        assert result.processing_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_assess_wallet_includes_layers(self, engine, sample_wallet):
        """Test all layers are evaluated."""
        result = await engine.assess_wallet(sample_wallet)
        
        assert "rules" in result.layers_evaluated
        assert "ml" in result.layers_evaluated
    
    def test_engine_stats(self, engine):
        """Test engine stats available."""
        stats = engine.get_engine_stats()
        
        assert "rule_registry" in stats
        assert "classifier" in stats
        assert "config" in stats
