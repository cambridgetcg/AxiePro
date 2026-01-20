# AxiePro Database Schema

## Design Philosophy

### Goals
1. **Fast trend analysis** - Pre-aggregated metrics for instant dashboard queries
2. **Arbitrage detection** - Compare listings vs recent sales in real-time
3. **Historical analysis** - Time-series data for backtesting strategies
4. **Breeding insights** - Track gene inheritance and ROI
5. **Meta tracking** - Identify which parts/builds are gaining value

### Data Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Sky Mavis RPC  │     │ Sky Mavis GQL   │     │    Goldrush     │
│  (Sales Events) │     │ (Listings/Meta) │     │ (Wallet Data)   │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      RAW DATA TABLES                            │
│  axie_sales │ axie_listings │ axie_metadata │ wallet_activity   │
└────────┬────────────────┬───────────────────┬───────────────────┘
         │                │                   │
         ▼                ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                   AGGREGATED TABLES                             │
│  market_snapshots │ parts_pricing │ class_metrics │ breeding    │
└────────┬────────────────┬───────────────────┬───────────────────┘
         │                │                   │
         ▼                ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MATERIALIZED VIEWS                           │
│  mv_floor_history │ mv_undervalued │ mv_daily_volume │ mv_hot   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  axie_metadata  │       │ axie_part_map   │       │   axie_parts    │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ axie_id (PK)    │──┐    │ axie_id (FK)    │    ┌──│ part_id (PK)    │
│ class           │  │    │ part_id (FK)    │────┘  │ part_name       │
│ breed_count     │  └───▶│ slot            │       │ part_type       │
│ genes           │       │ is_dominant     │       │ part_class      │
│ parts_json      │       └─────────────────┘       │ is_meta         │
│ pure_part_count │                                 └─────────────────┘
│ owner           │
└────────┬────────┘
         │
         ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   axie_sales    │       │  axie_listings  │       │    wallets      │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ axie_id (PK)    │       │ address (PK)    │
│ axie_id (FK)    │       │ class           │       │ label           │
│ seller          │       │ price_usd       │       │ total_volume    │
│ buyer           │       │ price_eth       │       │ is_whale        │
│ price_usd       │       │ seller          │       └─────────────────┘
│ price_token     │       │ listed_at       │
│ block_timestamp │       │ price_vs_floor  │
│ tx_hash         │       │ price_vs_last   │
└─────────────────┘       └─────────────────┘
(Partitioned by month)

┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ market_snapshot │       │  class_metrics  │       │  parts_pricing  │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ snapshot_at     │       │ snapshot_at     │       │ snapshot_at     │
│ total_listed    │       │ class           │       │ part_id         │
│ total_volume    │       │ floor_price_usd │       │ floor_price_usd │
│ avg_price       │       │ sales_count     │       │ volume_24h_usd  │
│ floor_price     │       │ volume_usd      │       │ floor_change_24h│
│ eth_usd         │       │ floor_change_pct│       │ volume_change   │
└─────────────────┘       └─────────────────┘       └─────────────────┘
```

---

## Core Tables

### 1. `axie_metadata` - Axie Master Data

```sql
CREATE TABLE axie_metadata (
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
    stat_total      SMALLINT GENERATED ALWAYS AS (hp + speed + skill + morale) STORED,

    -- Parts (denormalized for query speed)
    parts_json      JSONB,
    part_eyes       VARCHAR(50),
    part_ears       VARCHAR(50),
    part_mouth      VARCHAR(50),
    part_horn       VARCHAR(50),
    part_back       VARCHAR(50),
    part_tail       VARCHAR(50),

    -- Purity metrics
    pure_part_count SMALLINT,
    is_pure         BOOLEAN GENERATED ALWAYS AS (pure_part_count = 6) STORED,

    -- Ownership
    owner           VARCHAR(66),
    birth_date      TIMESTAMP,
    image_url       TEXT,

    -- Timestamps
    first_seen_at   TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_axie_class ON axie_metadata(class);
CREATE INDEX idx_axie_breed_count ON axie_metadata(breed_count);
CREATE INDEX idx_axie_class_breed ON axie_metadata(class, breed_count);
CREATE INDEX idx_axie_pure ON axie_metadata(is_pure) WHERE is_pure = TRUE;
CREATE INDEX idx_axie_parts ON axie_metadata(part_mouth, part_horn, part_back, part_tail);
CREATE INDEX idx_axie_owner ON axie_metadata(owner);
```

### 2. `axie_parts` - Parts Reference

```sql
CREATE TABLE axie_parts (
    part_id         VARCHAR(50) PRIMARY KEY,
    part_name       VARCHAR(100) NOT NULL,
    part_type       VARCHAR(20) NOT NULL,  -- Eyes, Ears, Mouth, Horn, Back, Tail
    part_class      VARCHAR(20) NOT NULL,  -- Beast, Plant, etc.

    -- Game mechanics
    energy_cost     SMALLINT,
    damage          SMALLINT,
    shield          SMALLINT,
    effect          TEXT,

    -- Meta tracking
    is_meta         BOOLEAN DEFAULT FALSE,
    meta_tier       VARCHAR(10),  -- S, A, B, C tier

    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_parts_type ON axie_parts(part_type);
CREATE INDEX idx_parts_class ON axie_parts(part_class);
CREATE INDEX idx_parts_meta ON axie_parts(is_meta) WHERE is_meta = TRUE;
```

### 3. `axie_part_mapping` - Axie-Parts Junction

```sql
CREATE TABLE axie_part_mapping (
    axie_id         INTEGER REFERENCES axie_metadata(axie_id),
    part_id         VARCHAR(50) REFERENCES axie_parts(part_id),
    slot            VARCHAR(20) NOT NULL,  -- eyes, ears, mouth, horn, back, tail
    is_dominant     BOOLEAN DEFAULT TRUE,  -- D, R1, R2 genes
    PRIMARY KEY (axie_id, part_id, slot, is_dominant)
);

CREATE INDEX idx_part_mapping_part ON axie_part_mapping(part_id);
```

---

## Transaction Tables

### 4. `axie_sales` - Sales History (Partitioned)

```sql
CREATE TABLE axie_sales (
    id              BIGSERIAL,
    tx_hash         VARCHAR(66) NOT NULL,

    -- Axie info (denormalized)
    axie_id         INTEGER NOT NULL,
    class           VARCHAR(20),
    breed_count     SMALLINT,

    -- Price data
    price_raw       NUMERIC(30, 0),
    price_token     NUMERIC(20, 10),
    token_type      VARCHAR(10) NOT NULL,  -- WETH, WRON
    price_usd       NUMERIC(12, 2),

    -- Exchange rates at sale time
    eth_usd_rate    NUMERIC(10, 2),
    ron_usd_rate    NUMERIC(10, 6),

    -- Parties
    seller          VARCHAR(66),
    buyer           VARCHAR(66),

    -- Blockchain data
    block_number    BIGINT NOT NULL,
    block_timestamp TIMESTAMP NOT NULL,

    created_at      TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (id, block_timestamp)
) PARTITION BY RANGE (block_timestamp);

-- Monthly partitions
CREATE TABLE axie_sales_2025_01 PARTITION OF axie_sales
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
-- Continue for each month...

-- Indexes
CREATE INDEX idx_sales_axie ON axie_sales(axie_id);
CREATE INDEX idx_sales_class ON axie_sales(class);
CREATE INDEX idx_sales_timestamp ON axie_sales(block_timestamp DESC);
CREATE INDEX idx_sales_price ON axie_sales(price_usd);
CREATE UNIQUE INDEX idx_sales_unique ON axie_sales(tx_hash, axie_id);
```

### 5. `axie_listings` - Current Marketplace State

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
    last_sale_price NUMERIC(12, 2),
    price_vs_floor  NUMERIC(8, 4),
    price_vs_last   NUMERIC(8, 4),

    snapshot_at     TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_listings_class ON axie_listings(class);
CREATE INDEX idx_listings_price ON axie_listings(price_usd);
CREATE INDEX idx_listings_undervalued ON axie_listings(price_vs_last) WHERE price_vs_last < 0.9;
```

---

## Aggregated Tables

### 6. `market_snapshots` - Hourly Market Metrics

```sql
CREATE TABLE market_snapshots (
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

CREATE INDEX idx_market_snap_time ON market_snapshots(snapshot_at DESC);
```

### 7. `class_metrics` - Per-Class Statistics

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
    floor_change_pct NUMERIC(8, 4),
    volume_change_pct NUMERIC(8, 4),

    UNIQUE(snapshot_at, class)
);

CREATE INDEX idx_class_metrics_time ON class_metrics(snapshot_at DESC);
CREATE INDEX idx_class_metrics_class ON class_metrics(class, snapshot_at DESC);
```

### 8. `parts_pricing` - Part Value Tracking

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

### 9. `price_alerts` - Automated Alerts

```sql
CREATE TABLE price_alerts (
    id              BIGSERIAL PRIMARY KEY,
    alert_type      VARCHAR(50) NOT NULL,  -- undervalued, volume_spike, floor_drop
    severity        VARCHAR(10) DEFAULT 'info',

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

### 10. `wallet_activity` - Whale Tracking

```sql
CREATE TABLE wallet_activity (
    id              BIGSERIAL PRIMARY KEY,
    wallet          VARCHAR(66) NOT NULL,
    activity_type   VARCHAR(20) NOT NULL,  -- buy, sell, breed, transfer

    axie_id         INTEGER,
    price_usd       NUMERIC(12, 2),

    block_timestamp TIMESTAMP NOT NULL,
    tx_hash         VARCHAR(66),

    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_wallet_activity_wallet ON wallet_activity(wallet, block_timestamp DESC);
CREATE INDEX idx_wallet_activity_time ON wallet_activity(block_timestamp DESC);

-- Tracked wallets
CREATE TABLE tracked_wallets (
    wallet          VARCHAR(66) PRIMARY KEY,
    label           VARCHAR(100),
    notes           TEXT,
    track_since     TIMESTAMP DEFAULT NOW(),
    is_active       BOOLEAN DEFAULT TRUE
);
```

### 11. `breeding_records` - Breeding Analytics

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
    offspring_value_usd NUMERIC(12, 2),
    roi_pct         NUMERIC(8, 4),

    -- Timing
    bred_at         TIMESTAMP,
    sold_at         TIMESTAMP,

    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_breeding_parents ON breeding_records(parent1_id, parent2_id);
CREATE INDEX idx_breeding_offspring ON breeding_records(offspring_id);
CREATE INDEX idx_breeding_time ON breeding_records(bred_at DESC);
```

---

## Materialized Views

### Floor Price History

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
```

### Undervalued Listings

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
WHERE l.price_vs_last < 0.85
   OR l.price_vs_floor < 0.95
ORDER BY l.price_vs_last ASC
LIMIT 100;

CREATE UNIQUE INDEX idx_mv_undervalued ON mv_undervalued(axie_id);
```

### Hot Parts (Trending Meta)

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
  AND pp.volume_change_24h > 0.2
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

### Estimate Axie Value

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

    v_base_price := get_floor_price(v_class);

    v_breed_mult := CASE v_breed_count
        WHEN 0 THEN 1.5
        WHEN 1 THEN 1.2
        WHEN 2 THEN 1.1
        ELSE 1.0
    END;

    v_pure_mult := 1.0 + (v_pure_count * 0.1);

    RETURN v_base_price * v_breed_mult * v_pure_mult;
END;
$$ LANGUAGE plpgsql STABLE;
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
| `parts_pricing` | Every 6 hours | Aggregation job |
| `mv_undervalued` | Every 5 min | REFRESH CONCURRENTLY |
| `mv_floor_history` | Every 15 min | REFRESH CONCURRENTLY |
| `mv_hot_parts` | Every hour | REFRESH CONCURRENTLY |

---

## Sample Queries

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
    ROUND((AVG(floor_price_usd) / LAG(AVG(floor_price_usd)) OVER (
        PARTITION BY class ORDER BY date_trunc('day', snapshot_at)
    ) - 1) * 100, 2) as change_pct
FROM class_metrics
WHERE snapshot_at > NOW() - INTERVAL '30 days'
GROUP BY 1, 2
ORDER BY 1 DESC, 2;
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

**Estimated Total:** ~100 MB/month for active tables

---

## Related Documentation

- **Infrastructure:** See `docs/INFRASTRUCTURE.md`
- **Architecture:** See `docs/ARCHITECTURE.md`
- **API Specification:** See `docs/03-api-specification.md`
