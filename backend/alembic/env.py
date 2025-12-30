"""
Alembic Migrations Environment

Configures Alembic to work with ChainShield's SQLAlchemy models.
Uses synchronous engine for migrations.
"""

from logging.config import fileConfig

from sqlalchemy import pool, create_engine
from sqlalchemy.engine import Connection
from alembic import context

# Import our models and config
from app.core.config import settings
from app.core.database import Base

# Import all models to register them with Base.metadata
from app.models import (  # noqa
    Wallet,
    Transaction,
    TransactionEdge,
    User,
    APIKey,
    RefreshToken,
    Alert,
    AlertRule,
    AuditLog,
)

# Alembic Config object
config = context.config

# Set the database URL from our settings
# Convert asyncpg URL to psycopg2 for sync migrations
db_url = settings.database_url
sync_database_url = db_url.replace("+asyncpg", "+psycopg2")
config.set_main_option("sqlalchemy.url", sync_database_url)

# Setup logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    Generates SQL script without connecting to database.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode using sync engine.
    """
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
