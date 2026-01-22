# AxiePro E2E Test Insights

Generated: 2026-01-22T09:53:58.914Z

## Executive Summary

- **Total Routes Tested**: 10
- **Passed**: 7
- **Failed/Issues**: 3
- **Not Deployed (404)**: 0

### Key Findings

**Routes with "Coming Soon" Placeholder:**
- `/explorer` (Explorer)
- `/breeding` (Breeding)
- `/market` (Market)

**Routes with Console Errors:**
- `/meta` (Meta): 2 errors

## Route Summary

| Route | Name | Status | Load Time | Errors | Warnings | API Calls | State |
|-------|------|--------|-----------|--------|----------|-----------|-------|
| `/` | Home | 200 | 2251ms | 0 | 0 | 4 | ⚠️ Issues |
| `/explorer` | Explorer | 200 | 2577ms | 0 | 0 | 0 | 🚧 Coming Soon |
| `/deals` | Deals | 200 | 2633ms | 0 | 0 | 2 | ✅ Live |
| `/meta` | Meta | 200 | 2566ms | 2 | 0 | 6 | ⚠️ Issues |
| `/portfolio` | Portfolio | 200 | 2397ms | 0 | 0 | 0 | ✅ Live |
| `/breeding` | Breeding | 200 | 2521ms | 0 | 0 | 0 | 🚧 Coming Soon |
| `/analytics` | Analytics | 200 | 2523ms | 0 | 0 | 4 | ⚠️ Issues |
| `/market` | Market | 200 | 2522ms | 0 | 0 | 2 | 🚧 Coming Soon |
| `/privacy` | Privacy | 200 | 2539ms | 0 | 0 | 0 | ✅ Live |
| `/terms` | Terms | 200 | 2487ms | 0 | 0 | 0 | ✅ Live |

## Detailed Route Analysis

### Home (`/`)

> Landing page with hero and features

| Metric | Value |
|--------|-------|
| HTTP Status | 200 |
| Load Time | 2251ms |
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

### Explorer (`/explorer`)

> Axie search and filtering

| Metric | Value |
|--------|-------|
| HTTP Status | 200 |
| Load Time | 2577ms |
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
| Load Time | 2633ms |
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
| Load Time | 2566ms |
| Page Title | AxiePro - Advanced Axie Infinity Market Analytics |
| Console Logs | 2 |
| Errors | 2 |
| Warnings | 0 |
| API Calls | 6 |
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
[200] GET https://api.axiepro.io/api/v1/meta/rising?limit=50&min_confidence=25
[200] GET https://api.axiepro.io/api/v1/meta/emerging?limit=50&min_confidence=25
[200] GET https://api.axiepro.io/api/v1/meta/falling?limit=50&min_confidence=25
[503] GET https://api.axiepro.io/api/v1/meta/summary
[200] GET https://api.axiepro.io/api/v1/meta/fading?limit=50&min_confidence=25
[503] GET https://api.axiepro.io/api/v1/meta/summary
```

**Console Errors:**
```
[error] Failed to load resource: the server responded with a status of 503 (Service Unavailable)
[error] Failed to load resource: the server responded with a status of 503 (Service Unavailable)
```

---

### Portfolio (`/portfolio`)

> Wallet holdings tracker (New)

| Metric | Value |
|--------|-------|
| HTTP Status | 200 |
| Load Time | 2397ms |
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
| Load Time | 2521ms |
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
| Load Time | 2523ms |
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
[200] GET https://api.axiepro.io/api/v1/valuation/deals/live?min_score=60&include_normalized=true
[200] GET https://api.axiepro.io/api/v1/market/stats
[200] GET https://api.axiepro.io/api/v1/valuation/stats/floors
[200] GET https://api.axiepro.io/api/v1/market/sales?per_page=100
```

---

### Market (`/market`)

> Market data and listings

| Metric | Value |
|--------|-------|
| HTTP Status | 200 |
| Load Time | 2522ms |
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
| Load Time | 2539ms |
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
| Load Time | 2487ms |
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

- **Base URL**: https://www.axiepro.io
- **Browser**: Chromium
- **Test Framework**: Playwright
