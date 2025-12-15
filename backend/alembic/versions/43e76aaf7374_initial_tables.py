"""Initial tables

Revision ID: 43e76aaf7374
Revises:
Create Date: 2025-01-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '43e76aaf7374'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types (with create_type=False since they may already exist)
    axie_class = sa.Enum(
        'beast', 'bug', 'bird', 'plant', 'aquatic', 'reptile', 'mech', 'dawn', 'dusk',
        name='axie_class',
        create_type=False
    )
    part_type = sa.Enum(
        'eyes', 'ears', 'mouth', 'horn', 'back', 'tail',
        name='part_type',
        create_type=False
    )
    gene_type = sa.Enum('d', 'r1', 'r2', name='gene_type', create_type=False)

    # Create types only if they don't exist
    axie_class.create(op.get_bind(), checkfirst=True)
    part_type.create(op.get_bind(), checkfirst=True)
    gene_type.create(op.get_bind(), checkfirst=True)

    # Create abilities table first (referenced by parts)
    op.create_table(
        'abilities',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ability_id', sa.String(50), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('class', axie_class, nullable=True),
        sa.Column('type', part_type, nullable=True),
        sa.Column('energy_cost', sa.SmallInteger(), default=1),
        sa.Column('damage', sa.SmallInteger(), default=0),
        sa.Column('shield', sa.SmallInteger(), default=0),
        sa.Column('heal', sa.SmallInteger(), default=0),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ability_id'),
    )

    # Create axies table
    op.create_table(
        'axies',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('class', axie_class, nullable=False),
        sa.Column('breed_count', sa.SmallInteger(), default=0),
        sa.Column('genes', sa.String(128), nullable=False),
        sa.Column('image_url', sa.Text(), nullable=True),
        sa.Column('owner_address', sa.String(42), nullable=False),
        sa.Column('birth_date', sa.DateTime(), nullable=True),
        sa.Column('matron_id', sa.BigInteger(), nullable=True),
        sa.Column('sire_id', sa.BigInteger(), nullable=True),
        sa.Column('purity_score', sa.SmallInteger(), nullable=True),
        sa.Column('gene_purity_score', sa.SmallInteger(), nullable=True),
        sa.Column('hp', sa.SmallInteger(), nullable=True),
        sa.Column('speed', sa.SmallInteger(), nullable=True),
        sa.Column('skill', sa.SmallInteger(), nullable=True),
        sa.Column('morale', sa.SmallInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['matron_id'], ['axies.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['sire_id'], ['axies.id'], ondelete='SET NULL'),
    )
    op.create_index('idx_axies_class', 'axies', ['class'])
    op.create_index('idx_axies_owner', 'axies', ['owner_address'])
    op.create_index('idx_axies_purity', 'axies', ['purity_score'])
    op.create_index('idx_axies_breed_count', 'axies', ['breed_count'])
    op.create_index('idx_axies_class_purity', 'axies', ['class', 'purity_score'])

    # Create parts reference table
    op.create_table(
        'parts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('part_id', sa.String(50), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('class', axie_class, nullable=False),
        sa.Column('type', part_type, nullable=False),
        sa.Column('ability_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('part_id'),
        sa.ForeignKeyConstraint(['ability_id'], ['abilities.id'], ondelete='SET NULL'),
    )
    op.create_index('idx_parts_class', 'parts', ['class'])
    op.create_index('idx_parts_type', 'parts', ['type'])

    # Create axie_parts junction table
    op.create_table(
        'axie_parts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('axie_id', sa.BigInteger(), nullable=False),
        sa.Column('part_id', sa.Integer(), nullable=False),
        sa.Column('position', part_type, nullable=False),
        sa.Column('gene_type', gene_type, nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['axie_id'], ['axies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['part_id'], ['parts.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('axie_id', 'position', 'gene_type', name='uq_axie_position_gene'),
    )
    op.create_index('idx_axie_parts_axie', 'axie_parts', ['axie_id'])
    op.create_index('idx_axie_parts_part', 'axie_parts', ['part_id'])
    op.create_index('idx_axie_parts_gene_type', 'axie_parts', ['gene_type'])

    # Create listings table
    op.create_table(
        'listings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('axie_id', sa.BigInteger(), nullable=False),
        sa.Column('seller_address', sa.String(42), nullable=False),
        sa.Column('price_eth', sa.Numeric(20, 8), nullable=False),
        sa.Column('price_usd', sa.Numeric(20, 2), nullable=True),
        sa.Column('listed_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(20), default='active'),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['axie_id'], ['axies.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_listings_axie', 'listings', ['axie_id'])
    op.create_index('idx_listings_seller', 'listings', ['seller_address'])
    op.create_index('idx_listings_status', 'listings', ['status'])
    op.create_index('idx_listings_price', 'listings', ['price_eth'])
    op.create_index('idx_listings_status_price', 'listings', ['status', 'price_eth'])

    # Create sales table
    op.create_table(
        'sales',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('axie_id', sa.BigInteger(), nullable=True),
        sa.Column('seller_address', sa.String(42), nullable=False),
        sa.Column('buyer_address', sa.String(42), nullable=False),
        sa.Column('price_eth', sa.Numeric(20, 8), nullable=False),
        sa.Column('price_usd', sa.Numeric(20, 2), nullable=True),
        sa.Column('tx_hash', sa.String(66), nullable=False),
        sa.Column('sold_at', sa.DateTime(), nullable=False),
        sa.Column('marketplace', sa.String(50), default='official'),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tx_hash'),
        sa.ForeignKeyConstraint(['axie_id'], ['axies.id'], ondelete='SET NULL'),
    )
    op.create_index('idx_sales_axie', 'sales', ['axie_id'])
    op.create_index('idx_sales_sold_at', 'sales', ['sold_at'])
    op.create_index('idx_sales_seller', 'sales', ['seller_address'])
    op.create_index('idx_sales_buyer', 'sales', ['buyer_address'])
    op.create_index('idx_sales_price', 'sales', ['price_eth'])

    # Create price_history table (designed for TimescaleDB hypertable)
    op.create_table(
        'price_history',
        sa.Column('time', sa.DateTime(), nullable=False),
        sa.Column('class', sa.String(20), nullable=False),
        sa.Column('trait_key', sa.String(100), nullable=False),
        sa.Column('floor_price_eth', sa.Numeric(20, 8), nullable=True),
        sa.Column('avg_price_eth', sa.Numeric(20, 8), nullable=True),
        sa.Column('median_price_eth', sa.Numeric(20, 8), nullable=True),
        sa.Column('max_price_eth', sa.Numeric(20, 8), nullable=True),
        sa.Column('volume', sa.Integer(), default=0),
        sa.Column('volume_eth', sa.Numeric(20, 8), default=0),
        sa.PrimaryKeyConstraint('time', 'class', 'trait_key'),
    )
    op.create_index('idx_price_history_time', 'price_history', ['time'])
    op.create_index('idx_price_history_class', 'price_history', ['class'])
    op.create_index('idx_price_history_trait', 'price_history', ['trait_key'])

    # Create wallets table
    op.create_table(
        'wallets',
        sa.Column('address', sa.String(42), nullable=False),
        sa.Column('alias', sa.String(100), nullable=True),
        sa.Column('first_seen', sa.DateTime(), nullable=True),
        sa.Column('last_active', sa.DateTime(), nullable=True),
        sa.Column('total_buy_volume_eth', sa.Numeric(20, 8), default=0),
        sa.Column('total_sell_volume_eth', sa.Numeric(20, 8), default=0),
        sa.Column('total_trades', sa.Integer(), default=0),
        sa.Column('axie_count', sa.Integer(), default=0),
        sa.Column('is_tracked', sa.Boolean(), default=False),
        sa.Column('is_whale', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('address'),
    )

    # Create wallet_holdings table
    op.create_table(
        'wallet_holdings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('wallet_address', sa.String(42), nullable=False),
        sa.Column('axie_id', sa.BigInteger(), nullable=False),
        sa.Column('acquired_at', sa.DateTime(), nullable=True),
        sa.Column('acquisition_price_eth', sa.Numeric(20, 8), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['wallet_address'], ['wallets.address'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['axie_id'], ['axies.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('wallet_address', 'axie_id', name='uq_wallet_axie'),
    )
    op.create_index('idx_holdings_wallet', 'wallet_holdings', ['wallet_address'])
    op.create_index('idx_holdings_axie', 'wallet_holdings', ['axie_id'])

    # Create breeding_pairs table
    op.create_table(
        'breeding_pairs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('matron_id', sa.BigInteger(), nullable=False),
        sa.Column('sire_id', sa.BigInteger(), nullable=False),
        sa.Column('breed_count', sa.Integer(), default=0),
        sa.Column('last_breed', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['matron_id'], ['axies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sire_id'], ['axies.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('matron_id', 'sire_id', name='uq_breeding_pair'),
    )
    op.create_index('idx_breeding_pairs_matron', 'breeding_pairs', ['matron_id'])
    op.create_index('idx_breeding_pairs_sire', 'breeding_pairs', ['sire_id'])

    # Create breeds table
    op.create_table(
        'breeds',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('pair_id', sa.Integer(), nullable=False),
        sa.Column('offspring_id', sa.BigInteger(), nullable=True),
        sa.Column('tx_hash', sa.String(66), nullable=False),
        sa.Column('breed_at', sa.DateTime(), nullable=False),
        sa.Column('breed_cost_slp', sa.Integer(), nullable=True),
        sa.Column('breed_cost_axs', sa.Numeric(20, 8), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tx_hash'),
        sa.ForeignKeyConstraint(['pair_id'], ['breeding_pairs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['offspring_id'], ['axies.id'], ondelete='SET NULL'),
    )
    op.create_index('idx_breeds_pair', 'breeds', ['pair_id'])
    op.create_index('idx_breeds_offspring', 'breeds', ['offspring_id'])
    op.create_index('idx_breeds_date', 'breeds', ['breed_at'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('breeds')
    op.drop_table('breeding_pairs')
    op.drop_table('wallet_holdings')
    op.drop_table('wallets')
    op.drop_table('price_history')
    op.drop_table('sales')
    op.drop_table('listings')
    op.drop_table('axie_parts')
    op.drop_table('parts')
    op.drop_table('axies')
    op.drop_table('abilities')

    # Drop enum types
    sa.Enum(name='gene_type').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='part_type').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='axie_class').drop(op.get_bind(), checkfirst=True)
