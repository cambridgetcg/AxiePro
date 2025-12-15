# Big Data Architecture: Axie Meta Analytics & Deal Snatcher

## Executive Summary

This document outlines the architecture for a data-intensive platform that:
1. **Tracks pricing trends** across millions of data points
2. **Detects meta shifts** before they become obvious to the market
3. **Snatches undervalued deals** in real-time with sub-second latency

---

## Data Scale Estimation

| Metric | Volume | Growth Rate |
|--------|--------|-------------|
| Total Axies | ~11 million | Stable (breeding slowed) |
| Active Listings | 50,000 - 100,000 | Daily fluctuation |
| Daily Sales | 5,000 - 10,000 | Varies with market |
| Unique Trait Combinations | ~50,000+ | Fixed |
| Price Points/Day | ~500,000 | Hourly snapshots × traits |
| Historical Data (1yr) | ~180M rows | Time-series |

**Storage Estimate**: 50-100 GB for 1 year of comprehensive price history

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DATA INGESTION LAYER                                   │
│                                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ Sky Mavis    │  │   Moralis    │  │   Ronin      │  │  Battle API  │        │
│  │  GraphQL     │  │    API       │  │    RPC       │  │  (Win Rates) │        │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘        │
│         │                 │                 │                 │                 │
│         └─────────────────┴────────┬────────┴─────────────────┘                 │
│                                    │                                            │
│                                    ▼                                            │
│                         ┌──────────────────┐                                    │
│                         │  Amazon Kinesis  │  ← Real-time stream                │
│                         │  Data Streams    │                                    │
│                         └────────┬─────────┘                                    │
│                                  │                                              │
└──────────────────────────────────┼──────────────────────────────────────────────┘
                                   │
                 ┌─────────────────┼─────────────────┐
                 │                 │                 │
                 ▼                 ▼                 ▼
┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐
│   HOT PATH         │ │   WARM PATH        │ │   COLD PATH        │
│   (Real-time)      │ │   (Analytics)      │ │   (Historical)     │
│                    │ │                    │ │                    │
│ ┌────────────────┐ │ │ ┌────────────────┐ │ │ ┌────────────────┐ │
│ │ Lambda         │ │ │ │ Kinesis        │ │ │ │ Kinesis        │ │
│ │ (Deal Detect)  │ │ │ │ Firehose       │ │ │ │ Firehose       │ │
│ └───────┬────────┘ │ │ └───────┬────────┘ │ │ └───────┬────────┘ │
│         │          │ │         │          │ │         │          │
│         ▼          │ │         ▼          │ │         ▼          │
│ ┌────────────────┐ │ │ ┌────────────────┐ │ │ ┌────────────────┐ │
│ │ ElastiCache    │ │ │ │ Aurora         │ │ │ │ S3 + Parquet   │ │
│ │ Redis Cluster  │ │ │ │ PostgreSQL     │ │ │ │ Data Lake      │ │
│ │ (Sub-ms reads) │ │ │ │ + TimescaleDB  │ │ │ └───────┬────────┘ │
│ └───────┬────────┘ │ │ └───────┬────────┘ │ │         │          │
│         │          │ │         │          │ │         ▼          │
│         ▼          │ │         ▼          │ │ ┌────────────────┐ │
│ ┌────────────────┐ │ │ ┌────────────────┐ │ │ │ Athena /       │ │
│ │ SNS/SQS        │ │ │ │ Grafana        │ │ │ │ Redshift       │ │
│ │ Deal Alerts    │ │ │ │ Dashboards     │ │ │ │ Serverless     │ │
│ └────────────────┘ │ │ └────────────────┘ │ │ └────────────────┘ │
└────────────────────┘ └────────────────────┘ └────────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │      SageMaker         │
                    │  Meta Shift Detection  │
                    │  Price Prediction      │
                    │  Anomaly Detection     │
                    └────────────────────────┘
```

---

## Database Selection Analysis

### Option Comparison

| Database | Pros | Cons | Cost (Est.) | Best For |
|----------|------|------|-------------|----------|
| **Aurora PostgreSQL + TimescaleDB** | SQL-compatible, great compression, continuous aggregates | Single-region by default | $150-400/mo | Primary operational DB |
| **Redshift Serverless** | Massive parallel queries, scales to PBs | Cold start latency, expensive at scale | Pay per query | Heavy analytics |
| **Amazon Timestream** | Serverless, auto-tiering | Limited query flexibility, expensive writes | $200-500/mo | Pure time-series |
| **ClickHouse (self-hosted)** | Blazing fast analytics, great compression | Ops overhead, complex | $100-200/mo | If you need speed |
| **DynamoDB** | Serverless, fast KV lookups | Expensive for scans, limited queries | Variable | Real-time lookups |

### **Recommended Stack**

```
┌─────────────────────────────────────────────────────────────────┐
│                    RECOMMENDED DATABASE STACK                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  AURORA POSTGRESQL + TIMESCALEDB EXTENSION               │    │
│  │  ─────────────────────────────────────────────────────   │    │
│  │  • Primary operational database                          │    │
│  │  • Time-series optimized with hypertables               │    │
│  │  • Continuous aggregates for pre-computed metrics       │    │
│  │  • 10-40x compression on time-series data               │    │
│  │  • SQL compatibility = easy queries                      │    │
│  │                                                          │    │
│  │  Instance: db.r6g.large ($200/mo) or Serverless v2      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  ELASTICACHE REDIS CLUSTER                               │    │
│  │  ─────────────────────────────────────────────────────   │    │
│  │  • Real-time floor prices (1-second updates)            │    │
│  │  • Fair value cache per Axie                            │    │
│  │  • Active listings index                                │    │
│  │  • Sub-millisecond reads for deal detection             │    │
│  │                                                          │    │
│  │  Instance: cache.r6g.large cluster ($150/mo)            │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  S3 + PARQUET (DATA LAKE)                                │    │
│  │  ─────────────────────────────────────────────────────   │    │
│  │  • Raw historical data archive                          │    │
│  │  • Partitioned by date for efficient queries            │    │
│  │  • Query via Athena (serverless, pay-per-query)         │    │
│  │  • Feed ML training pipelines                           │    │
│  │                                                          │    │
│  │  Cost: ~$2/mo per 100GB stored                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Meta Shift Detection System

### What is "Meta" in Axie?

The **meta** refers to the most effective strategies/builds in PvP battles. When the meta shifts:
1. Certain card combinations become dominant
2. Demand for Axies with those parts increases
3. Prices rise for meta-relevant traits
4. Early detection = arbitrage opportunity

### Detection Signals

```
┌─────────────────────────────────────────────────────────────────┐
│                    META SHIFT INDICATORS                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. BATTLE WIN RATE CHANGES                                     │
│     ───────────────────────                                     │
│     • Track win rates by part combination                       │
│     • Detect when specific parts start winning more             │
│     • Leading indicator (battles before market reacts)          │
│                                                                  │
│  2. PRICE VELOCITY                                              │
│     ──────────────                                              │
│     • Rate of price change for specific traits                  │
│     • Acceleration detection (2nd derivative)                   │
│     • Volume-weighted price momentum                            │
│                                                                  │
│  3. LISTING BEHAVIOR                                            │
│     ─────────────────                                           │
│     • Decrease in listings for certain traits (holding)         │
│     • Increase in buy-side pressure                             │
│     • Time-on-market decreasing                                 │
│                                                                  │
│  4. SOCIAL SIGNALS (Future)                                     │
│     ──────────────────────                                      │
│     • Discord/Twitter sentiment                                 │
│     • Streamer/pro player builds                                │
│     • Patch notes analysis                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### ML Pipeline for Meta Detection

```python
# Simplified meta detection model architecture

FEATURES = [
    # Price features (per trait)
    "price_7d_change",
    "price_velocity",
    "price_acceleration",
    "volume_7d",
    "volume_change",
    "listings_count",
    "listings_change",
    "time_to_sale_avg",

    # Battle features (if available)
    "win_rate_7d",
    "win_rate_change",
    "usage_rate",
    "usage_rate_change",

    # Cross-trait features
    "combo_win_rate",  # This trait + common pairings
    "class_floor_ratio",  # Price vs class floor
]

# Model: Gradient Boosting or LSTM for sequence prediction
# Output: Meta shift probability score per trait
```

---

## Deal Snatching System

### Architecture for Sub-Second Detection

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEAL SNATCHER PIPELINE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  NEW LISTING EVENT                                              │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1. PARSE LISTING (Lambda - 50ms)                        │   │
│  │     • Extract Axie ID, price, seller                     │   │
│  │     • Decode genes if not cached                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  2. FAIR VALUE LOOKUP (Redis - 1ms)                      │   │
│  │     • Get cached fair value for this gene combo          │   │
│  │     • Get current floor for class + purity               │   │
│  │     • Get trait-specific premium                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  3. DISCOUNT CALCULATION (Lambda - 10ms)                 │   │
│  │     • discount = (fair_value - listing_price) / fair_value│   │
│  │     • Apply confidence score                             │   │
│  │     • Check meta-relevance boost                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  4. DECISION ENGINE                                      │   │
│  │     IF discount > threshold AND confidence > 0.8:        │   │
│  │        → ALERT via SNS (Telegram/Discord/SMS)            │   │
│  │        → Optional: AUTO-BUY via smart contract           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  TOTAL LATENCY: < 100ms from listing to alert                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Fair Value Model

```python
def calculate_fair_value(axie: Axie) -> float:
    """
    Multi-factor fair value estimation.

    Components:
    1. Base value: Floor price for class + purity
    2. Trait premiums: Sum of individual part values
    3. Synergy bonus: Combinations that work well together
    4. Meta multiplier: Current meta relevance
    5. Breed discount: Higher breed count = lower value
    """

    # Base value
    base = get_floor_price(axie.class_, axie.purity_score)

    # Trait premiums (from historical sales data)
    trait_value = sum(
        get_trait_premium(part.name, part.class_)
        for part in axie.dominant_parts
    )

    # Synergy bonus (certain combos are worth more together)
    synergy = calculate_synergy_bonus(axie.parts)

    # Meta multiplier (from ML model)
    meta_score = get_meta_relevance(axie.parts)
    meta_multiplier = 1.0 + (meta_score * 0.5)  # Up to 50% boost

    # Breed count discount
    breed_discount = 1.0 - (axie.breed_count * 0.05)  # 5% per breed

    fair_value = (base + trait_value + synergy) * meta_multiplier * breed_discount

    return fair_value
```

---

## Data Pipeline Implementation

### Kinesis Stream Configuration

```python
# Infrastructure as Code (Terraform or CDK)

# Kinesis Data Stream for real-time events
stream_config = {
    "name": "axie-marketplace-events",
    "shard_count": 4,  # ~4MB/s write, 8MB/s read
    "retention_hours": 24,
}

# Event types flowing through stream
EVENT_TYPES = [
    "listing.created",
    "listing.cancelled",
    "listing.sold",
    "axie.transferred",
    "price.updated",
]
```

### TimescaleDB Schema for Analytics

```sql
-- Enable TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Price snapshots (hypertable)
CREATE TABLE trait_prices (
    time        TIMESTAMPTZ NOT NULL,
    trait_key   TEXT NOT NULL,           -- e.g., "mouth:nut-cracker"
    class       TEXT NOT NULL,
    floor_eth   DECIMAL(20,8),
    avg_eth     DECIMAL(20,8),
    median_eth  DECIMAL(20,8),
    volume      INTEGER,
    listings    INTEGER,

    PRIMARY KEY (time, trait_key, class)
);

-- Convert to hypertable (auto-partitions by time)
SELECT create_hypertable('trait_prices', 'time');

-- Compress old data automatically (10x-40x compression)
ALTER TABLE trait_prices SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'trait_key, class'
);

SELECT add_compression_policy('trait_prices', INTERVAL '7 days');

-- Continuous aggregate for hourly rollups (pre-computed)
CREATE MATERIALIZED VIEW trait_prices_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS hour,
    trait_key,
    class,
    FIRST(floor_eth, time) AS open_floor,
    MAX(floor_eth) AS high_floor,
    MIN(floor_eth) AS low_floor,
    LAST(floor_eth, time) AS close_floor,
    AVG(avg_eth) AS avg_price,
    SUM(volume) AS total_volume
FROM trait_prices
GROUP BY hour, trait_key, class;

-- Refresh policy
SELECT add_continuous_aggregate_policy('trait_prices_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour'
);

-- Meta shift tracking table
CREATE TABLE meta_signals (
    time            TIMESTAMPTZ NOT NULL,
    trait_key       TEXT NOT NULL,
    signal_type     TEXT NOT NULL,  -- 'price_velocity', 'volume_spike', 'win_rate_change'
    signal_value    DECIMAL(10,4),
    confidence      DECIMAL(5,4),

    PRIMARY KEY (time, trait_key, signal_type)
);

SELECT create_hypertable('meta_signals', 'time');
```

---

## AWS Infrastructure (Terraform)

```hcl
# terraform/main.tf

# Aurora PostgreSQL with TimescaleDB
resource "aws_rds_cluster" "main" {
  cluster_identifier     = "axie-explorer"
  engine                 = "aurora-postgresql"
  engine_version         = "15.4"
  database_name          = "axie_explorer"
  master_username        = var.db_username
  master_password        = var.db_password

  serverlessv2_scaling_configuration {
    min_capacity = 0.5   # Scale to zero when idle
    max_capacity = 16    # Scale up for heavy queries
  }

  # Enable Performance Insights
  performance_insights_enabled = true
}

# ElastiCache Redis
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "axie-cache"
  engine               = "redis"
  node_type            = "cache.r6g.large"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"

  # Enable cluster mode for horizontal scaling
  # cluster_mode { ... }
}

# Kinesis Data Stream
resource "aws_kinesis_stream" "marketplace" {
  name             = "axie-marketplace-events"
  shard_count      = 4
  retention_period = 24

  stream_mode_details {
    stream_mode = "PROVISIONED"
  }
}

# Lambda for deal detection
resource "aws_lambda_function" "deal_detector" {
  filename         = "deal_detector.zip"
  function_name    = "axie-deal-detector"
  role            = aws_iam_role.lambda_role.arn
  handler         = "main.handler"
  runtime         = "python3.11"
  timeout         = 10
  memory_size     = 256

  environment {
    variables = {
      REDIS_URL = aws_elasticache_cluster.redis.cache_nodes[0].address
      SNS_TOPIC = aws_sns_topic.alerts.arn
    }
  }
}

# SNS for alerts
resource "aws_sns_topic" "alerts" {
  name = "axie-deal-alerts"
}

# S3 for data lake
resource "aws_s3_bucket" "data_lake" {
  bucket = "axie-explorer-data-lake"
}
```

---

## Cost Estimate (Production Scale)

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| Aurora PostgreSQL Serverless v2 | 0.5-16 ACU | $100-400 |
| ElastiCache Redis | cache.r6g.large | $150 |
| Kinesis Data Streams | 4 shards | $60 |
| Lambda | ~10M invocations | $20 |
| S3 | 100GB + queries | $10 |
| Kinesis Firehose | Data delivery | $30 |
| SNS/SQS | Alerts | $5 |
| App Runner | Backend API | $50 |
| Vercel | Frontend | Free-$20 |
| **Total** | | **$425-745/mo** |

### Cost Optimization Tips
1. Use Aurora Serverless v2 - scales to zero when idle
2. Use S3 + Athena for historical queries (cheaper than keeping in DB)
3. Compress TimescaleDB data older than 7 days
4. Use spot instances for batch processing

---

## Implementation Phases

### Phase 1: Foundation (Current)
- [x] Gene parser
- [x] API clients (Moralis, Sky Mavis)
- [x] Database models
- [x] Basic API endpoints

### Phase 2: Data Pipeline
- [ ] Set up Aurora PostgreSQL + TimescaleDB
- [ ] Implement Kinesis stream ingestion
- [ ] Build price tracking jobs
- [ ] Create continuous aggregates

### Phase 3: Analytics
- [ ] Historical data backfill
- [ ] Price trend analysis queries
- [ ] Grafana dashboards
- [ ] Floor price alerts

### Phase 4: Meta Detection
- [ ] Win rate data integration (if available)
- [ ] Feature engineering pipeline
- [ ] Train meta detection model
- [ ] Deploy to SageMaker

### Phase 5: Deal Snatcher
- [ ] Real-time listing monitor
- [ ] Fair value model
- [ ] Alert system (Telegram/Discord)
- [ ] Optional: Auto-buy bot

---

## Key Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary DB | Aurora PostgreSQL + TimescaleDB | SQL-compatible, great for time-series, managed |
| Cache | ElastiCache Redis | Sub-ms latency for real-time deal detection |
| Streaming | Kinesis | Native AWS integration, reliable |
| Data Lake | S3 + Parquet | Cheap storage, query via Athena |
| ML | SageMaker | Managed training and inference |
| Frontend | Vercel + Next.js | Best DX, edge functions |
| Backend | App Runner | Simple container deployment |
