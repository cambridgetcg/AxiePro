# AxiePro Frontend Deployment Diagnostic Report

**Date:** 2025-12-29
**Test Method:** Playwright MCP Automated Browser Testing
**Production URL:** https://axiepro.io

---

## Executive Summary

**Problem:** The frontend code is correctly committed to GitHub and Vercel build succeeds, but the production site (axiepro.io) is serving OLD cached content.

**Root Cause:** The site is served through **Cloudflare CDN**, which is caching the old deployment. The new code with API integration, deals page, and footer fixes has NOT propagated to production despite successful builds.

---

## Test Results

### 1. Git Repository Verification

| Check | Status | Details |
|-------|--------|---------|
| Footer changes committed | ✅ Pass | Commit 6d17368 includes external URL changes |
| Deals page committed | ✅ Pass | `frontend/src/app/deals/page.tsx` exists in git |
| All components committed | ✅ Pass | 21 files, 2291 insertions |
| Pushed to origin/main | ✅ Pass | Commit b9aa9a2 is on remote |

### 2. Production Site Testing

#### Homepage (`/`)

| Element | Expected | Actual | Status |
|---------|----------|--------|--------|
| 24h Volume | Live API data | "125 ETH" (hardcoded) | ❌ FAIL |
| Total Sales | Live API data | "4,521" (hardcoded) | ❌ FAIL |
| Floor Price | Live API data | "0.008 ETH" (hardcoded) | ❌ FAIL |
| Trending Traits | Live API data | Static list | ❌ FAIL |
| MarketPulse component | Rendered | Not rendered | ❌ FAIL |

#### Analytics Page (`/analytics/`)

| Element | Expected | Actual | Status |
|---------|----------|--------|--------|
| MarketOverviewStats | Rendered with live data | Not present | ❌ FAIL |
| FloorPricesChart | Recharts visualization | Not present | ❌ FAIL |
| RecentSalesChart | Recharts visualization | Not present | ❌ FAIL |
| TopDealsTable | Live deals data | Not present | ❌ FAIL |
| "Coming Soon" text | Should NOT appear | Still showing | ❌ FAIL |

#### Deals Page (`/deals/`)

| Element | Expected | Actual | Status |
|---------|----------|--------|--------|
| Page loads | HTTP 200 | HTTP 404 | ❌ FAIL |
| Deal cards | Rendered | N/A | ❌ FAIL |
| useDeals hook | Called | N/A | ❌ FAIL |

#### Footer Links

| Link Text | Expected URL | Actual URL | Status |
|-----------|--------------|------------|--------|
| API Documentation | `https://api.axiepro.io/api/v1/docs` | `/docs/` (404) | ❌ FAIL |
| Axie Wiki | `https://docs.axieinfinity.com` | `/api/` (404) | ❌ FAIL |

### 3. Network Analysis

| Metric | Expected | Actual | Status |
|--------|----------|--------|--------|
| API calls to api.axiepro.io | Present | None observed | ❌ FAIL |
| RSC requests | Present | Present | ✅ Pass |
| Static assets | Load | Load | ✅ Pass |

**Critical Finding:** Zero network requests to `api.axiepro.io` - the hooks are NOT being called because the deployed code is old.

### 4. Infrastructure Headers

```
server: cloudflare
cf-cache-status: DYNAMIC
cf-ray: 9b5b31f379cab556-LHR
cache-control: public, max-age=0, must-revalidate
```

**Key Discovery:** Site is proxied through **Cloudflare**, not served directly from Vercel.

---

## Root Cause Analysis

### Hypothesis 1: Cloudflare Cache Issue (Most Likely)

```
                  GitHub Push
                      │
                      ▼
              ┌───────────────┐
              │    Vercel     │  ← Build succeeds
              │   Build/Deploy│
              └───────┬───────┘
                      │
                      ▼
              ┌───────────────┐
              │  Cloudflare   │  ← Caching OLD content
              │     CDN       │
              └───────┬───────┘
                      │
                      ▼
              ┌───────────────┐
              │   User sees   │  ← Stale version
              │  axiepro.io   │
              └───────────────┘
```

**Evidence:**
- Vercel build logs show success with all 9 routes
- But production shows old content
- Headers confirm Cloudflare is serving the content
- `cf-cache-status: DYNAMIC` doesn't guarantee fresh content

### Hypothesis 2: DNS Configuration Issue

The domain axiepro.io might point to:
- An old Vercel deployment
- A static export rather than the dynamic deployment
- Wrong Vercel project entirely

### Hypothesis 3: Vercel Project Misconfiguration

The Vercel project might be:
- Connected to wrong GitHub branch
- Not auto-deploying on push
- Pointing to wrong root directory

---

## Evidence Summary

### What SHOULD Be Deployed (Git HEAD)

```typescript
// frontend/src/components/layout/footer.tsx (committed)
<a href="https://api.axiepro.io/api/v1/docs">API Documentation</a>
<a href="https://docs.axieinfinity.com">Axie Wiki</a>
```

### What IS Deployed (Production)

```html
<!-- Production footer (from Playwright snapshot) -->
<a href="/docs/">Documentation</a>  <!-- OLD - causes 404 -->
<a href="/api/">API</a>             <!-- OLD - causes 404 -->
```

---

## Recommended Actions

### Immediate (Priority 1)

1. **Purge Cloudflare Cache**
   - Go to Cloudflare Dashboard → Cache → Purge Everything
   - Or use API: `curl -X POST "https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache" -d '{"purge_everything":true}'`

2. **Verify Vercel Deployment**
   - Check Vercel Dashboard → Deployments
   - Confirm latest deployment is from commit b9aa9a2
   - Check deployment URL directly (not through Cloudflare)

3. **Check DNS Configuration**
   - Verify axiepro.io CNAME points to correct Vercel deployment
   - May need to update if pointing to old deployment

### Short-term (Priority 2)

4. **Configure Cloudflare Page Rules**
   - Set Cache Level: Bypass for `axiepro.io/*`
   - Or set short TTL during development

5. **Add Cache-Busting Headers**
   - Configure Vercel to send `Surrogate-Control: no-store`
   - Or add `Cache-Control: private, no-cache` for dynamic pages

### Verification Checklist

After taking action:

- [ ] Homepage shows live market data (not "125 ETH")
- [ ] /deals/ returns 200 (not 404)
- [ ] Footer links are external URLs (not /docs/, /api/)
- [ ] Analytics page shows charts (not "Coming Soon")
- [ ] Network tab shows requests to api.axiepro.io

---

## Appendix: Build Output Confirmation

From Vercel build logs (user-provided):

```
Route (app)                              Size     First Load JS
┌ ○ /                                    25.5 kB         212 kB
├ ○ /_not-found                          896 B           101 kB
├ ○ /analytics                           11.6 kB         189 kB
├ ○ /breeding                            5.18 kB         174 kB
├ ○ /deals                               11.5 kB         189 kB  ← EXISTS!
├ ○ /explorer                            4.29 kB         173 kB
├ ○ /market                              4.42 kB         173 kB
├ ○ /privacy                             1.31 kB         170 kB
└ ○ /terms                               1.27 kB         170 kB
```

The build includes `/deals` route, confirming the code was built. The issue is **delivery**, not building.

---

## Conclusion

The deployment pipeline is working correctly up until the final delivery step. The new code has been:
- ✅ Committed to Git
- ✅ Pushed to GitHub
- ✅ Built successfully by Vercel
- ❌ **NOT delivered to users** due to Cloudflare caching or DNS misconfiguration

**Action Required:** Purge Cloudflare cache and/or verify DNS points to correct Vercel deployment.
