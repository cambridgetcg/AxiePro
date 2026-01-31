# Ronin API Phase 1 Implementation - Wallet Token Balances

## Status: 🚧 READY FOR IMPLEMENTATION

**Date**: 2026-01-31
**Phase**: 1 of 3 (Foundation)
**Complexity**: Medium (2 weeks)
**Value**: High (Core portfolio feature)

---

## EXECUTIVE SUMMARY

Implementing real-time wallet token balance tracking using Ronin RPC API. This enables users to see their current RON, WETH, WRON, AXS, and SLP holdings with USD valuations.

### What's Being Built

**Feature**: Real-time Wallet Token Balances
**API Endpoint**: `GET /api/v1/wallets/{address}/balances`
**User Story**: "As a portfolio tracker, I want to see my current token balances so that I can understand my asset allocation."

**Example Response**:
```json
{
  "success": true,
  "data": {
    "address": "0x...",
    "balances": [
      {"token": "WETH", "balance": "0.05", "balance_usd": "190.00"},
      {"token": "AXS", "balance": "50", "balance_usd": "350.00"},
      {"token": "WRON", "balance": "1000", "balance_usd": "150.00"},
      {"token": "RON", "balance": "123.456", "balance_usd": "18.52"}
    ],
    "total_value_usd": "708.52"
  }
}
```

### Components to Build

1. **RoninRPCClient extensions** - Blockchain balance fetching
2. **WalletTokenBalance model** - Database storage
3. **WalletBalanceService** - Business logic & caching
4. **API routes** - HTTP endpoints
5. **Database migration** - Schema creation

---

## ARCHITECTURE OVERVIEW

```
Frontend Request
    ↓
GET /api/v1/wallets/{address}/balances
    ↓
WalletBalanceService
    ├─ Check Redis (5-min TTL)
    ├─ Check Database (if not stale)
    └─ Fetch from Blockchain (RoninRPCClient)
        ├─ eth_getBalance (RON)
        ├─ eth_call (WETH balanceOf)
        ├─ eth_call (WRON balanceOf)
        ├─ eth_call (AXS balanceOf)
        └─ eth_call (SLP balanceOf)
    ↓
Cache & Store
    ├─ Update Database
    └─ Cache in Redis
    ↓
Return Response
```

---

## IMPLEMENTATION FILES

### 1. Database Migration

**File**: `backend/alembic/versions/20260131_add_wallet_token_balances.py` (NEW)

**Purpose**: Create `wallet_token_balances` table

**Schema**:
```sql
CREATE TABLE wallet_token_balances (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(42) REFERENCES wallets(address),
    token_type ENUM('RON', 'WETH', 'WRON', 'AXS', 'SLP'),
    balance NUMERIC(20, 8),
    balance_usd NUMERIC(20, 2),
    token_price_usd NUMERIC(20, 8),
    last_updated TIMESTAMP,
    block_number BIGINT,
    UNIQUE(wallet_address, token_type)
);
```

**Status**: ⏳ Not implemented yet

---

### 2. Database Model

**File**: `backend/src/models/wallet.py` (EXTEND)

**Changes**:
- Add `TokenType` enum
- Add `WalletTokenBalance` class
- Add relationship to `Wallet` class

**Pattern Source**: `wallet.py:62-139` (WalletHolding)

**Status**: ⏳ Not implemented yet

---

### 3. RPC Client Extensions

**File**: `backend/src/services/ronin_rpc_client.py` (EXTEND)

**Changes**:
Add three new methods (after line 618):
```python
async def get_native_balance(address: str) -> Decimal
async def get_erc20_balance(token_address: str, wallet_address: str) -> Decimal
async def get_wallet_balances(wallet_address: str) -> dict[str, Decimal]
```

Add token contract addresses (after line 119):
```python
AXS_CONTRACT = "0x97a9107c1793bc407d6f527b77e7fff4d812bece"
SLP_CONTRACT = "0xa8754b9fa15fc18bb59458815510e40a12cd2014"
BALANCE_OF_SIGNATURE = "0x70a08231"
```

**Pattern Source**: Existing RPC methods (lines 307-617)

**Status**: ⏳ Not implemented yet

---

### 4. Service Layer

**File**: `backend/src/services/wallet_balance_service.py` (NEW - 400 lines)

**Purpose**: Orchestrate cache → DB → blockchain flow

**Key Methods**:
```python
async def get_balances(address, force_refresh=False) -> Dict[str, BalanceData]
async def refresh_balances(address) -> Dict[str, BalanceData]
async def batch_refresh(addresses, max_concurrent=5) -> Dict
```

**Caching Strategy**:
- Redis: 5-minute TTL
- Database: Check staleness (5 minutes)
- Blockchain: Fallback when cache miss

**Pattern Source**: `market_aggregator.py:71-93` (MarketAggregatorService)

**Status**: ⏳ Not implemented yet

---

### 5. API Routes

**File**: `backend/src/api/routes/wallets.py` (EXTEND)

**Changes**:
Add two new endpoints:
```python
@router.get("/{address}/balances")
async def get_wallet_balances(address, force_refresh=False)

@router.post("/{address}/balances/refresh")
async def refresh_wallet_balances(address)
```

**Pattern Source**: Existing wallet endpoints (lines 64-149)

**Status**: ⏳ Not implemented yet

---

## TOKEN CONTRACT ADDRESSES (Ronin Mainnet)

| Token | Contract Address | Type | Usage |
|-------|------------------|------|-------|
| RON | NATIVE | Native | eth_getBalance |
| WETH | 0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5 | ERC20 | Axie marketplace |
| WRON | 0xe514d9deb7966c8be0ca922de8a064264ea6bcd4 | ERC20 | Wrapped RON |
| AXS | 0x97a9107c1793bc407d6f527b77e7fff4d812bece | ERC20 | Governance |
| SLP | 0xa8754b9fa15fc18bb59458815510e40a12cd2014 | ERC20 | Breeding |

**Verification Status**:
- ✅ WETH: Already in use (ronin_rpc_client.py:118)
- ✅ WRON: Already in use (ronin_rpc_client.py:119)
- ⚠️ AXS: Needs verification (from goldrush_client.py reference)
- ⚠️ SLP: Needs verification (from goldrush_client.py reference)

---

## IMPLEMENTATION SEQUENCE

### Step 1: Database Schema (Day 1)
```bash
cd backend
alembic revision -m "add_wallet_token_balances"
# Edit generated file with schema from plan
alembic upgrade head
```

### Step 2: Database Model (Day 1)
- Edit `models/wallet.py`
- Add TokenType enum
- Add WalletTokenBalance class
- Update Wallet relationship

### Step 3: RPC Client Extensions (Day 2-3)
- Edit `services/ronin_rpc_client.py`
- Add contract addresses
- Add get_native_balance()
- Add get_erc20_balance()
- Add get_wallet_balances()
- Unit tests

### Step 4: Service Layer (Day 4-5)
- Create `services/wallet_balance_service.py`
- Implement WalletBalanceService
- Implement caching logic
- Implement batch operations
- Unit tests

### Step 5: API Routes (Day 6-7)
- Edit `api/routes/wallets.py`
- Add balance endpoints
- Add Pydantic models
- Integration tests

### Step 6: Testing & Deployment (Day 8-10)
- E2E tests
- Performance testing
- Deploy to development
- Verify with real wallets
- Monitor RPC usage

---

## TESTING STRATEGY

### Unit Tests (30 tests)
- RPC balance fetching (10 tests)
- Service caching logic (10 tests)
- Database operations (5 tests)
- API response formatting (5 tests)

### Integration Tests (15 tests)
- Full GET /balances flow (5 tests)
- Cache hit/miss scenarios (5 tests)
- Force refresh behavior (5 tests)

### E2E Tests (5 tests)
- Complete caching cycle
- Batch refresh
- Error handling

---

## PERFORMANCE EXPECTATIONS

### RPC Usage
- Per wallet balance fetch: 5 RPC calls (RON + 4 tokens)
- With 5-min cache: 12 fetches/hour per wallet
- 100 active users: 1200 RPC calls/hour = 20/min (well under limit)

### Response Times
- Cache hit (Redis): < 50ms
- Cache hit (DB): < 100ms
- Cache miss (RPC): < 500ms

### Database Impact
- Minimal: ~125 KB for 1000 wallets

---

## RISK ASSESSMENT

### Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| AXS/SLP contract addresses wrong | Medium | Verify on Ronin Scan before deployment |
| RPC rate limit exceeded | High | Conservative caching (5-min TTL) |
| Token price staleness | Low | Document as Phase 2 enhancement |
| Database migration failure | High | Test on dev environment first |

### Mitigation Complete For:
- ✅ Provider failover (already in RPC client)
- ✅ Circuit breaker (already in RPC client)
- ✅ Exponential backoff (already in RPC client)
- ✅ Connection pooling (already in RPC client)

---

## DEPLOYMENT CHECKLIST

### Pre-Deployment
- [ ] Verify AXS contract address on Ronin Scan
- [ ] Verify SLP contract address on Ronin Scan
- [ ] Run all unit tests locally
- [ ] Run integration tests locally
- [ ] Apply migration on dev database
- [ ] Test with real wallet addresses

### Deployment
- [ ] Apply migration on production database
- [ ] Deploy backend code to App Runner
- [ ] Verify health endpoint
- [ ] Test API with curl
- [ ] Monitor CloudWatch for errors

### Post-Deployment
- [ ] Verify RPC call volume < 100/min
- [ ] Verify cache hit rate > 80%
- [ ] Verify response times < 500ms
- [ ] Test with multiple wallets
- [ ] Document any issues

---

## VERIFICATION COMMANDS

### Test Migration
```bash
cd backend
alembic upgrade head
psql $DATABASE_URL -c "\d wallet_token_balances"
```

### Test RPC Methods
```python
from src.services.ronin_rpc_client import RoninRPCClient

async with RoninRPCClient() as client:
    balance = await client.get_native_balance("0x...")
    print(f"RON balance: {balance}")
```

### Test API Endpoint
```bash
# Test balances endpoint
curl -s "https://api.axiepro.io/api/v1/wallets/0x.../balances" | jq

# Test force refresh
curl -s "https://api.axiepro.io/api/v1/wallets/0x.../balances?force_refresh=true" | jq

# Test refresh endpoint
curl -X POST "https://api.axiepro.io/api/v1/wallets/0x.../balances/refresh" | jq
```

### Monitor Performance
```bash
# Check RPC call frequency
aws logs filter-log-events \
  --log-group-name /aws/apprunner/axiepro-backend \
  --filter-pattern "RPC call" \
  --start-time $(($(date +%s) - 3600))000

# Check cache hit rate
redis-cli info stats | grep hit
```

---

## SUCCESS METRICS

### Phase 1 Complete When:
- ✅ All 5 token balances fetchable
- ✅ Cache hit rate > 80%
- ✅ Response time < 500ms (p95)
- ✅ Error rate < 1%
- ✅ 100% test coverage
- ✅ Documentation complete

### User Impact Metrics:
- Portfolio visibility enabled
- Foundation for Phase 2 (P&L tracking)
- Engagement increase (measurable after 1 week)

---

## DEPENDENCIES

### External Dependencies
- Ronin RPC endpoint (public): `https://api.roninchain.com/rpc`
- Token contract ABIs (standard ERC20)

### Internal Dependencies
- PostgreSQL database (already deployed)
- Redis cache (already deployed)
- Existing Wallet model
- Existing RoninRPCClient infrastructure

---

## NEXT PHASES

### Phase 2: Portfolio P&L (Weeks 3-4)
- Cost basis tracking
- P&L calculation
- Breeding cost analysis
- ROI insights

### Phase 3: Real-Time Features (Weeks 5-6)
- Live floor price feeds
- Price change alerts
- WebSocket streaming

---

## DOCUMENTATION UPDATES NEEDED

1. **API Documentation** (`docs/API_ENDPOINT_TESTS.md`)
   - Add wallet balance endpoints
   - Add example requests/responses

2. **README** (`backend/README.md`)
   - Add Phase 1 features to feature list
   - Update token support table

3. **SSM Parameters** (`docs/SSM_PARAMETERS.md`)
   - Add token price configuration (if dynamic)

---

## IMPLEMENTATION STATUS

| Component | Status | Estimated Time | Actual Time |
|-----------|--------|----------------|-------------|
| Database Migration | ⏳ Not started | 2 hours | - |
| Database Model | ⏳ Not started | 2 hours | - |
| RPC Client | ⏳ Not started | 8 hours | - |
| Service Layer | ⏳ Not started | 16 hours | - |
| API Routes | ⏳ Not started | 8 hours | - |
| Testing | ⏳ Not started | 16 hours | - |
| Documentation | ⏳ Not started | 4 hours | - |
| **Total** | **0% Complete** | **~56 hours (7 days)** | **TBD** |

---

## APPROVAL REQUIRED

**Decision Point**: Proceed with implementation?

**Options**:
1. ✅ **Proceed** - Implement Phase 1 now (7 days effort)
2. ⏸️ **Defer** - Wait for user feedback on design
3. 🔄 **Modify** - Adjust scope or approach

**Recommendation**: Proceed with implementation. Design is solid, patterns are proven, and value is clear.

---

**Document Status**: ✅ Complete and Ready for Implementation
**Last Updated**: 2026-01-31
**Created By**: Purpose Prompter (TRUTH → UNDERSTANDING → BEAUTY → JUSTICE → CREATIVITY)
