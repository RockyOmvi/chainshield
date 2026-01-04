"""
ChainShield Stripe Payment Service

Handles subscription management and payment processing.
"""

import hashlib
import hmac
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import os
import structlog

logger = structlog.get_logger()


class SubscriptionTier(str, Enum):
    """Subscription tiers matching pricing page."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, Enum):
    """Subscription status."""
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"


@dataclass
class PriceConfig:
    """Stripe price configuration."""
    tier: SubscriptionTier
    price_id: str
    amount: int  # in cents
    currency: str = "usd"
    interval: str = "month"


# Stripe price IDs (set in environment)
PRICE_CONFIG = {
    SubscriptionTier.FREE: PriceConfig(
        tier=SubscriptionTier.FREE,
        price_id="price_free",
        amount=0
    ),
    SubscriptionTier.PRO: PriceConfig(
        tier=SubscriptionTier.PRO,
        price_id=os.getenv("STRIPE_PRICE_PRO", "price_xxx"),
        amount=9900  # $99
    ),
    SubscriptionTier.ENTERPRISE: PriceConfig(
        tier=SubscriptionTier.ENTERPRISE,
        price_id=os.getenv("STRIPE_PRICE_ENTERPRISE", "price_xxx"),
        amount=49900  # $499
    ),
}


@dataclass
class Subscription:
    """User subscription data."""
    user_id: str
    tier: SubscriptionTier
    status: SubscriptionStatus
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False


class StripeService:
    """
    Stripe payment service.
    
    Handles:
    - Checkout session creation
    - Subscription management
    - Webhook processing
    - Customer portal
    """
    
    def __init__(self):
        self.api_key = os.getenv("STRIPE_SECRET_KEY", "")
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
        self.success_url = os.getenv("STRIPE_SUCCESS_URL", "http://localhost:3000/success")
        self.cancel_url = os.getenv("STRIPE_CANCEL_URL", "http://localhost:3000/cancel")
        
        self._stripe = None
        self._subscriptions: Dict[str, Subscription] = {}  # In-memory for demo
        
        self.logger = logger.bind(service="stripe")
        
        if self.api_key:
            try:
                import stripe
                stripe.api_key = self.api_key
                self._stripe = stripe
                self.logger.info("stripe_initialized")
            except ImportError:
                self.logger.warning("stripe_not_installed", hint="pip install stripe")
    
    @property
    def is_configured(self) -> bool:
        """Check if Stripe is properly configured."""
        return bool(self._stripe and self.api_key)
    
    async def create_checkout_session(
        self,
        user_id: str,
        user_email: str,
        tier: SubscriptionTier,
        trial_days: int = 14
    ) -> Dict[str, Any]:
        """
        Create a Stripe checkout session for subscription.
        
        Args:
            user_id: Internal user ID
            user_email: User's email
            tier: Subscription tier
            trial_days: Free trial period
            
        Returns:
            Checkout session with URL
        """
        if not self.is_configured:
            return {
                "error": "Stripe not configured",
                "demo_mode": True,
                "checkout_url": f"/demo/checkout?tier={tier.value}"
            }
        
        price_config = PRICE_CONFIG.get(tier)
        if not price_config or tier == SubscriptionTier.FREE:
            return {"error": "Invalid tier for checkout"}
        
        try:
            session = self._stripe.checkout.Session.create(
                customer_email=user_email,
                payment_method_types=["card"],
                line_items=[{
                    "price": price_config.price_id,
                    "quantity": 1,
                }],
                mode="subscription",
                success_url=f"{self.success_url}?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=self.cancel_url,
                subscription_data={
                    "trial_period_days": trial_days,
                    "metadata": {
                        "user_id": user_id,
                        "tier": tier.value,
                    }
                },
                metadata={
                    "user_id": user_id,
                }
            )
            
            self.logger.info(
                "checkout_session_created",
                user_id=user_id,
                tier=tier.value,
                session_id=session.id
            )
            
            return {
                "session_id": session.id,
                "checkout_url": session.url
            }
            
        except Exception as e:
            self.logger.error("checkout_session_failed", error=str(e))
            return {"error": str(e)}
    
    async def create_customer_portal_session(
        self,
        stripe_customer_id: str
    ) -> Dict[str, Any]:
        """
        Create a Stripe customer portal session for self-service.
        
        Args:
            stripe_customer_id: Stripe customer ID
            
        Returns:
            Portal session with URL
        """
        if not self.is_configured:
            return {"error": "Stripe not configured", "demo_mode": True}
        
        try:
            session = self._stripe.billing_portal.Session.create(
                customer=stripe_customer_id,
                return_url=self.success_url,
            )
            
            return {"portal_url": session.url}
            
        except Exception as e:
            self.logger.error("portal_session_failed", error=str(e))
            return {"error": str(e)}
    
    async def cancel_subscription(
        self,
        stripe_subscription_id: str,
        immediately: bool = False
    ) -> Dict[str, Any]:
        """
        Cancel a subscription.
        
        Args:
            stripe_subscription_id: Stripe subscription ID
            immediately: Cancel now or at period end
            
        Returns:
            Updated subscription status
        """
        if not self.is_configured:
            return {"error": "Stripe not configured"}
        
        try:
            if immediately:
                sub = self._stripe.Subscription.delete(stripe_subscription_id)
            else:
                sub = self._stripe.Subscription.modify(
                    stripe_subscription_id,
                    cancel_at_period_end=True
                )
            
            self.logger.info(
                "subscription_canceled",
                subscription_id=stripe_subscription_id,
                immediately=immediately
            )
            
            return {
                "status": sub.status,
                "cancel_at_period_end": sub.cancel_at_period_end
            }
            
        except Exception as e:
            self.logger.error("cancel_failed", error=str(e))
            return {"error": str(e)}
    
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str
    ) -> bool:
        """Verify Stripe webhook signature."""
        if not self.webhook_secret:
            return False
        
        try:
            self._stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            return True
        except Exception:
            return False
    
    async def handle_webhook(
        self,
        payload: bytes,
        signature: str
    ) -> Dict[str, Any]:
        """
        Handle Stripe webhook events.
        
        Args:
            payload: Raw webhook payload
            signature: Stripe signature header
            
        Returns:
            Processing result
        """
        if not self.is_configured:
            return {"error": "Stripe not configured"}
        
        try:
            event = self._stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
        except Exception as e:
            self.logger.error("webhook_verification_failed", error=str(e))
            return {"error": "Invalid signature"}
        
        event_type = event["type"]
        data = event["data"]["object"]
        
        self.logger.info("webhook_received", event_type=event_type)
        
        # Handle different event types
        if event_type == "checkout.session.completed":
            return await self._handle_checkout_completed(data)
        
        elif event_type == "customer.subscription.updated":
            return await self._handle_subscription_updated(data)
        
        elif event_type == "customer.subscription.deleted":
            return await self._handle_subscription_deleted(data)
        
        elif event_type == "invoice.payment_failed":
            return await self._handle_payment_failed(data)
        
        return {"status": "ignored", "event_type": event_type}
    
    async def _handle_checkout_completed(self, data: Dict) -> Dict[str, Any]:
        """Handle successful checkout."""
        user_id = data.get("metadata", {}).get("user_id")
        subscription_id = data.get("subscription")
        customer_id = data.get("customer")
        
        if user_id:
            # Create subscription record
            self._subscriptions[user_id] = Subscription(
                user_id=user_id,
                tier=SubscriptionTier.PRO,
                status=SubscriptionStatus.ACTIVE,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
            )
            
            self.logger.info(
                "subscription_created",
                user_id=user_id,
                tier="pro"
            )
        
        return {"status": "processed", "action": "subscription_created"}
    
    async def _handle_subscription_updated(self, data: Dict) -> Dict[str, Any]:
        """Handle subscription update."""
        subscription_id = data.get("id")
        status = data.get("status")
        
        # Find and update user subscription
        for user_id, sub in self._subscriptions.items():
            if sub.stripe_subscription_id == subscription_id:
                sub.status = SubscriptionStatus(status)
                sub.cancel_at_period_end = data.get("cancel_at_period_end", False)
                
                self.logger.info(
                    "subscription_updated",
                    user_id=user_id,
                    status=status
                )
                break
        
        return {"status": "processed", "action": "subscription_updated"}
    
    async def _handle_subscription_deleted(self, data: Dict) -> Dict[str, Any]:
        """Handle subscription deletion."""
        subscription_id = data.get("id")
        
        # Find and downgrade user
        for user_id, sub in self._subscriptions.items():
            if sub.stripe_subscription_id == subscription_id:
                sub.tier = SubscriptionTier.FREE
                sub.status = SubscriptionStatus.CANCELED
                
                self.logger.info(
                    "subscription_deleted",
                    user_id=user_id
                )
                break
        
        return {"status": "processed", "action": "subscription_deleted"}
    
    async def _handle_payment_failed(self, data: Dict) -> Dict[str, Any]:
        """Handle failed payment."""
        customer_id = data.get("customer")
        
        self.logger.warning(
            "payment_failed",
            customer_id=customer_id
        )
        
        # Could send email notification here
        
        return {"status": "processed", "action": "payment_failed_notification"}
    
    def get_subscription(self, user_id: str) -> Optional[Subscription]:
        """Get user's subscription."""
        return self._subscriptions.get(user_id)
    
    def get_tier(self, user_id: str) -> SubscriptionTier:
        """Get user's subscription tier."""
        sub = self._subscriptions.get(user_id)
        if sub and sub.status == SubscriptionStatus.ACTIVE:
            return sub.tier
        return SubscriptionTier.FREE


# Singleton instance
_stripe_service: Optional[StripeService] = None


def get_stripe_service() -> StripeService:
    """Get or create the Stripe service singleton."""
    global _stripe_service
    if _stripe_service is None:
        _stripe_service = StripeService()
    return _stripe_service
