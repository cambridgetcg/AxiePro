# AxiePro E2E Test Insights

Generated: 2026-01-21T11:04:04.550Z

## Executive Summary

- **Total Routes Tested**: 10
- **Passed**: 6
- **Failed/Issues**: 4
- **Not Deployed (404)**: 3

### Key Findings

**Routes Not Yet Deployed:**
- `/deals` (Deals)
- `/meta` (Meta)
- `/portfolio` (Portfolio)

**Routes with "Coming Soon" Placeholder:**
- `/explorer` (Explorer)
- `/breeding` (Breeding)
- `/analytics` (Analytics)
- `/market` (Market)

**Routes with Console Errors:**
- `/explorer` (Explorer): 4 errors
- `/deals` (Deals): 5 errors
- `/meta` (Meta): 5 errors
- `/portfolio` (Portfolio): 5 errors

## Route Summary

| Route | Name | Status | Load Time | Errors | Warnings | API Calls | State |
|-------|------|--------|-----------|--------|----------|-----------|-------|
| `/` | Home | 200 | 2314ms | 0 | 0 | 0 | ✅ Live |
| `/explorer` | Explorer | 200 | 2353ms | 4 | 0 | 2 | 🚧 Coming Soon |
| `/deals` | Deals | 404 | 2424ms | 5 | 0 | 2 | ❌ Not Deployed |
| `/meta` | Meta | 404 | 2358ms | 5 | 0 | 2 | ❌ Not Deployed |
| `/portfolio` | Portfolio | 404 | 2226ms | 5 | 0 | 2 | ❌ Not Deployed |
| `/breeding` | Breeding | 200 | 2484ms | 0 | 0 | 0 | 🚧 Coming Soon |
| `/analytics` | Analytics | 200 | 2356ms | 0 | 0 | 0 | 🚧 Coming Soon |
| `/market` | Market | 200 | 2388ms | 0 | 0 | 0 | 🚧 Coming Soon |
| `/privacy` | Privacy | 200 | 2359ms | 0 | 0 | 0 | ✅ Live |
| `/terms` | Terms | 200 | 2439ms | 0 | 0 | 0 | ✅ Live |

## Detailed Route Analysis

### Home (`/`)

> Landing page with hero and features

| Metric | Value |
|--------|-------|
| HTTP Status | 200 |
| Load Time | 2314ms |
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
- Nav: Market
- Nav: Breeding
- Nav: Analytics
- Footer

**Notes:**
- Page title: AxiePro - Advanced Axie Infinity Market Analytics

---

### Explorer (`/explorer`)

> Axie search and filtering

| Metric | Value |
|--------|-------|
| HTTP Status | 200 |
| Load Time | 2353ms |
| Page Title | AxiePro - Advanced Axie Infinity Market Analytics |
| Console Logs | 4 |
| Errors | 4 |
| Warnings | 0 |
| API Calls | 2 |
| Test Status | ❌ Failed |

**Content Found:**
- Header
- Coming Soon
- Wallet Button
- Nav: Home
- Nav: Explorer
- Nav: Market
- Nav: Breeding
- Nav: Analytics
- Footer

**Notes:**
- Page title: AxiePro - Advanced Axie Infinity Market Analytics
- Coming Soon placeholder detected

**API Calls:**
```
[404] GET https://axiepro.io/api/
[404] GET https://axiepro.io/api/__next._tree.txt?_rsc=7fcca
```

**Console Errors:**
```
[error] Failed to load resource: the server responded with a status of 404 ()
[error] Failed to load resource: the server responded with a status of 404 ()
[error] Failed to load resource: the server responded with a status of 404 ()
[error] Failed to load resource: the server responded with a status of 404 ()
```

---

### Deals (`/deals`)

> Undervalued listing detection

| Metric | Value |
|--------|-------|
| HTTP Status | 404 |
| Load Time | 2424ms |
| Page Title | AxiePro - Advanced Axie Infinity Market Analytics |
| Console Logs | 5 |
| Errors | 5 |
| Warnings | 0 |
| API Calls | 2 |
| Test Status | ❌ Failed |

**Content Found:**
- Header
- 404 Page
- Wallet Button
- Nav: Home
- Nav: Explorer
- Nav: Market
- Nav: Breeding
- Nav: Analytics
- Footer

**Notes:**
- Page title: AxiePro - Advanced Axie Infinity Market Analytics
- 404 Page detected - route not deployed

**API Calls:**
```
[404] GET https://axiepro.io/api/
[404] GET https://axiepro.io/api/__next._tree.txt?_rsc=65jui
```

**Console Errors:**
```
[error] Failed to load resource: the server responded with a status of 404 ()
[error] Failed to load resource: the server responded with a status of 404 ()
[error] Failed to load resource: the server responded with a status of 404 ()
[error] Failed to load resource: the server responded with a status of 404 ()
[error] Failed to load resource: the server responded with a status of 404 ()
```

---

### Meta (`/meta`)

> Meta shifts analysis (New)

| Metric | Value |
|--------|-------|
| HTTP Status | 404 |
| Load Time | 2358ms |
| Page Title | AxiePro - Advanced Axie Infinity Market Analytics |
| Console Logs | 5 |
| Errors | 5 |
| Warnings | 0 |
| API Calls | 2 |
| Test Status | ❌ Failed |

**Content Found:**
- Header
- 404 Page
- Wallet Button
- Nav: Home
- Nav: Explorer
- Nav: Market
- Nav: Breeding
- Nav: Analytics
- Footer

**Notes:**
- Page title: AxiePro - Advanced Axie Infinity Market Analytics
- 404 Page detected - route not deployed

**API Calls:**
```
[404] GET https://axiepro.io/api/
[404] GET https://axiepro.io/api/__next._tree.txt?_rsc=65jui
```

**Console Errors:**
```
[error] Failed to load resource: the server responded with a status of 404 ()
[error] Failed to load resource: the server responded with a status of 404 ()
[error] Failed to load resource: the server responded with a status of 404 ()
[error] Failed to load resource: the server responded with a status of 404 ()
[error] Failed to load resource: the server responded with a status of 404 ()
```

---

### Portfolio (`/portfolio`)

> Wallet holdings tracker (New)

| Metric | Value |
|--------|-------|
| HTTP Status | 404 |
| Load Time | 2226ms |
| Page Title | AxiePro - Advanced Axie Infinity Market Analytics |
| Console Logs | 5 |
| Errors | 5 |
| Warnings | 0 |
| API Calls | 2 |
| Test Status | ❌ Failed |

**Content Found:**
- Header
- 404 Page
- Wallet Button
- Nav: Home
- Nav: Explorer
- Nav: Market
- Nav: Breeding
- Nav: Analytics
- Footer

**Notes:**
- Page title: AxiePro - Advanced Axie Infinity Market Analytics
- 404 Page detected - route not deployed

**API Calls:**
```
[404] GET https://axiepro.io/api/
[404] GET https://axiepro.io/api/__next._tree.txt?_rsc=65jui
```

**Console Errors:**
```
[error] Failed to load resource: the server responded with a status of 404 ()
[error] Failed to load resource: the server responded with a status of 404 ()
[error] Failed to load resource: the server responded with a status of 404 ()
[error] Failed to load resource: the server responded with a status of 404 ()
[error] Failed to load resource: the server responded with a status of 404 ()
```

---

### Breeding (`/breeding`)

> Breeding simulator

| Metric | Value |
|--------|-------|
| HTTP Status | 200 |
| Load Time | 2484ms |
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
- Nav: Market
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
| Load Time | 2356ms |
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
- Nav: Market
- Nav: Breeding
- Nav: Analytics
- Footer

**Notes:**
- Page title: AxiePro - Advanced Axie Infinity Market Analytics
- Coming Soon placeholder detected

---

### Market (`/market`)

> Market data and listings

| Metric | Value |
|--------|-------|
| HTTP Status | 200 |
| Load Time | 2388ms |
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
- Nav: Market
- Nav: Breeding
- Nav: Analytics
- Footer

**Notes:**
- Page title: AxiePro - Advanced Axie Infinity Market Analytics
- Coming Soon placeholder detected

---

### Privacy (`/privacy`)

> Privacy policy

| Metric | Value |
|--------|-------|
| HTTP Status | 200 |
| Load Time | 2359ms |
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
- Nav: Market
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
| Load Time | 2439ms |
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
- Nav: Market
- Nav: Breeding
- Nav: Analytics
- Footer

**Notes:**
- Page title: AxiePro - Advanced Axie Infinity Market Analytics

---

## Recommendations

Based on the test results:

1. **Deploy Missing Routes**: The following routes return 404 and should be deployed:
   - /deals (Deals)
   - /meta (Meta)
   - /portfolio (Portfolio)

2. **Complete "Coming Soon" Features**: Routes marked as "Coming Soon" should be prioritized for completion.

3. **Navigation Consistency**: Ensure all routes in the header navigation are accessible and deployed.

4. **Error Monitoring**: Set up error tracking for production to catch console errors.

## Test Environment

- **Base URL**: https://axiepro.io
- **Browser**: Chromium
- **Test Framework**: Playwright
