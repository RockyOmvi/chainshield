"""Initial migration - Create all tables

Revision ID: 001_initial
Create Date: 2026-01-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255)),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('email_verified', sa.Boolean(), default=False),
        sa.Column('email_verified_at', sa.DateTime(timezone=True)),
        sa.Column('tier', sa.String(20), default='free'),
        sa.Column('stripe_customer_id', sa.String(255)),
        sa.Column('stripe_subscription_id', sa.String(255)),
        sa.Column('is_admin', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_login_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_stripe_customer_id', 'users', ['stripe_customer_id'])
    
    # API Keys table
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('key_id', sa.String(32), unique=True, nullable=False),
        sa.Column('key_hash', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), default='Default Key'),
        sa.Column('scopes', postgresql.JSON(), default=list),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True)),
        sa.Column('rate_limit_override', sa.Integer()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_api_keys_key_id', 'api_keys', ['key_id'])
    op.create_index('ix_api_keys_user_active', 'api_keys', ['user_id', 'is_active'])
    
    # Usage Records table
    op.create_table(
        'usage_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('requests_count', sa.Integer(), default=0),
        sa.Column('assessments_count', sa.Integer(), default=0),
        sa.Column('blocked_count', sa.Integer(), default=0),
        sa.Column('tier', sa.String(20), nullable=False),
        sa.Column('overage_count', sa.Integer(), default=0),
    )
    op.create_index('ix_usage_user_period', 'usage_records', ['user_id', 'period_start'])
    
    # Assessments table
    op.create_table(
        'assessments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('api_key_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('api_keys.id')),
        sa.Column('address', sa.String(255), nullable=False),
        sa.Column('chain', sa.String(50), default='ethereum'),
        sa.Column('risk_score', sa.Float(), nullable=False),
        sa.Column('risk_level', sa.String(20), nullable=False),
        sa.Column('blocked', sa.Boolean(), default=False),
        sa.Column('factors', postgresql.JSON(), default=list),
        sa.Column('entity_match', sa.String(255)),
        sa.Column('response_time_ms', sa.Integer()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_assessments_address', 'assessments', ['address'])
    op.create_index('ix_assessments_address_chain', 'assessments', ['address', 'chain'])
    op.create_index('ix_assessments_blocked', 'assessments', ['blocked', 'created_at'])
    op.create_index('ix_assessments_created_at', 'assessments', ['created_at'])
    
    # Blocklist table
    op.create_table(
        'blocklist',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('address', sa.String(255), unique=True, nullable=False),
        sa.Column('chain', sa.String(50), default='all'),
        sa.Column('reason', sa.Text()),
        sa.Column('source', sa.String(100)),
        sa.Column('added_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_blocklist_address', 'blocklist', ['address'])
    
    # Webhook Subscriptions table
    op.create_table(
        'webhook_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('url', sa.String(500), nullable=False),
        sa.Column('secret', sa.String(255)),
        sa.Column('events', postgresql.JSON(), default=list),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('failure_count', sa.Integer(), default=0),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True)),
        sa.Column('last_failed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('webhook_subscriptions')
    op.drop_table('blocklist')
    op.drop_table('assessments')
    op.drop_table('usage_records')
    op.drop_table('api_keys')
    op.drop_table('users')
