"""
ChainShield Billing and Quota System

Features:
- Usage tracking per user
- Tier-based limits (free, pro, enterprise)
- Monthly reset
- Overage handling
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional
import structlog

logger = structlog.get_logger()


class Tier(str, Enum):
    """User subscription tiers."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass
class TierLimits:
    """Limits for each tier."""
    requests_per_minute: int
    requests_per_day: int
    requests_per_month: int
    max_batch_size: int
    webhook_enabled: bool
    priority_support: bool
    
    # Premium features
    graph_analysis: bool = False
    real_time_alerts: bool = False
    custom_rules: bool = False


# Tier configurations
TIER_LIMITS = {
    Tier.FREE: TierLimits(
        requests_per_minute=10,
        requests_per_day=100,
        requests_per_month=1000,
        max_batch_size=5,
        webhook_enabled=False,
        priority_support=False,
    ),
    Tier.PRO: TierLimits(
        requests_per_minute=60,
        requests_per_day=5000,
        requests_per_month=100000,
        max_batch_size=50,
        webhook_enabled=True,
        priority_support=False,
        graph_analysis=True,
        real_time_alerts=True,
    ),
    Tier.ENTERPRISE: TierLimits(
        requests_per_minute=1000,
        requests_per_day=100000,
        requests_per_month=10000000,
        max_batch_size=500,
        webhook_enabled=True,
        priority_support=True,
        graph_analysis=True,
        real_time_alerts=True,
        custom_rules=True,
    ),
}


@dataclass
class UsageRecord:
    """User usage tracking."""
    user_id: str
    tier: Tier
    
    # Current period usage
    requests_today: int = 0
    requests_this_month: int = 0
    requests_this_minute: int = 0
    
    # Timestamps
    day_reset: Optional[datetime] = None
    month_reset: Optional[datetime] = None
    minute_reset: Optional[datetime] = None
    
    # Billing
    overage_charges: float = 0.0


class QuotaManager:
    """
    Manages API usage quotas and billing.
    
    Usage:
        quota = get_quota_manager()
        
        # Check if request allowed
        allowed, reason = await quota.check_quota(user_id, tier)
        
        if not allowed:
            raise HTTPException(429, reason)
        
        # Record usage
        await quota.record_usage(user_id)
    """
    
    def __init__(self):
        self.logger = logger.bind(module="quota_manager")
        self._usage: Dict[str, UsageRecord] = {}
    
    def _get_or_create_usage(self, user_id: str, tier: Tier = Tier.FREE) -> UsageRecord:
        """Get or create usage record for user."""
        if user_id not in self._usage:
            self._usage[user_id] = UsageRecord(
                user_id=user_id,
                tier=tier,
                day_reset=datetime.now(timezone.utc),
                month_reset=datetime.now(timezone.utc),
                minute_reset=datetime.now(timezone.utc)
            )
        return self._usage[user_id]
    
    def _check_and_reset(self, usage: UsageRecord) -> None:
        """Reset counters if period has elapsed."""
        now = datetime.now(timezone.utc)
        
        # Reset minute counter
        if usage.minute_reset and (now - usage.minute_reset).seconds >= 60:
            usage.requests_this_minute = 0
            usage.minute_reset = now
        
        # Reset daily counter
        if usage.day_reset and usage.day_reset.date() < now.date():
            usage.requests_today = 0
            usage.day_reset = now
        
        # Reset monthly counter
        if usage.month_reset and usage.month_reset.month != now.month:
            usage.requests_this_month = 0
            usage.month_reset = now
    
    async def check_quota(
        self, 
        user_id: str, 
        tier: Tier = Tier.FREE
    ) -> tuple[bool, Optional[str]]:
        """
        Check if user has remaining quota.
        
        Returns:
            (allowed, reason) - True if allowed, reason if not
        """
        usage = self._get_or_create_usage(user_id, tier)
        usage.tier = tier  # Update tier in case it changed
        
        self._check_and_reset(usage)
        
        limits = TIER_LIMITS.get(tier, TIER_LIMITS[Tier.FREE])
        
        # Check per-minute limit
        if usage.requests_this_minute >= limits.requests_per_minute:
            return False, f"Rate limit exceeded. Max {limits.requests_per_minute}/minute."
        
        # Check daily limit
        if usage.requests_today >= limits.requests_per_day:
            return False, f"Daily limit exceeded. Max {limits.requests_per_day}/day."
        
        # Check monthly limit
        if usage.requests_this_month >= limits.requests_per_month:
            return False, f"Monthly limit exceeded. Max {limits.requests_per_month}/month. Upgrade your plan."
        
        return True, None
    
    async def record_usage(self, user_id: str, tier: Tier = Tier.FREE) -> UsageRecord:
        """Record a single API request."""
        usage = self._get_or_create_usage(user_id, tier)
        
        self._check_and_reset(usage)
        
        usage.requests_this_minute += 1
        usage.requests_today += 1
        usage.requests_this_month += 1
        
        return usage
    
    async def get_usage(self, user_id: str) -> Optional[UsageRecord]:
        """Get usage record for user."""
        return self._usage.get(user_id)
    
    async def get_usage_summary(self, user_id: str) -> Dict:
        """Get usage summary for display."""
        usage = self._usage.get(user_id)
        
        if not usage:
            return {
                "tier": "free",
                "requests_today": 0,
                "requests_this_month": 0,
                "limits": {
                    "per_day": TIER_LIMITS[Tier.FREE].requests_per_day,
                    "per_month": TIER_LIMITS[Tier.FREE].requests_per_month
                }
            }
        
        limits = TIER_LIMITS.get(usage.tier, TIER_LIMITS[Tier.FREE])
        
        return {
            "tier": usage.tier.value,
            "requests_today": usage.requests_today,
            "requests_this_month": usage.requests_this_month,
            "limits": {
                "per_day": limits.requests_per_day,
                "per_month": limits.requests_per_month
            },
            "usage_percent": {
                "daily": (usage.requests_today / limits.requests_per_day) * 100,
                "monthly": (usage.requests_this_month / limits.requests_per_month) * 100
            }
        }
    
    def get_tier_info(self, tier: Tier) -> Dict:
        """Get information about a tier."""
        limits = TIER_LIMITS[tier]
        return {
            "tier": tier.value,
            "requests_per_minute": limits.requests_per_minute,
            "requests_per_day": limits.requests_per_day,
            "requests_per_month": limits.requests_per_month,
            "max_batch_size": limits.max_batch_size,
            "features": {
                "webhooks": limits.webhook_enabled,
                "graph_analysis": limits.graph_analysis,
                "real_time_alerts": limits.real_time_alerts,
                "custom_rules": limits.custom_rules,
                "priority_support": limits.priority_support
            }
        }


# Singleton
_quota_manager: Optional[QuotaManager] = None


def get_quota_manager() -> QuotaManager:
    """Get or create quota manager singleton."""
    global _quota_manager
    if _quota_manager is None:
        _quota_manager = QuotaManager()
    return _quota_manager
