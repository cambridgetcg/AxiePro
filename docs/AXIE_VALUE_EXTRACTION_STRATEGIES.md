# Axie Ecosystem Value Extraction Strategies

> Historical exploration. All acquisition, conversion, revenue, pricing and growth targets in this document are retired. They are not requirements or an active launch plan; see [the current orientation](../PRICING.md). Research and factual technical evidence remain available.

**Date:** 2025-12-23
**Objective:** Comprehensive brainstorm of methods to extract value from the Axie marketplace and ecosystem beyond simple buy-low-sell-high trading.

---

## Executive Summary

This document catalogs **15+ distinct strategies** for extracting value from the Axie ecosystem, organized into categories:

1. **Trading Strategies** - Direct market participation
2. **Information Arbitrage** - Data-driven edge
3. **Behavioral Exploitation** - Leveraging human biases
4. **Ecosystem Arbitrage** - Cross-platform and cross-asset opportunities
5. **Infrastructure Plays** - Building tools and services
6. **Risk Arbitrage** - Exploiting mispricings in risk

Each strategy includes theoretical framework, implementation approach, and relevant academic/industry research.

---

## Part 1: Trading Strategies

### 1.1 Market Making & Liquidity Provision

**Concept:** Profit from bid-ask spread by providing liquidity to thin markets.

**How It Works:**
```
Profit = (Ask Price - Bid Price) × Volume - Inventory Risk

Strategy:
1. Post buy orders (bids) below market
2. Post sell orders (asks) above market
3. Profit from spread when both sides fill
4. Manage inventory to avoid directional exposure
```

**Axie Application:**
- Focus on liquid classes (Plant, Aquatic, Beast)
- Set spread based on volatility: `Spread = k × σ_daily`
- Use hedonic model to set fair mid-price

**Challenges:**
- Inventory risk if market moves against you
- Competition from other market makers
- Execution latency on blockchain

**Expected Return:** 0.5-2% per transaction, 10-50% annualized

**Research:**
- NFT AMMs like Sudoswap use bonding curves
- NFTX creates fungible tokens backed by NFT vaults

---

### 1.2 Statistical Arbitrage (Pairs Trading)

**Concept:** Exploit mean-reverting price relationships between correlated assets.

**Mathematical Framework:**
```
Spread_t = ln(P_A,t) - β × ln(P_B,t)

If Spread_t > μ + 2σ: Short A, Long B
If Spread_t < μ - 2σ: Long A, Short B
Close when Spread → μ
```

**Cointegration Test (Engle-Granger):**
```python
from statsmodels.tsa.stattools import coint

# Test if two class floor prices are cointegrated
score, pvalue, _ = coint(beast_floors, plant_floors)
if pvalue < 0.05:
    print("Cointegrated - suitable for pairs trading")
```

**Axie Pairs to Test:**
| Pair A | Pair B | Rationale |
|--------|--------|-----------|
| Beast | Mech | Mech is Beast hybrid |
| Plant | Dawn | Dawn is Plant hybrid |
| Aquatic | Dusk | Dusk is Aquatic hybrid |
| Bird floor | Bug floor | Similar market dynamics |

**Expected Return:** 5-15% per trade, Sharpe > 1.0

---

### 1.3 Mean Reversion on Individual Axies

**Concept:** Axies that sell below their hedonic fair value tend to revert.

**Strategy:**
```
Z-score = (P_listing - FMV) / σ_FMV

Buy if Z < -2.0 (significantly undervalued)
Sell if Z > +1.5 (fairly valued or above)

Expected profit = |Z| × σ_FMV × (reversion rate)
```

**From Current Data Analysis:**
- 78% of Axies sell between $2-10
- Median: ~$4.50
- Outlier opportunities exist in tails

---

### 1.4 Momentum Trading

**Concept:** "Trend is your friend" - ride price movements.

**Indicators:**
```
# Moving Average Crossover
Signal = +1 if EMA_7 > EMA_21 else -1

# RSI (Relative Strength)
RSI = 100 - (100 / (1 + avg_gain/avg_loss))
Overbought if RSI > 70, Oversold if RSI < 30

# Part-specific momentum
Part_momentum = (Floor_7d - Floor_30d) / Floor_30d
```

**Application:**
- Track momentum by part type
- Enter positions on rising parts before they peak
- Combine with TrendScore from valuation model

---

## Part 2: Information Arbitrage

### 2.1 Whale Wallet Tracking

**Concept:** Monitor large traders' activity for alpha signals.

**From Current Data:**
```
Top Whale Sellers (by volume):
Seller                                       | Sales  | Volume
---------------------------------------------|--------|--------
0x094300dacf0eed244664e326d27406f0b90b8809   | 7,054  | $34,135
0x531e58fbf300e34e289afbdf8fe3601b1fbbb895   | 600    | $10,830
0x4a1f7fabef0ca332632dabd1c3604dba0a62b6b2   | 1,109  | $8,443
```

**Implementation:**
```python
def track_whale_activity(whale_addresses):
    """Monitor whale wallets for signals."""

    signals = []
    for addr in whale_addresses:
        # Track recent activity
        recent_buys = get_recent_purchases(addr, days=7)
        recent_sells = get_recent_sales(addr, days=7)

        # Compute net position change by class
        for cls in CLASSES:
            net = sum(b for b in recent_buys if b.class == cls) - \
                  sum(s for s in recent_sells if s.class == cls)

            if abs(net) > THRESHOLD:
                signals.append({
                    'whale': addr,
                    'class': cls,
                    'signal': 'accumulating' if net > 0 else 'distributing',
                    'magnitude': abs(net)
                })

    return signals
```

**Tools & Platforms:**
- Nansen, Arkham Intelligence for wallet labeling
- Custom monitoring via Ronin RPC event subscriptions

---

### 2.2 Sentiment Analysis

**Concept:** Extract trading signals from social media sentiment.

**Research Findings:**
- [Nature (2025)](https://www.nature.com/articles/s41598-025-22426-z): Discord sentiment predicts PFP NFT prices
- Twitter drives 70%+ of NFT marketplace traffic
- Contrarian signals often profitable (extreme bullish → price dip)

**Data Sources:**
| Platform | Signal Type | Latency |
|----------|-------------|---------|
| Discord | Community sentiment | Real-time |
| Twitter/X | Public sentiment | Minutes |
| Reddit | Discussion depth | Hours |
| Telegram | Insider chatter | Real-time |

**Sentiment Score Formula:**
```
Sentiment_t = Σ (Polarity_i × Reach_i × Recency_i)

Where:
- Polarity = VADER/BERT sentiment (-1 to +1)
- Reach = Follower count weight
- Recency = Exponential decay
```

**Trading Integration:**
```
If Sentiment > 2σ (extreme bullish): Contrarian SELL signal
If Sentiment < -2σ (extreme bearish): Contrarian BUY signal
```

---

### 2.3 Event-Driven Trading (Meta Shift Prediction)

**Concept:** Anticipate price moves from game updates and balance patches.

**How Meta Shifts Work:**
- Balance patches change card/part effectiveness
- Tournament results reveal emerging strategies
- New game modes create demand for specific builds

**Sources:**
- [OnlyFarms](https://onlyfarms.gg/wiki/general/meta-shift-in-gaming-meaning): Meta shift definitions
- [QuantifiedStrategies](https://www.quantifiedstrategies.com/event-driven-crypto-trading-leveraging-protocol-upgrades-and-airdrops/): Event-driven crypto trading

**Implementation:**
```python
def meta_shift_detector():
    """Monitor for meta shift signals."""

    signals = []

    # 1. Parse patch notes for balance changes
    patch_notes = fetch_latest_patch_notes()
    buffed_parts = extract_buffed_parts(patch_notes)
    nerfed_parts = extract_nerfed_parts(patch_notes)

    # 2. Track tournament winning builds
    tournament_results = fetch_recent_tournaments()
    trending_builds = analyze_winning_builds(tournament_results)

    # 3. Monitor pro player discussions
    pro_sentiment = analyze_pro_discord()

    # Generate signals
    for part in buffed_parts:
        signals.append({'part': part, 'action': 'BUY', 'reason': 'buffed'})

    for part in nerfed_parts:
        signals.append({'part': part, 'action': 'SELL', 'reason': 'nerfed'})

    return signals
```

**Lead Time:** Patch notes usually announced 24-72 hours before deployment

---

### 2.4 Information Speed Advantage

**Concept:** Faster data processing = earlier signals.

**Infrastructure Requirements:**
```
Data Pipeline:
Ronin RPC → Event Stream → Processing → Signal Generation → Execution

Latency Targets:
- Block detection: < 1 second
- Event parsing: < 100ms
- Signal generation: < 500ms
- Order execution: < 2 seconds
```

**Advantages Over Manual Traders:**
| Metric | Manual | Automated |
|--------|--------|-----------|
| Reaction time | Minutes | Seconds |
| Coverage | 10s of Axies | 1000s |
| Consistency | Variable | 24/7 |
| Emotion | Subject to | Immune |

---

## Part 3: Behavioral Exploitation

### 3.1 Anchoring Bias Exploitation

**Concept:** Exploit sellers' tendency to anchor on irrelevant prices.

**Research:**
- [Wikipedia: Anchoring Effect](https://en.wikipedia.org/wiki/Anchoring_effect)
- [Corporate Finance Institute](https://corporatefinanceinstitute.com/resources/career-map/sell-side/capital-markets/anchoring-bias/)

**Common Anchors in Axie:**
1. **Purchase price** - Sellers anchor to what they paid
2. **Round numbers** - $5, $10, $20, $50
3. **Historical highs** - "It was worth $X once"
4. **Listing clusters** - Following other listings

**From Current Data:**
```
Price Type    | Count  | Percentage
--------------|--------|------------
Round Dollar  | 1,601  | 1.43%
One Decimal   | 20,361 | 18.23%
Non-Round     | 89,726 | 80.34%
```

**Opportunity:** Look for sellers anchored to outdated high prices—they may eventually capitulate and sell below FMV.

**Strategy:**
```python
def find_anchoring_opportunities():
    """Find sellers anchored to outdated prices."""

    opportunities = []

    for listing in active_listings:
        # Check if listing has been active for extended period
        days_listed = (now - listing.created_at).days

        if days_listed > 14:  # Stale listing
            # Calculate FMV
            fmv = estimate_fmv(listing.axie)

            # Check if significantly overpriced
            overpricing = (listing.price - fmv) / fmv

            if overpricing > 0.3:  # 30%+ overpriced
                # High probability of price reduction
                opportunities.append({
                    'listing': listing,
                    'current_price': listing.price,
                    'fmv': fmv,
                    'days_stale': days_listed,
                    'expected_reduction': overpricing * 0.5  # Expect 50% correction
                })

    return opportunities
```

---

### 3.2 Round Number Exploitation

**Concept:** Prices cluster at round numbers due to cognitive ease.

**Strategy:**
```
Buy orders: Place at $X.99 instead of $X.00
Sell orders: Place at $X.01 instead of $X.00

Example:
- Instead of bidding $5.00, bid $5.01 (beat competitors)
- Instead of asking $10.00, ask $9.99 (psychological appeal)
```

**Research:** Round numbers serve as psychological support/resistance levels

---

### 3.3 Loss Aversion Exploitation

**Concept:** Sellers hate realizing losses; creates holding behavior.

**Prospect Theory (Kahneman & Tversky):**
```
V(x) = x^α           if x ≥ 0  (gains)
V(x) = -λ(-x)^β      if x < 0  (losses)

Where λ ≈ 2.25 (loss aversion coefficient)
```

**Implication:** Sellers who bought high will hold too long, eventually panic selling creates opportunities.

**Pattern:**
1. Price drops 20%
2. Anchored sellers refuse to sell at "loss"
3. Price stabilizes (no supply)
4. Eventually sellers capitulate en masse
5. Price drops sharply (panic)
6. **BUY opportunity** at bottom

---

### 3.4 FOMO/Fear Exploitation

**Concept:** Exploit crowd behavior at emotional extremes.

**FOMO (Fear Of Missing Out):**
- Rapid price increases attract late buyers
- Price often overshoots fundamentals
- **Strategy:** Sell into FOMO rallies

**Fear/Panic:**
- Rapid price decreases cause panic selling
- Price often overshoots to downside
- **Strategy:** Buy during panic

**Sentiment Indicators:**
```python
def extreme_sentiment_detector(sentiment_score, price_change_7d):
    """Detect FOMO or Fear conditions."""

    if sentiment_score > 0.8 and price_change_7d > 0.3:
        return 'FOMO', 'SELL'  # Contrarian sell

    if sentiment_score < 0.2 and price_change_7d < -0.2:
        return 'FEAR', 'BUY'  # Contrarian buy

    return 'NEUTRAL', 'HOLD'
```

---

## Part 4: Temporal Arbitrage

### 4.1 Time-of-Day Patterns

**From Current Data Analysis:**

```
Hour (UTC) | Sales | Avg Price | Interpretation
-----------|-------|-----------|---------------
4          | 6,684 | $7.30     | Peak activity (Asia prime time)
8          | 3,923 | $7.17     | Lowest price (Asia sleeping)
17         | 4,899 | $7.83     | Highest price (US afternoon)
21         | 3,761 | $7.68     | Low volume
```

**Strategy:**
- **Buy:** 07:00-09:00 UTC (lowest prices, low competition)
- **Sell:** 15:00-18:00 UTC (US activity, higher prices)

**Expected Edge:** 5-8% price differential between worst and best hours

---

### 4.2 Day-of-Week Patterns

**From Current Data:**

```
Day       | Sales  | Avg Price
----------|--------|----------
Sunday    | 17,007 | $7.67   ← Highest volume
Monday    | 14,822 | $7.60
Tuesday   | 16,189 | $7.46
Wednesday | 17,126 | $7.32   ← Lowest prices
Thursday  | 16,257 | $7.35
Friday    | 15,719 | $7.30   ← Lowest prices
Saturday  | 14,563 | $7.58
```

**Strategy:**
- **Buy:** Wednesday-Friday (lowest prices)
- **Sell:** Sunday-Monday (highest volume/prices)

**Expected Edge:** 4-5% price differential

---

### 4.3 Event Calendar Trading

**Predictable Events:**
| Event | Timing | Expected Impact |
|-------|--------|-----------------|
| Patch releases | ~Monthly | Meta shift, volatility |
| Tournaments | Varies | Demand for meta builds |
| Season endings | Quarterly | Reward distribution, sell pressure |
| New features | Announced | FOMO rallies |

---

## Part 5: Ecosystem Arbitrage

### 5.1 Cross-Marketplace Arbitrage

**Concept:** Same asset, different prices across platforms.

**Marketplaces:**
- Official Axie Marketplace
- Third-party aggregators
- P2P trading (Discord, etc.)

**Strategy:**
```
If Price_A < Price_B - fees:
    Buy on A, Sell on B

Expected profit = Price_B - Price_A - gas_A - gas_B - platform_fees
```

---

### 5.2 Token/NFT Arbitrage

**Concept:** Exploit mispricings between related assets.

**Relationships:**
| Asset A | Asset B | Relationship |
|---------|---------|--------------|
| AXS token | Axie floor | Correlation |
| SLP token | Breeding activity | Demand driver |
| Land floor | Axie demand | Ecosystem health |

**Strategy:** When correlation breaks, bet on reversion.

---

### 5.3 Breeding Cost Arbitrage

**Concept:** When breeding costs < expected offspring value - parent costs.

**Already covered in AXIE_BREEDING_ARBITRAGE_RESEARCH.md**

Key formula:
```
Arbitrage = E[V_offspring] - C_breeding - ΔV_parents
```

---

## Part 6: Distressed Asset Hunting

### 6.1 Liquidation Hunting

**Concept:** Identify forced sellers who must sell quickly at a discount.

**Research:**
- [Corporate Finance Institute](https://corporatefinanceinstitute.com/resources/valuation/forced-sale-value/): Forced sale typically 20-40% below FMV
- Fire sales create cascading price pressure

**Signals of Distressed Seller:**
1. **Bulk listings** - Many Axies listed simultaneously
2. **Rapid price reductions** - Multiple cuts in short period
3. **Below-floor pricing** - Listing below class floor
4. **Short listing duration** - "Need to sell fast"

**Implementation:**
```python
def detect_distressed_sellers():
    """Identify potentially distressed sellers."""

    sellers = {}

    for listing in recent_listings:
        seller = listing.seller

        if seller not in sellers:
            sellers[seller] = {
                'listings': [],
                'price_cuts': 0,
                'below_floor': 0
            }

        sellers[seller]['listings'].append(listing)

        # Track price cuts
        if listing.previous_price and listing.price < listing.previous_price:
            sellers[seller]['price_cuts'] += 1

        # Track below-floor listings
        floor = get_floor_price(listing.axie.class)
        if listing.price < floor * 0.95:
            sellers[seller]['below_floor'] += 1

    # Score distress
    distressed = []
    for seller, data in sellers.items():
        distress_score = (
            len(data['listings']) * 0.3 +
            data['price_cuts'] * 0.4 +
            data['below_floor'] * 0.3
        )

        if distress_score > THRESHOLD:
            distressed.append({
                'seller': seller,
                'score': distress_score,
                'listings': data['listings']
            })

    return distressed
```

**Expected Discount:** 15-30% below FMV

---

### 6.2 Wash Trading Detection (Avoid False Signals)

**Research:**
- [SpringerOpen (2025)](https://jfin-swufe.springeropen.com/articles/10.1186/s40854-025-00766-z): Advanced wash trading detection
- [arXiv (2023)](https://arxiv.org/abs/2305.01543): NFT wash trading detection methods
- [arXiv (2023)](https://arxiv.org/html/2312.12544v2): 6.7% of NFT sales are wash trades but account for >50% volume

**Why It Matters:**
- Wash trades inflate volume and prices artificially
- Can create false signals for momentum strategies
- Buying into wash-traded pumps = buying the top

**Detection Methods:**
1. **Self-trading:** Same wallet on both sides
2. **Circular trading:** A→B→C→A pattern
3. **Benford's Law violation:** Price patterns deviate from natural distribution
4. **Network analysis:** Cluster analysis of transaction graphs

**Implementation:**
```python
def is_likely_wash_trade(sale):
    """Score probability of wash trading."""

    flags = 0

    # Check for self-trading
    if sale.buyer == sale.seller:
        return 1.0  # Definite wash

    # Check for circular patterns
    if has_circular_history(sale.buyer, sale.seller, sale.axie_id):
        flags += 0.5

    # Check price vs Benford's Law
    if violates_benford(sale.price):
        flags += 0.2

    # Check for funding relationship
    if wallets_linked(sale.buyer, sale.seller):
        flags += 0.3

    return min(flags, 1.0)
```

---

## Part 7: Infrastructure & Data Products

### 7.1 Data API Service

**Concept:** Monetize data collection and analysis infrastructure.

**Products:**
| Product | Target User | Pricing Model |
|---------|-------------|---------------|
| Real-time floor prices | Traders | Subscription |
| Historical sales data | Researchers | Per-query |
| Valuation API | Marketplaces | Revenue share |
| Alert service | Collectors | Freemium |

---

### 7.2 Index Products

**Concept:** Create tradeable indices tracking Axie market segments.

**Research:**
- [Bitwise Blue-Chip NFT Index](https://bitwiseinvestments.com/crypto-funds/nft): Index fund model
- NFTX: Fungible tokens backed by NFT vaults

**Index Ideas:**
| Index | Composition | Use Case |
|-------|-------------|----------|
| Axie Floor Index | Floor prices across classes | Market health |
| Meta Index | Top tournament parts | Meta exposure |
| Virgin Index | Breed-0 floor prices | Breeding demand |
| Premium Index | Top 10% by price | High-end market |

---

### 7.3 Automation Tools

**Products to Build:**
1. **Sniping bot** - Auto-buy undervalued listings
2. **Repricing bot** - Auto-adjust listing prices
3. **Portfolio tracker** - P&L and analytics
4. **Breeding optimizer** - Suggest optimal pairs

---

## Part 8: Risk Arbitrage

### 8.1 Volatility Trading

**Concept:** Trade volatility itself, not direction.

**Metrics:**
```
Realized Volatility = σ(daily_returns, 30d)
Implied Volatility = Derived from option-like structures

If Realized > Implied: Sell volatility
If Realized < Implied: Buy volatility
```

**Implementation for Axies:**
- High volatility = wider market making spreads
- Low volatility = tighter spreads, more inventory

---

### 8.2 Correlation Breakdown

**Concept:** When correlations break, arbitrage opportunities appear.

**Normal Correlations:**
- Axie floors ↔ AXS price: ~0.6
- Class floors inter-correlation: ~0.7-0.9
- Volume ↔ Price: ~0.4

**Strategy:**
```python
def correlation_monitor():
    """Alert when correlations deviate."""

    current_corr = calculate_rolling_correlation(days=30)
    historical_corr = calculate_historical_correlation(days=365)

    for pair, corr in current_corr.items():
        z_score = (corr - historical_corr[pair]['mean']) / historical_corr[pair]['std']

        if abs(z_score) > 2:
            print(f"Correlation breakdown: {pair}, z={z_score:.2f}")
            # Bet on reversion to historical correlation
```

---

## Part 9: MEV & Advanced Blockchain Strategies

### 9.1 Front-Running Detection (Defensive)

**Concept:** Detect and avoid being front-run.

**Research:**
- [Ethereum.org: MEV](https://ethereum.org/developers/docs/mev/)
- [arXiv (2024)](https://arxiv.org/html/2411.03327v1): MEV taxonomy and detection

**How Front-Running Works:**
```
1. You submit buy order to mempool
2. Bot sees your order, submits same buy with higher gas
3. Bot's order executes first, price increases
4. Your order executes at worse price (or fails)
5. Bot sells to you at profit
```

**Protection:**
- Use private mempools (Flashbots-style)
- Submit transactions with tight slippage
- Break large orders into smaller chunks

---

### 9.2 Sandwich Attack Awareness

**Pattern:**
```
1. Bot front-runs your buy (price ↑)
2. Your buy executes (price ↑↑)
3. Bot back-runs with sell (profits from both moves)
```

**Mitigation:**
- Use limit orders, not market orders
- Set maximum slippage tolerance
- Trade during low-activity periods

---

## Part 10: Portfolio Construction

### 10.1 Diversification Framework

**Modern Portfolio Theory Applied:**
```
Portfolio_Return = Σ wᵢ × Rᵢ
Portfolio_Variance = Σᵢ Σⱼ wᵢ wⱼ Cov(Rᵢ, Rⱼ)

Optimize: max(Sharpe) = (Portfolio_Return - Rf) / σ_portfolio
```

**Diversification Dimensions:**
1. **Class:** Spread across Beast, Plant, Aquatic, etc.
2. **Price tier:** Mix floor and premium Axies
3. **Strategy:** Combine trading, breeding, holding
4. **Time:** Stagger purchases/sales

---

### 10.2 Kelly-Weighted Portfolio

```python
def optimal_portfolio_weights(opportunities):
    """Calculate Kelly-optimal weights across opportunities."""

    weights = {}
    total_kelly = 0

    for opp in opportunities:
        kelly = calculate_kelly_fraction(opp)
        weights[opp.id] = kelly
        total_kelly += kelly

    # Normalize to sum to 1
    if total_kelly > 1:
        weights = {k: v/total_kelly for k, v in weights.items()}

    # Apply fractional Kelly (25%)
    weights = {k: v * 0.25 for k, v in weights.items()}

    return weights
```

---

## Part 11: Implementation Priority Matrix

| Strategy | Expected Return | Implementation Difficulty | Capital Required | Time to Deploy |
|----------|-----------------|---------------------------|------------------|----------------|
| Mean Reversion | 15-30% | Medium | Low | 2-4 weeks |
| Temporal Arbitrage | 5-10% | Low | Low | 1 week |
| Breeding Arbitrage | 20-50% | High | Medium | 4-6 weeks |
| Whale Tracking | 10-20% | Medium | Low | 2-3 weeks |
| Market Making | 10-30% | High | High | 6-8 weeks |
| Sentiment Analysis | 5-15% | Medium | Low | 3-4 weeks |
| Distressed Hunting | 20-40% | Medium | Medium | 2-3 weeks |
| Event-Driven | 15-25% | Medium | Low | 2-3 weeks |

**Recommended Priority:**
1. Mean Reversion (quick wins, proven approach)
2. Temporal Arbitrage (low effort, consistent)
3. Distressed Hunting (high reward)
4. Breeding Arbitrage (complex but lucrative)

---

## Part 12: Risk Management Framework

### 12.1 Position Limits

```python
MAX_SINGLE_POSITION = 0.10  # 10% of portfolio in one Axie
MAX_CLASS_EXPOSURE = 0.30   # 30% in any single class
MAX_STRATEGY_EXPOSURE = 0.40 # 40% in any single strategy
```

### 12.2 Stop-Loss Rules

```python
INDIVIDUAL_STOP = -0.20  # Sell if down 20%
PORTFOLIO_STOP = -0.15   # Pause all trading if portfolio down 15%
DAILY_LOSS_LIMIT = -0.05 # Stop trading for day if down 5%
```

### 12.3 Drawdown Management

```python
def adjust_for_drawdown(current_drawdown, base_position_size):
    """Reduce position sizes during drawdowns."""

    if current_drawdown > 0.1:
        return base_position_size * 0.5
    elif current_drawdown > 0.05:
        return base_position_size * 0.75
    else:
        return base_position_size
```

---

## Part 13: Key Literature References

### Behavioral Finance
1. [Anchoring Effect (Wikipedia)](https://en.wikipedia.org/wiki/Anchoring_effect)
2. [Britannica: Behavioral Biases](https://www.britannica.com/money/behavioral-biases-in-finance)
3. [CFI: Anchoring Bias](https://corporatefinanceinstitute.com/resources/career-map/sell-side/capital-markets/anchoring-bias/)

### NFT Markets
4. [NFT Wash Trading Detection (SpringerOpen 2025)](https://jfin-swufe.springeropen.com/articles/10.1186/s40854-025-00766-z)
5. [Dark Side of NFTs: Wash Trading (arXiv)](https://arxiv.org/html/2312.12544v2)
6. [NFT Price Prediction via Sentiment (Nature 2025)](https://www.nature.com/articles/s41598-025-22426-z)

### Crypto/DeFi
7. [MEV: Taxonomy and Detection (arXiv 2024)](https://arxiv.org/html/2411.03327v1)
8. [Ethereum.org: MEV](https://ethereum.org/developers/docs/mev/)
9. [Event-Driven Crypto Trading (QuantifiedStrategies)](https://www.quantifiedstrategies.com/event-driven-crypto-trading-leveraging-protocol-upgrades-and-airdrops/)

### Valuation
10. [Forced Sale Value (CFI)](https://corporatefinanceinstitute.com/resources/valuation/forced-sale-value/)
11. [Bitwise NFT Index Fund](https://bitwiseinvestments.com/crypto-funds/nft)

---

## Appendix: SQL Queries for Strategy Implementation

```sql
-- Find potential distressed sellers (multiple recent listings)
SELECT
    seller,
    COUNT(*) as listing_count,
    MIN(price_usd) as lowest_price,
    AVG(price_usd) as avg_price
FROM axie.axie_sales
WHERE block_timestamp > NOW() - INTERVAL '7 days'
GROUP BY seller
HAVING COUNT(*) > 10
ORDER BY listing_count DESC;

-- Temporal pattern analysis
SELECT
    EXTRACT(HOUR FROM block_timestamp) as hour,
    EXTRACT(DOW FROM block_timestamp) as dow,
    AVG(price_usd) as avg_price,
    COUNT(*) as volume
FROM axie.axie_sales
WHERE price_usd BETWEEN 1 AND 100
GROUP BY 1, 2
ORDER BY 1, 2;

-- Detect unusual price movements (potential manipulation)
WITH daily_stats AS (
    SELECT
        DATE(block_timestamp) as date,
        class,
        AVG(price_usd) as avg_price,
        STDDEV(price_usd) as std_price
    FROM axie.axie_sales
    WHERE price_usd BETWEEN 1 AND 100
    GROUP BY 1, 2
)
SELECT
    *,
    (avg_price - LAG(avg_price) OVER (PARTITION BY class ORDER BY date)) /
    LAG(avg_price) OVER (PARTITION BY class ORDER BY date) as pct_change
FROM daily_stats
WHERE ABS(pct_change) > 0.15;  -- 15% daily moves
```

---

*Document prepared for AxiePro value extraction strategy development.*
