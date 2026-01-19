# EC2 Integration Plan for Axie Data Fetching

## Overview

Run long-running data fetch jobs on EC2 instead of local Mac to:
- Allow unattended execution (no sleep/lid issues)
- Lower latency to RDS (same region: us-east-1)
- Reusable infrastructure for future jobs

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        AWS us-east-1                            │
│  ┌─────────────────┐         ┌─────────────────────────────┐   │
│  │   EC2 t3.micro  │────────►│  RDS PostgreSQL             │   │
│  │   Amazon Linux  │  5432   │  cardforum                  │   │
│  │                 │         └─────────────────────────────┘   │
│  │  Python scripts │                                           │
│  │  fetch_*.py     │         ┌─────────────────────────────┐   │
│  │                 │────────►│  Secrets Manager            │   │
│  └────────┬────────┘         │  axie-explorer/api-keys     │   │
│           │                  └─────────────────────────────┘   │
└───────────┼─────────────────────────────────────────────────────┘
            │ HTTPS
            ▼
┌─────────────────────────────────────────────────────────────────┐
│              Sky Mavis API (Singapore)                          │
│              api-gateway.skymavis.com                           │
└─────────────────────────────────────────────────────────────────┘
```

## Existing Resources

| Resource | ID/Name | Status |
|----------|---------|--------|
| AWS Account | 034362054546 | ✓ |
| VPC | vpc-073cdce8e84cbccdc | ✓ Default VPC |
| Subnet | subnet-01095623139ea0f77 | ✓ Public subnet |
| RDS | cardforum | ✓ Publicly accessible |
| RDS Security Group | sg-074f5f4377d8723ff | ✓ Allows 0.0.0.0/0:5432 |
| IAM Role | EC2 | ✓ Needs Secrets Manager |
| Key Pair | cach_excel | ✓ SSH access |
| Secrets | axie-explorer/api-keys | ✓ API keys stored |

## Implementation Steps

### Step 1: IAM Role Update
Add SecretsManagerReadWrite policy to existing "EC2" role.

### Step 2: Security Group
Create `axie-fetcher-sg`:
- Inbound: SSH (22) from current IP
- Outbound: All (for API calls + RDS)

### Step 3: EC2 Instance
- AMI: ami-068c0051b15cdb816 (Amazon Linux 2023)
- Type: t3.micro (free tier, 1 vCPU, 1GB RAM)
- Storage: 8GB gp3
- Auto-install Python, psycopg2 via user data

### Step 4: Deployment Scripts
- `deploy.sh` - Upload scripts to EC2
- `run-job.sh` - Start a fetch job remotely
- `check-job.sh` - Monitor job progress

## Cost Analysis

| Component | Cost |
|-----------|------|
| EC2 t3.micro | $0.0104/hour (~$0.02 per 2-hour job) |
| Storage 8GB | $0.64/month |
| Data transfer | ~$0.09/GB out (minimal) |
| **Per job** | **~$0.03** |
| **Monthly (10 jobs)** | **~$1.00** |

Free tier: 750 hours/month EC2 t2.micro for 12 months

## Files to Create

```
ec2/
├── PLAN.md                 # This file
├── setup/
│   ├── iam-policy.json     # Secrets Manager policy
│   ├── user-data.sh        # EC2 bootstrap script
│   └── security-group.json # SG configuration
├── scripts/
│   ├── deploy.sh           # Deploy scripts to EC2
│   ├── run-job.sh          # Start remote job
│   └── check-job.sh        # Monitor progress
└── config.sh               # EC2 instance details
```

## Usage (After Setup)

```bash
# Deploy latest scripts
./ec2/scripts/deploy.sh

# Run June 2025 fetch job
./ec2/scripts/run-job.sh fetch_june2025_parallel.py

# Check progress
./ec2/scripts/check-job.sh
```
