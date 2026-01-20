# AxiePro Frontend Documentation

**Last Updated:** 2025-12-29
**Production URL:** https://axiepro.io
**Framework:** Next.js 16 (App Router) on Vercel

---

## Overview

The AxiePro frontend provides a responsive interface for Axie Infinity market analytics, deal discovery, and breeding optimization. Built with modern React patterns and real-time data fetching.

### Core User Goals

| User Type | Primary Need | Key Features |
|-----------|--------------|--------------|
| **Casual Trader** | Find deals, avoid overpaying | Deal alerts, fair value check |
| **Active Trader** | Exploit market inefficiencies | Temporal arbitrage, whale tracking |
| **Breeder** | Maximize breeding ROI | Breeding simulator, hidden value score |
| **Data Analyst** | Understand market dynamics | Analytics dashboard, data export |
| **Meta Chaser** | Stay ahead of trends | Meta shift alerts, part momentum |

---

## Tech Stack

| Component | Version | Purpose |
|-----------|---------|---------|
| Next.js | 16.0.10 | React framework with App Router |
| React | 19.2.1 | UI library |
| TypeScript | 5.x | Type safety |
| TanStack Query | 5.90.12 | Data fetching & caching |
| Zustand | 5.0.9 | Client state management |
| Recharts | 3.6.0 | Data visualization |
| TradingView Charts | - | Price charts |
| Tailwind CSS | 4.x | Styling |
| shadcn/ui | - | Component library |
| React Hook Form | - | Form handling |
| Zod | - | Validation |

---

## Project Structure

```
frontend/
├── src/
│   ├── app/                          # Next.js App Router
│   │   ├── layout.tsx                # Root layout
│   │   ├── page.tsx                  # Dashboard
│   │   ├── explorer/
│   │   │   ├── page.tsx              # Axie browser
│   │   │   └── [id]/page.tsx         # Axie detail
│   │   ├── market/page.tsx           # Market overview
│   │   ├── breeding/page.tsx         # Breeding simulator
│   │   ├── analytics/page.tsx        # Analytics dashboard
│   │   ├── deals/page.tsx            # Deal discovery
│   │   ├── wallet/[address]/page.tsx # Wallet portfolio
│   │   └── alerts/page.tsx           # Alert configuration
│   │
│   ├── components/
│   │   ├── ui/                       # shadcn/ui components
│   │   ├── dashboard/
│   │   │   ├── market-pulse.tsx      # Live market stats
│   │   │   ├── top-deals.tsx         # Deal list
│   │   │   └── floor-chart.tsx       # Floor price visualization
│   │   ├── analytics/
│   │   │   ├── market-overview-stats.tsx
│   │   │   ├── floor-prices-chart.tsx
│   │   │   ├── recent-sales-chart.tsx
│   │   │   ├── class-volume-chart.tsx
│   │   │   └── top-deals-table.tsx
│   │   ├── deals/
│   │   │   ├── deal-detail-card.tsx
│   │   │   └── valuation-breakdown.tsx
│   │   ├── valuation/
│   │   │   ├── price-display.tsx
│   │   │   ├── deal-indicator.tsx
│   │   │   ├── valuation-badge.tsx
│   │   │   └── valuation-card.tsx
│   │   ├── axie/
│   │   │   ├── AxieCard.tsx          # Axie preview card
│   │   │   ├── AxieGrid.tsx          # Grid of cards
│   │   │   ├── AxieFilters.tsx       # Filter sidebar
│   │   │   ├── GeneDisplay.tsx       # Gene visualization
│   │   │   └── PurityBadge.tsx       # Purity indicator
│   │   ├── breeding/
│   │   │   ├── BreedingSimulator.tsx
│   │   │   ├── ParentSelector.tsx
│   │   │   ├── OutcomePreview.tsx
│   │   │   └── ROICalculator.tsx
│   │   └── layout/
│   │       ├── Header.tsx
│   │       ├── Sidebar.tsx
│   │       └── Footer.tsx
│   │
│   ├── hooks/
│   │   ├── index.ts                  # Central exports
│   │   ├── use-valuation.ts          # Axie fair values
│   │   ├── use-deals.ts              # Deal discovery
│   │   ├── use-floor-prices.ts       # Floor prices
│   │   └── use-market-stats.ts       # Market data
│   │
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts             # Base fetch wrapper
│   │   │   └── market.ts             # Market API functions
│   │   ├── constants.ts
│   │   ├── utils.ts
│   │   └── types.ts
│   │
│   └── stores/
│       ├── filterStore.ts            # Filter state
│       └── breedingStore.ts          # Breeding selections
│
├── public/images/
├── tailwind.config.ts
├── next.config.js
└── package.json
```

---

## Information Architecture

```
AxiePro
├── / (Dashboard)
│   ├── Market Overview Cards
│   ├── Deal Opportunities
│   ├── Trending Parts
│   └── Recent Activity
│
├── /explorer
│   ├── Advanced Search & Filters
│   ├── Axie Grid/List View
│   └── /explorer/[id] (Axie Detail)
│       ├── Valuation Analysis
│       ├── Gene Breakdown
│       ├── Price History
│       └── Breeding Potential
│
├── /deals
│   ├── Live Deals (Z-score < -2)
│   ├── Snipe Opportunities (40%+ discount)
│   ├── Deal History
│   └── Alert Configuration
│
├── /market
│   ├── Floor Prices by Class
│   ├── Sales History
│   ├── Volume Analysis
│   └── /market/part/[partId] (Part Detail)
│
├── /analytics
│   ├── Overview Dashboard
│   ├── /analytics/trends (Meta Shifts)
│   ├── /analytics/temporal (Time Patterns)
│   └── /analytics/whales (Whale Tracking)
│
├── /breeding
│   ├── Simulator
│   ├── /breeding/optimizer (Best Pairs)
│   ├── /breeding/arbitrage (ROI Scanner)
│   └── /breeding/hidden-value (HVS Explorer)
│
├── /wallet/[address]
│   ├── Portfolio Overview
│   ├── Holdings
│   ├── Trade History
│   └── P&L Analysis
│
└── /alerts
    ├── Deal Alerts
    ├── Price Alerts
    └── Whale Alerts
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

## State Management

### Server State (TanStack Query)

```tsx
// hooks/use-market-stats.ts
export function useMarketStats() {
  return useQuery({
    queryKey: ['market', 'stats'],
    queryFn: () => marketApi.getStats(),
    staleTime: 60 * 1000, // 1 minute
  });
}

// hooks/use-deals.ts
export function useDeals(filters: DealFilters) {
  return useQuery({
    queryKey: ['deals', filters],
    queryFn: () => valuationApi.getDeals(filters),
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 30 * 1000, // Auto-refresh
  });
}

// hooks/use-valuation.ts
export function useValuation(axieId: number) {
  return useQuery({
    queryKey: ['valuation', axieId],
    queryFn: () => valuationApi.getValue(axieId),
    enabled: !!axieId,
  });
}
```

### Client State (Zustand)

```tsx
// stores/breedingStore.ts
interface BreedingStore {
  matron: Axie | null;
  sire: Axie | null;
  setMatron: (axie: Axie | null) => void;
  setSire: (axie: Axie | null) => void;
  swap: () => void;
  clear: () => void;
}

export const useBreedingStore = create<BreedingStore>((set) => ({
  matron: null,
  sire: null,
  setMatron: (axie) => set({ matron: axie }),
  setSire: (axie) => set({ sire: axie }),
  swap: () => set((state) => ({ matron: state.sire, sire: state.matron })),
  clear: () => set({ matron: null, sire: null }),
}));
```

### Caching Strategy

| Data Type | Stale Time | Cache Time | Refetch |
|-----------|------------|------------|---------|
| Live Deals | 30 seconds | 1 minute | Focus |
| Valuation | 1 minute | 5 minutes | Manual |
| Floor Prices | 1 minute | 5 minutes | Interval |
| Analytics | 5 minutes | 30 minutes | Manual |
| Part History | 15 minutes | 1 hour | Manual |

---

## Core Components

### DealCard Component

```tsx
interface DealCardProps {
  axie: Axie;
  fmv: number;
  discount: number;
  zScore: number;
  confidence: number;
}
```

Displays deal opportunity with:
- Axie image, ID, class, purity
- Listed price vs fair market value
- Discount percentage and Z-score
- Confidence indicator
- "Why it's a deal" explanation
- Marketplace link

### ValuationBreakdown Component

Shows hedonic model decomposition:
- Base value (class floor)
- Purity premium
- Breed count modifier
- Part premiums (with trend indicators)
- Total FMV with confidence interval

### GeneTable Component

```tsx
interface GeneTableProps {
  genes: AxieGenes;
  showValues?: boolean;
}
```

Displays full gene breakdown:
- Dominant, Recessive 1, Recessive 2 for each part
- Color-coded by class
- Value indicators for premium genes
- Hidden Value Score (HVS) calculation

---

## Backend Endpoints Required

### Current Endpoints (Live)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/market/stats` | Market overview stats |
| `GET /api/v1/market/sales` | Historical sales |
| `GET /api/v1/market/listings` | Active listings |
| `GET /api/v1/valuation/deals` | Deal opportunities |
| `GET /api/v1/valuation/snipes` | Snipe opportunities |
| `GET /api/v1/valuation/{id}` | Individual valuation |
| `GET /api/v1/axies/search` | Axie search |
| `POST /api/v1/breeding/simulate` | Breeding simulation |

### Planned Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/analytics/meta-shifts` | TrendScore by part |
| `GET /api/v1/analytics/temporal-patterns` | Hour/day patterns |
| `GET /api/v1/analytics/whales` | Whale activity |
| `POST /api/v1/breeding/monte-carlo` | Monte Carlo simulation |
| `GET /api/v1/breeding/hidden-value/{id}` | Hidden value score |

---

## Implementation Status

### Current Deployment State

| Component | Deployed | Functional | Live Data |
|-----------|----------|------------|-----------|
| Homepage | Yes | Partial | Static |
| Explorer | Yes | No | Coming Soon |
| Market | Yes | No | Coming Soon |
| Breeding | Yes | No | Coming Soon |
| Analytics | Yes | No | Coming Soon |
| Deals | Yes | Yes | Live |
| Wallet Connect | Yes | No | Pending |

### Local vs Deployed Gap

| Feature | Local Code | Deployed |
|---------|------------|----------|
| Market Stats Hook | `useMarketStats()` | Partially connected |
| Deals Page | Full implementation | Working |
| Analytics Charts | Components built | Static placeholders |
| Breeding Simulator | Basic UI | Coming Soon |

### Files Ready to Deploy

**Analytics Components:**
- `market-overview-stats.tsx`
- `top-deals-table.tsx`
- `class-volume-chart.tsx`
- `floor-prices-chart.tsx`
- `recent-sales-chart.tsx`

**Dashboard Components:**
- `market-pulse.tsx`
- `top-deals.tsx`
- `floor-chart.tsx`

---

## Environment Configuration

### Vercel Environment Variables

```env
NEXT_PUBLIC_API_URL=https://api.axiepro.io
```

### Local Development

```bash
cd frontend
npm install
npm run dev  # http://localhost:3000
```

---

## Responsive Design

| Breakpoint | Layout Changes |
|------------|----------------|
| Mobile (<640px) | Single column, collapsible filters, bottom nav |
| Tablet (640-1024px) | 2-column grid, sidebar filters |
| Desktop (>1024px) | 3-4 column grid, persistent sidebar |

---

## Performance Optimizations

1. **Virtual Scrolling** - For large Axie grids (react-virtual)
2. **Image Optimization** - Next.js Image with lazy loading
3. **Query Caching** - TanStack Query with appropriate stale times
4. **Prefetching** - Prefetch Axie details on hover
5. **Code Splitting** - Dynamic imports for chart components

---

## Implementation Roadmap

### Phase 1: Core Value (Weeks 1-2)
- [x] Deal Finder page with live data
- [x] Dashboard market overview
- [ ] Connect Analytics charts to API
- [ ] Connect Market page to API

### Phase 2: Discovery (Weeks 3-4)
- [ ] Explorer search and filters
- [ ] Axie detail page with valuation
- [ ] Gene display component

### Phase 3: Breeding (Weeks 5-6)
- [ ] Breeding simulator UI
- [ ] Parent selection
- [ ] Outcome predictions
- [ ] ROI calculator

### Phase 4: Advanced (Weeks 7-8)
- [ ] Wallet connection (Ronin)
- [ ] Portfolio tracking
- [ ] Real-time alerts
- [ ] Mobile optimization

---

## Related Documentation

- **Architecture:** See `docs/ARCHITECTURE.md`
- **Database:** See `docs/DATABASE_SCHEMA.md`
- **Infrastructure:** See `docs/INFRASTRUCTURE.md`
- **API:** See `docs/03-api-specification.md`
