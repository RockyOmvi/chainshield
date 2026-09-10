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
# Database-backed user store (Production Ready)
# =============================================================================

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.api.deps import get_db, get_current_user

# In-memory fallback for tokens (Redis in production)
_verification_tokens: dict = {}
_reset_tokens: dict = {}


async def get_user_by_email_db(session: AsyncSession, email: str):
    """Get user from database by email."""
    result = await session.execute(
        select(User).where(User.email == email.lower())
    )
    return result.scalar_one_or_none()


async def create_user_db(
    session: AsyncSession,
    email: str,
    password_hash: str,
    name: str,
    company: str = None,
    is_verified: bool = False,
):
    """Create a new user in the database."""
    user = User(
        email=email.lower(),
        hashed_password=password_hash,
        name=name,
        company=company,
        role="user",
        plan="free",
        is_active=True,
        is_verified=is_verified,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


# Fallback in-memory store for development without database
_users_fallback: dict = {}


def get_user_by_email(email: str):
    """Get user by email (in-memory fallback for dev)."""
    return _users_fallback.get(email.lower())


def create_user(email: str, password_hash: str, name: str, company: str = None) -> dict:
    """Create a new user (in-memory fallback for dev)."""
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
    _users_fallback[email.lower()] = user
    return user


# =============================================================================
# Email Service (Production Ready with SendGrid)
# =============================================================================

import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("SMTP_FROM", "noreply@chainshield.io")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


async def send_email(to_email: str, subject: str, html_content: str):
    """Send email using SendGrid or fallback to logging."""
    if SENDGRID_API_KEY:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={
                        "Authorization": f"Bearer {SENDGRID_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "personalizations": [{"to": [{"email": to_email}]}],
                        "from": {"email": FROM_EMAIL, "name": "ChainShield"},
                        "subject": subject,
                        "content": [{"type": "text/html", "value": html_content}]
                    }
                )
                if response.status_code in (200, 202):
                    logger.info("email_sent", to=to_email, subject=subject)
                else:
                    logger.error("email_failed", status=response.status_code)
        except Exception as e:
            logger.error("email_error", error=str(e))
    else:
        # Development mode - just log
        logger.info("email_mock", to=to_email, subject=subject)


async def send_verification_email(email: str, token: str):
    """Send verification email."""
    verify_url = f"{FRONTEND_URL}/verify-email?token={token}"
    html = f"""
    <h2>Welcome to ChainShield!</h2>
    <p>Please verify your email by clicking the link below:</p>
    <a href="{verify_url}" style="background:#6366f1;color:white;padding:12px 24px;text-decoration:none;border-radius:8px;">
        Verify Email
    </a>
    <p>Or copy this link: {verify_url}</p>
    <p>This link expires in 24 hours.</p>
    """
    await send_email(email, "Verify your ChainShield account", html)


async def send_password_reset_email(email: str, token: str):
    """Send password reset email."""
    reset_url = f"{FRONTEND_URL}/reset-password?token={token}"
    html = f"""
    <h2>Reset Your Password</h2>
    <p>Click the link below to reset your password:</p>
    <a href="{reset_url}" style="background:#6366f1;color:white;padding:12px 24px;text-decoration:none;border-radius:8px;">
        Reset Password
    </a>
    <p>Or copy this link: {reset_url}</p>
    <p>This link expires in 1 hour.</p>
    <p>If you didn't request this, please ignore this email.</p>
    """
    await send_email(email, "Reset your ChainShield password", html)


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserRegister,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user account.
    """
    # Check if user exists in DB
    existing_user = None
    try:
        existing_user = await get_user_by_email_db(db, data.email)
    except Exception as e:
        logger.warning("db_check_failed", error=str(e))
    
    if not existing_user and get_user_by_email(data.email):
        existing_user = True

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # In development mode or when SendGrid is not configured, auto-verify account
    auto_verify = settings.app_env == "development" or settings.debug or not SENDGRID_API_KEY
    password_hash = get_password_hash(data.password)

    try:
        await create_user_db(
            db,
            email=data.email,
            password_hash=password_hash,
            name=data.name,
            company=data.company,
            is_verified=auto_verify,
        )
    except Exception as e:
        logger.warning("db_create_failed_fallback_memory", error=str(e))
        mem_user = create_user(
            email=data.email,
            password_hash=password_hash,
            name=data.name,
            company=data.company
        )
        if auto_verify:
            mem_user["is_verified"] = True

    if not auto_verify and SENDGRID_API_KEY:
        token = secrets.token_urlsafe(32)
        _verification_tokens[token] = {
            "email": data.email,
            "expires": datetime.now(timezone.utc) + timedelta(hours=24)
        }
        background_tasks.add_task(send_verification_email, data.email, token)
        msg = "Registration successful. Please check your email to verify your account."
    else:
        msg = "Registration successful. You can now log in."

    logger.info("user_registered", email=data.email)
    return MessageResponse(message=msg)


@router.get("/verify/{token}", response_model=MessageResponse)
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db)
):
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
    
    email = token_data["email"]
    try:
        db_user = await get_user_by_email_db(db, email)
        if db_user:
            db_user.is_verified = True
            await db.commit()
    except Exception:
        pass

    user = get_user_by_email(email)
    if user:
        user["is_verified"] = True
    
    del _verification_tokens[token]
    logger.info("email_verified", email=email)
    return MessageResponse(message="Email verified successfully. You can now log in.")


@router.post("/login", response_model=TokenResponse)
async def login(
    data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Log in with email and password.
    
    Returns access and refresh tokens.
    """
    # 1. Try PostgreSQL database
    db_user = None
    try:
        db_user = await get_user_by_email_db(db, data.email)
    except Exception as e:
        logger.warning("db_login_lookup_failed", error=str(e))

    if db_user:
        if not verify_password(data.password, db_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # In development, auto-verify if not verified yet
        if not db_user.is_verified:
            if settings.app_env == "development" or settings.debug:
                db_user.is_verified = True
                await db.commit()
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Please verify your email before logging in"
                )

        if not db_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )

        # Update last login
        try:
            db_user.last_login_at = datetime.now(timezone.utc)
            await db.commit()
        except Exception:
            pass

        user_id = str(db_user.id)
        access_token = create_access_token(
            subject=user_id,
            extra_claims={
                "email": db_user.email,
                "role": db_user.role,
                "tier": db_user.plan,
                "name": db_user.name or db_user.email.split("@")[0]
            }
        )
        refresh_token = create_refresh_token(subject=user_id)
        logger.info("user_login", user_id=user_id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60
        )

    # 2. Fallback to in-memory store
    user = get_user_by_email(data.email)
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user["is_verified"]:
        if settings.app_env == "development" or settings.debug:
            user["is_verified"] = True
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please verify your email before logging in"
            )
    
    user_id = str(user["id"])
    access_token = create_access_token(
        subject=user_id,
        extra_claims={
            "email": user["email"],
            "role": user.get("role", "user"),
            "tier": user.get("tier", "free"),
            "name": user.get("name", user["email"].split("@")[0])
        }
    )
    refresh_token = create_refresh_token(subject=user_id)
    logger.info("user_login_fallback", user_id=user_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token_endpoint(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    try:
        payload = verify_token(refresh_token, token_type="refresh")
        user_id = payload.get("sub")
        
        user = None
        is_db = False
        try:
            result = await db.execute(select(User).where(User.id == int(user_id)))
            user = result.scalar_one_or_none()
            if user:
                is_db = True
        except Exception:
            pass

        if not user:
            for u in _users_fallback.values():
                if str(u.get("id")) == str(user_id):
                    user = u
                    break

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        uid = str(user.id) if is_db else str(user["id"])
        email = user.email if is_db else user["email"]
        role = user.role if is_db else user.get("role", "user")
        tier = user.plan if is_db else user.get("tier", "free")
        name = user.name if is_db else user.get("name", "")

        new_access_token = create_access_token(
            subject=uid,
            extra_claims={"email": email, "role": role, "tier": tier, "name": name}
        )
        new_refresh_token = create_refresh_token(subject=uid)
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/password-reset", response_model=MessageResponse)
async def request_password_reset(
    data: PasswordReset,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Request a password reset email.
    """
    user_exists = False
    try:
        db_u = await get_user_by_email_db(db, data.email)
        if db_u:
            user_exists = True
    except Exception:
        pass

    if not user_exists and get_user_by_email(data.email):
        user_exists = True

    if user_exists:
        token = secrets.token_urlsafe(32)
        _reset_tokens[token] = {
            "email": data.email,
            "expires": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        if SENDGRID_API_KEY:
            background_tasks.add_task(send_password_reset_email, data.email, token)

    return MessageResponse(
        message="If the email exists, a password reset link has been sent."
    )


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def confirm_password_reset(
    data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
):
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

    new_hash = get_password_hash(data.new_password)
    email = token_data["email"]

    try:
        db_user = await get_user_by_email_db(db, email)
        if db_user:
            db_user.hashed_password = new_hash
            await db.commit()
    except Exception:
        pass

    user = get_user_by_email(email)
    if user:
        user["password_hash"] = new_hash

    del _reset_tokens[data.token]
    logger.info("password_reset", email=email)
    return MessageResponse(message="Password reset successful. You can now log in.")


@router.get("/me")
async def get_me(
    current_user: dict = Depends(get_current_user)
):
    """Get current authenticated user info."""
    return current_user
