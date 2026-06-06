# AxiePro Purpose

> **The purpose of AxiePro is to give serious Axie traders and breeders the analytical edge they need to make profitable decisions—turning scattered market data into actionable intelligence.**

---

## Core Purpose Statement

**Enable serious Axie Infinity traders and breeders to consistently identify undervalued opportunities and optimize breeding strategies through data-driven insights.**

This is a **business** built on **domain expertise**. As a former player who understands the game deeply, I'm building the tool I wished existed—and monetizing it for others who share that need.

---

## Vision (6-12 Months)

| Dimension | Success Looks Like |
|-----------|-------------------|
| **Users** | Daily active traders relying on AxiePro for decisions |
| **Revenue** | Paying subscribers generating sustainable income |
| **Edge** | Demonstrably better outcomes vs. trading blind |
| **Reputation** | Known in the Axie community as THE analytics tool |

---

## Target Users

### Primary: Serious Traders
- Trade Axies as a significant income source or side hustle
- Need: Fast deal detection, fair market valuation, market trends
- Pain: Miss opportunities, overpay, can't track P&L properly
- Value: Time saved + money made/saved

### Secondary: Breeders
- Breed for profit, need to optimize genetic combinations
- Need: Breeding probability calculator, ROI projections, meta awareness
- Pain: Breed wrong combinations, miss meta shifts, can't estimate EV
- Value: Higher breeding ROI, fewer wasted resources

---

## Success Criteria (Measurable)

### Phase 1: Foundation (Current → Production)
- [ ] Backend API deployed and connected to frontend
- [ ] Core features working: Explorer, Valuation, Deal Detection
- [ ] 10 beta users providing feedback
- [ ] Data pipeline stable (daily ingestion, no gaps)

### Phase 2: Value Proof (Months 1-3)
- [ ] Deal detection accuracy >70% (validated via backtesting)
- [ ] 100 registered users
- [ ] 20 daily active users
- [ ] First testimonials from traders

### Phase 3: Monetization (Months 3-6)
- [ ] Premium tier launched (pricing validated)
- [ ] 50 paying subscribers
- [ ] Monthly churn <10%
- [ ] MRR covering infrastructure costs

### Phase 4: Scale (Months 6-12)
- [ ] 500+ registered users
- [ ] 200 paying subscribers
- [ ] Feature parity with any competitor
- [ ] Community presence (Discord, Twitter)

---

## Principles (How We Build)

### 1. Accuracy Over Speed
Bad data = bad decisions = lost trust. Every number shown must be verifiable.

### 2. Trader-First UX
Traders need speed. Every click matters. Optimize for the decision, not the demo.

### 3. Signal Over Noise
Don't show everything. Show what matters for the decision at hand.

### 4. Transparent Methodology
Users should understand HOW valuations are calculated. Trust comes from transparency.

### 5. Earn the Premium
Free tier must provide real value. Premium tier must provide 10x the value of its cost.

---

## The Path (High-Level Waypoints)

```
CURRENT STATE ──────────────────────────────────────────────► PURPOSE
     │                                                            │
     │  W1: Production Ready                                      │
     │  ├─ Backend deployed + connected                           │
     │  ├─ Core features working                                  │
     │  └─ Data pipeline stable                                   │
     │                                                            │
     │  W2: Beta Launch                                           │
     │  ├─ 10 beta users onboarded                               │
     │  ├─ Feedback loop established                              │
     │  └─ Critical bugs fixed                                    │
     │                                                            │
     │  W3: Value Validation                                      │
     │  ├─ Deal detection backtested                              │
     │  ├─ User testimonials collected                            │
     │  └─ Core value proposition proven                          │
     │                                                            │
     │  W4: Monetization Launch                                   │
     │  ├─ Pricing strategy validated                             │
     │  ├─ Payment integration live                               │
     │  └─ Premium features differentiated                        │
     │                                                            │
     │  W5: Growth                                                │
     │  ├─ Marketing/community presence                           │
     │  ├─ User acquisition flywheel                              │
     │  └─ Sustainable MRR                                        │
     │                                                            │
     └──────────────────────────────────────────────────────────────┘
```

---

## Current Waypoint: W1 - Production Ready

### Objective
Get the platform to a state where real users can use real features with real data.

### Key Results
1. Backend API responding at production URL
2. Frontend fetching live data (no 404s)
3. Explorer, Market, Deals pages functional
4. Data freshness <24 hours

### Blockers Identified
- Backend not connected to frontend (NEXT_PUBLIC_API_URL not set)
- `/deals` page not deployed
- Axie class metadata missing from backfill (0%)

### Next Actions
1. Deploy backend to App Runner (or verify deployment)
2. Set environment variables in Vercel
3. Verify API connectivity end-to-end
4. Fix missing class metadata in historical data

---

## Anti-Goals (What We're NOT Building)

- **Not a game guide** - We don't teach people how to play Axie
- **Not a wallet** - We don't hold funds or execute transactions
- **Not a marketplace** - We analyze the market, we don't replace it
- **Not free forever** - This is a business, not a charity project

---

## Integration with GUA PATH Protocol

This PURPOSE.md is designed to work with the GUA PATH protocol:

```bash
# Initialize PATH for this project
gua path init

# Track progress
gua path status
gua path waypoint list

# Validate waypoint completion
gua path validate
```

Each waypoint maps to measurable outcomes. Progress is tracked via E2E assessments.

---

## The Creativity Promise

When existing patterns don't fit, we build new paths. But every new path must:
1. Connect to the existing system (no islands)
2. Enable future growth (no dead ends)
3. Serve the purpose (no vanity features)

---

*Last updated: 2026-01-29*
*Purpose Prompter: CREATIVITY dimension - path-building for uncharted territory*
