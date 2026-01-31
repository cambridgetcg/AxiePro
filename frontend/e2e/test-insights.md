# AxiePro E2E Test Insights

Generated: 2026-01-29T17:37:26.450Z

## Executive Summary

- **Total Routes Tested**: 10
- **Passed**: 9
- **Failed/Issues**: 1
- **Not Deployed (404)**: 0

### Key Findings

**Routes with "Coming Soon" Placeholder:**
- `/explorer` (Explorer)
- `/breeding` (Breeding)
- `/market` (Market)

**Routes with Console Errors:**
- `/analytics` (Analytics): 4 errors

## Route Summary

| Route | Name | Status | Load Time | Errors | Warnings | API Calls | State |
|-------|------|--------|-----------|--------|----------|-----------|-------|
| `/` | Home | 200 | 2293ms | 0 | 0 | 4 | ✅ Live |
| `/explorer` | Explorer | 200 | 2549ms | 0 | 0 | 0 | 🚧 Coming Soon |
| `/deals` | Deals | 200 | 2529ms | 0 | 0 | 2 | ✅ Live |
| `/meta` | Meta | 200 | 2529ms | 0 | 0 | 5 | ✅ Live |
| `/portfolio` | Portfolio | 200 | 2451ms | 0 | 0 | 0 | ✅ Live |
| `/breeding` | Breeding | 200 | 2681ms | 0 | 0 | 0 | 🚧 Coming Soon |
| `/analytics` | Analytics | 200 | 2613ms | 4 | 0 | 3 | ⚠️ Issues |
| `/market` | Market | 200 | 2236ms | 0 | 0 | 2 | 🚧 Coming Soon |
| `/privacy` | Privacy | 200 | 2649ms | 0 | 0 | 0 | ✅ Live |
| `/terms` | Terms | 200 | 2549ms | 0 | 0 | 0 | ✅ Live |

## Detailed Route Analysis

### Home (`/`)

> Landing page with hero and features

| Metric | Value |
|--------|-------|
| HTTP Status | 200 |
| Load Time | 2293ms |
| Page Title | AxiePro - Advanced Axie Infinity Market Analytics |
| Console Logs | 0 |
| Errors | 0 |
| Warnings | 0 |
| API Calls | 4 |
| Test Status | ✅ Passed |

**Content Found:**
- Header
- Wallet Button
- Nav: Home
- Nav: Explorer
- Nav: Breeding
- Nav: Analytics
- Footer

**Notes:**
- Page title: AxiePro - Advanced Axie Infinity Market Analytics

**API Calls:**
```
[200] GET https://api.axiepro.io/api/v1/market/stats?use_cache=true
[200] GET https://api.axiepro.io/api/v1/meta/shifts?min_confidence=70&limit=10
[200] GET https://api.axiepro.io/api/v1/valuation/deals/live?min_score=50&include_normalized=true
[200] GET https://api.axiepro.io/api/v1/valuation/stats/floors
```

---

### Explorer (`/explorer`)

> Axie search and filtering

| Metric | Value |
|--------|-------|
| HTTP Status | 200 |
| Load Time | 2549ms |
| Page Title | AxiePro - Advanced Axie Infinity Market Analytics |
| Console Logs | 0 |
| Errors | 0 |
| Warnings | 0 |
| API Calls | 0 |
| Test Status | ✅ Passed |

**Content Found:**
- Header
- Coming Soon
- Wallet Button
- Nav: Home
- Nav: Explorer
- Nav: Breeding
- Nav: Analytics
- Footer

**Notes:**
- Page title: AxiePro - Advanced Axie Infinity Market Analytics
- Coming Soon placeholder detected

---

### Deals (`/deals`)

> Undervalued listing detection

| Metric | Value |
|--------|-------|
| HTTP Status | 200 |
| Load Time | 2529ms |
| Page Title | AxiePro - Advanced Axie Infinity Market Analytics |
| Console Logs | 0 |
| Errors | 0 |
| Warnings | 0 |
| API Calls | 2 |
| Test Status | ✅ Passed |

**Content Found:**
- Header
- Wallet Button
- Nav: Home
- Nav: Explorer
- Nav: Breeding
- Nav: Analytics
- Footer

**Notes:**
- Page title: AxiePro - Advanced Axie Infinity Market Analytics

**API Calls:**
```
[200] GET https://api.axiepro.io/api/v1/valuation/deals/live?min_score=50&include_normalized=true
[200] GET https://api.axiepro.io/api/v1/valuation/deals/snipes?limit=20&include_normalized=true
```

---

### Meta (`/meta`)

> Meta shifts analysis (New)

| Metric | Value |
|--------|-------|
| HTTP Status | 200 |
| Load Time | 2529ms |
| Page Title | AxiePro - Advanced Axie Infinity Market Analytics |
| Console Logs | 0 |
| Errors | 0 |
| Warnings | 0 |
| API Calls | 5 |
| Test Status | ✅ Passed |

**Content Found:**
- Header
- Wallet Button
- Nav: Home
- Nav: Explorer
- Nav: Breeding
- Nav: Analytics
- Footer

**Notes:**
- Page title: AxiePro - Advanced Axie Infinity Market Analytics

**API Calls:**
```
[200] GET https://api.axiepro.io/api/v1/meta/falling?limit=50&min_confidence=25
[200] GET https://api.axiepro.io/api/v1/meta/emerging?limit=50&min_confidence=25
[200] GET https://api.axiepro.io/api/v1/meta/rising?limit=50&min_confidence=25
[200] GET https://api.axiepro.io/api/v1/meta/summary?use_cache=true
[200] GET https://api.axiepro.io/api/v1/meta/fading?limit=50&min_confidence=25
```

---

### Portfolio (`/portfolio`)

> Wallet holdings tracker (New)

| Metric | Value |
|--------|-------|
| HTTP Status | 200 |
| Load Time | 2451ms |
| Page Title | AxiePro - Advanced Axie Infinity Market Analytics |
| Console Logs | 0 |
| Errors | 0 |
| Warnings | 0 |
| API Calls | 0 |
| Test Status | ✅ Passed |

**Content Found:**
- Header
- Wallet Button
- Nav: Home
- Nav: Explorer
- Nav: Breeding
- Nav: Analytics
- Footer

**Notes:**
- Page title: AxiePro - Advanced Axie Infinity Market Analytics

---

### Breeding (`/breeding`)

> Breeding simulator

| Metric | Value |
|--------|-------|
| HTTP Status | 200 |
| Load Time | 2681ms |
| Page Title | AxiePro - Advanced Axie Infinity Market Analytics |
| Console Logs | 0 |
| Errors | 0 |
| Warnings | 0 |
| API Calls | 0 |
| Test Status | ✅ Passed |

**Content Found:**
- Header
- Coming Soon
- Wallet Button
- Nav: Home
- Nav: Explorer
- Nav: Breeding
- Nav: Analytics
- Footer

**Notes:**
- Page title: AxiePro - Advanced Axie Infinity Market Analytics
- Coming Soon placeholder detected

---

### Analytics (`/analytics`)

> Market analytics

| Metric | Value |
|--------|-------|
| HTTP Status | 200 |
| Load Time | 2613ms |
| Page Title | AxiePro - Advanced Axie Infinity Market Analytics |
| Console Logs | 4 |
| Errors | 4 |
| Warnings | 0 |
| API Calls | 3 |
| Test Status | ❌ Failed |

**Content Found:**
- Header
- Wallet Button
- Nav: Home
- Nav: Explorer
- Nav: Breeding
- Nav: Analytics
- Footer

**Notes:**
- Page title: AxiePro - Advanced Axie Infinity Market Analytics

**API Calls:**
```
[200] GET https://api.axiepro.io/api/v1/market/stats?use_cache=true
[200] GET https://api.axiepro.io/api/v1/valuation/deals/live?min_score=60&include_normalized=true
[200] GET https://api.axiepro.io/api/v1/valuation/stats/floors
```

**Console Errors:**
```
[error] Access to fetch at 'https://api.axiepro.io/api/v1/market/sales/recent?hours=24&limit=200' from origin 'https://app.axiepro.io' has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.
[error] Failed to load resource: net::ERR_FAILED
[error] Access to fetch at 'https://api.axiepro.io/api/v1/market/sales/recent?hours=24&limit=200' from origin 'https://app.axiepro.io' has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.
[error] Failed to load resource: net::ERR_FAILED
```

---

### Market (`/market`)

> Market data and listings

| Metric | Value |
|--------|-------|
| HTTP Status | 200 |
| Load Time | 2236ms |
| Page Title | AxiePro - Advanced Axie Infinity Market Analytics |
| Console Logs | 0 |
| Errors | 0 |
| Warnings | 0 |
| API Calls | 2 |
| Test Status | ✅ Passed |

**Content Found:**
- Header
- Coming Soon
- Wallet Button
- Nav: Home
- Nav: Explorer
- Nav: Breeding
- Nav: Analytics
- Footer

**Notes:**
- Page title: AxiePro - Advanced Axie Infinity Market Analytics
- Coming Soon placeholder detected

**API Calls:**
```
[200] GET https://api.axiepro.io/api/v1/valuation/deals/snipes?limit=5&include_normalized=true
[200] GET https://api.axiepro.io/api/v1/valuation/stats/floors
```

---

### Privacy (`/privacy`)

> Privacy policy

| Metric | Value |
|--------|-------|
| HTTP Status | 200 |
| Load Time | 2649ms |
| Page Title | AxiePro - Advanced Axie Infinity Market Analytics |
| Console Logs | 0 |
| Errors | 0 |
| Warnings | 0 |
| API Calls | 0 |
| Test Status | ✅ Passed |

**Content Found:**
- Header
- Wallet Button
- Nav: Home
- Nav: Explorer
- Nav: Breeding
- Nav: Analytics
- Footer

**Notes:**
- Page title: AxiePro - Advanced Axie Infinity Market Analytics

---

### Terms (`/terms`)

> Terms of service

| Metric | Value |
|--------|-------|
| HTTP Status | 200 |
| Load Time | 2549ms |
| Page Title | AxiePro - Advanced Axie Infinity Market Analytics |
| Console Logs | 0 |
| Errors | 0 |
| Warnings | 0 |
| API Calls | 0 |
| Test Status | ✅ Passed |

**Content Found:**
- Header
- Wallet Button
- Nav: Home
- Nav: Explorer
- Nav: Breeding
- Nav: Analytics
- Footer

**Notes:**
- Page title: AxiePro - Advanced Axie Infinity Market Analytics

---

## Recommendations

Based on the test results:

1. **Deploy Missing Routes**: The following routes return 404 and should be deployed:

2. **Complete "Coming Soon" Features**: Routes marked as "Coming Soon" should be prioritized for completion.

3. **Navigation Consistency**: Ensure all routes in the header navigation are accessible and deployed.

4. **Error Monitoring**: Set up error tracking for production to catch console errors.

## Test Environment

- **Base URL**: https://app.axiepro.io
- **Browser**: Chromium
- **Test Framework**: Playwright
