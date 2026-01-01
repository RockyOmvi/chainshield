"""
ChainShield Sliding Window Rate Limiter

Production-grade rate limiting with sliding window algorithm.
Prevents gaming at hourly boundaries.
"""

import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional
import structlog

logger = structlog.get_logger()


@dataclass
class RateLimitEntry:
    """A rate limit record."""
    timestamp: float
    count: int = 1


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter.
    
    Unlike fixed window rate limits that reset at boundaries,
    sliding window tracks requests over a rolling time period.
    
    Benefits:
    - No gaming at window boundaries
    - Smooth rate limiting
    - More accurate enforcement
    """
    
    def __init__(
        self,
        window_seconds: int = 3600,
        cleanup_interval: int = 300
    ):
        """
        Initialize sliding window rate limiter.
        
        Args:
            window_seconds: Size of sliding window (default: 1 hour)
            cleanup_interval: How often to clean old entries (default: 5 min)
        """
        self.logger = logger.bind(module="sliding_rate_limiter")
        self.window_seconds = window_seconds
        self.cleanup_interval = cleanup_interval
        
        # Storage: identifier -> list of timestamps
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._last_cleanup = time.time()
    
    def _cleanup(self) -> None:
        """Remove expired entries."""
        now = time.time()
        
        # Only cleanup periodically
        if now - self._last_cleanup < self.cleanup_interval:
            return
        
        cutoff = now - self.window_seconds
        cleaned = 0
        
        for identifier in list(self._requests.keys()):
            # Remove old timestamps
            original_count = len(self._requests[identifier])
            self._requests[identifier] = [
                ts for ts in self._requests[identifier]
                if ts > cutoff
            ]
            cleaned += original_count - len(self._requests[identifier])
            
            # Remove empty entries
            if not self._requests[identifier]:
                del self._requests[identifier]
        
        self._last_cleanup = now
        
        if cleaned > 0:
            self.logger.debug(
                "rate_limiter_cleanup",
                cleaned_entries=cleaned
            )
    
    def check(self, identifier: str, limit: int) -> tuple:
        """
        Check if request is within rate limit.
        
        Args:
            identifier: Unique identifier (e.g., user_id, ip_hash)
            limit: Maximum requests per window
            
        Returns:
            Tuple of (allowed: bool, current_count: int, reset_in_seconds: int)
        """
        self._cleanup()
        
        now = time.time()
        cutoff = now - self.window_seconds
        
        # Get valid timestamps
        valid_requests = [
            ts for ts in self._requests[identifier]
            if ts > cutoff
        ]
        self._requests[identifier] = valid_requests
        
        current_count = len(valid_requests)
        allowed = current_count < limit
        
        # Calculate when oldest request will expire
        if valid_requests:
            oldest = min(valid_requests)
            reset_in = int((oldest + self.window_seconds) - now)
        else:
            reset_in = 0
        
        return allowed, current_count, max(reset_in, 0)
    
    def record(self, identifier: str) -> None:
        """Record a request."""
        self._requests[identifier].append(time.time())
    
    def check_and_record(self, identifier: str, limit: int) -> tuple:
        """
        Check if allowed and record if so.
        
        Args:
            identifier: Unique identifier
            limit: Maximum requests per window
            
        Returns:
            Tuple of (allowed: bool, current_count: int, reset_in_seconds: int)
        """
        allowed, count, reset_in = self.check(identifier, limit)
        
        if allowed:
            self.record(identifier)
            count += 1
        
        return allowed, count, reset_in
    
    def get_usage(self, identifier: str) -> Dict:
        """Get current usage for an identifier."""
        now = time.time()
        cutoff = now - self.window_seconds
        
        valid_requests = [
            ts for ts in self._requests[identifier]
            if ts > cutoff
        ]
        
        return {
            "identifier": identifier,
            "current_count": len(valid_requests),
            "window_seconds": self.window_seconds,
            "oldest_request": min(valid_requests) if valid_requests else None,
            "newest_request": max(valid_requests) if valid_requests else None,
        }
    
    def reset(self, identifier: str) -> None:
        """Reset rate limit for an identifier."""
        if identifier in self._requests:
            del self._requests[identifier]
    
    def get_stats(self) -> Dict:
        """Get rate limiter statistics."""
        now = time.time()
        cutoff = now - self.window_seconds
        
        total_active = 0
        total_requests = 0
        
        for timestamps in self._requests.values():
            valid = [ts for ts in timestamps if ts > cutoff]
            if valid:
                total_active += 1
                total_requests += len(valid)
        
        return {
            "active_identifiers": total_active,
            "total_requests_in_window": total_requests,
            "window_seconds": self.window_seconds,
            "last_cleanup": self._last_cleanup,
        }


# Singleton instance
_sliding_rate_limiter: Optional[SlidingWindowRateLimiter] = None


def get_sliding_rate_limiter() -> SlidingWindowRateLimiter:
    """Get or create the sliding window rate limiter singleton."""
    global _sliding_rate_limiter
    if _sliding_rate_limiter is None:
        _sliding_rate_limiter = SlidingWindowRateLimiter()
    return _sliding_rate_limiter
