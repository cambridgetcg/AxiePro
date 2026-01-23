# Market Analytics E2E Test Findings

**Date**: 2026-01-23
**Test File**: `market-analytics.spec.ts`
**Debugging System**: `fixtures/console-capture.ts`
**Status**: RESOLVED

## Executive Summary

The E2E debugging system successfully captured browser console output and network requests. Initial testing revealed a CORS configuration issue blocking API calls from localhost to the production API. **This has been resolved by implementing API mocking for deterministic E2E tests.**

### Final Results

```
10 passed (9.3s)
1 skipped (auto-refresh long-running test)
```

## Debugging System Validation

**Status**: Working correctly

The console capture system successfully:
- Captured console errors with full context
- Tracked network requests and responses
- Detected API call failures
- Provided structured output for analysis

## Critical Finding: CORS Blocking

### Error Captured

```
Access to fetch at 'https://api.axiepro.io/api/v1/valuation/stats/floors'
from origin 'http://localhost:3000' has been blocked by CORS policy:
Response to preflight request doesn't pass access control check:
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

### Affected Endpoints

| Endpoint | Status | Error |
|----------|--------|-------|
| `/valuation/stats/floors` | Blocked | CORS |
| `/valuation/deals/snipes` | Blocked | CORS |
| All `/api/v1/*` endpoints | Blocked | CORS |

### Root Cause

The production API at `api.axiepro.io` does not include `http://localhost:3000` in its `Access-Control-Allow-Origin` response header. This prevents local development testing against the production API.

### Impact

1. **E2E tests cannot validate real API responses** - All API calls fail before reaching the server
2. **Local development affected** - Developers cannot test against production data locally
3. **Console capture works** - The debugging system correctly identified the issue

## Test Results

| Test | Status | Notes |
|------|--------|-------|
| Floor prices load without errors | Failed | CORS blocked API |
| Floor prices display correctly | Failed | No data due to CORS |
| Snipes section loads | Failed | CORS blocked API |
| Refresh button triggers new API calls | Failed | CORS blocked API |
| Auto-refresh triggers after 60 seconds | Skipped | Long-running test |
| API response includes fresh data indicator | Failed | CORS blocked API |
| Handles API errors gracefully | Passed | Error handling works |
| Handles slow API response | Passed | Loading states work |
| Capture all console output | Passed | Debugging system works |

## Recommendations

### Immediate Fix Options

**Option 1: Add localhost to CORS allowlist (Development Only)**

Update API Gateway or backend CORS configuration:
```python
# FastAPI example
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://axiepro.io",
        "https://www.axiepro.io",
        "http://localhost:3000",  # Add for local dev
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Option 2: Use API mocking for E2E tests**

Configure Playwright to intercept and mock API responses:
```typescript
await page.route('**/valuation/stats/floors', (route) => {
  route.fulfill({
    status: 200,
    body: JSON.stringify({
      success: true,
      data: { beast: 0.015, aquatic: 0.012, ... },
      meta: { source: 'mock' }
    }),
  });
});
```

**Option 3: Run local API server for E2E tests**

Start the backend locally and point frontend to `http://localhost:8000`.

### Recommended Approach

1. **For E2E tests**: Use Option 2 (mocking) - Tests should be deterministic
2. **For local development**: Use Option 1 or Option 3 depending on needs

## Console Capture System Features Verified

| Feature | Status | Evidence |
|---------|--------|----------|
| Console log capture | Working | Captured all console.log output |
| Console error capture | Working | CORS errors captured with full details |
| Network request tracking | Working | Tracked all fetch requests |
| Network error detection | Working | Detected blocked requests |
| Page error capture | Working | Would capture uncaught exceptions |
| API call filtering | Working | `getApiCallsForEndpoint()` returns correct results |
| Markdown export | Working | `toMarkdown()` generates formatted output |
| JSON export | Working | `toJSON()` generates structured data |

## Resolution Implemented

### API Mocking Layer (`fixtures/api-mocks.ts`)

Created a comprehensive API mocking system with:

```typescript
// Set up mocks with default data
await setupApiMocks(page);

// Or customize responses
await setupApiMocks(page, {
  floorPrices: createFloorPricesMock({ beast: 0.025 }),
  delay: 3000,  // Test loading states
  failEndpoints: ['floors'],  // Test error handling
});
```

**Features**:
- Mock data for all market endpoints (floors, snipes, stats, meta)
- Customizable responses for specific test scenarios
- Delay injection for loading state tests
- Error injection for error handling tests
- Empty data mocks for empty state tests

### Key Changes

1. **`e2e/fixtures/api-mocks.ts`** - New API mocking utilities
2. **`e2e/market-analytics.spec.ts`** - Updated to use mocks by default
3. **Backend `cors_origins`** - Already includes `localhost:3000` (no change needed)

## Next Steps

1. [x] ~~Decide on CORS solution approach~~ - Using API mocking
2. [x] ~~Implement API mocking layer for E2E tests~~ - Done
3. [x] ~~Re-run tests after fix~~ - All passing
4. [ ] Validate floor prices data freshness in production
5. [ ] Add more endpoint mocks as needed for other tests

## Appendix: Sample Console Capture Output

```markdown
## Console Capture Summary

| Metric | Count |
|--------|-------|
| Total Logs | 15 |
| Errors | 6 |
| Warnings | 2 |
| API Calls | 4 |
| Page Errors | 0 |

### Errors

[error] Failed to load resource: net::ERR_FAILED
Location: :0

[error] Access to fetch at 'https://api.axiepro.io/api/v1/valuation/stats/floors'...
Location: webpack-internal:///...

### API Calls

[pending] GET https://api.axiepro.io/api/v1/valuation/stats/floors
[pending] GET https://api.axiepro.io/api/v1/valuation/deals/snipes
```

---

*Generated by E2E Console Capture System*
