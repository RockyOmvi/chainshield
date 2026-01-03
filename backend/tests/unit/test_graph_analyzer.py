"""
Unit tests for transaction graph analyzer.
"""

import pytest
from datetime import datetime, timedelta
import sys
sys.path.insert(0, '.')

from app.services.risk.graph_analyzer import (
    TransactionGraphAnalyzer,
    get_graph_analyzer,
    LayeringResult
)


class TestGraphAnalyzer:
    """Test suite for TransactionGraphAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        """Create a fresh analyzer instance."""
        return TransactionGraphAnalyzer()
    
    @pytest.fixture
    def simple_transactions(self):
        """Simple transaction set for testing."""
        now = datetime.utcnow()
        return [
            {"from": "0xA", "to": "0xB", "value": 10.0, "timestamp": now},
            {"from": "0xB", "to": "0xC", "value": 9.0, "timestamp": now + timedelta(minutes=10)},
            {"from": "0xC", "to": "0xD", "value": 8.0, "timestamp": now + timedelta(minutes=20)},
        ]
    
    @pytest.fixture
    def mixer_transactions(self):
        """Transactions involving a mixer."""
        now = datetime.utcnow()
        return [
            {"from": "0xUser", "to": "0x8589427373d6d84e98730d7795d8f6f8731fda16", 
             "value": 5.0, "timestamp": now},  # Deposit to Tornado Cash
        ]
    
    def test_no_layering_empty_txs(self, analyzer):
        """Empty transactions should not detect layering."""
        result = analyzer.detect_layering("0xA", [], depth=3)
        
        assert result.detected == False
        assert result.confidence == 0.0
    
    def test_detects_layering_path(self, analyzer, simple_transactions):
        """Should detect layering in A->B->C->D pattern."""
        result = analyzer.detect_layering("0xA", simple_transactions, depth=4)
        
        # A->B->C->D is a 3-hop path
        assert result.detected == True
        assert result.depth >= 2
        assert len(result.path) >= 3
    
    def test_layering_risk_score(self, analyzer, simple_transactions):
        """Layering should have positive risk score."""
        result = analyzer.detect_layering("0xA", simple_transactions, depth=4)
        
        if result.detected:
            assert result.risk_score > 0
    
    def test_mixer_path_detection(self, analyzer, mixer_transactions):
        """Should detect transactions to known mixers."""
        paths = analyzer.find_mixer_paths(mixer_transactions, "0xUser")
        
        assert len(paths) == 1
        assert paths[0]["type"] == "deposit_to_mixer"
        assert paths[0]["value"] == 5.0
    
    def test_build_cluster(self, analyzer, simple_transactions):
        """Should build counterparty cluster."""
        # Add more transactions to/from 0xB
        txs = [
            {"from": "0xA", "to": "0xB", "value": 10.0, "timestamp": datetime.utcnow()},
            {"from": "0xB", "to": "0xC", "value": 5.0, "timestamp": datetime.utcnow()},
            {"from": "0xB", "to": "0xD", "value": 3.0, "timestamp": datetime.utcnow()},
            {"from": "0xE", "to": "0xB", "value": 7.0, "timestamp": datetime.utcnow()},
        ]
        
        cluster = analyzer.build_cluster(txs, "0xB")
        
        assert cluster.center_address == "0xB"
        assert cluster.cluster_size >= 3  # A, C, D, E
        assert cluster.total_incoming > 0
        assert cluster.total_outgoing > 0
    
    def test_fan_pattern_detection(self, analyzer):
        """Should detect fan-out patterns."""
        now = datetime.utcnow()
        
        # One sender to many receivers
        txs = [
            {"from": "0xSender", "to": f"0xReceiver{i}", "value": 1.0, "timestamp": now}
            for i in range(10)
        ]
        
        result = analyzer.detect_fan_pattern(txs, "0xSender", threshold=5)
        
        assert result["fan_out"] == True
        assert result["fan_out_count"] == 10
    
    def test_fan_in_detection(self, analyzer):
        """Should detect fan-in patterns."""
        now = datetime.utcnow()
        
        # Many senders to one receiver
        txs = [
            {"from": f"0xSender{i}", "to": "0xReceiver", "value": 1.0, "timestamp": now}
            for i in range(10)
        ]
        
        result = analyzer.detect_fan_pattern(txs, "0xReceiver", threshold=5)
        
        assert result["fan_in"] == True
        assert result["fan_in_count"] == 10
    
    def test_concentration_score(self, analyzer):
        """Concentration should be high when one counterparty dominates."""
        now = datetime.utcnow()
        
        txs = [
            {"from": "0xCenter", "to": "0xBigReceiver", "value": 100.0, "timestamp": now},
            {"from": "0xCenter", "to": "0xSmall1", "value": 1.0, "timestamp": now},
            {"from": "0xCenter", "to": "0xSmall2", "value": 1.0, "timestamp": now},
        ]
        
        cluster = analyzer.build_cluster(txs, "0xCenter")
        
        # 0xBigReceiver gets 100 out of 102 total
        assert cluster.concentration_score > 0.9
    
    def test_singleton_works(self):
        """get_graph_analyzer should return same instance."""
        analyzer1 = get_graph_analyzer()
        analyzer2 = get_graph_analyzer()
        
        assert analyzer1 is analyzer2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
