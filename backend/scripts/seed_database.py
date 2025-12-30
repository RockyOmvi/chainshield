#!/usr/bin/env python3
"""
Database Seeding Script

Creates initial test data for development and staging environments:
- Admin user
- Test users
- API keys for each user
- Sample alert rules

Usage:
    python scripts/seed_database.py
    
    # Or with custom admin password:
    ADMIN_PASSWORD=MySecurePassword123! python scripts/seed_database.py
"""

import asyncio
import os
import sys
import secrets
import hashlib
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import get_password_hash, hash_api_key
from app.models import User, APIKey, AlertRule


# =============================================================================
# Seed Data Configuration
# =============================================================================

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@chainshield.io")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ChainShield2024!")

TEST_USERS = [
    {
        "email": "analyst@chainshield.io",
        "password": "Analyst123!",
        "full_name": "Test Analyst",
        "role": "analyst",
        "plan": "pro",
    },
    {
        "email": "user@chainshield.io", 
        "password": "User123!",
        "full_name": "Test User",
        "role": "user",
        "plan": "free",
    },
    {
        "email": "enterprise@chainshield.io",
        "password": "Enterprise123!",
        "full_name": "Enterprise User",
        "role": "user",
        "plan": "enterprise",
    },
]


# =============================================================================
# Seeding Functions
# =============================================================================

async def seed_users(session: AsyncSession) -> dict[str, User]:
    """Seed users and return created user objects."""
    users = {}
    
    # Check if admin already exists
    result = await session.execute(
        select(User).where(User.email == ADMIN_EMAIL)
    )
    admin = result.scalar_one_or_none()
    
    if admin:
        print(f"  ⚠️  Admin user already exists: {ADMIN_EMAIL}")
        users["admin"] = admin
    else:
        # Create admin user
        admin = User(
            email=ADMIN_EMAIL,
            hashed_password=get_password_hash(ADMIN_PASSWORD),
            full_name="System Administrator",
            role="admin",
            plan="enterprise",
            is_active=True,
            is_verified=True,
        )
        session.add(admin)
        await session.flush()
        users["admin"] = admin
        print(f"  ✅ Created admin user: {ADMIN_EMAIL}")
    
    # Create test users
    for user_data in TEST_USERS:
        result = await session.execute(
            select(User).where(User.email == user_data["email"])
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"  ⚠️  User already exists: {user_data['email']}")
            users[user_data["role"]] = existing
        else:
            user = User(
                email=user_data["email"],
                hashed_password=get_password_hash(user_data["password"]),
                full_name=user_data["full_name"],
                role=user_data["role"],
                plan=user_data["plan"],
                is_active=True,
                is_verified=True,
            )
            session.add(user)
            await session.flush()
            users[user_data["role"]] = user
            print(f"  ✅ Created user: {user_data['email']}")
    
    return users


async def seed_api_keys(session: AsyncSession, users: dict[str, User]) -> list[dict]:
    """Seed API keys for users."""
    created_keys = []
    
    api_key_configs = [
        {
            "user_key": "admin",
            "name": "Admin Master Key",
            "scopes": ["read:wallet", "write:wallet", "read:transaction", "write:transaction", "admin"],
            "rate_limit": 10000,
        },
        {
            "user_key": "analyst",
            "name": "Analyst API Key",
            "scopes": ["read:wallet", "read:transaction", "read:alert"],
            "rate_limit": 5000,
        },
        {
            "user_key": "user",
            "name": "User API Key",
            "scopes": ["read:wallet", "read:transaction"],
            "rate_limit": 1000,
        },
        {
            "user_key": "user",  # Enterprise user key
            "name": "Enterprise SDK Key",
            "scopes": ["read:wallet", "write:wallet", "read:transaction", "write:transaction"],
            "rate_limit": 50000,
        },
    ]
    
    for config in api_key_configs:
        user = users.get(config["user_key"])
        if not user:
            print(f"  ⚠️  User not found for key: {config['name']}")
            continue
        
        # Generate API key
        raw_key = f"{settings.api_key_prefix}{secrets.token_urlsafe(32)}"
        key_prefix = raw_key[:12]
        key_hash = hash_api_key(raw_key)
        
        # Check if key with same name exists
        result = await session.execute(
            select(APIKey).where(
                APIKey.user_id == user.id,
                APIKey.name == config["name"]
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"  ⚠️  API key already exists: {config['name']}")
        else:
            api_key = APIKey(
                user_id=user.id,
                name=config["name"],
                key_prefix=key_prefix,
                key_hash=key_hash,
                scopes=config["scopes"],
                rate_limit=config["rate_limit"],
                is_active=True,
                expires_at=datetime.utcnow() + timedelta(days=365),
            )
            session.add(api_key)
            await session.flush()
            
            created_keys.append({
                "name": config["name"],
                "key": raw_key,
                "user": user.email,
            })
            print(f"  ✅ Created API key: {config['name']}")
    
    return created_keys


async def seed_alert_rules(session: AsyncSession, users: dict[str, User]) -> None:
    """Seed sample alert rules."""
    admin = users.get("admin")
    if not admin:
        print("  ⚠️  Admin user not found, skipping alert rules")
        return
    
    alert_rules = [
        {
            "name": "High Risk Wallet Alert",
            "description": "Alert when a wallet with risk score > 80 is analyzed",
            "rule_type": "risk_threshold",
            "conditions": {"risk_score": {"gte": 80}, "target_type": "wallet"},
            "actions": [{"type": "notification", "channel": "email"}],
            "priority": 1,
        },
        {
            "name": "Large Transaction Alert",
            "description": "Alert on transactions > 100 ETH",
            "rule_type": "value_threshold",
            "conditions": {"value_eth": {"gte": 100}, "target_type": "transaction"},
            "actions": [{"type": "notification", "channel": "webhook"}],
            "priority": 2,
        },
        {
            "name": "Known Scam Address Alert",
            "description": "Alert when interacting with flagged addresses",
            "rule_type": "address_match",
            "conditions": {"tags": {"contains": "scam"}},
            "actions": [{"type": "notification", "channel": "email"}, {"type": "block"}],
            "priority": 1,
        },
    ]
    
    for rule_data in alert_rules:
        result = await session.execute(
            select(AlertRule).where(
                AlertRule.user_id == admin.id,
                AlertRule.name == rule_data["name"]
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"  ⚠️  Alert rule already exists: {rule_data['name']}")
        else:
            rule = AlertRule(
                user_id=admin.id,
                name=rule_data["name"],
                description=rule_data["description"],
                rule_type=rule_data["rule_type"],
                conditions=rule_data["conditions"],
                actions=rule_data["actions"],
                priority=rule_data["priority"],
                is_active=True,
            )
            session.add(rule)
            print(f"  ✅ Created alert rule: {rule_data['name']}")


# =============================================================================
# Main Entry Point
# =============================================================================

async def main():
    """Run database seeding."""
    print("\n" + "=" * 60)
    print("🌱 ChainShield Database Seeding")
    print("=" * 60)
    
    # Create async engine
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        try:
            print("\n📦 Seeding Users...")
            users = await seed_users(session)
            
            print("\n🔑 Seeding API Keys...")
            api_keys = await seed_api_keys(session, users)
            
            print("\n🚨 Seeding Alert Rules...")
            await seed_alert_rules(session, users)
            
            # Commit all changes
            await session.commit()
            
            print("\n" + "=" * 60)
            print("✅ Database seeding complete!")
            print("=" * 60)
            
            # Print API keys for reference
            if api_keys:
                print("\n🔐 Generated API Keys (save these!):\n")
                print("-" * 60)
                for key_info in api_keys:
                    print(f"  Name: {key_info['name']}")
                    print(f"  User: {key_info['user']}")
                    print(f"  Key:  {key_info['key']}")
                    print("-" * 60)
                
                print("\n⚠️  Store these keys securely - they won't be shown again!")
            
            print("\n📝 Default Credentials:")
            print(f"  Admin: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
            for user in TEST_USERS:
                print(f"  {user['role'].title()}: {user['email']} / {user['password']}")
            
        except Exception as e:
            await session.rollback()
            print(f"\n❌ Seeding failed: {e}")
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
