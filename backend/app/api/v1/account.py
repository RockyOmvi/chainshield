"""
ChainShield Account & Usage API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User, APIKey
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/account", tags=["Account"])


@router.get("/usage")
async def get_usage(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user usage and rate limits."""
    user_id = current_user.get("user_id")
    tier = current_user.get("tier", "free")

    requests_today = 0
    requests_this_month = 0

    if user_id:
        try:
            result = await db.execute(select(User).where(User.id == int(user_id)))
            user = result.scalar_one_or_none()
            if user:
                requests_today = user.api_calls_today
                requests_this_month = user.api_calls_month
                tier = user.plan
        except Exception as e:
            logger.debug("user_usage_lookup_fallback", error=str(e))

    limits = {
        "free": {"per_minute": 60, "per_day": 1000, "per_month": 30000},
        "pro": {"per_minute": 300, "per_day": 10000, "per_month": 300000},
        "enterprise": {"per_minute": 1000, "per_day": 100000, "per_month": 3000000},
    }.get(tier.lower(), {"per_minute": 60, "per_day": 1000, "per_month": 30000})

    remaining = max(0, limits["per_month"] - requests_this_month)

    return {
        "requests_today": requests_today,
        "requests_this_month": requests_this_month,
        "remaining": remaining,
        "tier": tier.upper(),
        "limits": limits,
    }


@router.get("/profile")
async def get_profile(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user profile."""
    user_id = current_user.get("user_id")
    email = current_user.get("email", "")
    name = current_user.get("name", email.split("@")[0] if "@" in email else "User")
    tier = current_user.get("tier", "free")
    created_at = "2025-01-01"

    if user_id:
        try:
            result = await db.execute(select(User).where(User.id == int(user_id)))
            user = result.scalar_one_or_none()
            if user:
                email = user.email
                name = user.name or name
                tier = user.plan
                created_at = user.created_at.strftime("%Y-%m-%d") if user.created_at else created_at
        except Exception:
            pass

    return {
        "id": user_id,
        "name": name,
        "email": email,
        "tier": tier.upper(),
        "createdAt": created_at,
    }


@router.get("/api-keys")
async def get_api_keys(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's API keys."""
    user_id = current_user.get("user_id")
    if not user_id:
        return []

    try:
        result = await db.execute(
            select(APIKey).where(APIKey.user_id == int(user_id))
        )
        keys = result.scalars().all()
        return [
            {
                "id": str(k.id),
                "name": k.name,
                "prefix": k.key_prefix,
                "created_at": k.created_at.isoformat() if k.created_at else None,
                "is_active": k.is_active,
            }
            for k in keys
        ]
    except Exception:
        return []
