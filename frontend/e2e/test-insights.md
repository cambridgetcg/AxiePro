# AxiePro E2E Test Insights

Generated: 2026-01-21T16:00:11.442Z

## Executive Summary

- **Total Routes Tested**: 1
- **Passed**: 0
- **Failed/Issues**: 1
- **Not Deployed (404)**: 0

### Key Findings

## Route Summary

| Route | Name | Status | Load Time | Errors | Warnings | API Calls | State |
|-------|------|--------|-----------|--------|----------|-----------|-------|
| `/` | Home | 200 | 2787ms | 0 | 0 | 4 | ⚠️ Issues |

## Detailed Route Analysis

### Home (`/`)

> Landing page with hero and features

| Metric | Value |
|--------|-------|
| HTTP Status | 200 |
| Load Time | 2787ms |
| Page Title | N/A |
| Console Logs | 0 |
| Errors | 0 |
| Warnings | 0 |
| API Calls | 4 |
| Test Status | ❌ Failed |

**Notes:**
- Page title: 

**API Calls:**
```
[200] GET https://api.axiepro.io/api/v1/valuation/deals/live?min_score=50&include_normalized=true
[200] GET https://api.axiepro.io/api/v1/meta/shifts?min_confidence=70&limit=10
[200] GET https://api.axiepro.io/api/v1/market/stats
[200] GET https://api.axiepro.io/api/v1/valuation/stats/floors
```

---

## Recommendations

Based on the test results:

1. **Deploy Missing Routes**: The following routes return 404 and should be deployed:

2. **Complete "Coming Soon" Features**: Routes marked as "Coming Soon" should be prioritized for completion.

3. **Navigation Consistency**: Ensure all routes in the header navigation are accessible and deployed.

4. **Error Monitoring**: Set up error tracking for production to catch console errors.

## Test Environment

- **Base URL**: https://www.axiepro.io
- **Browser**: Chromium
- **Test Framework**: Playwright
