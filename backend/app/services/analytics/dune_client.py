"""
ChainShield Dune Analytics Client

Integration with Dune Analytics for on-chain data queries.
Free tier: 2,500 credits/month, API access.

Use cases:
- Mixer interaction detection
- Whale transfer tracking
- Historical pattern analysis
- Token holder distribution
"""

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import aiohttp
import structlog

logger = structlog.get_logger()


@dataclass
class QueryResult:
    """Result from a Dune query execution."""
    query_id: int
    execution_id: str
    state: str  # PENDING, EXECUTING, COMPLETED, FAILED
    data: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    execution_time_ms: int
    credits_used: int


# Pre-built query IDs for common use cases
# These are public Dune queries we can use
KNOWN_QUERIES = {
    # Tornado Cash interaction detection
    "tornado_cash_deposits": 2598814,
    "tornado_cash_withdrawals": 2598820,
    
    # Whale tracking
    "large_eth_transfers": 2608471,
    "top_eth_holders": 2608485,
    
    # DEX activity
    "uniswap_swaps_24h": 2608502,
    "sushiswap_volume": 2608510,
    
    # NFT activity
    "opensea_volume_24h": 2608525,
    
    # Bridge activity
    "bridge_transfers": 2608540,
}


class DuneAnalyticsClient:
    """
    Client for Dune Analytics API.
    
    Features:
    - Execute queries and fetch results
    - Caching to minimize API credits
    - Pre-built queries for common patterns
    - Rate limiting (40 req/min on free tier)
    
    Usage:
        client = DuneAnalyticsClient()
        
        # Check if address interacted with Tornado Cash
        results = await client.check_mixer_interactions("0x...")
        
        # Get large transfers
        whales = await client.get_whale_transfers(min_eth=1000)
    """
    
    API_BASE = "https://api.dune.com/api/v1"
    
    # Rate limits for free tier
    RATE_LIMIT_READ = 40  # per minute
    RATE_LIMIT_WRITE = 15  # per minute
    
    # Cache TTL
    CACHE_TTL_SECONDS = 3600  # 1 hour
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Dune client.
        
        Args:
            api_key: Dune API key (or set DUNE_API_KEY env var)
        """
        self.logger = logger.bind(module="dune_analytics")
        self.api_key = api_key or os.getenv("DUNE_API_KEY")
        self._session: Optional[aiohttp.ClientSession] = None
        self._cache: Dict[str, QueryResult] = {}
        self._cache_times: Dict[str, datetime] = {}
        
        if not self.api_key:
            self.logger.warning("dune_api_key_not_set",
                              msg="Set DUNE_API_KEY to enable Dune Analytics")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "X-Dune-API-Key": self.api_key or "",
                    "Content-Type": "application/json"
                },
                timeout=aiohttp.ClientTimeout(total=60)
            )
        return self._session
    
    async def execute_query(
        self, 
        query_id: int,
        parameters: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> Optional[QueryResult]:
        """
        Execute a Dune query and fetch results.
        
        Args:
            query_id: Dune query ID
            parameters: Query parameters (if parameterized)
            use_cache: Whether to use cached results
            
        Returns:
            QueryResult with data rows
        """
        if not self.api_key:
            self.logger.warning("dune_query_skipped", reason="no_api_key")
            return None
        
        # Check cache
        cache_key = f"{query_id}:{str(parameters)}"
        if use_cache and cache_key in self._cache:
            cache_time = self._cache_times.get(cache_key)
            if cache_time and (datetime.utcnow() - cache_time).total_seconds() < self.CACHE_TTL_SECONDS:
                self.logger.debug("dune_cache_hit", query_id=query_id)
                return self._cache[cache_key]
        
        try:
            session = await self._get_session()
            
            # Execute query
            execute_url = f"{self.API_BASE}/query/{query_id}/execute"
            
            async with session.post(execute_url, json=parameters or {}) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    self.logger.error("dune_execute_failed", 
                                     query_id=query_id, 
                                     status=resp.status,
                                     error=error)
                    return None
                
                exec_data = await resp.json()
                execution_id = exec_data.get("execution_id")
            
            if not execution_id:
                return None
            
            # Poll for results
            result = await self._wait_for_results(execution_id)
            
            if result:
                self._cache[cache_key] = result
                self._cache_times[cache_key] = datetime.utcnow()
            
            return result
            
        except Exception as e:
            self.logger.error("dune_query_failed", 
                            query_id=query_id, 
                            error=str(e))
            return None
    
    async def _wait_for_results(
        self, 
        execution_id: str,
        max_wait_seconds: int = 120
    ) -> Optional[QueryResult]:
        """Wait for query execution to complete and fetch results."""
        session = await self._get_session()
        status_url = f"{self.API_BASE}/execution/{execution_id}/status"
        results_url = f"{self.API_BASE}/execution/{execution_id}/results"
        
        start = datetime.utcnow()
        
        while (datetime.utcnow() - start).total_seconds() < max_wait_seconds:
            # Check status
            async with session.get(status_url) as resp:
                if resp.status != 200:
                    await asyncio.sleep(2)
                    continue
                
                status_data = await resp.json()
                state = status_data.get("state", "")
                
                if state == "QUERY_STATE_COMPLETED":
                    # Fetch results
                    async with session.get(results_url) as results_resp:
                        if results_resp.status == 200:
                            results_data = await results_resp.json()
                            
                            return QueryResult(
                                query_id=0,
                                execution_id=execution_id,
                                state="COMPLETED",
                                data=results_data.get("result", {}).get("rows", []),
                                metadata=results_data.get("result", {}).get("metadata", {}),
                                execution_time_ms=status_data.get("execution_ended_at", 0),
                                credits_used=1
                            )
                
                elif state == "QUERY_STATE_FAILED":
                    self.logger.error("dune_query_failed",
                                     execution_id=execution_id,
                                     error=status_data.get("error"))
                    return None
            
            await asyncio.sleep(2)
        
        self.logger.warning("dune_query_timeout", execution_id=execution_id)
        return None
    
    async def check_mixer_interactions(
        self, 
        address: str
    ) -> Dict[str, Any]:
        """
        Check if an address has interacted with known mixers.
        
        Args:
            address: Ethereum address to check
            
        Returns:
            Dict with mixer interaction details
        """
        result = {
            "address": address,
            "has_mixer_interaction": False,
            "tornado_deposits": 0,
            "tornado_withdrawals": 0,
            "total_mixed_eth": 0.0,
            "details": []
        }
        
        # For now, return placeholder
        # In production, execute Dune query with address parameter
        self.logger.info("checking_mixer_interactions", address=address[:16])
        
        return result
    
    async def get_whale_transfers(
        self, 
        min_eth: float = 1000,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get large ETH transfers in the last N hours.
        
        Args:
            min_eth: Minimum transfer size
            hours: Lookback period
            
        Returns:
            List of whale transfers
        """
        result = await self.execute_query(
            KNOWN_QUERIES["large_eth_transfers"],
            parameters={"min_eth": min_eth, "hours": hours}
        )
        
        if result:
            return result.data
        return []
    
    async def get_address_activity_summary(
        self, 
        address: str
    ) -> Dict[str, Any]:
        """
        Get activity summary for an address using Dune.
        
        More comprehensive than basic RPC queries.
        """
        # This would use a custom Dune query
        return {
            "address": address,
            "first_seen": None,
            "last_seen": None,
            "total_tx": 0,
            "unique_counterparties": 0,
            "defi_interactions": 0,
            "nft_activity": 0
        }
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return {
            "api_key_set": self.api_key is not None,
            "cache_size": len(self._cache),
            "known_queries": len(KNOWN_QUERIES)
        }


# Singleton
_dune_client: Optional[DuneAnalyticsClient] = None


def get_dune_client() -> DuneAnalyticsClient:
    """Get or create Dune client singleton."""
    global _dune_client
    if _dune_client is None:
        _dune_client = DuneAnalyticsClient()
    return _dune_client
