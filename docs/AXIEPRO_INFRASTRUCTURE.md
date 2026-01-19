succer111# AxiePro.io Infrastructure Overview

**Last Updated:** 2025-12-29
**Status:** Production

---

## Executive Summary

AxiePro.io is a full-stack web application for Axie Infinity market analytics, deployed across Vercel (frontend) and AWS (backend). The architecture follows modern cloud-native patterns with automated CI/CD, secure secrets management, and scalable infrastructure.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AXIEPRO.IO ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   ┌──────────────┐         ┌───────────────────────────────────┐    │
│   │   Vercel     │         │         AWS (us-east-1)           │    │
│   │              │         │                                   │    │
│   │ axiepro.io   │ ──────► │  api.axiepro.io                  │    │
│   │ (Next.js 16) │  HTTPS  │  (App Runner / FastAPI)          │    │
│   │              │         │         │                         │    │
│   └──────────────┘         │         ▼                         │    │
│                            │  ┌─────────────┐  ┌────────────┐  │    │
│   ┌──────────────┐         │  │  RDS        │  │ ElastiCache│  │    │
│   │   GitHub     │         │  │ PostgreSQL  │  │   Redis    │  │    │
│   │              │         │  └─────────────┘  └────────────┘  │    │
│   │ cambridgetcg │ ──────► │                                   │    │
│   │ /AxiePro     │  CI/CD  │  ┌─────────────┐  ┌────────────┐  │    │
│   │              │         │  │   Lambda    │  │    EC2     │  │    │
│   └──────────────┘         │  │  Functions  │  │  (Fetcher) │  │    │
│                            │  └─────────────┘  └────────────┘  │    │
│                            └───────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 1. Repository Structure

**Repository:** https://github.com/cambridgetcg/AxiePro.git
**Branch:** main
**Type:** Monorepo

```
Ronin_API/
├── frontend/                 # Next.js 16 web application
│   ├── src/
│   │   ├── app/             # App router pages
│   │   ├── components/      # React components
│   │   ├── lib/             # API clients, utilities
│   │   ├── hooks/           # React Query hooks
│   │   └── types/           # TypeScript types
│   ├── package.json
│   ├── next.config.ts
│   └── tailwind.config.ts
│
├── backend/                  # FastAPI Python application
│   ├── src/
│   │   ├── api/routes/      # API endpoints (25 routes)
│   │   ├── services/        # Business logic, external clients
│   │   ├── models/          # SQLAlchemy models
│   │   └── config/          # Settings, AWS integration
│   ├── Dockerfile
│   ├── requirements.txt
│   └── infra/cloudformation.yaml
│
├── infrastructure/           # AWS App Runner configs
│   ├── apprunner-service.json
│   ├── apprunner-policy.json
│   └── apprunner-trust-policy.json
│
├── lambda/                   # AWS Lambda functions
│   └── orchestrator/        # EC2 job orchestration
│
├── ec2/                      # EC2 data fetcher setup
│   └── config.sh
│
├── database/                 # PostgreSQL migrations
│   └── migrations/
│
├── docs/                     # Documentation
│
├── .github/workflows/        # CI/CD pipelines
│   └── deploy-backend.yml
│
└── vercel.json              # Vercel deployment config
```

---

## 2. Frontend Hosting (Vercel)

### Technology Stack

| Component | Version | Purpose |
|-----------|---------|---------|
| Next.js | 16.0.10 | React framework with App Router |
| React | 19.2.1 | UI library |
| TanStack Query | 5.90.12 | Data fetching & caching |
| Recharts | 3.6.0 | Data visualization |
| Zustand | 5.0.9 | State management |
| Tailwind CSS | 4.x | Styling |
| TypeScript | 5.x | Type safety |

### Vercel Configuration

**`vercel.json`:**
```json
{
  "buildCommand": "cd frontend && npm run build",
  "outputDirectory": "frontend/.next",
  "installCommand": "cd frontend && npm install",
  "framework": "nextjs"
}
```

**`frontend/next.config.ts`:**
```typescript
const nextConfig: NextConfig = {
  images: {
    unoptimized: true,
  },
  trailingSlash: true,
};
```

### Deployment Flow

```
Git Push (main branch)
         │
         ▼
   Vercel Detects
         │
         ▼
   npm install (frontend/)
         │
         ▼
   next build
         │
         ▼
   Deploy to Edge Network
         │
         ▼
   axiepro.io (LIVE)
```

### Environment Variables

| Variable | Value | Description |
|----------|-------|-------------|
| `NEXT_PUBLIC_API_URL` | `https://api.axiepro.io` | Backend API endpoint |

---

## 3. Backend Hosting (AWS App Runner)

### Technology Stack

| Component | Version | Purpose |
|-----------|---------|---------|
| FastAPI | 0.109.0 | API framework |
| Uvicorn | 0.27.0 | ASGI server |
| SQLAlchemy | 2.0.25 | ORM |
| asyncpg | 0.29.0 | Async PostgreSQL driver |
| Redis | 5.0.1 | Caching client |
| Boto3 | 1.34+ | AWS SDK |

### App Runner Configuration

**Service Name:** `axiepro-api`
**Region:** us-east-1
**Resources:** 1 vCPU, 2 GB RAM

```json
{
  "ServiceName": "axiepro-api",
  "SourceConfiguration": {
    "ImageRepository": {
      "ImageIdentifier": "034362054546.dkr.ecr.us-east-1.amazonaws.com/axiepro-backend:latest",
      "ImageRepositoryType": "ECR",
      "AutoDeploymentsEnabled": true
    }
  },
  "InstanceConfiguration": {
    "Cpu": "1024",
    "Memory": "2048"
  },
  "NetworkConfiguration": {
    "EgressConfiguration": {
      "EgressType": "VPC"
    }
  },
  "HealthCheckConfiguration": {
    "Protocol": "HTTP",
    "Path": "/health",
    "Interval": 10
  }
}
```

### Docker Configuration

**`backend/Dockerfile`:**
```dockerfile
FROM python:3.11-slim as builder
# Multi-stage build
# Non-root user: appuser
# Port: 8000
# Health check: /health
```

### API Endpoints (25 total)

| Route File | Endpoints | Description |
|------------|-----------|-------------|
| `axies.py` | 5 | Search, details, genes, siblings, children |
| `market.py` | 4 | Listings, sales, floor prices, stats |
| `breeding.py` | 3 | Simulate, history, best-pairs |
| `valuation.py` | 10 | Fair value, deals, traits, model info |
| `wallets.py` | 3 | Overview, holdings, trades |

---

## 4. AWS Infrastructure

### AWS Account

**Account ID:** 034362054546
**Region:** us-east-1

### Resource Inventory

| Resource | Name/ID | Purpose |
|----------|---------|---------|
| App Runner | `axiepro-api` | API hosting |
| ECR | `axiepro-backend` | Docker images |
| RDS | `cardforum` (shared) | PostgreSQL database |
| ElastiCache | `axiepro-redis` | Redis cache |
| EC2 | `i-0cbc98fa8fc906281` | Data fetching |
| VPC Connector | `axiepro-vpc-connector` | Private networking |
| Secrets Manager | `axie-explorer/*` | API keys, credentials |

### Database Configuration

**Host:** cardforum.cn4c2su0o42n.us-east-1.rds.amazonaws.com
**Port:** 5432
**Database:** cardforum
**Schema:** axie
**Authentication:** IAM Database Authentication (passwordless)

### Cache Configuration

**Host:** axiepro-redis.jhgio5.0001.use1.cache.amazonaws.com
**Port:** 6379
**Type:** ElastiCache Redis

### IAM Roles

| Role | Purpose |
|------|---------|
| `axiepro-apprunner-instance-role` | App Runner runtime permissions |
| `axiepro-apprunner-ecr-access-role` | ECR image pull |
| `axiepro-lambda-role` | Lambda execution |
| `axiepro-ec2-role` | EC2 instance permissions |

### IAM Policies

```json
{
  "Statement": [
    {
      "Sid": "SecretsManagerAccess",
      "Effect": "Allow",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "arn:aws:secretsmanager:us-east-1:034362054546:secret:axie-explorer/*"
    },
    {
      "Sid": "RDSIAMAuth",
      "Effect": "Allow",
      "Action": "rds-db:connect",
      "Resource": "arn:aws:rds-db:us-east-1:034362054546:dbuser:*/iamuser"
    }
  ]
}
```

---

## 5. CI/CD Pipeline

### Backend Deployment (GitHub Actions)

**Workflow:** `.github/workflows/deploy-backend.yml`

```yaml
name: Deploy Backend to App Runner

on:
  push:
    branches: [main]
    paths: ['backend/**']
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - Checkout code
      - Configure AWS credentials
      - Login to Amazon ECR
      - Build Docker image
      - Push to ECR (latest + SHA tag)
      - Trigger App Runner deployment
      - Wait for completion
```

**Secrets Required:**
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `APPRUNNER_SERVICE_ARN`

### Frontend Deployment (Vercel)

Automatic deployment on git push to main branch. Vercel monitors the repository and triggers builds when changes are detected.

### Deployment Flow

```
Developer Push
      │
      ├─── frontend/** changes ──► Vercel Build ──► axiepro.io
      │
      └─── backend/** changes ──► GitHub Actions
                                        │
                                        ▼
                                  Build Docker Image
                                        │
                                        ▼
                                  Push to ECR
                                        │
                                        ▼
                                  App Runner Deploy
                                        │
                                        ▼
                                  api.axiepro.io
```

---

## 6. Data Pipeline Architecture

### Lambda Functions

| Function | Trigger | Purpose |
|----------|---------|---------|
| `axie-price-ingestion` | EventBridge (5 min) | Floor price snapshots |
| `axie-deal-detector` | Kinesis stream | Real-time deal detection |
| `axie-meta-analyzer` | EventBridge (hourly) | Meta shift analysis |
| `axie-fetch-orchestrator` | EventBridge (hourly) | EC2 job management |

### Pipeline Flow

```
EventBridge (Hourly)
        │
        ▼
Lambda Orchestrator
        │
        ├── Check EC2 state
        ├── Start EC2 if needed
        └── Monitor progress
              │
              ▼
        EC2 Worker
        │
        ├── fetch_continuous.py
        ├── Fetch from Sky Mavis API
        └── Store in RDS
              │
              ▼
        Kinesis Stream
              │
              ▼
        Lambda: Deal Detector
              │
              ▼
        SNS Alerts
```

### CloudFormation Resources

**`backend/infra/cloudformation.yaml`:**
- Kinesis Data Stream (1 shard)
- SNS Topics (deal alerts, meta insights)
- Lambda Functions (3)
- Security Groups
- CloudWatch Dashboard

---

## 7. Domain & DNS

### Domain Configuration

| Domain | Target | Provider |
|--------|--------|----------|
| axiepro.io | Vercel Edge | Vercel DNS |
| api.axiepro.io | App Runner | AWS Route 53 |

### SSL/TLS

- **Frontend:** Automatic via Vercel (Let's Encrypt)
- **Backend:** Automatic via App Runner

---

## 8. Environment Configuration

### Backend Environment Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `DATABASE_URL` | Secrets Manager | PostgreSQL connection |
| `REDIS_URL` | App Runner config | Redis connection |
| `GOLDRUSH_API_KEY` | Secrets Manager | Blockchain data API |
| `SKYMAVIS_API_KEY` | Secrets Manager | Axie marketplace API |
| `USE_IAM_AUTH` | App Runner config | Enable IAM DB auth |
| `AWS_REGION` | App Runner config | us-east-1 |
| `ENVIRONMENT` | App Runner config | production |

### Secrets Management Pattern

```
┌─────────────────────────────────────────────────────┐
│                  Development                         │
│  .env files → Environment Variables                 │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│                    CI/CD                             │
│  GitHub Secrets → Actions Environment               │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│                  Production                          │
│  AWS Secrets Manager → IAM Role → App Runner        │
└─────────────────────────────────────────────────────┘
```

---

## 9. Security Features

| Feature | Implementation |
|---------|----------------|
| IAM Database Auth | Passwordless RDS connections |
| VPC Isolation | Private subnets for DB/cache |
| Non-root Container | App runs as `appuser` |
| Secrets Manager | No hardcoded credentials |
| HTTPS/TLS | All endpoints encrypted |
| Private ECR | Authenticated image pulls |
| Least Privilege | IAM role-based access |

---

## 10. Monitoring & Observability

### CloudWatch Integration

- **Logs:** App Runner, Lambda, EC2
- **Metrics:** CPU, memory, request count, latency
- **Alarms:** Error rates, latency thresholds
- **Dashboard:** Unified view of all components

### Health Checks

| Component | Endpoint | Interval |
|-----------|----------|----------|
| App Runner | `/health` | 10 seconds |
| EC2 Worker | Process status | 5 minutes |
| Lambda | CloudWatch metrics | Per invocation |

---

## 11. Cost Overview

### Current Monthly Estimate

| Service | Cost |
|---------|------|
| RDS (shared) | ~$5 |
| App Runner | ~$25 |
| ElastiCache | ~$12 |
| EC2 (intermittent) | ~$5 |
| **Total** | **~$47/month** |

### After Full Lambda Deployment

| Service | Additional Cost |
|---------|----------------|
| Lambda (scheduled) | ~$5 |
| Kinesis (2 shards) | ~$30 |
| SNS | ~$1 |
| **New Total** | **~$83/month** |

---

## 12. Local Development

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start local services
docker-compose up -d  # PostgreSQL + Redis

# Run API
uvicorn src.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev  # http://localhost:3000
```

### Environment Files

**Backend:** `backend/.env` (copy from `.env.example`)
**Frontend:** `frontend/.env.local` (copy from `.env.example`)

---

## 13. Key File Paths

| Purpose | Path |
|---------|------|
| Git Remote | `.git/config` |
| Vercel Config | `vercel.json` |
| Next.js Config | `frontend/next.config.ts` |
| Backend Entry | `backend/src/main.py` |
| App Settings | `backend/src/config/settings.py` |
| App Runner Config | `infrastructure/apprunner-service.json` |
| CI/CD Workflow | `.github/workflows/deploy-backend.yml` |
| CloudFormation | `backend/infra/cloudformation.yaml` |
| Dockerfile | `backend/Dockerfile` |
| Lambda | `lambda/orchestrator/lambda_function.py` |

---

## 14. Quick Reference

### URLs

| Environment | Frontend | Backend API |
|-------------|----------|-------------|
| Production | https://axiepro.io | https://api.axiepro.io |
| Development | http://localhost:3000 | http://localhost:8000 |

### Commands

```bash
# Deploy backend manually
cd backend && docker build -t axiepro-backend . && docker push ...

# Run frontend build
cd frontend && npm run build

# Check App Runner status
aws apprunner describe-service --service-arn $APPRUNNER_SERVICE_ARN
```

### GitHub Actions

- **Trigger:** Push to `main` with changes in `backend/**`
- **Manual:** "Run workflow" button in Actions tab

---

## Summary

AxiePro.io is a production-ready, cloud-native application with:

- **Modern Frontend:** Next.js 16 on Vercel with React Query and Recharts
- **Scalable Backend:** FastAPI on AWS App Runner with auto-scaling
- **Secure Infrastructure:** IAM auth, VPC isolation, Secrets Manager
- **Automated CI/CD:** GitHub Actions → ECR → App Runner
- **Data Pipeline:** Lambda + EC2 for market data processing
- **Professional Monitoring:** CloudWatch logs, metrics, and dashboards

The architecture follows AWS best practices and is designed for reliability, security, and cost efficiency.
