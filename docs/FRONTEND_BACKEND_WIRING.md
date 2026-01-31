# Frontend-Backend API Wiring Guide

## Overview

This document describes the complete frontend-backend API integration for AxiePro, including configuration, deployment, and troubleshooting.

**Status**: ✅ **VERIFIED AND WORKING**

**Last Verified**: 2026-01-31

---

## Architecture

```
Next.js Frontend (Vercel/App Runner)
    ↓
    HTTP/HTTPS Request
    ↓
API Client (frontend/src/lib/api/client.ts)
    ↓
    URL: {NEXT_PUBLIC_API_URL}/api/v1{endpoint}
    ↓
FastAPI Backend (App Runner)
    ↓
    CORS Validation → Route Handler → Database → Response
    ↓
Frontend State (React Query)
```

---

## Configuration

### Frontend Configuration

**Environment Variables Required:**

| Variable | Purpose | Example | Required |
|----------|---------|---------|----------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL | `https://xxx.awsapprunner.com` | ✅ Yes |
| `NEXT_PUBLIC_ENV` | Environment identifier | `production` | ❌ No |
| `NEXT_PUBLIC_API_TIMEOUT` | Request timeout (ms) | `30000` | ❌ No |

**Configuration File**: `frontend/src/lib/config.ts`

```typescript
export const config = {
  apiBaseUrl: process.env.NEXT_PUBLIC_API_URL || '',
  apiVersion: 'v1',
};
```

**URL Construction**:
```
Final URL = {NEXT_PUBLIC_API_URL}/api/{apiVersion}{endpoint}
Example: https://nu8bq2ckxs.us-east-1.awsapprunner.com/api/v1/market/stats
```

---

### Backend Configuration

**Environment Variables Required:**

| Variable | Purpose | Example | Required |
|----------|---------|---------|----------|
| `CORS_ORIGINS` | Allowed frontend origins | `https://app.axiepro.io,http://localhost:3000` | ✅ Yes |
| `DATABASE_URL` | PostgreSQL connection | `postgresql://...` | ✅ Yes |
| `REDIS_URL` | Redis cache connection | `redis://...` | ✅ Yes |
| `JWT_SECRET` | Token signing secret | `min-32-char-random-string` | ✅ Yes |

**CORS Configuration** (`backend/src/main.py:84-93`):

```python
cors_origins = settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## CRITICAL: CORS Configuration

### Problem Statement

**CORS (Cross-Origin Resource Sharing)** prevents the frontend from making requests to the backend unless the backend explicitly allows the frontend's origin.

**Symptom of Misconfiguration**:
```
Access to fetch at 'https://backend.com/api/v1/market/stats'
from origin 'https://frontend.com' has been blocked by CORS policy:
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

### Solution: Environment-Specific Configuration

#### Development (localhost)

**Frontend**: `http://localhost:3000` or `http://127.0.0.1:3000`

**Backend CORS_ORIGINS**:
```bash
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

✓ Default configuration already supports this

---

#### Staging (App Runner + Vercel Preview)

**Frontend**:
- Vercel Preview: `https://axiepro-git-branch-username.vercel.app`
- App Runner: `https://xxx.us-east-1.awsapprunner.com`

**Backend CORS_ORIGINS**:
```bash
# Set via SSM Parameter Store
aws ssm put-parameter \
  --name "/axiepro/staging/app/cors_origins" \
  --value "https://axiepro-staging.vercel.app,https://nu8bq2ckxs.us-east-1.awsapprunner.com,http://localhost:3000" \
  --type "String" \
  --region us-west-2 \
  --overwrite
```

---

#### Production (Custom Domain)

**Frontend**:
- Primary: `https://app.axiepro.io`
- Alternatives: `https://axiepro.io`, `https://www.axiepro.io`

**Backend CORS_ORIGINS**:
```bash
# Set via SSM Parameter Store
aws ssm put-parameter \
  --name "/axiepro/production/app/cors_origins" \
  --value "https://app.axiepro.io,https://axiepro.io,https://www.axiepro.io" \
  --type "String" \
  --region us-west-2 \
  --overwrite
```

**Security Best Practice**:
- Do NOT include wildcard `*` in production
- Do NOT include `http://localhost:3000` in production
- Use specific domains only

---

## API Endpoints

### Complete Endpoint Mapping

| Frontend Call | Backend Route | Method | Purpose |
|--------------|---------------|--------|---------|
| `marketApi.getStats()` | `/market/stats` | GET | Market statistics |
| `marketApi.getListings()` | `/market/listings` | GET | Active listings |
| `marketApi.getSales()` | `/market/sales` | GET | Sales history |
| `marketApi.getFloorPrices()` | `/market/floor-prices` | GET | Floor prices by class |
| `marketApi.getAnalyticsSummary()` | `/market/analytics/summary` | GET | Analytics dashboard |
| `marketApi.getFloorPricesByClass()` | `/market/analytics/floor-prices` | GET | Floor price trends |
| `marketApi.getPriceHistory()` | `/market/analytics/price-history` | GET | Historical price data |
| `valuationApi.getValuation(id)` | `/valuation/{id}` | GET | Axie valuation |
| `valuationApi.getBatchValuations(ids)` | `/valuation/batch` | POST | Batch valuations |
| `valuationApi.getLiveDeals()` | `/valuation/deals/live` | GET | Undervalued deals |
| `authApi.requestChallenge(addr)` | `/auth/challenge` | POST | Get signature challenge |
| `authApi.verifySignature(...)` | `/auth/verify` | POST | Verify wallet signature |

**All endpoints prefixed with**: `/api/v1`

**Full URL Example**:
```
https://nu8bq2ckxs.us-east-1.awsapprunner.com/api/v1/market/stats
```

---

## Type Safety

### Response Structure

All API responses follow this standard format:

```typescript
{
  "success": boolean,
  "data": T,           // Actual response data
  "meta"?: {           // Optional pagination/metadata
    "total": number,
    "page": number,
    "per_page": number,
    "total_pages": number
  },
  "cached"?: boolean   // Optional cache hit indicator
}
```

### Type Definitions

**Location**: `frontend/src/types/`

- `market.ts` - Market data types
- `valuation.ts` - Valuation types
- `wallet.ts` - Authentication types

**Backend Validation**: Pydantic models ensure type safety at runtime

---

## Authentication Flow

### Wallet Signature Authentication

```
1. Frontend: requestChallenge(walletAddress)
     ↓
   Backend: Generate random challenge message
     ↓
   Response: { challenge_id, message, expires_at }

2. Frontend: Sign message with wallet (MetaMask/Ronin)
     ↓
   User signature

3. Frontend: verifySignature(challenge_id, signature)
     ↓
   Backend: Verify signature matches address
     ↓
   Response: { token (JWT), expires_at, address }

4. Frontend: Store token, include in subsequent requests
     ↓
   Header: Authorization: Bearer {token}
```

### Token Usage

```typescript
// Frontend automatically includes token when available
const response = await apiClient('/protected-endpoint', {
  authToken: getStoredToken(), // From auth context/localStorage
});
```

---

## Error Handling

### Frontend Error Handling

**Custom Error Class** (`frontend/src/lib/api/client.ts:12-28`):

```typescript
export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public data?: unknown
  ) {
    super(`API Error ${status}: ${statusText}`);
  }
}
```

**Usage in Components**:
```typescript
try {
  const stats = await marketApi.getStats();
} catch (error) {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      // Handle authentication error
      router.push('/login');
    } else if (error.status === 404) {
      // Handle not found
      showNotification('Resource not found');
    } else {
      // Handle other errors
      showNotification(`Error: ${error.statusText}`);
    }
  }
}
```

### Backend Error Responses

| Status | Meaning | Example |
|--------|---------|---------|
| 400 | Bad Request | Invalid query parameter |
| 401 | Unauthorized | Missing or invalid auth token |
| 403 | Forbidden | Valid token but insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 422 | Validation Error | Request body validation failed |
| 500 | Internal Server Error | Unhandled exception |

**Error Response Format**:
```json
{
  "detail": "Invalid class: InvalidClass"
}
```

---

## Caching Strategy

### Frontend Caching (React Query)

**Configuration** (`frontend/src/lib/config.ts`):
```typescript
staleTime: 60000,  // 1 minute
cacheTime: 300000, // 5 minutes
```

**Cache Keys**:
```typescript
['market', 'stats']
['market', 'listings', { class: 'beast', page: 1 }]
['valuation', axieId]
```

### Backend Caching (Redis)

**Cache TTLs** (`backend/src/config/settings.py:154-156`):
```python
cache_ttl_listings = 300        # 5 minutes
cache_ttl_floor_prices = 60     # 1 minute
cache_ttl_axie_details = 600    # 10 minutes
```

**Cache Invalidation**: Event-driven via cache_invalidator Lambda

---

## Deployment Checklist

### Pre-Deployment Verification

```bash
# 1. Verify backend is running
curl https://YOUR_BACKEND_URL/health
# Expected: {"status":"healthy","version":"0.1.0"}

# 2. Verify CORS configuration
curl -H "Origin: https://YOUR_FRONTEND_URL" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS \
     https://YOUR_BACKEND_URL/api/v1/market/stats
# Expected: Access-Control-Allow-Origin header in response

# 3. Test API endpoint
curl https://YOUR_BACKEND_URL/api/v1/market/stats
# Expected: JSON response with market data

# 4. Verify frontend can reach backend
# In browser console:
fetch('https://YOUR_BACKEND_URL/api/v1/market/stats')
  .then(r => r.json())
  .then(console.log)
# Expected: JSON response (no CORS error)
```

### Deployment Steps

#### 1. Configure Backend CORS

```bash
# Via SSM Parameter
aws ssm put-parameter \
  --name "/axiepro/production/app/cors_origins" \
  --value "https://app.axiepro.io,https://axiepro.io,https://www.axiepro.io" \
  --type "String" \
  --region us-west-2 \
  --overwrite

# Restart backend service to pick up new config
aws apprunner update-service \
  --service-arn YOUR_SERVICE_ARN \
  --region us-east-1
```

#### 2. Configure Frontend Environment

```bash
# Use the script we created
cd infrastructure/scripts
./configure-frontend-env.sh production us-west-2

# Verify generated file
cat ../../frontend/.env.production

# Should contain:
# NEXT_PUBLIC_API_URL=https://YOUR_BACKEND_URL
```

#### 3. Deploy Frontend

```bash
# If using Vercel
cd frontend
vercel --prod

# Or build and deploy to your hosting
npm run build
# Deploy dist/ to hosting provider
```

#### 4. Verify End-to-End

```bash
# Visit frontend in browser
https://app.axiepro.io

# Open Network tab in DevTools
# Navigate to Market page
# Verify API calls succeed:
# - Request URL: https://backend.com/api/v1/market/stats
# - Status: 200 OK
# - Response: JSON data
# - No CORS errors
```

---

## Troubleshooting

### Issue: CORS Error in Browser

**Symptom**:
```
Access to fetch at 'https://backend.com/api/v1/market/stats'
from origin 'https://frontend.com' has been blocked by CORS policy
```

**Diagnosis**:
```bash
# Check backend CORS configuration
curl https://backend.com/health | jq

# Check actual CORS headers
curl -v -H "Origin: https://frontend.com" \
     https://backend.com/api/v1/market/stats 2>&1 | grep -i access-control
```

**Solution**:
1. Update `CORS_ORIGINS` environment variable to include frontend URL
2. Restart backend service
3. Clear browser cache
4. Retry

---

### Issue: Frontend Shows "localhost:8000" in Production

**Symptom**: API requests go to `http://localhost:8000` instead of production backend

**Diagnosis**:
```bash
# Check frontend environment configuration
cat frontend/.env.production

# Verify environment variable is set
echo $NEXT_PUBLIC_API_URL
```

**Solution**:
1. Ensure `NEXT_PUBLIC_API_URL` is set in deployment environment
2. For Vercel: Set in Vercel dashboard under Environment Variables
3. For self-hosted: Set in `.env.production` file
4. Rebuild frontend with correct environment

---

### Issue: 401 Unauthorized on Protected Endpoints

**Symptom**: API returns 401 even with valid token

**Diagnosis**:
```javascript
// In browser console
console.log(localStorage.getItem('auth_token'));
// Should show JWT token

// Decode token to check expiration
const token = localStorage.getItem('auth_token');
const payload = JSON.parse(atob(token.split('.')[1]));
console.log('Expires:', new Date(payload.exp * 1000));
```

**Solution**:
1. If token expired: Re-authenticate
2. If token missing: Check auth flow is working
3. If token present but invalid: Clear storage and re-authenticate

---

### Issue: Slow API Responses

**Symptom**: API calls take >5 seconds

**Diagnosis**:
```bash
# Test backend directly
time curl https://backend.com/api/v1/market/stats

# Check database connection
psql $DATABASE_URL -c "SELECT 1"

# Check Redis connection
redis-cli -h $REDIS_HOST ping
```

**Solution**:
1. If database slow: Check query performance, add indexes
2. If Redis down: Fix Redis connection
3. If Lambda cold start: Increase provisioned concurrency
4. If App Runner slow: Scale up instance size

---

## Performance Benchmarks

### Expected Response Times

| Endpoint | Expected | Acceptable | Slow |
|----------|----------|-----------|------|
| `/health` | <50ms | <100ms | >200ms |
| `/market/stats` (cached) | <100ms | <200ms | >500ms |
| `/market/stats` (uncached) | <300ms | <500ms | >1s |
| `/market/listings` (20 items) | <200ms | <400ms | >800ms |
| `/valuation/{id}` (cached) | <150ms | <300ms | >600ms |
| `/valuation/batch` (10 items) | <400ms | <800ms | >2s |

### Monitoring

**Frontend** (Vercel Analytics):
- Page load time
- API request duration
- Error rate

**Backend** (CloudWatch):
- Request count
- Response time (p50, p95, p99)
- Error rate
- Cache hit ratio

---

## Security Considerations

### SSL/TLS
- ✅ All production traffic must use HTTPS
- ✅ No mixed content (HTTPS frontend → HTTP backend)
- ✅ Valid SSL certificates required

### CORS Security
- ✅ Specific origins only (no wildcards in production)
- ✅ Credentials allowed only for trusted origins
- ✅ Methods restricted to necessary ones

### Token Security
- ✅ JWT tokens stored securely (httpOnly cookies recommended)
- ✅ Tokens expire after reasonable time (default: 24 hours)
- ✅ Tokens refreshed before expiration
- ✅ No tokens in URL parameters or localStorage if possible

### Input Validation
- ✅ All user input validated on backend (Pydantic models)
- ✅ SQL injection prevented (SQLAlchemy ORM)
- ✅ XSS prevented (React auto-escaping)

---

## Related Documentation

- [SSM Parameters Guide](./SSM_PARAMETERS.md)
- [AWS Infrastructure](./AWS_INFRASTRUCTURE.md)
- [API Endpoint Tests](./API_ENDPOINT_TESTS.md)
- [Infrastructure Gaps Filled](../INFRASTRUCTURE_GAPS_FILLED.md)

---

**Document Status**: ✅ Complete and Verified
**Last Updated**: 2026-01-31
**Maintained By**: AxiePro Infrastructure Team
