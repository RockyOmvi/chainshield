"""
ChainShield User Authentication API

Complete auth flow:
- User registration
- Email verification
- Password reset
- Login/Logout
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, EmailStr, Field

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token
)
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


# =============================================================================
# Schemas
# =============================================================================

class UserRegister(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    name: str = Field(..., min_length=2, max_length=100)
    company: Optional[str] = None


class UserLogin(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class PasswordReset(BaseModel):
    """Password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


class TokenResponse(BaseModel):
    """Auth token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """User info response."""
    id: str
    email: str
    name: str
    company: Optional[str]
    is_verified: bool
    created_at: datetime


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str


# =============================================================================
# In-memory user store (replace with database in production)
# =============================================================================

# Simulated user database
_users = {}
_verification_tokens = {}
_reset_tokens = {}


def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email."""
    return _users.get(email.lower())


def create_user(email: str, password_hash: str, name: str, company: str = None) -> dict:
    """Create a new user."""
    user_id = secrets.token_hex(16)
    user = {
        "id": user_id,
        "email": email.lower(),
        "password_hash": password_hash,
        "name": name,
        "company": company,
        "is_verified": False,
        "created_at": datetime.now(timezone.utc),
        "api_calls_today": 0,
        "api_calls_month": 0,
        "tier": "free"
    }
    _users[email.lower()] = user
    return user


# =============================================================================
# Email sending (stub - implement with real email service)
# =============================================================================

async def send_verification_email(email: str, token: str):
    """Send verification email."""
    # TODO: Implement with SendGrid/SES
    logger.info("send_verification_email", email=email, token=token[:8])


async def send_password_reset_email(email: str, token: str):
    """Send password reset email."""
    # TODO: Implement with SendGrid/SES
    logger.info("send_password_reset_email", email=email, token=token[:8])


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserRegister,
    background_tasks: BackgroundTasks
):
    """
    Register a new user account.
    
    An email verification link will be sent.
    """
    # Check if user exists
    if get_user_by_email(data.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Create user
    password_hash = get_password_hash(data.password)
    user = create_user(
        email=data.email,
        password_hash=password_hash,
        name=data.name,
        company=data.company
    )
    
    # Generate verification token
    token = secrets.token_urlsafe(32)
    _verification_tokens[token] = {
        "email": data.email,
        "expires": datetime.now(timezone.utc) + timedelta(hours=24)
    }
    
    # Send verification email
    background_tasks.add_task(send_verification_email, data.email, token)
    
    logger.info("user_registered", email=data.email)
    
    return MessageResponse(
        message="Registration successful. Please check your email to verify your account."
    )


@router.get("/verify/{token}", response_model=MessageResponse)
async def verify_email(token: str):
    """
    Verify email address with token.
    """
    token_data = _verification_tokens.get(token)
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    if datetime.now(timezone.utc) > token_data["expires"]:
        del _verification_tokens[token]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token expired"
        )
    
    # Mark user as verified
    user = get_user_by_email(token_data["email"])
    if user:
        user["is_verified"] = True
    
    del _verification_tokens[token]
    
    logger.info("email_verified", email=token_data["email"])
    
    return MessageResponse(message="Email verified successfully. You can now log in.")


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin):
    """
    Log in with email and password.
    
    Returns access and refresh tokens.
    """
    user = get_user_by_email(data.email)
    
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user["is_verified"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in"
        )
    
    # Create tokens
    access_token = create_access_token(
        subject=user["id"],
        extra_claims={"email": user["email"], "tier": user["tier"]}
    )
    refresh_token = create_refresh_token(subject=user["id"])
    
    logger.info("user_login", user_id=user["id"])
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
    """
    Refresh access token using refresh token.
    """
    try:
        payload = verify_token(refresh_token, token_type="refresh")
        user_id = payload.get("sub")
        
        # Find user
        user = None
        for u in _users.values():
            if u["id"] == user_id:
                user = u
                break
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Create new tokens
        new_access_token = create_access_token(
            subject=user["id"],
            extra_claims={"email": user["email"], "tier": user["tier"]}
        )
        new_refresh_token = create_refresh_token(subject=user["id"])
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60
        )
        
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/password-reset", response_model=MessageResponse)
async def request_password_reset(
    data: PasswordReset,
    background_tasks: BackgroundTasks
):
    """
    Request a password reset email.
    """
    user = get_user_by_email(data.email)
    
    # Always return success (don't reveal if email exists)
    if user:
        token = secrets.token_urlsafe(32)
        _reset_tokens[token] = {
            "email": data.email,
            "expires": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        background_tasks.add_task(send_password_reset_email, data.email, token)
    
    return MessageResponse(
        message="If the email exists, a password reset link has been sent."
    )


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def confirm_password_reset(data: PasswordResetConfirm):
    """
    Reset password with token.
    """
    token_data = _reset_tokens.get(data.token)
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    if datetime.now(timezone.utc) > token_data["expires"]:
        del _reset_tokens[data.token]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token expired"
        )
    
    # Update password
    user = get_user_by_email(token_data["email"])
    if user:
        user["password_hash"] = get_password_hash(data.new_password)
    
    del _reset_tokens[data.token]
    
    logger.info("password_reset", email=token_data["email"])
    
    return MessageResponse(message="Password reset successful. You can now log in.")
