"""
API Endpoint Tests

Integration tests for API endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


class TestWalletEndpoints:
    """Test wallet API endpoints."""
    
    def test_wallet_analyze_requires_auth(self):
        """Test wallet analyze requires authentication."""
        response = client.post(
            "/api/v1/wallet/analyze",
            json={
                "address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
                "chain": "ethereum"
            }
        )
        
        # Should require authentication
        assert response.status_code == 401
    
    def test_wallet_profile_requires_auth(self):
        """Test wallet profile requires authentication."""
        response = client.get(
            "/api/v1/wallet/0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        )
        
        # Should require authentication
        assert response.status_code == 401


class TestTransactionEndpoints:
    """Test transaction API endpoints."""
    
    def test_transaction_analyze_requires_auth(self):
        """Test transaction analyze requires authentication."""
        response = client.post(
            "/api/v1/transaction/analyze",
            json={
                "tx_hash": "0x" + "a" * 64,
                "chain": "ethereum"
            }
        )
        
        # Should require authentication
        assert response.status_code == 401
    
    def test_transaction_details_requires_auth(self):
        """Test transaction details requires authentication."""
        response = client.get(
            f"/api/v1/transaction/{'0x' + 'a' * 64}"
        )
        
        # Should require authentication
        assert response.status_code == 401


class TestExplainEndpoint:
    """Test explain API endpoints."""
    
    def test_explain_wallet_requires_auth(self):
        """Test explain wallet requires authentication."""
        response = client.post(
            "/api/v1/explain",
            json={
                "type": "wallet",
                "identifier": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
            }
        )
        
        # Should require authentication
        assert response.status_code == 401
    
    def test_explain_transaction_requires_auth(self):
        """Test explain transaction requires authentication."""
        response = client.post(
            "/api/v1/explain",
            json={
                "type": "transaction",
                "identifier": "0x" + "a" * 64
            }
        )
        
        # Should require authentication
        assert response.status_code == 401


class TestAPIAuthentication:
    """Test API authentication mechanisms."""
    
    def test_missing_api_key_returns_401(self):
        """Test missing API key returns 401."""
        response = client.post(
            "/api/v1/wallet/analyze",
            json={"address": "0x" + "a" * 40}
        )
        
        assert response.status_code == 401
    
    def test_invalid_api_key_returns_401(self):
        """Test invalid API key returns 401."""
        response = client.post(
            "/api/v1/wallet/analyze",
            headers={"X-API-Key": "invalid_key"},
            json={"address": "0x" + "a" * 40}
        )
        
        assert response.status_code == 401
