"""
Unit tests for blacklist/sanctions rule.
"""

import pytest
import sys
sys.path.insert(0, '.')

from app.services.risk.rules.blacklist import BlacklistRule


class TestBlacklistRule:
    """Test suite for BlacklistRule."""
    
    @pytest.fixture
    def rule(self):
        """Create a fresh BlacklistRule instance."""
        return BlacklistRule()
    
    def test_tornado_cash_router_blocked(self, rule):
        """Tornado Cash router should be instantly blocked."""
        data = {
            "address": "0x8589427373D6D84E98730D7795D8f6f8731FDA16",
            "transactions": []
        }
        result = rule.evaluate(data)
        
        assert result.triggered == True
        assert result.severity.value == "critical"
        assert result.score >= 90
    
    def test_tornado_cash_01_eth_blocked(self, rule):
        """Tornado Cash 0.1 ETH pool should be blocked."""
        data = {
            "address": "0x47ce0c6ed5b0ce3d3a51fdb1c52dc66a7c3c2936",
            "transactions": []
        }
        result = rule.evaluate(data)
        
        assert result.triggered == True
        assert result.severity.value == "critical"
    
    def test_normal_address_not_blocked(self, rule):
        """Normal address should not be blocked."""
        data = {
            "address": "0x1234567890abcdef1234567890abcdef12345678",
            "transactions": []
        }
        result = rule.evaluate(data)
        
        # May or may not trigger based on other factors
        # But should not have critical severity for unknown address
        if result.triggered:
            assert result.severity.value != "critical" or result.score < 90
    
    def test_case_insensitive_matching(self, rule):
        """Address matching should be case-insensitive."""
        data = {
            "address": "0X8589427373D6D84E98730D7795D8F6F8731FDA16",  # uppercase
            "transactions": []
        }
        result = rule.evaluate(data)
        
        assert result.triggered == True
    
    def test_counterparty_mixer_interaction(self, rule):
        """Transactions with mixer counterparties should be flagged."""
        data = {
            "address": "0x1234567890abcdef1234567890abcdef12345678",
            "transactions": [
                {
                    "from": "0x1234567890abcdef1234567890abcdef12345678",
                    "to": "0x8589427373D6D84E98730D7795D8f6f8731FDA16",  # Tornado
                    "value": 10.0
                }
            ]
        }
        result = rule.evaluate(data)
        
        assert result.triggered == True
        assert result.severity.value in ["high", "critical"]
    
    def test_lazarus_group_blocked(self, rule):
        """Known Lazarus Group address should be blocked."""
        # This is a known Lazarus Group address from OFAC
        data = {
            "address": "0x098B716B8Aaf21512996dC57EB0615e2383E2f96",
            "transactions": []
        }
        result = rule.evaluate(data)
        
        assert result.triggered == True
        assert result.severity.value == "critical"


class TestHealthCheck:
    """Simple test to verify test infrastructure works."""
    
    def test_import_works(self):
        """Verify imports work correctly."""
        from app.services.risk.rules.blacklist import BlacklistRule
        assert BlacklistRule is not None
    
    def test_rule_can_be_instantiated(self):
        """Verify rule can be created."""
        rule = BlacklistRule()
        assert rule.enabled == True
        assert rule.name == "blacklist_check"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
