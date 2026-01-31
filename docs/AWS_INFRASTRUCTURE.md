# AxiePro AWS Infrastructure Documentation

**Last Updated**: 2026-01-30
**Environment**: Development (primary), with Staging & Production configurations
**Region**: us-east-1
**Total Stacks**: 10 coordinated CDK stacks

---

## Quick Reference

| Resource Type | Count | Primary Services |
|---------------|-------|------------------|
| **Compute** | 9 | App Runner (1), Lambda (7), ECS Fargate (1) |
| **Data** | 4 | Aurora PostgreSQL (1), ElastiCache Redis (1), DynamoDB (3), S3 (4) |
| **Networking** | 1 VPC | 6 subnets, 4 security groups, VPC endpoints |
| **Event/Messaging** | 7 | EventBridge, Kinesis (1), SNS (3), SQS (4) |
| **Security** | - | KMS (2), Secrets Manager (2), IAM (6 roles) |
| **Observability** | - | CloudWatch Dashboard, Alarms, X-Ray |

---

## Architecture Diagram

```
┌────────────────── USER LAYER ──────────────────────┐
│  Frontend (Vercel) → CloudFront → WAF → API Gateway│
└──────────────────────┬─────────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────┐
│              COMPUTE LAYER                         │
│  • App Runner (FastAPI, 1-10 instances)            │
│  • Lambda Functions (7):                           │
│    - price-ingestion (every 5min)                  │
│    - sales-ingestion (every 15min)                 │
│    - metadata-ingestion (every hour)               │
│    - listings-ingestion (every 5min)               │
│    - deal-detector (Kinesis trigger)               │
│    - meta-analyzer (every hour)                    │
│    - valuation (SQS trigger)                       │
│  • ECS Fargate (batch processing)                  │
└──────────────────────┬─────────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────┐
│              DATA LAYER                            │
│  • Aurora Serverless v2 (0.5-16 ACUs)             │
│  • ElastiCache Redis 7.1                          │
│  • DynamoDB (checkpoints, cache, sessions)         │
│  • S3 (logs, data lake, artifacts)                 │
└──────────────────────┬─────────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────┐
│              EVENT/MESSAGING LAYER                 │
│  • Kinesis Stream (real-time listings, 2 shards)   │
│  • SQS Queues (batch, valuation, notifications)    │
│  • SNS Topics (alerts, insights, system)           │
│  • EventBridge (scheduling & routing)              │
└─────────────────────────────────────────────────────┘
```

---

## Stack Deployment Order

Dependencies are managed via CDK stack references:

| # | Stack | Key Resources | Dependencies |
|---|-------|--------------|--------------|
| 1 | **Networking** | VPC, Subnets, Security Groups, VPC Endpoints | None |
| 2 | **Security** | KMS, Secrets Manager, IAM Roles | None |
| 3 | **Database** | Aurora Serverless v2, DynamoDB | Networking, Security |
| 4 | **Cache** | ElastiCache Redis | Networking, Security |
| 5 | **Storage** | S3 Buckets, ECR | Security |
| 6 | **Events** | Kinesis, SQS, SNS, EventBridge | Security |
| 7 | **Compute** | App Runner, Lambda, ECS | All above |
| 8 | **API** | API Gateway, CloudFront, WAF | Compute |
| 9 | **Observability** | CloudWatch Dashboard, Alarms | All above |
| 10 | **CI/CD** | CodePipeline, CodeBuild | Storage, Compute |

**Deployment Command**:
```bash
cd infrastructure
npx cdk deploy --all -c environment=development --require-approval never
```

---

## Detailed Service Configurations

### 1. Aurora PostgreSQL (Serverless v2)

| Setting | Development | Production |
|---------|-------------|------------|
| Version | 15.8 | 15.8 |
| Min Capacity | 0.5 ACUs | 0.5 ACUs |
| Max Capacity | 2 ACUs | 16 ACUs |
| Multi-AZ | No | Yes |
| Backup Retention | 1 day | 30 days |
| Deletion Protection | No | Yes |
| Performance Insights | Yes | Yes |
| IAM Authentication | Yes | Yes |

**Connection Details**:
- **Endpoint**: `{cluster-id}.cluster-cn4c2su0o42n.us-east-1.rds.amazonaws.com`
- **Port**: 5432
- **Database**: `axiepro`
- **Schema**: `axie`
- **User**: `axiepro_admin`
- **Auth**: IAM via `generate_db_auth_token()`

**Key Parameter Settings**:
- `max_connections`: 1000
- `idle_in_transaction_session_timeout`: 300s
- `statement_timeout`: 300s (5 min max query time)
- `rds.force_ssl`: 1 (TLS required)
- `random_page_cost`: 1.1 (SSD-optimized)

**Cost**: ~$15/month (dev), ~$80/month (prod)

---

### 2. ElastiCache Redis 7.1

| Setting | Development | Production |
|---------|-------------|------------|
| Node Type | cache.t3.micro | cache.r6g.large |
| Num Nodes | 1 (primary) | 2 (primary + replica) |
| Multi-AZ | No | Yes |
| Automatic Failover | No | Yes |
| Snapshots | 1 day | 7 days |
| TLS | Required | Required |

**Connection**:
- **Endpoint**: `{replication-group}.{random}.ng.0001.use1.cache.amazonaws.com`
- **Port**: 6379
- **URL**: `rediss://{endpoint}:6379` (TLS required)

**Cache Policies**:
- `maxmemory-policy`: allkeys-lru (evict least recently used)
- `timeout`: 300s (idle connection timeout)
- `activedefrag`: yes
- `slowlog-log-slower-than`: 10ms

**Use Cases**:
- API response caching (1-5 min TTL)
- Deal scores cache (5 min TTL)
- Floor prices cache (1 min TTL)
- Session data (15 min TTL)

**Cost**: ~$5/month (dev), ~$200/month (prod)

---

### 3. App Runner Service (FastAPI Backend)

| Setting | Development | Production |
|---------|-------------|------------|
| CPU | 512 (0.5 vCPU) | 1024 (1 vCPU) |
| Memory | 1024 MB | 2048 MB |
| Min Instances | 1 | 1 |
| Max Instances | 2 | 10 |
| Auto-scaling Trigger | CPU 70%, Memory 80% | CPU 70%, Memory 80% |

**Source**:
- Image: `{account}.dkr.ecr.us-east-1.amazonaws.com/axiepro-backend:latest`
- Port: 8000
- Startup: `uvicorn src.main:app --host 0.0.0.0 --port 8000`

**Health Check**:
- Endpoint: `/health`
- Interval: 10s
- Timeout: 5s
- Unhealthy threshold: 5 failures → restart instance

**Network**:
- VPC Connector: Private access to Aurora/Redis
- Public: Yes (receives traffic from API Gateway)

**Cost**: ~$25/month (dev), ~$50/month (prod)

---

### 4. Lambda Functions

**Shared Configuration**:
- Runtime: Python 3.11
- Layer: `axiepro-dependencies-layer` (psycopg2, httpx, pydantic, etc.)
- VPC: Yes (private subnets)
- Timeout: 30s-5min (function-specific)
- Memory: 256-1024 MB
- DLQ: SQS for failed invocations
- Retry: 2 attempts for async invocations

| Function | Trigger | Memory | Timeout | Purpose |
|----------|---------|--------|---------|---------|
| **price-ingestion** | EventBridge (every 5min) | 256 MB | 30s | Fetch ETH price from CoinGecko |
| **sales-ingestion** | EventBridge (every 15min) | 256 MB | 5 min | Scan Ronin blockchain for sales |
| **metadata-ingestion** | EventBridge (every hour) | 256 MB | 5 min | Fetch Axie metadata from Moralis/SkyMavis |
| **listings-ingestion** | EventBridge (every 5min) | 256 MB | 5 min | Fetch active listings from marketplace |
| **deal-detector** | Kinesis (batch 100, 5s window) | 256 MB | 30s | Score deals from real-time listings |
| **meta-analyzer** | EventBridge (every hour) | 1024 MB | 5 min | Compute meta shifts from price data |
| **valuation** | SQS (on-demand) | 256 MB | 30s | Calculate Axie valuations |

**Environment Variables** (all Lambdas):
```env
ENVIRONMENT=development|staging|production
AWS_REGION_NAME=us-east-1
USE_AWS_SECRETS=true
AWS_SECRET_NAME=arn:aws:secretsmanager:us-east-1:{account}:secret:axiepro-api-keys-dev-XXXXX
DATABASE_SECRET_NAME=arn:aws:secretsmanager:us-east-1:{account}:secret:axiepro-database-credentials-dev-XXXXX
DATABASE_HOST={aurora-endpoint}
DATABASE_PORT=5432
DATABASE_NAME=axiepro
REDIS_HOST={redis-endpoint}
REDIS_PORT=6379
REDIS_SSL=true
S3_DATA_BUCKET=axiepro-data-dev-{hash}
KINESIS_STREAM_NAME=axiepro-listings-stream-dev
SNS_DEAL_ALERTS_TOPIC=arn:aws:sns:us-east-1:{account}:axiepro-deal-alerts-dev
PARAMETER_PREFIX=/axiepro/development
POWERTOOLS_SERVICE_NAME=axiepro
POWERTOOLS_METRICS_NAMESPACE=AxiePro
LOG_LEVEL=INFO
```

**Cost**: ~$3/month (dev), ~$20/month (prod)

---

### 5. DynamoDB Tables

| Table | Partition Key | Sort Key | GSI | Billing | TTL | Use Case |
|-------|--------------|----------|-----|---------|-----|----------|
| **checkpoints** | checkpoint_id (STRING) | - | None | PAY_PER_REQUEST | ttl | Track last processed block/timestamp |
| **valuation-cache** | axie_id (STRING) | timestamp (NUMBER) | class-timestamp-index | PAY_PER_REQUEST | ttl | Cache valuation results (1 hour) |
| **sessions** | session_id (STRING) | - | user-index | PAY_PER_REQUEST | expires_at | User sessions |

**All tables**:
- Encryption: Customer-managed KMS (`dataKey`)
- Point-in-time recovery: Yes (staging/prod)
- Deletion protection: No (ephemeral data)

**Cost**: ~$1/month (dev), ~$10/month (prod)

---

### 6. S3 Buckets

| Bucket | Purpose | Versioning | Lifecycle | Encryption |
|--------|---------|-----------|-----------|-----------|
| **logs** | Access logs, CloudWatch exports | No | Delete after 90d | S3-managed |
| **data** | Data lake (historical sales, snapshots) | Yes | IA after 30d, Glacier after 90d, Delete after 365d | KMS |
| **artifacts** | CI/CD build artifacts, Docker layers | Yes | Delete after 30d | KMS |

**All buckets**:
- Block public access: Yes
- SSL required: Yes
- Server access logging: Enabled (logs to logs bucket)
- CORS: Configured (GET/HEAD allowed)

**Cost**: ~$5/month (dev), ~$15/month (prod)

---

### 7. Kinesis Data Stream

| Setting | Development | Production |
|---------|-------------|------------|
| Stream Name | `axiepro-listings-stream-dev` | `-prod` |
| Shards | 1 | 2 |
| Retention | 24 hours | 48 hours |
| Mode | PROVISIONED | PROVISIONED |
| Encryption | KMS (dataKey) | KMS (dataKey) |

**Purpose**: Real-time listings from listings-ingestion Lambda → deal-detector Lambda

**Throughput**:
- 1 shard: 1MB/s write, 2MB/s read, 1000 PUT/s
- 2 shards: 2MB/s write, 4MB/s read, 2000 PUT/s

**Consumer**: deal-detector Lambda (batch size 100, batch window 5s)

**Cost**: ~$10/month (dev), ~$30/month (prod)

---

### 8. SQS Queues

| Queue | Visibility Timeout | DLQ | Max Receives | Purpose |
|-------|-------------------|-----|--------------|---------|
| **batch-processing** | 15 min | dlq | 3 | Heavy blockchain data fetch |
| **valuation** | 60s | dlq | 3 | Axie valuation requests |
| **notifications** | 30s | dlq | 5 | Deal/meta alerts |
| **dlq** | 14 days | - | - | Failed message reservoir |

**All queues**:
- Encryption: KMS (dataKey)
- Message retention: 14 days (4 days for main queues)
- Long polling: Enabled (10-20s wait time)

**DLQ Monitoring**:
- CloudWatch alarm: Trigger if `dlq` depth > 0
- SNS notification to system-alerts topic

**Cost**: ~$1/month (dev), ~$5/month (prod)

---

### 9. SNS Topics

| Topic | Purpose | Subscribers |
|-------|---------|-------------|
| **deal-alerts** | New deals flagged (score >70) | Lambda (email sender), Webhooks (Discord/Slack) |
| **meta-insights** | Meta shifts detected | Lambda (notification router) |
| **system-alerts** | CloudWatch alarms, operational issues | Email (team), PagerDuty |

**All topics**:
- Encryption: KMS (dataKey)
- Delivery policy: Retry 3 times with exponential backoff
- Access policy: Publish/subscribe restricted to account services

**Cost**: ~$1/month (dev), ~$5/month (prod)

---

### 10. EventBridge Rules

**Scheduled Lambdas**:

| Rule | Schedule | Target | Purpose |
|------|----------|--------|---------|
| `axiepro-price-ingestion-trigger-dev` | rate(5 minutes) | price-ingestion Lambda | Fetch ETH price |
| `axiepro-sales-ingestion-trigger-dev` | rate(15 minutes) | sales-ingestion Lambda | Fetch blockchain sales |
| `axiepro-metadata-ingestion-trigger-dev` | rate(1 hour) | metadata-ingestion Lambda | Fetch Axie metadata |
| `axiepro-listings-ingestion-trigger-dev` | rate(5 minutes) | listings-ingestion Lambda | Fetch marketplace listings |
| `axiepro-meta-analysis-trigger-dev` | rate(1 hour) | meta-analyzer Lambda | Compute meta trends |

**Custom Event Bus**:
- Name: `axiepro-events-dev`
- Archive: Yes (production only, 90-day retention)
- Used for custom application events

---

## Security Configuration

### 1. Encryption (KMS)

**Two Customer-Managed Keys**:

| Key | Alias | Rotation | Used By |
|-----|-------|----------|---------|
| **dataKey** | `axiepro-data-key` | 365 days | RDS, ElastiCache, S3, Kinesis, DynamoDB, SQS, SNS |
| **secretsKey** | `axiepro-secrets-key` | 365 days | Secrets Manager |

**Key Policies**:
- Service principals only (RDS, Lambda, App Runner, etc.)
- No user access (reduces attack surface)
- Automatic rotation enabled

---

### 2. Secrets Manager

| Secret | Contents | Rotation |
|--------|----------|----------|
| `axiepro-api-keys-{env}` | `{ MORALIS_API_KEY, SKYMAVIS_API_KEY, COINGECKO_API_KEY, INTERNAL_SECRET }` | Manual |
| `axiepro-database-credentials-{env}` | `{ username: "axiepro_admin", password: "<auto>" }` | Managed by RDS (optional) |

**Access Pattern**:
```python
# In Lambda/App Runner
import boto3
secrets_client = boto3.client('secretsmanager')
response = secrets_client.get_secret_value(SecretId=os.environ['AWS_SECRET_NAME'])
secrets = json.loads(response['SecretString'])
moralis_key = secrets['MORALIS_API_KEY']
```

---

### 3. IAM Roles

**6 Service Roles with Least Privilege**:

| Role | Assumed By | Key Permissions |
|------|-----------|-----------------|
| **appRunnerInstanceRole** | tasks.apprunner.amazonaws.com | Secrets read, KMS decrypt, RDS IAM auth, X-Ray write |
| **appRunnerAccessRole** | build.apprunner.amazonaws.com | ECR pull (GetDownloadUrlForLayer, BatchGetImage) |
| **lambdaExecutionRole** | lambda.amazonaws.com | VPC access, Secrets read, KMS decrypt, CloudWatch logs, X-Ray |
| **ecsTaskRole** | ecs-tasks.amazonaws.com | Application permissions (Secrets, KMS, S3, DynamoDB) |
| **ecsExecutionRole** | ecs-tasks.amazonaws.com | Infrastructure permissions (ECR pull, Secrets retrieve) |
| **eventsRole** | events.amazonaws.com | Invoke Lambda, publish to SNS, send to SQS |

**Inline Policies**: None (all managed or custom managed policies)

---

### 4. Network Security

**VPC Configuration**:
- CIDR: `10.0.0.0/16` (dev), `10.1.0.0/16` (stg), `10.2.0.0/16` (prod)
- **Public Subnets** (2 AZs): NAT Gateways, VPC Endpoints
- **Private Subnets** (2 AZs): App Runner, Lambda, ECS
- **Isolated Subnets** (2 AZs): Aurora, ElastiCache (no internet)

**Security Groups**:

| SG | Ingress Rules | Purpose |
|----|--------------|---------|
| **database-sg** | Port 5432 from compute-sg, lambda-sg | Aurora access |
| **cache-sg** | Port 6379 from compute-sg, lambda-sg | Redis access |
| **compute-sg** | No ingress (App Runner managed) | App Runner/ECS tasks |
| **lambda-sg** | No ingress | Lambda functions in VPC |
| **vpc-endpoint-sg** | Port 443 from all VPC | VPC endpoints |

**All SGs**: Egress allows all traffic (outbound to external APIs)

**VPC Endpoints**:
- **Gateway** (free): S3, DynamoDB
- **Interface** (paid, prod/staging only): Secrets Manager, CloudWatch Logs, ECR, SQS, SNS, KMS

---

### 5. WAF (Staging/Production)

**Scope**: CLOUDFRONT

**Rule Sets**:
1. AWS Managed Rules - Common Rule Set (protects against OWASP Top 10)
2. AWS Managed Rules - Known Bad Inputs
3. AWS Managed Rules - SQL Injection Protection

**Metrics**: CloudWatch enabled, sampled requests logged

**Cost**: ~$10/month (per web ACL + rules)

---

## Monitoring & Observability

### CloudWatch Dashboard

**Name**: `axiepro-dashboard-{env}`

**20+ Widgets**:
1. API Gateway: Request count, latency, 4xx/5xx errors
2. Lambda (each): Invocations, errors, duration, throttles
3. Aurora: CPU, connections, read/write latency, replica lag
4. ElastiCache: CPU, memory, evictions, hit ratio, commands/sec
5. App Runner: Active instances, CPU/memory, response time
6. Kinesis: Iterator age, incoming records, incoming bytes
7. SQS: Messages visible, messages in-flight, age of oldest message

**Auto-refresh**: 1 minute

---

### CloudWatch Alarms

**Connected to**: SNS topic `axiepro-alarms-{env}`

**Critical Alarms**:
| Alarm | Metric | Threshold | Action |
|-------|--------|-----------|--------|
| Lambda error rate | Errors/Invocations | >5% for 5 min | SNS alert |
| API 5xx rate | 5xxError/Count | >1% for 5 min | SNS alert |
| Database CPU | CPUUtilization | >80% for 10 min | SNS alert |
| Redis evictions | Evictions | >100 in 5 min | SNS alert |
| Kinesis lag | IteratorAge | >3600s (1 hour) | SNS alert |
| DLQ depth | ApproximateNumberOfMessagesVisible | >0 | SNS alert |
| App Runner unhealthy | HealthStatus | Unhealthy | SNS alert |

**Notification Destinations**:
- Email: (configure subscription)
- Slack: Via SNS → Lambda webhook
- PagerDuty: Via SNS integration (production)

---

### X-Ray Tracing

**Enabled**: Staging, Production

**Traced Services**:
- App Runner (FastAPI with X-Ray SDK)
- Lambda functions (AWS_XRAY_DAEMON_ADDRESS)
- API Gateway (active tracing)

**Sampling**:
- Default: 1 request/second + 5% of additional requests
- Custom: Can increase for specific routes

**Service Map**: Visualizes dependencies (API Gateway → App Runner → Aurora → Lambda → Kinesis)

---

### Log Retention

| Service | Development | Production |
|---------|-------------|------------|
| Application (App Runner) | 7 days | 30 days |
| Lambda functions | 7 days | 30 days |
| API Gateway | 7 days | 30 days |
| Database (RDS/slow query) | 7 days | 30 days |
| ElastiCache (slow-log, engine-log) | 7 days | 30 days |

**Log Aggregation**:
- CloudWatch Insights: Available for querying
- Exports: Manual export to S3 (for long-term archival)

---

## Cost Breakdown

### Development (~$80/month)
```
Aurora Serverless v2 (0.5-2 ACU): $15
ElastiCache (t3.micro, 1 node): $5
App Runner (512 CPU, 1GB, 1-2 instances): $25
Lambda (256MB, ~1M invocations): $3
API Gateway (1M requests): $3
Kinesis (1 shard): $10
DynamoDB (PAY_PER_REQUEST, low usage): $1
S3 (10GB + requests): $5
NAT Gateway: $30
Other (KMS, VPC endpoints, CloudWatch): $3
──────────────────────────────────────
Total: ~$80/month
```

### Staging (~$200/month)
```
Aurora Serverless v2 (0.5-4 ACU, Multi-AZ): $35
ElastiCache (t3.small, 2 nodes): $25
App Runner (1024 CPU, 2GB, 1-4 instances): $50
Lambda (512MB, ~2M invocations): $8
API Gateway (5M requests): $17
CloudFront (500GB transfer): $25
Kinesis (1 shard): $10
DynamoDB (PAY_PER_REQUEST, moderate usage): $3
S3 (50GB + requests): $8
NAT Gateway: $30
WAF + VPC Endpoints + X-Ray: $20
──────────────────────────────────────
Total: ~$231/month
```

### Production (~$500/month)
```
Aurora Serverless v2 (0.5-16 ACU, Multi-AZ, backups): $80
ElastiCache (r6g.large, 2 nodes, snapshots): $200
App Runner (1024 CPU, 2GB, 1-10 instances): $50
Lambda (512MB, ~5M invocations, 100 reserved): $20
API Gateway (20M requests): $70
CloudFront (2TB transfer): $40
Kinesis (2 shards): $30
DynamoDB (PAY_PER_REQUEST, heavy usage): $10
S3 (200GB + requests): $15
NAT Gateway (2 AZs): $60
WAF + VPC Endpoints + X-Ray + KMS: $25
──────────────────────────────────────
Total: ~$600/month
```

**Cost Optimization Opportunities**:
1. Use reserved capacity for Aurora (save 30-40%)
2. Use Lambda reserved concurrency (save 20%)
3. Reduce log retention (7 days → save $10/month)
4. S3 Intelligent-Tiering (auto-optimize, save ~20%)
5. Spot instances for ECS Fargate (save 70% on spot capacity)

---

## Scaling Strategy

### Horizontal Scaling (Auto)
- **App Runner**: Scales 1→10 instances based on CPU 70%, Memory 80%
- **Lambda**: Concurrent execution up to AWS account limits (1000 default)
- **Aurora**: Reader replicas auto-added if CPU >70% for 10 min (staging/prod)

### Vertical Scaling (Manual)
- **App Runner**: Increase CPU/memory via CDK config update
- **Lambda**: Increase memory allocation (up to 10GB)
- **ElastiCache**: Change node type (requires brief downtime)
- **Aurora**: Increase max ACUs (0-128 available)

### Capacity Planning

**Current Traffic Estimate (Development)**:
- API requests: ~100 req/min
- Lambda invocations: ~1M/month
- Database queries: ~500 queries/min
- Kinesis records: ~100 records/min

**Expected Production Traffic**:
- API requests: ~500 req/min (~1M/day)
- Lambda invocations: ~5M/month
- Database queries: ~2000 queries/min
- Kinesis records: ~1000 records/min

**Scaling Limits**:
| Service | Current Max | AWS Limit | Headroom |
|---------|-------------|-----------|----------|
| App Runner instances | 10 | 25 (can request increase) | 2.5x |
| Lambda concurrency | 1000 | 1000 (can request increase) | 1x ⚠️ |
| Aurora ACUs | 16 | 128 | 8x |
| Kinesis shards | 2 | 500 (soft limit) | 250x |
| API Gateway RPS | 1000 | 10000 | 10x |

**Recommendation**: Request Lambda concurrency increase to 5000 before production launch.

---

## Operational Runbooks

### Deploy a New Version
```bash
# 1. Update code in GitHub (triggers CI/CD in staging/prod)
# 2. For manual deployment (dev):
cd infrastructure
npx cdk deploy "AxiePro-Compute-dev" --require-approval never

# 3. Verify deployment
aws apprunner describe-service \
  --service-arn $(aws apprunner list-services --query 'ServiceSummaryList[?ServiceName==`axiepro-api-dev`].ServiceArn' --output text) \
  --region us-east-1
```

### Check Lambda Execution Status
```bash
# Tail logs for a specific Lambda
aws logs tail /aws/lambda/axiepro-metadata-ingestion-dev \
  --region us-east-1 \
  --since 1h \
  --follow

# Check invocation metrics (last hour)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=axiepro-metadata-ingestion-dev \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%S') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%S') \
  --period 300 \
  --statistics Sum \
  --region us-east-1
```

### Database Maintenance
```bash
# Connect to Aurora via IAM auth
aws rds generate-db-auth-token \
  --hostname axiepro-aurora-cluster-dev.cluster-cn4c2su0o42n.us-east-1.rds.amazonaws.com \
  --port 5432 \
  --username axiepro_admin \
  --region us-east-1

# Use token as password in psql
PGPASSWORD=$(aws rds generate-db-auth-token ...) \
psql -h axiepro-aurora-cluster-dev.cluster-cn4c2su0o42n.us-east-1.rds.amazonaws.com \
     -p 5432 \
     -U axiepro_admin \
     -d axiepro \
     --set=sslmode=require
```

### Check DLQ for Failed Messages
```bash
# Get DLQ depth
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/{account}/axiepro-dlq-dev \
  --attribute-names ApproximateNumberOfMessages \
  --region us-east-1

# Receive messages from DLQ (for inspection)
aws sqs receive-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/{account}/axiepro-dlq-dev \
  --max-number-of-messages 10 \
  --region us-east-1
```

### Rotate API Keys
```bash
# 1. Update secret in Secrets Manager
aws secretsmanager update-secret \
  --secret-id axiepro-api-keys-dev \
  --secret-string '{"MORALIS_API_KEY":"new-key", ...}' \
  --region us-east-1

# 2. Restart App Runner (picks up new secret)
aws apprunner start-deployment \
  --service-arn $(aws apprunner list-services --query 'ServiceSummaryList[?ServiceName==`axiepro-api-dev`].ServiceArn' --output text) \
  --region us-east-1

# 3. No Lambda restart needed (fetches secret on each invocation)
```

---

## Security Best Practices

### ✅ Currently Implemented
1. All data encrypted at-rest (KMS) and in-transit (TLS 1.2+)
2. Private subnets for databases/cache
3. Security groups restrict access to services
4. IAM roles with least privilege
5. Secrets Manager for all credentials
6. VPC endpoints for private AWS API access
7. WAF with AWS Managed Rules (staging/prod)
8. Deletion protection on production database
9. Automatic backups (1-30 days retention)
10. CloudWatch logging for all services
11. X-Ray tracing for request flow (staging/prod)
12. Non-root containers (App Runner runs as appuser)

### ⚠️ Recommendations
1. **Rate Limiting**: Implement API gateway throttling per user (not just global)
2. **DLQ Monitoring**: Auto-remediation Lambda triggered by DLQ depth alarm
3. **Multi-Region DR**: Cross-region read replica for Aurora (production)
4. **Secrets Rotation**: Enable automatic rotation for API keys
5. **CORS Tightening**: Dev environment allows `*`, should restrict
6. **Custom WAF Rules**: Add application-specific rules (e.g., block known scraper IPs)
7. **Lambda Reserved Concurrency**: Set limits to prevent runaway costs
8. **GuardDuty**: Enable for threat detection (staging/prod)
9. **Config Rules**: Enforce compliance (e.g., all S3 buckets encrypted)
10. **Cost Anomaly Detection**: CloudWatch budget alerts

---

## Known Issues & Risks

### 🔴 Critical Issue: Data Pipeline Rate Limiting

**Problem**: All ingestion Lambdas hitting HTTP 429 from SkyMavis API

**Impact**:
- No price/sales/metadata being ingested
- Deal detection has no data
- Frontend shows empty states

**Root Cause**:
1. Multiple Lambdas hitting same API concurrently
2. No exponential backoff/retry
3. No circuit breaker
4. No multi-source fallback

**Solution Implemented**:
- ✅ Moralis API as primary source (separate rate limit pool)
- ✅ SkyMavis as fallback for gene data only
- ✅ Reduced batch size and increased delay
- ⏳ Awaiting 18:40 UTC verification run

---

### 🟡 Medium Risk: Single Region Deployment

**Issue**: All infrastructure in us-east-1 (no DR)

**Impact**: Regional outage = complete downtime

**Mitigation**:
- Short-term: Use RDS snapshots for manual failover
- Long-term: Multi-region active-active (W5 consideration)

---

### 🟡 Medium Risk: Lambda Concurrency Limits

**Issue**: 1000 concurrent executions across all functions

**Impact**: High traffic could throttle Lambdas

**Mitigation**:
- Request limit increase to 5000 before production launch
- Set reserved concurrency per function (prevent one function starving others)

---

### 🟢 Low Risk: NAT Gateway Single Point of Failure

**Issue**: Dev environment has 1 NAT Gateway (single AZ)

**Impact**: AZ failure = no internet for Lambdas

**Mitigation**:
- Already fixed in prod (2 NAT Gateways, Multi-AZ)
- Dev acceptable (short downtime OK)

---

## Disaster Recovery Plan

### RTO/RPO Targets

| Environment | RTO (Recovery Time Objective) | RPO (Recovery Point Objective) |
|-------------|------------------------------|--------------------------------|
| Development | 4 hours | 24 hours |
| Staging | 2 hours | 1 hour |
| Production | 1 hour | 5 minutes |

### Backup Strategy

**Aurora PostgreSQL**:
- Automated daily snapshots (1-30 day retention)
- Point-in-time restore (5-minute granularity)
- Manual snapshots before schema changes

**ElastiCache**:
- Automated daily snapshots (1-7 day retention)
- Can restore to new cluster (requires DNS update)

**DynamoDB**:
- Point-in-time recovery enabled (staging/prod)
- Can restore to any point in last 35 days

**S3**:
- Versioning enabled (data, artifacts buckets)
- Cross-region replication (production only, future)

### Recovery Procedures

**Scenario 1: Database Corruption**
```bash
# 1. Identify last known good snapshot
aws rds describe-db-cluster-snapshots \
  --db-cluster-identifier axiepro-aurora-cluster-prod \
  --region us-east-1

# 2. Restore snapshot to new cluster
aws rds restore-db-cluster-from-snapshot \
  --db-cluster-identifier axiepro-aurora-cluster-prod-restored \
  --snapshot-identifier rds:axiepro-aurora-cluster-prod-2026-01-30-06-00 \
  --region us-east-1

# 3. Update App Runner/Lambda env vars to point to new cluster
# 4. Verify data integrity
# 5. Delete old cluster after confirmation
```

**Scenario 2: Region Outage**
1. Deploy infrastructure to us-west-2 via CDK
2. Restore latest Aurora snapshot to new region
3. Update Route 53 DNS to point to new region
4. Estimated time: 2-4 hours

---

## Future Infrastructure Enhancements

### W2-W3 (Beta/Validation)
- [ ] Enable GuardDuty for threat detection
- [ ] Set up AWS Config rules for compliance
- [ ] Implement cost anomaly detection alerts
- [ ] Add custom WAF rules for scraper protection
- [ ] Request Lambda concurrency increase to 5000

### W4-W5 (Monetization/Growth)
- [ ] Multi-region active-active deployment
- [ ] Aurora Global Database (cross-region replication)
- [ ] CloudFront signed URLs for authenticated content
- [ ] SES for email notifications (replace SNS webhooks)
- [ ] ElastiCache cluster mode for horizontal scaling

### Post-W5 (Scale)
- [ ] Aurora read replica auto-scaling (5-10 replicas)
- [ ] API Gateway caching with cache invalidation
- [ ] DynamoDB Global Tables (multi-region)
- [ ] Step Functions for complex workflows
- [ ] EventBridge Pipes for advanced event routing

---

## Summary

**AxiePro AWS Infrastructure**:
- ✅ **Production-Grade**: 10 coordinated CDK stacks, enterprise patterns
- ✅ **Secure**: Multi-layer encryption, IAM least privilege, network isolation
- ✅ **Observable**: Comprehensive CloudWatch dashboards, alarms, X-Ray tracing
- ✅ **Scalable**: Auto-scaling for compute, serverless data layer
- ✅ **Cost-Optimized**: $80 (dev), $200 (staging), $500 (prod) per month
- ⚠️ **Operational Challenge**: External API rate limiting (addressed with Moralis switch)

**Key Strengths**:
1. Event-driven architecture enables real-time deal detection
2. Serverless-first approach minimizes operational overhead
3. Multi-AZ high availability in production
4. Automated backups and point-in-time recovery
5. Comprehensive monitoring with actionable alarms

**Next Steps**:
1. Verify Moralis metadata ingestion fix (18:40 UTC today)
2. Request Lambda concurrency increase to 5000
3. Enable GuardDuty and AWS Config (W2)
4. Plan multi-region deployment (W5)

---

**Last Reviewed**: 2026-01-30
**Maintained By**: Purpose Prompter PATH BUILDER
**Next Review**: After W1 completion (metadata coverage >80%)
