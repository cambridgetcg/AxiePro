# AWS Resources Inventory for AxiePro

**Last Updated:** 2025-12-29
**AWS Account:** 034362054546
**Region:** us-east-1

---

## Resource Ownership Summary

| Resource Type | Dedicated to AxiePro | Shared | Notes |
|--------------|---------------------|--------|-------|
| App Runner | `axiepro-api` | - | AxiePro only |
| ECR | `axiepro-backend` | - | AxiePro only |
| ElastiCache | `axiepro-redis` | - | AxiePro only |
| RDS | - | `cardforum` | Shared with card trading app |
| EC2 | `axiepro-ec2-fetcher` | - | AxiePro data jobs |
| Secrets Manager | `axie-explorer/*` | - | AxiePro only |
| IAM Roles | `axiepro-*` | `EC2` (generic) | Mixed |

---

## AxiePro Dedicated Resources

### Compute

| Service | Name | ID/ARN | Purpose |
|---------|------|--------|---------|
| **App Runner** | `axiepro-api` | `arn:aws:apprunner:us-east-1:034362054546:service/axiepro-api/*` | FastAPI backend |
| **EC2** | `axiepro-ec2-fetcher` | `i-0cbc98fa8fc906281` | Data fetching jobs |

### Container Registry

| Service | Name | URI | Purpose |
|---------|------|-----|---------|
| **ECR** | `axiepro-backend` | `034362054546.dkr.ecr.us-east-1.amazonaws.com/axiepro-backend` | Docker images |

### Cache

| Service | Name | Endpoint | Purpose |
|---------|------|----------|---------|
| **ElastiCache** | `axiepro-redis` | `axiepro-redis.jhgio5.0001.use1.cache.amazonaws.com:6379` | Caching, sessions |

### Networking

| Service | Name | ID | Purpose |
|---------|------|-----|---------|
| **VPC Connector** | `axiepro-vpc-connector` | `arn:aws:apprunner:us-east-1:034362054546:vpcconnector/axiepro-vpc-connector/1/*` | Private DB access |

### Secrets

| Service | Name | Purpose |
|---------|------|---------|
| **Secrets Manager** | `axie-explorer/api-keys` | API keys (Goldrush, SkyMavis) |

### IAM

| Role Name | Purpose | Needs Rename? |
|-----------|---------|---------------|
| `axiepro-apprunner-ecr-access-role` | App Runner ECR pull | No |
| `axiepro-apprunner-instance-role` | App Runner runtime | No |

---

## Shared Resources (Multi-App)

### Database

| Service | Name | Endpoint | Apps Using |
|---------|------|----------|------------|
| **RDS PostgreSQL** | `cardforum` | `cardforum.cn4c2su0o42n.us-east-1.rds.amazonaws.com:5432` | CardForum, **AxiePro** |

**AxiePro Database Usage:**
- Database: `postgres` (shared instance)
- Schema: `axie` (dedicated schema for AxiePro data)
- Tables: `axie.axies`, `axie.sales`, `axie.listings`, `axie.sync_state`, etc.

### IAM (Generic)

| Role Name | Purpose | Apps Using |
|-----------|---------|------------|
| `EC2` | Generic EC2 instance role | Multiple apps |

### Networking (Shared VPC)

| Resource | ID | Notes |
|----------|-----|-------|
| VPC | `vpc-073cdce8e84cbccdc` | Default VPC |
| Subnet | `subnet-01095623139ea0f77` | Public subnet |
| Security Group | `sg-05c5101c555c59f9c` | EC2 access |
| Security Group | `sg-074f5f4377d8723ff` | RDS access (0.0.0.0/0:5432) |

---

## Naming Convention

**Pattern:** `axiepro-<resource-type>[-<qualifier>]`

### Examples:
```
axiepro-api              # App Runner service
axiepro-backend          # ECR repository
axiepro-redis            # ElastiCache cluster
axiepro-ec2-fetcher      # EC2 instance for data jobs
axiepro-sg-apprunner     # Security group for App Runner
axiepro-lambda-price     # Lambda for price ingestion (future)
axiepro-kinesis-events   # Kinesis stream (future)
```

### Tags (apply to all AxiePro resources):
```json
{
  "Project": "AxiePro",
  "Environment": "production",
  "Owner": "alex",
  "CostCenter": "axie"
}
```

---

## Actions Needed

### 1. Add Name Tag to EC2 Instance
```bash
aws ec2 create-tags \
  --resources i-0cbc98fa8fc906281 \
  --tags Key=Name,Value=axiepro-ec2-fetcher Key=Project,Value=AxiePro
```

### 2. Create Dedicated Security Group for EC2
```bash
# Create new SG with proper name
aws ec2 create-security-group \
  --group-name axiepro-sg-ec2-fetcher \
  --description "Security group for AxiePro EC2 data fetcher" \
  --vpc-id vpc-073cdce8e84cbccdc

# Add SSH rule (replace with your IP)
aws ec2 authorize-security-group-ingress \
  --group-name axiepro-sg-ec2-fetcher \
  --protocol tcp \
  --port 22 \
  --cidr YOUR_IP/32
```

### 3. (Optional) Create Dedicated RDS for AxiePro
If you want to separate AxiePro data from CardForum:
```bash
aws rds create-db-instance \
  --db-instance-identifier axiepro-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 15 \
  --master-username axiepro_admin \
  --master-user-password "SECURE_PASSWORD" \
  --allocated-storage 20 \
  --tags Key=Project,Value=AxiePro
```

### 4. Create Dedicated IAM Role for EC2
```bash
# Create role with proper name
aws iam create-role \
  --role-name axiepro-ec2-fetcher-role \
  --assume-role-policy-document file://ec2-trust-policy.json \
  --tags Key=Project,Value=AxiePro
```

---

## Cost Allocation

To track AxiePro costs separately:

1. **Enable Cost Allocation Tags** in AWS Billing Console
2. **Tag all resources** with `Project=AxiePro`
3. **Use Cost Explorer** to filter by tag

---

## Resource Dependencies

```
                    ┌─────────────────┐
                    │   App Runner    │
                    │   axiepro-api   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │ ECR         │  │ RDS         │  │ ElastiCache │
    │ axiepro-    │  │ cardforum   │  │ axiepro-    │
    │ backend     │  │ (SHARED)    │  │ redis       │
    └─────────────┘  └──────┬──────┘  └─────────────┘
                            │
                            │ (also used by)
                            ▼
                    ┌─────────────────┐
                    │   EC2           │
                    │   axiepro-ec2-  │
                    │   fetcher       │
                    └─────────────────┘
```

---

## Future Resources (Planned)

| Service | Proposed Name | Purpose |
|---------|--------------|---------|
| Lambda | `axiepro-lambda-price-ingestion` | 5-min price snapshots |
| Lambda | `axiepro-lambda-deal-detector` | Real-time deal detection |
| Kinesis | `axiepro-kinesis-marketplace` | Event streaming |
| SNS | `axiepro-sns-alerts` | Deal notifications |
| S3 | `axiepro-data-lake` | Historical data archive |
