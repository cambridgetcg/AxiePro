# Deployment Guide: Vercel + AWS

## Architecture Overview

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                        AWS                               │
┌────────────┐      │                                                         │
│   Users    │      │  ┌─────────────────────────────────────────────────┐   │
└─────┬──────┘      │  │              VPC                                 │   │
      │             │  │                                                  │   │
      ▼             │  │   ┌──────────────┐    ┌──────────────────────┐  │   │
┌────────────┐      │  │   │ App Runner   │    │   RDS PostgreSQL     │  │   │
│  Vercel    │──────┼──┼──▶│ (FastAPI)    │───▶│   + TimescaleDB      │  │   │
│ (Next.js)  │      │  │   │              │    │                      │  │   │
└────────────┘      │  │   └──────────────┘    └──────────────────────┘  │   │
                    │  │          │                                       │   │
                    │  │          ▼                                       │   │
                    │  │   ┌──────────────┐                               │   │
                    │  │   │ ElastiCache  │                               │   │
                    │  │   │   (Redis)    │                               │   │
                    │  │   └──────────────┘                               │   │
                    │  │                                                  │   │
                    │  │   ┌──────────────┐                               │   │
                    │  │   │   Secrets    │                               │   │
                    │  │   │   Manager    │                               │   │
                    │  │   └──────────────┘                               │   │
                    │  └─────────────────────────────────────────────────┘   │
                    └─────────────────────────────────────────────────────────┘
```

---

## Step 1: AWS Setup

### 1.1 Create Secrets in AWS Secrets Manager

```bash
# Install AWS CLI if not already installed
# https://aws.amazon.com/cli/

# Configure AWS credentials
aws configure

# Create the secret
aws secretsmanager create-secret \
    --name axie-explorer/api-keys \
    --description "API keys for Axie Ronin Explorer" \
    --secret-string '{
        "MORALIS_API_KEY": "your-moralis-api-key-here",
        "SKYMAVIS_API_KEY": "your-skymavis-api-key-here"
    }'
```

### 1.2 Create RDS PostgreSQL Database

**Option A: AWS Console**
1. Go to RDS → Create Database
2. Choose PostgreSQL 15
3. Select "Free tier" or appropriate size
4. Set master username/password
5. Enable "Public access" for initial setup (disable later)
6. Note the endpoint URL

**Option B: AWS CLI**
```bash
aws rds create-db-instance \
    --db-instance-identifier axie-explorer-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 15.4 \
    --master-username axie_admin \
    --master-user-password "YOUR_SECURE_PASSWORD" \
    --allocated-storage 20 \
    --publicly-accessible
```

After creation, add DATABASE_URL to Secrets Manager:
```bash
aws secretsmanager put-secret-value \
    --secret-id axie-explorer/api-keys \
    --secret-string '{
        "MORALIS_API_KEY": "...",
        "SKYMAVIS_API_KEY": "...",
        "DATABASE_URL": "postgresql://axie_admin:PASSWORD@your-rds-endpoint:5432/axie_explorer"
    }'
```

### 1.3 Create ElastiCache Redis (Optional)

For caching and Celery task queue:

```bash
aws elasticache create-cache-cluster \
    --cache-cluster-id axie-explorer-cache \
    --cache-node-type cache.t3.micro \
    --engine redis \
    --num-cache-nodes 1
```

---

## Step 2: Deploy Backend to AWS App Runner

### 2.1 Create Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run with uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2.2 Push to ECR

```bash
# Create ECR repository
aws ecr create-repository --repository-name axie-explorer-api

# Get login credentials
aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Build and push
cd backend
docker build -t axie-explorer-api .
docker tag axie-explorer-api:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/axie-explorer-api:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/axie-explorer-api:latest
```

### 2.3 Create App Runner Service

```bash
aws apprunner create-service \
    --service-name axie-explorer-api \
    --source-configuration '{
        "ImageRepository": {
            "ImageIdentifier": "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/axie-explorer-api:latest",
            "ImageRepositoryType": "ECR",
            "ImageConfiguration": {
                "Port": "8000",
                "RuntimeEnvironmentVariables": {
                    "USE_AWS_SECRETS": "true",
                    "AWS_REGION": "us-east-1",
                    "AWS_SECRET_NAME": "axie-explorer/api-keys"
                }
            }
        },
        "AutoDeploymentsEnabled": true
    }' \
    --instance-configuration '{
        "Cpu": "1024",
        "Memory": "2048"
    }'
```

### 2.4 Grant App Runner Access to Secrets

Create IAM role with this policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:axie-explorer/*"
        }
    ]
}
```

---

## Step 3: Deploy Frontend to Vercel

### 3.1 Initialize Next.js Frontend

```bash
cd /Users/alex/Ronin_API
npx create-next-app@latest frontend --typescript --tailwind --app
cd frontend
```

### 3.2 Configure Environment Variables in Vercel

In Vercel Dashboard → Project Settings → Environment Variables:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | `https://your-app-runner-url.us-east-1.awsapprunner.com` |

### 3.3 Deploy to Vercel

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
cd frontend
vercel

# Follow prompts to link to your Vercel account
```

---

## Step 4: Run Database Migrations

Connect to your RDS instance and run migrations:

```bash
# Set DATABASE_URL to your RDS endpoint
export DATABASE_URL="postgresql://axie_admin:PASSWORD@your-rds-endpoint:5432/axie_explorer"

cd backend
source venv/bin/activate
alembic upgrade head
```

---

## Environment Variables Summary

### Backend (AWS App Runner)
| Variable | Description | Where Stored |
|----------|-------------|--------------|
| `USE_AWS_SECRETS` | Enable AWS Secrets Manager | App Runner config |
| `AWS_REGION` | AWS region | App Runner config |
| `AWS_SECRET_NAME` | Secret name in Secrets Manager | App Runner config |
| `MORALIS_API_KEY` | Moralis API key | Secrets Manager |
| `SKYMAVIS_API_KEY` | Sky Mavis API key | Secrets Manager |
| `DATABASE_URL` | PostgreSQL connection string | Secrets Manager |
| `REDIS_URL` | Redis connection string | Secrets Manager |

### Frontend (Vercel)
| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend API URL |

---

## Cost Estimate (Monthly)

| Service | Tier | Est. Cost |
|---------|------|-----------|
| **RDS PostgreSQL** | db.t3.micro | ~$15 |
| **App Runner** | 1 vCPU, 2GB | ~$25 |
| **ElastiCache** | cache.t3.micro | ~$12 |
| **Secrets Manager** | 2 secrets | ~$1 |
| **Vercel** | Hobby | Free |
| **Total** | | ~$53/month |

For production scale, costs increase with:
- Larger RDS instance
- Multiple App Runner instances
- Data transfer

---

## Security Checklist

- [ ] RDS not publicly accessible (use VPC)
- [ ] Secrets in Secrets Manager, not env vars
- [ ] App Runner IAM role has minimal permissions
- [ ] Enable RDS encryption at rest
- [ ] Enable CloudWatch logging
- [ ] Set up AWS WAF for API protection
- [ ] Configure CORS for your domain only
- [ ] Enable Vercel protection rules
