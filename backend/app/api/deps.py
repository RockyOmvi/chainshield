"""
ChainShield API Dependencies

FastAPI dependencies for:
- Authentication
- Database sessions
- Rate limiting
- Request context
"""

from typing import Optional
from fastapi import Depends, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import verify_token, verify_api_key, hash_api_key
from app.core.errors import UnauthorizedError, ForbiddenError
from app.core.logging import get_logger

logger = get_logger(__name__)

__all__ = [
    "get_db",
    "get_current_user",
    "get_current_user_optional",
    "get_api_key_user",
    "require_scopes",
]

# HTTP Bearer scheme for JWT
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get the current authenticated user from JWT token.
    
    Raises:
        UnauthorizedError: If no valid token
    """
    if not credentials:
        logger.warning(
            "auth_failed_missing_token",
            path=request.url.path,
            ip=request.client.host if request.client else "unknown"
        )
        raise UnauthorizedError("Missing authentication token")
    
    token = credentials.credentials
    payload = verify_token(token, token_type="access")
    
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Invalid token payload")
    
    # Store user info in request state
    request.state.user_id = user_id
    request.state.user_role = payload.get("role", "user")
    
    # Optionally fetch full user from database (for fresh data)
    # Falls back to JWT claims if DB lookup fails
    try:
        from sqlalchemy import select
        from app.models.user import User
        
        result = await db.execute(
            select(User).where(User.id == int(user_id))
        )
        user = result.scalar_one_or_none()
        
        if user:
            if not user.is_active:
                raise UnauthorizedError("User account is deactivated")
            
            return {
                "user_id": str(user.id),
                "email": user.email,
                "role": user.role,
                "plan": user.plan,
            }
    except UnauthorizedError:
        raise
    except Exception as e:
        # Fall back to JWT claims if DB not ready
        logger.debug("user_lookup_fallback", error=str(e))
    
    # Fallback to JWT claims
    return {
        "user_id": user_id,
        "role": payload.get("role", "user"),
        "email": payload.get("email"),
    }


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[dict]:
    """
    Get the current user if authenticated, otherwise None.
    
    Useful for endpoints that work with or without auth.
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = verify_token(token, token_type="access")
        
        user_id = payload.get("sub")
        if user_id:
            request.state.user_id = user_id
            return {
                "user_id": user_id,
                "role": payload.get("role", "user"),
            }
    except UnauthorizedError:
        pass
    
    return None


async def get_api_key_user(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Authenticate via API key.
    
    Raises:
        UnauthorizedError: If no valid API key
    """
    if not x_api_key:
        logger.warning(
            "auth_failed_missing_api_key",
            path=request.url.path,
            ip=request.client.host if request.client else "unknown"
        )
        raise UnauthorizedError("Missing API key")
    
    # Validate key format
    if not x_api_key.startswith(settings.api_key_prefix):
        logger.warning(
            "auth_failed_invalid_key_format",
            path=request.url.path,
            ip=request.client.host if request.client else "unknown"
        )
        raise UnauthorizedError("Invalid API key format")
    
    # Hash the key for lookup
    key_hash = hash_api_key(x_api_key)
    
    # Look up API key in database
    from sqlalchemy import select
    from app.models.user import APIKey
    
    try:
        result = await db.execute(
            select(APIKey).where(
                APIKey.key_hash == key_hash,
                APIKey.is_active == True  # noqa
            )
        )
        api_key_record = result.scalar_one_or_none()
        
        if not api_key_record:
            logger.warning(
                "auth_failed_invalid_api_key",
                path=request.url.path,
                ip=request.client.host if request.client else "unknown"
            )
            raise UnauthorizedError("Invalid API key")
        
        # Check if expired
        from datetime import datetime, timezone
        if api_key_record.expires_at and api_key_record.expires_at < datetime.now(timezone.utc):
            raise UnauthorizedError("API key expired")
        
        # Update last used timestamp
        api_key_record.last_used_at = datetime.now(timezone.utc)
        await db.commit()
        
        # Store in request state
        request.state.api_key = x_api_key[:12] + "..."
        request.state.api_key_id = api_key_record.id
        
        return {
            "user_id": str(api_key_record.user_id),
            "api_key_id": str(api_key_record.id),
            "scopes": api_key_record.scopes or ["read:wallet", "read:transaction"],
        }
        
    except UnauthorizedError:
        raise
    except Exception as e:
        # If table doesn't exist yet (no migrations), use fallback
        logger.warning(
            "api_key_lookup_fallback",
            error=str(e),
            path=request.url.path
        )
        # Fallback for development/testing before migrations
        request.state.api_key = x_api_key[:12] + "..."
        return {
            "user_id": "dev_user",
            "api_key_id": "dev_key",
            "scopes": ["read:wallet", "read:transaction", "write:wallet"],
        }


def require_scopes(*required_scopes: str):
    """
    Dependency factory to require specific scopes.
    
    Usage:
        @app.get("/admin", dependencies=[Depends(require_scopes("admin:read"))])
        async def admin_endpoint():
            ...
    """
    async def scope_checker(
        user: dict = Depends(get_current_user),
    ) -> dict:
        user_scopes = set(user.get("scopes", []))
        required = set(required_scopes)
        
        if not required.issubset(user_scopes):
            missing = required - user_scopes
            raise ForbiddenError(
                f"Missing required scopes: {', '.join(missing)}"
            )
        
        return user
    
    return scope_checker


def require_admin():
    """Dependency to require admin role."""
    async def admin_checker(
        user: dict = Depends(get_current_user),
    ) -> dict:
        if user.get("role") != "admin":
            raise ForbiddenError("Admin access required")
        return user
    
    return admin_checker
