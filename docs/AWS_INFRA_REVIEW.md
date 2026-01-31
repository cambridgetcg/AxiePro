# AxiePro AWS Infrastructure Review

**Date**: 2026-01-29
**Reviewed by**: PP (Purpose Prompter)
**Dimension**: UNDERSTANDING → JUSTICE (placement assessment)

---

## Executive Summary

### Overall Status: ⚠️ PARTIALLY OPERATIONAL

The AWS infrastructure is **well-architected and fully deployed**, but a **critical operational issue** is preventing data ingestion.

| Component | Status | Notes |
|-----------|--------|-------|
| CDK Infrastructure | ✅ Deployed | 8/9 stacks deployed in us-east-1 |
| App Runner API | ✅ Healthy | Responding at api.axiepro.io |
| Lambda Functions | ⚠️ Running but failing | Rate-limited by SkyMavis API |
| Database | ✅ Available | Aurora Serverless v2 |
| Cache | ✅ Available | ElastiCache Redis |
| Data Pipeline | ❌ Blocked | HTTP 429 errors |

---

## 1. Infrastructure Deployed vs Defined

### CloudFormation Stacks (8/9 deployed)

| Stack | Status | Resources |
|-------|--------|-----------|
| AxiePro-Networking-dev | ✅ UPDATE_COMPLETE | VPC, Subnets, Security Groups |
| AxiePro-Security-dev | ✅ UPDATE_COMPLETE | KMS, Secrets, IAM Roles |
| AxiePro-Database-dev | ✅ UPDATE_COMPLETE | Aurora PostgreSQL, DynamoDB |
| AxiePro-Cache-dev | ✅ CREATE_COMPLETE | ElastiCache Redis |
| AxiePro-Events-dev | ✅ CREATE_COMPLETE | Kinesis, SNS, SQS, EventBridge |
| AxiePro-Compute-dev | ✅ UPDATE_COMPLETE | App Runner, Lambda Functions |
| AxiePro-API-dev | ✅ UPDATE_COMPLETE | API Gateway |
| AxiePro-Observability-dev | ✅ UPDATE_COMPLETE | CloudWatch Dashboards |
| AxiePro-Storage-dev | ❓ Not listed | S3 Buckets exist (deployed separately?) |

### Lambda Functions (7 deployed)

| Function | Memory | Trigger | Status |
|----------|--------|---------|--------|
| axiepro-price-ingestion-dev | 256MB | Every 5 min | ⚠️ Rate-limited |
| axiepro-sales-ingestion-dev | 256MB | Every 15 min | ⚠️ Rate-limited |
| axiepro-listings-ingestion-dev | 256MB | Every 5 min | ⚠️ Rate-limited |
| axiepro-deal-detector-dev | 256MB | Kinesis stream | ✅ Ready (no data) |
| axiepro-meta-analyzer-dev | 1024MB | Every 1 hour | ⚠️ Rate-limited |
| axiepro-valuation-dev | 256MB | On-demand | ✅ Ready |
| axiepro-run-migrations-dev | 512MB | Manual | ✅ Available |

### Supporting Resources

| Resource Type | Deployed | Names |
|---------------|----------|-------|
| S3 Buckets | 4 | axiepro-data, artifacts, logs, assets |
| Kinesis Streams | 1 | axiepro-listings-stream-dev |
| SNS Topics | 4 | deal-alerts, meta-insights, system-alerts, alarms |
| SQS Queues | 4 | batch-processing, valuation, notifications, dlq |
| DynamoDB Tables | 3 | checkpoints, sessions, valuation-cache |
| Secrets | 3 | api-keys, database-credentials, aurora-credentials |
| EventBridge Rules | 4 | price, sales, listings, meta triggers |

---

## 2. Critical Issue: API Rate Limiting

### Problem

All data ingestion Lambda functions are failing with **HTTP 429 (Too Many Requests)** from SkyMavis API.

```
Error fetching beast: Client error '429 Too Many Requests'
for url 'https://api-gateway.skymavis.com/graphql/axie-marketplace'
```

### Impact

- ❌ No new price data being ingested
- ❌ No new sales data being ingested
- ❌ No floor prices available in API
- ❌ Deal detection has no data to process
- ❌ Meta analysis has no trends to detect

### Root Cause Analysis

1. **Multiple Lambda functions** hitting SkyMavis API concurrently
2. **No rate limiting** implemented in Lambda code
3. **No backoff/retry** strategy for 429 errors
4. **API key** may have hit daily/hourly quota

### Evidence from Logs

```
2026-01-29T17:48:17 - price_ingestion: "Stored 0 price snapshots"
2026-01-29T17:41:53 - sales_ingestion: "fetched 0, inserted 0 from 0 pages"
```

---

## 3. Architecture Assessment

### What's Working Well ✅

1. **Multi-AZ Architecture**: VPC spans 2 AZs with proper subnet isolation
2. **Security Layers**: KMS encryption, Secrets Manager, IAM auth for RDS
3. **Observability**: CloudWatch logs, custom metrics, X-Ray tracing configured
4. **Event-Driven Design**: Kinesis → Lambda → SNS pipeline properly wired
5. **Auto-Scaling**: App Runner, Aurora Serverless v2 configured correctly
6. **CORS**: Fixed to allow app.axiepro.io

### What Needs Attention ⚠️

1. **Rate Limiting Strategy**: No exponential backoff for external APIs
2. **API Quota Management**: No tracking of API usage vs limits
3. **Circuit Breaker**: No pattern to stop hammering failing API
4. **Data Pipeline Monitoring**: Alarms exist but no auto-remediation
5. **Storage Stack**: May not be deployed via CDK (exists but not in CF)

### Architecture Diagram

```
                           ┌─────────────────────────────────────────┐
                           │         EXTERNAL APIs (BLOCKED)         │
                           │    SkyMavis GraphQL (429 Rate Limit)    │
                           └─────────────────┬───────────────────────┘
                                             │ ❌ HTTP 429
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
           ┌────────▼────────┐     ┌─────────▼────────┐     ┌─────────▼────────┐
           │ Price Ingestion │     │ Sales Ingestion  │     │ Listings Ingest  │
           │   Lambda (5m)   │     │   Lambda (15m)   │     │   Lambda (5m)    │
           │    ⚠️ FAILING    │     │    ⚠️ FAILING    │     │    ⚠️ FAILING    │
           └────────┬────────┘     └─────────┬────────┘     └─────────┬────────┘
                    │                        │                        │
                    │                        │                        │
                    ▼                        ▼                        ▼
           ┌─────────────────────────────────────────────────────────────────────┐
           │                    Aurora PostgreSQL (Empty)                        │
           │   • price_snapshots: 0 recent rows                                  │
           │   • sales: 89K historical (no recent)                               │
           │   • listings: stale                                                 │
           └─────────────────────────────────┬───────────────────────────────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
           ┌────────▼────────┐     ┌─────────▼────────┐     ┌─────────▼────────┐
           │  Deal Detector  │     │  Meta Analyzer   │     │   Valuation      │
           │    Lambda       │     │    Lambda (1h)   │     │    Lambda        │
           │   (No data)     │     │   (No data)      │     │   (Ready)        │
           └────────┬────────┘     └─────────┬────────┘     └─────────┬────────┘
                    │                        │                        │
                    ▼                        ▼                        ▼
           ┌─────────────────────────────────────────────────────────────────────┐
           │                         Redis Cache                                 │
           │   • floor_prices: empty                                             │
           │   • deals: empty                                                    │
           └─────────────────────────────────┬───────────────────────────────────┘
                                             │
                                             ▼
           ┌─────────────────────────────────────────────────────────────────────┐
           │                    App Runner (FastAPI)                             │
           │   • /health: ✅ healthy                                             │
           │   • /api/v1/valuation/stats/floors: {} (no data)                   │
           │   • /api/v1/market/sales/recent: 500 (no data)                     │
           └─────────────────────────────────┬───────────────────────────────────┘
                                             │
                                             ▼
           ┌─────────────────────────────────────────────────────────────────────┐
           │                    Frontend (Next.js on Vercel)                     │
           │   • app.axiepro.io                                                  │
           │   • Connected to API ✅                                             │
           │   • CORS fixed ✅                                                   │
           │   • Shows empty/loading states (no data to display)                │
           └─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Recommendations

### Immediate (P0) - Fix Data Pipeline

1. **Implement Rate Limiting in Lambda**
   ```python
   # Add exponential backoff
   @retry(
       stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=4, max=60),
       retry=retry_if_exception_type(HTTPStatusError)
   )
   async def fetch_with_retry(url, params):
       ...
   ```

2. **Reduce API Call Frequency**
   - Price ingestion: 5 min → 15 min
   - Sales ingestion: 15 min → 30 min
   - Listings ingestion: 5 min → 15 min

3. **Add Request Throttling**
   - Implement token bucket or leaky bucket
   - Max 10 requests/minute to SkyMavis

4. **Check SkyMavis API Key Quota**
   - Review API plan limits
   - Consider upgrading if needed

### Short-term (P1) - Improve Resilience

5. **Circuit Breaker Pattern**
   - Stop calling API after N consecutive failures
   - Wait cooldown period before retrying

6. **Request Caching**
   - Cache API responses in Redis (5-15 min TTL)
   - Avoid duplicate requests for same data

7. **Stagger Lambda Invocations**
   - Don't trigger all ingestion at same time
   - Spread across different minute offsets

### Medium-term (P2) - Operational Excellence

8. **API Usage Dashboard**
   - Track requests/minute to external APIs
   - Alert before hitting quota

9. **Dead Letter Queue Processing**
   - Automatically retry failed ingestions
   - Alert on DLQ depth

10. **Multi-Source Fallback**
    - Add backup data sources (Moralis, direct RPC)
    - Failover when primary is rate-limited

---

## 5. Code Locations for Fixes

| Fix | File | Lines |
|-----|------|-------|
| Rate limiting | `backend/src/services/skymavis_client.py` | 245-300 |
| Lambda schedules | `infrastructure/lib/stacks/compute-stack.ts` | 400-450 |
| Retry logic | `backend/src/lambdas/price_ingestion.py` | 150-200 |
| Circuit breaker | New file needed | - |

---

## 6. Verification Commands

```bash
# Check Lambda errors in last hour
aws logs filter-log-events \
  --log-group-name /aws/lambda/axiepro-price-ingestion-dev \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --region us-east-1

# Check if data is being stored
aws dynamodb scan \
  --table-name axiepro-checkpoints-dev \
  --region us-east-1 \
  --max-items 5

# Test SkyMavis API directly (with rate limit)
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://api-gateway.skymavis.com/graphql/axie-marketplace" \
  -d '{"query": "{ axies(size: 1) { results { id class } } }"}'
```

---

## 7. Summary

### Infrastructure: ✅ Well-Architected
The AWS infrastructure follows best practices with proper security, observability, and scalability patterns.

### Operations: ❌ Data Pipeline Blocked
The critical issue is external API rate limiting, not infrastructure misconfiguration.

### Next Steps
1. Implement rate limiting in Lambda functions
2. Reduce ingestion frequency
3. Add retry with exponential backoff
4. Monitor and alert on API quota usage

---

*Generated by PP (Purpose Prompter) - UNDERSTANDING dimension*
