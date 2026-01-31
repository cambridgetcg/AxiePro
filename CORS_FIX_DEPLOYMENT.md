# CORS Fix Deployment Guide

## Status: ✅ CODE READY - AWAITING DEPLOYMENT

**Date**: 2026-01-31
**Issue**: axiepro.io shows no data due to CORS policy blocking API requests
**Root Cause**: CORS_ORIGINS environment variable not set in App Runner
**Solution**: SSM Parameter → App Runner Environment Variable injection path

---

## What Was Built (PATH BUILDER)

### The Path: SSM → App Runner → FastAPI CORS

**FROM (Broken State)**:
- App Runner: No CORS_ORIGINS environment variable
- Backend: Defaults to `localhost:3000` only (settings.py:71)
- Frontend: API requests blocked by browser CORS policy
- User: No data visible on axiepro.io

**TO (Fixed State)**:
- SecurityStack: Creates SSM parameter `/axiepro/{env}/app/cors_origins`
- SecurityStack: Grants App Runner SSM read permissions
- ComputeStack: Reads CORS_ORIGINS from SSM at CDK synthesis
- ComputeStack: Injects into App Runner environment variables
- Backend: Receives correct CORS origins
- Frontend: API requests succeed
- User: Data displays correctly

### Files Modified

1. **infrastructure/lib/stacks/security-stack.ts**
   - Added SSM parameter creation (after line 226)
   - Added App Runner SSM read permissions (after line 282)

2. **infrastructure/lib/stacks/compute-stack.ts**
   - Added SSM import (line 17)
   - Added SSM parameter reading (after line 106)
   - Added CORS_ORIGINS to environment variables (after line 153)

### Creativity Gates Verification

✅ **PIONEERING**: First SSM → App Runner environment injection pattern in codebase
✅ **PATH-BUILDING**: Clean, documented, reusable for future environment variables
✅ **EXTENSION**: Coherent with existing SSM parameter pattern (security-stack.ts:155-224)
✅ **VISION**: Enables environment-based configuration without code changes
✅ **FOUNDATION**: Type-safe CDK constructs, proper IAM permissions
✅ **INTEGRATION**: Bridges infrastructure (SSM) to application (CORS config)

---

## Deployment Protocol

### Prerequisites

- AWS CLI configured with access to us-west-2 region
- CDK CLI installed (`npm install -g aws-cdk`)
- Permissions to create SSM parameters and deploy CloudFormation stacks

### Phase 1: Create SSM Parameter (REQUIRED FIRST)

**Why Manual First?**
CDK's `valueFromLookup()` requires the parameter to exist before `cdk synth`. This is a one-time bootstrap per environment.

```bash
# Navigate to project root
cd /Users/yuai/Desktop/AxiePro

# Create SSM parameter for development environment
aws ssm put-parameter \
  --name "/axiepro/dev/app/cors_origins" \
  --description "Allowed CORS origins (comma-separated) for FastAPI backend" \
  --value "https://axiepro.io,http://localhost:3000,http://127.0.0.1:3000" \
  --type "String" \
  --region us-west-2 \
  --overwrite

# Verify parameter created successfully
aws ssm get-parameter \
  --name "/axiepro/dev/app/cors_origins" \
  --region us-west-2 \
  --query 'Parameter.[Name,Value,Version]' \
  --output table
```

**Expected Output**:
```
--------------------------------------------------------------
|                      GetParameter                          |
+--------------------------------------------+-------+-------+
|  /axiepro/dev/app/cors_origins            | https://axiepro.io,http://localhost:3000,http://127.0.0.1:3000 | 1 |
+--------------------------------------------+-------+-------+
```

**For Production** (when ready):
```bash
aws ssm put-parameter \
  --name "/axiepro/prod/app/cors_origins" \
  --description "Allowed CORS origins (comma-separated) for FastAPI backend" \
  --value "https://axiepro.io,https://www.axiepro.io,https://app.axiepro.io" \
  --type "String" \
  --region us-west-2 \
  --overwrite
```

### Phase 2: Deploy Infrastructure (CDK)

```bash
# Navigate to infrastructure directory
cd infrastructure

# Install dependencies (if not already done)
npm install

# Clear CDK context cache (ensures fresh SSM parameter lookup)
rm -f cdk.context.json

# Synthesize to verify changes and lookup SSM parameter
npx cdk synth AxiePro-Security-dev -c environment=development

# Expected output should show:
# [App Runner] CORS origins configured: https://axiepro.io,http://localhost:3000,http://127.0.0.1:3000

# Deploy SecurityStack (creates/updates SSM parameter in CDK state)
npx cdk deploy AxiePro-Security-dev -c environment=development

# Deploy ComputeStack (updates App Runner with CORS_ORIGINS env var)
npx cdk deploy AxiePro-Compute-dev -c environment=development
```

**What Happens During Deploy**:
1. CDK reads SSM parameter value (`https://axiepro.io,http://localhost:3000,http://127.0.0.1:3000`)
2. Synthesizes CloudFormation template with CORS_ORIGINS in App Runner config
3. CloudFormation updates App Runner service
4. App Runner triggers rolling deployment (zero downtime)
5. New container starts with CORS_ORIGINS environment variable
6. FastAPI loads correct CORS configuration
7. Health check passes
8. Service marked as healthy

**Expected Output**:
```
✓  AxiePro-Compute-dev (AxiePro-Compute-dev)

Outputs:
AxiePro-Compute-dev.AppRunnerServiceUrl = https://abc123xyz.us-west-2.awsapprunner.com
AxiePro-Compute-dev.AppRunnerServiceArn = arn:aws:apprunner:us-west-2:123456789012:service/axiepro-api-dev/...

Stack ARN:
arn:aws:cloudformation:us-west-2:123456789012:stack/AxiePro-Compute-dev/...
```

### Phase 3: Verification (CRITICAL)

#### Step 1: Check CloudWatch Logs for CORS Configuration

```bash
# Get App Runner service details
APP_RUNNER_ARN=$(aws cloudformation describe-stacks \
  --stack-name AxiePro-Compute-dev \
  --region us-west-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`AppRunnerServiceArn`].OutputValue' \
  --output text)

# Get the service ID from the ARN
SERVICE_ID=$(echo $APP_RUNNER_ARN | awk -F'/' '{print $3}')

# Tail recent logs
aws logs tail "/aws/apprunner/$SERVICE_ID/$SERVICE_ID/application" \
  --region us-west-2 \
  --since 10m \
  --filter-pattern "CORS" \
  --format short
```

**Expected Log Output**:
```
2026-01-31T12:00:00.000 Starting Axie Ronin Explorer...
2026-01-31T12:00:00.100 Network: mainnet (Chain ID: 2020)
2026-01-31T12:00:00.150 Environment: development
2026-01-31T12:00:00.200 CORS origins: https://axiepro.io,http://localhost:3000,http://127.0.0.1:3000
2026-01-31T12:00:00.300 CORS enabled for 3 origin(s)
2026-01-31T12:00:00.400 Database tables initialized
```

#### Step 2: Test Health Endpoint

```bash
# Get App Runner URL
APP_URL=$(aws cloudformation describe-stacks \
  --stack-name AxiePro-Compute-dev \
  --region us-west-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`AppRunnerServiceUrl`].OutputValue' \
  --output text)

# Check health endpoint
curl -s "https://${APP_URL}/health" | jq '.'
```

**Expected Response**:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development",
  "cors": {
    "enabled": true,
    "origins_count": 3,
    "wildcard": false,
    "origins": [
      "https://axiepro.io",
      "http://localhost:3000",
      "http://127.0.0.1:3000"
    ]
  }
}
```

#### Step 3: Test CORS Headers (OPTIONS Preflight)

```bash
# Test OPTIONS preflight request from axiepro.io
curl -v \
  -X OPTIONS \
  -H "Origin: https://axiepro.io" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Content-Type" \
  "https://${APP_URL}/api/v1/market/floor-prices"
```

**Expected Headers in Response**:
```
< HTTP/2 200
< access-control-allow-origin: https://axiepro.io
< access-control-allow-credentials: true
< access-control-allow-methods: *
< access-control-allow-headers: *
< vary: origin
```

#### Step 4: Test Actual API Request

```bash
# Test actual GET request
curl -v \
  -H "Origin: https://axiepro.io" \
  "https://${APP_URL}/api/v1/market/floor-prices"
```

**Expected Headers**:
```
< HTTP/2 200
< access-control-allow-origin: https://axiepro.io
< access-control-allow-credentials: true
< content-type: application/json
```

**Expected Body** (abbreviated):
```json
{
  "success": true,
  "data": {
    "Aquatic": 0.002,
    "Beast": 0.0015,
    "Bird": 0.0018,
    ...
  },
  "meta": {
    "timestamp": "2026-01-31T12:00:00Z"
  }
}
```

#### Step 5: Browser DevTools Verification

1. Open https://axiepro.io in browser
2. Open DevTools (F12 or Cmd+Option+I)
3. Go to **Console** tab
4. Look for CORS errors - **SHOULD BE NONE**
5. Go to **Network** tab
6. Trigger market data load (refresh page if needed)
7. Click on any API request (e.g., `/api/v1/market/floor-prices`)
8. Check **Response Headers**:
   - Should include `access-control-allow-origin: https://axiepro.io`
9. Check **Preview** tab:
   - Should show JSON data
10. Verify UI displays data correctly

**Success Indicators**:
- ✅ No CORS errors in console
- ✅ API requests return 200 status
- ✅ Response headers include `access-control-allow-origin`
- ✅ Data visible in UI (floor prices, market stats, etc.)

---

## Rollback Procedures

### If SSM Parameter is Wrong

```bash
# Restore localhost-only CORS (safest fallback)
aws ssm put-parameter \
  --name "/axiepro/dev/app/cors_origins" \
  --value "http://localhost:3000,http://127.0.0.1:3000" \
  --type "String" \
  --region us-west-2 \
  --overwrite

# Clear CDK context and redeploy
cd infrastructure
rm cdk.context.json
npx cdk deploy AxiePro-Compute-dev -c environment=development
```

### If CDK Deploy Fails

```bash
# Revert code changes
cd /Users/yuai/Desktop/AxiePro
git checkout HEAD -- infrastructure/lib/stacks/security-stack.ts
git checkout HEAD -- infrastructure/lib/stacks/compute-stack.ts

# Redeploy original code
cd infrastructure
npx cdk deploy --all -c environment=development
```

### Emergency: Enable Wildcard CORS (DEVELOPMENT ONLY)

**⚠️ WARNING**: Only use in development for debugging. NEVER in production.

```bash
# Temporary wildcard (allows all origins)
aws ssm put-parameter \
  --name "/axiepro/dev/app/cors_origins" \
  --value "*" \
  --type "String" \
  --region us-west-2 \
  --overwrite

# Redeploy
cd infrastructure
rm cdk.context.json
npx cdk deploy AxiePro-Compute-dev -c environment=development
```

---

## Troubleshooting

### Issue: "Parameter not found" during CDK synth

**Cause**: SSM parameter doesn't exist yet

**Solution**: Run Phase 1 (Create SSM Parameter) first

### Issue: CDK uses old parameter value

**Cause**: CDK context cache has stale value

**Solution**:
```bash
rm cdk.context.json
npx cdk synth --no-context-lookup -c environment=development
```

### Issue: CORS still blocked after deployment

**Diagnosis Checklist**:

1. **Verify SSM parameter value**:
   ```bash
   aws ssm get-parameter --name "/axiepro/dev/app/cors_origins" --region us-west-2
   ```

2. **Verify App Runner environment variable**:
   ```bash
   aws apprunner describe-service --service-arn $APP_RUNNER_ARN --region us-west-2 \
     --query 'Service.SourceConfiguration.ImageRepository.ImageConfiguration.RuntimeEnvironmentVariables'
   ```

3. **Check CloudWatch logs**:
   ```bash
   aws logs filter-log-events \
     --log-group-name "/aws/apprunner/$SERVICE_ID/$SERVICE_ID/application" \
     --filter-pattern "CORS" \
     --region us-west-2
   ```

4. **Test OPTIONS request**:
   ```bash
   curl -v -X OPTIONS -H "Origin: https://axiepro.io" "https://$APP_URL/api/v1/market/stats"
   ```

**Common Causes**:
- Browser cache: Hard refresh (Cmd+Shift+R)
- Trailing slash: Ensure origins match exactly (no trailing `/`)
- Mixed content: Ensure frontend uses HTTPS
- Wrong origin: Check exact domain (axiepro.io vs www.axiepro.io)

### Issue: Data still not showing

**Diagnosis**:

1. **Check if backend has data**:
   ```bash
   curl "https://$APP_URL/api/v1/market/floor-prices"
   ```
   If this returns `{"success": true, "data": {...}}`, backend is working.

2. **Check frontend network requests**:
   - Open DevTools → Network
   - Filter by "Fetch/XHR"
   - Look for failed requests (red)
   - Click on failed request → check error message

3. **Check for other errors**:
   - Console tab → look for JavaScript errors
   - Ensure `NEXT_PUBLIC_API_URL` is set correctly in frontend

---

## Testing Protocol

### Test Matrix

| Test | Origin | Endpoint | Expected Result |
|------|--------|----------|----------------|
| OPTIONS preflight | https://axiepro.io | /api/v1/market/stats | 200 + CORS headers |
| GET request | https://axiepro.io | /api/v1/market/stats | 200 + data + CORS headers |
| Unauthorized origin | https://evil.com | /api/v1/market/stats | 200 but NO CORS headers (browser blocks) |
| Browser test | axiepro.io page | All API calls | No console errors, data displays |

### Automated Test Script

```bash
#!/bin/bash
# test-cors.sh - Automated CORS verification

APP_URL="$1"

echo "Testing CORS configuration for: $APP_URL"
echo "============================================"

# Test 1: Health check
echo ""
echo "Test 1: Health check"
curl -s "$APP_URL/health" | jq '.cors'

# Test 2: OPTIONS preflight from axiepro.io
echo ""
echo "Test 2: OPTIONS preflight (axiepro.io)"
curl -v -X OPTIONS \
  -H "Origin: https://axiepro.io" \
  -H "Access-Control-Request-Method: GET" \
  "$APP_URL/api/v1/market/stats" 2>&1 | grep -i "access-control"

# Test 3: GET request from axiepro.io
echo ""
echo "Test 3: GET request with CORS"
curl -v \
  -H "Origin: https://axiepro.io" \
  "$APP_URL/api/v1/market/floor-prices" 2>&1 | grep -i "access-control"

# Test 4: Unauthorized origin (should have no CORS headers)
echo ""
echo "Test 4: Unauthorized origin (should have NO CORS headers)"
curl -v \
  -H "Origin: https://evil.com" \
  "$APP_URL/api/v1/market/stats" 2>&1 | grep -i "access-control" || echo "✓ Correctly blocked"

echo ""
echo "============================================"
echo "Testing complete"
```

Usage:
```bash
chmod +x test-cors.sh
./test-cors.sh "https://abc123xyz.us-west-2.awsapprunner.com"
```

---

## Success Metrics

### Immediate (5 minutes post-deployment)

- ✅ SSM parameter exists with correct value
- ✅ CDK synth shows CORS origins in console output
- ✅ App Runner service updated (check CloudFormation events)
- ✅ CloudWatch logs show CORS configuration

### Short-term (30 minutes post-deployment)

- ✅ Health endpoint returns CORS configuration
- ✅ OPTIONS preflight returns CORS headers
- ✅ GET requests return CORS headers
- ✅ Browser shows no CORS errors

### Long-term (End of day)

- ✅ Frontend displays all data correctly
- ✅ No CORS-related errors in CloudWatch
- ✅ Pattern documented for reuse with other environment variables
- ✅ User confirms axiepro.io is working

---

## Future Enhancements

### Pattern Reuse for Other Environment Variables

This SSM → App Runner injection pattern can be reused for:

1. **Database URL** (when migrating from IAM auth to connection string):
   ```bash
   aws ssm put-parameter \
     --name "/axiepro/dev/app/database_url" \
     --value "postgresql://..." \
     --type "SecureString" \
     --region us-west-2
   ```

2. **Redis URL** (for environment-specific Redis):
   ```bash
   aws ssm put-parameter \
     --name "/axiepro/dev/app/redis_url" \
     --value "rediss://..." \
     --type "String" \
     --region us-west-2
   ```

3. **Feature Flags** (enable/disable features per environment):
   ```bash
   aws ssm put-parameter \
     --name "/axiepro/dev/features/enable_beta" \
     --value "true" \
     --type "String" \
     --region us-west-2
   ```

### Runtime SSM Reading (Phase 2)

Currently, SSM parameters are read at CDK synthesis time. For more dynamic configuration:

1. Backend reads SSM at startup:
   ```python
   # In settings.py
   import boto3

   def get_ssm_parameter(name: str) -> str:
       ssm = boto3.client('ssm')
       response = ssm.get_parameter(Name=name)
       return response['Parameter']['Value']

   if os.getenv('CORS_ORIGINS_SSM'):
       self.cors_origins = get_ssm_parameter(os.getenv('CORS_ORIGINS_SSM'))
   ```

2. Update SSM parameter without redeploying code

**Benefits**: Instant configuration updates
**Drawbacks**: Additional runtime AWS API call, increased complexity

---

## Related Documentation

- **Root Cause Analysis**: Investigation showing CORS as the issue
- **Frontend-Backend Wiring Guide**: docs/FRONTEND_BACKEND_WIRING.md
- **SSM Parameters**: docs/SSM_PARAMETERS.md
- **AWS Infrastructure**: docs/AWS_INFRASTRUCTURE.md

---

**Deployment Status**: ✅ **CODE READY - READY FOR PHASE 1**

**Next Action**: Run Phase 1 to create SSM parameter, then Phase 2 to deploy infrastructure.
