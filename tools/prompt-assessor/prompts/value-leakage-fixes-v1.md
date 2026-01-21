# Value Leakage Fix Prompts - Version 1

## Purpose
Implementation-focused prompts to seal identified value leakage points in AxiePro's financial value extraction framework.

**Target Leakage Points:**
1. No cost-basis tracking (HIGH)
2. Portfolio aggregation missing (HIGH)
3. Meta shifts not exposed (HIGH)
4. Deal scoring not normalized (MEDIUM)
5. Part statistics incomplete (MEDIUM)

---

## Prompt 1: Portfolio P&L Implementation (FIX-PORTFOLIO-001)

**Category:** Implementation | **Token Budget:** 2000

```
Design portfolio P&L tracking for AxiePro. Analyze /backend/src/models and /backend/src/api/routes. Tables only, max 2000 tokens.

REQUIRED TABLES:

1. **Schema Changes** (columns: Table, Field, Type, Purpose)
   - New fields for WalletHolding model
   - Cost basis, acquisition date, realized/unrealized P&L

2. **API Endpoints** (columns: Method, Path, Request, Response, Priority)
   - Portfolio summary, holdings detail, P&L history
   - Max 5 endpoints

3. **Calculation Logic** (columns: Metric, Formula, Data Sources)
   - Total value, unrealized P&L, ROI %, CAGR
   - Max 6 metrics

4. **Implementation Steps** (columns: Step, File, Change, Effort)
   - Ordered implementation checklist
   - Max 8 steps

CONSTRAINTS:
- Use existing WalletHolding model
- Leverage hedonic valuation for current value
- No new external dependencies
```

---

## Prompt 2: Meta Shifts API Exposure (FIX-META-001)

**Category:** Implementation | **Token Budget:** 1500

```
Design meta shifts API exposure for AxiePro. Analyze /backend/src/lambdas/meta_analyzer.py and /backend/src/api/routes. Tables only, max 1500 tokens.

REQUIRED TABLES:

1. **Endpoint Design** (columns: Method, Path, Parameters, Response Schema)
   - Expose existing meta shift signals
   - Max 3 endpoints

2. **Response Structure** (columns: Field, Type, Description, Source)
   - Meta shift payload definition
   - Max 10 fields

3. **Caching Strategy** (columns: Key Pattern, TTL, Invalidation)
   - Redis caching for meta data

4. **Implementation Steps** (columns: Step, File, Change)
   - Max 6 steps

CONSTRAINTS:
- Expose EXISTING meta_analyzer signals (don't create new logic)
- Use existing Redis cache patterns
- Follow existing API conventions
```

---

## Prompt 3: Normalized Deal Scoring (FIX-DEALS-001)

**Category:** Implementation | **Token Budget:** 1500

```
Design normalized deal scoring for AxiePro. Analyze /backend/src/lambdas/deal_detector.py. Tables only, max 1500 tokens.

REQUIRED TABLES:

1. **Current vs Proposed Scoring** (columns: Component, Current, Proposed, Improvement)
   - How scoring changes

2. **Normalization Algorithm** (columns: Factor, Weight, Calculation, Range)
   - Multi-factor scoring: discount %, confidence, liquidity, time
   - Percentile-based normalization

3. **Score Tiers** (columns: Score Range, Label, Color, Action)
   - User-friendly tier system
   - Max 5 tiers

4. **Implementation Steps** (columns: Step, File, Change)
   - Max 5 steps

CONSTRAINTS:
- Backward compatible with existing deal_score field
- Add normalized_score as new field
- Keep existing thresholds working
```

---

## Prompt 4: Cost-Basis Tracking (FIX-COSTBASIS-001)

**Category:** Implementation | **Token Budget:** 1500

```
Design cost-basis tracking for AxiePro. Analyze /backend/src/models/wallet.py. Tables only, max 1500 tokens.

REQUIRED TABLES:

1. **Schema Changes** (columns: Model, Field, Type, Default, Purpose)
   - WalletHolding additions
   - Max 6 new fields

2. **Acquisition Detection** (columns: Event, Source, Fields Captured)
   - How to detect and record acquisitions
   - Purchase, breeding, transfer

3. **P&L Calculations** (columns: Metric, Formula, When Calculated)
   - Cost basis methods (FIFO, avg cost)
   - Max 5 calculations

4. **Migration Strategy** (columns: Step, Action, Risk)
   - Backfill existing holdings
   - Max 4 steps

CONSTRAINTS:
- Non-breaking migration
- Support multiple cost-basis methods
- Handle missing historical data gracefully
```

---

## Prompt 5: Complete Part Statistics (FIX-PARTS-001)

**Category:** Implementation | **Token Budget:** 1500

```
Design complete part statistics for AxiePro. Analyze /backend/src/services/valuation. Tables only, max 1500 tokens.

REQUIRED TABLES:

1. **Current Gap Analysis** (columns: Part Position, Currently Tracked, Missing, Impact)
   - Which parts are sampled vs full coverage

2. **Schema Enhancement** (columns: Table, Field, Type, Index)
   - Part-level price tracking
   - Max 5 additions

3. **Collection Strategy** (columns: Part Type, Data Source, Update Frequency)
   - How to capture all 6 part positions
   - Eyes, ears, mouth, horn, back, tail

4. **Implementation Steps** (columns: Step, File, Change, Priority)
   - Max 6 steps

CONSTRAINTS:
- Extend existing trait_statistics
- Use existing SkyMavis API
- Prioritize high-impact parts first
```

---

## Assessment Criteria

| Attribute | Target |
|-----------|--------|
| Actionability (AT) | 5.0 - Ready to implement |
| Accuracy (AC) | 5.0 - Correct file/model references |
| Efficiency (EF) | 4.5+ - Concise specs |
| Domain Alignment (DA) | 5.0 - Axie-specific |

---

*Version 1.0 - Implementation-focused prompts*
