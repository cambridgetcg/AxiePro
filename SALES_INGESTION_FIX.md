# Sales Ingestion Schema Mismatch Fix

## Problem
Critical bug discovered where `sales_ingestion.py` Lambda was writing to non-existent `sales` table instead of `axie_sales` table. **NO sales data has been captured since deployment.**

## Root Cause
Schema was upgraded to `axie_sales` with new columns, but Lambda code was never updated:
- Old table name: `sales` → New: `axie_sales`
- Old columns: `seller_address`, `buyer_address`, `price_eth`, `sold_at`, `marketplace`
- New columns: `seller`, `buyer`, `price_token`, `block_timestamp`, `block_number`, `eth_usd_rate`, `ron_usd_rate`, `class`, `breed_count`, `price_raw`

## Files Modified

### 1. backend/src/lambdas/sales_ingestion.py
**Changes:**
- ✅ Line 29: Added `schema_validation` import
- ✅ Lines 101-135: Added `get_exchange_rates()` function to fetch ETH/USD and RON/USD rates from DB
- ✅ Lines 137-178: Updated `convert_sale_to_record()` to:
  - Accept `eth_usd_rate` and `ron_usd_rate` parameters
  - Return correct column names matching `axie_sales` schema
  - Include all 14 columns (6 required + 8 optional)
- ✅ Lines 182-243: Updated `store_sales()` to:
  - Use `axie_sales` table instead of `sales`
  - Insert all 14 columns with correct names
  - Validate records before insertion via `validate_sales_record()`
- ✅ Lines 58-70: Fixed fallback query to use `axie_sales` and `block_timestamp`
- ✅ Lines 351-367: Updated handler to fetch exchange rates and pass to conversion

### 2. backend/src/lambdas/common/schema_validation.py (NEW)
**Purpose:** Prevent future schema mismatches

**Features:**
- `TableSchema` dataclass for defining expected schemas
- `AXIE_SALES_SCHEMA` with 6 required + 8 optional columns
- `AXIES_SCHEMA` for metadata validation
- `EXCHANGE_RATES_SCHEMA` for rate validation
- Validation functions that raise `ValueError` on mismatch

### 3. backend/tests/integration/test_sales_schema_compliance.py (NEW)
**Purpose:** Catch schema drift before deployment

**Tests:**
- ✅ `convert_sale_to_record()` produces valid schema
- ✅ All required columns present (6)
- ✅ All optional columns defined (8)
- ✅ No unknown columns in output
- ✅ Old column names removed
- ✅ Table name is `axie_sales` not `sales`

## Schema Mapping

| Old Column | New Column | Type | Required |
|-----------|------------|------|----------|
| axie_id | axie_id | INTEGER | ✅ |
| tx_hash | tx_hash | VARCHAR(66) | ✅ |
| - | block_number | BIGINT | ✅ |
| sold_at | block_timestamp | TIMESTAMP | ✅ |
| price_eth | price_token | NUMERIC(20,10) | ✅ |
| - | token_type | VARCHAR(10) | ✅ |
| price_usd | price_usd | NUMERIC(12,2) | ❌ |
| - | eth_usd_rate | NUMERIC(10,2) | ❌ |
| - | ron_usd_rate | NUMERIC(10,6) | ❌ |
| seller_address | seller | VARCHAR(66) | ❌ |
| buyer_address | buyer | VARCHAR(66) | ❌ |
| - | class | VARCHAR(20) | ❌ |
| - | breed_count | SMALLINT | ❌ |
| - | price_raw | NUMERIC(30,0) | ❌ |
| marketplace | REMOVED | - | - |

## Prevention Layer

### Schema Validation
All sales records are now validated before insertion:
```python
validate_sales_record(sale)  # Raises ValueError on mismatch
```

### Integration Test
Run before each deployment:
```bash
cd backend
pytest tests/integration/test_sales_schema_compliance.py -v
```

Catches:
- Missing required columns
- Unknown columns
- Wrong table names
- Old column names still present

## Deployment Checklist

- [x] Fix table name (3 locations)
- [x] Fix column mappings (14 columns)
- [x] Add exchange rate fetching
- [x] Create schema validation layer
- [x] Create integration test
- [x] Integrate validation into Lambda
- [ ] Run integration test locally (requires pytest setup)
- [ ] Deploy updated Lambda to AWS
- [ ] Monitor CloudWatch logs for successful inserts
- [ ] Verify data flowing into `axie_sales` table
- [ ] Run backfill for missed sales (optional)

## Expected Impact

**Before fix:**
- 0 sales captured (all INSERTs failing silently)
- Table `sales` doesn't exist
- No data for price analytics

**After fix:**
- All sales captured to `axie_sales` table
- Full schema compliance (14 columns)
- Exchange rates tracked for historical analysis
- Schema validation prevents future drift

## Verification Commands

```sql
-- Check if sales are being inserted
SELECT COUNT(*) FROM axie_sales WHERE created_at > NOW() - INTERVAL '1 hour';

-- Check latest sales
SELECT axie_id, price_token, token_type, block_timestamp
FROM axie_sales
ORDER BY block_timestamp DESC
LIMIT 10;

-- Verify exchange rates are populated
SELECT axie_id, eth_usd_rate, ron_usd_rate
FROM axie_sales
WHERE eth_usd_rate IS NOT NULL
LIMIT 10;
```

## Next Steps

1. Deploy updated Lambda:
   ```bash
   cd infrastructure
   npm run deploy
   ```

2. Monitor first execution:
   ```bash
   aws logs tail /aws/lambda/axiepro-sales-ingestion-dev --follow
   ```

3. Verify data:
   ```sql
   SELECT COUNT(*) FROM axie_sales WHERE created_at > NOW() - INTERVAL '10 minutes';
   ```

4. (Optional) Backfill missed sales:
   - Manually invoke Lambda with extended block range
   - Or wait for natural accumulation over 24-48 hours
