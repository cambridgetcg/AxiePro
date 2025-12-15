# System Architecture

## Overview

The Axie Ronin Explorer follows a three-tier architecture with clear separation between data ingestion, business logic, and presentation layers.

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
│   │                                                                      │   │
│   │  ┌────────────────────────────────────────────────────────────┐    │   │
│   │  │                      REST API Routes                        │    │   │
│   │  │  /axies  /market  /breeding  /analytics  /wallet  /alerts  │    │   │
│   │  └────────────────────────────────────────────────────────────┘    │   │
│   │                              │                                      │   │
│   │  ┌────────────────────────────────────────────────────────────┐    │   │
│   │  │                    Service Layer                            │    │   │
│   │  │  AxieService  MarketService  BreedingService  WalletService │    │   │
│   │  └────────────────────────────────────────────────────────────┘    │   │
│   │                              │                                      │   │
│   │  ┌────────────────────────────────────────────────────────────┐    │   │
│   │  │                    Utility Layer                            │    │   │
│   │  │    GeneParser    PriceCalculator    TraitAnalyzer          │    │   │
│   │  └────────────────────────────────────────────────────────────┘    │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                      Background Workers (Celery)                     │   │
│   │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                │   │
│   │  │ Marketplace  │ │    Price     │ │    Axie      │                │   │
│   │  │   Indexer    │ │   Tracker    │ │   Syncer     │                │   │
│   │  └──────────────┘ └──────────────┘ └──────────────┘                │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                DATA LAYER                                    │
│                                                                              │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────────┐ │
│   │  PostgreSQL  │    │    Redis     │    │      External APIs           │ │
│   │ + TimescaleDB│    │    Cache     │    │                              │ │
│   │              │    │              │    │  ┌────────┐ ┌─────────────┐  │ │
│   │ - axies      │    │ - listings   │    │  │Moralis │ │ Sky Mavis   │  │ │
│   │ - sales      │    │ - prices     │    │  │  API   │ │  GraphQL    │  │ │
│   │ - prices     │    │ - sessions   │    │  └────────┘ └─────────────┘  │ │
│   │ - wallets    │    │              │    │                              │ │
│   └──────────────┘    └──────────────┘    │  ┌────────┐ ┌─────────────┐  │ │
│                                           │  │Ronin   │ │ Chainstack  │  │ │
│                                           │  │  RPC   │ │    RPC      │  │ │
│                                           │  └────────┘ └─────────────┘  │ │
│                                           └──────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Data Ingestion Pipeline

The system continuously ingests data from multiple sources:

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA INGESTION FLOW                          │
└─────────────────────────────────────────────────────────────────┘

  Sky Mavis GraphQL                    Moralis API
        │                                   │
        │ Axie metadata                     │ NFT transfers
        │ Marketplace listings              │ Wallet balances
        │ Gene data                         │ Token prices
        ▼                                   ▼
┌──────────────┐                   ┌──────────────┐
│   GraphQL    │                   │   REST API   │
│   Client     │                   │   Client     │
└──────────────┘                   └──────────────┘
        │                                   │
        └─────────────┬─────────────────────┘
                      │
                      ▼
              ┌──────────────┐
              │  Data        │
              │  Normalizer  │
              └──────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
┌──────────────┐ ┌──────────┐ ┌──────────┐
│  PostgreSQL  │ │  Redis   │ │  Event   │
│   (persist)  │ │ (cache)  │ │  Queue   │
└──────────────┘ └──────────┘ └──────────┘
```

### 2. Gene Parsing System

Axie genes are stored as 256-bit integers. The parser decodes them into readable traits:

```
Gene Hex: 0x0000000000000000300c3...

┌─────────────────────────────────────────────────────────────┐
│                    GENE STRUCTURE                            │
├──────────┬──────────┬──────────┬──────────┬────────────────┤
│  Class   │   Eyes   │   Ears   │   Horn   │  Mouth, Back,  │
│  (4 bit) │ (32 bit) │ (32 bit) │ (32 bit) │  Tail (each    │
│          │          │          │          │   32 bit)      │
└──────────┴──────────┴──────────┴──────────┴────────────────┘

Each body part gene contains:
┌──────────┬──────────┬──────────┐
│    D     │    R1    │    R2    │
│(Dominant)│(Recessive│(Recessive│
│          │    1)    │    2)    │
└──────────┴──────────┴──────────┘
```

### 3. Price Analytics Engine

```
┌─────────────────────────────────────────────────────────────┐
│                 PRICE ANALYSIS PIPELINE                      │
└─────────────────────────────────────────────────────────────┘

Raw Sales Data
      │
      ▼
┌──────────────┐
│   Filter     │ Remove outliers, wash trades
│   & Clean    │
└──────────────┘
      │
      ▼
┌──────────────┐
│   Trait      │ Group by class, body parts, purity
│   Grouping   │
└──────────────┘
      │
      ▼
┌──────────────┐
│   Time       │ 1h, 24h, 7d, 30d aggregations
│   Windows    │
└──────────────┘
      │
      ▼
┌──────────────┐
│   Metrics    │ Floor, median, avg, volume
│   Calc       │
└──────────────┘
      │
      ▼
┌──────────────┐
│ TimescaleDB  │ Store as hypertable
│   Storage    │
└──────────────┘
```

### 4. Breeding Probability Calculator

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

## Infrastructure

### Development Environment

```yaml
# docker-compose.yml
services:
  db:
    image: timescale/timescaledb:latest-pg15
    ports: ["5432:5432"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  backend:
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [db, redis]

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [backend]

  celery:
    build: ./backend
    command: celery -A src.worker worker
    depends_on: [db, redis]
```

### Production Considerations

| Component | Recommendation |
|-----------|----------------|
| Database | Managed PostgreSQL (Supabase, RDS, Neon) with TimescaleDB |
| Cache | Redis Cloud or Upstash |
| Backend | Railway, Render, or AWS ECS |
| Frontend | Vercel (optimized for Next.js) |
| Workers | Separate container/service for Celery |

## Security Considerations

1. **API Keys** - Store in environment variables, never commit
2. **Rate Limiting** - Implement on all public endpoints
3. **Input Validation** - Validate wallet addresses, Axie IDs
4. **CORS** - Restrict to known frontend domains
5. **Database** - Use parameterized queries (SQLAlchemy handles this)

## Scalability Path

```
Phase 1 (MVP)           Phase 2 (Growth)         Phase 3 (Scale)
─────────────           ────────────────         ───────────────
Single server     →     Separate services   →    Kubernetes
SQLite/Postgres         + Read replicas          + Sharding
In-memory cache         Redis cluster            + CDN
                        Load balancer            + Queue partitioning
```
