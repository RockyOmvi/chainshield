"""
ChainShield Blacklist Rule

Checks addresses against known malicious address lists.
Uses Bloom filter for O(1) lookups on large lists.

This is the fastest rule layer - catches known bad actors immediately.
"""

from typing import Any, Dict, List, Optional, Set
import hashlib
import structlog

from app.services.risk.rules.base import RiskRule, RuleResult, RuleSeverity
from app.services.risk.config import risk_config

logger = structlog.get_logger()


class SimpleBloomFilter:
    """
    Simple Bloom filter implementation for address lookups.
    
    In production, use pybloom-live or a Redis-backed bloom filter.
    This implementation is for demonstration and small lists.
    """
    
    def __init__(self, expected_items: int = 10000, fp_rate: float = 0.01):
        """
        Initialize bloom filter.
        
        Args:
            expected_items: Expected number of items
            fp_rate: Acceptable false positive rate
        """
        import math
        
        # Calculate optimal size and hash count
        self.size = int(-expected_items * math.log(fp_rate) / (math.log(2) ** 2))
        self.hash_count = int(self.size / expected_items * math.log(2))
        self.bit_array = [False] * self.size
        self.item_count = 0
    
    def _hashes(self, item: str) -> List[int]:
        """Generate hash values for an item."""
        hashes = []
        for i in range(self.hash_count):
            h = hashlib.sha256(f"{item}:{i}".encode()).hexdigest()
            hashes.append(int(h, 16) % self.size)
        return hashes
    
    def add(self, item: str) -> None:
        """Add an item to the filter."""
        item = item.lower()
        for h in self._hashes(item):
            self.bit_array[h] = True
        self.item_count += 1
    
    def add_many(self, items: Set[str]) -> None:
        """Add multiple items."""
        for item in items:
            self.add(item)
    
    def might_contain(self, item: str) -> bool:
        """
        Check if item might be in the set.
        
        Returns:
            True if item might be in set (can be false positive)
            False if item is definitely not in set
        """
        item = item.lower()
        return all(self.bit_array[h] for h in self._hashes(item))


class BlacklistRule(RiskRule):
    """
    Rule that checks addresses against known malicious lists.
    
    Lists included:
    - Mixer contracts (Tornado Cash, etc.)
    - Sanctioned addresses (OFAC)
    - Known scam addresses
    - Phishing contracts
    """
    
    def __init__(
        self,
        name: str = "blacklist_check",
        enabled: bool = True,
        weight: float = 1.0,
        additional_addresses: Optional[Set[str]] = None
    ):
        super().__init__(name, enabled, weight)
        
        # Initialize bloom filter with known addresses
        self.bloom = SimpleBloomFilter(expected_items=50000)
        self.exact_set: Set[str] = set()
        
        # Add mixer contracts
        for addr in risk_config.known_patterns.mixer_contracts:
            self._add_address(addr, "mixer")
        
        # Add sanctioned addresses from config
        for addr in risk_config.known_patterns.sanctioned_addresses:
            self._add_address(addr, "sanctioned")
        
        # Add OFAC sanctions database (Tornado Cash, Lazarus, etc.)
        try:
            from app.services.risk.sanctions import get_sanctions_database
            sanctions_db = get_sanctions_database()
            for addr in sanctions_db.get_all_addresses():
                self._add_address(addr, "ofac_sanctioned")
            self.logger.info("ofac_sanctions_loaded", count=len(sanctions_db.get_all_addresses()))
        except ImportError:
            pass  # Sanctions module optional
        except Exception as e:
            self.logger.warning("ofac_sanctions_load_failed", error=str(e))
        
        # Add any additional addresses
        if additional_addresses:
            for addr in additional_addresses:
                self._add_address(addr, "custom")
        
        self.logger.info(
            "blacklist_initialized",
            address_count=len(self.exact_set)
        )
    
    def _add_address(self, address: str, category: str) -> None:
        """Add address to both bloom filter and exact set."""
        addr_lower = address.lower()
        self.bloom.add(addr_lower)
        self.exact_set.add(addr_lower)
    
    @property
    def description(self) -> str:
        return "Checks if address is on known malicious or sanctioned lists"
    
    def evaluate(
        self, 
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> RuleResult:
        """
        Evaluate if address is blacklisted.
        
        Checks:
        1. The wallet address itself
        2. Recent transaction counterparties
        """
        if not self.enabled:
            return self._make_result(triggered=False)
        
        address = data.get("address", "").lower()
        factors = []
        details = {}
        total_matches = 0
        severity = RuleSeverity.INFO
        
        # Check main address
        if self._is_blacklisted(address):
            factors.append(f"Address {address[:10]}... is on blacklist")
            details["direct_match"] = True
            severity = RuleSeverity.CRITICAL
            total_matches += 1
        
        # Check transaction counterparties
        transactions = data.get("transactions", [])
        blacklisted_counterparties = []
        
        for tx in transactions:
            from_addr = tx.get("from", "").lower()
            to_addr = tx.get("to", "").lower()
            
            if from_addr and from_addr != address and self._is_blacklisted(from_addr):
                if from_addr not in blacklisted_counterparties:
                    blacklisted_counterparties.append(from_addr)
            
            if to_addr and to_addr != address and self._is_blacklisted(to_addr):
                if to_addr not in blacklisted_counterparties:
                    blacklisted_counterparties.append(to_addr)
        
        if blacklisted_counterparties:
            count = len(blacklisted_counterparties)
            factors.append(f"Interacted with {count} blacklisted addresses")
            details["blacklisted_counterparties"] = blacklisted_counterparties[:5]
            total_matches += count
            
            # ANY mixer/blacklist interaction = HIGH minimum
            if count >= 3:
                severity = max(severity, RuleSeverity.CRITICAL)
            else:
                severity = max(severity, RuleSeverity.HIGH)
        
        # Calculate score
        if total_matches == 0:
            return self._make_result(triggered=False)
        
        # Score based on severity and count
        if details.get("direct_match"):
            score = 100.0  # Direct blacklist = max score
        else:
            score = min(40 * total_matches, 90)  # 40 per interaction, cap at 90
        
        return self._make_result(
            triggered=True,
            severity=severity,
            score=score,
            message=f"Blacklist matches found: {total_matches}",
            details=details,
            factors=factors
        )
    
    def _is_blacklisted(self, address: str) -> bool:
        """
        Check if address is blacklisted.
        
        Uses bloom filter for fast negative check,
        then exact set for confirmation.
        """
        if not address:
            return False
        
        addr_lower = address.lower()
        
        # Fast negative check with bloom filter
        if not self.bloom.might_contain(addr_lower):
            return False
        
        # Confirm with exact set (bloom filter can have false positives)
        return addr_lower in self.exact_set
    
    def add_address(self, address: str, category: str = "runtime") -> None:
        """Add address to blacklist at runtime."""
        self._add_address(address, category)
        self.logger.info("address_added_to_blacklist", address=address[:10], category=category)
    
    def remove_address(self, address: str) -> bool:
        """
        Remove address from exact set.
        Note: Cannot remove from bloom filter (by design).
        """
        addr_lower = address.lower()
        if addr_lower in self.exact_set:
            self.exact_set.remove(addr_lower)
            return True
        return False
