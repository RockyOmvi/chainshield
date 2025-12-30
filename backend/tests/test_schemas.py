"""
Schema Validation Tests

Tests for Pydantic schema validation.
"""

import pytest
from pydantic import ValidationError

from app.schemas import (
    WalletAnalyzeRequest,
    TransactionAnalyzeRequest,
    ExplainRequest,
    Chain,
    RiskLevel,
)
from app.schemas.base import validate_ethereum_address, validate_tx_hash


class TestAddressValidation:
    """Test Ethereum address validation."""
    
    def test_valid_address_lowercase(self):
        """Test valid lowercase address."""
        address = "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"
        result = validate_ethereum_address(address)
        assert result == address
    
    def test_valid_address_checksummed(self):
        """Test valid checksummed address is normalized to lowercase."""
        address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        result = validate_ethereum_address(address)
        assert result == address.lower()
    
    def test_invalid_address_too_short(self):
        """Test address that's too short."""
        with pytest.raises(ValueError, match="42 characters"):
            validate_ethereum_address("0x123")
    
    def test_invalid_address_no_prefix(self):
        """Test address without 0x prefix."""
        with pytest.raises(ValueError, match="start with 0x"):
            validate_ethereum_address("d8da6bf26964af9d7eed9e03e53415d37aa96045")
    
    def test_invalid_address_non_hex(self):
        """Test address with non-hex characters."""
        with pytest.raises(ValueError, match="hex characters"):
            validate_ethereum_address("0xZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ")


class TestTxHashValidation:
    """Test transaction hash validation."""
    
    def test_valid_tx_hash(self):
        """Test valid transaction hash."""
        tx_hash = "0x" + "a" * 64
        result = validate_tx_hash(tx_hash)
        assert result == tx_hash
    
    def test_valid_tx_hash_mixed_case(self):
        """Test mixed case hash is normalized."""
        tx_hash = "0x" + "Aa" * 32
        result = validate_tx_hash(tx_hash)
        assert result == tx_hash.lower()
    
    def test_invalid_tx_hash_too_short(self):
        """Test hash that's too short."""
        with pytest.raises(ValueError, match="66 characters"):
            validate_tx_hash("0x123")
    
    def test_invalid_tx_hash_no_prefix(self):
        """Test hash without 0x prefix."""
        with pytest.raises(ValueError, match="start with 0x"):
            validate_tx_hash("a" * 64)


class TestWalletAnalyzeRequest:
    """Test WalletAnalyzeRequest schema."""
    
    def test_valid_request(self):
        """Test valid wallet analyze request."""
        request = WalletAnalyzeRequest(
            address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
            chain=Chain.ETHEREUM,
            include_history=True,
            include_explanation=True
        )
        assert request.address == "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"
        assert request.chain == Chain.ETHEREUM
    
    def test_default_values(self):
        """Test default values are set correctly."""
        request = WalletAnalyzeRequest(
            address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        )
        assert request.chain == Chain.ETHEREUM
        assert request.include_history is False
        assert request.include_explanation is False
    
    def test_invalid_address_rejected(self):
        """Test invalid address is rejected."""
        with pytest.raises(ValidationError):
            WalletAnalyzeRequest(address="invalid")


class TestTransactionAnalyzeRequest:
    """Test TransactionAnalyzeRequest schema."""
    
    def test_valid_request(self):
        """Test valid transaction analyze request."""
        request = TransactionAnalyzeRequest(
            tx_hash="0x" + "a" * 64,
            chain=Chain.ETHEREUM
        )
        assert len(request.tx_hash) == 66
    
    def test_invalid_hash_rejected(self):
        """Test invalid hash is rejected."""
        with pytest.raises(ValidationError):
            TransactionAnalyzeRequest(tx_hash="invalid")


class TestExplainRequest:
    """Test ExplainRequest schema with context validation."""
    
    def test_valid_wallet_explain(self):
        """Test valid wallet explanation request."""
        request = ExplainRequest(
            target_type="wallet",
            target_id="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        )
        assert request.target_type == "wallet"
    
    def test_valid_transaction_explain(self):
        """Test valid transaction explanation request."""
        request = ExplainRequest(
            target_type="transaction",
            target_id="0x" + "b" * 64
        )
        assert request.target_type == "transaction"
    
    def test_context_size_limit(self):
        """Test context size is limited to 10KB."""
        large_context = {"data": "x" * 20000}  # > 10KB
        with pytest.raises(ValidationError, match="10KB"):
            ExplainRequest(
                target_type="wallet",
                target_id="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
                context=large_context
            )
    
    def test_target_type_validation(self):
        """Test target_type must be wallet or transaction."""
        with pytest.raises(ValidationError):
            ExplainRequest(
                target_type="invalid",
                target_id="0x" + "a" * 40
            )
