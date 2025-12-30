"""Initial migration - Create all tables

Revision ID: 0001
Revises: 
Create Date: 2024-12-30 06:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==========================================================================
    # Users Table
    # ==========================================================================
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=50), server_default='user', nullable=False),
        sa.Column('plan', sa.String(length=50), server_default='free', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_verified', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_role', 'users', ['role'], unique=False)
    
    # ==========================================================================
    # API Keys Table
    # ==========================================================================
    op.create_table(
        'api_keys',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('key_prefix', sa.String(length=12), nullable=False),
        sa.Column('key_hash', sa.String(length=255), nullable=False),
        sa.Column('scopes', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('rate_limit', sa.Integer(), server_default='1000', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_api_keys_key_hash', 'api_keys', ['key_hash'], unique=True)
    op.create_index('ix_api_keys_key_prefix', 'api_keys', ['key_prefix'], unique=False)
    op.create_index('ix_api_keys_user_id', 'api_keys', ['user_id'], unique=False)
    
    # ==========================================================================
    # Refresh Tokens Table
    # ==========================================================================
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=False),
        sa.Column('device_info', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('is_revoked', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_refresh_tokens_token_hash', 'refresh_tokens', ['token_hash'], unique=True)
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'], unique=False)
    
    # ==========================================================================
    # Wallets Table
    # ==========================================================================
    op.create_table(
        'wallets',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('address', sa.String(length=66), nullable=False),
        sa.Column('chain', sa.String(length=20), server_default='ethereum', nullable=False),
        sa.Column('label', sa.String(length=255), nullable=True),
        sa.Column('wallet_type', sa.String(length=50), nullable=True),
        sa.Column('risk_score', sa.Integer(), nullable=True),
        sa.Column('risk_level', sa.String(length=20), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('is_contract', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tags', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('extra_data', sa.JSON(), server_default='{}', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_wallets_address', 'wallets', ['address'], unique=False)
    op.create_index('ix_wallets_address_chain', 'wallets', ['address', 'chain'], unique=True)
    op.create_index('ix_wallets_chain', 'wallets', ['chain'], unique=False)
    op.create_index('ix_wallets_risk_score', 'wallets', ['risk_score'], unique=False)
    
    # ==========================================================================
    # Transactions Table
    # ==========================================================================
    op.create_table(
        'transactions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tx_hash', sa.String(length=66), nullable=False),
        sa.Column('chain', sa.String(length=20), server_default='ethereum', nullable=False),
        sa.Column('block_number', sa.BigInteger(), nullable=True),
        sa.Column('block_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('from_address', sa.String(length=66), nullable=False),
        sa.Column('to_address', sa.String(length=66), nullable=True),
        sa.Column('value_wei', sa.Numeric(precision=78, scale=0), nullable=True),
        sa.Column('value_eth', sa.Numeric(precision=36, scale=18), nullable=True),
        sa.Column('gas_used', sa.BigInteger(), nullable=True),
        sa.Column('gas_price', sa.BigInteger(), nullable=True),
        sa.Column('tx_type', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('risk_score', sa.Integer(), nullable=True),
        sa.Column('risk_level', sa.String(length=20), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('flags', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('extra_data', sa.JSON(), server_default='{}', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_transactions_tx_hash', 'transactions', ['tx_hash'], unique=False)
    op.create_index('ix_transactions_tx_hash_chain', 'transactions', ['tx_hash', 'chain'], unique=True)
    op.create_index('ix_transactions_chain', 'transactions', ['chain'], unique=False)
    op.create_index('ix_transactions_from_address', 'transactions', ['from_address'], unique=False)
    op.create_index('ix_transactions_to_address', 'transactions', ['to_address'], unique=False)
    op.create_index('ix_transactions_block_number', 'transactions', ['block_number'], unique=False)
    op.create_index('ix_transactions_risk_score', 'transactions', ['risk_score'], unique=False)
    
    # ==========================================================================
    # Transaction Edges Table (Graph)
    # ==========================================================================
    op.create_table(
        'transaction_edges',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tx_hash', sa.String(length=66), nullable=False),
        sa.Column('chain', sa.String(length=20), server_default='ethereum', nullable=False),
        sa.Column('from_address', sa.String(length=66), nullable=False),
        sa.Column('to_address', sa.String(length=66), nullable=False),
        sa.Column('value_eth', sa.Numeric(precision=36, scale=18), nullable=True),
        sa.Column('edge_type', sa.String(length=50), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_transaction_edges_from_address', 'transaction_edges', ['from_address'], unique=False)
    op.create_index('ix_transaction_edges_to_address', 'transaction_edges', ['to_address'], unique=False)
    op.create_index('ix_transaction_edges_tx_hash', 'transaction_edges', ['tx_hash'], unique=False)
    
    # ==========================================================================
    # Alert Rules Table
    # ==========================================================================
    op.create_table(
        'alert_rules',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('rule_type', sa.String(length=50), nullable=False),
        sa.Column('conditions', sa.JSON(), nullable=False),
        sa.Column('actions', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('priority', sa.Integer(), server_default='5', nullable=False),
        sa.Column('cooldown_minutes', sa.Integer(), server_default='60', nullable=False),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trigger_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_alert_rules_user_id', 'alert_rules', ['user_id'], unique=False)
    op.create_index('ix_alert_rules_rule_type', 'alert_rules', ['rule_type'], unique=False)
    
    # ==========================================================================
    # Alerts Table
    # ==========================================================================
    op.create_table(
        'alerts',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('rule_id', sa.BigInteger(), nullable=True),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('target_type', sa.String(length=50), nullable=True),
        sa.Column('target_id', sa.String(length=66), nullable=True),
        sa.Column('risk_score', sa.Integer(), nullable=True),
        sa.Column('is_read', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_acknowledged', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('extra_data', sa.JSON(), server_default='{}', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['rule_id'], ['alert_rules.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_alerts_user_id', 'alerts', ['user_id'], unique=False)
    op.create_index('ix_alerts_alert_type', 'alerts', ['alert_type'], unique=False)
    op.create_index('ix_alerts_severity', 'alerts', ['severity'], unique=False)
    op.create_index('ix_alerts_created_at', 'alerts', ['created_at'], unique=False)
    
    # ==========================================================================
    # Audit Logs Table
    # ==========================================================================
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('resource_id', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('request_id', sa.String(length=36), nullable=True),
        sa.Column('details', sa.JSON(), server_default='{}', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'], unique=False)
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'], unique=False)
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'], unique=False)
    op.create_index('ix_audit_logs_resource_type', 'audit_logs', ['resource_type'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order (respect foreign keys)
    op.drop_table('audit_logs')
    op.drop_table('alerts')
    op.drop_table('alert_rules')
    op.drop_table('transaction_edges')
    op.drop_table('transactions')
    op.drop_table('wallets')
    op.drop_table('refresh_tokens')
    op.drop_table('api_keys')
    op.drop_table('users')
