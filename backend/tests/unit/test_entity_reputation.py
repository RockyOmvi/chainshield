"""
Unit tests for entity reputation service.
"""

import pytest
import sys
sys.path.insert(0, '.')

from app.services.risk.entity_reputation import (
    EntityReputation,
    get_entity_reputation,
    KnownEntity
)


class TestEntityReputation:
    """Test suite for EntityReputation service."""
    
    @pytest.fixture
    def reputation(self):
        """Create a fresh EntityReputation instance."""
        return EntityReputation()
    
    def test_binance_known(self, reputation):
        """Binance hot wallet should be recognized."""
        entity = reputation.get_entity("0x28C6c06298d514Db089934071355E5743bf21d60")
        
        assert entity is not None
        assert "Binance" in entity.name
        assert entity.category == "exchange"
        assert entity.trust_score >= 0.9
    
    def test_coinbase_known(self, reputation):
        """Coinbase addresses should be recognized."""
        entity = reputation.get_entity("0x71660c4005ba85c37ccec55d0c4493e66fe775d3")
        
        assert entity is not None
        assert "Coinbase" in entity.name
        assert entity.trust_score >= 0.9
    
    def test_usdc_known(self, reputation):
        """USDC contract should be recognized."""
        entity = reputation.get_entity("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")
        
        assert entity is not None
        assert entity.name == "USDC"
        assert entity.category == "stablecoin"
        assert entity.trust_score >= 0.95
    
    def test_uniswap_known(self, reputation):
        """Uniswap router should be recognized."""
        entity = reputation.get_entity("0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D")
        
        assert entity is not None
        assert "Uniswap" in entity.name
        assert entity.category == "defi"
    
    def test_unknown_address(self, reputation):
        """Unknown address should return None."""
        entity = reputation.get_entity("0x0000000000000000000000000000000000000001")
        
        assert entity is None
    
    def test_case_insensitive_lookup(self, reputation):
        """Lookup should be case-insensitive."""
        entity1 = reputation.get_entity("0x28c6c06298d514db089934071355e5743bf21d60")  # lowercase
        entity2 = reputation.get_entity("0x28C6C06298D514DB089934071355E5743BF21D60")  # uppercase
        
        assert entity1 is not None
        assert entity2 is not None
        assert entity1.name == entity2.name
    
    def test_score_adjustment(self, reputation):
        """Score adjustment should reduce risk for trusted entities."""
        raw_score = 50.0
        
        # Binance has 0.9 trust, should reduce by 90%
        adjusted = reputation.adjust_score(
            "0x28C6c06298d514Db089934071355E5743bf21d60",
            raw_score
        )
        
        assert adjusted < raw_score
        assert adjusted == pytest.approx(5.0, abs=0.5)  # 50 * (1 - 0.9) = 5
    
    def test_score_adjustment_unknown(self, reputation):
        """Unknown address should get no score adjustment."""
        raw_score = 50.0
        adjusted = reputation.adjust_score(
            "0x0000000000000000000000000000000000000001",
            raw_score
        )
        
        assert adjusted == raw_score
    
    def test_is_trusted(self, reputation):
        """is_trusted should correctly identify trusted entities."""
        assert reputation.is_trusted("0x28C6c06298d514Db089934071355E5743bf21d60") == True
        assert reputation.is_trusted("0x0000000000000000000000000000000000000001") == False
    
    def test_get_by_category(self, reputation):
        """Should be able to filter by category."""
        exchanges = reputation.get_all_by_category("exchange")
        
        assert len(exchanges) > 0
        for addr, entity in exchanges.items():
            assert entity.category == "exchange"
    
    def test_entity_count(self, reputation):
        """Should have a reasonable number of known entities."""
        assert len(reputation.entities) >= 50  # We have 71+ defined


class TestKnownEntity:
    """Test the KnownEntity dataclass."""
    
    def test_entity_creation(self):
        """KnownEntity should be creatable."""
        entity = KnownEntity(
            name="Test Exchange",
            category="exchange",
            trust_score=0.85,
            chain="ethereum"
        )
        
        assert entity.name == "Test Exchange"
        assert entity.verified == True  # default
    
    def test_entity_notes(self):
        """Entity can have notes."""
        entity = KnownEntity(
            name="Defunct Exchange",
            category="exchange",
            trust_score=0.3,
            chain="ethereum",
            verified=False,
            notes="Bankrupt in 2022"
        )
        
        assert "Bankrupt" in entity.notes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
