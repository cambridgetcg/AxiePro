-- AxiePro Database Schema - Analysis Tables
-- Run after 01_create_core_tables.sql

SET search_path TO axie, public;

-- ============================================
-- 8. CURRENT LISTINGS SNAPSHOT
-- ============================================
CREATE TABLE IF NOT EXISTS axie_listings (
    axie_id         INTEGER PRIMARY KEY,

    -- Axie info
    class           VARCHAR(20),
    breed_count     SMALLINT,
    pure_part_count SMALLINT,

    -- Listing info
    price_usd       NUMERIC(12, 2),
    price_eth       NUMERIC(20, 10),
    seller          VARCHAR(66),
    listed_at       TIMESTAMP,

    -- Arbitrage detection
    last_sale_price NUMERIC(12, 2),
    price_vs_floor  NUMERIC(8, 4),
    price_vs_last   NUMERIC(8, 4),

    snapshot_at     TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_listings_class ON axie_listings(class);
CREATE INDEX IF NOT EXISTS idx_listings_price ON axie_listings(price_usd);
CREATE INDEX IF NOT EXISTS idx_listings_breed ON axie_listings(breed_count);
CREATE INDEX IF NOT EXISTS idx_listings_undervalued ON axie_listings(price_vs_last) WHERE price_vs_last < 0.9;

-- ============================================
-- 9. LISTING HISTORY (Track Changes)
-- ============================================
CREATE TABLE IF NOT EXISTS listing_history (
    id              BIGSERIAL PRIMARY KEY,
    axie_id         INTEGER NOT NULL,
    price_usd       NUMERIC(12, 2),
    price_eth       NUMERIC(20, 10),
    seller          VARCHAR(66),
    snapshot_at     TIMESTAMP NOT NULL,
    is_active       BOOLEAN DEFAULT TRUE,
    sold_at         TIMESTAMP,
    delisted_at     TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_listing_hist_axie ON listing_history(axie_id, snapshot_at DESC);
CREATE INDEX IF NOT EXISTS idx_listing_hist_time ON listing_history(snapshot_at DESC);

-- ============================================
-- 10. PARTS PRICING (Meta Tracking)
-- ============================================
CREATE TABLE IF NOT EXISTS parts_pricing (
    id              BIGSERIAL PRIMARY KEY,
    snapshot_at     TIMESTAMP NOT NULL,
    part_id         VARCHAR(50) NOT NULL,
    part_type       VARCHAR(20),
    part_class      VARCHAR(20),

    axies_listed    INTEGER,
    floor_price_usd NUMERIC(12, 2),
    avg_price_usd   NUMERIC(12, 2),
    sales_24h       INTEGER,
    volume_24h_usd  NUMERIC(14, 2),

    floor_change_24h NUMERIC(8, 4),
    volume_change_24h NUMERIC(8, 4),

    UNIQUE(snapshot_at, part_id)
);

CREATE INDEX IF NOT EXISTS idx_parts_pricing_time ON parts_pricing(snapshot_at DESC);
CREATE INDEX IF NOT EXISTS idx_parts_pricing_part ON parts_pricing(part_id, snapshot_at DESC);
CREATE INDEX IF NOT EXISTS idx_parts_pricing_trending ON parts_pricing(volume_change_24h DESC) WHERE volume_change_24h > 0.1;

-- ============================================
-- 11. PRICE ALERTS
-- ============================================
CREATE TABLE IF NOT EXISTS price_alerts (
    id              BIGSERIAL PRIMARY KEY,
    alert_type      VARCHAR(50) NOT NULL,
    severity        VARCHAR(10) DEFAULT 'info',

    axie_id         INTEGER,
    class           VARCHAR(20),
    part_id         VARCHAR(50),

    message         TEXT,
    current_value   NUMERIC(14, 2),
    threshold_value NUMERIC(14, 2),
    deviation_pct   NUMERIC(8, 4),

    created_at      TIMESTAMP DEFAULT NOW(),
    acknowledged_at TIMESTAMP,
    acted_on        BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_alerts_type ON price_alerts(alert_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_unacked ON price_alerts(created_at DESC) WHERE acknowledged_at IS NULL;

-- ============================================
-- 12. WALLET TRACKING
-- ============================================
CREATE TABLE IF NOT EXISTS tracked_wallets (
    wallet          VARCHAR(66) PRIMARY KEY,
    label           VARCHAR(100),
    notes           TEXT,
    track_since     TIMESTAMP DEFAULT NOW(),
    is_active       BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS wallet_activity (
    id              BIGSERIAL PRIMARY KEY,
    wallet          VARCHAR(66) NOT NULL,
    activity_type   VARCHAR(20) NOT NULL,

    axie_id         INTEGER,
    price_usd       NUMERIC(12, 2),

    block_timestamp TIMESTAMP NOT NULL,
    tx_hash         VARCHAR(66),

    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wallet_activity_wallet ON wallet_activity(wallet, block_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_wallet_activity_time ON wallet_activity(block_timestamp DESC);

-- ============================================
-- 13. BREEDING RECORDS
-- ============================================
CREATE TABLE IF NOT EXISTS breeding_records (
    id              BIGSERIAL PRIMARY KEY,

    parent1_id      INTEGER NOT NULL,
    parent2_id      INTEGER NOT NULL,
    parent1_class   VARCHAR(20),
    parent2_class   VARCHAR(20),

    offspring_id    INTEGER NOT NULL,
    offspring_class VARCHAR(20),

    slp_cost        INTEGER,
    axs_cost        NUMERIC(10, 4),
    total_cost_usd  NUMERIC(12, 2),

    offspring_value_usd NUMERIC(12, 2),
    roi_pct         NUMERIC(8, 4),

    bred_at         TIMESTAMP,
    sold_at         TIMESTAMP,
    genes_as_expected BOOLEAN,

    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_breeding_parents ON breeding_records(parent1_id, parent2_id);
CREATE INDEX IF NOT EXISTS idx_breeding_offspring ON breeding_records(offspring_id);
CREATE INDEX IF NOT EXISTS idx_breeding_time ON breeding_records(bred_at DESC);

-- ============================================
-- 14. PROCESSING STATE (Track sync progress)
-- ============================================
CREATE TABLE IF NOT EXISTS sync_state (
    id              VARCHAR(50) PRIMARY KEY,
    last_block      BIGINT,
    last_timestamp  TIMESTAMP,
    records_synced  BIGINT DEFAULT 0,
    updated_at      TIMESTAMP DEFAULT NOW()
);

INSERT INTO sync_state (id, last_block, last_timestamp)
VALUES ('axie_sales', 0, '2024-01-01'::timestamp)
ON CONFLICT (id) DO NOTHING;

COMMENT ON TABLE axie_listings IS 'Current marketplace listings (refreshed every 5 min)';
COMMENT ON TABLE parts_pricing IS 'Part-level pricing for meta analysis';
COMMENT ON TABLE price_alerts IS 'Automated trading alerts';
COMMENT ON TABLE breeding_records IS 'Breeding outcomes for ROI analysis';

SELECT 'Analysis tables created successfully' as status;
