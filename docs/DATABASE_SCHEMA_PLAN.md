# AxiePro Database Schema Plan

## Design Philosophy

### Goals
1. **Fast trend analysis** - Pre-aggregated metrics for instant dashboard queries
2. **Arbitrage detection** - Compare listings vs recent sales in real-time
3. **Historical analysis** - Time-series data for backtesting strategies
4. **Breeding insights** - Track gene inheritance and ROI
5. **Meta tracking** - Identify which parts/builds are gaining value

### Data Flow Architecture
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Sky Mavis RPC  │     │ Sky Mavis GQL   │     │    Goldrush     │
│  (Sales Events) │     │ (Listings/Meta) │     │ (Wallet Data)   │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      RAW DATA TABLES                            │
│  axie_sales_raw │ axie_listings_raw │ axie_metadata │ wallets   │
└────────┬────────────────┬───────────────────┬───────────────────┘
         │                │                   │
         ▼                ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                   DERIVED/AGGREGATED TABLES                     │
│  market_snapshots │ parts_pricing │ class_metrics │ breeding    │
└────────┬────────────────┬───────────────────┬───────────────────┘
         │                │                   │
         ▼                ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MATERIALIZED VIEWS                           │
│  daily_volume │ floor_history │ undervalued_listings │ alerts   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Tables

### 1. `axie_metadata` - Axie Master Data (Dimension Table)
Stores static/semi-static Axie attributes. Updated on first sale or periodically refreshed.

```sql
CREATE TABLE axie_metadata (
    axie_id         INTEGER PRIMARY KEY,
    name            VARCHAR(100),
    class           VARCHAR(20) NOT NULL,  -- Beast, Plant, Aquatic, Bird, Bug, Reptile, Mech, Dawn, Dusk
    breed_count     SMALLINT NOT NULL,     -- 0-7

    -- Genetic data (critical for breeding)
    genes           VARCHAR(64),           -- 256-bit hex string
    gene_quality    SMALLINT,              -- Calculated purity score 0-100

    -- Stats (for battle value assessment)
    hp              SMALLINT,
    speed           SMALLINT,
    skill           SMALLINT,
    morale          SMALLINT,
    stat_total      SMALLINT GENERATED ALWAYS AS (hp + speed + skill + morale) STORED,

    -- Parts (denormalized for query speed, also in parts table)
    parts_json      JSONB,                 -- Full parts data for flexibility

    -- Part IDs for efficient filtering (indexed)
    part_eyes       VARCHAR(50),
    part_ears       VARCHAR(50),
    part_mouth      VARCHAR(50),
    part_horn       VARCHAR(50),
    part_back       VARCHAR(50),
    part_tail       VARCHAR(50),

    -- Purity metrics
    pure_part_count SMALLINT,              -- Count of parts matching class (0-6)
    is_pure         BOOLEAN GENERATED ALWAYS AS (pure_part_count = 6) STORED,

    -- Metadata
    birth_date      TIMESTAMP,
    image_url       TEXT,
    owner           VARCHAR(66),           -- Current owner (updated on sale)

    -- Timestamps
    first_seen_at   TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX idx_axie_class ON axie_metadata(class);
CREATE INDEX idx_axie_breed_count ON axie_metadata(breed_count);
CREATE INDEX idx_axie_class_breed ON axie_metadata(class, breed_count);
CREATE INDEX idx_axie_pure ON axie_metadata(is_pure) WHERE is_pure = TRUE;
CREATE INDEX idx_axie_parts ON axie_metadata(part_mouth, part_horn, part_back, part_tail);
CREATE INDEX idx_axie_owner ON axie_metadata(owner);
CREATE INDEX idx_axie_genes ON axie_metadata(genes);
```

### 2. `axie_parts` - Normalized Parts Reference
For efficient part-based queries and meta analysis.

```sql
CREATE TABLE axie_parts (
    part_id         VARCHAR(50) PRIMARY KEY,  -- e.g., "mouth-nut-cracker"
    part_name       VARCHAR(100) NOT NULL,    -- e.g., "Nut Cracker"
    part_type       VARCHAR(20) NOT NULL,     -- Eyes, Ears, Mouth, Horn, Back, Tail
    part_class      VARCHAR(20) NOT NULL,     -- Beast, Plant, etc.

    -- Game mechanics (if available)
    energy_cost     SMALLINT,
    damage          SMALLINT,
    shield          SMALLINT,
    effect          TEXT,

    -- Meta tracking
    is_meta         BOOLEAN DEFAULT FALSE,    -- Manually flagged meta parts
    meta_tier       VARCHAR(10),              -- S, A, B, C tier

    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_parts_type ON axie_parts(part_type);
CREATE INDEX idx_parts_class ON axie_parts(part_class);
CREATE INDEX idx_parts_meta ON axie_parts(is_meta) WHERE is_meta = TRUE;
```

### 3. `axie_part_mapping` - Many-to-Many Axie-Parts
For complex part combination queries.

```sql
CREATE TABLE axie_part_mapping (
    axie_id         INTEGER REFERENCES axie_metadata(axie_id),
    part_id         VARCHAR(50) REFERENCES axie_parts(part_id),
    slot            VARCHAR(20) NOT NULL,     -- eyes, ears, mouth, horn, back, tail
    is_dominant     BOOLEAN DEFAULT TRUE,     -- D, R1, R2 genes
    PRIMARY KEY (axie_id, part_id, slot, is_dominant)
);

CREATE INDEX idx_part_mapping_part ON axie_part_mapping(part_id);
```

---

## Transaction Tables

### 4. `axie_sales` - Sales History (Fact Table)
Append-only, partitioned by month for efficient time-range queries.

```sql
CREATE TABLE axie_sales (
    id              BIGSERIAL,
    tx_hash         VARCHAR(66) NOT NULL,

    -- Axie info (denormalized for query speed)
    axie_id         INTEGER NOT NULL,
    class           VARCHAR(20),
    breed_count     SMALLINT,

    -- Price data
    price_raw       NUMERIC(30, 0),           -- Raw wei/token units
    price_token     NUMERIC(20, 10),          -- Human readable token amount
    token_type      VARCHAR(10) NOT NULL,     -- WETH, WRON, etc.
    price_usd       NUMERIC(12, 2),           -- USD at time of sale

    -- Exchange rate at sale time (for historical accuracy)
    eth_usd_rate    NUMERIC(10, 2),
    ron_usd_rate    NUMERIC(10, 6),

    -- Parties
    seller          VARCHAR(66),
    buyer           VARCHAR(66),

    -- Blockchain data
    block_number    BIGINT NOT NULL,
    block_timestamp TIMESTAMP NOT NULL,

    -- Processing metadata
    created_at      TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (id, block_timestamp)
) PARTITION BY RANGE (block_timestamp);

-- Create monthly partitions (extend as needed)
CREATE TABLE axie_sales_2025_01 PARTITION OF axie_sales
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE axie_sales_2025_02 PARTITION OF axie_sales
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
-- ... continue for each month

-- Indexes on parent table (inherited by partitions)
CREATE INDEX idx_sales_axie ON axie_sales(axie_id);
CREATE INDEX idx_sales_class ON axie_sales(class);
CREATE INDEX idx_sales_timestamp ON axie_sales(block_timestamp DESC);
CREATE INDEX idx_sales_price ON axie_sales(price_usd);
CREATE INDEX idx_sales_seller ON axie_sales(seller);
CREATE INDEX idx_sales_buyer ON axie_sales(buyer);
CREATE INDEX idx_sales_tx ON axie_sales(tx_hash);

-- Unique constraint to prevent duplicates
CREATE UNIQUE INDEX idx_sales_unique ON axie_sales(tx_hash, axie_id);
```

### 5. `axie_listings` - Current Marketplace State
Point-in-time snapshot of active listings. Truncated and reloaded periodically.

```sql
CREATE TABLE axie_listings (
    axie_id         INTEGER PRIMARY KEY,

    -- Axie info (denormalized)
    class           VARCHAR(20),
    breed_count     SMALLINT,
    pure_part_count SMALLINT,

    -- Listing info
    price_usd       NUMERIC(12, 2),
    price_eth       NUMERIC(20, 10),
    seller          VARCHAR(66),
    listed_at       TIMESTAMP,

    -- For arbitrage detection
    last_sale_price NUMERIC(12, 2),          -- Most recent sale price
    price_vs_floor  NUMERIC(8, 4),           -- Ratio to class floor
    price_vs_last   NUMERIC(8, 4),           -- Ratio to last sale

    -- Snapshot metadata
    snapshot_at     TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_listings_class ON axie_listings(class);
CREATE INDEX idx_listings_price ON axie_listings(price_usd);
CREATE INDEX idx_listings_breed ON axie_listings(breed_count);
CREATE INDEX idx_listings_undervalued ON axie_listings(price_vs_last) WHERE price_vs_last < 0.9;
```

### 6. `listing_history` - Historical Listing Snapshots
For tracking how long items stay listed, price changes over time.

```sql
CREATE TABLE listing_history (
    id              BIGSERIAL PRIMARY KEY,
    axie_id         INTEGER NOT NULL,
    price_usd       NUMERIC(12, 2),
    price_eth       NUMERIC(20, 10),
    seller          VARCHAR(66),
    snapshot_at     TIMESTAMP NOT NULL,

    -- Status
    is_active       BOOLEAN DEFAULT TRUE,
    sold_at         TIMESTAMP,
    delisted_at     TIMESTAMP
);

CREATE INDEX idx_listing_hist_axie ON listing_history(axie_id, snapshot_at DESC);
CREATE INDEX idx_listing_hist_time ON listing_history(snapshot_at DESC);
```

---

## Aggregated Tables (Pre-computed for Speed)

### 7. `market_snapshots` - Hourly Market Metrics
Pre-aggregated metrics updated every hour for instant dashboard queries.

```sql
CREATE TABLE market_snapshots (
    id              BIGSERIAL PRIMARY KEY,
    snapshot_at     TIMESTAMP NOT NULL,
    period_type     VARCHAR(10) DEFAULT 'hourly',  -- hourly, daily, weekly

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

CREATE INDEX idx_market_snap_time ON market_snapshots(snapshot_at DESC);
```

### 8. `class_metrics` - Per-Class Statistics
Hourly metrics broken down by class.

```sql
CREATE TABLE class_metrics (
    id              BIGSERIAL PRIMARY KEY,
    snapshot_at     TIMESTAMP NOT NULL,
    class           VARCHAR(20) NOT NULL,

    -- Listings
    total_listed    INTEGER,
    floor_price_usd NUMERIC(12, 2),
    avg_price_usd   NUMERIC(12, 2),

    -- Sales (last period)
    sales_count     INTEGER,
    volume_usd      NUMERIC(14, 2),
    avg_sale_usd    NUMERIC(12, 2),

    -- Trend indicators
    floor_change_pct NUMERIC(8, 4),          -- vs previous period
    volume_change_pct NUMERIC(8, 4),

    UNIQUE(snapshot_at, class)
);

CREATE INDEX idx_class_metrics_time ON class_metrics(snapshot_at DESC);
CREATE INDEX idx_class_metrics_class ON class_metrics(class, snapshot_at DESC);
```

### 9. `breed_count_metrics` - Per-Breed-Count Statistics
Critical for breeding ROI analysis.

```sql
CREATE TABLE breed_count_metrics (
    id              BIGSERIAL PRIMARY KEY,
    snapshot_at     TIMESTAMP NOT NULL,
    breed_count     SMALLINT NOT NULL,

    -- Listings
    total_listed    INTEGER,
    floor_price_usd NUMERIC(12, 2),
    avg_price_usd   NUMERIC(12, 2),

    -- Premium calculation (vs breed_count + 1)
    virgin_premium_pct NUMERIC(8, 4),        -- 0-breed vs 1-breed

    UNIQUE(snapshot_at, breed_count)
);

CREATE INDEX idx_breed_metrics_time ON breed_count_metrics(snapshot_at DESC);
```

### 10. `parts_pricing` - Part Value Tracking
Track which parts command premium prices - essential for meta analysis.

```sql
CREATE TABLE parts_pricing (
    id              BIGSERIAL PRIMARY KEY,
    snapshot_at     TIMESTAMP NOT NULL,
    part_id         VARCHAR(50) NOT NULL,
    part_type       VARCHAR(20),
    part_class      VARCHAR(20),

    -- Metrics
    axies_listed    INTEGER,
    floor_price_usd NUMERIC(12, 2),
    avg_price_usd   NUMERIC(12, 2),
    sales_24h       INTEGER,
    volume_24h_usd  NUMERIC(14, 2),

    -- Trend
    floor_change_24h NUMERIC(8, 4),
    volume_change_24h NUMERIC(8, 4),

    UNIQUE(snapshot_at, part_id)
);

CREATE INDEX idx_parts_pricing_time ON parts_pricing(snapshot_at DESC);
CREATE INDEX idx_parts_pricing_part ON parts_pricing(part_id, snapshot_at DESC);
CREATE INDEX idx_parts_pricing_trending ON parts_pricing(volume_change_24h DESC)
    WHERE volume_change_24h > 0.1;
```

---

## Analytics Tables

### 11. `price_alerts` - Automated Alerts
Store triggered alerts for undervalued listings, volume spikes, etc.

```sql
CREATE TABLE price_alerts (
    id              BIGSERIAL PRIMARY KEY,
    alert_type      VARCHAR(50) NOT NULL,    -- undervalued, volume_spike, floor_drop, whale_buy
    severity        VARCHAR(10) DEFAULT 'info',  -- info, warning, critical

    -- Context
    axie_id         INTEGER,
    class           VARCHAR(20),
    part_id         VARCHAR(50),

    -- Alert details
    message         TEXT,
    current_value   NUMERIC(14, 2),
    threshold_value NUMERIC(14, 2),
    deviation_pct   NUMERIC(8, 4),

    -- Status
    created_at      TIMESTAMP DEFAULT NOW(),
    acknowledged_at TIMESTAMP,
    acted_on        BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_alerts_type ON price_alerts(alert_type, created_at DESC);
CREATE INDEX idx_alerts_unacked ON price_alerts(created_at DESC) WHERE acknowledged_at IS NULL;
```

### 12. `wallet_activity` - Whale Tracking
Monitor large holders and notable traders.

```sql
CREATE TABLE wallet_activity (
    id              BIGSERIAL PRIMARY KEY,
    wallet          VARCHAR(66) NOT NULL,
    activity_type   VARCHAR(20) NOT NULL,    -- buy, sell, breed, transfer

    axie_id         INTEGER,
    price_usd       NUMERIC(12, 2),

    block_timestamp TIMESTAMP NOT NULL,
    tx_hash         VARCHAR(66),

    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_wallet_activity_wallet ON wallet_activity(wallet, block_timestamp DESC);
CREATE INDEX idx_wallet_activity_time ON wallet_activity(block_timestamp DESC);

-- Tracked wallets (manually curated)
CREATE TABLE tracked_wallets (
    wallet          VARCHAR(66) PRIMARY KEY,
    label           VARCHAR(100),            -- "Top Breeder", "Market Maker", etc.
    notes           TEXT,
    track_since     TIMESTAMP DEFAULT NOW(),
    is_active       BOOLEAN DEFAULT TRUE
);
```

### 13. `breeding_records` - Breeding Analytics
Track breeding outcomes for ROI analysis.

```sql
CREATE TABLE breeding_records (
    id              BIGSERIAL PRIMARY KEY,

    -- Parents
    parent1_id      INTEGER NOT NULL,
    parent2_id      INTEGER NOT NULL,
    parent1_class   VARCHAR(20),
    parent2_class   VARCHAR(20),

    -- Offspring
    offspring_id    INTEGER NOT NULL,
    offspring_class VARCHAR(20),

    -- Costs
    slp_cost        INTEGER,
    axs_cost        NUMERIC(10, 4),
    total_cost_usd  NUMERIC(12, 2),

    -- Value
    offspring_value_usd NUMERIC(12, 2),      -- First sale or estimated
    roi_pct         NUMERIC(8, 4),

    -- Timing
    bred_at         TIMESTAMP,
    sold_at         TIMESTAMP,

    -- Gene analysis
    genes_as_expected BOOLEAN,               -- Did genes inherit as predicted?

    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_breeding_parents ON breeding_records(parent1_id, parent2_id);
CREATE INDEX idx_breeding_offspring ON breeding_records(offspring_id);
CREATE INDEX idx_breeding_time ON breeding_records(bred_at DESC);
```

---

## Materialized Views (Auto-refreshed)

### Floor Price History (for charting)
```sql
CREATE MATERIALIZED VIEW mv_floor_history AS
SELECT
    date_trunc('hour', snapshot_at) as hour,
    class,
    MIN(floor_price_usd) as floor_usd,
    AVG(total_listed) as avg_listed
FROM class_metrics
GROUP BY 1, 2
ORDER BY 1 DESC, 2;

CREATE UNIQUE INDEX idx_mv_floor_history ON mv_floor_history(hour, class);

-- Refresh every 15 minutes
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_floor_history;
```

### Undervalued Listings (for arbitrage)
```sql
CREATE MATERIALIZED VIEW mv_undervalued AS
SELECT
    l.axie_id,
    l.class,
    l.breed_count,
    l.price_usd as listing_price,
    l.last_sale_price,
    l.price_vs_last,
    m.parts_json,
    m.pure_part_count
FROM axie_listings l
JOIN axie_metadata m ON l.axie_id = m.axie_id
WHERE l.price_vs_last < 0.85  -- 15%+ below last sale
   OR l.price_vs_floor < 0.95  -- Near floor with good parts
ORDER BY l.price_vs_last ASC
LIMIT 100;

CREATE UNIQUE INDEX idx_mv_undervalued ON mv_undervalued(axie_id);

-- Refresh every 5 minutes
```

### Daily Volume Summary
```sql
CREATE MATERIALIZED VIEW mv_daily_volume AS
SELECT
    date_trunc('day', block_timestamp) as day,
    class,
    COUNT(*) as sales,
    SUM(price_usd) as volume_usd,
    AVG(price_usd) as avg_price,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_usd) as median_price,
    MIN(price_usd) as min_price,
    MAX(price_usd) as max_price
FROM axie_sales
WHERE block_timestamp > NOW() - INTERVAL '90 days'
GROUP BY 1, 2
ORDER BY 1 DESC, 2;

CREATE UNIQUE INDEX idx_mv_daily_volume ON mv_daily_volume(day, class);
```

### Hot Parts (trending meta)
```sql
CREATE MATERIALIZED VIEW mv_hot_parts AS
SELECT
    p.part_id,
    p.part_name,
    p.part_type,
    p.part_class,
    pp.floor_price_usd,
    pp.volume_24h_usd,
    pp.volume_change_24h,
    pp.floor_change_24h
FROM parts_pricing pp
JOIN axie_parts p ON pp.part_id = p.part_id
WHERE pp.snapshot_at = (SELECT MAX(snapshot_at) FROM parts_pricing)
  AND pp.volume_change_24h > 0.2  -- 20%+ volume increase
ORDER BY pp.volume_change_24h DESC
LIMIT 50;

CREATE UNIQUE INDEX idx_mv_hot_parts ON mv_hot_parts(part_id);
```

---

## Utility Functions

### Get Floor Price by Class
```sql
CREATE OR REPLACE FUNCTION get_floor_price(p_class VARCHAR)
RETURNS NUMERIC AS $$
    SELECT floor_price_usd
    FROM class_metrics
    WHERE class = p_class
    ORDER BY snapshot_at DESC
    LIMIT 1;
$$ LANGUAGE SQL STABLE;
```

### Calculate Axie Value Estimate
```sql
CREATE OR REPLACE FUNCTION estimate_axie_value(p_axie_id INTEGER)
RETURNS NUMERIC AS $$
DECLARE
    v_class VARCHAR;
    v_breed_count SMALLINT;
    v_pure_count SMALLINT;
    v_base_price NUMERIC;
    v_breed_mult NUMERIC;
    v_pure_mult NUMERIC;
BEGIN
    SELECT class, breed_count, pure_part_count
    INTO v_class, v_breed_count, v_pure_count
    FROM axie_metadata WHERE axie_id = p_axie_id;

    -- Get class floor
    v_base_price := get_floor_price(v_class);

    -- Breed count multiplier (virgin premium)
    v_breed_mult := CASE v_breed_count
        WHEN 0 THEN 1.5
        WHEN 1 THEN 1.2
        WHEN 2 THEN 1.1
        ELSE 1.0
    END;

    -- Purity multiplier
    v_pure_mult := 1.0 + (v_pure_count * 0.1);

    RETURN v_base_price * v_breed_mult * v_pure_mult;
END;
$$ LANGUAGE plpgsql STABLE;
```

### Recent Sales for Axie
```sql
CREATE OR REPLACE FUNCTION get_axie_sales(p_axie_id INTEGER, p_limit INTEGER DEFAULT 10)
RETURNS TABLE (
    sale_date TIMESTAMP,
    price_usd NUMERIC,
    buyer VARCHAR,
    seller VARCHAR
) AS $$
    SELECT block_timestamp, price_usd, buyer, seller
    FROM axie_sales
    WHERE axie_id = p_axie_id
    ORDER BY block_timestamp DESC
    LIMIT p_limit;
$$ LANGUAGE SQL STABLE;
```

---

## Data Refresh Schedule

| Table/View | Refresh Frequency | Method |
|------------|-------------------|--------|
| `axie_sales` | Real-time | RPC event listener |
| `axie_listings` | Every 5 min | GraphQL full refresh |
| `axie_metadata` | On first sale / daily | GraphQL on-demand |
| `market_snapshots` | Hourly | Aggregation job |
| `class_metrics` | Hourly | Aggregation job |
| `breed_count_metrics` | Hourly | Aggregation job |
| `parts_pricing` | Every 6 hours | Aggregation job |
| `mv_undervalued` | Every 5 min | REFRESH CONCURRENTLY |
| `mv_floor_history` | Every 15 min | REFRESH CONCURRENTLY |
| `mv_daily_volume` | Every hour | REFRESH CONCURRENTLY |
| `mv_hot_parts` | Every hour | REFRESH CONCURRENTLY |

---

## Sample Queries for Trading

### Find Undervalued Listings
```sql
SELECT
    l.axie_id,
    l.class,
    l.price_usd as listing_price,
    l.last_sale_price,
    ROUND((1 - l.price_vs_last) * 100, 1) as discount_pct,
    m.breed_count,
    m.pure_part_count
FROM axie_listings l
JOIN axie_metadata m ON l.axie_id = m.axie_id
WHERE l.price_vs_last < 0.85
  AND m.breed_count <= 2
ORDER BY discount_pct DESC
LIMIT 20;
```

### Track Floor Price Trend
```sql
SELECT
    date_trunc('day', snapshot_at) as day,
    class,
    AVG(floor_price_usd) as avg_floor,
    LAG(AVG(floor_price_usd)) OVER (PARTITION BY class ORDER BY date_trunc('day', snapshot_at)) as prev_floor,
    ROUND((AVG(floor_price_usd) / LAG(AVG(floor_price_usd)) OVER (PARTITION BY class ORDER BY date_trunc('day', snapshot_at)) - 1) * 100, 2) as change_pct
FROM class_metrics
WHERE snapshot_at > NOW() - INTERVAL '30 days'
GROUP BY 1, 2
ORDER BY 1 DESC, 2;
```

### Identify Hot Parts (Meta Shift)
```sql
SELECT
    part_name,
    part_type,
    floor_price_usd,
    volume_24h_usd,
    ROUND(volume_change_24h * 100, 1) as volume_change_pct,
    ROUND(floor_change_24h * 100, 1) as floor_change_pct
FROM mv_hot_parts
WHERE volume_change_24h > 0.3
ORDER BY volume_change_24h DESC;
```

### Virgin Premium Analysis
```sql
SELECT
    class,
    MAX(CASE WHEN breed_count = 0 THEN floor_price_usd END) as virgin_floor,
    MAX(CASE WHEN breed_count = 1 THEN floor_price_usd END) as breed1_floor,
    ROUND((MAX(CASE WHEN breed_count = 0 THEN floor_price_usd END) /
           MAX(CASE WHEN breed_count = 1 THEN floor_price_usd END) - 1) * 100, 1) as premium_pct
FROM class_metrics
WHERE snapshot_at = (SELECT MAX(snapshot_at) FROM class_metrics)
GROUP BY class
ORDER BY premium_pct DESC;
```

### Whale Activity
```sql
SELECT
    wallet,
    tw.label,
    COUNT(*) as txns_24h,
    SUM(CASE WHEN activity_type = 'buy' THEN price_usd ELSE 0 END) as bought_usd,
    SUM(CASE WHEN activity_type = 'sell' THEN price_usd ELSE 0 END) as sold_usd
FROM wallet_activity wa
JOIN tracked_wallets tw USING (wallet)
WHERE block_timestamp > NOW() - INTERVAL '24 hours'
GROUP BY wallet, tw.label
HAVING COUNT(*) > 5
ORDER BY bought_usd DESC;
```

---

## Storage Estimates

| Table | Rows/Month | Row Size | Monthly Growth |
|-------|------------|----------|----------------|
| axie_sales | ~200,000 | ~300 bytes | ~60 MB |
| axie_metadata | ~500,000 total | ~500 bytes | ~250 MB total |
| axie_listings | ~150,000 snapshots | ~200 bytes | ~30 MB |
| market_snapshots | 720 | ~200 bytes | ~0.15 MB |
| class_metrics | 6,480 | ~150 bytes | ~1 MB |
| parts_pricing | ~50,000 | ~150 bytes | ~7.5 MB |

**Estimated Total: ~100 MB/month for active tables**

---

## Implementation Priority

### Phase 1: Core (Week 1)
1. `axie_sales` - Start collecting sales immediately
2. `axie_metadata` - Populate on first sale
3. `market_snapshots` - Basic metrics

### Phase 2: Analysis (Week 2)
4. `class_metrics` - Per-class breakdown
5. `breed_count_metrics` - Breeding analysis
6. `axie_listings` - Snapshot current market

### Phase 3: Advanced (Week 3+)
7. `parts_pricing` - Meta tracking
8. `price_alerts` - Automated notifications
9. `mv_undervalued` - Arbitrage detection
10. `breeding_records` - ROI tracking
