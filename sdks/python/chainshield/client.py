"""
ChainShield SDK Main Client

The main client class for interacting with ChainShield API.
"""

import httpx
from typing import List, Optional, Dict, Any, Union
from urllib.parse import urljoin

from chainshield.models import (
    RiskAssessment,
    Chain,
    WebhookConfig,
    UsageInfo,
    AlertType,
)
from chainshield.exceptions import (
    ChainShieldError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    NotFoundError,
    ServerError,
)


class ChainShield:
    """
    ChainShield API Client.
    
    The main interface for interacting with ChainShield risk assessment API.
    
    Usage:
        client = ChainShield(api_key="cs_your_api_key")
        
        # Analyze a wallet
        result = client.analyze("0x742d35Cc...")
        print(f"Risk: {result.risk_score} ({result.risk_level})")
        
        # Check if sanctioned
        if client.is_sanctioned("0x123..."):
            print("Address is sanctioned!")
        
        # Batch analyze
        results = client.analyze_batch(["0x111...", "0x222..."])
    
    Args:
        api_key: Your ChainShield API key (starts with "cs_")
        base_url: API base URL (default: https://api.chainshield.io)
        timeout: Request timeout in seconds (default: 30)
    """
    
    DEFAULT_BASE_URL = "https://api.chainshield.io"
    API_VERSION = "v1"
    
    def __init__(
        self,
        api_key: str,
        base_url: str = None,
        timeout: float = 30.0
    ):
        if not api_key:
            raise AuthenticationError("API key is required")
        
        if not api_key.startswith("cs_"):
            raise AuthenticationError("Invalid API key format. Keys start with 'cs_'")
        
        self.api_key = api_key
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        
        self._client = httpx.Client(
            base_url=f"{self.base_url}/api/{self.API_VERSION}",
            headers={
                "X-API-Key": self.api_key,
                "Content-Type": "application/json",
                "User-Agent": "ChainShield-Python-SDK/1.0.0"
            },
            timeout=timeout
        )
    
    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Handle API response and raise appropriate errors."""
        if response.status_code == 200 or response.status_code == 201:
            return response.json()
        
        try:
            error_data = response.json()
            message = error_data.get("detail", str(error_data))
        except:
            message = response.text or f"HTTP {response.status_code}"
        
        if response.status_code == 401:
            raise AuthenticationError(message, status_code=401)
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(
                message, 
                retry_after=int(retry_after) if retry_after else None
            )
        elif response.status_code == 400:
            raise ValidationError(message, status_code=400)
        elif response.status_code == 404:
            raise NotFoundError(message, status_code=404)
        elif response.status_code >= 500:
            raise ServerError(message, status_code=response.status_code)
        else:
            raise ChainShieldError(message, status_code=response.status_code)
    
    # =========================================================================
    # Wallet Analysis
    # =========================================================================
    
    def analyze(
        self,
        address: str,
        chain: Union[Chain, str] = Chain.ETHEREUM
    ) -> RiskAssessment:
        """
        Analyze a wallet address for risk.
        
        Args:
            address: Wallet address to analyze
            chain: Blockchain network (default: ethereum)
        
        Returns:
            RiskAssessment with risk score and factors
        
        Example:
            result = client.analyze("0x742d35Cc...")
            if result.is_high_risk:
                print(f"High risk: {result.factors}")
        """
        if isinstance(chain, Chain):
            chain = chain.value
        
        response = self._client.post(
            "/wallet/analyze",
            json={"address": address, "chain": chain}
        )
        data = self._handle_response(response)
        return RiskAssessment.from_dict(data)
    
    def analyze_batch(
        self,
        addresses: List[str],
        chain: Union[Chain, str] = Chain.ETHEREUM
    ) -> List[RiskAssessment]:
        """
        Analyze multiple wallet addresses.
        
        Args:
            addresses: List of wallet addresses
            chain: Blockchain network
        
        Returns:
            List of RiskAssessment results
        """
        if isinstance(chain, Chain):
            chain = chain.value
        
        response = self._client.post(
            "/wallet/analyze/batch",
            json={"addresses": addresses, "chain": chain}
        )
        data = self._handle_response(response)
        return [RiskAssessment.from_dict(r) for r in data.get("results", [])]
    
    def is_sanctioned(self, address: str) -> bool:
        """
        Quick check if address is sanctioned/blocked.
        
        Args:
            address: Wallet address to check
        
        Returns:
            True if address is sanctioned
        """
        try:
            result = self.analyze(address)
            return result.blocked
        except:
            return False
    
    def is_high_risk(self, address: str, threshold: float = 70.0) -> bool:
        """
        Quick check if address is high risk.
        
        Args:
            address: Wallet address to check
            threshold: Risk score threshold (default: 70)
        
        Returns:
            True if risk score exceeds threshold
        """
        result = self.analyze(address)
        return result.risk_score >= threshold
    
    # =========================================================================
    # Usage & Account
    # =========================================================================
    
    def get_usage(self) -> UsageInfo:
        """
        Get current API usage statistics.
        
        Returns:
            UsageInfo with current usage and limits
        """
        response = self._client.get("/account/usage")
        data = self._handle_response(response)
        return UsageInfo.from_dict(data)
    
    # =========================================================================
    # Webhooks
    # =========================================================================
    
    def register_webhook(
        self,
        url: str,
        events: List[Union[AlertType, str]] = None,
        secret: str = None
    ) -> Dict[str, Any]:
        """
        Register a webhook for real-time alerts.
        
        Args:
            url: Webhook endpoint URL
            events: List of event types to subscribe to
            secret: Shared secret for HMAC verification
        
        Returns:
            Webhook configuration with ID
        """
        if events is None:
            events = [AlertType.HIGH_RISK, AlertType.BLOCKED]
        
        event_values = [
            e.value if isinstance(e, AlertType) else e 
            for e in events
        ]
        
        response = self._client.post(
            "/webhooks",
            json={
                "url": url,
                "events": event_values,
                "secret": secret
            }
        )
        return self._handle_response(response)
    
    def list_webhooks(self) -> List[Dict[str, Any]]:
        """List all registered webhooks."""
        response = self._client.get("/webhooks")
        return self._handle_response(response)
    
    def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook by ID."""
        response = self._client.delete(f"/webhooks/{webhook_id}")
        return response.status_code == 200
    
    # =========================================================================
    # Health
    # =========================================================================
    
    def health(self) -> Dict[str, Any]:
        """Check API health status."""
        response = self._client.get("/health")
        return self._handle_response(response)
    
    def ping(self) -> bool:
        """Quick connectivity check."""
        try:
            self.health()
            return True
        except:
            return False
    
    # =========================================================================
    # Context Manager
    # =========================================================================
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
    
    def close(self):
        """Close the HTTP client."""
        self._client.close()


# Async client for high-performance applications
class AsyncChainShield:
    """
    Async ChainShield API Client.
    
    Same as ChainShield but with async/await support.
    
    Usage:
        async with AsyncChainShield(api_key="cs_xxx") as client:
            result = await client.analyze("0x742d35Cc...")
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = None,
        timeout: float = 30.0
    ):
        self.api_key = api_key
        self.base_url = (base_url or ChainShield.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        
        self._client = httpx.AsyncClient(
            base_url=f"{self.base_url}/api/{ChainShield.API_VERSION}",
            headers={
                "X-API-Key": self.api_key,
                "Content-Type": "application/json",
                "User-Agent": "ChainShield-Python-SDK/1.0.0"
            },
            timeout=timeout
        )
    
    async def analyze(
        self,
        address: str,
        chain: Union[Chain, str] = Chain.ETHEREUM
    ) -> RiskAssessment:
        """Analyze a wallet address for risk."""
        if isinstance(chain, Chain):
            chain = chain.value
        
        response = await self._client.post(
            "/wallet/analyze",
            json={"address": address, "chain": chain}
        )
        
        if response.status_code != 200:
            raise ChainShieldError(response.text, response.status_code)
        
        return RiskAssessment.from_dict(response.json())
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self._client.aclose()
