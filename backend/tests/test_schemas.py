"""
Schema Validation Tests

Tests for Pydantic schemas and validation.
"""

import pytest
from pydantic import ValidationError

from app.schemas import (
    WalletAnalyzeRequest,
    TransactionAnalyzeRequest,
    Chain,
)


class TestAddressValidation:
    """Test Ethereum address validation."""
    
    def test_valid_address(self):
        """Test valid Ethereum address."""
        request = WalletAnalyzeRequest(
            address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        )
        assert request.address == "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"
    
    def test_address_lowercase_conversion(self):
        """Test address is converted to lowercase."""
        request = WalletAnalyzeRequest(
            address="0xD8DA6BF26964AF9D7EED9E03E53415D37AA96045"
        )
        assert request.address == request.address.lower()
    
    def test_invalid_address_too_short(self):
        """Test invalid address - too short."""
        with pytest.raises(ValidationError) as exc_info:
            WalletAnalyzeRequest(address="0x123")
        assert "address" in str(exc_info.value).lower()
    
    def test_invalid_address_no_prefix(self):
        """Test invalid address - no 0x prefix."""
        with pytest.raises(ValidationError) as exc_info:
            WalletAnalyzeRequest(address="d8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
        assert "address" in str(exc_info.value).lower()


class TestTxHashValidation:
    """Test transaction hash validation."""
    
    def test_valid_tx_hash(self):
        """Test valid transaction hash."""
        request = TransactionAnalyzeRequest(
            tx_hash="0x" + "a" * 64
        )
        assert request.tx_hash.startswith("0x")
    
    def test_invalid_tx_hash_too_short(self):
        """Test invalid tx hash - too short."""
        with pytest.raises(ValidationError) as exc_info:
            TransactionAnalyzeRequest(tx_hash="0x123")
        assert "tx_hash" in str(exc_info.value).lower()
    
    def test_invalid_tx_hash_no_prefix(self):
        """Test invalid tx hash - no 0x prefix."""
        with pytest.raises(ValidationError) as exc_info:
            TransactionAnalyzeRequest(tx_hash="a" * 64)
        assert "tx_hash" in str(exc_info.value).lower()


class TestWalletAnalyzeRequest:
    """Test WalletAnalyzeRequest schema."""
    
    def test_default_chain(self):
        """Test default chain is ethereum."""
        request = WalletAnalyzeRequest(
            address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        )
        assert request.chain == Chain.ETHEREUM
    
    def test_include_history_default(self):
        """Test include_history default is False."""
        request = WalletAnalyzeRequest(
            address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        )
        assert request.include_history is False


class TestTransactionAnalyzeRequest:
    """Test TransactionAnalyzeRequest schema."""
    
    def test_valid_request(self):
        """Test valid transaction analyze request."""
        request = TransactionAnalyzeRequest(
            tx_hash="0x" + "a" * 64,
            chain=Chain.ETHEREUM
        )
        assert request.chain == Chain.ETHEREUM
