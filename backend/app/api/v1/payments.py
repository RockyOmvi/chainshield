"""
ChainShield Payments API

Endpoints for subscription management and billing.
"""

from fastapi import APIRouter, Request, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
from typing import Optional
import structlog

from app.services.payments import (
    get_stripe_service,
    SubscriptionTier,
)

router = APIRouter(prefix="/payments", tags=["payments"])
logger = structlog.get_logger()


class CreateCheckoutRequest(BaseModel):
    """Request to create checkout session."""
    email: EmailStr
    tier: str = "pro"


class CheckoutResponse(BaseModel):
    """Checkout session response."""
    session_id: Optional[str] = None
    checkout_url: Optional[str] = None
    error: Optional[str] = None
    demo_mode: bool = False


class PortalRequest(BaseModel):
    """Request for customer portal."""
    customer_id: str


class CancelRequest(BaseModel):
    """Request to cancel subscription."""
    subscription_id: str
    immediately: bool = False


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(request: CreateCheckoutRequest):
    """
    Create a Stripe checkout session for subscription.
    
    Returns a checkout URL to redirect the user to.
    """
    stripe = get_stripe_service()
    
    # Map tier string to enum
    tier_map = {
        "pro": SubscriptionTier.PRO,
        "enterprise": SubscriptionTier.ENTERPRISE,
    }
    
    tier = tier_map.get(request.tier.lower())
    if not tier:
        raise HTTPException(status_code=400, detail="Invalid subscription tier")
    
    # Generate user ID (in production, get from auth token)
    import hashlib
    user_id = hashlib.sha256(request.email.encode()).hexdigest()[:16]
    
    result = await stripe.create_checkout_session(
        user_id=user_id,
        user_email=request.email,
        tier=tier,
        trial_days=14
    )
    
    return CheckoutResponse(**result)


@router.post("/portal")
async def create_customer_portal(request: PortalRequest):
    """
    Create a customer portal session for self-service billing management.
    """
    stripe = get_stripe_service()
    result = await stripe.create_customer_portal_session(request.customer_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/cancel")
async def cancel_subscription(request: CancelRequest):
    """
    Cancel a subscription.
    
    Set immediately=true to cancel now, otherwise cancels at period end.
    """
    stripe = get_stripe_service()
    result = await stripe.cancel_subscription(
        stripe_subscription_id=request.subscription_id,
        immediately=request.immediately
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature")
):
    """
    Handle Stripe webhook events.
    
    Processes events like:
    - checkout.session.completed
    - customer.subscription.updated
    - customer.subscription.deleted
    - invoice.payment_failed
    """
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")
    
    payload = await request.body()
    stripe = get_stripe_service()
    
    result = await stripe.handle_webhook(payload, stripe_signature)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/status")
async def get_payment_status():
    """
    Check if Stripe payments are configured.
    """
    stripe = get_stripe_service()
    
    return {
        "configured": stripe.is_configured,
        "tiers": [
            {"name": "free", "price": 0, "requests": 1000},
            {"name": "pro", "price": 99, "requests": 100000},
            {"name": "enterprise", "price": "custom", "requests": "unlimited"},
        ]
    }
