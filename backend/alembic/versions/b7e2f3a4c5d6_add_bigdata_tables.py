"""Add big data tables for price tracking and meta analysis

Revision ID: b7e2f3a4c5d6
Revises: 43e76aaf7374
Create Date: 2025-01-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e2f3a4c5d6'
down_revision: Union[str, None] = '43e76aaf7374'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pg_trgm extension for text search
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # =====================================================
    # Price Snapshots - Partitioned by month for time-series
    # =====================================================
    op.execute("""
        CREATE TABLE price_snapshots (
            time            TIMESTAMPTZ NOT NULL,
            trait_key       TEXT NOT NULL,
            class           TEXT NOT NULL,
            floor_eth       DECIMAL(20,8),
            avg_eth         DECIMAL(20,8),
            volume          INTEGER DEFAULT 0,
            listings_count  INTEGER DEFAULT 0,
            PRIMARY KEY (time, trait_key, class)
        ) PARTITION BY RANGE (time)
    """)

    # Create partitions for 2025
    months = [
        ('2025-01-01', '2025-02-01'),
        ('2025-02-01', '2025-03-01'),
        ('2025-03-01', '2025-04-01'),
        ('2025-04-01', '2025-05-01'),
        ('2025-05-01', '2025-06-01'),
        ('2025-06-01', '2025-07-01'),
        ('2025-07-01', '2025-08-01'),
        ('2025-08-01', '2025-09-01'),
        ('2025-09-01', '2025-10-01'),
        ('2025-10-01', '2025-11-01'),
        ('2025-11-01', '2025-12-01'),
        ('2025-12-01', '2026-01-01'),
    ]

    for i, (start, end) in enumerate(months, 1):
        partition_name = f"price_snapshots_2025_{i:02d}"
        op.execute(f"""
            CREATE TABLE {partition_name} PARTITION OF price_snapshots
            FOR VALUES FROM ('{start}') TO ('{end}')
        """)

    # Create indexes for price_snapshots
    op.execute("CREATE INDEX idx_price_snapshots_time_brin ON price_snapshots USING BRIN (time)")
    op.execute("CREATE INDEX idx_price_snapshots_trait ON price_snapshots (trait_key)")
    op.execute("CREATE INDEX idx_price_snapshots_class ON price_snapshots (class)")
    op.execute("CREATE INDEX idx_price_snapshots_trait_time ON price_snapshots (trait_key, time DESC)")

    # =====================================================
    # Detected Deals - For deal snatching opportunities
    # =====================================================
    op.create_table(
        'detected_deals',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('axie_id', sa.BigInteger, nullable=False, index=True),
        sa.Column('class', sa.String(20), nullable=False, index=True),
        sa.Column('price_eth', sa.Numeric(20, 8), nullable=False),
        sa.Column('avg_eth', sa.Numeric(20, 8)),
        sa.Column('discount_percent', sa.Float),
        sa.Column('deal_score', sa.Integer),
        sa.Column('is_snipe', sa.Boolean, default=False, index=True),
        sa.Column('part_analysis', sa.JSON),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('status', sa.String(20), default='active'),  # active, sold, expired
        sa.Column('sold_at', sa.DateTime(timezone=True)),
        sa.UniqueConstraint('axie_id', 'detected_at', name='uq_detected_deals_axie_time'),
    )

    # Index for finding active high-score deals
    op.execute("""
        CREATE INDEX idx_detected_deals_active_score
        ON detected_deals (deal_score DESC, detected_at DESC)
        WHERE status = 'active'
    """)

    # =====================================================
    # Meta Shifts - For tracking meta changes
    # =====================================================
    op.create_table(
        'meta_shifts',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('trait_key', sa.String(100), nullable=False, index=True),
        sa.Column('class', sa.String(20), nullable=False, index=True),
        sa.Column('shift_type', sa.String(20), nullable=False),  # rising, falling, emerging, fading
        sa.Column('confidence', sa.Integer),  # 0-100
        sa.Column('signals', sa.JSON),  # Array of signal descriptions
        sa.Column('velocity_24h', sa.Float),  # Price change % in 24h
        sa.Column('velocity_7d', sa.Float),   # Price change % in 7d
        sa.Column('volume_change_24h', sa.Float),  # Volume change % in 24h
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False, index=True),
    )

    # Index for finding recent high-confidence shifts
    op.execute("""
        CREATE INDEX idx_meta_shifts_recent
        ON meta_shifts (detected_at DESC, confidence DESC)
    """)

    # =====================================================
    # Listings Stream - For real-time listing tracking
    # =====================================================
    op.create_table(
        'listing_events',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('axie_id', sa.BigInteger, nullable=False, index=True),
        sa.Column('event_type', sa.String(20), nullable=False),  # listed, delisted, sold, price_change
        sa.Column('price_eth', sa.Numeric(20, 8)),
        sa.Column('previous_price_eth', sa.Numeric(20, 8)),
        sa.Column('seller_address', sa.String(42)),
        sa.Column('buyer_address', sa.String(42)),
        sa.Column('event_time', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('block_number', sa.BigInteger),
        sa.Column('transaction_hash', sa.String(66)),
        sa.Column('processed', sa.Boolean, default=False),
    )

    # Index for unprocessed events
    op.execute("""
        CREATE INDEX idx_listing_events_unprocessed
        ON listing_events (event_time DESC)
        WHERE processed = false
    """)

    # =====================================================
    # Trait Rankings - Aggregated trait value rankings
    # =====================================================
    op.create_table(
        'trait_rankings',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('trait_key', sa.String(100), nullable=False),
        sa.Column('class', sa.String(20), nullable=False),
        sa.Column('rank', sa.Integer, nullable=False),
        sa.Column('floor_eth', sa.Numeric(20, 8)),
        sa.Column('avg_eth', sa.Numeric(20, 8)),
        sa.Column('volume_24h', sa.Integer),
        sa.Column('price_change_24h', sa.Float),
        sa.Column('price_change_7d', sa.Float),
        sa.Column('calculated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('trait_key', 'class', 'calculated_at', name='uq_trait_rankings'),
    )

    # Index for getting latest rankings
    op.execute("""
        CREATE INDEX idx_trait_rankings_latest
        ON trait_rankings (class, calculated_at DESC, rank)
    """)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('trait_rankings')
    op.drop_table('listing_events')
    op.drop_table('meta_shifts')
    op.drop_table('detected_deals')

    # Drop partitions first
    for i in range(1, 13):
        op.execute(f"DROP TABLE IF EXISTS price_snapshots_2025_{i:02d}")

    op.execute("DROP TABLE IF EXISTS price_snapshots")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
