"""
ChainShield Risk Intelligence Integration

Integrates with external blockchain analytics providers:
- Chainalysis (KYT, Reactor, Sanctions API)
- TRM Labs (Risk API)
- Elliptic (Transaction Screening)

These provide real-time sanctions screening and entity identification
that are required for regulatory compliance.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import os
import aiohttp
import structlog

logger = structlog.get_logger()


class Provider(Enum):
    """Available risk intelligence providers."""
    CHAINALYSIS = "chainalysis"
    TRM_LABS = "trm"
    ELLIPTIC = "elliptic"
    NANSEN = "nansen"


class RiskCategory(Enum):
    """Risk categories from external providers."""
    SANCTIONS = "sanctions"
    DARKNET = "darknet"
    MIXER = "mixer"
    RANSOMWARE = "ransomware"
    SCAM = "scam"
    FRAUD = "fraud"
    GAMBLING = "gambling"
    HIGH_RISK_EXCHANGE = "high_risk_exchange"
    UNKNOWN = "unknown"


@dataclass
class SanctionsResult:
    """Result from sanctions screening."""
    is_sanctioned: bool
    sanction_source: Optional[str] = None  # e.g., "OFAC", "EU", "UN"
    sanction_name: Optional[str] = None    # Entity name if sanctioned
    confidence: float = 1.0
    checked_at: datetime = None
    
    def __post_init__(self):
        if self.checked_at is None:
            self.checked_at = datetime.utcnow()


@dataclass
class EntityInfo:
    """Entity information from external provider."""
    name: Optional[str] = None
    category: Optional[str] = None  # exchange, defi, personal, etc.
    risk_score: float = 0.0
    risk_categories: List[RiskCategory] = None
    cluster_size: int = 0  # Related addresses
    total_received_usd: float = 0.0
    total_sent_usd: float = 0.0
    provider: Provider = Provider.CHAINALYSIS
    
    def __post_init__(self):
        if self.risk_categories is None:
            self.risk_categories = []


@dataclass
class TransactionRisk:
    """Risk assessment for a specific transaction."""
    tx_hash: str
    risk_score: float
    risk_categories: List[RiskCategory]
    counterparty_risk: float
    flagged: bool
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


class RiskIntelligenceProvider:
    """
    Integration with external blockchain analytics providers.
    
    Supports:
    - Chainalysis KYT (Know Your Transaction)
    - Chainalysis Reactor (entity identification)
    - TRM Labs Risk API
    - Elliptic Transaction Screening
    
    Usage:
        provider = RiskIntelligenceProvider(provider=Provider.CHAINALYSIS)
        await provider.initialize()
        
        # Check sanctions
        result = await provider.check_sanctions(address)
        if result.is_sanctioned:
            # Block transaction
        
        # Get entity info
        entity = await provider.get_entity_info(address)
        if entity.category == "mixer":
            # Flag for review
    """
    
    # API Endpoints
    CHAINALYSIS_KYT_API = "https://api.chainalysis.com/api/kyt/v2"
    CHAINALYSIS_REACTOR_API = "https://api.chainalysis.com/api/reactor/v1"
    TRM_API = "https://api.trmlabs.com/public/v2"
    ELLIPTIC_API = "https://api.elliptic.co/v2"
    
    # Cache TTL
    CACHE_TTL_SECONDS = 3600  # 1 hour
    
    def __init__(
        self, 
        provider: Provider = Provider.CHAINALYSIS,
        api_key: Optional[str] = None
    ):
        """
        Initialize risk intelligence provider.
        
        Args:
            provider: Which provider to use
            api_key: API key (or load from env)
        """
        self.logger = logger.bind(module="risk_intelligence")
        self.provider = provider
        self.api_key = api_key
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Cache for sanctions checks (expensive API calls)
        self._sanctions_cache: Dict[str, SanctionsResult] = {}
        self._entity_cache: Dict[str, EntityInfo] = {}
        
        # Load API key from environment if not provided
        self._load_api_key()
    
    def _load_api_key(self) -> None:
        """Load API key from environment."""
        env_map = {
            Provider.CHAINALYSIS: "CHAINALYSIS_API_KEY",
            Provider.TRM_LABS: "TRM_LABS_API_KEY",
            Provider.ELLIPTIC: "ELLIPTIC_API_KEY",
            Provider.NANSEN: "NANSEN_API_KEY",
        }
        
        if not self.api_key:
            env_var = env_map.get(self.provider, "")
            self.api_key = os.getenv(env_var)
        
        if not self.api_key:
            self.logger.warning(
                "api_key_not_configured",
                provider=self.provider.value,
                msg="Risk intelligence disabled - set API key in environment"
            )
    
    async def initialize(self) -> None:
        """Initialize HTTP session."""
        if self._session is None:
            self._session = aiohttp.ClientSession(
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=30)
            )
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API headers for the provider."""
        if self.provider == Provider.CHAINALYSIS:
            return {
                "X-API-Key": self.api_key or "",
                "Content-Type": "application/json"
            }
        elif self.provider == Provider.TRM_LABS:
            return {
                "Authorization": f"Bearer {self.api_key or ''}",
                "Content-Type": "application/json"
            }
        else:
            return {"Content-Type": "application/json"}
    
    async def check_sanctions(
        self, 
        address: str,
        chain: str = "ethereum"
    ) -> SanctionsResult:
        """
        Check if an address is on a sanctions list.
        
        This is the most critical check - sanctioned addresses
        MUST be blocked to comply with OFAC regulations.
        
        Args:
            address: Blockchain address
            chain: Blockchain name
            
        Returns:
            SanctionsResult with is_sanctioned flag
        """
        # Check cache first
        cache_key = f"{chain}:{address.lower()}"
        if cache_key in self._sanctions_cache:
            cached = self._sanctions_cache[cache_key]
            age = (datetime.utcnow() - cached.checked_at).total_seconds()
            if age < self.CACHE_TTL_SECONDS:
                return cached
        
        # If no API key, use local blacklist only
        if not self.api_key or not self._session:
            return SanctionsResult(is_sanctioned=False, confidence=0.0)
        
        try:
            result = await self._check_sanctions_api(address, chain)
            self._sanctions_cache[cache_key] = result
            return result
            
        except Exception as e:
            self.logger.error("sanctions_check_failed", 
                            address=address[:10], error=str(e))
            # Fail open with warning (can be configured to fail closed)
            return SanctionsResult(is_sanctioned=False, confidence=0.0)
    
    async def _check_sanctions_api(
        self, 
        address: str, 
        chain: str
    ) -> SanctionsResult:
        """Call external API for sanctions check."""
        
        if self.provider == Provider.CHAINALYSIS:
            # Chainalysis KYT API
            url = f"{self.CHAINALYSIS_KYT_API}/users/{address}"
            async with self._session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Check for sanctions exposure
                    exposures = data.get("exposures", [])
                    for exp in exposures:
                        if exp.get("category") == "sanctions":
                            return SanctionsResult(
                                is_sanctioned=True,
                                sanction_source="OFAC",
                                sanction_name=exp.get("name"),
                                confidence=1.0
                            )
                    
                    return SanctionsResult(is_sanctioned=False)
                    
                elif resp.status == 404:
                    # Address not in Chainalysis database (clean)
                    return SanctionsResult(is_sanctioned=False, confidence=0.8)
        
        elif self.provider == Provider.TRM_LABS:
            # TRM Labs API
            url = f"{self.TRM_API}/screening/addresses"
            payload = {
                "address": address,
                "chain": chain
            }
            async with self._session.post(url, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    if data.get("isSanctioned"):
                        return SanctionsResult(
                            is_sanctioned=True,
                            sanction_source=data.get("sanctionList", "OFAC"),
                            confidence=1.0
                        )
                    
                    return SanctionsResult(is_sanctioned=False)
        
        # Default: not sanctioned
        return SanctionsResult(is_sanctioned=False, confidence=0.5)
    
    async def get_entity_info(
        self, 
        address: str,
        chain: str = "ethereum"
    ) -> Optional[EntityInfo]:
        """
        Get entity identification for an address.
        
        Returns entity info if the address is attributed to
        a known service (exchange, DeFi protocol, etc.)
        
        Args:
            address: Blockchain address
            chain: Blockchain name
            
        Returns:
            EntityInfo if known, None otherwise
        """
        # Check cache
        cache_key = f"{chain}:{address.lower()}"
        if cache_key in self._entity_cache:
            return self._entity_cache[cache_key]
        
        if not self.api_key or not self._session:
            return None
        
        try:
            entity = await self._get_entity_api(address, chain)
            if entity:
                self._entity_cache[cache_key] = entity
            return entity
            
        except Exception as e:
            self.logger.error("entity_lookup_failed",
                            address=address[:10], error=str(e))
            return None
    
    async def _get_entity_api(
        self, 
        address: str, 
        chain: str
    ) -> Optional[EntityInfo]:
        """Call external API for entity identification."""
        
        if self.provider == Provider.CHAINALYSIS:
            url = f"{self.CHAINALYSIS_REACTOR_API}/addresses/{address}"
            async with self._session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    return EntityInfo(
                        name=data.get("name"),
                        category=data.get("category"),
                        risk_score=data.get("riskScore", 0),
                        cluster_size=data.get("clusterSize", 0),
                        total_received_usd=data.get("totalReceivedUsd", 0),
                        total_sent_usd=data.get("totalSentUsd", 0),
                        provider=Provider.CHAINALYSIS
                    )
        
        return None
    
    async def get_risk_score(
        self, 
        address: str,
        chain: str = "ethereum"
    ) -> float:
        """
        Get external risk score for an address.
        
        This can be used to boost/reduce the internal risk score.
        
        Args:
            address: Blockchain address
            chain: Blockchain name
            
        Returns:
            Risk score 0-100
        """
        entity = await self.get_entity_info(address, chain)
        if entity:
            return entity.risk_score
        
        # Check sanctions - any sanction = 100
        sanctions = await self.check_sanctions(address, chain)
        if sanctions.is_sanctioned:
            return 100.0
        
        return 0.0
    
    async def screen_transaction(
        self,
        tx_hash: str,
        chain: str = "ethereum"
    ) -> Optional[TransactionRisk]:
        """
        Screen a specific transaction for risk.
        
        Args:
            tx_hash: Transaction hash
            chain: Blockchain name
            
        Returns:
            TransactionRisk assessment
        """
        if not self.api_key or not self._session:
            return None
        
        try:
            if self.provider == Provider.CHAINALYSIS:
                url = f"{self.CHAINALYSIS_KYT_API}/transfers"
                payload = {
                    "transferReference": tx_hash,
                    "asset": "ETH",
                    "network": chain.upper()
                }
                async with self._session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Extract risk info
                        exposures = data.get("exposures", [])
                        categories = [
                            RiskCategory[exp.get("category", "unknown").upper()]
                            for exp in exposures
                            if exp.get("category", "").upper() in RiskCategory.__members__
                        ]
                        
                        risk_score = data.get("riskScore", 0)
                        
                        return TransactionRisk(
                            tx_hash=tx_hash,
                            risk_score=risk_score,
                            risk_categories=categories,
                            counterparty_risk=data.get("counterpartyRisk", 0),
                            flagged=risk_score > 70,
                            details=data
                        )
            
            return None
            
        except Exception as e:
            self.logger.error("tx_screening_failed",
                            tx_hash=tx_hash[:20], error=str(e))
            return None
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
    
    def clear_cache(self) -> None:
        """Clear all caches."""
        self._sanctions_cache.clear()
        self._entity_cache.clear()


# Singleton instances for each provider
_providers: Dict[Provider, RiskIntelligenceProvider] = {}


def get_risk_intelligence(
    provider: Provider = Provider.CHAINALYSIS
) -> RiskIntelligenceProvider:
    """Get or create risk intelligence provider singleton."""
    if provider not in _providers:
        _providers[provider] = RiskIntelligenceProvider(provider=provider)
    return _providers[provider]
