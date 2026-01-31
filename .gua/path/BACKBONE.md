# Backbone: Current State → W1 (Production Ready)

**Built**: 2026-01-29
**Updated**: 2026-01-29 (Post AWS Infrastructure Review)
**Builder**: PP Path-Builder (Creativity Dimension)

## Critical Path Visualization

```
CURRENT STATE
     │
     │  ┌─────────────────────────────────────────────────────────┐
     │  │ B1-B3: COMPLETE ✅                                      │
     │  │   • Backend deployed (App Runner us-east-1)             │
     │  │   • Frontend connected (CORS fixed)                     │
     │  │   • E2E tests: 23/24 passing                            │
     │  └─────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  ⚠️ BLOCKER: SkyMavis API Rate Limiting (HTTP 429)              │
│  ─────────────────────────────────────────────────────────────  │
│  All Lambda ingestion functions failing.                        │
│  No new data entering the system.                               │
│  Floor prices API returns empty {}.                             │
└─────────────────────────────────────────────────────────────────┘
     │
     │  Must fix rate limiting before data can flow
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  B4: FIX RATE LIMITING (FOUNDATION)                             │
│  ─────────────────────────────────────────────────────────────  │
│  Actions:                                                       │
│    1. Add exponential backoff to SkyMavis client                │
│    2. Implement request throttling (token bucket)               │
│    3. Add circuit breaker pattern                               │
│    4. Reduce Lambda trigger frequency                           │
│  Exit Criteria:                                                 │
│    Lambda functions complete without 429 errors                 │
└─────────────────────────────────────────────────────────────────┘
     │
     │  [Rate limiting solved]
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  B5: RESUME DATA PIPELINE                                       │
│  ─────────────────────────────────────────────────────────────  │
│  Actions:                                                       │
│    1. Deploy updated Lambda functions                           │
│    2. Monitor first successful ingestion cycle                  │
│    3. Verify data in database (price_snapshots, sales)          │
│    4. Verify Redis cache populated (floor_prices)               │
│  Exit Criteria:                                                 │
│    Fresh data (<1 hour) in database and cache                   │
└─────────────────────────────────────────────────────────────────┘
     │
     │  [Data flowing]
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  B6: VALIDATE DATA-DRIVEN FEATURES                              │
│  ─────────────────────────────────────────────────────────────  │
│  Actions:                                                       │
│    1. Verify Market page shows floor prices                     │
│    2. Verify Deals page shows undervalued listings              │
│    3. Run full E2E test suite (24/24 pass)                      │
│    4. Run backfill for class metadata                           │
│  Exit Criteria:                                                 │
│    All features working with live data                          │
└─────────────────────────────────────────────────────────────────┘
     │
     │  [All features validated]
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  W1: PRODUCTION READY ✓                                         │
│  ─────────────────────────────────────────────────────────────  │
│  All criteria met:                                              │
│    ✓ Backend deployed and healthy                               │
│    ✓ Frontend connected to backend                              │
│    ✓ Data pipeline operational (no 429 errors)                  │
│    ✓ All features working with live data                        │
│    ✓ 24/24 E2E tests passing                                    │
└─────────────────────────────────────────────────────────────────┘
```

## Completed Steps

### B1: Deploy Backend ✅ COMPLETE
- App Runner service healthy at api.axiepro.io
- Aurora PostgreSQL connected
- Redis cache connected
- /health returns 200

### B2: Connect Frontend ✅ COMPLETE
- NEXT_PUBLIC_API_URL set in Vercel
- CORS origins configured
- Frontend making API calls

### B3: Validate Core Features ✅ PARTIAL
- 23/24 E2E tests passing
- 1 test failing due to no data (expected)

---

## Remaining Steps (Foundation Solidification)

### B4: Fix Rate Limiting [CRITICAL - CURRENT BLOCKER]

**Why this is the foundation**: Without solving rate limiting, no data flows, and all data-dependent features remain broken.

| Task | File | Change |
|------|------|--------|
| 4.1 Add exponential backoff | `backend/src/services/skymavis_client.py` | `@retry(wait=wait_exponential(...))` |
| 4.2 Add request throttling | `backend/src/services/skymavis_client.py` | Token bucket rate limiter |
| 4.3 Add circuit breaker | `backend/src/services/circuit_breaker.py` | New file |
| 4.4 Reduce frequencies | `infrastructure/lib/stacks/compute-stack.ts` | Change EventBridge rules |
| 4.5 Add response caching | `backend/src/services/skymavis_client.py` | Redis cache for API responses |

**Implementation Details**:

```python
# 4.1 Exponential backoff (tenacity library)
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    retry=retry_if_exception_type(httpx.HTTPStatusError)
)
async def fetch_with_retry(self, url: str, params: dict):
    ...
```

```python
# 4.2 Token bucket rate limiter
class RateLimiter:
    def __init__(self, requests_per_minute: int = 10):
        self.tokens = requests_per_minute
        self.max_tokens = requests_per_minute
        self.last_refill = time.time()

    async def acquire(self):
        # Refill tokens based on elapsed time
        # Block if no tokens available
```

```python
# 4.3 Circuit breaker
class CircuitBreaker:
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered

    def __init__(self, failure_threshold=5, recovery_timeout=60):
        ...
```

```typescript
// 4.4 Reduce EventBridge frequencies (compute-stack.ts)
// Before: rate(5 minutes)
// After: rate(15 minutes)
schedule: events.Schedule.rate(Duration.minutes(15)),
```

**Validation**:
```bash
# Test Lambda locally with new rate limiting
cd backend
python -c "
import asyncio
from src.services.skymavis_client import SkyMavisClient
async def test():
    async with SkyMavisClient() as client:
        for i in range(20):
            result = await client.get_axie(1)
            print(f'{i}: {result}')
asyncio.run(test())
"
```

---

### B5: Resume Data Pipeline [DEPENDS ON B4]

**Why second**: Once rate limiting is fixed, we need to deploy and verify data flows.

| Task | Command | Validation |
|------|---------|------------|
| 5.1 Deploy Lambda updates | `cdk deploy AxiePro-Compute-dev` | Stack updates |
| 5.2 Trigger test ingestion | Invoke Lambda manually | No 429 errors |
| 5.3 Check database | Query price_snapshots table | Recent rows exist |
| 5.4 Check Redis | `redis-cli HGETALL floor_prices` | Data present |

**Validation**:
```bash
# Check Lambda logs for success
aws logs filter-log-events \
  --log-group-name /aws/lambda/axiepro-price-ingestion-dev \
  --filter-pattern "SUCCESS" \
  --start-time $(date -d '1 hour ago' +%s)000

# Check data freshness
psql -c "SELECT MAX(created_at) FROM price_snapshots"
```

---

### B6: Validate Data-Driven Features [DEPENDS ON B5]

**Why third**: With data flowing, validate all features work with live data.

| Task | Test | Expected |
|------|------|----------|
| 6.1 Market page | `curl api.axiepro.io/api/v1/valuation/stats/floors` | Returns floor prices |
| 6.2 Deals page | Navigate to /deals | Shows listings |
| 6.3 Full E2E | `npx playwright test` | 24/24 pass |
| 6.4 Backfill | `python scripts/backfill_axie_class.py` | >90% coverage |

**Validation**:
```bash
# Full E2E test suite
cd frontend && npx playwright test --project=chromium

# Backfill class metadata
cd backend && python scripts/backfill_axie_class.py --limit 1000
```

---

## Dependency Graph

```
B1 ✅ ──► B2 ✅ ──► B3 ✅ ──► B4 [CURRENT] ──► B5 ──► B6 ──► W1 ✓
         (done)    (done)    (done)     (blocking)
```

**Current focus**: B4 - Fix Rate Limiting

---

## Foundation Files to Modify

| Priority | File | Purpose |
|----------|------|---------|
| P0 | `backend/src/services/skymavis_client.py` | Add backoff, throttling, caching |
| P0 | `backend/src/services/circuit_breaker.py` | New: circuit breaker pattern |
| P0 | `infrastructure/lib/stacks/compute-stack.ts` | Reduce trigger frequencies |
| P1 | `backend/src/lambdas/price_ingestion.py` | Use new rate-limited client |
| P1 | `backend/src/lambdas/sales_ingestion.py` | Use new rate-limited client |
| P1 | `backend/src/lambdas/listings_ingestion.py` | Use new rate-limited client |

---

## Signals to Watch

| Signal | Meaning | Response |
|--------|---------|----------|
| 429 errors continue | Rate limiting insufficient | Reduce frequency more |
| Timeouts instead of 429 | Backoff too aggressive | Reduce wait times |
| Circuit breaker tripping | API unhealthy | Check SkyMavis status |
| Data gaps in database | Ingestion not running | Check EventBridge rules |
| Redis empty | Cache not populated | Check cache TTL config |

---

## Definition of Foundation Complete

All of the following must be true:

- [x] Backend deployed and healthy (B1)
- [x] Frontend connected (B2)
- [x] 23/24 E2E tests pass (B3)
- [ ] **No 429 errors in Lambda logs** (B4)
- [ ] **Fresh data in database** (<1 hour old) (B5)
- [ ] **Floor prices API returns data** (B6)
- [ ] **24/24 E2E tests pass** (B6)

When all checked → **W1: Production Ready** achieved.
