"""
Database Migration Lambda

Runs database migrations against Aurora PostgreSQL.
This Lambda has VPC access and can connect to the private Aurora cluster.

Uses raw SQL from migration files instead of full Alembic machinery
to minimize dependencies and runtime complexity.
"""
import json
import os

# Import shared utilities from common module
from src.lambdas.common import (
    logger,
    get_db_connection,
)


# Migration scripts (based on alembic versions)
MIGRATION_SCRIPTS = {
    "43e76aaf7374": """
-- Migration: 43e76aaf7374 - Initial tables
-- Create enum types
DO $$ BEGIN
    CREATE TYPE axie_class AS ENUM ('beast', 'bug', 'bird', 'plant', 'aquatic', 'reptile', 'mech', 'dawn', 'dusk');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE part_type AS ENUM ('eyes', 'ears', 'mouth', 'horn', 'back', 'tail');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE gene_type AS ENUM ('d', 'r1', 'r2');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Create abilities table
CREATE TABLE IF NOT EXISTS abilities (
    id SERIAL PRIMARY KEY,
    ability_id VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    class axie_class,
    type part_type,
    energy_cost SMALLINT DEFAULT 1,
    damage SMALLINT DEFAULT 0,
    shield SMALLINT DEFAULT 0,
    heal SMALLINT DEFAULT 0,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create axies table
CREATE TABLE IF NOT EXISTS axies (
    id BIGINT PRIMARY KEY,
    name VARCHAR(255),
    class axie_class NOT NULL,
    breed_count SMALLINT DEFAULT 0,
    genes VARCHAR(128) NOT NULL,
    image_url TEXT,
    owner_address VARCHAR(42) NOT NULL,
    birth_date TIMESTAMP,
    matron_id BIGINT REFERENCES axies(id) ON DELETE SET NULL,
    sire_id BIGINT REFERENCES axies(id) ON DELETE SET NULL,
    purity_score SMALLINT,
    gene_purity_score SMALLINT,
    hp SMALLINT,
    speed SMALLINT,
    skill SMALLINT,
    morale SMALLINT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_axies_class ON axies(class);
CREATE INDEX IF NOT EXISTS idx_axies_owner ON axies(owner_address);
CREATE INDEX IF NOT EXISTS idx_axies_purity ON axies(purity_score);
CREATE INDEX IF NOT EXISTS idx_axies_breed_count ON axies(breed_count);
CREATE INDEX IF NOT EXISTS idx_axies_class_purity ON axies(class, purity_score);

-- Create parts reference table
CREATE TABLE IF NOT EXISTS parts (
    id SERIAL PRIMARY KEY,
    part_id VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    class axie_class NOT NULL,
    type part_type NOT NULL,
    ability_id INTEGER REFERENCES abilities(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_parts_class ON parts(class);
CREATE INDEX IF NOT EXISTS idx_parts_type ON parts(type);

-- Create axie_parts junction table
CREATE TABLE IF NOT EXISTS axie_parts (
    id SERIAL PRIMARY KEY,
    axie_id BIGINT NOT NULL REFERENCES axies(id) ON DELETE CASCADE,
    part_id INTEGER NOT NULL REFERENCES parts(id) ON DELETE CASCADE,
    position part_type NOT NULL,
    gene_type gene_type NOT NULL,
    UNIQUE(axie_id, position, gene_type)
);
CREATE INDEX IF NOT EXISTS idx_axie_parts_axie ON axie_parts(axie_id);
CREATE INDEX IF NOT EXISTS idx_axie_parts_part ON axie_parts(part_id);
CREATE INDEX IF NOT EXISTS idx_axie_parts_gene_type ON axie_parts(gene_type);

-- Create listings table
CREATE TABLE IF NOT EXISTS listings (
    id SERIAL PRIMARY KEY,
    axie_id BIGINT NOT NULL REFERENCES axies(id) ON DELETE CASCADE,
    seller_address VARCHAR(42) NOT NULL,
    price_eth NUMERIC(20, 8) NOT NULL,
    price_usd NUMERIC(20, 2),
    listed_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_listings_axie ON listings(axie_id);
CREATE INDEX IF NOT EXISTS idx_listings_seller ON listings(seller_address);
CREATE INDEX IF NOT EXISTS idx_listings_status ON listings(status);
CREATE INDEX IF NOT EXISTS idx_listings_price ON listings(price_eth);
CREATE INDEX IF NOT EXISTS idx_listings_status_price ON listings(status, price_eth);

-- Create sales table
CREATE TABLE IF NOT EXISTS sales (
    id SERIAL PRIMARY KEY,
    axie_id BIGINT REFERENCES axies(id) ON DELETE SET NULL,
    seller_address VARCHAR(42) NOT NULL,
    buyer_address VARCHAR(42) NOT NULL,
    price_eth NUMERIC(20, 8) NOT NULL,
    price_usd NUMERIC(20, 2),
    tx_hash VARCHAR(66) NOT NULL UNIQUE,
    sold_at TIMESTAMP NOT NULL,
    marketplace VARCHAR(50) DEFAULT 'official',
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sales_axie ON sales(axie_id);
CREATE INDEX IF NOT EXISTS idx_sales_sold_at ON sales(sold_at);
CREATE INDEX IF NOT EXISTS idx_sales_seller ON sales(seller_address);
CREATE INDEX IF NOT EXISTS idx_sales_buyer ON sales(buyer_address);
CREATE INDEX IF NOT EXISTS idx_sales_price ON sales(price_eth);

-- Create price_history table
CREATE TABLE IF NOT EXISTS price_history (
    time TIMESTAMP NOT NULL,
    class VARCHAR(20) NOT NULL,
    trait_key VARCHAR(100) NOT NULL,
    floor_price_eth NUMERIC(20, 8),
    avg_price_eth NUMERIC(20, 8),
    median_price_eth NUMERIC(20, 8),
    max_price_eth NUMERIC(20, 8),
    volume INTEGER DEFAULT 0,
    volume_eth NUMERIC(20, 8) DEFAULT 0,
    PRIMARY KEY (time, class, trait_key)
);
CREATE INDEX IF NOT EXISTS idx_price_history_time ON price_history(time);
CREATE INDEX IF NOT EXISTS idx_price_history_class ON price_history(class);
CREATE INDEX IF NOT EXISTS idx_price_history_trait ON price_history(trait_key);

-- Create wallets table
CREATE TABLE IF NOT EXISTS wallets (
    address VARCHAR(42) PRIMARY KEY,
    alias VARCHAR(100),
    first_seen TIMESTAMP,
    last_active TIMESTAMP,
    total_buy_volume_eth NUMERIC(20, 8) DEFAULT 0,
    total_sell_volume_eth NUMERIC(20, 8) DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    axie_count INTEGER DEFAULT 0,
    is_tracked BOOLEAN DEFAULT FALSE,
    is_whale BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create wallet_holdings table
CREATE TABLE IF NOT EXISTS wallet_holdings (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(42) NOT NULL REFERENCES wallets(address) ON DELETE CASCADE,
    axie_id BIGINT NOT NULL REFERENCES axies(id) ON DELETE CASCADE,
    acquired_at TIMESTAMP,
    acquisition_price_eth NUMERIC(20, 8),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(wallet_address, axie_id)
);
CREATE INDEX IF NOT EXISTS idx_holdings_wallet ON wallet_holdings(wallet_address);
CREATE INDEX IF NOT EXISTS idx_holdings_axie ON wallet_holdings(axie_id);

-- Create breeding_pairs table
CREATE TABLE IF NOT EXISTS breeding_pairs (
    id SERIAL PRIMARY KEY,
    matron_id BIGINT NOT NULL REFERENCES axies(id) ON DELETE CASCADE,
    sire_id BIGINT NOT NULL REFERENCES axies(id) ON DELETE CASCADE,
    breed_count INTEGER DEFAULT 0,
    last_breed TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(matron_id, sire_id)
);
CREATE INDEX IF NOT EXISTS idx_breeding_pairs_matron ON breeding_pairs(matron_id);
CREATE INDEX IF NOT EXISTS idx_breeding_pairs_sire ON breeding_pairs(sire_id);

-- Create breeds table
CREATE TABLE IF NOT EXISTS breeds (
    id SERIAL PRIMARY KEY,
    pair_id INTEGER NOT NULL REFERENCES breeding_pairs(id) ON DELETE CASCADE,
    offspring_id BIGINT REFERENCES axies(id) ON DELETE SET NULL,
    tx_hash VARCHAR(66) NOT NULL UNIQUE,
    breed_at TIMESTAMP NOT NULL,
    breed_cost_slp INTEGER,
    breed_cost_axs NUMERIC(20, 8),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_breeds_pair ON breeds(pair_id);
CREATE INDEX IF NOT EXISTS idx_breeds_offspring ON breeds(offspring_id);
CREATE INDEX IF NOT EXISTS idx_breeds_date ON breeds(breed_at);

-- Create alembic_version table if not exists
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    PRIMARY KEY (version_num)
);
""",
    "b7e2f3a4c5d6": """
-- Migration: b7e2f3a4c5d6 - Add big data tables
-- Enable pg_trgm extension for text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create price_snapshots partitioned table
CREATE TABLE IF NOT EXISTS price_snapshots (
    time            TIMESTAMPTZ NOT NULL,
    trait_key       TEXT NOT NULL,
    class           TEXT NOT NULL,
    floor_eth       DECIMAL(20,8),
    avg_eth         DECIMAL(20,8),
    volume          INTEGER DEFAULT 0,
    listings_count  INTEGER DEFAULT 0,
    PRIMARY KEY (time, trait_key, class)
) PARTITION BY RANGE (time);

-- Create partitions for 2025 and 2026
DO $$
DECLARE
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
BEGIN
    -- 2025 partitions
    FOR i IN 1..12 LOOP
        partition_name := 'price_snapshots_2025_' || LPAD(i::TEXT, 2, '0');
        start_date := DATE '2025-01-01' + ((i-1) || ' months')::INTERVAL;
        end_date := DATE '2025-01-01' + (i || ' months')::INTERVAL;

        IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = partition_name) THEN
            EXECUTE format(
                'CREATE TABLE %I PARTITION OF price_snapshots FOR VALUES FROM (%L) TO (%L)',
                partition_name, start_date, end_date
            );
        END IF;
    END LOOP;

    -- 2026 partitions
    FOR i IN 1..12 LOOP
        partition_name := 'price_snapshots_2026_' || LPAD(i::TEXT, 2, '0');
        start_date := DATE '2026-01-01' + ((i-1) || ' months')::INTERVAL;
        end_date := DATE '2026-01-01' + (i || ' months')::INTERVAL;

        IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = partition_name) THEN
            EXECUTE format(
                'CREATE TABLE %I PARTITION OF price_snapshots FOR VALUES FROM (%L) TO (%L)',
                partition_name, start_date, end_date
            );
        END IF;
    END LOOP;
END $$;

-- Create indexes for price_snapshots
CREATE INDEX IF NOT EXISTS idx_price_snapshots_time_brin ON price_snapshots USING BRIN (time);
CREATE INDEX IF NOT EXISTS idx_price_snapshots_trait ON price_snapshots (trait_key);
CREATE INDEX IF NOT EXISTS idx_price_snapshots_class ON price_snapshots (class);
CREATE INDEX IF NOT EXISTS idx_price_snapshots_trait_time ON price_snapshots (trait_key, time DESC);

-- Create detected_deals table
CREATE TABLE IF NOT EXISTS detected_deals (
    id BIGSERIAL PRIMARY KEY,
    axie_id BIGINT NOT NULL,
    class VARCHAR(20) NOT NULL,
    price_eth NUMERIC(20, 8) NOT NULL,
    avg_eth NUMERIC(20, 8),
    discount_percent FLOAT,
    deal_score INTEGER,
    is_snipe BOOLEAN DEFAULT FALSE,
    part_analysis JSONB,
    detected_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    sold_at TIMESTAMPTZ,
    UNIQUE(axie_id, detected_at)
);
CREATE INDEX IF NOT EXISTS idx_detected_deals_axie ON detected_deals(axie_id);
CREATE INDEX IF NOT EXISTS idx_detected_deals_class ON detected_deals(class);
CREATE INDEX IF NOT EXISTS idx_detected_deals_detected_at ON detected_deals(detected_at);
CREATE INDEX IF NOT EXISTS idx_detected_deals_is_snipe ON detected_deals(is_snipe);

-- Index for finding active high-score deals
CREATE INDEX IF NOT EXISTS idx_detected_deals_active_score
ON detected_deals (deal_score DESC, detected_at DESC)
WHERE status = 'active';

-- Create meta_shifts table
CREATE TABLE IF NOT EXISTS meta_shifts (
    id BIGSERIAL PRIMARY KEY,
    trait_key VARCHAR(100) NOT NULL,
    class VARCHAR(20) NOT NULL,
    shift_type VARCHAR(20) NOT NULL,
    confidence INTEGER,
    signals JSONB,
    velocity_24h FLOAT,
    velocity_7d FLOAT,
    volume_change_24h FLOAT,
    detected_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_meta_shifts_trait ON meta_shifts(trait_key);
CREATE INDEX IF NOT EXISTS idx_meta_shifts_class ON meta_shifts(class);
CREATE INDEX IF NOT EXISTS idx_meta_shifts_detected_at ON meta_shifts(detected_at);

-- Index for finding recent high-confidence shifts
CREATE INDEX IF NOT EXISTS idx_meta_shifts_recent
ON meta_shifts (detected_at DESC, confidence DESC);

-- Create listing_events table
CREATE TABLE IF NOT EXISTS listing_events (
    id BIGSERIAL PRIMARY KEY,
    axie_id BIGINT NOT NULL,
    event_type VARCHAR(20) NOT NULL,
    price_eth NUMERIC(20, 8),
    previous_price_eth NUMERIC(20, 8),
    seller_address VARCHAR(42),
    buyer_address VARCHAR(42),
    event_time TIMESTAMPTZ NOT NULL,
    block_number BIGINT,
    transaction_hash VARCHAR(66),
    processed BOOLEAN DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_listing_events_axie ON listing_events(axie_id);
CREATE INDEX IF NOT EXISTS idx_listing_events_time ON listing_events(event_time);

-- Index for unprocessed events
CREATE INDEX IF NOT EXISTS idx_listing_events_unprocessed
ON listing_events (event_time DESC)
WHERE processed = false;

-- Create trait_rankings table
CREATE TABLE IF NOT EXISTS trait_rankings (
    id BIGSERIAL PRIMARY KEY,
    trait_key VARCHAR(100) NOT NULL,
    class VARCHAR(20) NOT NULL,
    rank INTEGER NOT NULL,
    floor_eth NUMERIC(20, 8),
    avg_eth NUMERIC(20, 8),
    volume_24h INTEGER,
    price_change_24h FLOAT,
    price_change_7d FLOAT,
    calculated_at TIMESTAMPTZ NOT NULL,
    UNIQUE(trait_key, class, calculated_at)
);

-- Index for getting latest rankings
CREATE INDEX IF NOT EXISTS idx_trait_rankings_latest
ON trait_rankings (class, calculated_at DESC, rank);
""",
    "c3d4e5f6g7h8": """
-- Migration: c3d4e5f6g7h8 - Add 2026 partitions for price_snapshots
-- This ensures data for 2026 can be stored

DO $$
DECLARE
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
BEGIN
    -- 2026 partitions (may already exist from previous migration, so use IF NOT EXISTS pattern)
    FOR i IN 1..12 LOOP
        partition_name := 'price_snapshots_2026_' || LPAD(i::TEXT, 2, '0');
        start_date := DATE '2026-01-01' + ((i-1) || ' months')::INTERVAL;
        end_date := DATE '2026-01-01' + (i || ' months')::INTERVAL;

        IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = partition_name) THEN
            EXECUTE format(
                'CREATE TABLE %I PARTITION OF price_snapshots FOR VALUES FROM (%L) TO (%L)',
                partition_name, start_date, end_date
            );
            RAISE NOTICE 'Created partition: %', partition_name;
        ELSE
            RAISE NOTICE 'Partition already exists: %', partition_name;
        END IF;
    END LOOP;

    -- Also add 2027 partitions for future-proofing
    FOR i IN 1..12 LOOP
        partition_name := 'price_snapshots_2027_' || LPAD(i::TEXT, 2, '0');
        start_date := DATE '2027-01-01' + ((i-1) || ' months')::INTERVAL;
        end_date := DATE '2027-01-01' + (i || ' months')::INTERVAL;

        IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = partition_name) THEN
            EXECUTE format(
                'CREATE TABLE %I PARTITION OF price_snapshots FOR VALUES FROM (%L) TO (%L)',
                partition_name, start_date, end_date
            );
            RAISE NOTICE 'Created partition: %', partition_name;
        ELSE
            RAISE NOTICE 'Partition already exists: %', partition_name;
        END IF;
    END LOOP;
END $$;
""",
    "d4e5f6g7h8i9": """
-- Migration: d4e5f6g7h8i9 - Fix listings table for ingestion
-- Remove foreign key constraint (we may not have all axies in our database)
-- Add unique partial index for upsert logic

-- Drop the foreign key constraint if it exists
DO $$ BEGIN
    ALTER TABLE listings DROP CONSTRAINT IF EXISTS listings_axie_id_fkey;
EXCEPTION WHEN undefined_object THEN NULL; END $$;

-- Remove NOT NULL from axie_id reference requirement (make it a soft reference)
ALTER TABLE listings ALTER COLUMN axie_id DROP NOT NULL;
ALTER TABLE listings ALTER COLUMN axie_id SET NOT NULL;  -- Re-add, just without FK

-- Create unique partial index for active listings by axie_id
-- This enables ON CONFLICT for upsert logic
CREATE UNIQUE INDEX IF NOT EXISTS idx_listings_active_axie
ON listings (axie_id)
WHERE status = 'active';

-- Add index for finding stale listings
CREATE INDEX IF NOT EXISTS idx_listings_updated_status
ON listings (updated_at, status)
WHERE status = 'active';
""",
    "e5f6g7h8i9j0": """
-- Migration: e5f6g7h8i9j0 - Add class column to listings
-- The floor prices query needs class info, and joining with axies table
-- requires axies to be populated. Store class directly in listings instead.

-- Add class column
ALTER TABLE listings ADD COLUMN IF NOT EXISTS class_ VARCHAR(20);

-- Add breed_count column for deal scoring
ALTER TABLE listings ADD COLUMN IF NOT EXISTS breed_count SMALLINT DEFAULT 0;

-- Create index for floor price queries by class
CREATE INDEX IF NOT EXISTS idx_listings_class_status_price
ON listings (class_, status, price_eth)
WHERE status = 'active';
""",
    "f6g7h8i9j0k1": """
-- Migration: f6g7h8i9j0k1 - Drop sales FK constraint
-- Removes the foreign key constraint that requires axie metadata
-- to exist before sales can be inserted. Sales can be inserted independently
-- and linked to metadata later.

-- Drop the FK constraint on sales table
ALTER TABLE sales DROP CONSTRAINT IF EXISTS sales_axie_id_fkey;

-- Add a comment explaining why
COMMENT ON TABLE sales IS 'Axie sales data. FK to axies removed to allow independent ingestion. Metadata linked via axie_id when available.';

-- Create ingestion_metadata table for tracking block progress
CREATE TABLE IF NOT EXISTS ingestion_metadata (
    key             VARCHAR(100) PRIMARY KEY,
    value           TEXT NOT NULL,
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE ingestion_metadata IS 'Tracks ingestion progress for resumable data pipelines';
"""
}

MIGRATION_ORDER = ["43e76aaf7374", "b7e2f3a4c5d6", "c3d4e5f6g7h8", "d4e5f6g7h8i9", "e5f6g7h8i9j0", "f6g7h8i9j0k1"]


def get_current_revision(conn) -> str:
    """Get current database revision."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'alembic_version'
            )
        """)
        if not cur.fetchone()[0]:
            return None

        cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
        row = cur.fetchone()
        return row[0] if row else None


def set_revision(conn, revision: str):
    """Set the current revision in alembic_version."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM alembic_version")
        cur.execute("INSERT INTO alembic_version (version_num) VALUES (%s)", (revision,))
    conn.commit()


def run_migration(conn, revision: str):
    """Run a single migration."""
    logger.info(f"Running migration {revision}")
    sql = MIGRATION_SCRIPTS.get(revision)
    if not sql:
        raise ValueError(f"Unknown migration: {revision}")

    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    logger.info(f"Migration {revision} completed")


@logger.inject_lambda_context
def handler(event, context):
    """Lambda handler for running database migrations."""
    logger.info("Starting database migration")

    action = event.get("action", "upgrade")
    target_revision = event.get("revision", "head")

    conn = None
    try:
        conn = get_db_connection()
        logger.info(f"Connected to database at {os.environ.get('DATABASE_HOST')}")

        current = get_current_revision(conn)
        logger.info(f"Current revision: {current}")

        if action == "current":
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Current revision retrieved",
                    "current_revision": current
                })
            }

        if action == "upgrade":
            if target_revision == "head":
                # Run all migrations after current
                start_idx = 0
                if current:
                    try:
                        start_idx = MIGRATION_ORDER.index(current) + 1
                    except ValueError:
                        start_idx = 0

                migrations_to_run = MIGRATION_ORDER[start_idx:]
            else:
                # Run up to and including target revision
                try:
                    end_idx = MIGRATION_ORDER.index(target_revision) + 1
                except ValueError:
                    return {
                        "statusCode": 400,
                        "body": json.dumps({"error": f"Unknown revision: {target_revision}"})
                    }

                start_idx = 0
                if current:
                    try:
                        start_idx = MIGRATION_ORDER.index(current) + 1
                    except ValueError:
                        start_idx = 0

                migrations_to_run = MIGRATION_ORDER[start_idx:end_idx]

            if not migrations_to_run:
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "message": "Database is already up to date",
                        "current_revision": current
                    })
                }

            for rev in migrations_to_run:
                run_migration(conn, rev)
                set_revision(conn, rev)

            final_revision = migrations_to_run[-1]
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Migration completed successfully",
                    "previous_revision": current,
                    "current_revision": final_revision,
                    "migrations_run": migrations_to_run
                })
            }

        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": f"Unknown action: {action}",
                "valid_actions": ["upgrade", "current"]
            })
        }

    except Exception as e:
        logger.exception(f"Migration error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "action": action
            })
        }
    finally:
        if conn:
            conn.close()
