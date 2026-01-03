"""
ChainShield API v1 Package

Registers all v1 API routers.
"""

from fastapi import APIRouter

from app.api.v1.wallet import router as wallet_router
from app.api.v1.transaction import router as transaction_router
from app.api.v1.explain import router as explain_router
from app.api.v1.risk import router as risk_router
from app.api.v1.auth import router as auth_router
from app.api.v1.admin import router as admin_router

# Create main v1 router
api_v1_router = APIRouter()

# Include all endpoint routers
api_v1_router.include_router(wallet_router)
api_v1_router.include_router(transaction_router)
api_v1_router.include_router(explain_router)
api_v1_router.include_router(risk_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(admin_router)

__all__ = ["api_v1_router"]


