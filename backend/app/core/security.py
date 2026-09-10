"""
ChainShield Security Module

JWT authentication and API key management with:
- Password hashing
- Token generation/validation
- API key verification
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.errors import UnauthorizedError
from app.core.logging import get_logger

logger = get_logger(__name__)

__all__ = [
    "pwd_context",
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "generate_api_key",
    "hash_api_key",
    "verify_api_key",
]

import bcrypt

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError, InvalidHashError
    _argon2_hasher = PasswordHasher()
except Exception:
    _argon2_hasher = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash (supporting bcrypt and argon2)."""
    if not plain_password or not hashed_password:
        return False

    # Check argon2
    if hashed_password.startswith("$argon2"):
        if _argon2_hasher is not None:
            try:
                return _argon2_hasher.verify(hashed_password, plain_password)
            except Exception:
                pass
        return False

    # Check bcrypt
    try:
        truncated = plain_password.encode('utf-8')[:72]
        return bcrypt.checkpw(truncated, hashed_password.encode('utf-8'))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash a password for storage using bcrypt."""
    truncated = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(truncated, salt).decode('utf-8')


class CompatibilityPwdContext:
    def verify(self, plain: str, hashed: str) -> bool:
        return verify_password(plain, hashed)

    def hash(self, plain: str) -> str:
        return get_password_hash(plain)


pwd_context = CompatibilityPwdContext()


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        subject: Token subject (usually user ID)
        expires_delta: Optional custom expiry
        extra_claims: Additional claims to include
        
    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )
    
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    
    if extra_claims:
        to_encode.update(extra_claims)
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt


def create_refresh_token(
    subject: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        subject: Token subject (usually user ID)
        expires_delta: Optional custom expiry
        
    Returns:
        Encoded JWT refresh token
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.jwt_refresh_token_expire_days
        )
    
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
        "jti": secrets.token_hex(16),  # Unique token ID for revocation
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> dict:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token to verify
        token_type: Expected token type ("access" or "refresh")
        
    Returns:
        Decoded token payload
        
    Raises:
        UnauthorizedError: If token is invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        # Verify token type
        if payload.get("type") != token_type:
            raise UnauthorizedError("Invalid token type")
        
        # Verify expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            raise UnauthorizedError("Token has expired")
        
        return payload
        
    except JWTError as e:
        logger.warning("jwt_verification_failed", error=str(e))
        raise UnauthorizedError("Invalid token")


def generate_api_key() -> Tuple[str, str, str]:
    """
    Generate a new API key.
    
    Returns:
        (full_key, key_hash, key_id) - only return full_key to user once
    """
    # Generate random key
    random_part = secrets.token_hex(24)
    full_key = f"{settings.api_key_prefix}{random_part}"
    
    # Generate unique key ID
    key_id = secrets.token_hex(16)
    
    # Hash for storage
    key_hash = hash_api_key(full_key)
    
    return full_key, key_hash, key_id


def hash_api_key(key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()


def verify_api_key(key: str, key_hash: str) -> bool:
    """
    Verify an API key against its hash.
    
    Uses constant-time comparison to prevent timing attacks.
    """
    computed_hash = hash_api_key(key)
    # Constant-time comparison prevents timing attacks
    return hmac.compare_digest(computed_hash, key_hash)
