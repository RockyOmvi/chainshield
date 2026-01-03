"""
ChainShield Audit Logging Service

Comprehensive audit logging for compliance:
- All risk assessments
- Sanctions block events
- API access logs
- Tamper-proof hash chain

CRITICAL for regulatory compliance (SOC 2, etc.)
"""

import hashlib
import json
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional
import aiofiles
import structlog
from pathlib import Path

logger = structlog.get_logger()


class AuditEventType(str, Enum):
    """Types of audit events."""
    # Risk Assessment
    WALLET_ASSESSED = "wallet_assessed"
    TRANSACTION_ASSESSED = "transaction_assessed"
    BATCH_ASSESSED = "batch_assessed"
    
    # Sanctions/Blocking
    SANCTIONS_HIT = "sanctions_hit"
    ADDRESS_BLOCKED = "address_blocked"
    ADDRESS_UNBLOCKED = "address_unblocked"
    
    # Entity Management
    ENTITY_ADDED = "entity_added"
    ENTITY_REMOVED = "entity_removed"
    ENTITY_UPDATED = "entity_updated"
    
    # API Access
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    RATE_LIMIT_HIT = "rate_limit_hit"
    
    # System
    CONFIG_CHANGED = "config_changed"
    MODEL_LOADED = "model_loaded"
    SYSTEM_ERROR = "system_error"


class AuditSeverity(str, Enum):
    """Severity levels for audit events."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Single audit log entry."""
    
    event_type: AuditEventType
    severity: AuditSeverity
    timestamp: datetime
    
    # Optional context
    user_id: Optional[str] = None
    api_key_id: Optional[str] = None
    ip_address: Optional[str] = None
    
    # Event data
    address: Optional[str] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    blocked: Optional[bool] = None
    
    # Additional details
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Hash chain for tamper detection
    previous_hash: Optional[str] = None
    event_hash: Optional[str] = None
    
    def compute_hash(self) -> str:
        """Compute SHA-256 hash of this event."""
        # Create deterministic representation
        data = {
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "api_key_id": self.api_key_id,
            "ip_address": self.ip_address,
            "address": self.address,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "blocked": self.blocked,
            "details": self.details,
            "previous_hash": self.previous_hash
        }
        
        json_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "api_key_id": self.api_key_id,
            "ip_address": self.ip_address,
            "address": self.address,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "blocked": self.blocked,
            "details": self.details,
            "previous_hash": self.previous_hash,
            "event_hash": self.event_hash
        }


class AuditLogger:
    """
    Tamper-proof audit logging service.
    
    Features:
    - Hash chain for integrity verification
    - Multiple output backends (file, database, remote)
    - Async logging for performance
    - Structured logging format
    
    Usage:
        audit = get_audit_logger()
        
        await audit.log_assessment(
            address="0x...",
            risk_score=85.0,
            risk_level="HIGH",
            blocked=False
        )
    """
    
    def __init__(self, log_dir: str = "logs/audit"):
        """Initialize audit logger."""
        self.logger = logger.bind(module="audit_logger")
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self._last_hash: Optional[str] = None
        self._event_count = 0
        self._current_log_file: Optional[Path] = None
        
        self._initialize_log_file()
    
    def _initialize_log_file(self) -> None:
        """Initialize today's log file."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._current_log_file = self.log_dir / f"audit_{today}.jsonl"
        
        # Read last hash if file exists
        if self._current_log_file.exists():
            try:
                with open(self._current_log_file, "r") as f:
                    lines = f.readlines()
                    if lines:
                        last_event = json.loads(lines[-1])
                        self._last_hash = last_event.get("event_hash")
                        self._event_count = len(lines)
            except Exception as e:
                self.logger.error("audit_init_failed", error=str(e))
    
    async def log(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity = AuditSeverity.INFO,
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        address: Optional[str] = None,
        risk_score: Optional[float] = None,
        risk_level: Optional[str] = None,
        blocked: Optional[bool] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """
        Log an audit event.
        
        Returns the created event with hash chain.
        """
        # Create event
        event = AuditEvent(
            event_type=event_type,
            severity=severity,
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            api_key_id=api_key_id,
            ip_address=ip_address,
            address=address,
            risk_score=risk_score,
            risk_level=risk_level,
            blocked=blocked,
            details=details or {},
            previous_hash=self._last_hash
        )
        
        # Compute hash (creates tamper-proof chain)
        event.event_hash = event.compute_hash()
        self._last_hash = event.event_hash
        self._event_count += 1
        
        # Write to log file
        await self._write_event(event)
        
        # Also log via structlog
        self.logger.info(
            event_type.value,
            severity=severity.value,
            address=address[:16] if address else None,
            risk_score=risk_score,
            blocked=blocked
        )
        
        return event
    
    async def _write_event(self, event: AuditEvent) -> None:
        """Write event to log file."""
        try:
            # Check if we need to rotate to new day's file
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            expected_file = self.log_dir / f"audit_{today}.jsonl"
            
            if expected_file != self._current_log_file:
                self._current_log_file = expected_file
            
            # Write as JSONL (one JSON object per line)
            async with aiofiles.open(self._current_log_file, "a") as f:
                await f.write(json.dumps(event.to_dict()) + "\n")
                
        except Exception as e:
            self.logger.error("audit_write_failed", error=str(e))
    
    async def log_assessment(
        self,
        address: str,
        risk_score: float,
        risk_level: str,
        blocked: bool,
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """Log a risk assessment event."""
        event_type = AuditEventType.WALLET_ASSESSED
        severity = AuditSeverity.CRITICAL if blocked else AuditSeverity.INFO
        
        return await self.log(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            api_key_id=api_key_id,
            ip_address=ip_address,
            address=address,
            risk_score=risk_score,
            risk_level=risk_level,
            blocked=blocked,
            details=details
        )
    
    async def log_sanctions_hit(
        self,
        address: str,
        sanction_type: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> AuditEvent:
        """Log a sanctions hit event (CRITICAL)."""
        return await self.log(
            event_type=AuditEventType.SANCTIONS_HIT,
            severity=AuditSeverity.CRITICAL,
            user_id=user_id,
            ip_address=ip_address,
            address=address,
            blocked=True,
            details={"sanction_type": sanction_type}
        )
    
    async def log_api_access(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """Log API access events."""
        severity = (
            AuditSeverity.WARNING 
            if event_type in [AuditEventType.AUTH_FAILURE, AuditEventType.RATE_LIMIT_HIT]
            else AuditSeverity.INFO
        )
        
        return await self.log(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            api_key_id=api_key_id,
            ip_address=ip_address,
            details=details
        )
    
    async def verify_chain(self, log_file: Optional[Path] = None) -> bool:
        """
        Verify the integrity of the audit log chain.
        
        Returns True if chain is intact, False if tampered.
        """
        log_file = log_file or self._current_log_file
        
        if not log_file or not log_file.exists():
            return True  # Empty is valid
        
        try:
            previous_hash = None
            
            with open(log_file, "r") as f:
                for line_num, line in enumerate(f, 1):
                    event_data = json.loads(line)
                    
                    # Check previous hash matches
                    if event_data.get("previous_hash") != previous_hash:
                        self.logger.error(
                            "chain_broken",
                            line=line_num,
                            expected=previous_hash,
                            found=event_data.get("previous_hash")
                        )
                        return False
                    
                    # Verify this event's hash
                    stored_hash = event_data.get("event_hash")
                    
                    # Recreate event to compute hash
                    event = AuditEvent(
                        event_type=AuditEventType(event_data["event_type"]),
                        severity=AuditSeverity(event_data["severity"]),
                        timestamp=datetime.fromisoformat(event_data["timestamp"]),
                        user_id=event_data.get("user_id"),
                        api_key_id=event_data.get("api_key_id"),
                        ip_address=event_data.get("ip_address"),
                        address=event_data.get("address"),
                        risk_score=event_data.get("risk_score"),
                        risk_level=event_data.get("risk_level"),
                        blocked=event_data.get("blocked"),
                        details=event_data.get("details", {}),
                        previous_hash=event_data.get("previous_hash")
                    )
                    
                    computed_hash = event.compute_hash()
                    
                    if computed_hash != stored_hash:
                        self.logger.error(
                            "hash_mismatch",
                            line=line_num,
                            stored=stored_hash,
                            computed=computed_hash
                        )
                        return False
                    
                    previous_hash = stored_hash
            
            self.logger.info("chain_verified", events=line_num)
            return True
            
        except Exception as e:
            self.logger.error("chain_verification_failed", error=str(e))
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get audit logger statistics."""
        return {
            "log_dir": str(self.log_dir),
            "current_file": str(self._current_log_file) if self._current_log_file else None,
            "event_count": self._event_count,
            "last_hash": self._last_hash[:16] if self._last_hash else None
        }


# Singleton
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create audit logger singleton."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
