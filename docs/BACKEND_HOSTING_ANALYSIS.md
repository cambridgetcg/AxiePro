# Backend Hosting Analysis & Architecture Recommendations

**Date:** 2025-12-29
**Status:** Analysis Complete
**Project:** Axie Ronin Explorer (AxiePro)

---

## Executive Summary

This document analyzes the current AWS implementation status and provides recommendations for backend hosting architecture. The project is a blockchain analytics platform for Axie Infinity with real-time market data, valuation models, and deal detection capabilities.

**Key Finding:** The current App Runner architecture is well-suited for the API workload. For the advanced real-time features (deal snatching, meta detection), a hybrid architecture with Lambda and Kinesis is recommended.

---

## Current AWS Implementation Status

### Deployed Resources

| Resource | Status | Details |
|----------|--------|---------|
| **App Runner** | ✅ Configured | `axiepro-api` service, 1 vCPU, 2GB RAM |
| **ECR Repository** | ✅ Active | `034362054546.dkr.ecr.us-east-1.amazonaws.com/axiepro-backend` |
| **RDS PostgreSQL** | ✅ Running | `cardforum` (SHARED - AxiePro uses `axie` schema) |
| **ElastiCache Redis** | ✅ Running | `axiepro-redis.jhgio5.0001.use1.cache.amazonaws.com:6379` |
| **VPC Connector** | ✅ Configured | `axiepro-vpc-connector` for private DB access |
| **EC2 (Data Jobs)** | ✅ Running | `i-0cbc98fa8fc906281` (t3.micro) at `3.91.12.195` |
| **IAM Roles** | ✅ Configured | ECR access role + instance role |
| **Secrets Manager** | ⚠️ Partial | Keys in env vars (should migrate to Secrets Manager) |
| **CI/CD Pipeline** | ✅ Active | GitHub Actions → ECR → App Runner |

### Architecture Diagram (Current)

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                        AWS us-east-1                     │
┌────────────┐      │                                                         │
│   Users    │      │  ┌─────────────────────────────────────────────────┐   │
└─────┬──────┘      │  │              VPC                                 │   │
      │             │  │                                                  │   │
      ▼             │  │   ┌──────────────┐    ┌──────────────────────┐  │   │
┌────────────┐      │  │   │ App Runner   │    │   RDS PostgreSQL     │  │   │
│  Vercel    │──────┼──┼──▶│ axiepro-api  │───▶│   cardforum (SHARED) │  │   │
│ (Next.js)  │      │  │   │ 1vCPU/2GB    │    │   schema: axie       │  │   │
└────────────┘      │  │   └──────────────┘    └──────────────────────┘  │   │
                    │  │          │                                       │   │
                    │  │          ▼                                       │   │
                    │  │   ┌──────────────┐                               │   │
                    │  │   │ ElastiCache  │                               │   │
                    │  │   │ Redis        │                               │   │
                    │  │   └──────────────┘                               │   │
                    │  │                                                  │   │
                    │  │   ┌──────────────┐                               │   │
                    │  │   │ EC2 t3.micro │  ← Data fetching jobs         │   │
                    │  │   │ 3.91.12.195  │                               │   │
                    │  │   └──────────────┘                               │   │
                    │  └─────────────────────────────────────────────────┘   │
                    └─────────────────────────────────────────────────────────┘

GitHub Actions → ECR → App Runner (Auto-deploy on push to main)
```

### Configuration Files

| File | Purpose | Status |
|------|---------|--------|
| `infrastructure/apprunner-service.json` | App Runner service definition | ✅ Complete |
| `infrastructure/apprunner-policy.json` | IAM policy for Secrets Manager + RDS | ✅ Complete |
| `infrastructure/apprunner-trust-policy.json` | Trust policy for App Runner | ✅ Complete |
| `.github/workflows/deploy-backend.yml` | CI/CD pipeline | ✅ Complete |
| `backend/Dockerfile` | Multi-stage build | ✅ Complete |
| `ec2/config.sh` | EC2 instance configuration | ✅ Complete |

---

## Hosting Options Analysis

### Option 1: AWS App Runner (Current)

**Best for:** Simple API workloads, auto-scaling, managed infrastructure

| Pros | Cons |
|------|------|
| ✅ Fully managed, no ops overhead | ❌ Limited customization |
| ✅ Auto-scaling (0 to N instances) | ❌ Cold start latency (~2-5s) |
| ✅ Built-in health checks & rollbacks | ❌ No GPU support |
| ✅ Native ECR integration | ❌ Max 25 vCPU per service |
| ✅ VPC connector for private resources | ❌ No persistent storage |
| ✅ Pay per vCPU-second (cost-effective) | |

**Cost:** ~$25-50/month for low-medium traffic

**Verdict:** ✅ **KEEP for API workload** - Perfect fit for the FastAPI backend

---

### Option 2: AWS ECS Fargate

**Best for:** Container orchestration without managing servers

| Pros | Cons |
|------|------|
| ✅ More control than App Runner | ❌ More complex setup |
| ✅ Task definitions for fine-tuning | ❌ Requires ALB for HTTPS |
| ✅ Service discovery | ❌ Higher baseline cost |
| ✅ Spot capacity for savings | |
| ✅ Better logging/monitoring | |

**Cost:** ~$40-80/month (includes ALB)

**Verdict:** Consider for **future scaling** if App Runner limits are hit

---

### Option 3: AWS Lambda + API Gateway

**Best for:** Event-driven, sporadic workloads

| Pros | Cons |
|------|------|
| ✅ True serverless, pay-per-invocation | ❌ 15-minute timeout |
| ✅ Scales to thousands concurrent | ❌ Cold starts problematic |
| ✅ Perfect for scheduled jobs | ❌ 10GB memory limit |
| ✅ Native event triggers | ❌ No persistent connections |

**Cost:** ~$5-20/month for API, more for heavy compute

**Verdict:** ✅ **USE for scheduled jobs** (price ingestion, deal detection)

---

### Option 4: EC2 (Self-managed)

**Best for:** Long-running processes, full control

| Pros | Cons |
|------|------|
| ✅ Full control | ❌ Ops overhead (patching, scaling) |
| ✅ Persistent storage | ❌ Manual scaling |
| ✅ Any instance type | ❌ Pay even when idle |
| ✅ Spot instances (70% savings) | |

**Cost:** t3.micro ~$7.50/month, t3.medium ~$30/month

**Verdict:** ✅ **KEEP for data fetching jobs** (already running)

---

### Option 5: AWS EKS (Kubernetes)

**Best for:** Large-scale, multi-service architectures

| Pros | Cons |
|------|------|
| ✅ Industry standard | ❌ Complex, high learning curve |
| ✅ Portable (not locked to AWS) | ❌ $72/month just for control plane |
| ✅ Advanced scheduling | ❌ Overkill for this project |

**Cost:** ~$100-200/month minimum

**Verdict:** ❌ **NOT RECOMMENDED** - Overkill for current scale

---

## Recommended Architecture

### Hybrid Architecture (Recommended)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              AWS us-east-1                                       │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                           API LAYER                                         │ │
│  │                                                                             │ │
│  │   ┌──────────────────────────────────────────────────────────────────┐    │ │
│  │   │                    AWS App Runner                                 │    │ │
│  │   │                    axiepro-api                                    │    │ │
│  │   │                                                                   │    │ │
│  │   │   FastAPI Backend                                                │    │ │
│  │   │   • /api/v1/axies     - Search & details                        │    │ │
│  │   │   • /api/v1/market    - Listings & sales                        │    │ │
│  │   │   • /api/v1/breeding  - Breeding simulator                      │    │ │
│  │   │   • /api/v1/valuation - Fair value & deals                      │    │ │
│  │   │   • /health           - Health checks                           │    │ │
│  │   └──────────────────────────────────────────────────────────────────┘    │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                           │
│                                      ▼                                           │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                         DATA LAYER                                          │ │
│  │                                                                             │ │
│  │   ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     │ │
│  │   │ RDS PostgreSQL  │     │ ElastiCache     │     │ S3 Data Lake    │     │ │
│  │   │ + TimescaleDB   │     │ Redis           │     │ (Future)        │     │ │
│  │   │                 │     │                 │     │                 │     │ │
│  │   │ • axies         │     │ • floor_prices  │     │ • Historical    │     │ │
│  │   │ • listings      │     │ • listings      │     │ • Parquet files │     │ │
│  │   │ • sales         │     │ • fair_values   │     │ • Athena query  │     │ │
│  │   │ • trait_prices  │     │ • sessions      │     │                 │     │ │
│  │   └─────────────────┘     └─────────────────┘     └─────────────────┘     │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                           │
│                                      ▼                                           │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                    BACKGROUND PROCESSING LAYER                              │ │
│  │                                                                             │ │
│  │   ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     │ │
│  │   │ Lambda          │     │ Lambda          │     │ EC2 t3.micro    │     │ │
│  │   │ price_ingestion │     │ deal_detector   │     │ batch_processor │     │ │
│  │   │                 │     │                 │     │                 │     │ │
│  │   │ Trigger:        │     │ Trigger:        │     │ Jobs:           │     │ │
│  │   │ EventBridge     │     │ EventBridge or  │     │ • Gap backfill  │     │ │
│  │   │ (every 5 min)   │     │ Kinesis stream  │     │ • Historical    │     │ │
│  │   │                 │     │                 │     │ • Metadata sync │     │ │
│  │   └─────────────────┘     └─────────────────┘     └─────────────────┘     │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                    REAL-TIME LAYER (Future)                                 │ │
│  │                                                                             │ │
│  │   ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     │ │
│  │   │ Kinesis Data    │────▶│ Lambda          │────▶│ SNS/SQS         │     │ │
│  │   │ Streams         │     │ deal_processor  │     │ Alerts          │     │ │
│  │   │                 │     │                 │     │                 │     │ │
│  │   │ Events:         │     │ < 100ms         │     │ • Telegram      │     │ │
│  │   │ • listing.new   │     │ latency         │     │ • Discord       │     │ │
│  │   │ • listing.sold  │     │                 │     │ • Email         │     │ │
│  │   └─────────────────┘     └─────────────────┘     └─────────────────┘     │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────┐
│                              EXTERNAL                                             │
│                                                                                   │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│   │ Sky Mavis   │  │ Covalent    │  │ Moralis     │  │ Ronin RPC   │            │
│   │ GraphQL     │  │ Goldrush    │  │ API         │  │ (Public)    │            │
│   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                                   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Progress Tracker

### Phase 1: Core Infrastructure ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| AWS Account Setup | ✅ | Account 034362054546 |
| VPC + Subnets | ✅ | Default VPC with public subnets |
| RDS PostgreSQL | ✅ | cardforum instance running |
| ElastiCache Redis | ✅ | axiepro-redis cluster running |
| ECR Repository | ✅ | axiepro-backend repository |
| App Runner Service | ✅ | axiepro-api configured |
| VPC Connector | ✅ | Private access to RDS/Redis |
| IAM Roles | ✅ | ECR access + instance roles |
| GitHub Actions CI/CD | ✅ | Auto-deploy on push |

### Phase 2: Backend Application ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| FastAPI Application | ✅ | src/main.py |
| API Routes | ✅ | axies, market, breeding, wallets, valuation |
| Database Models | ✅ | SQLAlchemy + Alembic migrations |
| External API Clients | ✅ | SkyMavis, Goldrush, Moralis, Ronin RPC |
| Gene Parser | ✅ | 256-bit hex decoding |
| Valuation Model | ✅ | Hedonic pricing implementation |
| Docker Build | ✅ | Multi-stage Dockerfile |
| Health Checks | ✅ | /health endpoint |

### Phase 3: Data Pipeline 🔄 IN PROGRESS

| Task | Status | Notes |
|------|--------|-------|
| Sales Data Backfill | 🔄 | Gap backfill running on EC2 |
| Metadata Sync | 🔄 | Batch processor implemented |
| TimescaleDB Extension | ⏳ | Planned for trait_prices |
| Continuous Aggregates | ⏳ | For hourly/daily rollups |
| Price Snapshots Lambda | ⏳ | 5-minute ingestion |

### Phase 4: Real-Time Features ⏳ PLANNED

| Task | Status | Notes |
|------|--------|-------|
| Kinesis Data Stream | ⏳ | For marketplace events |
| Deal Detection Lambda | ⏳ | Sub-100ms processing |
| Alert System (SNS) | ⏳ | Telegram/Discord integration |
| WebSocket Notifications | ⏳ | Real-time frontend updates |

### Phase 5: Advanced Analytics ⏳ PLANNED

| Task | Status | Notes |
|------|--------|-------|
| S3 Data Lake | ⏳ | Historical data archive |
| Athena Queries | ⏳ | Ad-hoc analytics |
| Meta Detection ML | ⏳ | SageMaker deployment |
| Grafana Dashboards | ⏳ | Monitoring & visualization |

---

## Cost Projections

### Current Monthly Cost (MVP)

| Service | Configuration | Cost |
|---------|--------------|------|
| RDS PostgreSQL | db.t3.micro (assumed) | ~$15 |
| App Runner | 1 vCPU, 2GB, low traffic | ~$25 |
| ElastiCache Redis | cache.t3.micro | ~$12 |
| EC2 (data jobs) | t3.micro, intermittent | ~$5 |
| Data Transfer | Minimal | ~$2 |
| **Total** | | **~$59/month** |

### Projected Cost (Full Features)

| Service | Configuration | Cost |
|---------|--------------|------|
| RDS PostgreSQL | db.t3.small + TimescaleDB | ~$30 |
| App Runner | 1-2 vCPU, auto-scaling | ~$50 |
| ElastiCache Redis | cache.t3.medium | ~$50 |
| Lambda (scheduled) | ~1M invocations | ~$20 |
| Kinesis (real-time) | 2 shards | ~$30 |
| S3 + Athena | 50GB + queries | ~$10 |
| SNS/SQS | Alerts | ~$5 |
| **Total** | | **~$195/month** |

### Cost Optimization Opportunities

1. **Reserved Instances** - 30-40% savings on RDS/ElastiCache
2. **Spot Instances** - 70% savings on EC2 batch jobs
3. **Aurora Serverless v2** - Scale to zero when idle
4. **S3 Intelligent Tiering** - Auto-optimize storage class
5. **Lambda Graviton** - 20% cheaper ARM processors

---

## Security Checklist

| Item | Status | Action Needed |
|------|--------|---------------|
| Secrets in Secrets Manager | ⚠️ | Migrate from env vars |
| RDS not publicly accessible | ⚠️ | Currently public, should use VPC only |
| IAM least privilege | ✅ | Roles properly scoped |
| VPC security groups | ✅ | Configured for App Runner |
| HTTPS/TLS | ✅ | App Runner provides SSL |
| API rate limiting | ⏳ | Implement in FastAPI |
| WAF protection | ⏳ | Consider for production |
| CloudWatch logging | ⏳ | Enable detailed logging |
| Backup/DR strategy | ⏳ | Configure RDS snapshots |

---

## Recommendations Summary

### Immediate Actions (This Week)

1. **Migrate secrets to Secrets Manager** - Remove hardcoded credentials from apprunner-service.json
2. **Restrict RDS access** - Remove public accessibility, use VPC connector only
3. **Enable RDS automated backups** - Daily snapshots with 7-day retention
4. **Set up CloudWatch alarms** - CPU, memory, error rates

### Short-Term (Next 2-4 Weeks)

1. **Deploy price ingestion Lambda** - Scheduled every 5 minutes
2. **Enable TimescaleDB** - Install extension on RDS
3. **Create continuous aggregates** - Hourly/daily price rollups
4. **Implement API rate limiting** - Protect against abuse

### Medium-Term (1-2 Months)

1. **Kinesis stream setup** - Real-time marketplace events
2. **Deal detection Lambda** - Sub-100ms processing
3. **Alert system (SNS → Telegram)** - Notify on deals
4. **S3 data lake** - Archive historical data

### Long-Term (3+ Months)

1. **Meta detection ML model** - SageMaker deployment
2. **Grafana dashboards** - Advanced visualization
3. **Multi-region DR** - Aurora Global Database
4. **Auto-buy integration** - Smart contract execution

---

## Conclusion

The current App Runner + RDS + ElastiCache architecture is appropriate for the API workload and provides a solid foundation. The recommended hybrid approach adds Lambda for scheduled/event-driven tasks and Kinesis for real-time processing, enabling the advanced deal detection features without over-engineering the core infrastructure.

**Priority Focus:**
1. Complete data pipeline (backfill + continuous sync)
2. Implement real-time deal detection (Kinesis + Lambda)
3. Security hardening (Secrets Manager migration, RDS access restriction)

The architecture can scale from the current ~$60/month MVP to a full-featured platform at ~$200/month while maintaining operational simplicity through managed AWS services.
