"""
ChainShield ERC20 Token Analyzer

Fetches real ERC20 token transfer data from Etherscan.
Replaces estimated token features with actual data.

Free API: Etherscan (5 calls/sec on free tier)
"""

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
import aiohttp
import structlog

logger = structlog.get_logger()


@dataclass
class TokenTransfer:
    """Single ERC20 token transfer."""
    tx_hash: str
    block_number: int
    timestamp: datetime
    from_address: str
    to_address: str
    token_address: str
    token_symbol: str
    token_name: str
    value: float
    value_usd: Optional[float] = None


@dataclass
class TokenMetrics:
    """Aggregated token metrics for an address."""
    address: str
    total_erc20_txs: int
    total_received: float
    total_sent: float
    unique_tokens: int
    unique_senders: int
    unique_receivers: int
    avg_time_between_sent: float  # minutes
    avg_time_between_received: float  # minutes
    min_value_received: float
    max_value_received: float
    avg_value_received: float
    min_value_sent: float
    max_value_sent: float
    avg_value_sent: float


class TokenAnalyzer:
    """
    Analyzes ERC20 token transfers for risk assessment.
    
    Features:
    - Fetch ERC20 transfer history from Etherscan
    - Calculate real token metrics
    - Detect token patterns (wash trading, airdrops)
    
    Usage:
        analyzer = TokenAnalyzer()
        metrics = await analyzer.get_token_metrics("0x...")
    """
    
    ETHERSCAN_API = "https://api.etherscan.io/api"
    
    # Rate limit: 5 calls/sec on free tier
    RATE_LIMIT_DELAY = 0.25
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize token analyzer.
        
        Args:
            api_key: Etherscan API key (or set ETHERSCAN_API_KEY env var)
        """
        self.logger = logger.bind(module="token_analyzer")
        self.api_key = api_key or os.getenv("ETHERSCAN_API_KEY")
        self._session: Optional[aiohttp.ClientSession] = None
        
        if not self.api_key:
            self.logger.warning("etherscan_api_key_not_set",
                              msg="Token analysis limited without API key")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session
    
    async def get_erc20_transfers(
        self, 
        address: str,
        start_block: int = 0,
        end_block: int = 99999999,
        max_results: int = 100
    ) -> List[TokenTransfer]:
        """
        Fetch ERC20 token transfers for an address.
        
        Args:
            address: Ethereum address
            start_block: Starting block
            end_block: Ending block
            max_results: Maximum transfers to return
            
        Returns:
            List of TokenTransfer objects
        """
        if not self.api_key:
            return []
        
        try:
            session = await self._get_session()
            
            params = {
                "module": "account",
                "action": "tokentx",
                "address": address,
                "startblock": start_block,
                "endblock": end_block,
                "page": 1,
                "offset": min(max_results, 1000),
                "sort": "desc",
                "apikey": self.api_key
            }
            
            async with session.get(self.ETHERSCAN_API, params=params) as resp:
                if resp.status != 200:
                    return []
                
                data = await resp.json()
                
                if data.get("status") != "1":
                    return []
                
                transfers = []
                for tx in data.get("result", [])[:max_results]:
                    try:
                        # Calculate value in token units
                        decimals = int(tx.get("tokenDecimal", 18))
                        raw_value = int(tx.get("value", 0))
                        value = raw_value / (10 ** decimals)
                        
                        transfer = TokenTransfer(
                            tx_hash=tx.get("hash", ""),
                            block_number=int(tx.get("blockNumber", 0)),
                            timestamp=datetime.fromtimestamp(int(tx.get("timeStamp", 0))),
                            from_address=tx.get("from", "").lower(),
                            to_address=tx.get("to", "").lower(),
                            token_address=tx.get("contractAddress", "").lower(),
                            token_symbol=tx.get("tokenSymbol", ""),
                            token_name=tx.get("tokenName", ""),
                            value=value
                        )
                        transfers.append(transfer)
                    except Exception:
                        continue
                
                return transfers
            
        except Exception as e:
            self.logger.error("erc20_fetch_failed", 
                            address=address[:16], 
                            error=str(e))
            return []
        
        finally:
            await asyncio.sleep(self.RATE_LIMIT_DELAY)
    
    async def get_token_metrics(
        self, 
        address: str,
        max_txs: int = 500
    ) -> TokenMetrics:
        """
        Calculate ERC20 token metrics for an address.
        
        These metrics replace the estimated values in kaggle_adapter.
        
        Args:
            address: Ethereum address
            max_txs: Maximum transactions to analyze
            
        Returns:
            TokenMetrics with real data
        """
        address_lower = address.lower()
        transfers = await self.get_erc20_transfers(address, max_results=max_txs)
        
        if not transfers:
            # Return empty metrics
            return TokenMetrics(
                address=address,
                total_erc20_txs=0,
                total_received=0.0,
                total_sent=0.0,
                unique_tokens=0,
                unique_senders=0,
                unique_receivers=0,
                avg_time_between_sent=0.0,
                avg_time_between_received=0.0,
                min_value_received=0.0,
                max_value_received=0.0,
                avg_value_received=0.0,
                min_value_sent=0.0,
                max_value_sent=0.0,
                avg_value_sent=0.0
            )
        
        # Separate received and sent
        received = [t for t in transfers if t.to_address == address_lower]
        sent = [t for t in transfers if t.from_address == address_lower]
        
        # Calculate metrics
        total_received = sum(t.value for t in received)
        total_sent = sum(t.value for t in sent)
        
        # Unique entities
        unique_tokens = len(set(t.token_address for t in transfers))
        unique_senders = len(set(t.from_address for t in received))
        unique_receivers = len(set(t.to_address for t in sent))
        
        # Time between transactions
        def calc_avg_time_diff(txs: List[TokenTransfer]) -> float:
            if len(txs) < 2:
                return 0.0
            sorted_txs = sorted(txs, key=lambda t: t.timestamp)
            diffs = []
            for i in range(1, len(sorted_txs)):
                diff = (sorted_txs[i].timestamp - sorted_txs[i-1].timestamp).total_seconds() / 60
                diffs.append(diff)
            return sum(diffs) / len(diffs) if diffs else 0.0
        
        avg_time_sent = calc_avg_time_diff(sent)
        avg_time_received = calc_avg_time_diff(received)
        
        # Value stats
        received_values = [t.value for t in received] or [0]
        sent_values = [t.value for t in sent] or [0]
        
        return TokenMetrics(
            address=address,
            total_erc20_txs=len(transfers),
            total_received=total_received,
            total_sent=total_sent,
            unique_tokens=unique_tokens,
            unique_senders=unique_senders,
            unique_receivers=unique_receivers,
            avg_time_between_sent=avg_time_sent,
            avg_time_between_received=avg_time_received,
            min_value_received=min(received_values),
            max_value_received=max(received_values),
            avg_value_received=sum(received_values) / len(received_values),
            min_value_sent=min(sent_values),
            max_value_sent=max(sent_values),
            avg_value_sent=sum(sent_values) / len(sent_values)
        )
    
    async def detect_wash_trading(
        self, 
        address: str,
        threshold: float = 0.8
    ) -> Dict[str, Any]:
        """
        Detect potential wash trading patterns in token transfers.
        
        Wash trading: sending tokens to self or circular transfers.
        
        Args:
            address: Address to analyze
            threshold: Ratio threshold for detection
            
        Returns:
            Detection result
        """
        transfers = await self.get_erc20_transfers(address, max_results=200)
        
        if not transfers:
            return {"detected": False, "confidence": 0.0, "details": []}
        
        address_lower = address.lower()
        
        # Count self-transfers
        self_transfers = [t for t in transfers 
                        if t.from_address == address_lower 
                        and t.to_address == address_lower]
        
        # Count circular transfers (sent then received same amount)
        sent_amounts = {}
        for t in transfers:
            if t.from_address == address_lower:
                key = f"{t.token_address}:{t.value:.4f}"
                sent_amounts[key] = sent_amounts.get(key, 0) + 1
        
        received_same = 0
        for t in transfers:
            if t.to_address == address_lower:
                key = f"{t.token_address}:{t.value:.4f}"
                if key in sent_amounts and sent_amounts[key] > 0:
                    received_same += 1
                    sent_amounts[key] -= 1
        
        # Calculate wash trading score
        total_txs = len(transfers)
        suspicious_txs = len(self_transfers) + received_same
        ratio = suspicious_txs / total_txs if total_txs > 0 else 0
        
        return {
            "detected": ratio > threshold,
            "confidence": min(ratio, 1.0),
            "self_transfers": len(self_transfers),
            "circular_transfers": received_same,
            "total_transfers": total_txs,
            "details": []
        }
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()


# Singleton
_token_analyzer: Optional[TokenAnalyzer] = None


def get_token_analyzer() -> TokenAnalyzer:
    """Get or create token analyzer singleton."""
    global _token_analyzer
    if _token_analyzer is None:
        _token_analyzer = TokenAnalyzer()
    return _token_analyzer
