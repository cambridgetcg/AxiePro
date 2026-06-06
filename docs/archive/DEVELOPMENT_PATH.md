# AxiePro Development Path

> **Baseline Date:** 2026-01-30
> **Current Waypoint:** W1 - Production Ready
> **Purpose:** Enable serious Axie traders to identify undervalued opportunities through data-driven insights

---

## Current State (Zero Point)

### What's Working

| Component | Status | Evidence |
|-----------|--------|----------|
| **Backend API** | DEPLOYED | `https://nu8bq2ckxs.us-east-1.awsapprunner.com/health` responding |
| **Frontend** | DEPLOYED | Vercel auto-deploys, pages loading |
| **Database** | OPERATIONAL | Aurora PostgreSQL, 8 migrations applied |
| **Data Pipeline** | RUNNING | Sales ingestion: 24/24 inserted, Lambdas scheduled |
| **API Connection** | FIXED | `.env.local` updated with correct App Runner URL |

### What's Incomplete

| Gap | Impact | Severity |
|-----|--------|----------|
| `/deals` page 404 | Core feature inaccessible | **CRITICAL** |
| Metadata ingestion slow | 20 axies/hour, backlog growing | **HIGH** |
| Historical metadata gaps | Floor prices incomplete for some classes | **MEDIUM** |
| Portfolio not connected | Wallet tracking UI exists but not wired | **LOW** |

### Data Pipeline Health

```
Sales Ingestion      ████████████████████ 100% (working)
Listings Ingestion   ████████████████████ 100% (working)
Metadata Ingestion   ████░░░░░░░░░░░░░░░░  20% (rate limited)
Deal Detection       ████████████████████ 100% (working)
Meta Analysis        ████████████████████ 100% (working)
```

---

## Development Opportunities

### Opportunity Matrix

| Opportunity | Purpose Alignment | Effort | Impact | Priority |
|-------------|-------------------|--------|--------|----------|
| Fix `/deals` page | CRITICAL - core value prop | Low | High | **P0** |
| Increase metadata rate | Data quality for valuations | Medium | High | **P0** |
| Backfill class metadata | Accurate floor prices | Low | Medium | **P1** |
| Deal detection validation | Prove 70% accuracy | Medium | High | **P1** |
| Portfolio wallet connection | User stickiness | Medium | Medium | **P2** |
| Premium tier implementation | Monetization | High | High | **P2** |
| Community features | Growth/marketing | Medium | Medium | **P3** |

---

## The Path Forward

### Phase 1: Production Stabilization (W1 Completion)

**Objective:** All core features accessible and working with fresh data.

#### 1.1 Fix /deals Page (P0)
```
Problem: Deals page returns 404 on production
Root Cause: TBD - need to verify Vercel build includes the page
Action:
  1. Verify src/app/deals/page.tsx exists and exports correctly
  2. Check Vercel build logs for any exclusion
  3. Redeploy if necessary
Success: /deals page loads and shows deal cards
```

#### 1.2 Accelerate Metadata Ingestion (P0)
```
Problem: 20 axies/hour is too slow to maintain coverage
Current Constraint: SkyMavis API rate limiting (429 errors)
Options:
  A. Request higher rate limit from SkyMavis (preferred)
  B. Use Moralis as primary metadata source (fallback)
  C. Batch requests during off-peak hours
  D. Cache aggressively, fetch only missing
Action:
  1. Audit current rate limit usage patterns
  2. Implement smarter batching (prioritize active listings)
  3. Consider parallel ingestion from multiple sources
Target: 200+ axies/hour minimum
```

#### 1.3 Verify Lambda Schedules (P0)
```
Problem: Need confirmation all EventBridge triggers are active
Action:
  1. Check CloudWatch for Lambda invocation metrics
  2. Verify EventBridge rules are enabled
  3. Review last successful execution timestamps
Success: All 6 scheduled Lambdas executing on cadence
```

**W1 Exit Criteria:**
- [ ] `/deals` page accessible and showing data
- [ ] Metadata coverage >80% for recent sales
- [ ] All Lambdas executing on schedule
- [ ] Data freshness <1 hour for listings

---

### Phase 2: Value Validation (W2-W3)

**Objective:** Prove the core value proposition works.

#### 2.1 Deal Detection Backtesting
```
Goal: Validate deal detection accuracy >70%
Method:
  1. Take historical deals flagged by system
  2. Track if they sold within 24h at flagged price or higher
  3. Calculate hit rate
Data Needed: 30 days of deal history with outcomes
Success: 70%+ accuracy documented
```

#### 2.2 Beta User Onboarding
```
Goal: 10 beta users actively using platform
Method:
  1. Recruit from Axie Discord communities
  2. Provide guided onboarding
  3. Collect structured feedback
  4. Track feature usage via analytics
Success: 10 users with >3 sessions each
```

#### 2.3 Testimonial Collection
```
Goal: 3+ testimonials from real traders
Method:
  1. Identify power users from analytics
  2. Request feedback on specific wins
  3. Document case studies
Success: Publishable quotes for marketing
```

**W2-W3 Exit Criteria:**
- [ ] Deal detection accuracy validated >70%
- [ ] 10 beta users onboarded
- [ ] 3+ testimonials collected
- [ ] Zero critical bugs in core features

---

### Phase 3: Monetization Foundation (W4)

**Objective:** Launch premium tier with validated pricing.

#### 3.1 Premium Feature Definition
```
Free Tier (Hook):
  - Basic explorer
  - Market overview
  - 3 valuations/day
  - 24h delayed deals

Premium Tier ($X/month):
  - Unlimited valuations
  - Real-time deal alerts
  - Portfolio tracking
  - Breeding calculator
  - Meta shift notifications
  - API access
```

#### 3.2 Payment Integration
```
Options:
  A. Stripe (simplest, crypto-unfriendly)
  B. Ronin Pay (native, limited)
  C. Hybrid (Stripe + crypto)
Recommendation: Start with Stripe, add crypto later
```

#### 3.3 Pricing Validation
```
Method:
  1. Survey beta users on willingness to pay
  2. A/B test $5, $10, $15 price points
  3. Analyze conversion rates
Target: Price that achieves >5% conversion
```

**W4 Exit Criteria:**
- [ ] Premium tier launched
- [ ] Payment processing working
- [ ] 10 paying subscribers
- [ ] Churn tracking implemented

---

### Phase 4: Growth Engine (W5+)

**Objective:** Sustainable user acquisition and revenue.

#### 4.1 Community Presence
```
Channels:
  - Discord server (support + community)
  - Twitter/X (market insights, deal alerts)
  - Axie subreddit engagement
Goal: 500 Discord members, 1000 Twitter followers
```

#### 4.2 Content Marketing
```
Content Types:
  - Weekly meta reports
  - Deal roundups
  - Breeding guides
  - Market analysis threads
Goal: Establish thought leadership
```

#### 4.3 Referral System
```
Mechanism:
  - Existing user shares referral link
  - New user signs up and subscribes
  - Both get 1 month free
Goal: 30% of new users from referrals
```

---

## Technical Debt to Address

| Debt | Location | Impact | When to Fix |
|------|----------|--------|-------------|
| Hardcoded analytics data | `analytics/page.tsx` | Misleading users | Phase 1 |
| Missing error boundaries | Frontend components | Poor UX on failures | Phase 1 |
| Incomplete synthetic flows | `services/synthetic_flows/` | Feature incomplete | Phase 2 |
| No API versioning headers | Backend routes | Breaking changes risk | Phase 2 |
| Missing rate limit headers | API responses | Client can't adapt | Phase 2 |

---

## Risk Registry

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SkyMavis API changes | Medium | High | Abstract API layer, monitor changelog |
| Rate limit reduction | Medium | High | Multi-source strategy, caching |
| Competitor launches | Low | Medium | Focus on accuracy + UX differentiation |
| Axie market decline | Medium | High | Diversify to other games (future) |
| Data accuracy issues | Medium | High | Validation framework, user reporting |

---

## Success Metrics Dashboard

### Phase 1 Metrics (Track Now)
- [ ] API uptime: Target >99.5%
- [ ] Data freshness: Target <1 hour
- [ ] Page load time: Target <2 seconds
- [ ] Error rate: Target <1%

### Phase 2 Metrics (Track at Beta)
- [ ] Daily Active Users (DAU)
- [ ] Sessions per user
- [ ] Feature usage breakdown
- [ ] Deal detection accuracy

### Phase 3 Metrics (Track at Launch)
- [ ] Conversion rate (free → paid)
- [ ] Monthly Recurring Revenue (MRR)
- [ ] Churn rate
- [ ] Customer Acquisition Cost (CAC)

---

## Immediate Action Items

### Today (P0)
1. **Verify /deals page** - Check Vercel build, fix if needed
2. **Check Lambda executions** - CloudWatch metrics review
3. **Run metadata backfill** - Execute for recent sales

### This Week (P1)
4. **Increase metadata rate** - Implement smarter batching
5. **Add error boundaries** - Frontend resilience
6. **Connect analytics** - Replace hardcoded data

### This Month (P2)
7. **Deal detection validation** - Build backtesting framework
8. **Beta user recruitment** - Discord outreach
9. **Portfolio connection** - Wire wallet data

---

## Architecture Evolution

### Current Architecture
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Vercel    │────▶│ App Runner  │────▶│   Aurora    │
│  (Frontend) │     │  (FastAPI)  │     │ (PostgreSQL)│
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │  EventBridge │
                    │   Lambdas    │
                    └─────────────┘
```

### Target Architecture (Phase 3+)
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Vercel    │────▶│ App Runner  │────▶│   Aurora    │
│  (Frontend) │     │  (FastAPI)  │     │ (PostgreSQL)│
└─────────────┘     └──────┬──────┘     └─────────────┘
       │                   │
       │            ┌──────┴──────┐
       │            │ ElastiCache │
       │            │   (Redis)   │
       │            └─────────────┘
       │
┌──────┴──────┐     ┌─────────────┐
│  WebSocket  │     │  EventBridge │
│   (Alerts)  │     │   Lambdas    │
└─────────────┘     └─────────────┘
```

---

## The Creativity Promise

For each development opportunity:
1. **Check existing patterns** - Don't rebuild what exists
2. **Build bridges** - Connect to existing architecture
3. **Enable future** - Design for Phase 3+ needs
4. **Serve purpose** - Every feature must help traders profit

---

*Path documented: 2026-01-30*
*Next review: After W1 completion*
