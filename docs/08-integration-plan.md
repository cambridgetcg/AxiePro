# Integration Plan: Using Existing AWS Infrastructure

## Current State Assessment

### Your Existing Resources

| Resource | Name | Config | Status |
|----------|------|--------|--------|
| **Aurora PostgreSQL** | `op-price-data` | Serverless v2 (0-16 ACU), v16.8 | Available |
| **S3** | `pricedata-tcg` | - | Available |
| **AWS Account** | `034362054546` | `us-east-1` | Active |
| **Vercel** | `cambridgetcg` | - | Active |

### Aurora Cluster Details
```
Endpoint: op-price-data.cluster-cn4c2su0o42n.us-east-1.rds.amazonaws.com
Engine: Aurora PostgreSQL 16.8
Scaling: 0.0 - 16.0 ACU (Serverless v2)
Auto-pause: 900 seconds (15 min idle → scale to zero)
```

---

## Integration Strategy

### Option A: Add Database to Existing Cluster (Recommended)

**Pros:**
- No additional cluster cost
- Share existing Serverless v2 capacity
- Single endpoint to manage
- Already configured VPC/security groups

**Implementation:**
```sql
-- Connect to existing cluster and create new database
CREATE DATABASE axie_explorer;

-- Create dedicated user
CREATE USER axie_admin WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE axie_explorer TO axie_admin;
```

### Option B: Create Separate Cluster

Only if you need complete isolation. Adds ~$100+/month.

---

## Step-by-Step Integration Plan

### Phase 1: Database Setup (Today)

```bash
# 1. Store credentials in Secrets Manager
aws secretsmanager create-secret \
    --name axie-explorer/database \
    --secret-string '{
        "host": "op-price-data.cluster-cn4c2su0o42n.us-east-1.rds.amazonaws.com",
        "port": 5432,
        "database": "axie_explorer",
        "username": "axie_admin",
        "password": "GENERATE_SECURE_PASSWORD"
    }'

# 2. Store API keys
aws secretsmanager create-secret \
    --name axie-explorer/api-keys \
    --secret-string '{
        "MORALIS_API_KEY": "YOUR_KEY",
        "SKYMAVIS_API_KEY": "YOUR_KEY"
    }'
```

### Phase 2: Create Database Schema

Connect to your Aurora cluster and run:

```sql
-- Connect to cluster
-- psql -h op-price-data.cluster-cn4c2su0o42n.us-east-1.rds.amazonaws.com -U postgres

-- Create database
CREATE DATABASE axie_explorer;
\c axie_explorer

-- Enable useful extensions
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- For text search

-- Create partitioned table for price history (instead of TimescaleDB hypertable)
CREATE TABLE price_snapshots (
    time            TIMESTAMPTZ NOT NULL,
    trait_key       TEXT NOT NULL,
    class           TEXT NOT NULL,
    floor_eth       DECIMAL(20,8),
    avg_eth         DECIMAL(20,8),
    volume          INTEGER DEFAULT 0,
    listings_count  INTEGER DEFAULT 0,
    PRIMARY KEY (time, trait_key, class)
) PARTITION BY RANGE (time);

-- Create monthly partitions (auto-create via pg_cron or Lambda)
CREATE TABLE price_snapshots_2025_01 PARTITION OF price_snapshots
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE price_snapshots_2025_02 PARTITION OF price_snapshots
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
-- ... continue for future months

-- Create BRIN index (efficient for time-series)
CREATE INDEX idx_price_snapshots_time_brin ON price_snapshots USING BRIN (time);

-- Create indexes for common queries
CREATE INDEX idx_price_snapshots_trait ON price_snapshots (trait_key);
CREATE INDEX idx_price_snapshots_class ON price_snapshots (class);
```

### Phase 3: Deploy Backend to App Runner

```bash
# 1. Create ECR repository
aws ecr create-repository --repository-name axie-explorer-api

# 2. Build and push Docker image
cd /Users/alex/Ronin_API/backend
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 034362054546.dkr.ecr.us-east-1.amazonaws.com
docker build -t axie-explorer-api .
docker tag axie-explorer-api:latest 034362054546.dkr.ecr.us-east-1.amazonaws.com/axie-explorer-api:latest
docker push 034362054546.dkr.ecr.us-east-1.amazonaws.com/axie-explorer-api:latest

# 3. Create App Runner service (via console or CLI)
```

### Phase 4: Deploy Frontend to Vercel

```bash
# Initialize Next.js frontend
cd /Users/alex/Ronin_API
npx create-next-app@latest frontend --typescript --tailwind --app

# Deploy to Vercel
cd frontend
vercel --prod

# Set environment variable in Vercel
vercel env add NEXT_PUBLIC_API_URL
# Enter: https://your-app-runner-url.us-east-1.awsapprunner.com
```

---

## Architecture Diagram (With Your Infrastructure)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        YOUR AWS ACCOUNT (034362054546)                   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                          VPC (us-east-1)                         │    │
│  │                                                                  │    │
│  │   ┌────────────────────────────────────────────────────────┐    │    │
│  │   │           Aurora Serverless v2 (Existing)              │    │    │
│  │   │           op-price-data cluster                        │    │    │
│  │   │                                                        │    │    │
│  │   │   ┌──────────────┐    ┌──────────────┐                │    │    │
│  │   │   │  op_price    │    │ axie_explorer│  ← NEW         │    │    │
│  │   │   │  (existing)  │    │  (new DB)    │                │    │    │
│  │   │   └──────────────┘    └──────────────┘                │    │    │
│  │   │                                                        │    │    │
│  │   └────────────────────────────────────────────────────────┘    │    │
│  │                              ▲                                   │    │
│  │                              │                                   │    │
│  │   ┌──────────────────────────┼─────────────────────────────┐    │    │
│  │   │                          │                              │    │    │
│  │   │  ┌───────────────┐  ┌────┴────────┐  ┌──────────────┐  │    │    │
│  │   │  │  App Runner   │  │  Lambda     │  │   S3         │  │    │    │
│  │   │  │  (FastAPI)    │  │  (Jobs)     │  │  Data Lake   │  │    │    │
│  │   │  │    NEW        │  │   NEW       │  │  (existing)  │  │    │    │
│  │   │  └───────┬───────┘  └─────────────┘  └──────────────┘  │    │    │
│  │   │          │                                              │    │    │
│  │   └──────────┼──────────────────────────────────────────────┘    │    │
│  │              │                                                   │    │
│  └──────────────┼───────────────────────────────────────────────────┘    │
│                 │                                                         │
│  ┌──────────────┼─────────────────────────────────────────────────────┐  │
│  │              │            Secrets Manager                          │  │
│  │   ┌──────────┴──────────┐  ┌───────────────────┐                  │  │
│  │   │ axie-explorer/      │  │ axie-explorer/    │                  │  │
│  │   │ database            │  │ api-keys          │                  │  │
│  │   └─────────────────────┘  └───────────────────┘                  │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
              │
              │ HTTPS
              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              VERCEL                                      │
│                                                                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                      Next.js Frontend                            │   │
│   │                      (cambridgetcg account)                      │   │
│   │                                                                  │   │
│   │   Env: NEXT_PUBLIC_API_URL=https://app-runner-url...            │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Cost Impact

### Current Costs (Estimated)
Your `op-price-data` cluster is already running, so:

| Item | Additional Cost |
|------|-----------------|
| Aurora (shared cluster) | $0 (already paying) |
| App Runner (1 vCPU) | ~$25-50/mo |
| Secrets Manager (2 secrets) | ~$1/mo |
| Lambda (data jobs) | ~$5-20/mo |
| **Total Additional** | **~$30-70/mo** |

### Future Additions (Phase 2+)
| Item | Cost |
|------|------|
| ElastiCache Redis | ~$50-150/mo |
| Kinesis (real-time) | ~$30-60/mo |

---

## Immediate Next Steps

### 1. Create Secrets (5 min)
```bash
# Get your API keys ready, then run:
aws secretsmanager create-secret \
    --name axie-explorer/api-keys \
    --secret-string '{"MORALIS_API_KEY":"xxx","SKYMAVIS_API_KEY":"xxx"}'
```

### 2. Create Database (10 min)
```bash
# Connect to your Aurora cluster
psql -h op-price-data.cluster-cn4c2su0o42n.us-east-1.rds.amazonaws.com -U postgres -d postgres

# Then run the SQL from Phase 2 above
```

### 3. Run Migration (5 min)
```bash
cd /Users/alex/Ronin_API/backend
export DATABASE_URL="postgresql://axie_admin:PASSWORD@op-price-data.cluster-cn4c2su0o42n.us-east-1.rds.amazonaws.com:5432/axie_explorer"
source venv/bin/activate
alembic upgrade head
```

### 4. Test Locally (5 min)
```bash
# Create local .env with Aurora connection
cp .env.example .env
# Edit .env with your Aurora endpoint

# Run API
uvicorn src.main:app --reload
# Visit http://localhost:8000/docs
```

---

## Questions to Decide

1. **Do you have your Moralis/Sky Mavis API keys yet?**
   - Moralis: https://admin.moralis.io/
   - Sky Mavis: https://developers.skymavis.com/

2. **What's your Aurora master password?** (needed to create the `axie_explorer` database)

3. **Do you want to start with the backend deployment, or frontend first?**
