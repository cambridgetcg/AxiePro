"""Add wallet token balances table

Revision ID: 202601311300_wallet_balances
Revises: 20260131_restore_sales_fk_deferrable
Create Date: 2026-01-31 13:00:00

Enables real-time wallet token balance tracking via Ronin RPC.
Supports: RON, WETH, WRON, AXS, SLP
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

# Revision identifiers
revision = '202601311300_wallet_balances'
down_revision = '20260131_restore_sales_fk_deferrable'
branch_labels = None
depends_on = None


def upgrade():
    # Create enum for token types
    token_type_enum = ENUM(
        'RON', 'WETH', 'WRON', 'AXS', 'SLP',
        name='token_type',
        create_type=True,
        schema='axie'
    )

    # Create wallet_token_balances table
    op.create_table(
        'wallet_token_balances',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            'wallet_address',
            sa.String(42),
            sa.ForeignKey('axie.wallets.address', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('token_type', token_type_enum, nullable=False),

        # Balance data
        sa.Column(
            'balance',
            sa.Numeric(20, 8),
            nullable=False,
            comment='Token balance in native units (e.g., 1.5 WETH)',
        ),
        sa.Column(
            'balance_usd',
            sa.Numeric(20, 2),
            nullable=True,
            comment='USD value at last update',
        ),
        sa.Column(
            'token_price_usd',
            sa.Numeric(20, 8),
            nullable=True,
            comment='Token price in USD at last update',
        ),

        # Metadata
        sa.Column(
            'last_updated',
            sa.DateTime(timezone=True),
            nullable=False,
            comment='When balance was last fetched from blockchain',
        ),
        sa.Column(
            'block_number',
            sa.BigInteger(),
            nullable=True,
            comment='Block number at last update (for debugging)',
        ),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            onupdate=sa.text('now()'),
        ),

        # Constraints
        sa.UniqueConstraint('wallet_address', 'token_type', name='uq_wallet_token'),

        schema='axie',
    )

    # Indexes for efficient queries
    op.create_index(
        'idx_wallet_token_balances_wallet',
        'wallet_token_balances',
        ['wallet_address'],
        schema='axie',
    )
    op.create_index(
        'idx_wallet_token_balances_token',
        'wallet_token_balances',
        ['token_type'],
        schema='axie',
    )
    op.create_index(
        'idx_wallet_token_balances_updated',
        'wallet_token_balances',
        ['last_updated'],
        schema='axie',
    )
    op.create_index(
        'idx_wallet_token_balances_wallet_updated',
        'wallet_token_balances',
        ['wallet_address', 'last_updated'],
        schema='axie',
    )


def downgrade():
    op.drop_table('wallet_token_balances', schema='axie')
    op.execute('DROP TYPE IF EXISTS axie.token_type')
