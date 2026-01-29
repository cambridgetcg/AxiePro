-- AxiePro Database Schema - Core Tables
-- Run this first to create the foundation tables

-- Create schema for axie data
CREATE SCHEMA IF NOT EXISTS axie;
SET search_path TO axie, public;

-- ============================================
-- 1. AXIE PARTS REFERENCE TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS axie_parts (
    part_id         VARCHAR(50) PRIMARY KEY,
    part_name       VARCHAR(100) NOT NULL,
    part_type       VARCHAR(20) NOT NULL,     -- Eyes, Ears, Mouth, Horn, Back, Tail
    part_class      VARCHAR(20) NOT NULL,     -- Beast, Plant, etc.
    energy_cost     SMALLINT,
    damage          SMALLINT,
    shield          SMALLINT,
    effect          TEXT,
    is_meta         BOOLEAN DEFAULT FALSE,
    meta_tier       VARCHAR(10),
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_parts_type ON axie_parts(part_type);
CREATE INDEX IF NOT EXISTS idx_parts_class ON axie_parts(part_class);
CREATE INDEX IF NOT EXISTS idx_parts_meta ON axie_parts(is_meta) WHERE is_meta = TRUE;

-- ============================================
-- 2. AXIE METADATA (Master Dimension Table)
-- ============================================
CREATE TABLE IF NOT EXISTS axie_metadata (
    axie_id         INTEGER PRIMARY KEY,
    name            VARCHAR(100),
    class           VARCHAR(20) NOT NULL,
    breed_count     SMALLINT NOT NULL,

    -- Genetic data
    genes           VARCHAR(64),
    gene_quality    SMALLINT,

    -- Stats
    hp              SMALLINT,
    speed           SMALLINT,
    skill           SMALLINT,
    morale          SMALLINT,

    -- Parts (denormalized for speed)
    parts_json      JSONB,
    part_eyes       VARCHAR(50),
    part_ears       VARCHAR(50),
    part_mouth      VARCHAR(50),
    part_horn       VARCHAR(50),
    part_back       VARCHAR(50),
    part_tail       VARCHAR(50),

    -- Purity
    pure_part_count SMALLINT,

    -- Metadata
    birth_date      TIMESTAMP,
    image_url       TEXT,
    owner           VARCHAR(66),

    first_seen_at   TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_axie_class ON axie_metadata(class);
CREATE INDEX IF NOT EXISTS idx_axie_breed_count ON axie_metadata(breed_count);
CREATE INDEX IF NOT EXISTS idx_axie_class_breed ON axie_metadata(class, breed_count);
CREATE INDEX IF NOT EXISTS idx_axie_parts ON axie_metadata(part_mouth, part_horn, part_back, part_tail);
CREATE INDEX IF NOT EXISTS idx_axie_owner ON axie_metadata(owner);
CREATE INDEX IF NOT EXISTS idx_axie_genes ON axie_metadata(genes);
CREATE INDEX IF NOT EXISTS idx_axie_purity ON axie_metadata(pure_part_count);

-- ============================================
-- 3. AXIE SALES (Partitioned Fact Table)
-- ============================================
CREATE TABLE IF NOT EXISTS axie_sales (
    id              BIGSERIAL,
    tx_hash         VARCHAR(66) NOT NULL,

    -- Axie info (denormalized)
    axie_id         INTEGER NOT NULL,
    class           VARCHAR(20),
    breed_count     SMALLINT,

    -- Price data
    price_raw       NUMERIC(30, 0),
    price_token     NUMERIC(20, 10),
    token_type      VARCHAR(10) NOT NULL,
    price_usd       NUMERIC(12, 2),

    -- Exchange rates at sale time
    eth_usd_rate    NUMERIC(10, 2),
    ron_usd_rate    NUMERIC(10, 6),

    -- Parties
    seller          VARCHAR(66),
    buyer           VARCHAR(66),

    -- Blockchain
    block_number    BIGINT NOT NULL,
    block_timestamp TIMESTAMP NOT NULL,

    created_at      TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (id, block_timestamp)
) PARTITION BY RANGE (block_timestamp);

-- Create partitions for 2024-2025
CREATE TABLE IF NOT EXISTS axie_sales_2024_01 PARTITION OF axie_sales FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE IF NOT EXISTS axie_sales_2024_02 PARTITION OF axie_sales FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
CREATE TABLE IF NOT EXISTS axie_sales_2024_03 PARTITION OF axie_sales FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');
CREATE TABLE IF NOT EXISTS axie_sales_2024_04 PARTITION OF axie_sales FOR VALUES FROM ('2024-04-01') TO ('2024-05-01');
CREATE TABLE IF NOT EXISTS axie_sales_2024_05 PARTITION OF axie_sales FOR VALUES FROM ('2024-05-01') TO ('2024-06-01');
CREATE TABLE IF NOT EXISTS axie_sales_2024_06 PARTITION OF axie_sales FOR VALUES FROM ('2024-06-01') TO ('2024-07-01');
CREATE TABLE IF NOT EXISTS axie_sales_2024_07 PARTITION OF axie_sales FOR VALUES FROM ('2024-07-01') TO ('2024-08-01');
CREATE TABLE IF NOT EXISTS axie_sales_2024_08 PARTITION OF axie_sales FOR VALUES FROM ('2024-08-01') TO ('2024-09-01');
CREATE TABLE IF NOT EXISTS axie_sales_2024_09 PARTITION OF axie_sales FOR VALUES FROM ('2024-09-01') TO ('2024-10-01');
CREATE TABLE IF NOT EXISTS axie_sales_2024_10 PARTITION OF axie_sales FOR VALUES FROM ('2024-10-01') TO ('2024-11-01');
CREATE TABLE IF NOT EXISTS axie_sales_2024_11 PARTITION OF axie_sales FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');
CREATE TABLE IF NOT EXISTS axie_sales_2024_12 PARTITION OF axie_sales FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');
CREATE TABLE IF NOT EXISTS axie_sales_2025_01 PARTITION OF axie_sales FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE IF NOT EXISTS axie_sales_2025_02 PARTITION OF axie_sales FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE IF NOT EXISTS axie_sales_2025_03 PARTITION OF axie_sales FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');
CREATE TABLE IF NOT EXISTS axie_sales_2025_04 PARTITION OF axie_sales FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');
CREATE TABLE IF NOT EXISTS axie_sales_2025_05 PARTITION OF axie_sales FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');
CREATE TABLE IF NOT EXISTS axie_sales_2025_06 PARTITION OF axie_sales FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');
CREATE TABLE IF NOT EXISTS axie_sales_2025_07 PARTITION OF axie_sales FOR VALUES FROM ('2025-07-01') TO ('2025-08-01');
CREATE TABLE IF NOT EXISTS axie_sales_2025_08 PARTITION OF axie_sales FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');
CREATE TABLE IF NOT EXISTS axie_sales_2025_09 PARTITION OF axie_sales FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');
CREATE TABLE IF NOT EXISTS axie_sales_2025_10 PARTITION OF axie_sales FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
CREATE TABLE IF NOT EXISTS axie_sales_2025_11 PARTITION OF axie_sales FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
CREATE TABLE IF NOT EXISTS axie_sales_2025_12 PARTITION OF axie_sales FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');
CREATE TABLE IF NOT EXISTS axie_sales_2026_01 PARTITION OF axie_sales FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE IF NOT EXISTS axie_sales_2026_02 PARTITION OF axie_sales FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE IF NOT EXISTS axie_sales_2026_03 PARTITION OF axie_sales FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE IF NOT EXISTS axie_sales_2026_04 PARTITION OF axie_sales FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE IF NOT EXISTS axie_sales_2026_05 PARTITION OF axie_sales FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE IF NOT EXISTS axie_sales_2026_06 PARTITION OF axie_sales FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
CREATE TABLE IF NOT EXISTS axie_sales_2026_07 PARTITION OF axie_sales FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
CREATE TABLE IF NOT EXISTS axie_sales_2026_08 PARTITION OF axie_sales FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
CREATE TABLE IF NOT EXISTS axie_sales_2026_09 PARTITION OF axie_sales FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');
CREATE TABLE IF NOT EXISTS axie_sales_2026_10 PARTITION OF axie_sales FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');
CREATE TABLE IF NOT EXISTS axie_sales_2026_11 PARTITION OF axie_sales FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE IF NOT EXISTS axie_sales_2026_12 PARTITION OF axie_sales FOR VALUES FROM ('2026-12-01') TO ('2027-01-01');

-- Indexes
CREATE INDEX IF NOT EXISTS idx_sales_axie ON axie_sales(axie_id);
CREATE INDEX IF NOT EXISTS idx_sales_class ON axie_sales(class);
CREATE INDEX IF NOT EXISTS idx_sales_timestamp ON axie_sales(block_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sales_price ON axie_sales(price_usd);
CREATE INDEX IF NOT EXISTS idx_sales_seller ON axie_sales(seller);
CREATE INDEX IF NOT EXISTS idx_sales_buyer ON axie_sales(buyer);
CREATE UNIQUE INDEX IF NOT EXISTS idx_sales_unique ON axie_sales(tx_hash, axie_id);

-- ============================================
-- 4. MARKET SNAPSHOTS (Hourly Aggregates)
-- ============================================
CREATE TABLE IF NOT EXISTS market_snapshots (
    id              BIGSERIAL PRIMARY KEY,
    snapshot_at     TIMESTAMP NOT NULL,
    period_type     VARCHAR(10) DEFAULT 'hourly',

    -- Overall market
    total_listed    INTEGER,
    total_volume_usd NUMERIC(14, 2),
    total_sales     INTEGER,
    avg_price_usd   NUMERIC(12, 2),
    median_price_usd NUMERIC(12, 2),
    floor_price_usd NUMERIC(12, 2),

    -- Exchange rates
    eth_usd         NUMERIC(10, 2),
    ron_usd         NUMERIC(10, 6),
    axs_usd         NUMERIC(10, 4),
    slp_usd         NUMERIC(10, 6),

    UNIQUE(snapshot_at, period_type)
);

CREATE INDEX IF NOT EXISTS idx_market_snap_time ON market_snapshots(snapshot_at DESC);

-- ============================================
-- 5. CLASS METRICS (Per-Class Stats)
-- ============================================
CREATE TABLE IF NOT EXISTS class_metrics (
    id              BIGSERIAL PRIMARY KEY,
    snapshot_at     TIMESTAMP NOT NULL,
    class           VARCHAR(20) NOT NULL,

    -- Listings
    total_listed    INTEGER,
    floor_price_usd NUMERIC(12, 2),
    avg_price_usd   NUMERIC(12, 2),

    -- Sales
    sales_count     INTEGER,
    volume_usd      NUMERIC(14, 2),
    avg_sale_usd    NUMERIC(12, 2),

    -- Trends
    floor_change_pct NUMERIC(8, 4),
    volume_change_pct NUMERIC(8, 4),

    UNIQUE(snapshot_at, class)
);

CREATE INDEX IF NOT EXISTS idx_class_metrics_time ON class_metrics(snapshot_at DESC);
CREATE INDEX IF NOT EXISTS idx_class_metrics_class ON class_metrics(class, snapshot_at DESC);

-- ============================================
-- 6. BREED COUNT METRICS
-- ============================================
CREATE TABLE IF NOT EXISTS breed_count_metrics (
    id              BIGSERIAL PRIMARY KEY,
    snapshot_at     TIMESTAMP NOT NULL,
    breed_count     SMALLINT NOT NULL,

    total_listed    INTEGER,
    floor_price_usd NUMERIC(12, 2),
    avg_price_usd   NUMERIC(12, 2),
    virgin_premium_pct NUMERIC(8, 4),

    UNIQUE(snapshot_at, breed_count)
);

CREATE INDEX IF NOT EXISTS idx_breed_metrics_time ON breed_count_metrics(snapshot_at DESC);

-- ============================================
-- 7. EXCHANGE RATES HISTORY
-- ============================================
CREATE TABLE IF NOT EXISTS exchange_rates (
    id              BIGSERIAL PRIMARY KEY,
    recorded_at     TIMESTAMP NOT NULL,
    eth_usd         NUMERIC(10, 2),
    ron_usd         NUMERIC(10, 6),
    axs_usd         NUMERIC(10, 4),
    slp_usd         NUMERIC(10, 6)
);

CREATE INDEX IF NOT EXISTS idx_exchange_time ON exchange_rates(recorded_at DESC);

COMMENT ON TABLE axie_sales IS 'Historical sales data partitioned by month';
COMMENT ON TABLE axie_metadata IS 'Axie attributes, stats, and parts (dimension table)';
COMMENT ON TABLE market_snapshots IS 'Hourly market-wide metrics';
COMMENT ON TABLE class_metrics IS 'Per-class metrics updated hourly';

SELECT 'Core tables created successfully' as status;
