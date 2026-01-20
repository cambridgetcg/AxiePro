# AxiePro Infrastructure

**Last Updated:** 2025-12-29
**Status:** Production
**AWS Account:** 034362054546
**Region:** us-east-1

---

## Overview

AxiePro.io is a full-stack web application for Axie Infinity market analytics, deployed across Vercel (frontend) and AWS (backend).

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

## Repository Structure

**Repository:** https://github.com/cambridgetcg/AxiePro.git
**Branch:** main
**Type:** Monorepo

```
AxiePro/
├── frontend/                 # Next.js web application
│   ├── src/
│   │   ├── app/             # App router pages
│   │   ├── components/      # React components
│   │   ├── lib/             # API clients, utilities
│   │   ├── hooks/           # React Query hooks
│   │   └── types/           # TypeScript types
│   └── package.json
│
├── backend/                  # FastAPI Python application
│   ├── src/
│   │   ├── api/routes/      # API endpoints (25 routes)
│   │   ├── services/        # Business logic
│   │   ├── models/          # SQLAlchemy models
│   │   └── config/          # Settings
│   ├── Dockerfile
│   └── requirements.txt
│
├── infrastructure/           # AWS CDK (see infrastructure/README.md)
├── lambda/                   # AWS Lambda functions
├── ec2/                      # EC2 data fetcher setup
├── database/                 # PostgreSQL migrations
├── docs/                     # Documentation
└── .github/workflows/        # CI/CD pipelines
```

---

## Technology Stack

### Frontend (Vercel)

| Component | Version | Purpose |
|-----------|---------|---------|
| Next.js | 16.0.10 | React framework with App Router |
| React | 19.2.1 | UI library |
| TanStack Query | 5.90.12 | Data fetching & caching |
| Recharts | 3.6.0 | Data visualization |
| Zustand | 5.0.9 | State management |
| Tailwind CSS | 4.x | Styling |
| TypeScript | 5.x | Type safety |

### Backend (AWS)

| Component | Version | Purpose |
|-----------|---------|---------|
| FastAPI | 0.109.0 | API framework |
| Uvicorn | 0.27.0 | ASGI server |
| SQLAlchemy | 2.0.25 | ORM |
| asyncpg | 0.29.0 | Async PostgreSQL driver |
| Redis | 5.0.1 | Caching client |
| Boto3 | 1.34+ | AWS SDK |

---

## AWS Resource Inventory

### AxiePro Dedicated Resources

| Service | Name/ID | Purpose |
|---------|---------|---------|
| **App Runner** | `axiepro-api` | FastAPI backend hosting |
| **ECR** | `axiepro-backend` | Docker images |
| **ElastiCache** | `axiepro-redis` | Redis cache |
| **EC2** | `i-0cbc98fa8fc906281` | Data fetching jobs |
| **VPC Connector** | `axiepro-vpc-connector` | Private DB access |
| **Secrets Manager** | `axie-explorer/*` | API keys, credentials |

### Shared Resources

| Service | Name | Used By |
|---------|------|---------|
| **RDS PostgreSQL** | `cardforum` | CardForum, AxiePro (schema: `axie`) |
| **VPC** | `vpc-073cdce8e84cbccdc` | Multiple apps |

### Connection Details

| Resource | Endpoint |
|----------|----------|
| **Database** | `cardforum.cn4c2su0o42n.us-east-1.rds.amazonaws.com:5432` |
| **Redis** | `axiepro-redis.jhgio5.0001.use1.cache.amazonaws.com:6379` |
| **API** | `https://api.axiepro.io` |
| **Frontend** | `https://axiepro.io` |

---

## IAM Roles & Policies

| Role | Purpose |
|------|---------|
| `axiepro-apprunner-instance-role` | App Runner runtime permissions |
| `axiepro-apprunner-ecr-access-role` | ECR image pull |
| `axiepro-lambda-role` | Lambda execution |
| `axiepro-ec2-role` | EC2 instance permissions |

**Key Permissions:**
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

## CI/CD Pipeline

### Backend Deployment (GitHub Actions)

**Workflow:** `.github/workflows/deploy-backend.yml`

```
Developer Push (backend/**)
         │
         ▼
   GitHub Actions
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

**Required Secrets:**
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `APPRUNNER_SERVICE_ARN`

### Frontend Deployment (Vercel)

Automatic on git push to main. Vercel monitors repository and triggers builds.

---

## Data Pipeline

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
        Kinesis Stream → Lambda → SNS Alerts
```

---

## Environment Configuration

### Backend Environment Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `DATABASE_URL` | Secrets Manager | PostgreSQL connection |
| `REDIS_URL` | App Runner config | Redis connection |
| `GOLDRUSH_API_KEY` | Secrets Manager | Blockchain data API |
| `SKYMAVIS_API_KEY` | Secrets Manager | Axie marketplace API |
| `USE_IAM_AUTH` | App Runner config | Enable IAM DB auth |
| `ENVIRONMENT` | App Runner config | production |

### Frontend Environment Variables

| Variable | Value | Description |
|----------|-------|-------------|
| `NEXT_PUBLIC_API_URL` | `https://api.axiepro.io` | Backend API endpoint |

---

## Security

| Feature | Implementation |
|---------|----------------|
| IAM Database Auth | Passwordless RDS connections |
| VPC Isolation | Private subnets for DB/cache |
| Non-root Container | App runs as `appuser` |
| Secrets Manager | No hardcoded credentials |
| HTTPS/TLS | All endpoints encrypted |
| Private ECR | Authenticated image pulls |

---

## Monitoring

### CloudWatch Integration

- **Logs:** App Runner, Lambda, EC2
- **Metrics:** CPU, memory, request count, latency
- **Alarms:** Error rates, latency thresholds

### Health Checks

| Component | Endpoint | Interval |
|-----------|----------|----------|
| App Runner | `/health` | 10 seconds |
| EC2 Worker | Process status | 5 minutes |

---

## Cost Overview

### Current Monthly Estimate (~$47)

| Service | Cost |
|---------|------|
| RDS (shared) | ~$5 |
| App Runner | ~$25 |
| ElastiCache | ~$12 |
| EC2 (intermittent) | ~$5 |

### With Full Data Pipeline (~$83)

| Service | Additional Cost |
|---------|----------------|
| Lambda (scheduled) | ~$5 |
| Kinesis (2 shards) | ~$30 |
| SNS | ~$1 |

---

## Local Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev  # http://localhost:3000
```

---

## Resource Tagging

Apply to all AxiePro resources:
```json
{
  "Project": "AxiePro",
  "Environment": "production",
  "Owner": "alex",
  "CostCenter": "axie"
}
```

---

## Related Documentation

- **CDK Infrastructure:** See `infrastructure/README.md` for IaC details
- **Architecture:** See `docs/ARCHITECTURE.md` for system design
- **Database:** See `docs/DATABASE_SCHEMA.md` for schema details
- **API:** See `docs/03-api-specification.md` for endpoints
