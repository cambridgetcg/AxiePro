# Axie Trade Data Fetch Analysis

**Date:** 2025-12-20
**Analyst:** Claude Code

## Executive Summary

The axie trade data fetch process has a **6-month data gap** (July - November 2025) caused by a **database constraint mismatch** that prevented sales from being inserted.

## Current State

| Metric | Value |
|--------|-------|
| **Total Sales in DB** | 22,015 |
| **Data Range** | June 1, 2025 → Dec 15, 2025 |
| **Block Range** | 45,626,000 → 51,315,301 |
| **Gap** | Block 45,765,000 → 51,313,845 (~5.5M blocks) |

### Monthly Breakdown

| Month | Sales | Volume USD |
|-------|-------|------------|
| June 2025 | 21,859 | $206,460 |
| December 2025 | 156 | $471 |
| **Jul-Nov 2025** | **0** | **MISSING** |

## Root Cause Analysis

### 1. Database Constraint Mismatch

**Problem:** The fetch script uses an `ON CONFLICT` clause that doesn't match the table's unique constraint.

**Script Code (`fetch_june2025_to_now.py:139`):**
```sql
ON CONFLICT (tx_hash, axie_id) DO NOTHING
```

**Actual Table Constraint:**
```sql
-- Primary Key
(id, block_timestamp)

-- Unique Index
idx_sales_unique_v2: (tx_hash, axie_id, block_timestamp)
```

**Result:** PostgreSQL error on first insert:
```
there is no unique or exclusion constraint matching the ON CONFLICT specification
```

### 2. Transaction Cascade Failure

Once the first insert fails, PostgreSQL aborts the entire transaction. All subsequent inserts within the same transaction fail with:
```
current transaction is aborted, commands ignored until end of transaction block
```

**Evidence from logs:**
```
Sales found: 1,360
Sales inserted: 0  (100% failure rate)
```

### 3. Missing Error Recovery

The `insert_sales()` function commits after each chunk but doesn't rollback failed individual inserts:

```python
# fetch_june2025_to_now.py:130-161
def insert_sales(conn, sales):
    cur = conn.cursor()
    for sale in sales:
        try:
            cur.execute("""INSERT INTO axie_sales...""")
            # No rollback on failure!
        except Exception as e:
            logger.warning(f"Insert error...")  # Just logs, doesn't recover
    conn.commit()  # Commits nothing if transaction is aborted
```

## Fetch Scripts Architecture

### Available Scripts

| Script | Purpose | Status |
|--------|---------|--------|
| `fetch_continuous.py` | Lambda pipeline worker (premium sales only) | Works with job system |
| `fetch_june2025_to_now.py` | Historical backfill (async, batch processor) | **BROKEN** - constraint mismatch |
| `fetch_dec_to_now.py` | Recent data catchup (simple, sequential) | Works (uses older constraint) |
| `fetch_june2025_parallel.py` | Parallel historical fetch | Works (different insert logic) |

### Core Components

```
backend/src/services/
├── ronin_rpc_client.py    # Async RPC client with failover
├── batch_processor.py     # High-throughput parallel processor
└── checkpoint_manager.py  # Resumable progress tracking
```

**Performance Characteristics:**
- `batch_processor.py`: Claims ~3,500 blk/s with parallel workers
- `fetch_dec_to_now.py`: Conservative 1 req/2s (~250 blk/s)
- Actual observed: 9 blk/s (limited by rate limiting + errors)

## Sync State Table

```sql
SELECT * FROM axie.sync_state;

         id          | last_block |      records_synced | processing_rate
---------------------+------------+---------------------+-----------------
 june2025_to_present |   45635999 |               1,360 |            8.99
 axie_sales          |   51315301 |                 156 |            NULL
```

- `june2025_to_present`: Stopped at block 45,635,999 (only 10K blocks processed)
- `axie_sales`: December catchup completed

## Fix Strategy

### Option 1: Add Missing Unique Constraint (Recommended)

```sql
-- Add the constraint that scripts expect
CREATE UNIQUE INDEX IF NOT EXISTS idx_sales_tx_axie
ON axie.axie_sales (tx_hash, axie_id);
```

**Pros:** No script changes needed
**Cons:** Slightly different dedup behavior (ignores timestamp in conflicts)

### Option 2: Fix Script ON CONFLICT Clause

```python
# Change to match existing constraint
ON CONFLICT (tx_hash, axie_id, block_timestamp) DO NOTHING
```

**Pros:** Uses existing index
**Cons:** Requires script modification

### Option 3: Use Simpler Fetch Script

Use `fetch_dec_to_now.py` pattern with modifications for historical range:
- Sequential, simple, reliable
- Proper error handling with per-insert try/except
- Slower but guaranteed to work

## Recommended Action Plan

1. **Add missing unique constraint:**
   ```sql
   CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_sales_tx_axie
   ON axie.axie_sales (tx_hash, axie_id);
   ```

2. **Reset the sync checkpoint:**
   ```sql
   UPDATE axie.sync_state
   SET last_block = 45765000, records_synced = 0
   WHERE id = 'june2025_to_present';
   ```

3. **Run backfill with fixed script or use `fetch_dec_to_now.py` pattern**

4. **Monitor progress and verify data integrity**

## Block to Date Reference

| Block | Approximate Date |
|-------|------------------|
| 45,626,000 | June 1, 2025 |
| 45,765,000 | June 6, 2025 (gap start) |
| 48,500,000 | September 2025 |
| 51,313,845 | December 15, 2025 (gap end) |
| ~51,500,000 | December 20, 2025 (today) |

*Block time: ~3 seconds*

## Files Modified

- None yet (analysis only)

## Resolution

### Fix Applied (2025-12-20)

1. **Created fixed backfill script**: `fetch_gap_backfill.py`
   - Uses correct `ON CONFLICT (tx_hash, axie_id, block_timestamp)` clause
   - Proper error handling with per-insert rollback
   - Checkpoint-based resumability
   - Conservative rate limiting

2. **Test Results** (1,000 blocks):
   ```
   Blocks processed: 1,000
   Sales inserted: 115
   Avg rate: 2.4 blk/s
   Total sales in DB: 22,130
   ```

3. **Full Backfill Estimate**:
   - Remaining blocks: ~5.5M
   - At 2.4 blk/s: ~640 hours (~27 days)
   - Conservative but reliable

### Running the Backfill

```bash
# Resume from checkpoint (recommended)
source backend/venv/bin/activate
nohup python3 fetch_gap_backfill.py --resume > gap_backfill.log 2>&1 &

# Or start fresh
nohup python3 fetch_gap_backfill.py > gap_backfill.log 2>&1 &

# Monitor progress
tail -f gap_backfill.log
```

### Alternative: Faster Parallel Fetch

For faster processing, consider:
1. Using Sky Mavis premium API (higher rate limits)
2. Running multiple instances with non-overlapping block ranges
3. Using the `fetch_june2025_to_now.py` after fixing ON CONFLICT clause

## Next Steps

1. ✅ Identified root cause (constraint mismatch)
2. ✅ Created fixed script (`fetch_gap_backfill.py`)
3. ✅ Tested with small block range
4. 🔄 Run full historical backfill
5. ⏳ Verify data integrity after completion
