# AxiePro Frontend Wiring & Deployment Plan

**Created:** 2025-12-29
**Status:** Ready for Execution

---

## Executive Summary

After deep analysis, I discovered that the **frontend code is complete but not deployed**. All React components, hooks, and API clients exist locally but haven't been committed to Git. Vercel is deploying an old version with placeholder data.

### Root Cause Analysis

| Issue | Explanation |
|-------|-------------|
| Static Data on Production | Old code deployed before components were built |
| "Coming Soon" Placeholders | Analytics/Deals pages show old placeholder content |
| 404 on /api, /docs | Footer links to non-existent internal pages |
| No Live API Calls | Latest hooks not deployed to production |

### Solution

1. Fix footer links (point to external resources)
2. Commit all new frontend components
3. Push to Git (triggers Vercel auto-deploy)
4. Verify `NEXT_PUBLIC_API_URL` in Vercel

---

## Component Architecture (Already Built)

### Hooks Layer

```
frontend/src/hooks/
├── index.ts              # Central exports
├── use-valuation.ts      # useValuation() - Axie fair values
├── use-deals.ts          # useDeals(), useSnipes() - Deal discovery
├── use-floor-prices.ts   # useFloorPrices() - Class floor prices
└── use-market-stats.ts   # useMarketStats(), useSales(), useListings()
```

### API Client Layer

```
frontend/src/lib/api/
├── client.ts             # Base fetch wrapper with error handling
└── market.ts             # marketApi.getStats(), getSales(), etc.
```

### Component Layer

```
frontend/src/components/
├── dashboard/
│   ├── market-pulse.tsx  # Live market stats - uses useMarketStats()
│   ├── top-deals.tsx     # Deal list - uses useDeals()
│   └── floor-chart.tsx   # Floor price visualization
├── analytics/
│   ├── market-overview-stats.tsx
│   ├── floor-prices-chart.tsx
│   ├── recent-sales-chart.tsx
│   ├── class-volume-chart.tsx
│   └── top-deals-table.tsx
├── deals/
│   ├── deal-detail-card.tsx
│   └── valuation-breakdown.tsx
└── valuation/
    ├── price-display.tsx
    ├── deal-indicator.tsx
    ├── valuation-badge.tsx
    ├── valuation-compact.tsx
    └── valuation-card.tsx
```

### Page Layer

```
frontend/src/app/
├── page.tsx              # Homepage - uses MarketPulse, TopDeals, FloorChart
├── analytics/page.tsx    # Full analytics - all chart components
├── deals/page.tsx        # Deal discovery - useDeals, useSnipes
├── explorer/page.tsx     # Coming Soon (planned)
├── market/page.tsx       # Coming Soon (planned)
└── breeding/page.tsx     # Coming Soon (planned)
```

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Backend API                               │
│  https://api.axiepro.io/api/v1/                                 │
│  ├── /market/stats     → 24h/7d/30d market statistics           │
│  ├── /market/sales     → Historical sales with filters          │
│  ├── /market/listings  → Active marketplace listings            │
│  ├── /valuation/deals  → Undervalued Axies (deal detection)     │
│  ├── /valuation/snipes → Quick-flip opportunities               │
│  └── /valuation/{id}   → Individual Axie valuation              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API Client Layer                              │
│  frontend/src/lib/api/                                          │
│  ├── client.ts → apiClient() with error handling                │
│  └── market.ts → marketApi.getStats(), getSales(), etc.         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    React Query Hooks                             │
│  frontend/src/hooks/                                            │
│  ├── useMarketStats()  → Cached market data (1min stale)        │
│  ├── useDeals()        → Deal opportunities (30s polling)       │
│  ├── useSnipes()       → Time-sensitive snipes                  │
│  └── useFloorPrices()  → Floor prices by class                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    UI Components                                 │
│  ├── MarketPulse       → 4 stat cards (volume, sales, floor)    │
│  ├── TopDeals          → Deal list with scores/discounts        │
│  ├── FloorPricesChart  → Floor by class visualization           │
│  ├── RecentSalesChart  → Price history chart                    │
│  └── TopDealsTable     → Full deals with marketplace links      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Status

### Already Complete (Local)

| File | Status | Description |
|------|--------|-------------|
| `hooks/use-market-stats.ts` | ✅ Built | Market data hooks |
| `hooks/use-deals.ts` | ✅ Built | Deal detection hooks |
| `lib/api/market.ts` | ✅ Built | API client functions |
| `components/dashboard/*` | ✅ Built | Dashboard widgets |
| `components/analytics/*` | ✅ Built | Analytics charts |
| `components/deals/*` | ✅ Built | Deal cards |
| `app/page.tsx` | ✅ Wired | Uses MarketPulse, TopDeals |
| `app/analytics/page.tsx` | ✅ Wired | Full analytics suite |
| `app/deals/page.tsx` | ✅ Wired | Deal discovery page |

### Needs Deployment

| Task | Status | Action |
|------|--------|--------|
| Footer links | ✅ Fixed | Changed to external URLs |
| Git commit | ⏳ Pending | Stage all new files |
| Git push | ⏳ Pending | Triggers Vercel deploy |
| Vercel env vars | ⏳ Pending | Verify NEXT_PUBLIC_API_URL |

---

## Deployment Checklist

### Pre-Deployment

- [x] Footer links fixed (no more 404s)
- [x] All components exist locally
- [x] All hooks wired to API client
- [x] Pages import and use components
- [ ] NEXT_PUBLIC_API_URL verified in Vercel

### Files to Commit

**New Files (Untracked):**
```
frontend/src/components/analytics/
frontend/src/components/dashboard/
frontend/src/components/deals/
frontend/src/hooks/use-market-stats.ts
frontend/src/lib/api/market.ts
frontend/src/types/market.ts
```

**Modified Files:**
```
frontend/src/app/page.tsx
frontend/src/app/analytics/page.tsx
frontend/src/app/deals/page.tsx
frontend/src/hooks/index.ts
frontend/src/components/layout/footer.tsx
```

### Post-Deployment Verification

1. Homepage loads with live market data
2. Analytics page shows real charts
3. Deals page shows actual opportunities
4. No 404 errors in console
5. Footer links work (external)

---

## Environment Configuration

### Required Vercel Environment Variable

```
NEXT_PUBLIC_API_URL=https://api.axiepro.io
```

**Where to set:**
1. Go to Vercel Dashboard → Project → Settings → Environment Variables
2. Add variable for Production environment
3. Redeploy if needed

### Backend CORS (Already Configured)

```python
# backend/src/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Accepts all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| API not responding | Low | High | Backend is on App Runner with health checks |
| CORS errors | Low | High | Already configured for all origins |
| Env var missing | Medium | High | Verify in Vercel before pushing |
| Build failure | Low | Medium | Local build passes |

---

## Execution Steps

### Step 1: Stage All Frontend Files
```bash
git add frontend/src/components/analytics/
git add frontend/src/components/dashboard/
git add frontend/src/components/deals/
git add frontend/src/hooks/
git add frontend/src/lib/api/market.ts
git add frontend/src/types/market.ts
git add frontend/src/app/
git add frontend/src/components/layout/footer.tsx
```

### Step 2: Commit
```bash
git commit -m "Deploy complete frontend with live API integration

- Add dashboard components (MarketPulse, TopDeals, FloorChart)
- Add analytics components (charts, tables, stats)
- Add deals page with deal discovery functionality
- Add React Query hooks for all API endpoints
- Add market API client with typed responses
- Fix footer links (external resources)
- Wire homepage to live market data
- Wire analytics page to full chart suite

🤖 Generated with Claude Code"
```

### Step 3: Push
```bash
git push origin main
```

### Step 4: Verify Deployment
- Check Vercel deployment logs
- Test live site for data
- Monitor console for errors

---

## Success Criteria

After deployment, the site should:

1. **Homepage**: Show real-time market stats (not hardcoded 125 ETH)
2. **Analytics**: Display interactive charts with live data
3. **Deals**: Show actual undervalued Axies with scores
4. **Footer**: All links work (no 404s)
5. **Console**: No API errors
6. **Network**: See actual API calls to api.axiepro.io

---

## Post-Deployment Roadmap

| Priority | Task | Effort |
|----------|------|--------|
| P1 | Verify live data displays correctly | 1 hour |
| P2 | Monitor for API errors | Ongoing |
| P3 | Build Explorer page functionality | 2-3 days |
| P4 | Build Breeding simulator | 2-3 days |
| P5 | Add wallet connection | 1-2 days |
