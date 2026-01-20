# AxiePro System Architecture

## Overview

AxiePro follows a three-tier architecture with clear separation between data ingestion, business logic, and presentation layers. The system is designed for:

1. **Real-time market tracking** - Sub-second deal detection
2. **Meta shift analysis** - Early detection of market trends
3. **Historical analytics** - Time-series data for backtesting

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PRESENTATION LAYER                              │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                        Next.js Frontend                              │   │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│   │  │ Explorer │ │ Analytics│ │ Breeding │ │ Portfolio│ │ Alerts   │  │   │
│   │  │  Page    │ │  Page    │ │   Page   │ │   Page   │ │  Page    │  │   │
│   │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              APPLICATION LAYER                               │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                        FastAPI Backend                               │   │
│   │  ┌────────────────────────────────────────────────────────────┐    │   │
│   │  │                      REST API Routes                        │    │   │
│   │  │  /axies  /market  /breeding  /analytics  /wallet  /alerts  │    │   │
│   │  └────────────────────────────────────────────────────────────┘    │   │
│   │  ┌────────────────────────────────────────────────────────────┐    │   │
│   │  │                    Service Layer                            │    │   │
│   │  │  AxieService  MarketService  BreedingService  WalletService │    │   │
│   │  └────────────────────────────────────────────────────────────┘    │   │
│   │  ┌────────────────────────────────────────────────────────────┐    │   │
│   │  │                    Utility Layer                            │    │   │
│   │  │    GeneParser    PriceCalculator    TraitAnalyzer          │    │   │
│   │  └────────────────────────────────────────────────────────────┘    │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                DATA LAYER                                    │
│                                                                              │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────────┐ │
│   │  PostgreSQL  │    │    Redis     │    │      External APIs           │ │
│   │              │    │    Cache     │    │                              │ │
│   │ - axies      │    │ - listings   │    │  ┌────────┐ ┌─────────────┐  │ │
│   │ - sales      │    │ - prices     │    │  │Moralis │ │ Sky Mavis   │  │ │
│   │ - prices     │    │ - sessions   │    │  │  API   │ │  GraphQL    │  │ │
│   │ - wallets    │    │              │    │  └────────┘ └─────────────┘  │ │
│   └──────────────┘    └──────────────┘    │  ┌────────┐ ┌─────────────┐  │ │
│                                           │  │Ronin   │ │ Chainstack  │  │ │
│                                           │  │  RPC   │ │    RPC      │  │ │
│                                           │  └────────┘ └─────────────┘  │ │
│                                           └──────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Scale

| Metric | Volume | Notes |
|--------|--------|-------|
| Total Axies | ~11 million | Stable (breeding slowed) |
| Active Listings | 50,000 - 100,000 | Daily fluctuation |
| Daily Sales | 5,000 - 10,000 | Varies with market |
| Unique Trait Combinations | ~50,000+ | Fixed |
| Historical Data (1yr) | ~180M rows | Time-series |

**Storage Estimate:** 50-100 GB for 1 year of comprehensive price history

---

## Data Pipeline Architecture

### Three-Path Design

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
│                         │  Amazon Kinesis  │                                    │
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
│ Lambda → Redis     │ │ Firehose → Aurora  │ │ Firehose → S3      │
│ Deal Detection     │ │ PostgreSQL         │ │ Data Lake          │
│ Sub-ms reads       │ │ Dashboards         │ │ Athena queries     │
│                    │ │                    │ │                    │
│ → SNS Alerts       │ │ → Grafana          │ │ → ML Training      │
└────────────────────┘ └────────────────────┘ └────────────────────┘
```

### Data Sources

| Source | Data Type | Frequency |
|--------|-----------|-----------|
| Sky Mavis GraphQL | Axie metadata, listings, genes | On-demand |
| Moralis API | NFT transfers, wallet balances | Real-time |
| Ronin RPC | Sales events, transactions | Block-based |
| Battle API | Win rates (future) | Periodic |

---

## Core Components

### 1. Gene Parsing System

Axie genes are stored as 256-bit integers. The parser decodes them into readable traits:

```
Gene Hex: 0x0000000000000000300c3...

┌─────────────────────────────────────────────────────────────┐
│                    GENE STRUCTURE                            │
├──────────┬──────────┬──────────┬──────────┬────────────────┤
│  Class   │   Eyes   │   Ears   │   Horn   │  Mouth, Back,  │
│  (4 bit) │ (32 bit) │ (32 bit) │ (32 bit) │  Tail (32 bit) │
└──────────┴──────────┴──────────┴──────────┴────────────────┘

Each body part gene contains:
┌──────────┬──────────┬──────────┐
│    D     │    R1    │    R2    │
│(Dominant)│(Recessive│(Recessive│
│          │    1)    │    2)    │
└──────────┴──────────┴──────────┘
```

### 2. Fair Value Model

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
    base = get_floor_price(axie.class_, axie.purity_score)
    trait_value = sum(get_trait_premium(part) for part in axie.dominant_parts)
    synergy = calculate_synergy_bonus(axie.parts)
    meta_multiplier = 1.0 + (get_meta_relevance(axie.parts) * 0.5)
    breed_discount = 1.0 - (axie.breed_count * 0.05)

    return (base + trait_value + synergy) * meta_multiplier * breed_discount
```

### 3. Deal Snatching Pipeline

```
NEW LISTING EVENT
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  1. PARSE LISTING (Lambda - 50ms)                        │
│     • Extract Axie ID, price, seller                     │
│     • Decode genes if not cached                         │
└─────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  2. FAIR VALUE LOOKUP (Redis - 1ms)                      │
│     • Get cached fair value for this gene combo          │
│     • Get current floor for class + purity               │
└─────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  3. DISCOUNT CALCULATION (Lambda - 10ms)                 │
│     • discount = (fair_value - listing_price) / fair_value│
│     • Apply confidence score                             │
└─────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  4. DECISION ENGINE                                      │
│     IF discount > threshold AND confidence > 0.8:        │
│        → ALERT via SNS (Telegram/Discord)                │
└─────────────────────────────────────────────────────────┘

TOTAL LATENCY: < 100ms from listing to alert
```

---

## Meta Shift Detection

### What is "Meta"?

The **meta** refers to the most effective strategies/builds in PvP battles. When the meta shifts:
1. Certain card combinations become dominant
2. Demand for Axies with those parts increases
3. Prices rise for meta-relevant traits
4. **Early detection = arbitrage opportunity**

### Detection Signals

| Signal | Description | Type |
|--------|-------------|------|
| **Win Rate Changes** | Track by part combination | Leading indicator |
| **Price Velocity** | Rate of price change | Lagging indicator |
| **Listing Behavior** | Time-on-market decreasing | Real-time |
| **Volume Spikes** | Unusual trading activity | Real-time |

### ML Features

```python
FEATURES = [
    # Price features (per trait)
    "price_7d_change",
    "price_velocity",
    "price_acceleration",
    "volume_7d",
    "listings_count",
    "time_to_sale_avg",

    # Battle features (if available)
    "win_rate_7d",
    "win_rate_change",
    "usage_rate",

    # Cross-trait features
    "combo_win_rate",
    "class_floor_ratio",
]
```

---

## Database Stack

### Recommended Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  AURORA POSTGRESQL                                               │
│  ─────────────────                                               │
│  • Primary operational database                                  │
│  • Time-series optimized (partitioned tables)                   │
│  • Pre-computed aggregates for fast dashboards                  │
│  • SQL compatibility = easy queries                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  ELASTICACHE REDIS CLUSTER                                       │
│  ─────────────────────────                                       │
│  • Real-time floor prices (1-second updates)                    │
│  • Fair value cache per Axie                                    │
│  • Active listings index                                        │
│  • Sub-millisecond reads for deal detection                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  S3 + PARQUET (DATA LAKE)                                        │
│  ─────────────────────────                                       │
│  • Raw historical data archive                                  │
│  • Partitioned by date for efficient queries                    │
│  • Query via Athena (serverless, pay-per-query)                 │
│  • Feed ML training pipelines                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Breeding Calculator

```
Parent A Genes          Parent B Genes
      │                       │
      └───────────┬───────────┘
                  │
                  ▼
        ┌──────────────┐
        │   Combine    │
        │   Gene Pools │
        └──────────────┘
                  │
                  ▼
        ┌──────────────┐
        │  Calculate   │  D: 37.5%, R1: 9.375%, R2: 3.125%
        │ Probability  │  for each part
        └──────────────┘
                  │
                  ▼
        ┌──────────────┐
        │   Generate   │  Most likely combinations
        │  Outcomes    │  with probabilities
        └──────────────┘
                  │
                  ▼
        ┌──────────────┐
        │   Value      │  Expected value based on
        │  Estimation  │  trait price data
        └──────────────┘
```

---

## Security Considerations

1. **API Keys** - Store in AWS Secrets Manager
2. **Rate Limiting** - Implement on all public endpoints
3. **Input Validation** - Validate wallet addresses, Axie IDs
4. **CORS** - Restrict to known frontend domains
5. **Database** - Use parameterized queries (SQLAlchemy)
6. **IAM Auth** - Passwordless database connections

---

## Scalability Path

```
Phase 1 (MVP)           Phase 2 (Growth)         Phase 3 (Scale)
─────────────           ────────────────         ───────────────
Single server     →     Separate services   →    Kubernetes
PostgreSQL              + Read replicas          + Sharding
In-memory cache         Redis cluster            + CDN
                        Load balancer            + Queue partitioning
```

---

## Implementation Phases

### Phase 1: Foundation (Complete)
- [x] Gene parser
- [x] API clients (Moralis, Sky Mavis)
- [x] Database models
- [x] Basic API endpoints

### Phase 2: Data Pipeline (In Progress)
- [x] PostgreSQL + partitioned tables
- [ ] Kinesis stream ingestion
- [ ] Price tracking jobs
- [ ] Continuous aggregates

### Phase 3: Analytics
- [ ] Historical data backfill
- [ ] Price trend analysis
- [ ] Floor price alerts

### Phase 4: Meta Detection
- [ ] Feature engineering pipeline
- [ ] Train meta detection model
- [ ] Deploy ML inference

### Phase 5: Deal Snatcher
- [ ] Real-time listing monitor
- [ ] Fair value model
- [ ] Alert system (Telegram/Discord)

---

## Related Documentation

- **Infrastructure:** See `docs/INFRASTRUCTURE.md`
- **Database Schema:** See `docs/DATABASE_SCHEMA.md`
- **API Specification:** See `docs/03-api-specification.md`
