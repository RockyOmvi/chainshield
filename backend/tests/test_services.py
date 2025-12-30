"""
Service Layer Tests

Tests for service layer functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.blockchain.wallet import WalletService
from app.services.blockchain.transaction import TransactionService
from app.schemas import Chain, RiskLevel


class TestWalletService:
    """Test wallet service functionality."""
    
    @pytest.fixture
    def wallet_service(self):
        """Create wallet service instance."""
        return WalletService()
    
    def test_wallet_service_creation(self, wallet_service):
        """Test wallet service can be created."""
        assert wallet_service is not None
    
    def test_score_to_level_high(self, wallet_service):
        """Test high risk score conversion."""
        level = wallet_service._score_to_level(85)
        assert level == RiskLevel.HIGH
    
    def test_score_to_level_medium(self, wallet_service):
        """Test medium risk score conversion."""
        level = wallet_service._score_to_level(55)
        assert level == RiskLevel.MEDIUM
    
    def test_score_to_level_low(self, wallet_service):
        """Test low risk score conversion."""
        level = wallet_service._score_to_level(25)
        assert level == RiskLevel.LOW


class TestTransactionService:
    """Test transaction service functionality."""
    
    @pytest.fixture
    def transaction_service(self):
        """Create transaction service instance."""
        return TransactionService()
    
    def test_transaction_service_creation(self, transaction_service):
        """Test transaction service can be created."""
        assert transaction_service is not None
    
    def test_score_to_level_high(self, transaction_service):
        """Test high risk score conversion."""
        level = transaction_service._score_to_level(80)
        assert level == RiskLevel.HIGH
    
    def test_score_to_level_medium(self, transaction_service):
        """Test medium risk score conversion."""
        level = transaction_service._score_to_level(50)
        assert level == RiskLevel.MEDIUM
    
    def test_score_to_level_low(self, transaction_service):
        """Test low risk score conversion."""
        level = transaction_service._score_to_level(20)
        assert level == RiskLevel.LOW
