# ✅ Moralis Switch Deployment Complete

**Date:** 2026-01-30 16:46 UTC
**Status:** DEPLOYED & VERIFIED
**Next Run:** Every 2 hours at :40 past the hour (e.g., 18:40, 20:40 UTC)

---

## Deployment Summary

### ✅ Lambda Function Updated
- **Function:** `axiepro-metadata-ingestion-dev`
- **Last Modified:** 2026-01-30 16:46:34 UTC (just deployed)
- **Code Size:** 266,975 bytes (includes new Moralis logic)
- **Timeout:** 300 seconds (5 min)
- **Memory:** 256 MB

### ✅ EventBridge Trigger Verified
- **Rule:** `axiepro-metadata-ingestion-trigger-dev`
- **State:** **ENABLED** ✓
- **Schedule:** Every 2 hours
- **Next Run:** Check current time, next execution at :40 past the hour

### ✅ Changes Deployed
1. **Primary API:** Moralis (replaces SkyMavis)
2. **Fallback API:** SkyMavis (genes only, optional)
3. **Batch Size:** 10 axies (increased from 1)
4. **Max Per Run:** 100 axies (increased from 10)
5. **Batch Delay:** 2 seconds (reduced from 6)

---

## What Changed: Before vs After

| Aspect | BEFORE (SkyMavis-only) | AFTER (Moralis-first) | Improvement |
|--------|------------------------|----------------------|-------------|
| **Primary API** | SkyMavis GraphQL | **Moralis NFT API** | Separate rate limit pool |
| **Rate Limiting** | 100% 429 errors | Expected <5% errors | No more blocking |
| **Axies/batch** | 1 | **10** | 10x |
| **Max/run** | 10 | **100** | 10x |
| **Throughput** | **0 axies/hour** | **Target: 100+ axies/hour** | ∞ (was 0) |
| **Daily capacity** | **0 axies** | **1,200 axies** | ∞ (was 0) |
| **Data source** | Single (SkyMavis) | **Hybrid (Moralis + SkyMavis)** | More resilient |
| **Genes fallback** | None | SkyMavis (optional) | Best effort enrichment |

---

## Expected Results (Next Run)

### Success Indicators (CloudWatch Logs)

**What to look for at next :40 minute mark:**

```
✅ GOOD: "Starting Moralis-first metadata ingestion"
✅ GOOD: "Found X axies from active listings missing metadata"
✅ GOOD: "Processing 100 axies (limit: 100)"
✅ GOOD: "Batch 1/10: fetched 10/10 axies from Moralis"
✅ GOOD: "Batch 1/10: stored 10 axies"
✅ GOOD: "Metadata ingestion complete: fetched 100, stored 100"

❌ BAD: "429 Too Many Requests" (if Moralis also rate limits)
⚠️ PARTIAL: "Batch 1/10: fetched 5/10" (some failures, but better than 0)
```

### CloudWatch Metrics (New)

1. **AxiesFetched**
   - Old: 0
   - Target: 100
   - Watch for: Consistent 100 per run

2. **AxiesStored**
   - Old: 0
   - Target: 100
   - Watch for: Matches AxiesFetched

3. **AxiesEnriched** (NEW)
   - Tracks how many got SkyMavis gene data
   - Expected: 0-100 (optional, not critical)

---

## Monitoring Plan

### Immediate (Next 2-4 Hours)

**Action 1: Wait for Next Scheduled Run**
- Lambda runs every 2 hours at :40 past the hour
- Current time: ~16:46 UTC
- Next run: **18:40 UTC** (in ~2 hours)

**Action 2: Check CloudWatch Logs**
```bash
# At 18:40 UTC, run:
aws logs tail /aws/lambda/axiepro-metadata-ingestion-dev \
  --region us-east-1 \
  --since 10m \
  --follow
```

**Action 3: Verify Metrics**
```bash
# Check AxiesFetched metric (should be >0)
aws cloudwatch get-metric-statistics \
  --namespace AxiePro \
  --metric-name AxiesFetched \
  --dimensions Name=service,Value=axiepro-datafeed \
  --statistics Sum \
  --start-time $(date -u -v-3H '+%Y-%m-%dT%H:%M:%S') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%S') \
  --period 3600 \
  --region us-east-1
```

### Short-term (24 Hours)

**Day 2 Goals:**
- [ ] Verify 100+ axies fetched per run (consistent)
- [ ] No 429 errors in logs
- [ ] 12 runs completed (every 2 hours)
- [ ] Total fetched: 1,200+ axies
- [ ] Database coverage improving (run SQL query)

**Database Coverage Query:**
```sql
-- Run this after 24 hours to check improvement
SELECT
  COUNT(DISTINCT m.axie_id) AS total_with_metadata,
  COUNT(DISTINCT l.axie_id) AS total_active_listings,
  (COUNT(DISTINCT m.axie_id) * 100.0 / COUNT(DISTINCT l.axie_id)) AS coverage_pct,
  (COUNT(DISTINCT m.axie_id) * 100.0 / COUNT(DISTINCT l.axie_id)) -
    LAG(COUNT(DISTINCT m.axie_id) * 100.0 / COUNT(DISTINCT l.axie_id)) OVER (ORDER BY DATE_TRUNC('day', NOW())) AS improvement_pct
FROM listings l
LEFT JOIN axie_metadata m ON l.axie_id = m.axie_id
WHERE l.status = 'active';
```

### Medium-term (3-7 Days)

**W1 Completion Criteria:**
- [ ] Metadata coverage >80% for active listings
- [ ] Consistent throughput (100+ axies/hour)
- [ ] No critical errors in pipeline

**Estimated Time to 80% Coverage:**
- If 5,000 active listings: 5,000 / 1,200/day = ~4 days
- If 10,000 active listings: 10,000 / 1,200/day = ~8 days
- If 50,000 active listings: 50,000 / 1,200/day = ~42 days

**Adjustment Options if Needed:**
1. Increase MAX_AXIES_PER_RUN to 200 (if Moralis allows)
2. Increase run frequency to every hour (instead of 2 hours)
3. Run multiple parallel batches (spawn additional Lambdas)

---

## Troubleshooting

### If Next Run Still Shows 0 Axies Fetched

**Check 1: Moralis API Key**
```bash
# Verify Moralis key is in secrets
aws secretsmanager get-secret-value \
  --secret-id axiepro-secrets-dev \
  --region us-east-1 \
  --query SecretString \
  --output text | jq -r '.MORALIS_API_KEY'
```

**Check 2: Lambda Code Deployed**
```bash
# Confirm Lambda has new code
aws lambda get-function --function-name axiepro-metadata-ingestion-dev \
  --region us-east-1 \
  --query 'Configuration.CodeSha256'
```

**Check 3: CloudWatch Error Logs**
```bash
# Look for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/axiepro-metadata-ingestion-dev \
  --region us-east-1 \
  --start-time $(($(date +%s) - 3600))000 \
  --filter-pattern "ERROR"
```

### If Moralis Also Rate Limits

**Symptoms:**
- Logs show "Moralis rate limited, waiting 60s"
- AxiesFetched < 100 (partial success)

**Solutions:**
1. Reduce AXIES_PER_BATCH from 10 to 5
2. Increase BATCH_DELAY_SECONDS from 2 to 5
3. Reduce MAX_AXIES_PER_RUN from 100 to 50
4. Contact Moralis support for higher rate limit

**Code to adjust:**
```python
# In metadata_ingestion.py, modify:
AXIES_PER_BATCH = 5  # Reduce from 10
BATCH_DELAY_SECONDS = 5.0  # Increase from 2.0
MAX_AXIES_PER_RUN = 50  # Reduce from 100
```

Then redeploy:
```bash
cd infrastructure
npm run cdk deploy AxiePro-Compute-dev --require-approval never
```

---

## Rollback Plan (If Needed)

### Option 1: Restore Original SkyMavis-Only Code

**⚠️ WARNING:** This will return to 0 throughput (100% 429 errors)

```bash
cd backend/src/lambdas
cp metadata_ingestion.py.backup metadata_ingestion.py
cd ../../infrastructure
npm run cdk deploy AxiePro-Compute-dev --require-approval never
```

### Option 2: Disable Metadata Ingestion Temporarily

```bash
# Disable EventBridge rule (stops scheduled runs)
aws events disable-rule \
  --name axiepro-metadata-ingestion-trigger-dev \
  --region us-east-1
```

### Option 3: Adjust Parameters (Recommended)

Better to reduce throughput targets than rollback completely:
- Reduce MAX_AXIES_PER_RUN to 50
- Reduce AXIES_PER_BATCH to 5
- Increase BATCH_DELAY_SECONDS to 5
- Monitor and iterate

---

## Files & Documentation

| File | Purpose |
|------|---------|
| `backend/src/lambdas/metadata_ingestion.py` | **LIVE CODE** (Moralis-first) |
| `backend/src/lambdas/metadata_ingestion.py.backup` | Backup (SkyMavis-only) |
| `backend/src/lambdas/metadata_ingestion_moralis.py` | Source (development) |
| `MORALIS_SWITCH_SUMMARY.md` | Implementation details |
| `W1_FINDINGS.md` | Diagnostic that led to this fix |
| `DEPLOYMENT_COMPLETE.md` | **THIS FILE** - Deployment status |

---

## Success Criteria Checklist

### Deployment Phase (COMPLETE)
- [X] Code modified with Moralis-first approach
- [X] Original backed up to `metadata_ingestion.py.backup`
- [X] CDK deployed successfully
- [X] Lambda function updated (verified: 16:46:34 UTC)
- [X] EventBridge trigger still enabled (verified)

### Verification Phase (IN PROGRESS)
- [ ] Wait for next run at :40 past the hour
- [ ] Check CloudWatch logs for success
- [ ] Verify AxiesFetched metric > 0
- [ ] Confirm no 429 errors in logs

### W1 Completion Phase (PENDING)
- [ ] 24h throughput: 1,000+ axies
- [ ] Metadata coverage improving
- [ ] Time to 80% coverage estimated
- [ ] W1 complete and ready for W2 (beta users)

---

## Next Action Items

### YOU (User):
1. **Wait for next run** - Lambda executes at :40 past the hour (e.g., 18:40 UTC)
2. **Check logs at that time** - CloudWatch `/aws/lambda/axiepro-metadata-ingestion-dev`
3. **Report results** - Share if you see success or errors

### AUTOMATED:
1. Lambda will run every 2 hours automatically
2. CloudWatch will collect metrics
3. EventBridge will trigger on schedule

### MONITORING (Tomorrow):
1. Run database coverage query (see above)
2. Check 24h throughput
3. Estimate time to 80% coverage
4. Adjust parameters if needed

---

**Current Time:** ~16:46 UTC
**Next Run:** ~18:40 UTC (check current time for exact)
**Status:** ✅ DEPLOYED, waiting for next scheduled execution

---

*Deployment completed: 2026-01-30 16:46 UTC*
*Moralis-first metadata ingestion is now LIVE*
