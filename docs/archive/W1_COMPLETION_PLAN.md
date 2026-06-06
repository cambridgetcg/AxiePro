# W1 Completion Plan: Production Ready

**Current Status:** 75% Complete
**Target:** 100% Complete (Ready for Beta)
**Timeline:** 2-3 Days
**Critical Blocker:** Metadata rate limiting (20 axies/hour → need 200+/hour)

---

## Zero Point Summary

### ✅ What's Working (75%)

**Backend Infrastructure:**
- App Runner API deployed and responding: `https://nu8bq2ckxs.us-east-1.awsapprunner.com`
- 11 route modules operational (auth, axies, market, valuation, breeding, wallets, meta)
- Aurora PostgreSQL: 8/8 migrations applied
- ElastiCache Redis: Connected and caching

**Data Pipeline:**
- ✅ Sales ingestion: 24/24 inserted daily (Ronin RPC)
- ✅ Listings ingestion: Every 5 minutes (SkyMavis API)
- ✅ Price ingestion: Every 15 minutes (floor price snapshots)
- ✅ Deal detection: Real-time on Kinesis
- ✅ Meta analysis: Every 2 hours
- ⚠️ Metadata ingestion: 20 axies/hour (RATE LIMITED - blocker)

**Frontend:**
- 9 pages deployed on Vercel
- 3/7 core pages fully wired: Explorer, Market, Deals
- Deal detection showing normalized scoring
- Real-time floor prices by class
- Responsive UI with Tailwind + shadcn/ui

**Infrastructure:**
- All 10 CDK stacks deployed (api, database, cache, networking, events, compute, observability, storage, security, cicd)
- EventBridge scheduled rules configured
- CloudWatch logging active

### ❌ Critical Blocker (25%)

**Metadata Coverage: ~20% (Target: 80%+)**

**Problem:**
- Current rate: 20 axies/hour
- Need: 200+ axies/hour (10x increase)
- Impact: Floor prices incomplete, valuation confidence low

**Root Cause:**
- `backend/src/lambdas/metadata_ingestion.py:43-46`
  - `MAX_AXIES_PER_RUN = 10` (too conservative)
  - `BATCH_DELAY_SECONDS = 6.0` (too slow)
  - Rate limit protection = 10 axies / 60 seconds = 10/min = 600/hour theoretical max
  - But actual: only 20/hour due to Lambda timeout and batch size

**Solution Path:** See below ↓

---

## W1 Completion Checklist

```
W1 Exit Criteria (from PURPOSE.md):
- [X] `/deals` page accessible and showing data        ← DONE
- [ ] Metadata coverage >80% for recent sales          ← BLOCKER
- [ ] All Lambdas executing on schedule                ← VERIFY
- [X] Data freshness <1 hour for listings              ← DONE (5 min)
```

**Status: 2/4 complete, 1 to verify, 1 critical blocker**

---

## Critical Path: Fix Metadata Rate Limiting

### Day 1: Verify & Diagnose (TODAY)

#### Task 1.1: Verify EventBridge Rules Enabled
```bash
# Check if all 7 scheduled Lambdas have active EventBridge triggers
# CloudWatch Console → Events → Rules

Expected rules:
1. sales_ingestion_rule (every 30 min) - VERIFY
2. listings_ingestion_rule (every 5 min) - VERIFY
3. metadata_ingestion_rule (every 60 min) - VERIFY
4. price_ingestion_rule (every 15 min) - VERIFY
5. meta_analyzer_rule (every 2 hours) - VERIFY
6. health_check_rule (every 5 min) - VERIFY
7. synthetic_flows_rule (every hour) - VERIFY

Action: Check each rule status = "Enabled"
Success: All 7 rules enabled, invocation count > 0 (past 24h)
```

**How to check:**
1. AWS Console → CloudWatch → Events → Rules
2. For each rule:
   - Verify "State" = "Enabled"
   - Check "Invocations" metric (should be > 0)
3. If any disabled: Click "Actions" → "Enable"

#### Task 1.2: Audit Metadata Ingestion Logs
```bash
# Review metadata_ingestion Lambda logs for errors

# CloudWatch Console:
# Logs → Log groups → /aws/lambda/metadata_ingestion
# Filter: Last 24 hours

Look for:
- Rate limit errors (HTTP 429)
- Batch failures
- Timeout errors
- Success rate

Success: Understand exact bottleneck (rate limit vs timeout vs other)
```

**Key metrics to extract:**
- Total axies processed (count "Successfully fetched metadata")
- Rate limit errors (count "429" or "rate limit")
- Average batch processing time
- Lambda timeout occurrences

#### Task 1.3: Calculate Current Metadata Coverage
```sql
-- Connect to Aurora PostgreSQL and run:

-- Total unique axies in listings (target universe)
SELECT COUNT(DISTINCT axie_id) AS total_listings
FROM listings
WHERE status = 'active';

-- Total unique axies with metadata
SELECT COUNT(DISTINCT axie_id) AS total_metadata
FROM axie_metadata;

-- Coverage percentage
SELECT
  (SELECT COUNT(DISTINCT axie_id) FROM axie_metadata) * 100.0 /
  NULLIF((SELECT COUNT(DISTINCT axie_id) FROM listings WHERE status = 'active'), 0)
  AS coverage_pct;

-- Missing metadata for active listings
SELECT COUNT(DISTINCT l.axie_id) AS missing_metadata
FROM listings l
LEFT JOIN axie_metadata m ON l.axie_id = m.axie_id
WHERE l.status = 'active' AND m.axie_id IS NULL;
```

**Success:** Baseline coverage % documented (likely 10-30%)

---

### Day 2: Implement Fix (TOMORROW)

#### Option A: Optimize SkyMavis Batching (RECOMMENDED)

**Current Settings:**
```python
# backend/src/lambdas/metadata_ingestion.py:43-46
MAX_AXIES_PER_RUN = 10      # Too small
BATCH_DELAY_SECONDS = 6.0   # Too conservative
```

**Proposed Changes:**
```python
MAX_AXIES_PER_RUN = 50      # 5x increase
BATCH_DELAY_SECONDS = 2.0   # 3x faster
```

**Expected Throughput:**
- Old: 10 axies / 60 sec = 10/min = 600/hour theoretical (20/hour actual)
- New: 50 axies / 120 sec = 25/min = 1500/hour theoretical (target 200+/hour)

**Implementation:**
```bash
# 1. Edit the file
code backend/src/lambdas/metadata_ingestion.py

# 2. Change lines 43-46:
MAX_AXIES_PER_RUN = 50
BATCH_DELAY_SECONDS = 2.0

# 3. Add exponential backoff for rate limits (if not present):
# On 429 error:
#   - First retry: wait 5s
#   - Second retry: wait 15s
#   - Third retry: wait 45s
#   - Then skip batch

# 4. Deploy
cd infrastructure
npm run cdk deploy compute-stack
```

**Risk:** May hit SkyMavis rate limit harder
**Mitigation:** Monitor CloudWatch for 429 errors, adjust if needed

#### Option B: Enable Moralis Parallel Source (BACKUP)

**Current:** SkyMavis only
**Proposed:** Query Moralis in parallel, merge results

**Implementation:**
```python
# backend/src/lambdas/metadata_ingestion.py

# Add Moralis client import (already exists in codebase)
from src.services.moralis_client import MoralisClient

# In fetch loop:
async def fetch_metadata(axie_ids):
    # Try SkyMavis first
    skymavis_results = await skymavis_client.fetch_axies(axie_ids)

    # If rate limited, use Moralis
    if skymavis_results.status_code == 429:
        moralis_results = await moralis_client.fetch_axie_metadata(axie_ids)
        return moralis_results

    return skymavis_results
```

**Cost:** Moralis API calls (paid)
**Use when:** Option A fails or insufficient

#### Option C: Request Higher SkyMavis Rate Limit (PARALLEL)

**Action:**
1. Contact SkyMavis Developer Relations
2. Explain use case: "Building Axie trading analytics platform, need higher rate limit for metadata ingestion"
3. Request: 1000 requests/hour (currently ~100?)

**Timeline:** Unknown (could be weeks)
**Recommendation:** Submit request, don't wait for response

---

### Day 3: Validate & Monitor (DAY AFTER TOMORROW)

#### Task 3.1: Deploy Metadata Ingestion Changes
```bash
cd infrastructure
npm run cdk deploy compute-stack

# Verify deployment
aws lambda get-function --function-name metadata_ingestion --region us-east-1

# Check EventBridge trigger still active
aws events list-rules --name-prefix metadata_ingestion --region us-east-1
```

**Success:** Lambda updated, trigger still enabled

#### Task 3.2: Monitor Ingestion for 24 Hours
```bash
# CloudWatch Logs Insights query:

fields @timestamp, @message
| filter @message like /Successfully fetched metadata/
| stats count() as axies_processed by bin(1h)
| sort @timestamp desc

# Expected: 200+ axies/hour sustained
```

**Metrics to track:**
- Axies processed per hour (target: 200+)
- Rate limit errors (target: <5%)
- Lambda duration (should not timeout)
- Coverage % increasing (query hourly)

#### Task 3.3: Verify W1 Completion
```
Final Checklist:
- [ ] Metadata coverage >80% (SQL query)
- [ ] All EventBridge rules enabled (CloudWatch check)
- [ ] No critical Lambda errors (past 24h logs)
- [ ] Deal detection showing accurate valuations (E2E test)

E2E Test:
1. Go to https://axiepro.vercel.app/explorer
2. Search for a random Axie ID (e.g., 12345678)
3. View valuation card
4. Check "Confidence: High" (not "Low - missing metadata")
5. Go to /deals page
6. Verify deals show "normalized score" (not errors)
7. Check data timestamp (<1 hour old)

Success: All 7 steps pass
```

---

## Immediate Actions (Next 3 Hours)

### Action 1: Verify Lambda Schedules
```
Time: 30 minutes
Who: You (via AWS Console)
What:
1. Open AWS Console → CloudWatch → Events → Rules
2. Check 7 rules listed above
3. Verify all "Enabled"
4. Check invocation metrics (past 24h)
5. Document findings in FINDINGS.md

Success: Know which Lambdas are running, which aren't
```

### Action 2: Calculate Metadata Coverage
```
Time: 15 minutes
Who: You (via database client or Lambda query)
What:
1. Connect to Aurora PostgreSQL
2. Run SQL queries from Task 1.3
3. Document coverage % (e.g., "23% coverage, 15,234 missing")

Success: Baseline coverage % known
```

### Action 3: Review Metadata Ingestion Code
```
Time: 30 minutes
Who: You (code review)
What:
1. Read backend/src/lambdas/metadata_ingestion.py
2. Understand current batching logic
3. Identify exact rate limit handling
4. Note BATCH_DELAY_SECONDS, MAX_AXIES_PER_RUN values

Success: Understand code, ready to modify tomorrow
```

### Action 4: Plan Fix Implementation
```
Time: 30 minutes
Who: You (planning)
What:
1. Decide: Option A (optimize batching) or Option B (Moralis)
2. Write out exact code changes needed
3. Identify deployment steps
4. Plan monitoring approach

Success: Clear plan for Day 2 implementation
```

---

## Success Metrics

**W1 Complete When:**
1. Metadata coverage: >80% (from ~20%)
2. Metadata ingestion: >200 axies/hour (from 20/hour)
3. All Lambdas: Executing on schedule (verified in CloudWatch)
4. E2E test: Passes (Explorer → Valuation → Deals all working)

**Then:** Ready to recruit beta users (W2)

---

## Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Rate limit increase doesn't work | MEDIUM | HIGH | Option B: Enable Moralis parallel ingestion |
| Moralis API costs too high | LOW | MEDIUM | Monitor usage, optimize caching, request SkyMavis limit increase |
| Lambda timeout with larger batches | MEDIUM | MEDIUM | Reduce batch size to 30, increase timeout to 15min |
| Coverage doesn't reach 80% in 3 days | MEDIUM | HIGH | Extend timeline, prioritize active listings only |

---

## After W1 Completion

**Next Waypoint: W2 Beta Launch**

Immediate tasks:
1. Wire analytics page to real data (1 day)
2. Add error boundaries to frontend (1 day)
3. Create beta onboarding guide (2 hours)
4. Recruit 10 beta users from Axie Discord (3-5 days)

**Timeline:** W2 complete in 7-10 days after W1

---

## File References

**Backend:**
- `backend/src/lambdas/metadata_ingestion.py` - Rate limiting fix needed here
- `backend/src/services/skymavis_client.py` - SkyMavis API client
- `backend/src/services/moralis_client.py` - Moralis API client (backup)

**Infrastructure:**
- `infrastructure/lib/stacks/compute-stack.ts` - Lambda deployment config
- `infrastructure/lib/stacks/events-stack.ts` - EventBridge rules

**Database:**
- `database/02_ingestion_tables.sql` - axie_metadata table schema
- `database/07_ingestion_metadata.sql` - Ingestion progress tracking

**Monitoring:**
- CloudWatch: `/aws/lambda/metadata_ingestion` - Lambda logs
- CloudWatch Events: `metadata_ingestion_rule` - Schedule trigger

---

## Support Resources

**Documentation:**
- `PURPOSE.md` - High-level waypoints and success criteria
- `DEVELOPMENT_PATH.md` - Detailed execution plans for W1-W5
- `PATH_FORWARD.md` - Comprehensive development roadmap (this file)

**GUA Knowledge:**
- Insights saved to AWS (cross-device access)
- Run `gua search metadata` to find related patterns
- Run `gua search "rate limit"` for similar issues

**Codebase Assessment:**
- Explore agent a3ab103 completed full codebase assessment
- Zero point baseline documented
- All file references mapped

---

*Plan created: 2026-01-30*
*Target completion: 2026-02-02*
*Next review: After Day 1 tasks complete*
