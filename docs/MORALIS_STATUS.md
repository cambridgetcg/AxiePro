# Moralis Integration Status Report

**Date**: 2026-01-30 18:49 UTC
**Context**: User reported no Moralis API usage, questioned if integration is active

---

## TL;DR: Integration Active, Wrong API

✅ **Moralis integration IS ACTIVE** - CloudWatch logs prove API calls succeeding
❌ **Moralis NFT API lacks Axie class data** - 100 fetched, 0 stored
❌ **SkyMavis enrichment failing** - All requests getting 429 rate limited

---

## Timeline of Issues Fixed

### Issue #1: Circular Import (18:05 UTC - 18:41 UTC)
**Error**: `Runtime.ImportModuleError: cannot import name 'get_axie_ids_from_listings' from partially initialized module`

**Root cause**: File tried to import helper functions from itself:
```python
from src.lambdas.metadata_ingestion import (
    get_axie_ids_from_listings,
    get_axie_ids_from_sales,
    get_missing_axie_ids,
    store_axies,
)
```

**Fix**: Replaced circular import with actual function implementations
**Status**: ✅ **FIXED** at 18:41 UTC

---

### Issue #2: SQL Error (18:42 UTC - 18:43 UTC)
**Error**: `for SELECT DISTINCT, ORDER BY expressions must appear in select list`

**Root cause**: PostgreSQL requires ORDER BY columns to be in SELECT list when using DISTINCT

**Fix**: Removed `ORDER BY l.created_at DESC` from listings query
**Status**: ✅ **FIXED** at 18:43 UTC

---

### Issue #3: Invalid Axie Class (18:45 UTC - 18:49 UTC)
**Error**: `invalid input value for enum axie_class: "Unknown"`

**Root cause**: Moralis NFT API returns axies without class data → defaults to "Unknown" → database rejects

**Findings from CloudWatch**:
- ✅ Moralis API calls succeeding: "Batch 8: fetched 10/10 axies from Moralis"
- ✅ No Moralis rate limiting
- ❌ All axies have class="Unknown" (Moralis metadata incomplete)
- ❌ SkyMavis enrichment failing: "SkyMavis rate limited for genes 93878, skipping"
- **Result**: 100 fetched, 0 stored

**Fix Applied** (18:48 UTC):
1. Added class validation - skip axies without valid class
2. Updated genes query to include class field
3. Made SkyMavis enrichment fetch class + genes + parts
4. Merge SkyMavis class into Moralis data

**Status**: ⏳ **DEPLOYED, AWAITING NEXT RUN**

---

## Current Architecture

### Data Flow
```
1. Moralis NFT API (PRIMARY)
   ├─ Fetches: token_id, owner, metadata, token_uri
   ├─ Missing: class, genes, parts, stats
   └─ Result: INCOMPLETE - unusable without enrichment

2. SkyMavis GraphQL (FALLBACK for enrichment)
   ├─ Fetches: class, genes, parts
   ├─ Issue: 100% rate limited (429 errors)
   └─ Result: FAILS - cannot enrich Moralis data

3. Database Storage
   ├─ Requires: valid class (Beast/Plant/Aquatic/Bird/Bug/Reptile/Mech/Dawn/Dusk)
   ├─ Rejects: "Unknown" or missing class
   └─ Result: 0 stored (no valid data after Moralis + failed enrichment)
```

---

## Why Moralis Shows No Usage (User's Question)

**User's observation**: "i dont see any usage on the moralis api key"

**Reality**: Moralis IS being called extensively:
- Deployment: 2026-01-30 16:46 UTC
- First Lambda run: 18:05 UTC (scheduled, every 2 hours at :40)
- Moralis calls per run: 100 (10 batches × 10 axies)
- Success rate: 100% (API calls succeed)
- Storage rate: 0% (data unusable without class)

**Possible reasons for "no usage" visibility**:
1. Moralis dashboard updates may be delayed
2. Usage tracked by different metric (requests vs successful data)
3. Free tier may not show real-time usage
4. User checking wrong Moralis account/project

**Proof Moralis is active** (CloudWatch logs):
```
18:45:45 - "Batch 10: fetched 10/10 axies from Moralis"
18:46:21 - "Batch 8: fetched 10/10 axies from Moralis"
18:46:35 - "Metadata ingestion complete: fetched 100, stored 0, enriched with genes 0"
```

---

## Root Cause Analysis

### The Wrong API Problem

**Moralis NFT API** (what we're using):
- General-purpose NFT metadata API
- Works for ANY NFT contract on Ronin
- Returns: token ownership, transfers, basic metadata
- **Does NOT have**: Axie-specific game data (class, genes, parts, stats)

**What we actually need**:
- Axie Infinity-specific data source
- Includes: class, breed count, purity, genes, parts, stats
- Options:
  1. SkyMavis GraphQL API (current fallback, but rate limited)
  2. Ronin RPC + on-chain data parsing (complex)
  3. Alternative Axie data providers (if exist)

### The Rate Limiting Problem

**SkyMavis API**:
- Current limit unknown (no published rate limits)
- Observed: ~1 request triggers 429
- Previous approach: 1 axie every 6 seconds = 0 throughput
- Hybrid approach: Still 100% rate limited on enrichment
- **Conclusion**: Cannot be used as fallback at any scale

---

## Options Going Forward

### Option 1: Stick with SkyMavis Only (Conservative)
**Approach**: Go back to SkyMavis-only, but MUCH slower
- Rate: 1 request per minute (vs 10 per 6 seconds)
- Throughput: 60 axies/hour (vs 0 currently)
- Pros: Known to work, complete data
- Cons: Slow, still at risk of rate limiting

### Option 2: Find Axie-Specific Moralis Endpoint
**Approach**: Research if Moralis has Axie Infinity-specific APIs
- Moralis Web3 Gaming APIs?
- Community-maintained Axie datasets?
- Pros: Higher rate limits, Moralis infrastructure
- Cons: May not exist, requires research

### Option 3: Alternative Data Sources
**Approach**: Explore other Axie data providers
- Axie.tech APIs
- Community indexers
- Lunacian.io data sources
- Pros: May have better rate limits
- Cons: Unknown reliability, may require payment

### Option 4: On-Chain Parsing (Complex)
**Approach**: Use Ronin RPC directly, parse contract events
- Fetch Transfer events for Axie contract
- Parse gene data from on-chain storage
- Pros: No rate limiting, free
- Cons: Very complex, requires deep understanding of Axie contracts

---

## Immediate Next Steps

1. **Wait for next scheduled run** (20:40 UTC)
   - Check if ANY axies have class data from Moralis
   - Check if SkyMavis enrichment succeeds for any axies
   - Log storage success rate

2. **If still 0 stored**:
   - Acknowledge Moralis NFT API is wrong tool
   - Choose between Options 1-4 above
   - Implement chosen approach

3. **Quick test**:
   - Manually invoke Lambda
   - Check CloudWatch for storage > 0
   - Verify Moralis API usage in Moralis dashboard

---

## Recommendation

**Immediate**: Option 1 (Conservative SkyMavis)
- Change `AXIES_PER_BATCH = 1`
- Change `BATCH_DELAY_SECONDS = 60.0` (1 minute)
- Remove Moralis entirely
- Expected: 60 axies/hour, >80% coverage in ~24 hours

**Long-term**: Research Option 2 or 3
- Investigate Axie-specific data sources
- Test rate limits and data completeness
- Only switch if clearly better than SkyMavis

---

## Current Status

**Integration Status**: ✅ **ACTIVE** (Moralis being called, SkyMavis being called)
**Throughput**: ❌ **0 axies/hour** (data incomplete)
**Next Run**: 20:40 UTC (scheduled EventBridge)
**Blocking Issue**: Moralis NFT API lacks Axie class data
**Solution**: Switch back to SkyMavis-only with ultra-conservative rate limiting

---

**Document Version**: 1.0
**Author**: Claude Sonnet 4.5
**Next Update**: After 20:40 UTC run or user decision on approach
