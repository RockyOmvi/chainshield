# ChainShield Database Setup

## Quick Start

```bash
# 1. Start PostgreSQL (via Docker)
docker-compose up -d postgres

# 2. Run migrations
cd backend
alembic upgrade head

# 3. Seed database
python scripts/seed_database.py
```

## Migration Commands

```bash
# Apply all migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# Rollback all migrations
alembic downgrade base

# Create new migration
alembic revision -m "description"

# Auto-generate migration from models
alembic revision --autogenerate -m "description"

# Show current revision
alembic current

# Show migration history
alembic history
```

## Seed Data

The seeding script creates:

| Entity | Count | Description |
|--------|-------|-------------|
| Users | 4 | Admin + 3 test users |
| API Keys | 4 | One per user + enterprise key |
| Alert Rules | 3 | Sample monitoring rules |

### Default Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@chainshield.io | ChainShield2024! |
| Analyst | analyst@chainshield.io | Analyst123! |
| User | user@chainshield.io | User123! |
| Enterprise | enterprise@chainshield.io | Enterprise123! |

### Custom Admin Password

```bash
ADMIN_PASSWORD=MySecurePassword python scripts/seed_database.py
```

## Environment Variables

Required in `.env`:

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/chainshield
```

## Tables Created

1. **users** - User accounts
2. **api_keys** - API authentication keys
3. **refresh_tokens** - JWT refresh tokens
4. **wallets** - Analyzed wallet data
5. **transactions** - Analyzed transaction data
6. **transaction_edges** - Graph relationships
7. **alert_rules** - User alert configurations
8. **alerts** - Generated alerts
9. **audit_logs** - Activity audit trail
