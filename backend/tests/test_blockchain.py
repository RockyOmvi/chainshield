"""
Blockchain Client Tests

Tests for blockchain provider client with mocked responses.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal

from app.services.blockchain.client import (
    BlockchainClient,
    EthereumProvider,
    WalletBalance,
    TransactionData,
)


class TestEthereumProvider:
    """Test Ethereum JSON-RPC provider."""
    
    @pytest.fixture
    def provider(self):
        """Create a provider for testing."""
        return EthereumProvider(
            name="test",
            base_url="http://localhost:8545"
        )
    
    @pytest.mark.asyncio
    async def test_get_balance_parses_hex(self, provider):
        """Test balance is parsed from hex correctly."""
        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": "0xde0b6b3a7640000"  # 1 ETH in wei
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(provider, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            balance = await provider.get_balance("0x" + "a" * 40)
            
            assert balance == 10**18  # 1 ETH in wei
    
    @pytest.mark.asyncio
    async def test_get_block_number(self, provider):
        """Test block number is parsed correctly."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": "0x10d4f1"  # Block 1102065
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(provider, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            block = await provider.get_block_number()
            
            assert block == 1102065


class TestBlockchainClient:
    """Test multi-provider blockchain client."""
    
    @pytest.fixture
    def client(self):
        """Create a blockchain client for testing."""
        return BlockchainClient()
    
    @pytest.mark.asyncio
    async def test_initialize_adds_public_provider(self, client):
        """Test initialization adds at least public provider."""
        await client.initialize()
        
        assert len(client._providers) >= 1
        assert client._providers[-1].name == "public"
    
    @pytest.mark.asyncio
    async def test_provider_rotation_on_failure(self, client):
        """Test provider rotates on failure."""
        await client.initialize()
        
        initial_index = client._current_provider_index
        client._rotate_provider()
        
        # If only one provider, index stays same
        # If multiple, it changes
        if len(client._providers) > 1:
            assert client._current_provider_index != initial_index


class TestWalletBalance:
    """Test WalletBalance dataclass."""
    
    def test_balance_conversion(self):
        """Test balance is created correctly."""
        balance = WalletBalance(
            address="0x" + "a" * 40,
            chain="ethereum",
            balance_wei=10**18,
            balance_eth=Decimal("1.0")
        )
        
        assert balance.balance_wei == 10**18
        assert balance.balance_eth == Decimal("1.0")
        assert balance.fetched_at is not None
    
    def test_address_stored(self):
        """Test address is stored correctly."""
        address = "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"
        balance = WalletBalance(
            address=address,
            chain="ethereum",
            balance_wei=0,
            balance_eth=Decimal("0")
        )
        
        assert balance.address == address


class TestTransactionData:
    """Test TransactionData dataclass."""
    
    def test_gas_cost_calculation(self):
        """Test gas cost is calculated correctly."""
        from datetime import datetime
        
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
            gas_price=10**9,  # 1 Gwei
            is_success=True,
            input_data="0x"
        )
        
        # Gas cost = 21000 * 10^9 / 10^18 = 0.000021 ETH
        assert tx.gas_cost_eth == Decimal("0.000021")
