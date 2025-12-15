# Frontend Design

## Overview

The frontend is built with Next.js 14 using the App Router, providing a responsive interface for Axie discovery, market analysis, and breeding optimization.

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS + shadcn/ui components
- **State Management**: TanStack Query (server state), Zustand (client state)
- **Charts**: Recharts + TradingView Lightweight Charts
- **Tables**: TanStack Table
- **Forms**: React Hook Form + Zod validation

## Project Structure

```
frontend/
├── src/
│   ├── app/                          # Next.js App Router
│   │   ├── layout.tsx                # Root layout
│   │   ├── page.tsx                  # Home/Dashboard
│   │   ├── explorer/
│   │   │   ├── page.tsx              # Axie browser
│   │   │   └── [id]/page.tsx         # Axie detail
│   │   ├── market/
│   │   │   ├── page.tsx              # Market overview
│   │   │   ├── sales/page.tsx        # Sales history
│   │   │   └── listings/page.tsx     # Active listings
│   │   ├── breeding/
│   │   │   ├── page.tsx              # Breeding simulator
│   │   │   └── optimizer/page.tsx    # Best pairs finder
│   │   ├── analytics/
│   │   │   ├── page.tsx              # Analytics dashboard
│   │   │   ├── prices/page.tsx       # Price charts
│   │   │   └── trends/page.tsx       # Trending traits
│   │   ├── wallet/
│   │   │   └── [address]/page.tsx    # Wallet portfolio
│   │   └── api/                      # API routes (if needed)
│   │
│   ├── components/
│   │   ├── ui/                       # shadcn/ui components
│   │   ├── axie/
│   │   │   ├── AxieCard.tsx          # Axie preview card
│   │   │   ├── AxieDetail.tsx        # Full axie details
│   │   │   ├── AxieGrid.tsx          # Grid of axie cards
│   │   │   ├── AxieFilters.tsx       # Filter sidebar
│   │   │   ├── PartBadge.tsx         # Body part display
│   │   │   ├── GeneDisplay.tsx       # Gene visualization
│   │   │   └── PurityBadge.tsx       # Purity indicator
│   │   ├── market/
│   │   │   ├── PriceChart.tsx        # Price history chart
│   │   │   ├── SalesTable.tsx        # Recent sales table
│   │   │   ├── FloorPriceCard.tsx    # Floor price display
│   │   │   └── VolumeChart.tsx       # Volume over time
│   │   ├── breeding/
│   │   │   ├── BreedingSimulator.tsx # Main simulator
│   │   │   ├── ParentSelector.tsx    # Select matron/sire
│   │   │   ├── OutcomePreview.tsx    # Breeding outcomes
│   │   │   ├── ProbabilityTree.tsx   # Gene probabilities
│   │   │   └── ROICalculator.tsx     # Cost/profit calc
│   │   ├── wallet/
│   │   │   ├── WalletOverview.tsx    # Wallet summary
│   │   │   ├── HoldingsTable.tsx     # Axie holdings
│   │   │   ├── TradeHistory.tsx      # Buy/sell history
│   │   │   └── PnLChart.tsx          # Profit/loss chart
│   │   └── layout/
│   │       ├── Header.tsx            # Navigation header
│   │       ├── Sidebar.tsx           # Main navigation
│   │       ├── Footer.tsx            # Footer
│   │       └── SearchBar.tsx         # Global search
│   │
│   ├── hooks/
│   │   ├── useAxies.ts               # Axie queries
│   │   ├── useMarket.ts              # Market data queries
│   │   ├── useBreeding.ts            # Breeding calculations
│   │   ├── usePrices.ts              # Price history
│   │   └── useWallet.ts              # Wallet data
│   │
│   ├── lib/
│   │   ├── api.ts                    # API client
│   │   ├── constants.ts              # App constants
│   │   ├── utils.ts                  # Utility functions
│   │   └── types.ts                  # TypeScript types
│   │
│   └── stores/
│       ├── filterStore.ts            # Filter state
│       └── breedingStore.ts          # Breeding selections
│
├── public/
│   └── images/                       # Static images
│
├── tailwind.config.ts
├── next.config.js
└── package.json
```

---

## Page Designs

### 1. Home / Dashboard

**Route**: `/`

Overview of market activity and quick access to key features.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  [Logo]  Explorer   Market   Breeding   Analytics   [Search]   [Wallet] │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      MARKET OVERVIEW                             │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │   │
│  │  │ 24h Vol  │ │  Sales   │ │  Floor   │ │ Avg Price│           │   │
│  │  │ 125 ETH  │ │  4,521   │ │ 0.008 ETH│ │ 0.027 ETH│           │   │
│  │  │  ▲ 12%   │ │  ▲ 8%    │ │  ▼ 3%    │ │  ▲ 5%    │           │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌──────────────────────────┐  ┌──────────────────────────────────┐   │
│  │    TRENDING TRAITS ▲     │  │         RECENT SALES             │   │
│  │                          │  │                                  │   │
│  │  🟢 Nut Cracker   +15%   │  │  Beast #123456    0.045 ETH     │   │
│  │  🟢 Ronin Back    +12%   │  │  Plant #234567    0.032 ETH     │   │
│  │  🟢 Cottontail    +10%   │  │  Aqua  #345678    0.028 ETH     │   │
│  │  🔴 Cute Bunny    -8%    │  │  Beast #456789    0.025 ETH     │   │
│  │  🔴 Imp Horn      -6%    │  │  Bird  #567890    0.022 ETH     │   │
│  └──────────────────────────┘  └──────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │              FLOOR PRICES BY CLASS                               │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │        [Bar Chart: Floor prices per class]                 │ │   │
│  │  │  Beast | Plant | Aqua | Bird | Bug | Reptile | Mech | ...  │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2. Axie Explorer

**Route**: `/explorer`

Browse and filter Axies with advanced search capabilities.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            AXIE EXPLORER                                │
├─────────────────────────────────────────────────────────────────────────┤
│ ┌───────────────┐  ┌────────────────────────────────────────────────┐  │
│ │   FILTERS     │  │  Sort: [Price ▼]  View: [Grid] [List]  Found: 1,234│
│ │               │  ├────────────────────────────────────────────────┤  │
│ │ Class         │  │ ┌──────────┐ ┌──────────┐ ┌──────────┐        │  │
│ │ [x] Beast     │  │ │ [Image]  │ │ [Image]  │ │ [Image]  │        │  │
│ │ [ ] Plant     │  │ │ #123456  │ │ #234567  │ │ #345678  │        │  │
│ │ [ ] Aquatic   │  │ │ Beast    │ │ Beast    │ │ Beast    │        │  │
│ │ [ ] Bird      │  │ │ ★★★★★★  │ │ ★★★★★☆  │ │ ★★★★★★  │        │  │
│ │ ...           │  │ │ Breed: 0 │ │ Breed: 2 │ │ Breed: 1 │        │  │
│ │               │  │ │ 0.025 ETH│ │ 0.018 ETH│ │ 0.032 ETH│        │  │
│ │ Purity        │  │ └──────────┘ └──────────┘ └──────────┘        │  │
│ │ [====●===] 6  │  │                                                │  │
│ │               │  │ ┌──────────┐ ┌──────────┐ ┌──────────┐        │  │
│ │ Breed Count   │  │ │ [Image]  │ │ [Image]  │ │ [Image]  │        │  │
│ │ [==●======] 2 │  │ │ ...      │ │ ...      │ │ ...      │        │  │
│ │               │  │ └──────────┘ └──────────┘ └──────────┘        │  │
│ │ Price Range   │  │                                                │  │
│ │ [0.01] - [1]  │  │                    [Load More]                 │  │
│ │               │  └────────────────────────────────────────────────┘  │
│ │ ── PARTS ──   │                                                      │
│ │               │                                                      │
│ │ Mouth:        │                                                      │
│ │ [Nut Cracker▼]│                                                      │
│ │               │                                                      │
│ │ Horn:         │                                                      │
│ │ [Any        ▼]│                                                      │
│ │               │                                                      │
│ │ [Apply Filters]│                                                     │
│ └───────────────┘                                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3. Axie Detail Page

**Route**: `/explorer/[id]`

Detailed view of a single Axie with history and breeding info.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ← Back to Explorer                                    [Share] [Track]  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────┐  ┌──────────────────────────────────────────┐ │
│  │                     │  │  BEAST #12345678                         │ │
│  │      [Axie Image]   │  │  "Beastie McBeastface"                   │ │
│  │                     │  │                                          │ │
│  │                     │  │  Purity: ★★★★★★ (6/6)                   │ │
│  │                     │  │  Breed Count: 2/7                        │ │
│  │                     │  │  Owner: 0x1234...abcd                    │ │
│  └─────────────────────┘  │                                          │ │
│                           │  ┌────┬────┬────┬────┐                   │ │
│                           │  │ HP │ SPD│ SKL│ MRL│                   │ │
│                           │  │ 31 │ 35 │ 31 │ 43 │                   │ │
│                           │  └────┴────┴────┴────┘                   │ │
│                           │                                          │ │
│                           │  Listed: 0.025 ETH ($45.50)              │ │
│                           │  [View on Marketplace]                   │ │
│                           └──────────────────────────────────────────┘ │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  GENES & PARTS                                                   │   │
│  │  ┌─────────┬────────────────┬────────────────┬────────────────┐ │   │
│  │  │  Part   │   Dominant     │   Recessive 1  │   Recessive 2  │ │   │
│  │  ├─────────┼────────────────┼────────────────┼────────────────┤ │   │
│  │  │  Eyes   │ 🟡 Chubby      │ 🟡 Chubby      │ 🟢 Papi        │ │   │
│  │  │  Ears   │ 🟡 Nut Cracker │ 🟡 Nut Cracker │ 🔵 Puppy       │ │   │
│  │  │  Mouth  │ 🟡 Nut Cracker │ 🟡 Axie Kiss   │ 🟡 Nut Cracker │ │   │
│  │  │  Horn   │ 🟡 Little Branch│ 🔴 Imp        │ 🟡 Little Branch│ │   │
│  │  │  Back   │ 🟡 Ronin       │ 🟡 Ronin       │ 🔵 Hero        │ │   │
│  │  │  Tail   │ 🟡 Cottontail  │ 🟡 Hare        │ 🟡 Cottontail  │ │   │
│  │  └─────────┴────────────────┴────────────────┴────────────────┘ │   │
│  │  Gene Purity: 14/18                                              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌───────────────────────┐  ┌───────────────────────────────────────┐  │
│  │      ABILITIES        │  │          PRICE HISTORY                │  │
│  │                       │  │  ┌─────────────────────────────────┐  │  │
│  │  ⚔️ Nut Cracker       │  │  │     [Line chart of prices]     │  │  │
│  │  DMG: 105  SHD: 30    │  │  │                                 │  │  │
│  │  Apply 2 Fragile      │  │  └─────────────────────────────────┘  │  │
│  │                       │  │                                       │  │
│  │  ⚔️ Little Branch     │  │  Last Sale: 0.030 ETH (Dec 1, 2024)  │  │
│  │  DMG: 95   SHD: 40    │  │  Avg Similar: 0.028 ETH              │  │
│  │  ...                  │  │                                       │  │
│  └───────────────────────┘  └───────────────────────────────────────┘  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  FAMILY                                                          │   │
│  │  Parents: #11111111 (Matron) × #22222222 (Sire)                 │   │
│  │  Children: #33333333, #44444444                                 │   │
│  │  [Use in Breeding Simulator]                                    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4. Breeding Simulator

**Route**: `/breeding`

Simulate breeding outcomes and calculate ROI.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         BREEDING SIMULATOR                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────┐    ♥    ┌─────────────────────┐               │
│  │      MATRON         │         │        SIRE         │               │
│  │  ┌─────────────┐    │         │   ┌─────────────┐   │               │
│  │  │   [Image]   │    │         │   │   [Image]   │   │               │
│  │  └─────────────┘    │         │   └─────────────┘   │               │
│  │  #12345678          │         │   #87654321         │               │
│  │  Beast ★★★★★★      │         │   Beast ★★★★★☆    │               │
│  │  Breed: 2/7         │         │   Breed: 1/7        │               │
│  │                     │         │                     │               │
│  │  [Select Axie]      │         │   [Select Axie]     │               │
│  │  [Clear]            │         │   [Clear]           │               │
│  └─────────────────────┘         └─────────────────────┘               │
│                                                                         │
│                      [🧬 SIMULATE BREEDING]                             │
│                                                                         │
│  ═══════════════════════════════════════════════════════════════════   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  BREEDING COST                                                   │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                       │   │
│  │  │ 0.5 AXS  │  │ 900 SLP  │  │ $12.50   │                       │   │
│  │  │ ($4.25)  │  │ ($8.25)  │  │  TOTAL   │                       │   │
│  │  └──────────┘  └──────────┘  └──────────┘                       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  OFFSPRING PREDICTIONS                                           │   │
│  │                                                                   │   │
│  │  Class Probability:    ████████████████████░░ Beast (87.5%)     │   │
│  │                        ██░░░░░░░░░░░░░░░░░░░░ Mech (6.25%)      │   │
│  │                        ██░░░░░░░░░░░░░░░░░░░░ Dusk (6.25%)      │   │
│  │                                                                   │   │
│  │  ┌─────────────────────────────────────────────────────────────┐ │   │
│  │  │  PART PROBABILITIES                                         │ │   │
│  │  │  ┌────────┬──────────────────────────────────────────────┐  │ │   │
│  │  │  │ Mouth  │ Nut Cracker (46%) | Tiny Turtle (28%) | ...  │  │ │   │
│  │  │  │ Horn   │ Little Branch (50%) | Imp (25%) | ...        │  │ │   │
│  │  │  │ Back   │ Ronin (56%) | Hero (22%) | ...               │  │ │   │
│  │  │  │ Tail   │ Cottontail (46%) | Hare (31%) | ...          │  │ │   │
│  │  │  └────────┴──────────────────────────────────────────────┘  │ │   │
│  │  └─────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  ROI ANALYSIS                                                    │   │
│  │                                                                   │   │
│  │  Expected Value:        0.022 ETH ($39.60)                       │   │
│  │  Breeding Cost:         0.007 ETH ($12.50)                       │   │
│  │  Expected Profit:       0.015 ETH ($27.10)   ✅ +117% ROI       │   │
│  │                                                                   │   │
│  │  Break-even Probability: 68%                                     │   │
│  │                                                                   │   │
│  │  Best Outcome:          6-purity Beast w/ Nut Cracker (12.5%)   │   │
│  │                         Est. Value: 0.035 ETH                    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5. Analytics Dashboard

**Route**: `/analytics`

Market trends, price charts, and insights.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ANALYTICS    [Overview] [Prices] [Trends] [Whales]                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  TRAIT PRICE COMPARISON                              [7D ▼]     │   │
│  │  ┌───────────────────────────────────────────────────────────┐  │   │
│  │  │                                                           │  │   │
│  │  │           [Multi-line chart comparing traits]             │  │   │
│  │  │           - Nut Cracker (mouth)                           │  │   │
│  │  │           - Ronin (back)                                  │  │   │
│  │  │           - Cottontail (tail)                             │  │   │
│  │  │                                                           │  │   │
│  │  └───────────────────────────────────────────────────────────┘  │   │
│  │  Select traits: [+ Add Trait]                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌──────────────────────────┐  ┌──────────────────────────────────┐   │
│  │   TOP GAINERS (24h)      │  │    TOP LOSERS (24h)              │   │
│  │                          │  │                                  │   │
│  │  1. Nut Cracker   +15%   │  │  1. Cute Bunny      -12%        │   │
│  │  2. Ronin Back    +12%   │  │  2. Imp Horn        -8%         │   │
│  │  3. Little Branch +10%   │  │  3. Gerbil          -6%         │   │
│  │  4. Cottontail    +8%    │  │  4. Hot Butt        -5%         │   │
│  │  5. Serious       +7%    │  │  5. Timber          -4%         │   │
│  └──────────────────────────┘  └──────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  VOLUME BY CLASS                                     [30D ▼]    │   │
│  │  ┌───────────────────────────────────────────────────────────┐  │   │
│  │  │            [Stacked bar chart by class]                   │  │   │
│  │  └───────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component Specifications

### AxieCard Component

```tsx
interface AxieCardProps {
  axie: Axie;
  showListing?: boolean;
  onSelect?: (axie: Axie) => void;
  selected?: boolean;
  compact?: boolean;
}
```

Features:
- Displays Axie image, ID, class, purity, breed count
- Shows current listing price if listed
- Hover state reveals quick stats
- Click navigates to detail page or triggers onSelect

### AxieFilters Component

```tsx
interface FilterState {
  classes: AxieClass[];
  minPurity: number;
  maxBreedCount: number;
  priceRange: [number, number];
  parts: {
    mouth?: string;
    horn?: string;
    back?: string;
    tail?: string;
  };
  geneType: 'd' | 'r1' | 'r2' | 'any';
  listedOnly: boolean;
}
```

Features:
- Class multi-select with icons
- Purity slider (0-6)
- Breed count slider (0-7)
- Price range inputs with ETH/USD toggle
- Part dropdowns for each position
- Gene type selector
- Listed only toggle
- Clear all / Apply buttons

### PriceChart Component

```tsx
interface PriceChartProps {
  traitKey: string;
  interval: '1h' | '4h' | '1d' | '1w';
  dateRange: [Date, Date];
  showVolume?: boolean;
  showMovingAverage?: boolean;
}
```

Features:
- Candlestick or line chart option
- Volume bars overlay
- Moving average lines
- Zoom and pan
- Crosshair with tooltips
- Export to PNG

---

## State Management

### Server State (TanStack Query)

```tsx
// hooks/useAxies.ts
export function useAxies(filters: FilterState) {
  return useInfiniteQuery({
    queryKey: ['axies', filters],
    queryFn: ({ pageParam = 1 }) =>
      api.getAxies({ ...filters, page: pageParam }),
    getNextPageParam: (lastPage) => lastPage.meta.nextPage,
  });
}

// hooks/useBreeding.ts
export function useBreedingSimulation(matronId: number, sireId: number) {
  return useQuery({
    queryKey: ['breeding', matronId, sireId],
    queryFn: () => api.simulateBreeding(matronId, sireId),
    enabled: !!matronId && !!sireId,
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
3. **Query Caching** - 5-minute stale time for price data
4. **Prefetching** - Prefetch Axie details on hover
5. **Code Splitting** - Dynamic imports for chart components
