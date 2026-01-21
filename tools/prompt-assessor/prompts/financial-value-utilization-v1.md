# Financial Value Utilization Prompts - Version 1

## Purpose
Prompts for analyzing how to maximize financial value from AxiePro's available API data, presented through the website to help users make profitable decisions in the Axie Infinity marketplace.

---

## Prompt 1: High-Value Data Combinations (VALUE-DATA-001)

**Category:** Discovery
**Target:** Identifying data synergies for financial insights

```
Analyze the AxiePro backend data sources in /backend/src to identify:

1. What data combinations create the highest financial value for users?
   - Which API endpoints, when combined, reveal arbitrage opportunities?
   - What data pairs enable better price predictions?
   - Which metrics together indicate undervalued Axies?

2. What derived metrics can be computed from existing data?
   - ROI calculations from breeding data + market prices
   - Value scores from genes + current floor prices
   - Risk metrics from price volatility + volume

3. What real-time signals indicate immediate profit opportunities?
   - Price drops below historical patterns
   - Listings significantly below valuation
   - Meta shifts creating demand spikes

4. What historical patterns predict future value?
   - Seasonal price trends
   - Meta evolution cycles
   - Whale accumulation signals

Output as:
- Data combination matrix (source A + source B = insight)
- Derived metrics inventory with formulas
- Real-time signal definitions
- Pattern indicators table
```

---

## Prompt 2: User Financial Dashboard Design (DASH-FIN-001)

**Category:** Design
**Target:** Website presentation for maximum user value

```
Based on the AxiePro frontend in /frontend/src and backend APIs, design financial dashboards:

1. What key financial metrics should users see first?
   - Portfolio value and P&L tracking
   - Market opportunity scores
   - Risk/reward indicators

2. How should data be visualized for quick decisions?
   - Price charts with entry/exit signals
   - Heat maps for class/part opportunities
   - Alert systems for deals

3. What user segments need different dashboard views?
   - Traders (quick flips, arbitrage)
   - Breeders (ROI optimization)
   - Collectors (value appreciation)
   - Whales (portfolio management)

4. What interactive features maximize engagement?
   - Custom alert configurations
   - Portfolio simulation tools
   - Watchlist with price targets

Deliver:
- Dashboard wireframe descriptions per user segment
- Component hierarchy for financial widgets
- Data refresh requirements per widget
- User flow for key actions (buy signal → purchase)
```

---

## Prompt 3: Profit Opportunity Detection (PROFIT-DETECT-001)

**Category:** Analysis
**Target:** Algorithms for finding profitable opportunities

```
Examine the AxiePro services in /backend/src/services to define profit detection:

1. What constitutes a "deal" in the current implementation?
   - How is discount percentage calculated?
   - What thresholds trigger deal alerts?
   - How accurate are current valuations?

2. What additional profit signals could be implemented?
   - Breeding pair profitability scoring
   - Meta shift early detection
   - Whale movement tracking
   - Cross-market arbitrage

3. How should opportunities be ranked for users?
   - Expected profit margin
   - Time sensitivity (how fast will it sell?)
   - Confidence score (how reliable is the signal?)
   - Capital required

4. What false positive filters are needed?
   - Wash trading detection
   - Manipulation pattern recognition
   - Outlier price filtering

Produce:
- Current deal detection algorithm breakdown
- Proposed profit signals with implementation complexity
- Ranking algorithm specification
- Filter rules for signal quality
```

---

## Prompt 4: Monetization Strategy Analysis (MONETIZE-001)

**Category:** Strategy
**Target:** Revenue opportunities from data

```
Analyze AxiePro's data assets for monetization potential:

1. What data/features justify premium subscriptions?
   - Real-time vs delayed alerts
   - Advanced analytics vs basic metrics
   - API access tiers
   - Portfolio limits

2. What pricing models fit the user base?
   - Freemium with upgrade triggers
   - Usage-based (alerts per month)
   - Performance-based (% of profits)
   - Flat subscription tiers

3. What competitive advantages does the data provide?
   - Unique data sources
   - Proprietary algorithms
   - Speed advantages
   - Accuracy metrics

4. What partnerships could enhance value?
   - Data licensing opportunities
   - Affiliate programs with marketplaces
   - Integration partnerships

Output:
- Feature tier matrix (Free/Pro/Enterprise)
- Pricing model comparison with pros/cons
- Competitive moat analysis
- Partnership opportunity list
```

---

## Prompt 5: Risk Management Features (RISK-MGT-001)

**Category:** Analysis
**Target:** Protecting user capital

```
Define risk management features using AxiePro data:

1. What risks do Axie traders face?
   - Price volatility and flash crashes
   - Liquidity risk (can't sell)
   - Meta shifts devaluing holdings
   - Smart contract/platform risks

2. What risk metrics can be computed from available data?
   - Volatility indicators per class/part
   - Liquidity scores (time to sell)
   - Concentration risk in portfolios
   - Historical drawdown patterns

3. What protective features should be offered?
   - Stop-loss alerts
   - Portfolio diversification warnings
   - Overexposure notifications
   - Market sentiment indicators

4. How should risk be communicated to users?
   - Risk scores (1-10 scale)
   - Visual risk indicators
   - Contextual warnings
   - Educational content triggers

Deliver:
- Risk taxonomy for Axie trading
- Computable risk metrics with data sources
- Feature specifications for risk tools
- UI/UX patterns for risk communication
```

---

## Usage Notes

- Run each prompt using Task agent with Explore subtype
- Assess using prompt-assessor framework
- Target: All prompts Grade A (4.5+)
- Focus on actionable financial insights

## Assessment Checklist

| Attribute | Weight | Target |
|-----------|--------|--------|
| Comprehension Depth (CD) | 15% | 4.5+ |
| Coverage Breadth (CB) | 12% | 4.5+ |
| Accuracy (AC) | 15% | 5.0 |
| Actionability (AT) | 12% | 4.5+ |
| Bridging Capability (BC) | 10% | 4.0+ |
| Domain Alignment (DA) | 10% | 5.0 |
| Clarity & Structure (CS) | 8% | 4.5+ |
| Efficiency (EF) | 8% | 4.0+ |
| Gap Detection (GD) | 5% | 4.0+ |
| Reproducibility (RP) | 5% | 4.5+ |

---

*Version 1.0 - Initial prompts for financial value assessment*
