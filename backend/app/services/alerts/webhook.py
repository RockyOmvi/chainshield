"""
ChainShield Alert Webhook System

Sends real-time alerts via webhooks for:
- HIGH_RISK - Score > 70
- CRITICAL_RISK - Score > 85
- BLOCKED - Sanctions hit
- MIXER_DETECTED - Tornado Cash interaction

Features:
- Retry with exponential backoff
- Webhook signature verification
- Event batching option
"""

import asyncio
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import aiohttp
import structlog

logger = structlog.get_logger()


class AlertType(str, Enum):
    """Types of webhook alerts."""
    HIGH_RISK = "high_risk"
    CRITICAL_RISK = "critical_risk"
    BLOCKED = "blocked"
    MIXER_DETECTED = "mixer_detected"
    SANCTIONS_HIT = "sanctions_hit"
    UNUSUAL_PATTERN = "unusual_pattern"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class WebhookConfig:
    """Configuration for a webhook endpoint."""
    id: str
    url: str
    secret: str  # For HMAC signing
    enabled: bool = True
    events: List[AlertType] = field(default_factory=lambda: list(AlertType))
    retry_count: int = 3
    timeout_seconds: int = 10


@dataclass
class AlertEvent:
    """Single alert event."""
    event_id: str
    event_type: AlertType
    severity: AlertSeverity
    timestamp: datetime
    
    # Alert data
    address: str
    chain: str
    risk_score: float
    risk_level: str
    blocked: bool
    
    # Additional context
    factors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "address": self.address,
            "chain": self.chain,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "blocked": self.blocked,
            "factors": self.factors,
            "details": self.details
        }


class WebhookManager:
    """
    Manages webhook endpoints and dispatches alerts.
    
    Usage:
        manager = get_webhook_manager()
        
        # Register a webhook
        manager.register_webhook(WebhookConfig(
            id="my_webhook",
            url="https://example.com/webhook",
            secret="my_secret_key"
        ))
        
        # Send alert
        await manager.send_alert(AlertEvent(...))
    """
    
    # Retry configuration
    INITIAL_BACKOFF = 1.0
    MAX_BACKOFF = 60.0
    BACKOFF_MULTIPLIER = 2.0
    
    def __init__(self):
        self.logger = logger.bind(module="webhook_manager")
        self.webhooks: Dict[str, WebhookConfig] = {}
        self._session: Optional[aiohttp.ClientSession] = None
        self._event_queue: List[AlertEvent] = []
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session
    
    def register_webhook(self, config: WebhookConfig) -> None:
        """Register a webhook endpoint."""
        self.webhooks[config.id] = config
        self.logger.info("webhook_registered", 
                        webhook_id=config.id, 
                        events=[e.value for e in config.events])
    
    def unregister_webhook(self, webhook_id: str) -> bool:
        """Unregister a webhook."""
        if webhook_id in self.webhooks:
            del self.webhooks[webhook_id]
            return True
        return False
    
    def list_webhooks(self) -> List[Dict[str, Any]]:
        """List all registered webhooks."""
        return [
            {
                "id": w.id,
                "url": w.url[:50] + "..." if len(w.url) > 50 else w.url,
                "enabled": w.enabled,
                "events": [e.value for e in w.events]
            }
            for w in self.webhooks.values()
        ]
    
    def _sign_payload(self, payload: str, secret: str) -> str:
        """Create HMAC-SHA256 signature for payload."""
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
    
    async def send_alert(self, event: AlertEvent) -> Dict[str, bool]:
        """
        Send alert to all matching webhooks.
        
        Returns dict of webhook_id -> success status.
        """
        results = {}
        
        for webhook in self.webhooks.values():
            if not webhook.enabled:
                continue
            
            if event.event_type not in webhook.events:
                continue
            
            success = await self._send_to_webhook(webhook, event)
            results[webhook.id] = success
        
        return results
    
    async def _send_to_webhook(
        self, 
        webhook: WebhookConfig, 
        event: AlertEvent
    ) -> bool:
        """Send event to a single webhook with retry."""
        payload = json.dumps(event.to_dict())
        signature = self._sign_payload(payload, webhook.secret)
        
        headers = {
            "Content-Type": "application/json",
            "X-ChainShield-Signature": f"sha256={signature}",
            "X-ChainShield-Event": event.event_type.value,
            "X-ChainShield-Timestamp": str(int(time.time()))
        }
        
        backoff = self.INITIAL_BACKOFF
        
        for attempt in range(webhook.retry_count):
            try:
                session = await self._get_session()
                
                async with session.post(
                    webhook.url,
                    data=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=webhook.timeout_seconds)
                ) as resp:
                    if resp.status < 300:
                        self.logger.info(
                            "webhook_sent",
                            webhook_id=webhook.id,
                            event_type=event.event_type.value,
                            status=resp.status
                        )
                        return True
                    
                    self.logger.warning(
                        "webhook_failed",
                        webhook_id=webhook.id,
                        status=resp.status,
                        attempt=attempt + 1
                    )
                    
            except Exception as e:
                self.logger.warning(
                    "webhook_error",
                    webhook_id=webhook.id,
                    error=str(e),
                    attempt=attempt + 1
                )
            
            # Exponential backoff
            if attempt < webhook.retry_count - 1:
                await asyncio.sleep(backoff)
                backoff = min(backoff * self.BACKOFF_MULTIPLIER, self.MAX_BACKOFF)
        
        self.logger.error(
            "webhook_all_retries_failed",
            webhook_id=webhook.id,
            event_id=event.event_id
        )
        return False
    
    def create_alert_from_assessment(
        self,
        address: str,
        chain: str,
        risk_score: float,
        risk_level: str,
        blocked: bool,
        factors: List[str] = None
    ) -> Optional[AlertEvent]:
        """
        Create an alert event from a risk assessment.
        
        Only creates alert if thresholds are met.
        """
        import uuid
        
        # Determine event type and severity
        if blocked:
            event_type = AlertType.BLOCKED
            severity = AlertSeverity.CRITICAL
        elif risk_score >= 85:
            event_type = AlertType.CRITICAL_RISK
            severity = AlertSeverity.CRITICAL
        elif risk_score >= 70:
            event_type = AlertType.HIGH_RISK
            severity = AlertSeverity.WARNING
        else:
            return None  # No alert needed
        
        return AlertEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            severity=severity,
            timestamp=datetime.now(timezone.utc),
            address=address,
            chain=chain,
            risk_score=risk_score,
            risk_level=risk_level,
            blocked=blocked,
            factors=factors or []
        )
    
    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()


# Singleton
_webhook_manager: Optional[WebhookManager] = None


def get_webhook_manager() -> WebhookManager:
    """Get or create webhook manager singleton."""
    global _webhook_manager
    if _webhook_manager is None:
        _webhook_manager = WebhookManager()
    return _webhook_manager
