"""
API Endpoint Integration Tests

Tests for actual API endpoints with mocked services.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient
from datetime import datetime
from decimal import Decimal


class TestWalletEndpoints:
    """Integration tests for wallet endpoints."""
    
    @pytest.fixture
    def mock_wallet_service(self):
        """Mock the wallet service."""
        with patch("app.api.v1.wallet.wallet_service") as mock:
            yield mock
    
    @pytest.fixture
    def mock_api_key_auth(self):
        """Mock API key authentication to always pass."""
        with patch("app.api.deps.get_api_key_user") as mock:
            mock.return_value = {
                "user_id": "test_user",
                "api_key_id": "test_key",
                "scopes": ["read:wallet", "read:transaction"]
            }
            yield mock
    
    @pytest.mark.asyncio
    async def test_analyze_wallet_success(self, client: AsyncClient, mock_api_key_auth):
        """Test successful wallet analysis."""
        from app.schemas import WalletRiskScore, RiskLevel, WalletAnalyzeResponse
        from app.api.v1.wallet import wallet_service
        
        mock_response = WalletAnalyzeResponse(
            address="0xd8da6bf26964af9d7eed9e03e53415d37aa96045",
            chain="ethereum",
            risk=WalletRiskScore(
                score=42,
                level=RiskLevel.MEDIUM,
                confidence=0.85,
                tags=["test"]
            ),
            analyzed_at=datetime.utcnow()
        )
        
        with patch.object(wallet_service, "analyze_wallet", return_value=mock_response):
            response = await client.post(
                "/api/v1/wallet/analyze",
                json={
                    "address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
                    "chain": "ethereum"
                },
                headers={"X-API-Key": "cs_test_key"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["risk"]["score"] == 42
    
    @pytest.mark.asyncio
    async def test_analyze_wallet_invalid_address(self, client: AsyncClient):
        """Test wallet analysis with invalid address."""
        response = await client.post(
            "/api/v1/wallet/analyze",
            json={
                "address": "invalid_address",
                "chain": "ethereum"
            },
            headers={"X-API-Key": "cs_test_key"}
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_get_wallet_profile(self, client: AsyncClient, mock_api_key_auth):
        """Test getting wallet profile."""
        from app.schemas import WalletProfile, Chain
        from app.api.v1.wallet import wallet_service
        
        mock_profile = WalletProfile(
            address="0xd8da6bf26964af9d7eed9e03e53415d37aa96045",
            chain=Chain.ETHEREUM,
            balance_eth=10.5,
            total_tx_count=100,
            is_contract=False
        )
        
        with patch.object(wallet_service, "get_wallet_profile", return_value=mock_profile):
            response = await client.get(
                "/api/v1/wallet/0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
                headers={"X-API-Key": "cs_test_key"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestTransactionEndpoints:
    """Integration tests for transaction endpoints."""
    
    @pytest.mark.asyncio
    async def test_analyze_transaction_success(self, client: AsyncClient):
        """Test successful transaction analysis."""
        from app.schemas import TransactionAnalyzeResponse, TransactionRiskScore, RiskLevel
        from app.api.v1.transaction import transaction_service
        
        tx_hash = "0x" + "a" * 64
        mock_response = TransactionAnalyzeResponse(
            tx_hash=tx_hash,
            chain="ethereum",
            risk=TransactionRiskScore(
                score=25,
                level=RiskLevel.LOW,
                confidence=0.7,
                flags=[]
            ),
            analyzed_at=datetime.utcnow()
        )
        
        with patch.object(transaction_service, "analyze_transaction", return_value=mock_response):
            response = await client.post(
                "/api/v1/transaction/analyze",
                json={
                    "tx_hash": tx_hash,
                    "chain": "ethereum"
                },
                headers={"X-API-Key": "cs_test_key"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    @pytest.mark.asyncio
    async def test_analyze_transaction_invalid_hash(self, client: AsyncClient):
        """Test transaction analysis with invalid hash."""
        response = await client.post(
            "/api/v1/transaction/analyze",
            json={
                "tx_hash": "not_a_hash",
                "chain": "ethereum"
            },
            headers={"X-API-Key": "cs_test_key"}
        )
        
        assert response.status_code == 422  # Validation error


class TestExplainEndpoint:
    """Integration tests for explain endpoint."""
    
    @pytest.mark.asyncio
    async def test_explain_wallet(self, client: AsyncClient):
        """Test wallet explanation."""
        from app.api.v1.explain import generate_wallet_explanation
        
        mock_result = {
            "explanation": "Test explanation",
            "confidence": 0.8,
            "factors": ["factor1"],
            "recommendations": ["rec1"]
        }
        
        with patch("app.api.v1.explain.generate_wallet_explanation", return_value=mock_result):
            response = await client.post(
                "/api/v1/explain",
                json={
                    "target_type": "wallet",
                    "target_id": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
                },
                headers={"X-API-Key": "cs_test_key"}
            )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_explain_transaction(self, client: AsyncClient):
        """Test transaction explanation."""
        from app.api.v1.explain import generate_transaction_explanation
        
        mock_result = {
            "explanation": "Test tx explanation",
            "confidence": 0.7,
            "factors": ["factor1"],
            "recommendations": ["rec1"]
        }
        
        tx_hash = "0x" + "b" * 64
        with patch("app.api.v1.explain.generate_transaction_explanation", return_value=mock_result):
            response = await client.post(
                "/api/v1/explain",
                json={
                    "target_type": "transaction",
                    "target_id": tx_hash
                },
                headers={"X-API-Key": "cs_test_key"}
            )
        
        assert response.status_code == 200


class TestAuthenticationFlow:
    """Test authentication scenarios."""
    
    @pytest.mark.asyncio
    async def test_missing_api_key_rejected(self, client: AsyncClient):
        """Test request without API key is rejected."""
        response = await client.post(
            "/api/v1/wallet/analyze",
            json={
                "address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
            }
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_invalid_api_key_format_rejected(self, client: AsyncClient):
        """Test API key with wrong prefix is rejected."""
        response = await client.post(
            "/api/v1/wallet/analyze",
            json={
                "address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
            },
            headers={"X-API-Key": "wrong_prefix_key"}
        )
        
        assert response.status_code == 401
