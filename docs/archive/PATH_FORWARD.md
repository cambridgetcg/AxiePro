# AxiePro: Path Forward from Zero Point

**Date Established:** 2026-01-30
**Zero Point Assessment:** 75% Production Ready (W1)
**Purpose:** Enable serious Axie traders to identify undervalued opportunities through data-driven insights

---

## Executive Summary

### Current State (Zero Point)

**What's Working (75%):**
- ✅ Backend API: 11 route modules deployed and responding
- ✅ Frontend: 9 pages deployed, 3/7 fully wired to backend
- ✅ Data Pipeline: 8/9 Lambdas operational (sales, listings, pricing, deals, meta)
- ✅ Infrastructure: All 10 CDK stacks deployed (App Runner, Aurora, Redis, EventBridge)
- ✅ Database: 8/8 migrations applied, schema optimized
- ✅ Deal Detection: Live with normalized scoring

**Critical Blocker (25%):**
- ❌ Metadata Ingestion: 20 axies/hour vs need 200+/hour (rate limited)
  - Impact: Floor prices incomplete for many Axies
  - Root cause: Conservative batching + SkyMavis API rate limits
  - Result: Valuation confidence suffers

### Path to Purpose

```
CURRENT STATE (W1: 75%) ──────────────────────────────────────► PURPOSE
     │
     ├─ W1 Completion: Production Ready (Est. 2-3 days)
     │  └─ Fix metadata rate limiting → 80%+ coverage
     │
     ├─ W2: Beta Launch (Est. 1-2 weeks)
     │  └─ 10 beta users, feedback loop, bug fixes
     │
     ├─ W3: Value Validation (Est. 2-3 weeks)
     │  └─ 70%+ deal accuracy, testimonials, proof of value
     │
     ├─ W4: Monetization Launch (Est. 1-2 months)
     │  └─ Premium tier, payment integration, 50+ subscribers
     │
     └─ W5: Growth (Est. 3-6 months)
        └─ Community, marketing, sustainable MRR
```

---

## Waypoint 1: Production Ready (CURRENT - 75% Complete)

### Objective
All core features accessible and working with fresh, accurate data.

### Exit Criteria

| Criterion | Current | Target | Status |
|-----------|---------|--------|--------|
| `/deals` page accessible | ✅ YES | ✅ YES | DONE |
| Deal data showing | ✅ YES | ✅ YES | DONE |
| Metadata coverage | ❌ ~20% | 80%+ | **BLOCKER** |
| Lambda execution | ⚠️ Unknown | 100% | VERIFY |
| Listing freshness | ✅ <5min | <1h | DONE |

### Critical Path (2-3 Days)

#### Day 1: Verify & Diagnose
```
[X] 1. Verify EventBridge rules enabled
    Action: Check CloudWatch → EventBridge → Rules
    Success: All 7 rules show "Enabled" status

[X] 2. Audit metadata ingestion logs
    Action: CloudWatch Logs → /aws/lambda/metadata_ingestion
    Look for: Rate limit errors (429), batch failures, success rate
    Success: Understand bottleneck precisely

[X] 3. Calculate metadata coverage
    SQL: SELECT COUNT(DISTINCT axie_id) FROM axie_metadata
         vs COUNT(DISTINCT axie_id) FROM listings
    Success: Baseline coverage % established
```

#### Day 2: Fix Rate Limiting
```
[ ] 4. Option A: Optimize SkyMavis batching
    Current: 10 axies/batch, 6s delay = 100 axies/hour max
    Proposed: 50 axies/batch, 2s delay = 900 axies/hour max
    File: backend/src/lambdas/metadata_ingestion.py:43-46
    Risk: May hit rate limit harder → Monitor CloudWatch

    CHANGES:
    - MAX_AXIES_PER_RUN: 10 → 50
    - BATCH_DELAY_SECONDS: 6.0 → 2.0
    - Add exponential backoff on 429 errors

[ ] 5. Option B: Enable Moralis parallel source
    Current: SkyMavis only
    Proposed: Query Moralis in parallel, fallback to SkyMavis
    File: backend/src/services/moralis_client.py (already exists)
    Risk: Cost increase from Moralis API usage

    CHANGES:
    - Add Moralis metadata fetch to pipeline
    - Use SkyMavis for genes, Moralis for metadata
    - Merge results (prefer SkyMavis when both available)

[ ] 6. Option C: Request higher SkyMavis rate limit
    Action: Contact SkyMavis developer relations
    Timeline: Unknown (could be weeks)
    Recommendation: Do in parallel, don't wait

RECOMMENDED APPROACH: A + C
  - Implement Option A immediately (optimized batching)
  - Submit Option C request (higher limit)
  - Keep Option B as backup if A fails
```

#### Day 3: Validate & Monitor
```
[ ] 7. Deploy metadata ingestion changes
    Action: CDK deploy compute-stack
    Verification: Lambda updated, EventBridge trigger still active

[ ] 8. Monitor ingestion for 24 hours
    Metrics to track:
    - Axies processed per hour
    - Rate limit errors (should decrease)
    - Database coverage % (should increase)
    Success: >200 axies/hour sustained

[ ] 9. Verify W1 completion
    Checklist:
    - [ ] Metadata coverage >80%
    - [ ] All 7 EventBridge rules enabled
    - [ ] No critical errors in Lambda logs (past 24h)
    - [ ] Deal detection showing accurate valuations
    Success: W1 exit criteria met
```

### W1 Completion Gate

**Before declaring W1 complete, verify:**
1. Run E2E test: Search for Axie → View valuation → Check deal score
2. Check data freshness: Listings updated within 1 hour
3. Verify backend health: `curl https://nu8bq2ckxs.us-east-1.awsapprunner.com/health`
4. Test all core pages: Explorer, Market, Deals (all loading data)

**W1 Complete = Ready for Beta Users**

---

## Waypoint 2: Beta Launch (Est. 1-2 Weeks After W1)

### Objective
10 beta users actively using the platform, providing structured feedback.

### Prerequisites
- W1 complete (production stable)
- Analytics wired (track feature usage)
- Error boundaries added (graceful failure)

### Key Results

| Metric | Target | Tracking |
|--------|--------|----------|
| Beta users onboarded | 10 | Manual list |
| Daily active users | 5+ | Google Analytics |
| Sessions per user | 3+ | GA events |
| Critical bugs reported | <3 | GitHub Issues |
| Feature usage | Track | GA custom events |

### Execution Plan

#### Week 1: Prepare for Beta
```
[ ] 1. Wire analytics to real data
    Files: frontend/src/app/analytics/page.tsx
    Change: Replace mock data with API calls to /market/analytics/*
    Success: Charts show real 24h/7d/30d trends

[ ] 2. Add error boundaries to all pages
    Files: frontend/src/app/*/page.tsx
    Pattern: Wrap page content in <ErrorBoundary fallback={<ErrorState />}>
    Success: Pages show friendly error, don't crash

[ ] 3. Create beta user onboarding guide
    Document: docs/BETA_GUIDE.md
    Content:
    - What is AxiePro?
    - How to use Explorer, Market, Deals
    - What to test (walkthroughs)
    - How to report feedback (GitHub Issues template)

[ ] 4. Set up feedback collection
    Create: GitHub Issue templates (Bug Report, Feature Request, Feedback)
    Create: Discord channel for beta users (optional)
    Success: Clear feedback channels established
```

#### Week 2: Recruit & Onboard
```
[ ] 5. Recruit 10 beta users
    Sources:
    - Axie Infinity Discord (Trading channels)
    - Axie subreddit r/AxieInfinity
    - Twitter/X Axie communities
    - Personal network (if former player)

    Pitch: "Help test a new Axie trading analytics tool. Get early access."
    Success: 10 users signed up

[ ] 6. Onboard users individually
    Process:
    1. Send beta guide
    2. Walk through Explorer, Market, Deals
    3. Ask them to test 1-2 workflows
    4. Schedule check-in after 3 days
    Success: 10 users completed first session

[ ] 7. Collect initial feedback
    After 1 week of usage:
    - Survey users (Google Form): What worked? What broke? What's confusing?
    - Review GitHub Issues
    - Analyze GA data (which features used most?)
    Success: Feedback documented, patterns identified

[ ] 8. Fix critical bugs
    Priority: Anything preventing core workflow (search, valuation, deals)
    Timeline: 48h turnaround on critical issues
    Success: Zero show-stoppers remaining
```

### W2 Completion Gate

**Before declaring W2 complete:**
1. 10 users have each completed 3+ sessions
2. Critical bugs resolved (GitHub Issues closed)
3. Feature usage tracked in GA (know what's used, what's ignored)
4. At least 3 positive feedback quotes (for testimonials)

**W2 Complete = Value Hypothesis Testable**

---

## Waypoint 3: Value Validation (Est. 2-3 Weeks After W2)

### Objective
Prove the core value proposition: "Traders make better decisions using AxiePro."

### Prerequisites
- W2 complete (beta users active)
- Deal detection stable
- 30+ days of deal history in database

### Key Results

| Metric | Target | Method |
|--------|--------|--------|
| Deal accuracy | >70% | Backtesting historical deals |
| User testimonials | 3+ | Survey power users |
| Sessions per user | 5+ | Analytics tracking |
| Retention (7-day) | >30% | Cohort analysis |

### Execution Plan

#### Week 1: Backtesting Framework
```
[ ] 1. Build deal backtesting script
    File: backend/scripts/backtest_deals.py
    Logic:
    - Fetch deals flagged in past 30 days
    - Check if sold within 24h at flagged price or higher
    - Calculate hit rate (sold_profitable / total_flagged)
    Success: Script outputs accuracy %

[ ] 2. Run initial backtest
    Data: Past 30 days of deals (if available)
    Success: Baseline accuracy calculated (may be <70%)

[ ] 3. Analyze false positives
    Why did flagged deals NOT sell?
    - Overvaluation (model wrong)
    - Market shift (meta changed)
    - Listing removed (seller changed mind)
    Success: Understand failure modes

[ ] 4. Tune deal detection thresholds
    Files: backend/src/lambdas/deal_detector.py
    Adjust: DEAL_THRESHOLD_PERCENT, SNIPE_THRESHOLD_PERCENT
    Goal: Optimize precision vs recall
    Success: Retest shows >70% accuracy
```

#### Week 2-3: Testimonial Collection
```
[ ] 5. Identify power users
    Criteria: 10+ sessions, used deals page, high engagement
    Method: Query GA data for top 5 users
    Success: 5 candidates identified

[ ] 6. Interview power users
    Questions:
    - Have you used AxiePro to make a trade decision?
    - Did you find a deal you wouldn't have otherwise?
    - How much $ did you save/make?
    - What would you pay for this?
    Success: 3+ success stories documented

[ ] 7. Create case studies
    Format: "User X found a deal worth Y ETH using AxiePro"
    Include: Screenshots, before/after valuation
    Success: 3 publishable case studies

[ ] 8. Document value proof
    File: docs/VALUE_PROOF.md
    Content:
    - Deal accuracy: X%
    - User testimonials (3 quotes)
    - Case studies (3 stories)
    - Analytics (usage patterns)
    Success: Compelling proof of value
```

### W3 Completion Gate

**Before declaring W3 complete:**
1. Deal detection accuracy >70% (backtested)
2. 3+ user testimonials collected
3. At least 1 documented case of user profiting from AxiePro
4. Retention rate >30% (users coming back)

**W3 Complete = Ready to Monetize**

---

## Waypoint 4: Monetization Launch (Est. 1-2 Months After W3)

### Objective
Launch premium tier, achieve first 50 paying subscribers.

### Prerequisites
- W3 complete (value proven)
- User/subscription model in database
- Payment integration tested

### Key Results

| Metric | Target | Timeline |
|--------|--------|----------|
| Paying subscribers | 50 | Month 1-2 |
| Free → Paid conversion | >5% | Month 1 |
| Monthly churn | <10% | Month 2+ |
| MRR | Cover infra costs | Month 2 |

### Phase 1: Premium Architecture (Week 1-2)

#### Database Changes
```
[ ] 1. Add user/subscription tables
    Migration: 09_user_subscriptions.sql
    Tables:
    - users (id, wallet_address, created_at, tier)
    - subscriptions (id, user_id, tier, status, started_at, expires_at)
    - usage_limits (tier, resource, limit_per_day)
    Success: Schema deployed to Aurora

[ ] 2. Implement tier checking middleware
    File: backend/src/middleware/subscription.py
    Logic:
    - Check user tier from JWT or wallet
    - Enforce limits (free: 3 valuations/day, premium: unlimited)
    - Return 429 if limit exceeded
    Success: Endpoints enforce tier limits

[ ] 3. Add usage tracking
    Table: usage_events (user_id, resource, timestamp)
    Track: Valuation requests, deal views, API calls
    Success: Can query "valuations used today by user X"
```

#### Premium Features Definition
```
FREE TIER (Hook):
- [X] Basic explorer (search by ID)
- [X] Market overview (floor prices)
- [ ] 3 valuations per day (rate limit)
- [ ] 24h delayed deals (filter by timestamp)

PREMIUM TIER ($10-15/month):
- [ ] Unlimited valuations
- [ ] Real-time deal alerts (Kinesis stream)
- [ ] Portfolio tracking (wallet integration)
- [ ] Breeding calculator (UI wired to backend)
- [ ] Meta shift notifications (alerts enabled)
- [ ] API access (token generation)
```

### Phase 2: Payment Integration (Week 3-4)

#### Stripe Setup
```
[ ] 4. Create Stripe account
    Setup: Developer account, test mode
    Products: Monthly subscription ($10-15, test multiple prices)
    Success: Stripe dashboard configured

[ ] 5. Implement Stripe checkout
    Files:
    - backend/src/api/routes/billing.py (create checkout session)
    - frontend/src/app/subscribe/page.tsx (subscribe button → Stripe)
    Flow:
    1. User clicks "Upgrade to Premium"
    2. Backend creates Stripe checkout session
    3. Redirect to Stripe payment page
    4. Stripe webhook confirms payment
    5. Backend updates subscription table
    Success: Test payment completes, user tier updated

[ ] 6. Implement subscription management
    Pages:
    - /account (view current tier, usage stats)
    - /subscribe (upgrade to premium)
    - /billing (manage subscription, cancel)
    Success: Users can self-serve tier changes

[ ] 7. Add Stripe webhook handler
    Endpoint: /api/v1/webhooks/stripe
    Events: checkout.session.completed, customer.subscription.deleted
    Success: Subscriptions auto-update on payment events
```

### Phase 3: Launch & Pricing (Week 5-6)

#### Pricing Validation
```
[ ] 8. Survey beta users on pricing
    Question: "Would you pay $X/month for premium features?"
    Test: $5, $10, $15 price points
    Success: Identify price with >20% willingness-to-pay

[ ] 9. A/B test pricing (if volume allows)
    Method: Show 50% of users $10, 50% $15
    Track: Conversion rate by price point
    Success: Optimal price identified

[ ] 10. Launch premium tier
    Announcement:
    - Email beta users
    - Post on Axie Discord/Reddit
    - Twitter/X announcement
    Message: "Premium now available - real-time deals, unlimited valuations"
    Success: First 10 subscribers within 48h
```

### Phase 4: Growth to 50 Subscribers (Week 7-8)

#### Conversion Optimization
```
[ ] 11. Add upgrade prompts
    Locations:
    - After 3rd valuation (free limit hit)
    - On deals page (show premium-only features grayed out)
    - Success modal: "Upgrade to track this deal in real-time"
    Success: Conversion rate >5%

[ ] 12. Offer launch discount
    Promo: "50% off first month" for early adopters
    Timeline: 2 weeks
    Success: 20+ subscribers in first 2 weeks

[ ] 13. Track churn & retention
    Metrics:
    - Monthly churn rate (canceled / total)
    - Retention cohorts (% still paying after 30/60/90 days)
    Success: Churn <10%, identify reasons for cancellations

[ ] 14. Iterate on value
    Based on churn feedback:
    - What premium features are used most?
    - What's missing that users want?
    - How to improve retention?
    Success: Product roadmap prioritized by subscriber feedback
```

### W4 Completion Gate

**Before declaring W4 complete:**
1. 50 paying subscribers
2. Stripe integration stable (no payment failures)
3. Churn rate <10%
4. MRR covers AWS infrastructure costs (~$100-200/month)

**W4 Complete = Sustainable Business Model Proven**

---

## Waypoint 5: Growth (Est. 3-6 Months After W4)

### Objective
Build community, scale user acquisition, achieve 200+ paying subscribers.

### Prerequisites
- W4 complete (monetization working)
- Product-market fit validated
- Core features stable

### Key Results

| Metric | Target | Timeline |
|--------|--------|----------|
| Registered users | 500+ | Month 3 |
| Paying subscribers | 200+ | Month 6 |
| Discord members | 500+ | Month 3 |
| Twitter followers | 1000+ | Month 6 |
| Referral conversion | 30% | Month 3+ |

### Growth Levers

#### 1. Community Building
```
[ ] Create Discord server
    Channels: #general, #deals, #support, #feedback, #premium
    Moderation: Set rules, appoint moderators
    Success: 100 members in first month

[ ] Twitter/X presence
    Content: Daily market insights, deal highlights, meta shift alerts
    Frequency: 1-2 posts/day
    Success: 500 followers in first 2 months

[ ] Axie subreddit engagement
    Activity: Share useful insights, answer questions, post deal roundups
    Frequency: 3x/week
    Success: Recognized as helpful contributor
```

#### 2. Content Marketing
```
[ ] Weekly meta reports
    Format: "This week in Axie: [meta shifts, floor price changes, notable deals]"
    Distribution: Discord, Twitter, Reddit
    Success: 100+ views per report

[ ] Breeding guides
    Content: "How to use AxiePro breeding calculator for ROI"
    Format: Video walkthrough or written guide
    Success: 500+ views

[ ] Deal roundups
    Content: "Top 10 deals this week found by AxiePro users"
    Includes: Screenshots, savings calculations
    Success: 200+ views, drives signups
```

#### 3. Referral System
```
[ ] Implement referral program
    Mechanism:
    - User shares referral link
    - New user signs up & subscribes
    - Both get 1 month free (or $5 credit)
    Success: 30% of new subscribers from referrals

[ ] Track referral effectiveness
    Metrics: Referrals sent, signups, conversions
    Optimize: Test different incentives
    Success: Sustainable viral coefficient
```

#### 4. Feature Development
```
Prioritize based on subscriber feedback:

HIGH PRIORITY (user-requested):
[ ] Real-time deal alerts (push notifications)
[ ] Portfolio P&L tracking
[ ] Breeding ROI calculator (full implementation)
[ ] Meta shift alerts (automated detection)

MEDIUM PRIORITY (differentiation):
[ ] Advanced filters (genes, purity, breed count)
[ ] Batch valuation (upload CSV of Axie IDs)
[ ] Historical trends (price charts per Axie)
[ ] Market maker detection (whale watching)

LOW PRIORITY (nice-to-have):
[ ] Mobile app (React Native)
[ ] Axie comparison tool
[ ] Scholar tracking (for managers)
[ ] API for third-party integrations
```

### W5 Completion Gate

**Before declaring W5 complete:**
1. 200+ paying subscribers
2. 500+ Discord members OR 1000+ Twitter followers
3. 30% of new users from referrals
4. Sustainable MRR growth (>10% month-over-month)

**W5 Complete = Established Business**

---

## Development Opportunities by Priority

### P0 (Critical - W1 Blockers)

| Opportunity | Impact | Effort | Timeline |
|-------------|--------|--------|----------|
| Fix metadata rate limiting | HIGH - Enables accurate valuations | MEDIUM - Code + deploy | 2-3 days |
| Verify Lambda schedules | HIGH - Ensures data freshness | LOW - CloudWatch check | 1 hour |

### P1 (High Value - W2 Enablers)

| Opportunity | Impact | Effort | Timeline |
|-------------|--------|--------|----------|
| Wire analytics to real data | HIGH - Beta user trust | LOW - Replace mocks | 1 day |
| Add error boundaries | MEDIUM - User experience | LOW - Component wrappers | 1 day |
| Create beta onboarding guide | HIGH - User success | LOW - Documentation | 2 hours |

### P2 (Medium Value - W3-W4 Features)

| Opportunity | Impact | Effort | Timeline |
|-------------|--------|--------|----------|
| Deal detection backtesting | HIGH - Prove value | MEDIUM - Script + analysis | 1 week |
| User/subscription model | HIGH - Monetization | MEDIUM - DB + middleware | 1 week |
| Stripe integration | HIGH - Payment flow | MEDIUM - API + webhooks | 1 week |
| Portfolio wallet integration | MEDIUM - Stickiness | MEDIUM - Web3 + backend | 2 weeks |

### P3 (Nice-to-Have - W5 Growth)

| Opportunity | Impact | Effort | Timeline |
|-------------|--------|--------|----------|
| Referral system | MEDIUM - Viral growth | MEDIUM - Tracking + UI | 1 week |
| Discord community | MEDIUM - Engagement | LOW - Setup + moderation | 3 days |
| Content marketing | MEDIUM - Awareness | ONGOING - Regular posts | Continuous |

---

## Risk Mitigation

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SkyMavis API changes | MEDIUM | HIGH | Abstract API layer, monitor changelog, multi-source strategy |
| Rate limit reduction | MEDIUM | HIGH | Caching, Moralis backup, request higher limit |
| Database scaling | LOW | MEDIUM | Aurora auto-scaling, optimize queries, add indexes |
| Lambda cold starts | LOW | LOW | Provisioned concurrency for critical Lambdas |

### Business Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Competitor launches | LOW | MEDIUM | Focus on accuracy + UX differentiation, build moat via community |
| Axie market decline | MEDIUM | HIGH | Diversify to other games (future), build loyal user base |
| Low conversion rate | MEDIUM | HIGH | A/B test pricing, improve free tier value, optimize upgrade prompts |
| High churn | MEDIUM | HIGH | Collect feedback, iterate on features, improve onboarding |

### Market Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Insufficient traders | LOW | HIGH | Market research validates 10k+ active traders, beta will prove demand |
| Price sensitivity | MEDIUM | MEDIUM | Test multiple price points, offer annual discount, bundle features |
| Free alternatives | MEDIUM | MEDIUM | Compete on accuracy + speed, not features alone |

---

## Success Metrics Dashboard

### W1 Metrics (Track Now)
```sql
-- Metadata coverage
SELECT
  (SELECT COUNT(DISTINCT axie_id) FROM axie_metadata) * 100.0 /
  (SELECT COUNT(DISTINCT axie_id) FROM listings) AS coverage_pct;

-- Data freshness
SELECT MAX(updated_at) FROM listings; -- Should be <1 hour ago

-- Lambda execution count (CloudWatch)
-- Check: sales_ingestion, listings_ingestion, metadata_ingestion invocation count (past 24h)
```

### W2 Metrics (Track at Beta)
```javascript
// Google Analytics custom events
ga('send', 'event', 'Feature', 'Used', 'Explorer');
ga('send', 'event', 'Feature', 'Used', 'Deals');
ga('send', 'event', 'Valuation', 'Requested', axieId);

// Track: DAU, sessions per user, feature usage breakdown
```

### W3 Metrics (Track for Validation)
```sql
-- Deal accuracy
SELECT
  COUNT(*) FILTER (WHERE sold_profitable) * 100.0 / COUNT(*) AS accuracy_pct
FROM deal_backtest_results;

-- User retention
SELECT
  cohort_week,
  COUNT(DISTINCT user_id) FILTER (WHERE weeks_since_signup = 1) AS week_1_retention,
  COUNT(DISTINCT user_id) FILTER (WHERE weeks_since_signup = 4) AS week_4_retention
FROM user_cohorts
GROUP BY cohort_week;
```

### W4 Metrics (Track for Monetization)
```sql
-- MRR
SELECT SUM(price) AS mrr
FROM subscriptions
WHERE status = 'active';

-- Conversion rate
SELECT
  COUNT(*) FILTER (WHERE tier = 'premium') * 100.0 / COUNT(*) AS conversion_pct
FROM users
WHERE created_at > NOW() - INTERVAL '30 days';

-- Churn rate
SELECT
  COUNT(*) FILTER (WHERE canceled_at IS NOT NULL) * 100.0 /
  COUNT(*) AS churn_pct
FROM subscriptions
WHERE started_at < NOW() - INTERVAL '30 days';
```

---

## Immediate Next Actions (This Week)

### Today (30 Jan)
1. ✅ Set zero point baseline (DONE - this document)
2. [ ] Verify EventBridge rules enabled (CloudWatch console)
3. [ ] Calculate metadata coverage % (SQL query)
4. [ ] Review metadata_ingestion Lambda logs (identify bottleneck)

### Tomorrow (31 Jan)
5. [ ] Implement metadata batching optimization (if needed)
6. [ ] Submit SkyMavis rate limit increase request
7. [ ] Deploy changes to compute-stack
8. [ ] Monitor ingestion rate for 24h

### This Week (1-2 Feb)
9. [ ] Validate W1 completion (all exit criteria met)
10. [ ] Wire analytics page to real data
11. [ ] Add error boundaries to frontend pages
12. [ ] Create beta onboarding guide

**Next Waypoint Unlock:** W2 Beta Launch (Est. 7-10 Feb)

---

## Architecture Evolution Path

### Current (W1)
```
Vercel Frontend → App Runner API → Aurora DB
                       ↓
                  EventBridge → Lambdas (9)
```

### Target (W4+)
```
Vercel Frontend → App Runner API → Aurora DB
       ↓               ↓
  WebSocket      ElastiCache Redis
  (Alerts)          (Cache)
                       ↓
                  EventBridge → Lambdas (12+)
                       ↓
                  Kinesis Stream (Events)
```

**New Infrastructure Needed:**
- WebSocket server (for real-time deal alerts) - W4
- ElastiCache Redis (already exists, expand usage) - W3
- Kinesis stream (for event-driven architecture) - W4
- Lambda functions: subscription_manager, usage_tracker, alert_dispatcher - W4

---

## The Creativity Promise

Every development opportunity on this path must:

1. **Connect to existing** - No island features, integrate with current architecture
2. **Enable future** - Design for W5+, not just current waypoint
3. **Serve purpose** - Every feature helps traders profit or make better decisions

**Examples:**
- ✅ Metadata rate limiting fix → Enables accurate valuations → Core value prop
- ✅ Deal backtesting → Proves value hypothesis → Enables W4 monetization
- ✅ Stripe integration → Monetization → Enables W5 sustainable growth
- ❌ Mobile app (W1-W3) → Not core to value prop, defer to W5+

---

## Path Validation Checklist

**Before moving to next waypoint, verify:**

```
W1 → W2:
- [ ] Metadata coverage >80%
- [ ] All Lambdas executing on schedule
- [ ] Zero critical errors in past 48h
- [ ] E2E test passes (search → valuation → deal)

W2 → W3:
- [ ] 10 beta users onboarded
- [ ] 5+ daily active users
- [ ] Critical bugs resolved
- [ ] Feature usage tracked

W3 → W4:
- [ ] Deal accuracy >70% (backtested)
- [ ] 3+ user testimonials
- [ ] 1+ documented profit case
- [ ] Retention >30%

W4 → W5:
- [ ] 50 paying subscribers
- [ ] Stripe integration stable
- [ ] Churn <10%
- [ ] MRR covers costs
```

---

## Summary: The Path Ahead

**Current Position:** W1 at 75% - One critical blocker (metadata rate limiting)

**Immediate Goal:** Complete W1 in 2-3 days → Ready for beta users

**6-Month Vision:** W4 complete - 50+ paying subscribers, proven business model

**12-Month Vision:** W5 complete - 200+ subscribers, established community, sustainable growth

**The journey from 75% to monetization:** 4 waypoints, ~4-6 months, purpose-driven development.

Every line of code serves the purpose: **Enable serious Axie traders to identify undervalued opportunities through data-driven insights.**

---

*Path documented: 2026-01-30*
*Based on zero point assessment by Explore agent (a3ab103)*
*Next review: After W1 completion*
