# AxiePro SSM Parameter Store Configuration

This document describes all AWS Systems Manager (SSM) Parameter Store parameters required for AxiePro deployment.

## Overview

AxiePro uses SSM Parameter Store to manage environment-specific configuration across all AWS services. Parameters are organized by category and prefixed with the environment name.

**Parameter Naming Convention:**
```
/axiepro/{environment}/{category}/{parameter}
```

- `{environment}`: `dev`, `staging`, or `production`
- `{category}`: `database`, `redis`, `secrets`, `app`, `monitoring`
- `{parameter}`: Specific configuration key

## Quick Start

### Automated Setup

Use the provided script to create all parameters automatically:

```bash
cd infrastructure/scripts
./setup-ssm-parameters.sh dev us-west-2
```

This will:
1. Read the manifest from `config/ssm-parameters.json`
2. Create parameters with default values
3. Auto-generate secrets where applicable
4. Pull values from CDK outputs where available
5. Flag parameters requiring manual configuration

### Manual Setup

For sensitive parameters that require manual configuration:

```bash
# SkyMavis API Key (required)
aws ssm put-parameter \
  --name "/axiepro/dev/secrets/skymavis-key" \
  --value "YOUR_SKYMAVIS_API_KEY" \
  --type "SecureString" \
  --region us-west-2

# Moralis API Key (optional backup)
aws ssm put-parameter \
  --name "/axiepro/dev/secrets/moralis-key" \
  --value "YOUR_MORALIS_API_KEY" \
  --type "SecureString" \
  --region us-west-2
```

## Parameter Reference

### Database Parameters

Connection parameters for Aurora PostgreSQL Serverless v2.

| Parameter | Type | Required | Default | Source |
|-----------|------|----------|---------|--------|
| `/axiepro/{env}/database/host` | String | Yes | - | CDK Output: `DatabaseStack.ClusterEndpoint` |
| `/axiepro/{env}/database/port` | String | Yes | `5432` | Static |
| `/axiepro/{env}/database/name` | String | Yes | `axiepro` | Static |
| `/axiepro/{env}/database/user` | String | Yes | `axiepro_admin` | Static |
| `/axiepro/{env}/database/schema` | String | Yes | `axie` | Static |

**Notes:**
- Database password is stored in AWS Secrets Manager (not SSM)
- Host endpoint is automatically populated from CDK stack outputs

### Redis Parameters

Connection parameters for ElastiCache Redis.

| Parameter | Type | Required | Default | Source |
|-----------|------|----------|---------|--------|
| `/axiepro/{env}/redis/endpoint` | String | Yes | - | CDK Output: `CacheStack.RedisEndpoint` |
| `/axiepro/{env}/redis/port` | String | Yes | `6379` | Static |
| `/axiepro/{env}/redis/ssl` | String | Yes | `true` | Static |
| `/axiepro/{env}/redis/ttl_default` | String | No | `300` | Static |

**Notes:**
- SSL is required for all environments
- Default TTL is 5 minutes (300 seconds)

### Secrets Parameters

API keys and sensitive configuration.

| Parameter | Type | Required | Source | Instructions |
|-----------|------|----------|--------|--------------|
| `/axiepro/{env}/secrets/skymavis-key` | SecureString | Yes | Manual | Obtain from [SkyMavis Developer Portal](https://developers.skymavis.com/console) |
| `/axiepro/{env}/secrets/moralis-key` | SecureString | No | Manual | Obtain from [Moralis Admin](https://admin.moralis.io/settings) |
| `/axiepro/{env}/secrets/internal` | SecureString | Yes | Auto-generated | Used for service-to-service authentication |
| `/axiepro/{env}/secrets/jwt-secret` | SecureString | Yes | Auto-generated | Used for JWT token signing |

**Security Notes:**
- All secrets use `SecureString` type (encrypted with AWS KMS)
- Auto-generated secrets are 32-64 character random strings
- Never commit secrets to version control

### Application Parameters

General application configuration.

| Parameter | Type | Required | Default | Allowed Values |
|-----------|------|----------|---------|----------------|
| `/axiepro/{env}/app/environment` | String | Yes | - | `dev`, `staging`, `production` |
| `/axiepro/{env}/app/log_level` | String | Yes | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `/axiepro/{env}/app/region` | String | Yes | `us-west-2` | AWS region codes |
| `/axiepro/{env}/app/cors_origins` | String | Yes | `http://localhost:3000` | Comma-separated URLs |

**Environment-Specific Recommendations:**

**Development:**
```
log_level: DEBUG
cors_origins: http://localhost:3000,http://localhost:8000
```

**Staging:**
```
log_level: INFO
cors_origins: https://staging.axiepro.com
```

**Production:**
```
log_level: WARNING
cors_origins: https://axiepro.com,https://www.axiepro.com
```

### Monitoring Parameters

Observability and error tracking configuration.

| Parameter | Type | Required | Default | Source |
|-----------|------|----------|---------|--------|
| `/axiepro/{env}/monitoring/sentry_dsn` | String | No | - | Manual: [Sentry Project Settings](https://sentry.io/settings/) |
| `/axiepro/{env}/monitoring/cloudwatch_namespace` | String | Yes | `AxiePro` | Static |

## Verification

### Check All Parameters

List all parameters for an environment:

```bash
aws ssm get-parameters-by-path \
  --path "/axiepro/dev/" \
  --recursive \
  --region us-west-2 \
  --query "Parameters[*].[Name,Type]" \
  --output table
```

### Check Specific Parameter

Get a specific parameter value:

```bash
# Non-secret parameter
aws ssm get-parameter \
  --name "/axiepro/dev/database/host" \
  --region us-west-2 \
  --query "Parameter.Value" \
  --output text

# Encrypted parameter
aws ssm get-parameter \
  --name "/axiepro/dev/secrets/skymavis-key" \
  --with-decryption \
  --region us-west-2 \
  --query "Parameter.Value" \
  --output text
```

### Verify Required Parameters

The setup script automatically verifies all required parameters:

```bash
cd infrastructure/scripts
./setup-ssm-parameters.sh dev us-west-2
```

Expected output:
```
Total parameters: 23
Existing: 15
Created: 8
Requires manual setup: 2
Missing (required): 0
```

## Local Development

For local development, export parameters to `.env` file:

```bash
cd infrastructure/scripts
./setup-ssm-parameters.sh dev us-west-2

# This creates: backend/.env.dev
```

The generated `.env.dev` file can be used for local backend development:

```bash
cd backend
cp .env.dev .env
uvicorn src.main:app --reload
```

## Deployment Integration

### CDK Deployment

Parameters are automatically read by CDK stacks during deployment:

```typescript
// infrastructure/lib/stacks/compute-stack.ts
const parameterPrefix = `/axiepro/${props.environment}`;

const dbHost = ssm.StringParameter.valueForStringParameter(
  this,
  `${parameterPrefix}/database/host`
);
```

### Lambda Functions

Lambda functions read parameters via environment variables set by CDK:

```python
# backend/src/lambdas/sales_ingestion.py
import os

DATABASE_HOST = os.getenv("DATABASE_HOST")  # From SSM parameter
```

### Frontend

Frontend configuration is generated from CDK outputs + SSM parameters:

```bash
cd infrastructure/scripts
./configure-frontend-env.sh production us-west-2

# Creates: frontend/.env.production
```

## Security Best Practices

1. **Use SecureString for Secrets**
   - All API keys and sensitive values use `SecureString` type
   - Encrypted with AWS KMS

2. **Least Privilege IAM**
   - Lambda execution roles only have read access to required parameters
   - Parameter path prefix restricts access scope

3. **Environment Isolation**
   - Each environment has separate parameters
   - Production parameters are never accessible from dev/staging

4. **Secret Rotation**
   - Rotate auto-generated secrets periodically
   - SkyMavis API key rotation: Update parameter + restart services

5. **Audit Logging**
   - All parameter access is logged in CloudTrail
   - Monitor for unexpected parameter reads

## Troubleshooting

### Parameter Not Found

**Error:** `ParameterNotFound: Parameter /axiepro/dev/database/host not found`

**Solution:**
1. Check parameter name is correct (case-sensitive)
2. Verify region matches deployment region
3. Run setup script: `./setup-ssm-parameters.sh dev us-west-2`

### Access Denied

**Error:** `AccessDeniedException: User is not authorized to perform: ssm:GetParameter`

**Solution:**
1. Check IAM permissions include `ssm:GetParameter` action
2. Verify parameter path matches IAM policy prefix
3. For SecureString, ensure `kms:Decrypt` permission

### CDK Output Not Found

**Error:** `[DRY RUN] Would create: /axiepro/dev/database/host (CDK output not found)`

**Solution:**
1. Deploy database stack first: `npx cdk deploy DatabaseStack -c environment=dev`
2. Verify stack output exists: `aws cloudformation describe-stacks --stack-name axiepro-DatabaseStack-dev`
3. Re-run setup script

## Migration from Hardcoded Values

If migrating from hardcoded configuration:

1. **Identify Hardcoded Values**
   ```bash
   grep -r "DATABASE_HOST" backend/src/
   ```

2. **Create SSM Parameters**
   ```bash
   ./setup-ssm-parameters.sh dev us-west-2
   ```

3. **Update Code to Read from Environment**
   ```python
   # Before
   DATABASE_HOST = "localhost"

   # After
   DATABASE_HOST = os.getenv("DATABASE_HOST")
   ```

4. **Deploy Updated Code**
   ```bash
   npx cdk deploy ComputeStack -c environment=dev
   ```

## Related Documentation

- [AWS Infrastructure Overview](./AWS_INFRASTRUCTURE.md)
- [Deployment Guide](./DEPLOYMENT_GUIDE.md)
- [Environment Configuration](../infrastructure/lib/config/environments.ts)
- [SSM Parameter Manifest](../infrastructure/config/ssm-parameters.json)
