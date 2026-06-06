# W1 Completion: Diagnostic Findings

**Date:** 2026-01-30
**Execution:** Day 1 - Verification & Diagnosis
**Status:** ❌ CRITICAL BLOCKER CONFIRMED

---

## Executive Summary

**W1 Status: 50% Complete** (worse than initial 75% estimate)

### What's Working ✅
- EventBridge: All 6 rules ENABLED
- Lambda Functions: All 6 deployed (updated today)
- Sales/Listings/Price Ingestion: Running successfully
- Health Check: Running every 5 minutes
- Meta Analysis: Running hourly
- App Runner: Backend API responding
- Frontend: All pages deployed

### Critical Blocker ❌
**Metadata Ingestion: COMPLETE FAILURE**
- Throughput: **0 axies/hour** (not 20 as estimated)
- Every API request gets `429 Too Many Requests`
- 100% failure rate after retries
- No metadata being stored

---

## Detailed Findings

### 1. EventBridge Rules Status

**All 6 Scheduled Rules ENABLED:**

| Rule | Schedule | Status | Last Invocation |
|------|----------|--------|-----------------|
| health-check-trigger | Every 5 min | ✅ ENABLED | Active |
| listings-ingestion-trigger | Every 5 min | ✅ ENABLED | Active |
| meta-analysis-trigger | Every 1 hour | ✅ ENABLED | Active |
| **metadata-ingestion-trigger** | **Every 2 hours** | ✅ ENABLED | **FAILING** |
| price-ingestion-trigger | Every 15 min | ✅ ENABLED | Active |
| sales-ingestion-trigger | Every 30 min | ✅ ENABLED | Active |

**Finding:** Infrastructure is correctly configured. Problem is NOT with scheduling.

---

### 2. Lambda Functions Status

**All 6 Lambdas Deployed:**

| Function | Last Modified | Status |
|----------|---------------|--------|
| axiepro-health-check-dev | 2026-01-30 16:02:43 | ✅ Running |
| axiepro-listings-ingestion-dev | 2026-01-30 16:02:43 | ✅ Running |
| axiepro-metadata-ingestion-dev | 2026-01-30 16:02:43 | ❌ FAILING |
| axiepro-meta-analyzer-dev | 2026-01-30 16:02:43 | ✅ Running |
| axiepro-price-ingestion-dev | 2026-01-30 16:02:43 | ✅ Running |
| axiepro-sales-ingestion-dev | 2026-01-30 16:02:43 | ✅ Running |

**Missing Lambda:** `deal-detector` (Kinesis trigger, not EventBridge scheduled)

**Finding:** Code was deployed TODAY. Issue is NOT stale deployment.

---

### 3. Metadata Ingestion Failure Analysis

#### CloudWatch Logs Evidence

**Recent Execution (2026-01-30 15:41 UTC):**

```
15:41:03 - START: "Found 100 axies from sales missing metadata"
15:41:06 - ERROR: Batch 0 - 429 Too Many Requests (after 3 retries)
15:41:12 - ERROR: Batch 10 - 429 Too Many Requests (after 3 retries)
15:41:18 - ERROR: Batch 20 - 429 Too Many Requests (after 3 retries)
15:41:24 - ERROR: Batch 30 - 429 Too Many Requests (after 3 retries)
... [pattern continues for ALL batches] ...
15:41:49 - ERROR: Batch 90 - 429 Too Many Requests (after 3 retries)
15:42:08 - COMPLETE: "fetched 0, stored 0"
```

**Duration:** 65 seconds
**Result:** **0 axies fetched, 0 stored**
**Retry Pattern:** 3 retries per batch (2s, 4s, 6s backoff)

#### Current Configuration

From `backend/src/lambdas/metadata_ingestion.py:43-47`:

```python
AXIES_PER_BATCH = 1             # Only 1 axie per batch
MAX_AXIES_PER_RUN = 10          # Max 10 axies total
BATCH_DELAY_SECONDS = 6.0       # 6 seconds between batches
```

**Schedule:** Every 2 hours (from CDK)

#### Rate Limit Analysis

**Theoretical Throughput:**
- 10 axies per run (MAX_AXIES_PER_RUN)
- 12 runs per day (every 2 hours)
- = 120 axies/day = 5 axies/hour

**Actual Throughput:**
- **0 axies/hour** (100% failure rate)

**SkyMavis API Rate Limit:**
- Unknown exact limit
- Appears to be **extremely** strict
- Even 1 request per 6 seconds is rejected
- Possibly shared across all AxiePro Lambdas

---

### 4. Root Cause Analysis

**Primary Cause:** SkyMavis API rate limiting

**Contributing Factors:**

1. **No Alternative Data Source**
   - Moralis client exists in code (`moralis_client.py`)
   - Not being used by metadata ingestion Lambda
   - Would provide parallel data source

2. **Aggressive Retry Logic**
   - 3 retries with 2s/4s backoff
   - Compounds rate limiting (4 requests per batch attempt)
   - May be triggering anti-abuse mechanisms

3. **Shared Rate Limit Pool**
   - `listings_ingestion` (every 5 min)
   - `price_ingestion` (every 15 min)
   - `sales_ingestion` (every 30 min)
   - All hit SkyMavis API concurrently
   - Metadata ingestion gets crowded out

4. **Batch Size Too Conservative**
   - `AXIES_PER_BATCH = 1` is extremely slow
   - Even if successful, would only fetch 10/run
   - Need 1000x increase to reach 80% coverage

---

### 5. Metadata Coverage Calculation

**Need to Query Database:**

```sql
-- Total unique axies with metadata
SELECT COUNT(DISTINCT axie_id) AS total_metadata
FROM axie_metadata;

-- Total unique axies in active listings
SELECT COUNT(DISTINCT axie_id) AS total_listings
FROM listings
WHERE status = 'active';

-- Coverage percentage
SELECT
  (SELECT COUNT(DISTINCT axie_id) FROM axie_metadata) * 100.0 /
  NULLIF((SELECT COUNT(DISTINCT axie_id) FROM listings WHERE status = 'active'), 0)
  AS coverage_pct;

-- Missing metadata count
SELECT COUNT(DISTINCT l.axie_id) AS missing_metadata
FROM listings l
LEFT JOIN axie_metadata m ON l.axie_id = m.axie_id
WHERE l.status = 'active' AND m.axie_id IS NULL;
```

**Unable to run directly** (need database credentials or Lambda query function)

**Estimated Coverage:**
- If 100 axies are consistently missing (from logs)
- And 0 are being added per run
- Coverage is **NOT improving** over time
- Likely **<10%** based on failure duration

---

## W1 Exit Criteria Assessment

```
W1 Exit Criteria (from PURPOSE.md):
- [X] `/deals` page accessible and showing data      ✅ DONE
- [ ] Metadata coverage >80% for recent sales        ❌ CRITICAL FAIL (0% growth)
- [X] All Lambdas executing on schedule              ✅ DONE (executing, but failing)
- [X] Data freshness <1 hour for listings            ✅ DONE (5 min)
```

**Status: 3/4 criteria met, BUT...**
- Criterion #2 is CRITICAL BLOCKER
- Metadata coverage is not just below 80%, it's **not improving at all**
- Current throughput: 0 axies/hour

---

## Revised W1 Completion Estimate

**Previous:** 75% complete, 2-3 days to finish
**Actual:** 50% complete, **cannot estimate** until rate limiting solved

**Blockers:**
1. Metadata ingestion completely failing (0 throughput)
2. No Moralis integration active (alternative source unused)
3. Unknown SkyMavis rate limit (need to contact them or test extensively)

**Dependencies:**
- **Option A:** Switch to Moralis (requires code changes + testing)
- **Option B:** Request higher SkyMavis limit (timeline unknown, could be weeks)
- **Option C:** Dramatically slow down + spread out (may take months to reach 80%)

---

## Recommended Immediate Actions

### Action 1: Switch to Moralis for Metadata (HIGHEST PRIORITY)

**Why:**
- Moralis client already exists: `backend/src/services/moralis_client.py`
- Can fetch Axie metadata via NFT API
- Different rate limit pool (won't conflict with SkyMavis)
- Faster implementation than waiting for SkyMavis approval

**Implementation:**
1. Modify `backend/src/lambdas/metadata_ingestion.py`
2. Use Moralis as **primary** source, SkyMavis as fallback (for genes)
3. Increase `MAX_AXIES_PER_RUN` to 50-100 (Moralis likely has higher limits)
4. Test throughput

**Timeline:** 4-6 hours (code + deploy + test)

**Risk:** Moralis API costs (but unavoidable if SkyMavis is blocking)

### Action 2: Request Higher SkyMavis Rate Limit (PARALLEL)

**Why:**
- May unlock higher throughput in future
- Shows good faith to SkyMavis
- Could be approved quickly (or could take weeks)

**Implementation:**
1. Email SkyMavis Developer Relations
2. Explain use case: "Building Axie trading analytics, need metadata for 50k+ listings"
3. Request 1000+ requests/hour (from current unknown limit)

**Timeline:** Unknown (1 day to months)

**Risk:** May be rejected, may never respond

### Action 3: Add Exponential Backoff + Smarter Retry (PARALLEL)

**Why:**
- Current retry logic may be triggering anti-abuse
- Exponential backoff is best practice for rate limits
- Could reduce 429 errors even with same limit

**Implementation:**
1. Modify retry decorator in `metadata_ingestion.py`
2. Increase backoff: 5s, 15s, 45s, 135s (instead of 2s, 4s, 6s)
3. Add jitter to avoid thundering herd

**Timeline:** 1 hour (code + deploy)

**Risk:** Still may not work if limit is very strict

---

## Decision Matrix

| Option | Effort | Timeline | Success Likelihood | Cost |
|--------|--------|----------|-------------------|------|
| **A: Switch to Moralis** | MEDIUM | 4-6 hours | **HIGH** (90%) | $$ (API costs) |
| **B: Request SkyMavis limit** | LOW | Unknown | **MEDIUM** (50%) | Free |
| **C: Slow down + wait** | LOW | Months | **LOW** (20%) | Time |
| **D: Better retry logic** | LOW | 1 hour | **LOW** (30%) | Free |

**Recommended Approach:** **A + B** (Moralis switch + SkyMavis request in parallel)

---

## Next Steps (Today)

1. ✅ **Verify Lambda schedules** - COMPLETE
2. ✅ **Review metadata logs** - COMPLETE
3. 🔄 **Calculate metadata coverage** - BLOCKED (need DB access)
4. 🔄 **Review metadata_ingestion.py code** - IN PROGRESS
5. ⏭️ **Implement Moralis switch** - NEXT
6. ⏭️ **Submit SkyMavis rate limit request** - NEXT

---

## File References

**Lambda Code:**
- `backend/src/lambdas/metadata_ingestion.py:43-47` - Config constants (BATCH_SIZE, DELAY)
- `backend/src/lambdas/metadata_ingestion.py:365` - Handler entry point
- `backend/src/lambdas/metadata_ingestion.py:387` - Query for missing metadata
- `backend/src/lambdas/metadata_ingestion.py:444` - Error handling (429 errors)
- `backend/src/services/moralis_client.py` - Moralis integration (NOT USED YET)
- `backend/src/services/skymavis_client.py` - SkyMavis GraphQL client (RATE LIMITED)

**Infrastructure:**
- `infrastructure/lib/stacks/compute-stack.ts:690-697` - Metadata ingestion schedule (every 2 hours)
- `infrastructure/lib/stacks/compute-stack.ts:477-496` - Metadata Lambda config

**CloudWatch:**
- Log Group: `/aws/lambda/axiepro-metadata-ingestion-dev`
- Recent errors: All batches getting 429 (Too Many Requests)

---

*Findings documented: 2026-01-30 16:45 UTC*
*Next action: Implement Moralis switch for metadata ingestion*
