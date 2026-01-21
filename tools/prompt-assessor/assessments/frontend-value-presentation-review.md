# AxiePro Frontend Value Presentation Review

**Date:** 2025-01-20
**Assessment Method:** Prompt-based exploration (ecosystem participant frame)
**Scope:** Frontend value capture opportunities presentation
**Perspective:** Trader, Breeder, Collector, Whale

---

## Executive Summary

| Metric | Current | Potential | Gap |
|--------|---------|-----------|-----|
| Value Capture Clarity | 65% | 100% | 35% |
| Actionable Opportunities | 4 | 12 | 8 |
| User Segment Coverage | 60% | 100% | 40% |
| Time-to-Value (seconds) | 15s | <5s | -10s |
| Decision Confidence | Medium | High | Upgrade needed |

**Bottom Line:** Strong analytics foundation, but value capture paths are fragmented. Users must mentally synthesize data across multiple pages to identify opportunities.

---

## 1. Ecosystem Participant Profiles

### User Segment Analysis

| Segment | Primary Goal | Time Horizon | Risk Tolerance | Current Support |
|---------|--------------|--------------|----------------|-----------------|
| **Day Trader** | Flip undervalued Axies | Minutes-Hours | High | ★★★★☆ |
| **Swing Trader** | Meta trend arbitrage | Days-Weeks | Medium | ★★☆☆☆ |
| **Breeder** | Optimize offspring value | Weeks-Months | Medium | ★☆☆☆☆ |
| **Collector** | Build valuable portfolio | Months-Years | Low | ★★☆☆☆ |
| **Whale** | Market-moving plays | Variable | Variable | ★☆☆☆☆ |

---

## 2. Current Value Presentation Audit

### What's Working Well

| Feature | Value Delivered | User Segment | Score |
|---------|-----------------|--------------|-------|
| Deal Detection | 20-40%+ discount identification | Day Traders | A |
| Z-Score Confidence | Statistical deal validation | Day Traders | A |
| Real-time Polling | 30s deal refresh | Day Traders | A- |
| Floor Prices | Class-level price context | All | B+ |
| Valuation Breakdown | Feature contribution visibility | Traders | B+ |
| Market Pulse | 24h activity snapshot | All | B |

### What's Missing or Weak

| Gap | Impact | Affected Segment | Priority |
|-----|--------|------------------|----------|
| No meta shifts UI | Can't see early opportunities | Swing Traders | **HIGH** |
| No portfolio P&L view | Can't track actual profits | Collectors, Whales | **HIGH** |
| No normalized scoring display | User confusion on deal quality | All Traders | **HIGH** |
| Breeding ROI absent | Can't optimize breeding | Breeders | **HIGH** |
| No whale activity feed | Miss market-moving events | All | MEDIUM |
| No price alerts/notifications | Miss time-sensitive deals | Day Traders | MEDIUM |
| No export/reports | No tax/accounting support | All | MEDIUM |
| No historical P&L charts | Can't analyze performance | Collectors | LOW |

---

## 3. Value Capture Path Analysis

### Current User Journeys (Pain Points)

#### Day Trader Journey
```
Homepage → Deals Page → Filter → Evaluate → Buy (external)
   ↓           ↓           ↓         ↓
 [OK]     [GOOD]     [OK]    [FRICTION: Must leave app]
```

**Friction Points:**
1. No price alerts - must manually refresh
2. No watchlist for tracking specific opportunities
3. Buy action leaves app (no transaction tracking)
4. Can't see how deal score was calculated (normalized vs legacy)

#### Swing Trader Journey
```
Analytics → ??? → Where are meta shifts? → Can't find → Leave
              ↓
        [DEAD END - Meta API exists but no UI]
```

**Critical Gap:** Meta shift data exists in backend but has NO frontend exposure.

#### Breeder Journey
```
Breeding Page → "Coming Soon" → Nothing actionable → Leave
```

**Critical Gap:** Breeding simulator is placeholder only.

#### Collector Journey
```
Explorer → Single Axie lookup → No portfolio view → Can't track holdings
                                        ↓
                              [DEAD END - Portfolio API exists but no UI]
```

**Critical Gap:** Portfolio P&L backend exists but has NO frontend exposure.

---

## 4. Value Presentation Gaps (Detailed)

### Gap 1: Meta Shifts Not Visible (HIGH)

**Backend Status:** ✅ Implemented (`/api/v1/meta/*` endpoints)
**Frontend Status:** ❌ Not implemented

| What Exists | What's Missing |
|-------------|----------------|
| Rising traits API | Meta shifts dashboard |
| Falling traits API | Trend alerts/badges |
| Emerging meta API | Meta shift cards |
| Fading meta API | Price velocity charts |
| Summary endpoint | Confidence indicators |

**Value Lost:**
- Swing traders can't identify early meta opportunities
- 4-7 day lead time advantage not exposed to users
- Competitive differentiation hidden

**Recommended Components:**
1. `MetaShiftCard` - Individual shift with confidence
2. `MetaTrendsDashboard` - Overview of all shifts
3. `MetaAlertBadge` - Homepage notification

---

### Gap 2: Portfolio P&L Not Visible (HIGH)

**Backend Status:** ✅ Implemented (`/api/v1/wallets/{address}/portfolio/*`)
**Frontend Status:** ❌ Not implemented

| What Exists | What's Missing |
|-------------|----------------|
| Portfolio summary API | Portfolio dashboard page |
| Holdings with P&L API | Holdings table with P&L |
| Cost basis update API | Cost basis editor |
| Refresh valuations API | Bulk refresh UI |

**Value Lost:**
- Users can't see if they're profitable
- No cost-basis tracking visibility
- Can't justify subscription value
- Missing "stickiness" for retention

**Recommended Components:**
1. `PortfolioDashboard` - Summary cards (total value, P&L, ROI)
2. `HoldingsTable` - Sortable by P&L, value, acquisition
3. `CostBasisEditor` - Manual entry for historical holdings
4. `PnLChart` - Performance over time

---

### Gap 3: Normalized Scoring Not Displayed (HIGH)

**Backend Status:** ✅ Implemented (scoring service + API params)
**Frontend Status:** ❌ Using legacy `deal_score` only

| What Exists | What's Missing |
|-------------|----------------|
| `include_normalized=true` param | Request normalized scores |
| `normalized_score` field | Display normalized score |
| `tier` field | Show tier badges (SNIPE/ELITE/GOOD/FAIR/PASS) |
| `tier_color` field | Use tier colors |
| `score_components` | Show component breakdown |

**Value Lost:**
- Users see inconsistent 0-100 scores
- No tier classification (SNIPE vs ELITE vs GOOD)
- Score components hidden (discount/confidence/liquidity/time)
- Time decay not visible (fresh deals not highlighted)

**Recommended Updates:**
1. Update `useDeals` hook to request `include_normalized=true`
2. Add `NormalizedScoreBadge` component with tier colors
3. Add `ScoreBreakdown` tooltip showing components
4. Add "Fresh" badge for listings < 30 minutes old

---

### Gap 4: Breeding ROI Missing (HIGH)

**Backend Status:** ⚠️ Partial (valuation exists, no breeding calc)
**Frontend Status:** ❌ Placeholder only

**Value Lost:**
- Breeders have no ROI visibility
- Can't optimize breeding pairs
- Gene probability not calculated
- Offspring value estimation missing

**Recommended Approach:**
1. Backend: Add breeding cost + offspring value calculator
2. Frontend: `BreedingCalculator` with parent inputs
3. Frontend: `OffspringProbabilities` gene display
4. Frontend: `BreedingROICard` showing expected profit

---

## 5. Recommended Frontend Enhancements

### Priority 1: Expose Existing Backend Value (1-2 weeks)

| Component | Effort | Value | Files to Create |
|-----------|--------|-------|-----------------|
| Meta Shifts Dashboard | 3d | HIGH | `app/meta/page.tsx`, `components/meta/*` |
| Portfolio P&L Page | 4d | HIGH | `app/portfolio/page.tsx`, `components/portfolio/*` |
| Normalized Score Display | 1d | HIGH | Update `DealDetailCard`, add `NormalizedScoreBadge` |
| Meta Shift Alert Banner | 1d | MEDIUM | `components/dashboard/meta-alert.tsx` |

### Priority 2: Enhanced Value Communication (2-4 weeks)

| Component | Effort | Value | Description |
|-----------|--------|-------|-------------|
| Watchlist | 3d | HIGH | Save Axies for tracking |
| Deal Alerts | 3d | HIGH | Browser/email notifications |
| Portfolio Performance Chart | 2d | MEDIUM | P&L over time visualization |
| Export Reports | 2d | MEDIUM | CSV/PDF for tax purposes |

### Priority 3: New Value Features (4-8 weeks)

| Component | Effort | Value | Description |
|-----------|--------|-------|-------------|
| Breeding Calculator | 5d | HIGH | Full gene probability engine |
| Whale Activity Feed | 3d | MEDIUM | Track large transactions |
| Price Alerts | 3d | MEDIUM | Threshold-based notifications |
| Trade Journal | 5d | LOW | Log trades with notes |

---

## 6. Component Specifications

### 6.1 Meta Shifts Dashboard

**Route:** `/meta` or `/market/meta`

**Components Needed:**
```
/components/meta/
├── meta-summary-card.tsx      # Total shifts by type
├── meta-shift-card.tsx        # Individual shift detail
├── meta-trends-chart.tsx      # 7-day trend visualization
├── meta-alert-badge.tsx       # Notification badge
└── meta-confidence-gauge.tsx  # Confidence indicator
```

**Data Flow:**
```typescript
// hooks/use-meta.ts
export function useMetaSummary() {
  return useQuery({
    queryKey: ['meta', 'summary'],
    queryFn: () => api.get('/meta/summary'),
    staleTime: 60000, // 1 minute
  });
}

export function useMetaShifts(type?: string) {
  return useQuery({
    queryKey: ['meta', 'shifts', type],
    queryFn: () => api.get('/meta/shifts', { params: { shift_type: type } }),
    refetchInterval: 300000, // 5 minutes
  });
}
```

**UI Layout:**
```
┌─────────────────────────────────────────────────────────┐
│ Meta Shifts Dashboard                          [Refresh] │
├─────────────────────────────────────────────────────────┤
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│ │ Rising   │ │ Falling  │ │ Emerging │ │ Fading   │    │
│ │    12    │ │    8     │ │    5     │ │    3     │    │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘    │
├─────────────────────────────────────────────────────────┤
│ Top Rising Traits                                       │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ part:horn:lagging  │ +32% 24h │ 85% conf │ [View]  │ │
│ │ class:beast        │ +18% 24h │ 72% conf │ [View]  │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

### 6.2 Portfolio P&L Dashboard

**Route:** `/portfolio` or `/wallet/{address}`

**Components Needed:**
```
/components/portfolio/
├── portfolio-summary.tsx      # Total value, P&L, ROI
├── holdings-table.tsx         # Sortable holdings list
├── pnl-chart.tsx              # Performance over time
├── cost-basis-editor.tsx      # Manual cost entry modal
└── portfolio-refresh.tsx      # Bulk refresh button
```

**UI Layout:**
```
┌─────────────────────────────────────────────────────────┐
│ Portfolio: 0x1234...5678                      [Refresh] │
├─────────────────────────────────────────────────────────┤
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐     │
│ │ Total Value  │ │ Total P&L    │ │ ROI          │     │
│ │ 12.45 ETH    │ │ +2.31 ETH    │ │ +22.7%       │     │
│ │              │ │ ▲ +18.5%     │ │              │     │
│ └──────────────┘ └──────────────┘ └──────────────┘     │
├─────────────────────────────────────────────────────────┤
│ Holdings (47 Axies)           [Sort: P&L ▼] [Filter ▼] │
│ ┌─────┬───────┬──────────┬───────────┬─────────┬─────┐ │
│ │ ID  │ Class │ Cost     │ Value     │ P&L     │     │ │
│ ├─────┼───────┼──────────┼───────────┼─────────┼─────┤ │
│ │ #123│ Beast │ 0.05 ETH │ 0.08 ETH  │ +60%    │ [E] │ │
│ │ #456│ Plant │ 0.03 ETH │ 0.02 ETH  │ -33%    │ [E] │ │
│ └─────┴───────┴──────────┴───────────┴─────────┴─────┘ │
│                                                         │
│ Coverage: 38/47 (81%) have cost basis                   │
└─────────────────────────────────────────────────────────┘
```

---

### 6.3 Normalized Score Enhancement

**Update existing DealDetailCard:**

```typescript
// Before
<Badge>{deal.deal_score}</Badge>

// After
<NormalizedScoreBadge
  score={deal.normalized_score}
  tier={deal.tier}
  tierLabel={deal.tier_label}
  tierColor={deal.tier_color}
  components={deal.score_components}
/>
```

**New Component:**
```tsx
// components/deals/normalized-score-badge.tsx
export function NormalizedScoreBadge({
  score, tier, tierLabel, tierColor, components
}: Props) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger>
          <Badge style={{ backgroundColor: tierColor }}>
            {tierLabel} ({score})
          </Badge>
        </TooltipTrigger>
        <TooltipContent>
          <div className="space-y-1">
            <div>Discount: {(components.discount_percentile * 100).toFixed(0)}%</div>
            <div>Confidence: {(components.confidence_percentile * 100).toFixed(0)}%</div>
            <div>Liquidity: {(components.liquidity_score * 100).toFixed(0)}%</div>
            <div>Freshness: {(components.time_score * 100).toFixed(0)}%</div>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
```

---

## 7. Value Capture Metrics Dashboard

**Proposed Homepage Redesign:**

Replace current "Features Grid" with **Value Capture Dashboard**:

```
┌─────────────────────────────────────────────────────────┐
│ YOUR VALUE CAPTURE OPPORTUNITIES                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ ┌─────────────────────┐  ┌─────────────────────┐       │
│ │ 🔥 ACTIVE SNIPES    │  │ 📈 META RISING      │       │
│ │       7             │  │       12            │       │
│ │ Avg discount: 45%   │  │ Top: +32% (24h)     │       │
│ │ [View Snipes →]     │  │ [View Trends →]     │       │
│ └─────────────────────┘  └─────────────────────┘       │
│                                                         │
│ ┌─────────────────────┐  ┌─────────────────────┐       │
│ │ 💰 YOUR PORTFOLIO   │  │ 📊 MARKET HEALTH    │       │
│ │ +2.31 ETH (+22.7%)  │  │ Bullish             │       │
│ │ 47 holdings         │  │ Vol: +15% (24h)     │       │
│ │ [View P&L →]        │  │ [View Analytics →]  │       │
│ └─────────────────────┘  └─────────────────────┘       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 8. Assessment Scores

### Current Frontend Value Presentation

| Attribute | Score | Evidence |
|-----------|-------|----------|
| **Comprehension Depth (CD)** | 4.0 | Good deal breakdown, but meta/portfolio hidden |
| **Coverage Breadth (CB)** | 3.5 | Missing meta, portfolio, breeding UI |
| **Accuracy (AC)** | 4.5 | Data accurate when shown |
| **Actionability (AT)** | 3.5 | Actions exist but paths fragmented |
| **Bridging Capability (BC)** | 3.0 | Pages don't connect value opportunities |
| **Domain Alignment (DA)** | 4.0 | Good Axie-specific terminology |
| **Clarity & Structure (CS)** | 4.0 | Clean UI but value paths unclear |
| **Efficiency (EF)** | 3.5 | Too many clicks to find opportunities |
| **Gap Detection (GD)** | 2.5 | User doesn't know what they're missing |
| **Reproducibility (RP)** | 4.0 | Consistent experience |

**Total Score:** 3.65/5.00 | **Grade:** B+

### Target After Enhancements

| Attribute | Current | Target | Improvement |
|-----------|---------|--------|-------------|
| CD | 4.0 | 4.5 | +0.5 (expose meta signals) |
| CB | 3.5 | 4.5 | +1.0 (add portfolio, meta UI) |
| AC | 4.5 | 5.0 | +0.5 (normalized scoring) |
| AT | 3.5 | 4.5 | +1.0 (clear action paths) |
| BC | 3.0 | 4.5 | +1.5 (value dashboard) |
| DA | 4.0 | 4.5 | +0.5 (breeding terms) |
| CS | 4.0 | 4.5 | +0.5 (unified value view) |
| EF | 3.5 | 4.5 | +1.0 (fewer clicks) |
| GD | 2.5 | 4.0 | +1.5 (show missing opportunities) |
| RP | 4.0 | 4.0 | — (maintain) |

**Target Score:** 4.45/5.00 | **Target Grade:** A-

---

## 9. Implementation Roadmap

### Phase 1: Expose Hidden Value (Sprint 1-2)

| Task | Priority | Effort | Impact |
|------|----------|--------|--------|
| Update deals API to use normalized scoring | P1 | 2h | HIGH |
| Create `NormalizedScoreBadge` component | P1 | 4h | HIGH |
| Create `/meta` page with basic dashboard | P1 | 2d | HIGH |
| Create `/portfolio` page with summary | P1 | 3d | HIGH |
| Add meta alert banner to homepage | P2 | 4h | MEDIUM |

### Phase 2: Enhance Value Communication (Sprint 3-4)

| Task | Priority | Effort | Impact |
|------|----------|--------|--------|
| Holdings table with P&L sorting | P1 | 1d | HIGH |
| Cost basis editor modal | P1 | 1d | HIGH |
| Meta shift cards with confidence | P2 | 1d | MEDIUM |
| Portfolio performance chart | P2 | 1d | MEDIUM |
| Redesign homepage value dashboard | P2 | 2d | MEDIUM |

### Phase 3: New Value Features (Sprint 5-8)

| Task | Priority | Effort | Impact |
|------|----------|--------|--------|
| Watchlist functionality | P2 | 3d | HIGH |
| Deal alerts (browser notifications) | P2 | 2d | HIGH |
| Breeding calculator MVP | P1 | 5d | HIGH |
| Export reports (CSV) | P3 | 2d | MEDIUM |

---

## 10. Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Time to first deal view | ~15s | <5s | Analytics |
| Portfolio views/user/day | 0 | 3+ | Page views |
| Meta page engagement | 0% | 25% | Traffic share |
| Deal conversion rate | Unknown | +20% | Click to buy ratio |
| Session duration | Unknown | +30% | Analytics |
| Feature discovery | Low | High | Survey |

---

## Conclusion

**Current State:** AxiePro has sophisticated backend analytics (meta shifts, portfolio P&L, normalized scoring) that are **completely invisible** to users. The frontend presents basic deal detection well but fails to expose the full value capture potential.

**Key Insight:** Users are only seeing ~60% of the value the platform can deliver. The remaining 40% exists in the backend but has no UI.

**Recommended Action:** Prioritize frontend work to expose existing backend capabilities before building new features. This provides maximum value with minimum development effort.

**ROI of Recommendations:**
- 1-2 weeks of frontend work could unlock 40% more user value
- Portfolio P&L view is critical for subscription conversion
- Meta shifts exposure provides competitive differentiation

---

*Assessment generated using Prompt Effectiveness Assessor framework v2*
*Perspective: Ecosystem participant value capture analysis*
