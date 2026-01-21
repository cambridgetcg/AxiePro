# Financial Value Utilization Prompts - Version 2

## Purpose
Optimized prompts for maximizing financial value from AxiePro API data. Refined for **efficiency** while maintaining depth.

**Changes from v1:**
- Added token constraints (max 2000-2500 tokens)
- Table-only output format
- No code blocks or wireframes
- Focus on actionable insights only
- Explicit gap sections

---

## Prompt 1: High-Value Data Combinations (VALUE-DATA-002)

**Category:** Discovery | **Token Budget:** 2500

```
Analyze AxiePro backend data in /backend/src for financial value. Tables only, max 2500 tokens.

REQUIRED TABLES:

1. **Data Combination Matrix** (columns: Source A, Source B, Derived Insight, Financial Value, Use Case)
   - Top 10 highest-value data combinations only
   - Focus on arbitrage, prediction, undervalue detection

2. **Derived Metrics Inventory** (columns: Metric, Formula, Data Sources, Update Freq, User Value)
   - Max 10 most valuable derived metrics
   - Include ROI, value scores, risk metrics

3. **Real-Time Profit Signals** (columns: Signal Type, Trigger Condition, Confidence, Time Sensitivity)
   - Max 5 immediate-action signals

4. **Historical Patterns** (columns: Pattern, Indicator, Lead Time, Expected ROI)
   - Max 5 predictive patterns

CONSTRAINTS:
- No prose explanations
- No data flow diagrams
- No code blocks
- Skip standard metrics (simple averages, counts)
- Focus on unique AxiePro advantages

GAPS: List top 3 missing data combinations that would increase value.
```

---

## Prompt 2: Financial Dashboard Components (DASH-FIN-002)

**Category:** Design | **Token Budget:** 2000

```
Design financial dashboard components for AxiePro. Tables only, max 2000 tokens.

REQUIRED TABLES:

1. **User Segment Metrics** (columns: Segment, Key Metric 1, Key Metric 2, Key Metric 3, Refresh Rate)
   - Traders, Breeders, Collectors, Whales
   - Max 3 metrics per segment

2. **Widget Inventory** (columns: Widget, Purpose, Data Endpoint, Priority, Status)
   - Existing vs missing widgets
   - Max 15 widgets total

3. **Data Refresh Matrix** (columns: Data Type, Current Rate, Optimal Rate, Impact)
   - What needs faster updates

4. **User Flow Actions** (columns: User Type, Goal, Steps, Data Needed)
   - Max 4 critical user flows

CONSTRAINTS:
- No wireframes or ASCII diagrams
- No component code
- Focus on what exists vs what's needed
- Backend endpoint references only

GAPS: List top 3 missing dashboard features with impact.
```

---

## Prompt 3: Profit Detection Enhancement (PROFIT-DETECT-002)

**Category:** Analysis | **Token Budget:** 2500

```
Analyze profit detection in /backend/src/services. Tables only, max 2500 tokens.

REQUIRED TABLES:

1. **Current Deal Algorithm** (columns: Component, Current Value, Data Source, Accuracy)
   - Thresholds, calculations, confidence levels
   - Max 8 key parameters

2. **Proposed Profit Signals** (columns: Signal, Implementation Complexity, Expected Value, Priority)
   - Breeding ROI, meta shift, whale tracking, arbitrage
   - Max 6 new signals

3. **Ranking Algorithm Spec** (columns: Factor, Weight, Calculation, Threshold)
   - Profit potential, time sensitivity, confidence, capital efficiency
   - Max 6 ranking factors

4. **False Positive Filters** (columns: Filter Type, Detection Method, Reduction %)
   - Wash trading, manipulation, outliers
   - Max 5 filters

CONSTRAINTS:
- No pseudo-code
- No implementation details
- Focus on specs and thresholds only
- Skip obvious validations

GAPS: List top 3 accuracy improvements needed.
```

---

## Prompt 4: Monetization Quick Analysis (MONETIZE-002)

**Category:** Strategy | **Token Budget:** 2000

```
Analyze monetization opportunities for AxiePro. Tables only, max 2000 tokens.

REQUIRED TABLES:

1. **Feature Tier Matrix** (columns: Feature, Free, Pro ($10/mo), Enterprise ($500/mo))
   - Max 12 features
   - Focus on data/analytics features

2. **Pricing Model Comparison** (columns: Model, Pros, Cons, Recommended For)
   - Freemium, usage-based, flat subscription
   - Max 4 models

3. **Competitive Moat** (columns: Advantage, Barrier Height, Competitor Gap)
   - What's defensible
   - Max 5 advantages

4. **Partnership Opportunities** (columns: Partner Type, Revenue Model, Effort, Impact)
   - Max 6 high-value partnerships

CONSTRAINTS:
- No financial projections
- No implementation roadmaps
- Focus on strategy decisions only
- Skip obvious partnerships (ads, affiliates)

GAPS: List top 3 untapped revenue streams.
```

---

## Prompt 5: Risk Metrics Summary (RISK-MGT-002)

**Category:** Analysis | **Token Budget:** 2000

```
Define risk metrics for Axie traders using /backend/src data. Tables only, max 2000 tokens.

REQUIRED TABLES:

1. **Risk Taxonomy** (columns: Risk Category, Sub-Risks, Impact Level, Mitigation Available)
   - Price, liquidity, concentration, meta, platform
   - Max 5 categories, 2-3 sub-risks each

2. **Computable Metrics** (columns: Metric, Formula, Data Source, Threshold, Alert Type)
   - Volatility, DTS, concentration, meta shift
   - Max 10 key metrics

3. **Alert Triggers** (columns: Alert, Condition, Severity, User Action)
   - Max 6 critical alerts

4. **Risk Communication** (columns: Risk Level, Color, Icon, Message Pattern)
   - How to display risk to users
   - Max 5 levels

CONSTRAINTS:
- No UI mockups
- No decision trees
- Focus on metrics and thresholds only
- Skip obvious risk descriptions

GAPS: List top 3 risk metrics that can't be computed with current data.
```

---

## Efficiency Guidelines

### Token Efficiency Targets
| Output Type | Max Tokens | Target Rows |
|-------------|-----------|-------------|
| Tables | 2000-2500 | 30-40 total |
| Gaps section | 200 | 3-5 items |

### What to Skip
- Prose explanations
- Code examples
- Wireframes/diagrams
- Implementation details
- Obvious/standard patterns

### What to Include
- Actionable specs
- Specific thresholds
- Data source references
- Priority rankings
- Gap identification

---

## Assessment Criteria (v2 targets)

| Attribute | v1 Score | v2 Target | Improvement Strategy |
|-----------|----------|-----------|---------------------|
| CD | 5.0 | 5.0 | Maintain depth |
| CB | 5.0 | 4.5+ | Focus on essentials |
| AC | 5.0 | 5.0 | Maintain |
| AT | 4.5-5.0 | 4.5+ | More specific |
| BC | 4.0-4.5 | 4.5+ | Maintain |
| DA | 5.0 | 5.0 | Maintain |
| CS | 4.5-5.0 | 5.0 | Tables only |
| **EF** | **2.5-3.0** | **4.5+** | **Token limits, tables only** |
| GD | 4.5-5.0 | 4.5+ | Explicit gap sections |
| RP | 4.5 | 4.5+ | Maintain |

**Goal:** All prompts achieve Grade A (4.5+) with 60%+ token reduction

---

*Version 2.0 - Optimized for efficiency*
