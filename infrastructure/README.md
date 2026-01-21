# AxiePro AWS Infrastructure

Production-grade AWS infrastructure for the AxiePro Axie Infinity Analytics Platform, built with AWS CDK (TypeScript).

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EDGE LAYER                                     │
│  CloudFront CDN → WAF → API Gateway → App Runner (FastAPI)                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                            COMPUTE LAYER                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  App Runner  │  │ ECS Fargate  │  │    Lambda    │  │  EventBridge │   │
│  │  (API)       │  │  (Batch)     │  │  (Scheduled) │  │  (Events)    │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                             DATA LAYER                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   Aurora     │  │  ElastiCache │  │   DynamoDB   │  │      S3      │   │
│  │  Serverless  │  │    Redis     │  │  (Sessions)  │  │  (Data Lake) │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EVENT PROCESSING                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   Kinesis    │  │     SQS      │  │     SNS      │  │  WebSocket   │   │
│  │  (Streaming) │  │   (Queues)   │  │   (Topics)   │  │    API       │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Stacks

| Stack | Description | Resources |
|-------|-------------|-----------|
| **Networking** | Network foundation | VPC, Subnets, Security Groups, VPC Endpoints |
| **Security** | Security & secrets | KMS Keys, Secrets Manager, IAM Roles |
| **Database** | Persistent storage | Aurora Serverless v2, DynamoDB Tables |
| **Cache** | Caching layer | ElastiCache Redis Cluster |
| **Storage** | Object storage | S3 Buckets, ECR Repository |
| **Events** | Event processing | EventBridge, Kinesis, SQS, SNS, WebSocket API |
| **Compute** | Application hosting | App Runner, ECS Fargate, Lambda Functions |
| **API** | API layer | API Gateway, CloudFront, WAF |
| **Observability** | Monitoring | CloudWatch Dashboards, Alarms, X-Ray |
| **CI/CD** | Deployment pipeline | CodePipeline, CodeBuild |

## Prerequisites

- Node.js 18+
- AWS CLI configured with appropriate credentials
- AWS CDK CLI (`npm install -g aws-cdk`)

## Quick Start

```bash
# 1. Install dependencies
cd infrastructure
npm install

# 2. Bootstrap CDK (first time only)
npx cdk bootstrap

# 3. Deploy to development
./scripts/deploy.sh development

# Or deploy specific stack
./scripts/deploy.sh development Networking
```

## Environments

| Environment | Use Case | Features |
|-------------|----------|----------|
| **development** | Local testing | Minimal resources, no HA, quick iteration |
| **staging** | Pre-production | Production-like, reduced scale, all features |
| **production** | Live traffic | Full HA, deletion protection, all features |

### Environment Configuration

```typescript
// lib/config/environments.ts
const productionConfig = {
  database: {
    minCapacity: 0.5,    // Aurora ACUs
    maxCapacity: 16,
    enableMultiAz: true,
  },
  cache: {
    nodeType: 'cache.r6g.large',
    numReplicas: 1,
  },
  compute: {
    appRunner: {
      minInstances: 1,
      maxInstances: 10,
    },
  },
  // ...
};
```

## Deployment

### Deploy All Stacks

```bash
# Development (no approval required)
npm run deploy:dev

# Staging (requires approval for IAM/security changes)
npm run deploy:staging

# Production (requires approval)
npm run deploy:prod
```

### Deploy Specific Stack

```bash
npx cdk deploy "AxiePro-Networking-dev" -c environment=development
```

### View Changes Before Deploying

```bash
npm run diff
```

## Cost Estimates

| Environment | Monthly Cost |
|-------------|--------------|
| Development | ~$80 |
| Staging | ~$200 |
| Production | ~$500 |

### Production Cost Breakdown

| Service | Configuration | Monthly Cost |
|---------|---------------|--------------|
| Aurora Serverless v2 | 0.5-16 ACU, Multi-AZ | ~$80 |
| ElastiCache Redis | cache.r6g.large, 1 replica | ~$200 |
| App Runner | 1-10 instances | ~$50 |
| Lambda | ~1M invocations | ~$5 |
| API Gateway | ~10M requests | ~$35 |
| CloudFront | 100GB transfer | ~$10 |
| Kinesis | 2 shards | ~$30 |
| S3 | 100GB + requests | ~$5 |
| Other (VPC, KMS, etc.) | - | ~$85 |

## Project Structure

```
infrastructure/
├── bin/
│   └── axiepro-infra.ts      # CDK app entry point
├── lib/
│   ├── config/
│   │   ├── constants.ts      # Shared constants
│   │   └── environments.ts   # Environment configs
│   ├── stacks/
│   │   ├── networking-stack.ts
│   │   ├── security-stack.ts
│   │   ├── database-stack.ts
│   │   ├── cache-stack.ts
│   │   ├── storage-stack.ts
│   │   ├── events-stack.ts
│   │   ├── compute-stack.ts
│   │   ├── api-stack.ts
│   │   ├── observability-stack.ts
│   │   └── cicd-stack.ts
│   └── index.ts
├── scripts/
│   ├── deploy.sh
│   └── destroy.sh
├── cdk.json
├── package.json
└── tsconfig.json
```

## Stack Dependencies

```
Networking
    ├── Security
    ├── Database
    └── Cache
         │
         ├── Storage
         └── Events
              │
              └── Compute
                   │
                   └── API
                        │
                        ├── Observability
                        └── CI/CD
```

## Configuration

### Update Constants

Edit `lib/config/constants.ts`:

```typescript
export const DOMAIN_NAME = 'axiepro.io';
export const AWS_ACCOUNT = '034362054546';
export const AWS_REGION = 'us-east-1';
```

### Secrets

After deployment, update secrets in AWS Secrets Manager:

1. Go to AWS Console → Secrets Manager
2. Find `axiepro-api-keys-{env}`
3. Update with actual API keys:
   - `MORALIS_API_KEY`
   - `SKYMAVIS_API_KEY`
   - `COINGECKO_API_KEY`

### CI/CD Setup

1. Create GitHub connection in AWS CodeStar Connections
2. Update `cicd-stack.ts` with:
   - GitHub organization name
   - Connection ARN

## Monitoring

### CloudWatch Dashboard

Access at: `https://console.aws.amazon.com/cloudwatch/home#dashboards:name=axiepro-dashboard-{env}`

### Key Metrics

- API latency and error rates
- Database CPU and connections
- Redis memory and hit ratio
- Lambda invocations and errors
- Kinesis processing lag
- SQS queue depth

### Alarms

Alerts are sent to SNS topic `axiepro-alarms-{env}`. Configure email/Slack notifications.

## Security

### Encryption

- All data encrypted at rest with KMS
- TLS 1.2+ for all transit
- Redis in-transit encryption enabled

### Network

- Private subnets for databases and cache
- VPC endpoints for AWS services
- Security groups with minimal access

### WAF Rules

- AWS Managed Rules (Common, SQLi, Known Bad Inputs)
- Rate limiting (2000 requests / 5 min per IP)

## Troubleshooting

### CDK Bootstrap Error

```bash
npx cdk bootstrap aws://ACCOUNT_ID/REGION
```

### Permission Denied

Ensure AWS credentials have admin access for initial deployment.

### Stack Stuck in UPDATE_ROLLBACK

```bash
aws cloudformation continue-update-rollback --stack-name STACK_NAME
```

### View Logs

```bash
# App Runner logs
aws logs tail /aws/apprunner/axiepro-api-{env}

# Lambda logs
aws logs tail /aws/lambda/axiepro-price-ingestion-{env}
```

## Cleanup

```bash
# Development only
./scripts/destroy.sh development

# Production (requires explicit confirmation)
./scripts/destroy.sh production
```

## License

Proprietary - AxiePro
