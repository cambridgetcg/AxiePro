# AxiePro Frontend Implementation Plan

**Date:** 2025-12-29
**Objective:** Build a frontend that exposes Axie trading analytics to help users understand market trends and capture value from the ecosystem.

---

## Executive Summary

This plan transforms the research from our valuation models and value extraction strategies into an actionable frontend experience. The frontend will serve three core user goals:

1. **Understand** - Visualize market trends, meta shifts, and price dynamics
2. **Discover** - Find undervalued Axies and profitable opportunities
3. **Execute** - Take action on breeding arbitrage, deal sniping, and trading signals

---

## Part 1: User Journey & Value Proposition

### Target Users

| User Type | Primary Need | Key Features |
|-----------|--------------|--------------|
| **Casual Trader** | Find deals, avoid overpaying | Deal alerts, fair value check |
| **Active Trader** | Exploit market inefficiencies | Temporal arbitrage, whale tracking |
| **Breeder** | Maximize breeding ROI | Breeding simulator, hidden value score |
| **Data Analyst** | Understand market dynamics | Analytics dashboard, data export |
| **Meta Chaser** | Stay ahead of trends | Meta shift alerts, part momentum |

### Value Extraction Mapping to UI

| Strategy (from Research) | UI Feature | Priority |
|-------------------------|------------|----------|
| Mean Reversion (Z-score) | Deal Finder, Fair Value Badge | P0 |
| Temporal Arbitrage | Time Heatmap, Best Buy/Sell Times | P1 |
| Breeding Arbitrage | Breeding Simulator + ROI Calculator | P0 |
| Whale Tracking | Whale Activity Feed | P1 |
| Meta Shift Detection | Trending Parts Dashboard | P0 |
| Distressed Seller Detection | Liquidation Alert Feed | P2 |
| Hidden Value (Recessive Genes) | Gene Explorer, HVS Score | P1 |

---

## Part 2: Information Architecture

### Site Map

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
│   ├── /analytics/whales (Whale Tracking)
│   └── /analytics/correlation (Asset Pairs)
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

## Part 3: Core Pages & Components

### 3.1 Dashboard (Home Page)

**Purpose:** At-a-glance market health + immediate opportunities

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  AxiePro    [Explorer] [Deals] [Market] [Analytics] [Breeding]  🔔  [Connect]  │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌─────────────────────────── MARKET PULSE ───────────────────────────────┐   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │   │
│  │  │ 24h Vol  │ │ Sales    │ │ Avg Floor│ │ Deals    │ │ Meta Shift│    │   │
│  │  │ 142 ETH  │ │ 5,234    │ │ $4.50    │ │ 23 Live  │ │ 🔥 Bird   │    │   │
│  │  │ ▲ 15%    │ │ ▲ 8%     │ │ ▼ 2%     │ │ ▲ 5      │ │ +18% 7d   │    │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘     │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
│  ┌────────────────── TOP DEALS NOW ──────────────────┐  ┌─── TRENDING ───┐   │
│  │                                                    │  │                │   │
│  │  🔥 Beast #12345    $3.20 → FMV $5.80  (-45%)     │  │  ▲ Ronin +15%  │   │
│  │     Z-score: -2.8   Conf: 94%   [View] [Buy]      │  │  ▲ Nut Cr +12% │   │
│  │                                                    │  │  ▲ Cotton +10% │   │
│  │  🔥 Plant #23456    $2.80 → FMV $4.20  (-33%)     │  │  ▼ Imp    -8%  │   │
│  │     Z-score: -2.3   Conf: 91%   [View] [Buy]      │  │  ▼ Gerbil -6%  │   │
│  │                                                    │  │                │   │
│  │  ⚡ Bird #34567     $8.50 → FMV $14.00 (-39%)     │  │  [View All →]  │   │
│  │     Z-score: -2.1   Conf: 89%   [View] [Buy]      │  │                │   │
│  │                                                    │  └────────────────┘   │
│  │  [View All 23 Deals →]                            │                        │
│  └────────────────────────────────────────────────────┘                        │
│                                                                                │
│  ┌────────────────── FLOOR PRICES BY CLASS ──────────────────────────────┐    │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │    │
│  │  │  Beast │ Plant │ Aqua │ Bird │ Bug │ Reptile │ Mech │ Dawn│Dusk │  │    │
│  │  │  $4.20 │ $3.80 │$4.50 │$5.20 │$3.60│  $4.00  │$6.50 │$7.20│$6.80│  │    │
│  │  │   ▼2%  │  ▲1%  │ ▼1%  │ ▲5%  │ ─   │   ▼1%   │ ▲3%  │ ▲2% │ ▲1% │  │    │
│  │  └─────────────────────────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────────────────────────┘    │
│                                                                                │
│  ┌──────────── BEST BUY TIME ────────────┐  ┌────── WHALE ACTIVITY ──────┐   │
│  │  📊 Historical best buy: 07:00-09:00   │  │  🐋 0x123...abc BUYING     │   │
│  │     UTC (Asia sleep, -8% avg discount) │  │     5 Beasts in 1 hour    │   │
│  │                                        │  │                           │   │
│  │  📊 Best sell: 15:00-18:00 UTC         │  │  🐋 0x456...def SELLING   │   │
│  │     (US active, +5% avg premium)       │  │     Liquidating Birds     │   │
│  │                                        │  │                           │   │
│  │  Current: 14:30 UTC (GOOD TO SELL)     │  │  [View Whale Dashboard →] │   │
│  └────────────────────────────────────────┘  └───────────────────────────┘   │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

**Components Needed:**
- `<MarketPulse />` - Real-time stats cards
- `<DealCard />` - Deal opportunity with Z-score, confidence
- `<TrendingParts />` - Parts with momentum
- `<FloorPriceBar />` - Class floor prices
- `<TemporalInsight />` - Best buy/sell time
- `<WhaleActivityFeed />` - Recent whale moves

**Backend Endpoints:**
- `GET /api/v1/valuation/deals/live` - Live deals
- `GET /api/v1/valuation/stats/floors` - Floor prices
- `GET /api/v1/market/stats` - Volume, sales count
- `GET /api/v1/valuation/stats/trending` - Trending parts (NEW)
- `GET /api/v1/analytics/temporal` - Time patterns (NEW)
- `GET /api/v1/analytics/whales` - Whale activity (NEW)

---

### 3.2 Deal Finder Page

**Purpose:** Surface all undervalued opportunities with actionable data

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  DEAL FINDER                                              [🔔 Set Alerts]      │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌─────────────────────────────── FILTERS ────────────────────────────────┐   │
│  │  Min Discount: [20%▼]  Z-Score: [< -2.0▼]  Class: [All▼]  Conf: [>80%▼]│   │
│  │  Price Range: [$1] - [$100]                              [Reset Filters]│   │
│  └────────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
│  Found: 23 deals                                Sort by: [Best Value ▼]       │
│                                                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐   │
│  │  🔥🔥🔥 SNIPE ALERT                                                    │   │
│  │  ┌──────────┐                                                          │   │
│  │  │ [Image]  │  Beast #12345678        Listed: $3.20                    │   │
│  │  │          │  Pure 6/6, Breed 0      Fair Value: $5.80                │   │
│  │  │          │                                                          │   │
│  │  │ ★★★★★★  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  └──────────┘  │  VALUATION BREAKDOWN                            │    │   │
│  │                │  ├─ Base (Beast Floor): $4.20                   │    │   │
│  │                │  ├─ Purity Premium: +$0.80                      │    │   │
│  │                │  ├─ Virgin Premium: +$0.50                      │    │   │
│  │                │  ├─ Part: Nut Cracker: +$0.30                   │    │   │
│  │                │  └─ Total FMV: $5.80 (95% CI: $4.90-$6.70)      │    │   │
│  │                └─────────────────────────────────────────────────┘    │   │
│  │                                                                        │   │
│  │  Discount: -45%    Z-Score: -2.8    Confidence: 94%    Deal Score: 92 │   │
│  │                                                                        │   │
│  │  Why it's a deal:                                                      │   │
│  │  • Listed 23% below class floor                                        │   │
│  │  • Virgin Axie (high breeding value)                                   │   │
│  │  • Trending part: Nut Cracker (+12% 7d)                               │   │
│  │  • Seller appears distressed (5 listings in 1 hour)                   │   │
│  │                                                                        │   │
│  │  [View Details]  [Open Marketplace]  [Add to Watchlist]               │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐   │
│  │  🔥 GOOD DEAL                                                          │   │
│  │  ... (similar layout, less prominent)                                  │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

**Key Components:**
- `<DealFilters />` - Filter by discount, Z-score, class, confidence
- `<DealDetailCard />` - Expanded deal with valuation breakdown
- `<ValuationBreakdown />` - Hedonic model decomposition
- `<DealReasons />` - AI-generated deal explanation
- `<DistressIndicator />` - Seller distress signals

**Backend Endpoints:**
- `GET /api/v1/valuation/deals/live` - Existing
- `GET /api/v1/valuation/deals/snipes` - Existing
- `GET /api/v1/valuation/{axie_id}` - Existing
- `GET /api/v1/analytics/distressed-sellers` - NEW

---

### 3.3 Analytics Dashboard

**Purpose:** Deep market intelligence for informed decision-making

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  ANALYTICS    [Overview] [Meta Trends] [Temporal] [Whales] [Correlations]      │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ═══════════════════════════ META TREND DETECTOR ═════════════════════════    │
│                                                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐   │
│  │  EMERGING META (TrendScore > 0.3)                                      │   │
│  │                                                                         │   │
│  │  Part           │ 7d Change │ Volume Δ │ TrendScore │ Signal           │   │
│  │  ────────────────────────────────────────────────────────────────────  │   │
│  │  🟢 Ronin (back)│   +18%    │   +245%  │    0.72    │ STRONG BUY       │   │
│  │  🟢 Nut Cracker │   +15%    │   +180%  │    0.65    │ BUY              │   │
│  │  🟢 Cottontail  │   +12%    │   +120%  │    0.48    │ ACCUMULATE       │   │
│  │                                                                         │   │
│  │  FADING META (TrendScore < -0.3)                                       │   │
│  │  ────────────────────────────────────────────────────────────────────  │   │
│  │  🔴 Imp (horn)  │   -12%    │   -40%   │   -0.55    │ SELL             │   │
│  │  🔴 Gerbil      │   -8%     │   -30%   │   -0.38    │ REDUCE           │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐   │
│  │  PART PRICE CHART                                    [7D] [30D] [90D]  │   │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │   │
│  │  │                                                                  │  │   │
│  │  │     📈 Multi-line chart showing selected parts over time        │  │   │
│  │  │        - EMA 7 (short-term trend)                               │  │   │
│  │  │        - EMA 30 (long-term trend)                               │  │   │
│  │  │        - Golden/Death cross indicators                          │  │   │
│  │  │                                                                  │  │   │
│  │  └──────────────────────────────────────────────────────────────────┘  │   │
│  │  Compare: [+ Ronin] [+ Nut Cracker] [+ Cottontail] [+ Add Part]       │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
│  ═══════════════════════════ TEMPORAL PATTERNS ═══════════════════════════    │
│                                                                                │
│  ┌──────────────────────────────────┐  ┌──────────────────────────────────┐  │
│  │  HOURLY PRICE HEATMAP (UTC)      │  │  DAY-OF-WEEK ANALYSIS            │  │
│  │  ┌────────────────────────────┐  │  │                                  │  │
│  │  │  Hour: Price deviation     │  │  │  Day      │ Avg Price │ Volume   │  │
│  │  │  ──────────────────────    │  │  │  ──────────────────────────────  │  │
│  │  │  00  ██░░░░  +2%           │  │  │  Sunday   │  $4.80    │ 17,007   │  │
│  │  │  04  ████░░  +5%           │  │  │  Monday   │  $4.75    │ 14,822   │  │
│  │  │  08  ░░░░░░  -8% 🟢BUY     │  │  │  Tuesday  │  $4.65    │ 16,189   │  │
│  │  │  12  ███░░░  +3%           │  │  │  Wed      │  $4.55🟢  │ 17,126   │  │
│  │  │  16  █████░  +7% 🔴SELL    │  │  │  Thursday │  $4.58    │ 16,257   │  │
│  │  │  20  ██░░░░  +1%           │  │  │  Friday   │  $4.52🟢  │ 15,719   │  │
│  │  │                            │  │  │  Saturday │  $4.72    │ 14,563   │  │
│  │  └────────────────────────────┘  │  │                                  │  │
│  │  Best Buy: 07-09 UTC (-8%)       │  │  Best Buy: Wed-Fri               │  │
│  │  Best Sell: 15-18 UTC (+7%)      │  │  Best Sell: Sun-Mon              │  │
│  └──────────────────────────────────┘  └──────────────────────────────────┘  │
│                                                                                │
│  ═══════════════════════════ WHALE INTELLIGENCE ══════════════════════════    │
│                                                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐   │
│  │  TOP WHALE MOVEMENTS (7 days)                                          │   │
│  │                                                                         │   │
│  │  Wallet            │ Action      │ Class   │ Volume  │ Signal          │   │
│  │  ────────────────────────────────────────────────────────────────────  │   │
│  │  0x094...809 🐋    │ ACCUMULATE  │ Beast   │ $5,200  │ 🟢 BULLISH     │   │
│  │  0x531...895       │ DISTRIBUTE  │ Bird    │ $3,100  │ 🔴 BEARISH     │   │
│  │  0x4a1...b2b       │ ACCUMULATE  │ Plant   │ $2,800  │ 🟢 BULLISH     │   │
│  │                                                                         │   │
│  │  Whale Consensus: 🟢 NET ACCUMULATION (+$4,900 net inflow to top 10)   │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

**Key Components:**
- `<TrendTable />` - Parts with TrendScore, signals
- `<PartPriceChart />` - Multi-line with EMA overlays
- `<TemporalHeatmap />` - Hour/day price deviation
- `<WhaleTracker />` - Whale wallet activity
- `<CrossoverIndicator />` - Golden/death cross alerts

**Backend Endpoints (NEW):**
- `GET /api/v1/analytics/meta-shifts` - TrendScore by part
- `GET /api/v1/analytics/temporal-patterns` - Hour/day patterns
- `GET /api/v1/analytics/whales` - Top whale activity
- `GET /api/v1/analytics/part-history/{part_id}` - Part price history

---

### 3.4 Breeding Arbitrage Scanner

**Purpose:** Find profitable breeding opportunities using Monte Carlo simulation

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  BREEDING ARBITRAGE SCANNER                                                    │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌────────────────────────────────── MODE ────────────────────────────────┐   │
│  │  [🧬 Simulate Pair]  [🔍 Find Best Partner]  [📊 Scan All Arbitrage]   │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
│  ═══════════════════════ PAIR SIMULATOR ══════════════════════════════════    │
│                                                                                │
│  ┌─────────────────────────┐    ♥    ┌─────────────────────────────────────┐  │
│  │      MATRON             │         │           SIRE                      │  │
│  │  ┌───────────────┐      │         │      ┌───────────────┐              │  │
│  │  │    [Image]    │      │         │      │    [Image]    │              │  │
│  │  └───────────────┘      │         │      └───────────────┘              │  │
│  │  Beast #12345678        │         │      Beast #87654321                │  │
│  │  ★★★★★★ Pure           │         │      ★★★★★☆ 5-pure               │  │
│  │  Breed: 2/7             │         │      Breed: 1/7                     │  │
│  │  Market Price: $8.50    │         │      Market Price: $6.20            │  │
│  │                         │         │                                     │  │
│  │  Hidden Value Score: 72 │         │      Hidden Value Score: 85        │  │
│  │  🟢 R1: Ronin (back)    │         │      🟢 R1: Nut Cracker (mouth)    │  │
│  │  🟡 R2: Common          │         │      🟢 R2: Cottontail (tail)      │  │
│  │                         │         │                                     │  │
│  │  [Select Axie]          │         │      [Select Axie]                  │  │
│  └─────────────────────────┘         └─────────────────────────────────────┘  │
│                                                                                │
│                        [🧬 RUN MONTE CARLO SIMULATION]                        │
│                              10,000 iterations                                 │
│                                                                                │
│  ═══════════════════════ SIMULATION RESULTS ══════════════════════════════    │
│                                                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐   │
│  │  BREEDING OPPORTUNITY SCORE (BOS): 0.42 🟢 PROFITABLE                  │   │
│  │                                                                         │   │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │   │
│  │  │  FINANCIAL SUMMARY                                                │  │   │
│  │  │  ────────────────────────────────────────────────────────────────│  │   │
│  │  │  Breeding Cost:         $12.50 (0.5 AXS + 900 SLP)               │  │   │
│  │  │  Parent Opp Cost:       $3.20 (breed slot consumption)           │  │   │
│  │  │  Total Investment:      $15.70                                   │  │   │
│  │  │                                                                   │  │   │
│  │  │  Expected Offspring:    $22.40 (95% CI: $8.50 - $45.00)          │  │   │
│  │  │  Expected Profit:       $6.70 (+43% ROI)                         │  │   │
│  │  │                                                                   │  │   │
│  │  │  Profit Probability:    68%                                      │  │   │
│  │  │  Break-even Value:      $15.70                                   │  │   │
│  │  │  Kelly Fraction:        0.18 (recommend 5% of bankroll)          │  │   │
│  │  └──────────────────────────────────────────────────────────────────┘  │   │
│  │                                                                         │   │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │   │
│  │  │  OFFSPRING VALUE DISTRIBUTION                                     │  │   │
│  │  │  ┌────────────────────────────────────────────────────────────┐  │  │   │
│  │  │  │     [Histogram of offspring values from Monte Carlo]       │  │  │   │
│  │  │  │                                                            │  │  │   │
│  │  │  │  █                                                         │  │  │   │
│  │  │  │  █ █                                                       │  │  │   │
│  │  │  │  █ █ █ █                                                   │  │  │   │
│  │  │  │  █ █ █ █ █ █ █                                             │  │  │   │
│  │  │  │  █ █ █ █ █ █ █ █ █ █ █ █                                   │  │  │   │
│  │  │  │  ─────────────────────────────────────────────────────     │  │  │   │
│  │  │  │  $5   $10   $15   $20   $25   $30   $40   $50+              │  │  │   │
│  │  │  │       ▲ Break-even    ▲ Expected                           │  │  │   │
│  │  │  └────────────────────────────────────────────────────────────┘  │  │   │
│  │  └──────────────────────────────────────────────────────────────────┘  │   │
│  │                                                                         │   │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │   │
│  │  │  TOP OUTCOME SCENARIOS                                            │  │   │
│  │  │  ────────────────────────────────────────────────────────────────│  │   │
│  │  │  🥇 Best Case (5%):   6-pure Beast w/ Ronin + Nut Cracker        │  │   │
│  │  │     Estimated Value: $45.00   Probability: 2.3%                  │  │   │
│  │  │                                                                   │  │   │
│  │  │  🥈 Good Case (25%):  5-pure Beast w/ one premium part           │  │   │
│  │  │     Estimated Value: $18.00   Probability: 22.5%                 │  │   │
│  │  │                                                                   │  │   │
│  │  │  📊 Median Case:      4-pure Beast, standard parts               │  │   │
│  │  │     Estimated Value: $12.50   Probability: 45.2%                 │  │   │
│  │  │                                                                   │  │   │
│  │  │  ⚠️ Worst Case (5%):  Low purity, no premium parts               │  │   │
│  │  │     Estimated Value: $5.50    Probability: 8.0%                  │  │   │
│  │  └──────────────────────────────────────────────────────────────────┘  │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
│  ═══════════════════════ ARBITRAGE SCANNER ═══════════════════════════════    │
│                                                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐   │
│  │  TOP BREEDING ARBITRAGE OPPORTUNITIES (from your inventory)            │   │
│  │                                                                         │   │
│  │  Pair                    │ BOS  │ Exp ROI │ P(profit) │ Kelly          │   │
│  │  ────────────────────────────────────────────────────────────────────  │   │
│  │  #12345 × #67890         │ 0.52 │  +58%   │   72%     │ 0.22           │   │
│  │  #23456 × #78901         │ 0.45 │  +43%   │   68%     │ 0.18           │   │
│  │  #34567 × #89012         │ 0.38 │  +31%   │   64%     │ 0.14           │   │
│  │                                                                         │   │
│  │  [Scan My Inventory]  [Scan Marketplace]  [Export Analysis]            │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

**Key Components:**
- `<BreedingPairSelector />` - Select matron/sire with gene preview
- `<HiddenValueScore />` - Display recessive gene value
- `<MonteCarloResults />` - Simulation output visualization
- `<OffspringDistribution />` - Histogram of outcomes
- `<BreedingROICard />` - Financial summary
- `<ArbitrageScanner />` - Table of top opportunities

**Backend Endpoints:**
- `POST /api/v1/breeding/simulate` - Existing (enhanced)
- `POST /api/v1/breeding/monte-carlo` - NEW (10K simulations)
- `GET /api/v1/breeding/arbitrage-scan` - NEW (scan inventory)
- `GET /api/v1/breeding/hidden-value/{axie_id}` - NEW (HVS calculation)

---

### 3.5 Axie Detail Page (Enhanced)

**Purpose:** Complete analysis of a single Axie for trading/breeding decisions

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  ← Back                                     [Share] [Track] [Use in Breeding]  │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌───────────────────┐  ┌────────────────────────────────────────────────────┐│
│  │                   │  │  BEAST #12345678           "Beastie McBeastface"   ││
│  │    [Axie Image]   │  │                                                    ││
│  │                   │  │  ┌─────────────────────────────────────────────┐   ││
│  │                   │  │  │  VALUATION SUMMARY                          │   ││
│  │                   │  │  │                                             │   ││
│  └───────────────────┘  │  │  Listed Price:    $8.50                     │   ││
│                         │  │  Fair Value:      $7.20 (95% CI: $6.10-$8.30)│  ││
│                         │  │  Status:          ⚠️ SLIGHTLY OVERPRICED    │   ││
│                         │  │  Z-Score:         +0.8                      │   ││
│                         │  │  Recommendation:  WAIT (or offer $7.00)     │   ││
│                         │  │                                             │   ││
│                         │  │  [View on Marketplace]                      │   ││
│                         │  └─────────────────────────────────────────────┘   ││
│                         │                                                    ││
│                         │  Stats: HP 31 │ SPD 35 │ SKL 31 │ MRL 43          ││
│                         │  Purity: ★★★★★★ (6/6)   Breed: 2/7               ││
│                         │  Owner: 0x1234...abcd                             ││
│                         └────────────────────────────────────────────────────┘│
│                                                                                │
│  ┌─────────────────────── VALUATION BREAKDOWN ────────────────────────────┐   │
│  │                                                                         │   │
│  │  Component             │ Value   │ Contribution │ Notes                 │   │
│  │  ────────────────────────────────────────────────────────────────────  │   │
│  │  Beast Floor           │ $4.20   │ Base         │ Class baseline        │   │
│  │  Purity (6/6)          │ +$0.80  │ +19%         │ Above average         │   │
│  │  Breed Count (2/7)     │ +$0.40  │ +10%         │ Moderate premium      │   │
│  │  Part: Nut Cracker     │ +$0.60  │ +14%         │ 🔥 Trending +12%      │   │
│  │  Part: Ronin Back      │ +$0.70  │ +17%         │ 🔥 Trending +18%      │   │
│  │  Part: Cottontail      │ +$0.30  │ +7%          │ Stable                │   │
│  │  Other Parts           │ +$0.20  │ +5%          │ Common                │   │
│  │  ────────────────────────────────────────────────────────────────────  │   │
│  │  TOTAL FMV             │ $7.20   │              │ Confidence: 91%       │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
│  ┌───────────────────── GENE ANALYSIS ────────────────────────────────────┐   │
│  │  ┌─────────┬────────────────┬────────────────┬────────────────┐        │   │
│  │  │  Part   │   Dominant     │   Recessive 1  │   Recessive 2  │        │   │
│  │  ├─────────┼────────────────┼────────────────┼────────────────┤        │   │
│  │  │  Eyes   │ 🟡 Chubby      │ 🟡 Chubby      │ 🟢 Papi        │        │   │
│  │  │  Ears   │ 🟡 Nut Cracker │ 🟡 Nut Cracker │ 🔵 Puppy       │        │   │
│  │  │  Mouth  │ 🟡 Nut Cracker │ 🔴 Axie Kiss   │ 🟡 Nut Cracker │        │   │
│  │  │  Horn   │ 🟡 Little Branch│ 🔴 Imp        │ 🟡 Little Branch│        │   │
│  │  │  Back   │ 🟡 Ronin       │ 🟡 Ronin       │ 🔵 Hero        │        │   │
│  │  │  Tail   │ 🟡 Cottontail  │ 🟡 Hare        │ 🟡 Cottontail  │        │   │
│  │  └─────────┴────────────────┴────────────────┴────────────────┘        │   │
│  │                                                                         │   │
│  │  Gene Purity: 14/18 (78%)                                              │   │
│  │  Hidden Value Score: 72/100                                            │   │
│  │  Notable Recessives: R1 Ronin (back) - $0.70 premium if dominant       │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
│  ┌──────────── PRICE HISTORY ────────────┐  ┌──────── BREEDING VALUE ──────┐ │
│  │  ┌─────────────────────────────────┐  │  │                              │ │
│  │  │  [Candlestick chart]            │  │  │  Breed Slots: 5 remaining    │ │
│  │  │                                 │  │  │  Slot Value: $1.60 each      │ │
│  │  │  Last Sale: $7.50 (Dec 15)      │  │  │  Total Breed Value: $8.00    │ │
│  │  │  Avg (30d): $7.20               │  │  │                              │ │
│  │  │  High (30d): $9.00              │  │  │  Best Partner Match: 12     │ │
│  │  │  Low (30d): $6.50               │  │  │  Avg BOS: 0.35               │ │
│  │  └─────────────────────────────────┘  │  │                              │ │
│  └───────────────────────────────────────┘  │  [Find Best Partner →]       │ │
│                                              └──────────────────────────────┘ │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

**Key Components:**
- `<ValuationSummary />` - FMV, Z-score, recommendation
- `<ValuationBreakdown />` - Hedonic decomposition
- `<GeneTable />` - Full gene display with value indicators
- `<HiddenValueScore />` - Recessive gene value
- `<PriceHistoryChart />` - Historical prices
- `<BreedingValueCard />` - Breeding potential summary

**Backend Endpoints:**
- `GET /api/v1/valuation/{axie_id}` - Existing (enhanced output)
- `GET /api/v1/axies/{axie_id}/genes` - Existing
- `GET /api/v1/breeding/best-pairs/{axie_id}` - Existing

---

## Part 4: New Backend Endpoints Required

### Analytics Endpoints

```typescript
// Meta Shift Detection
GET /api/v1/analytics/meta-shifts
Response: {
  emerging: [{ part, trend_score, price_change_7d, volume_change }],
  fading: [{ part, trend_score, price_change_7d, volume_change }],
  stable: [{ part, trend_score }]
}

// Temporal Patterns
GET /api/v1/analytics/temporal-patterns
Response: {
  hourly: [{ hour, avg_price, price_deviation, volume, recommendation }],
  daily: [{ day, avg_price, volume, recommendation }],
  best_buy_time: { hour_utc, expected_discount },
  best_sell_time: { hour_utc, expected_premium }
}

// Whale Tracking
GET /api/v1/analytics/whales
Query: ?days=7&min_volume=1000
Response: {
  whales: [{
    address, label, action, classes, volume_usd,
    net_position_change, signal
  }],
  consensus: { direction, net_flow }
}

// Distressed Seller Detection
GET /api/v1/analytics/distressed-sellers
Response: {
  distressed: [{
    seller, listing_count, price_cuts, below_floor_count,
    distress_score, listings: [{ axie_id, price, discount }]
  }]
}

// Part Price History
GET /api/v1/analytics/part-history/{part_id}
Query: ?days=30&interval=1d
Response: {
  part_id, part_name,
  history: [{ date, floor, avg, volume }],
  ema_7, ema_30, trend_score
}
```

### Breeding Endpoints

```typescript
// Enhanced Monte Carlo Simulation
POST /api/v1/breeding/monte-carlo
Body: { matron_id, sire_id, simulations: 10000 }
Response: {
  expected_value, std_dev,
  profit_probability, break_even_value,
  percentiles: { p5, p25, p50, p75, p95 },
  bos: number, kelly_fraction: number,
  top_outcomes: [{ description, value, probability }],
  distribution: [{ value_bin, count }]
}

// Hidden Value Score
GET /api/v1/breeding/hidden-value/{axie_id}
Response: {
  hvs: number,
  recessive_values: [{
    part, gene_type, part_name, dominant_value, recessive_value,
    value_delta, inheritance_probability
  }],
  total_hidden_value: number
}

// Arbitrage Scanner
GET /api/v1/breeding/arbitrage-scan
Query: ?wallet_address=0x...&min_bos=0.2
Response: {
  opportunities: [{
    matron_id, sire_id, bos, expected_roi,
    profit_probability, kelly_fraction,
    reason: string
  }]
}
```

---

## Part 5: Component Library

### Core Components

| Component | Purpose | Props |
|-----------|---------|-------|
| `<DealCard />` | Display deal opportunity | axie, fmv, discount, z_score, confidence |
| `<ValuationBadge />` | Quick FMV indicator | value, listed_price, status |
| `<TrendIndicator />` | Part trend arrow | trend_score, change_7d |
| `<ZScoreGauge />` | Visual Z-score | z_score, threshold |
| `<ConfidenceBar />` | Confidence level | confidence_pct |
| `<PriceChart />` | TradingView-style chart | data, emas, interval |
| `<GeneTable />` | Gene breakdown | genes, show_values |
| `<HVSBadge />` | Hidden value score | hvs, notable_recessives |
| `<MonteCarloChart />` | Distribution histogram | distribution_data |
| `<BOSGauge />` | Breeding opportunity score | bos, components |
| `<TemporalHeatmap />` | Hour/day price map | hourly_data |
| `<WhaleAlert />` | Whale activity notification | whale, action, volume |

### Shared Hooks

```typescript
// Data fetching hooks
useDeals(filters) → { deals, isLoading, refetch }
useValuation(axieId) → { valuation, isLoading }
useMetaShifts() → { emerging, fading, stable }
useTemporalPatterns() → { hourly, daily, recommendations }
useWhaleActivity(days) → { whales, consensus }
useBreedingSimulation(matronId, sireId) → { results, isLoading }
useHiddenValue(axieId) → { hvs, recessives }
useArbitrageScan(walletAddress) → { opportunities }
usePartHistory(partId, days) → { history, ema7, ema30, trendScore }
```

---

## Part 6: Implementation Phases

### Phase 1: Core Value (Weeks 1-3)

**Goal:** Deliver immediate value with deal detection

| Task | Component | Backend | Priority |
|------|-----------|---------|----------|
| Deal Finder Page | `<DealCard />`, `<ValuationBreakdown />` | Existing endpoints | P0 |
| Enhanced Axie Detail | `<ValuationSummary />`, `<GeneTable />` | Existing + minor changes | P0 |
| Dashboard Overview | `<MarketPulse />`, `<TrendingParts />` | Existing endpoints | P0 |

### Phase 2: Analytics (Weeks 4-6)

**Goal:** Market intelligence for informed decisions

| Task | Component | Backend | Priority |
|------|-----------|---------|----------|
| Meta Trends Page | `<TrendTable />`, `<PartPriceChart />` | NEW: meta-shifts, part-history | P0 |
| Temporal Patterns | `<TemporalHeatmap />` | NEW: temporal-patterns | P1 |
| Whale Tracking | `<WhaleTracker />`, `<WhaleAlert />` | NEW: whales | P1 |

### Phase 3: Breeding (Weeks 7-9)

**Goal:** Breeding arbitrage discovery

| Task | Component | Backend | Priority |
|------|-----------|---------|----------|
| Monte Carlo Simulator | `<MonteCarloChart />`, `<BOSGauge />` | NEW: monte-carlo | P0 |
| Hidden Value Score | `<HVSBadge />` | NEW: hidden-value | P1 |
| Arbitrage Scanner | `<ArbitrageScanner />` | NEW: arbitrage-scan | P1 |

### Phase 4: Polish & Alerts (Weeks 10-12)

**Goal:** Real-time notifications and UX refinement

| Task | Component | Backend | Priority |
|------|-----------|---------|----------|
| Alert System | `<AlertConfig />` | Existing Lambda integration | P1 |
| Wallet Integration | Connect wallet, track portfolio | NEW: wallet endpoints | P2 |
| Mobile Optimization | Responsive layouts | N/A | P1 |

---

## Part 7: Technical Architecture

### Frontend Stack

```
Next.js 14 (App Router)
├── React 19
├── TypeScript 5
├── Tailwind CSS 4
├── TanStack Query 5 (server state)
├── Zustand (client state)
├── Recharts + TradingView Lightweight Charts
├── Radix UI (accessible components)
└── Framer Motion (animations)
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                        │
│                                                                              │
│   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐        │
│   │   Pages         │    │   Components    │    │   Hooks         │        │
│   │   /deals        │───▶│   <DealCard/>   │◀───│   useDeals()    │        │
│   │   /analytics    │    │   <TrendTable/> │    │   useMetaShifts()│       │
│   │   /breeding     │    │   <BOSGauge/>   │    │   useBreeding() │        │
│   └─────────────────┘    └─────────────────┘    └────────┬────────┘        │
│                                                          │                  │
│                                    TanStack Query Cache  │                  │
│                                    ┌─────────────────────┴───┐              │
│                                    │   queryClient           │              │
│                                    │   - deals: 30s stale    │              │
│                                    │   - valuation: 60s      │              │
│                                    │   - analytics: 5min     │              │
│                                    └─────────────────────────┘              │
└──────────────────────────────────────────────┬──────────────────────────────┘
                                               │
                                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              API CLIENT (lib/api/)                            │
│                                                                               │
│   baseURL: process.env.NEXT_PUBLIC_API_URL                                   │
│   ┌───────────────────────────────────────────────────────────────────────┐  │
│   │   GET  /api/v1/valuation/deals/live     → deals[]                     │  │
│   │   GET  /api/v1/analytics/meta-shifts    → { emerging, fading }        │  │
│   │   POST /api/v1/breeding/monte-carlo     → { distribution, bos }       │  │
│   └───────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────┬───────────────────────────────┘
                                               │
                                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                            BACKEND (FastAPI on App Runner)                    │
│                                                                               │
│   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│   │   API Routes    │    │   Services      │    │   Database      │         │
│   │   /valuation    │───▶│   HedonicModel  │───▶│   RDS Postgres  │         │
│   │   /analytics    │    │   AnalyticsSvc  │    │   ElastiCache   │         │
│   │   /breeding     │    │   BreedingSim   │    │                 │         │
│   └─────────────────┘    └─────────────────┘    └─────────────────┘         │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Caching Strategy

| Data Type | Stale Time | Cache Time | Refetch |
|-----------|------------|------------|---------|
| Live Deals | 30 seconds | 1 minute | Focus |
| Valuation | 1 minute | 5 minutes | Manual |
| Floor Prices | 1 minute | 5 minutes | Interval |
| Analytics | 5 minutes | 30 minutes | Manual |
| Part History | 15 minutes | 1 hour | Manual |
| Monte Carlo | N/A | 10 minutes | Manual |

---

## Part 8: Success Metrics

### User Engagement

| Metric | Target | Measurement |
|--------|--------|-------------|
| Daily Active Users | 500+ | Analytics |
| Deals Viewed / DAU | 10+ | Event tracking |
| Breeding Simulations / DAU | 3+ | Event tracking |
| Return Rate (7d) | 40%+ | Analytics |

### Value Delivered

| Metric | Target | Measurement |
|--------|--------|-------------|
| Deals Acted On | 20%+ of viewed | Marketplace referral clicks |
| Avg Discount Captured | 25%+ | User surveys |
| Breeding ROI | +30%+ | User feedback |

### Technical

| Metric | Target | Measurement |
|--------|--------|-------------|
| Page Load Time | < 2 seconds | Lighthouse |
| API Response Time | < 500ms (p95) | CloudWatch |
| Uptime | 99.5%+ | Monitoring |

---

## Summary

This frontend implementation plan transforms the research from our valuation models and value extraction strategies into a user-friendly interface that:

1. **Surfaces deals** using hedonic pricing and Z-score analysis
2. **Reveals market trends** through meta shift detection and temporal patterns
3. **Enables breeding arbitrage** with Monte Carlo simulation and hidden value scoring
4. **Tracks whale activity** for institutional signal detection
5. **Provides actionable recommendations** for buy/sell/breed decisions

The phased approach prioritizes immediate value delivery (deal detection) while building toward comprehensive market intelligence and breeding optimization tools.
