"""
ChainShield Admin Panel API

Admin-only endpoints for:
- User management
- System statistics
- Blocklist management
- Configuration
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.logging import get_logger
from app.services.monitoring import get_metrics_collector
from app.services.sla import get_sla_monitor
from app.services.billing.quota import get_quota_manager, Tier

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


# =============================================================================
# Schemas
# =============================================================================

class AdminStats(BaseModel):
    """System statistics for admin dashboard."""
    total_users: int
    active_users_today: int
    total_assessments: int
    blocked_addresses: int
    system_uptime: float
    sla_status: dict


class UserInfo(BaseModel):
    """User info for admin view."""
    id: str
    email: str
    name: str
    tier: str
    is_verified: bool
    created_at: datetime
    requests_today: int
    requests_month: int


class UserUpdate(BaseModel):
    """User update request."""
    tier: Optional[str] = None
    is_verified: Optional[bool] = None
    is_active: Optional[bool] = None


class BlocklistEntry(BaseModel):
    """Add to blocklist request."""
    address: str
    chain: str = "ethereum"
    reason: str
    source: str = "manual"


# =============================================================================
# Mock user data (replace with database)
# =============================================================================

_mock_users = {
    "admin@chainshield.io": {
        "id": "admin_001",
        "email": "admin@chainshield.io",
        "name": "Admin User",
        "tier": "enterprise",
        "is_verified": True,
        "is_active": True,
        "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
    },
    "user1@example.com": {
        "id": "user_001",
        "email": "user1@example.com",
        "name": "Test User 1",
        "tier": "free",
        "is_verified": True,
        "is_active": True,
        "created_at": datetime(2025, 12, 1, tzinfo=timezone.utc),
    },
    "user2@example.com": {
        "id": "user_002",
        "email": "user2@example.com",
        "name": "Test User 2",
        "tier": "pro",
        "is_verified": True,
        "is_active": True,
        "created_at": datetime(2025, 12, 15, tzinfo=timezone.utc),
    }
}


# =============================================================================
# Admin authentication (Production Ready)
# =============================================================================

from fastapi import Header
from app.core.security import verify_token

# In-memory blocklist (use Redis/DB in production)
_custom_blocklist: dict = {}


async def verify_admin(authorization: str = Header(None)):
    """
    Verify admin access via JWT token.
    
    Checks:
    1. Valid JWT token
    2. User has admin role or enterprise tier
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required"
        )
    
    # Extract token from "Bearer <token>"
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme"
            )
        
        # Verify token
        payload = verify_token(token)
        
        # Check admin privileges (tier = enterprise or explicit admin role)
        tier = payload.get("tier", "free")
        is_admin = payload.get("is_admin", False)
        
        if tier not in ("enterprise", "admin") and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        
        return payload
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/stats", response_model=AdminStats)
async def get_admin_stats(admin: bool = Depends(verify_admin)):
    """
    Get system-wide statistics.
    
    Requires admin role.
    """
    metrics = get_metrics_collector()
    sla = get_sla_monitor()
    
    summary = metrics.get_summary()
    sla_summary = sla.get_summary()
    
    return AdminStats(
        total_users=len(_mock_users),
        active_users_today=2,  # Mock
        total_assessments=summary.get("total_assessments", 0),
        blocked_addresses=37,  # From sanctions list
        system_uptime=summary.get("uptime_seconds", 0),
        sla_status=sla_summary
    )


@router.get("/users", response_model=List[UserInfo])
async def list_users(
    skip: int = 0,
    limit: int = 50,
    tier: Optional[str] = None,
    admin: bool = Depends(verify_admin)
):
    """
    List all users with pagination.
    
    Requires admin role.
    """
    quota = get_quota_manager()
    
    users = []
    for user_data in list(_mock_users.values())[skip:skip+limit]:
        if tier and user_data["tier"] != tier:
            continue
        
        usage = await quota.get_usage(user_data["id"])
        
        users.append(UserInfo(
            id=user_data["id"],
            email=user_data["email"],
            name=user_data["name"],
            tier=user_data["tier"],
            is_verified=user_data["is_verified"],
            created_at=user_data["created_at"],
            requests_today=usage.requests_today if usage else 0,
            requests_month=usage.requests_this_month if usage else 0
        ))
    
    return users


@router.get("/users/{user_id}", response_model=UserInfo)
async def get_user(
    user_id: str,
    admin: bool = Depends(verify_admin)
):
    """
    Get single user details.
    """
    for user_data in _mock_users.values():
        if user_data["id"] == user_id:
            quota = get_quota_manager()
            usage = await quota.get_usage(user_id)
            
            return UserInfo(
                id=user_data["id"],
                email=user_data["email"],
                name=user_data["name"],
                tier=user_data["tier"],
                is_verified=user_data["is_verified"],
                created_at=user_data["created_at"],
                requests_today=usage.requests_today if usage else 0,
                requests_month=usage.requests_this_month if usage else 0
            )
    
    raise HTTPException(status_code=404, detail="User not found")


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    update: UserUpdate,
    admin: bool = Depends(verify_admin)
):
    """
    Update user settings (tier, verification, active status).
    """
    for email, user_data in _mock_users.items():
        if user_data["id"] == user_id:
            if update.tier:
                user_data["tier"] = update.tier
            if update.is_verified is not None:
                user_data["is_verified"] = update.is_verified
            if update.is_active is not None:
                user_data["is_active"] = update.is_active
            
            logger.info("admin_updated_user", 
                       user_id=user_id, 
                       changes=update.model_dump(exclude_none=True))
            
            return {"message": "User updated", "user_id": user_id}
    
    raise HTTPException(status_code=404, detail="User not found")


@router.post("/blocklist")
async def add_to_blocklist(
    entry: BlocklistEntry,
    admin: dict = Depends(verify_admin)
):
    """
    Add address to blocklist.
    
    Production: Stores in Redis/PostgreSQL.
    Development: Uses in-memory store.
    """
    # Normalize address
    address_lower = entry.address.lower()
    
    # Add to in-memory blocklist (use Redis/DB in production)
    _custom_blocklist[address_lower] = {
        "address": address_lower,
        "chain": entry.chain,
        "reason": entry.reason,
        "source": entry.source,
        "added_by": admin.get("sub", "unknown"),
        "added_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Also add to the runtime sanctions list for immediate effect
    try:
        from app.services.risk.rules.blacklist import SANCTIONED_ADDRESSES
        SANCTIONED_ADDRESSES.add(address_lower)
    except:
        pass
    
    logger.info("admin_blocklist_add",
               address=entry.address,
               chain=entry.chain,
               reason=entry.reason,
               admin=admin.get("sub"))
    
    return {
        "message": "Address added to blocklist",
        "address": entry.address,
        "chain": entry.chain,
        "total_custom": len(_custom_blocklist)
    }


@router.get("/blocklist")
async def get_blocklist(
    skip: int = 0,
    limit: int = 100,
    admin: bool = Depends(verify_admin)
):
    """
    Get current blocklist.
    """
    # Return sample from sanctions list
    from app.services.risk.rules.blacklist import SANCTIONED_ADDRESSES
    
    entries = []
    for addr in list(SANCTIONED_ADDRESSES)[skip:skip+limit]:
        entries.append({
            "address": addr,
            "chain": "ethereum",
            "reason": "OFAC Sanctions",
            "source": "ofac"
        })
    
    return {
        "total": len(SANCTIONED_ADDRESSES),
        "entries": entries
    }


@router.get("/audit-log")
async def get_audit_log(
    skip: int = 0,
    limit: int = 100,
    admin: bool = Depends(verify_admin)
):
    """
    Get recent audit log entries.
    """
    from app.services.audit import get_audit_logger
    
    audit = get_audit_logger()
    stats = audit.get_stats()
    
    return {
        "stats": stats,
        "message": "View full logs in logs/audit/ directory"
    }


@router.get("/config")
async def get_config(admin: bool = Depends(verify_admin)):
    """
    Get current system configuration.
    """
    from app.core.config import settings
    
    return {
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "debug": settings.debug,
        "rate_limit_enabled": settings.rate_limit_enabled,
        "features": {
            "signup_enabled": True,
            "billing_enabled": False,
            "email_verification_required": True
        }
    }
