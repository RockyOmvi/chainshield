"""
Wallet and Transaction Service Tests

Tests for the blockchain service layer.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from decimal import Decimal


class TestWalletService:
    """Tests for WalletService."""
    
    @pytest.fixture
    def wallet_service(self):
        """Create wallet service instance."""
        from app.services.blockchain.wallet import WalletService
        return WalletService()
    
    @pytest.mark.asyncio
    async def test_analyze_wallet_returns_response(self, wallet_service):
        """Test analyze_wallet returns proper response."""
        from app.schemas import WalletAnalyzeRequest, Chain
        from app.services.blockchain.client import WalletBalance
        
        request = WalletAnalyzeRequest(
            address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
            chain=Chain.ETHEREUM,
            include_history=True,
            include_explanation=True
        )
        
        mock_balance = WalletBalance(
            address="0xd8da6bf26964af9d7eed9e03e53415d37aa96045",
            chain="ethereum",
            balance_wei=10**18,
            balance_eth=Decimal("1.0")
        )
        
        with patch.object(wallet_service._client, "get_wallet_balance", return_value=mock_balance):
            with patch.object(wallet_service._client, "is_contract", return_value=False):
                with patch.object(wallet_service._client, "get_transaction_count", return_value=50):
                    response = await wallet_service.analyze_wallet(request)
        
        assert response.address == request.address.lower()
        assert response.risk is not None
        assert response.risk.score >= 0
    
    @pytest.mark.asyncio
    async def test_analyze_wallet_handles_blockchain_error(self, wallet_service):
        """Test analyze_wallet handles blockchain errors gracefully."""
        from app.schemas import WalletAnalyzeRequest, Chain, RiskLevel
        
        request = WalletAnalyzeRequest(
            address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
            chain=Chain.ETHEREUM
        )
        
        with patch.object(wallet_service._client, "get_wallet_balance", side_effect=Exception("RPC Error")):
            response = await wallet_service.analyze_wallet(request)
        
        assert response.risk.level == RiskLevel.UNKNOWN
        assert "blockchain_error" in response.risk.tags
    
    def test_calculate_preliminary_risk_new_wallet(self, wallet_service):
        """Test risk calculation for new wallet."""
        from app.services.blockchain.client import WalletBalance
        
        balance = WalletBalance(
            address="0x" + "a" * 40,
            chain="ethereum",
            balance_wei=0,
            balance_eth=Decimal("0")
        )
        
        score, tags = wallet_service._calculate_preliminary_risk(
            balance=balance,
            is_contract=False,
            tx_count=0
        )
        
        assert score > 20  # Base + new wallet bonus
        assert "new_wallet" in tags
    
    def test_calculate_preliminary_risk_high_value(self, wallet_service):
        """Test risk calculation for high value wallet."""
        from app.services.blockchain.client import WalletBalance
        
        balance = WalletBalance(
            address="0x" + "a" * 40,
            chain="ethereum",
            balance_wei=200 * 10**18,
            balance_eth=Decimal("200")
        )
        
        score, tags = wallet_service._calculate_preliminary_risk(
            balance=balance,
            is_contract=False,
            tx_count=100
        )
        
        assert "high_value" in tags
    
    def test_score_to_level_thresholds(self, wallet_service):
        """Test score to risk level conversion."""
        from app.schemas import RiskLevel
        
        assert wallet_service._score_to_level(0) == RiskLevel.UNKNOWN
        assert wallet_service._score_to_level(20) == RiskLevel.LOW
        assert wallet_service._score_to_level(50) == RiskLevel.MEDIUM
        assert wallet_service._score_to_level(80) == RiskLevel.HIGH


class TestTransactionService:
    """Tests for TransactionService."""
    
    @pytest.fixture
    def transaction_service(self):
        """Create transaction service instance."""
        from app.services.blockchain.transaction import TransactionService
        return TransactionService()
    
    def test_detect_tx_type_transfer(self, transaction_service):
        """Test transaction type detection for simple transfer."""
        from app.services.blockchain.client import TransactionData
        
        tx = TransactionData(
            tx_hash="0x" + "a" * 64,
            chain="ethereum",
            block_number=12345,
            timestamp=datetime.utcnow(),
            from_address="0x" + "a" * 40,
            to_address="0x" + "b" * 40,
            value_wei=10**18,
            value_eth=Decimal("1.0"),
            gas_used=21000,
            gas_price=10**9,
            is_success=True,
            input_data="0x"
        )
        
        tx_type = transaction_service._detect_tx_type(tx)
        assert tx_type == "transfer"
    
    def test_detect_tx_type_contract_creation(self, transaction_service):
        """Test transaction type detection for contract creation."""
        from app.services.blockchain.client import TransactionData
        
        tx = TransactionData(
            tx_hash="0x" + "a" * 64,
            chain="ethereum",
            block_number=12345,
            timestamp=datetime.utcnow(),
            from_address="0x" + "a" * 40,
            to_address=None,  # No recipient = contract creation
            value_wei=0,
            value_eth=Decimal("0"),
            gas_used=500000,
            gas_price=10**9,
            is_success=True,
            input_data="0x6080604052..."
        )
        
        tx_type = transaction_service._detect_tx_type(tx)
        assert tx_type == "contract_creation"
    
    def test_detect_tx_type_erc20_transfer(self, transaction_service):
        """Test transaction type detection for ERC-20 transfer."""
        from app.services.blockchain.client import TransactionData
        
        tx = TransactionData(
            tx_hash="0x" + "a" * 64,
            chain="ethereum",
            block_number=12345,
            timestamp=datetime.utcnow(),
            from_address="0x" + "a" * 40,
            to_address="0x" + "b" * 40,
            value_wei=0,
            value_eth=Decimal("0"),
            gas_used=65000,
            gas_price=10**9,
            is_success=True,
            input_data="0xa9059cbb000000000000000000000000...",  # transfer method
            method_id="0xa9059cbb"
        )
        
        tx_type = transaction_service._detect_tx_type(tx)
        assert tx_type == "erc20_transfer"
    
    def test_calculate_risk_failed_transaction(self, transaction_service):
        """Test risk calculation for failed transaction."""
        from app.services.blockchain.client import TransactionData
        
        tx = TransactionData(
            tx_hash="0x" + "a" * 64,
            chain="ethereum",
            block_number=12345,
            timestamp=datetime.utcnow(),
            from_address="0x" + "a" * 40,
            to_address="0x" + "b" * 40,
            value_wei=10**18,
            value_eth=Decimal("1.0"),
            gas_used=21000,
            gas_price=10**9,
            is_success=False,  # Failed
            input_data="0x"
        )
        
        score, flags = transaction_service._calculate_risk(tx)
        
        assert score > 15  # Base + failed bonus
        assert "failed" in flags
    
    def test_calculate_risk_high_value(self, transaction_service):
        """Test risk calculation for high value transaction."""
        from app.services.blockchain.client import TransactionData
        
        tx = TransactionData(
            tx_hash="0x" + "a" * 64,
            chain="ethereum",
            block_number=12345,
            timestamp=datetime.utcnow(),
            from_address="0x" + "a" * 40,
            to_address="0x" + "b" * 40,
            value_wei=150 * 10**18,
            value_eth=Decimal("150"),
            gas_used=21000,
            gas_price=10**9,
            is_success=True,
            input_data="0x"
        )
        
        score, flags = transaction_service._calculate_risk(tx)
        
        assert "high_value" in flags
        assert "very_high_value" in flags
