# Database Schema Design

## Overview

The database uses PostgreSQL with the TimescaleDB extension for efficient time-series data storage. The schema is designed to support:

- Fast Axie lookups by traits and genes
- Historical price tracking with time-based aggregations
- Wallet portfolio analysis
- Breeding history and outcome tracking

## Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     axies       │       │   axie_parts    │       │     parts       │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │──┐    │ id (PK)         │    ┌──│ id (PK)         │
│ name            │  │    │ axie_id (FK)    │────┘  │ part_id         │
│ class           │  └───▶│ part_id (FK)    │       │ name            │
│ breed_count     │       │ position        │       │ class           │
│ genes           │       │ gene_type (D/R1)│       │ type (mouth,    │
│ image_url       │       └─────────────────┘       │       horn, etc)│
│ owner_address   │                                 │ ability_id      │
│ birth_date      │                                 └─────────────────┘
│ matron_id       │                                          │
│ sire_id         │       ┌─────────────────┐                │
│ created_at      │       │   abilities     │◀───────────────┘
│ updated_at      │       ├─────────────────┤
└─────────────────┘       │ id (PK)         │
         │                │ name            │
         │                │ energy_cost     │
         │                │ damage          │
         │                │ shield          │
         │                │ description     │
         │                └─────────────────┘
         │
         ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     sales       │       │   listings      │       │    wallets      │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │       │ address (PK)    │
│ axie_id (FK)    │       │ axie_id (FK)    │       │ alias           │
│ seller_address  │       │ seller_address  │       │ first_seen      │
│ buyer_address   │       │ price_eth       │       │ last_active     │
│ price_eth       │       │ price_usd       │       │ total_volume    │
│ price_usd       │       │ listed_at       │       │ axie_count      │
│ tx_hash         │       │ expires_at      │       │ created_at      │
│ sold_at (time)  │       │ status          │       │ updated_at      │
│ marketplace     │       │ created_at      │       └─────────────────┘
└─────────────────┘       └─────────────────┘
         │
         │ TimescaleDB
         │ hypertable
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        price_history (hypertable)                    │
├─────────────────────────────────────────────────────────────────────┤
│ time (PK)          │ Timestamp, partitioned by day                   │
│ class              │ Axie class for grouping                         │
│ trait_key          │ Composite key (e.g., "mouth:cute_bunny")        │
│ floor_price_eth    │ Lowest sale price in period                     │
│ avg_price_eth      │ Average sale price                              │
│ median_price_eth   │ Median sale price                               │
│ max_price_eth      │ Highest sale price                              │
│ volume             │ Number of sales                                 │
│ volume_eth         │ Total ETH volume                                │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────┐       ┌─────────────────┐
│ breeding_pairs  │       │    breeds       │
├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │
│ matron_id (FK)  │       │ pair_id (FK)    │──────▶ breeding_pairs
│ sire_id (FK)    │       │ offspring_id(FK)│──────▶ axies
│ breed_count     │       │ tx_hash         │
│ last_breed      │       │ breed_at        │
│ created_at      │       │ created_at      │
└─────────────────┘       └─────────────────┘
```

## Table Definitions

### Core Tables

```sql
-- Axie Classes Enum
CREATE TYPE axie_class AS ENUM (
    'beast', 'bug', 'bird', 'plant',
    'aquatic', 'reptile', 'mech',
    'dawn', 'dusk'
);

-- Body Part Types Enum
CREATE TYPE part_type AS ENUM (
    'eyes', 'ears', 'mouth', 'horn', 'back', 'tail'
);

-- Gene Types Enum
CREATE TYPE gene_type AS ENUM ('d', 'r1', 'r2');

-- Main Axies Table
CREATE TABLE axies (
    id BIGINT PRIMARY KEY,                    -- Axie NFT ID
    name VARCHAR(255),
    class axie_class NOT NULL,
    breed_count SMALLINT DEFAULT 0,
    genes VARCHAR(128) NOT NULL,              -- Hex encoded genes
    image_url TEXT,
    owner_address VARCHAR(42) NOT NULL,
    birth_date TIMESTAMP,
    matron_id BIGINT REFERENCES axies(id),
    sire_id BIGINT REFERENCES axies(id),

    -- Purity metrics (precomputed for fast queries)
    purity_score SMALLINT,                    -- 0-6 (parts matching class)
    gene_purity_score SMALLINT,               -- Including R1, R2

    -- Stats
    hp SMALLINT,
    speed SMALLINT,
    skill SMALLINT,
    morale SMALLINT,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for common queries
CREATE INDEX idx_axies_class ON axies(class);
CREATE INDEX idx_axies_owner ON axies(owner_address);
CREATE INDEX idx_axies_purity ON axies(purity_score);
CREATE INDEX idx_axies_breed_count ON axies(breed_count);

-- Body Parts Reference Table
CREATE TABLE parts (
    id SERIAL PRIMARY KEY,
    part_id VARCHAR(50) UNIQUE NOT NULL,      -- e.g., "mouth-cute-bunny"
    name VARCHAR(100) NOT NULL,               -- e.g., "Cute Bunny"
    class axie_class NOT NULL,
    type part_type NOT NULL,
    ability_id INTEGER REFERENCES abilities(id),

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_parts_class ON parts(class);
CREATE INDEX idx_parts_type ON parts(type);

-- Axie Parts Junction Table (6 parts × 3 gene types = up to 18 rows per axie)
CREATE TABLE axie_parts (
    id SERIAL PRIMARY KEY,
    axie_id BIGINT REFERENCES axies(id) ON DELETE CASCADE,
    part_id INTEGER REFERENCES parts(id),
    position part_type NOT NULL,
    gene_type gene_type NOT NULL,

    UNIQUE(axie_id, position, gene_type)
);

CREATE INDEX idx_axie_parts_axie ON axie_parts(axie_id);
CREATE INDEX idx_axie_parts_part ON axie_parts(part_id);
CREATE INDEX idx_axie_parts_gene_type ON axie_parts(gene_type);

-- Abilities Table
CREATE TABLE abilities (
    id SERIAL PRIMARY KEY,
    ability_id VARCHAR(50) UNIQUE NOT NULL,
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
```

### Market Data Tables

```sql
-- Current Listings (active marketplace listings)
CREATE TABLE listings (
    id SERIAL PRIMARY KEY,
    axie_id BIGINT REFERENCES axies(id),
    seller_address VARCHAR(42) NOT NULL,
    price_eth DECIMAL(20, 8) NOT NULL,
    price_usd DECIMAL(20, 2),

    listed_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',      -- active, sold, cancelled

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_listings_axie ON listings(axie_id);
CREATE INDEX idx_listings_status ON listings(status);
CREATE INDEX idx_listings_price ON listings(price_eth);
CREATE INDEX idx_listings_seller ON listings(seller_address);

-- Sales History
CREATE TABLE sales (
    id SERIAL PRIMARY KEY,
    axie_id BIGINT REFERENCES axies(id),
    seller_address VARCHAR(42) NOT NULL,
    buyer_address VARCHAR(42) NOT NULL,
    price_eth DECIMAL(20, 8) NOT NULL,
    price_usd DECIMAL(20, 2),
    tx_hash VARCHAR(66) UNIQUE NOT NULL,
    sold_at TIMESTAMP NOT NULL,
    marketplace VARCHAR(50) DEFAULT 'official',

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sales_axie ON sales(axie_id);
CREATE INDEX idx_sales_sold_at ON sales(sold_at DESC);
CREATE INDEX idx_sales_seller ON sales(seller_address);
CREATE INDEX idx_sales_buyer ON sales(buyer_address);
CREATE INDEX idx_sales_price ON sales(price_eth);

-- Price History Hypertable (TimescaleDB)
CREATE TABLE price_history (
    time TIMESTAMPTZ NOT NULL,
    class axie_class,
    trait_key VARCHAR(100),                   -- e.g., "mouth:cute_bunny" or "class:beast"

    floor_price_eth DECIMAL(20, 8),
    avg_price_eth DECIMAL(20, 8),
    median_price_eth DECIMAL(20, 8),
    max_price_eth DECIMAL(20, 8),

    volume INTEGER DEFAULT 0,
    volume_eth DECIMAL(20, 8) DEFAULT 0,

    PRIMARY KEY (time, class, trait_key)
);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('price_history', 'time');

-- Continuous aggregate for daily stats
CREATE MATERIALIZED VIEW price_history_daily
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS day,
    class,
    trait_key,
    AVG(floor_price_eth) AS avg_floor,
    AVG(avg_price_eth) AS avg_price,
    SUM(volume) AS total_volume,
    SUM(volume_eth) AS total_volume_eth
FROM price_history
GROUP BY day, class, trait_key;
```

### User & Wallet Tables

```sql
-- Wallets (tracked addresses)
CREATE TABLE wallets (
    address VARCHAR(42) PRIMARY KEY,
    alias VARCHAR(100),
    first_seen TIMESTAMP,
    last_active TIMESTAMP,

    -- Aggregated stats
    total_buy_volume_eth DECIMAL(20, 8) DEFAULT 0,
    total_sell_volume_eth DECIMAL(20, 8) DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    axie_count INTEGER DEFAULT 0,

    -- Tracking flags
    is_tracked BOOLEAN DEFAULT FALSE,
    is_whale BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Wallet Axie Holdings (current state)
CREATE TABLE wallet_holdings (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(42) REFERENCES wallets(address),
    axie_id BIGINT REFERENCES axies(id),
    acquired_at TIMESTAMP,
    acquisition_price_eth DECIMAL(20, 8),

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(wallet_address, axie_id)
);

CREATE INDEX idx_holdings_wallet ON wallet_holdings(wallet_address);
CREATE INDEX idx_holdings_axie ON wallet_holdings(axie_id);
```

### Breeding Tables

```sql
-- Breeding Pairs
CREATE TABLE breeding_pairs (
    id SERIAL PRIMARY KEY,
    matron_id BIGINT REFERENCES axies(id),
    sire_id BIGINT REFERENCES axies(id),
    breed_count INTEGER DEFAULT 0,
    last_breed TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(matron_id, sire_id)
);

-- Breeding Events
CREATE TABLE breeds (
    id SERIAL PRIMARY KEY,
    pair_id INTEGER REFERENCES breeding_pairs(id),
    offspring_id BIGINT REFERENCES axies(id),
    tx_hash VARCHAR(66) UNIQUE NOT NULL,
    breed_cost_slp INTEGER,
    breed_cost_axs DECIMAL(20, 8),
    breed_at TIMESTAMP NOT NULL,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_breeds_pair ON breeds(pair_id);
CREATE INDEX idx_breeds_offspring ON breeds(offspring_id);
CREATE INDEX idx_breeds_date ON breeds(breed_at DESC);
```

## Query Examples

### Find Axies by Traits

```sql
-- Find all pure Beast axies with "Nut Cracker" mouth (dominant)
SELECT a.id, a.name, a.purity_score, l.price_eth
FROM axies a
JOIN axie_parts ap ON a.id = ap.axie_id
JOIN parts p ON ap.part_id = p.id
LEFT JOIN listings l ON a.id = l.axie_id AND l.status = 'active'
WHERE a.class = 'beast'
  AND a.purity_score = 6
  AND p.name = 'Nut Cracker'
  AND ap.position = 'mouth'
  AND ap.gene_type = 'd'
ORDER BY l.price_eth ASC NULLS LAST;
```

### Floor Price by Trait Over Time

```sql
-- Get 7-day floor price trend for Beast mouths
SELECT
    time_bucket('1 day', time) AS day,
    trait_key,
    AVG(floor_price_eth) AS floor
FROM price_history
WHERE class = 'beast'
  AND trait_key LIKE 'mouth:%'
  AND time > NOW() - INTERVAL '7 days'
GROUP BY day, trait_key
ORDER BY day, trait_key;
```

### Breeding ROI Analysis

```sql
-- Calculate average breeding outcomes vs cost
SELECT
    p_matron.class AS matron_class,
    p_sire.class AS sire_class,
    COUNT(*) AS breed_count,
    AVG(b.breed_cost_slp) AS avg_cost_slp,
    AVG(offspring_sale.price_eth) AS avg_offspring_value
FROM breeds b
JOIN breeding_pairs bp ON b.pair_id = bp.id
JOIN axies a_matron ON bp.matron_id = a_matron.id
JOIN axies a_sire ON bp.sire_id = a_sire.id
JOIN parts p_matron ON ... -- dominant class
JOIN parts p_sire ON ...
LEFT JOIN sales offspring_sale ON b.offspring_id = offspring_sale.axie_id
GROUP BY p_matron.class, p_sire.class
ORDER BY breed_count DESC;
```

## Indexes Strategy

| Table | Index | Purpose |
|-------|-------|---------|
| axies | class, purity_score | Filter by class and purity |
| axies | owner_address | Wallet portfolio lookup |
| axie_parts | (part_id, gene_type) | Trait-based searches |
| listings | (status, price_eth) | Active listing queries |
| sales | sold_at DESC | Recent sales feed |
| price_history | (time, class, trait_key) | Time-series aggregations |

## Migration Strategy

1. **Initial Setup**: Create base tables without TimescaleDB
2. **Add TimescaleDB**: Install extension, convert price_history
3. **Seed Parts Data**: Import all known body parts and abilities
4. **Historical Import**: Backfill sales and price history
5. **Add Continuous Aggregates**: Set up materialized views
