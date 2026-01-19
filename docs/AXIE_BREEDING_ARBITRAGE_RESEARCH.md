# Axie Breeding Arbitrage: Research & Mathematical Framework

**Date:** 2025-12-23
**Objective:** Identify breeding opportunities where expected offspring value exceeds breeding costs + opportunity cost of parent value

---

## Executive Summary

Breeding arbitrage in Axie Infinity is a **probabilistic investment decision** where:
- **Input:** Two parent Axies + breeding costs (SLP, AXS, gas)
- **Output:** One offspring with uncertain genetic composition
- **Opportunity:** Parents with "hidden value" in recessive genes that can produce premium offspring

This document presents a comprehensive framework combining:
1. **Mendelian Genetics** - Probability calculations for gene inheritance
2. **Real Options Theory** - Valuing breeding flexibility as an option
3. **Monte Carlo Simulation** - Estimating offspring value distributions
4. **Kelly Criterion** - Optimal capital allocation across breeding pairs
5. **Stochastic Dominance** - Comparing breeding opportunities without full utility specification

---

## Part 1: Axie Genetics Fundamentals

### 1.1 Gene Structure

Each Axie has **6 body parts**, each with **3 genes**:

| Gene Type | Symbol | Visual Expression | Inheritance Probability |
|-----------|--------|-------------------|------------------------|
| Dominant | D | Visible on Axie | 37.5% |
| Recessive 1 | R1 | Hidden | 9.375% |
| Recessive 2 | R2 | Hidden | 3.125% |

**Total:** 6 parts × 3 genes = **18 genes per Axie**

### 1.2 Gene Encoding

Genes are stored as 256-bit hex strings. Example:
```
0x500000000a10102414a309441445294a146018c214a5294414a1094a14210948
```

**Decoding Structure:**
```
Bits 0-3:   Class (0-8 mapping to Beast, Bug, Bird, etc.)
Bits 4-255: Part genes in groups of 4 bits each

Per part (6 parts × 12 bits = 72 bits for parts):
  - D gene:  4 bits (part ID)
  - R1 gene: 4 bits
  - R2 gene: 4 bits
```

### 1.3 Inheritance Mechanism

When breeding Parent A × Parent B:

```
For each body part:
    Offspring_D = sample from {A.D, A.R1, A.R2, B.D, B.R1, B.R2}

    Probability distribution:
    ┌─────────────┬─────────────┐
    │  Parent A   │  Parent B   │
    ├─────────────┼─────────────┤
    │ D:  37.5%   │ D:  37.5%   │
    │ R1:  9.375% │ R1:  9.375% │
    │ R2:  3.125% │ R2:  3.125% │
    └─────────────┴─────────────┘
    Total: 100%
```

**Key Insight:** Recessive genes are the "hidden value"—a parent with common dominant parts but rare recessive genes can produce valuable offspring.

### 1.4 Class Inheritance

Offspring class is determined by a **separate probability table**:

| Class Combination | Offspring Probabilities |
|-------------------|------------------------|
| Same class (e.g., Beast × Beast) | 100% same class |
| Different pure (e.g., Beast × Plant) | 50% Beast, 50% Plant |
| With hybrid (e.g., Beast × Mech) | Complex distribution |

**Hybrid Classes:**
- Mech = Beast + Bug
- Dawn = Plant + Bird
- Dusk = Reptile + Aquatic

---

## Part 2: Expected Value Framework

### 2.1 Breeding ROI Formula

**Net Expected Value (NEV) of Breeding:**

```
NEV = E[V_offspring] - C_breeding - ΔV_parents

Where:
- E[V_offspring] = Expected value of offspring (probability-weighted)
- C_breeding = Direct costs (SLP + AXS + gas)
- ΔV_parents = Opportunity cost (breed slot consumption value)
```

### 2.2 Offspring Value Estimation

The offspring value depends on the **realized genotype**:

```
E[V_offspring] = Σ P(genotype_i) × V(genotype_i)
               = Σ P(class_j) × Σ P(parts_k | class_j) × V(class_j, parts_k)
```

**Decomposed:**
```
V(offspring) = V_floor(class) + Σ Premium(part_i)

Where:
- V_floor(class) = Minimum price for that class
- Premium(part_i) = Additional value from having specific part i
```

### 2.3 Joint Probability for Multiple Parts

Using the **product rule** for independent part inheritance:

```
P(specific_combination) = ∏ P(part_i = desired)
                        = P(eyes) × P(ears) × P(mouth) × P(horn) × P(back) × P(tail)
```

**Example:** Probability of offspring having 4 specific premium parts:
```
P(4_premium) = (0.375 + 0.09375 + 0.03125)^4 × (1-P_premium)^2
             = (0.5)^4 × (0.5)^2  (if each parent has the part in D position)
             = 0.0156 = 1.56%
```

### 2.4 Breeding Cost Structure

| Cost Component | Current Estimate | Notes |
|----------------|------------------|-------|
| SLP Cost | Variable by breed # | Increases with each breed |
| AXS Cost | ~0.5 AXS | Fixed per breed |
| Gas Fee | ~0.001 RON | Negligible |
| **Breed Slot Value** | See formula below | Opportunity cost |

**Breed Slot Opportunity Cost:**
```
ΔV_parent = V(breed_count=n) - V(breed_count=n+1)

Empirical from data:
- Virgin (0→1): ~$0.27 loss (4.71 - 4.44)
- Low (1→2): ~$0.23 loss
- Mid (3→4): ~$3.91 loss (8.96 - 5.05)
- High (6→7): ~$9.64 loss (22.80 - 13.16)
```

---

## Part 3: Real Options Framework

### 3.1 Breeding as a Real Option

Each breeding slot represents a **call option** on potential offspring:

| Option Analog | Breeding Equivalent |
|---------------|---------------------|
| Underlying asset (S) | Expected offspring value |
| Strike price (K) | Breeding cost |
| Time to expiry (T) | Time until next breed available |
| Volatility (σ) | Variance in offspring value |
| Option value (C) | Value of breeding slot |

**Sources:**
- [Real Options Valuation (Wikipedia)](https://en.wikipedia.org/wiki/Real_options_valuation)
- [McKinsey: Real Power of Real Options](https://www.mckinsey.com/capabilities/strategy-and-corporate-finance/our-insights/the-real-power-of-real-options)

### 3.2 Binomial Tree Valuation

For discrete breeding decisions, use a **binomial decision tree**:

```
                    ┌── Premium offspring (P = p_premium)
                    │   Value = V_premium
    Breed Now ──────┤
                    │
                    └── Floor offspring (P = 1 - p_premium)
                        Value = V_floor

    vs.

    Wait / Don't Breed: Value = V_parent (unchanged)
```

**Decision Rule:**
```
Breed if: p_premium × V_premium + (1-p_premium) × V_floor > C_breeding + ΔV_parents
```

**Sources:**
- [Binomial Options Pricing Model (Wikipedia)](https://en.wikipedia.org/wiki/Binomial_options_pricing_model)
- [Using Binomial Decision Trees for Real Options (ResearchGate)](https://www.researchgate.net/publication/220210234_Using_Binomial_Decision_Trees_to_Solve_Real-Option_Valuation_Problems)

### 3.3 Black-Scholes Adaptation

For continuous-time approximation:

```
C = S × N(d₁) - K × e^(-rT) × N(d₂)

Where:
- S = E[V_offspring]
- K = C_breeding
- T = 1 (single breeding event)
- σ = std(V_offspring) / E[V_offspring]
- r = risk-free rate (≈0 for short-term)

d₁ = [ln(S/K) + (r + σ²/2)T] / (σ√T)
d₂ = d₁ - σ√T
```

**Interpretation:** The breeding slot value includes a "time value" component from the optionality to wait for better market conditions or find better breeding partners.

**Sources:**
- [Black-Scholes for Strategic Decisions (McCracken)](https://www.mccrackenalliance.com/blog/black-scholes-model-using-option-pricing-for-strategic-business-decisions)
- [ACCA: Real Options and Black-Scholes](https://www.accaglobal.com/uk/en/student/exam-support-resources/professional-exams-study-resources/p4/technical-articles/investment-appraisal.html)

---

## Part 4: Monte Carlo Simulation

### 4.1 Simulation Framework

Given Parent A and Parent B genomes, simulate N offspring:

```python
def simulate_offspring(parent_a, parent_b, n_simulations=10000):
    """Monte Carlo simulation for offspring value distribution."""

    offspring_values = []

    for _ in range(n_simulations):
        # Simulate each part independently
        offspring_parts = {}
        for part in ['eyes', 'ears', 'mouth', 'horn', 'back', 'tail']:
            # Sample from 6-gene pool with Axie probabilities
            genes = [
                (parent_a[part]['D'], 0.375),
                (parent_a[part]['R1'], 0.09375),
                (parent_a[part]['R2'], 0.03125),
                (parent_b[part]['D'], 0.375),
                (parent_b[part]['R1'], 0.09375),
                (parent_b[part]['R2'], 0.03125),
            ]
            offspring_parts[part] = weighted_sample(genes)

        # Simulate class
        offspring_class = simulate_class(parent_a.class, parent_b.class)

        # Value the offspring using hedonic model
        value = estimate_value(offspring_class, offspring_parts)
        offspring_values.append(value)

    return np.array(offspring_values)
```

### 4.2 Output Metrics

From the simulation distribution:

```python
def breeding_metrics(offspring_values, breeding_cost, parent_opp_cost):
    """Calculate key breeding decision metrics."""

    total_cost = breeding_cost + parent_opp_cost
    net_values = offspring_values - total_cost

    return {
        'expected_value': np.mean(offspring_values),
        'expected_profit': np.mean(net_values),
        'profit_probability': np.mean(net_values > 0),
        'median_profit': np.median(net_values),
        'value_at_risk_5': np.percentile(net_values, 5),  # 5th percentile
        'upside_potential_95': np.percentile(net_values, 95),
        'sharpe_ratio': np.mean(net_values) / np.std(net_values),
        'max_loss': np.min(net_values),
        'max_gain': np.max(net_values),
    }
```

### 4.3 Variance Reduction Techniques

**Stratified Sampling:** Ensure adequate coverage of rare high-value outcomes:

```python
def stratified_simulate(parent_a, parent_b, n_per_stratum=1000):
    """Stratified sampling for rare premium combinations."""

    # Define strata by number of premium parts
    strata = {
        '0_premium': [],
        '1_premium': [],
        '2_premium': [],
        '3+_premium': []
    }

    # Sample within each stratum
    for stratum in strata:
        force_premium_count = int(stratum[0])
        samples = conditional_simulate(parent_a, parent_b,
                                       force_premium=force_premium_count,
                                       n=n_per_stratum)
        strata[stratum] = samples

    # Weight by true probability of each stratum
    # ...
```

**Sources:**
- [Monte Carlo Methods in Genetic Analysis (SpringerLink)](https://link.springer.com/chapter/10.1007/978-1-4612-0751-1_2)
- [Look-Ahead Monte Carlo for Parental Selection (Nature)](https://www.nature.com/articles/s41598-021-83634-x)
- [Predicting Offspring Genetic Variation (Genetics Selection Evolution)](https://link.springer.com/article/10.1186/1297-9686-46-42)

---

## Part 5: Kelly Criterion for Breeding Capital Allocation

### 5.1 Problem Setup

Given limited breeding budget, how much capital to allocate to each breeding opportunity?

**Kelly Formula:**
```
f* = (p × b - q) / b

Where:
- f* = Optimal fraction of capital to bet
- p = Probability of profit
- q = 1 - p = Probability of loss
- b = Odds (profit / loss ratio)
```

**Adapted for Breeding:**
```
f* = [P(profit) × E[profit|profit] - P(loss) × E[loss|loss]] / E[profit|profit]

Or equivalently:
f* = E[R] / σ²(R)  (for continuous returns)

Where R = (V_offspring - C_total) / C_total
```

### 5.2 Fractional Kelly for Risk Management

Full Kelly is **too aggressive** for practical use. Recommended: **25-50% Kelly**

```python
def kelly_allocation(breeding_opportunities, total_budget, kelly_fraction=0.25):
    """Allocate breeding budget using fractional Kelly."""

    allocations = {}

    for pair_id, metrics in breeding_opportunities.items():
        # Calculate full Kelly fraction
        if metrics['profit_probability'] > 0 and metrics['expected_profit'] > 0:
            edge = metrics['expected_profit']
            odds = metrics['upside_potential_95'] / abs(metrics['value_at_risk_5'])
            full_kelly = (metrics['profit_probability'] * odds - (1 - metrics['profit_probability'])) / odds

            # Apply fractional Kelly
            f = max(0, full_kelly * kelly_fraction)
            allocations[pair_id] = f * total_budget
        else:
            allocations[pair_id] = 0

    # Normalize if total exceeds budget
    total_allocated = sum(allocations.values())
    if total_allocated > total_budget:
        scale = total_budget / total_allocated
        allocations = {k: v * scale for k, v in allocations.items()}

    return allocations
```

### 5.3 Kelly Properties Relevant to Breeding

| Property | Implication for Breeding |
|----------|-------------------------|
| Never risks ruin | Always preserves some capital |
| Maximizes log wealth | Optimal for compounding breeding profits |
| Myopic optimality | Each breeding decision independent |
| High variance | Use fractional Kelly (25-50%) |

**Sources:**
- [Kelly Criterion (Wikipedia)](https://en.wikipedia.org/wiki/Kelly_criterion)
- [Kelly Criterion in Finance (CFA Institute)](https://blogs.cfainstitute.org/investor/2018/06/14/the-kelly-criterion-you-dont-know-the-half-of-it/)
- [Good and Bad Properties of Kelly (Berkeley)](https://www.stat.berkeley.edu/~aldous/157/Papers/Good_Bad_Kelly.pdf)

---

## Part 6: Stochastic Dominance for Pair Comparison

### 6.1 First-Order Stochastic Dominance (FSD)

Breeding pair A **dominates** pair B if:

```
∀v: P(V_A ≥ v) ≥ P(V_B ≥ v)

(And strict inequality for at least one v)
```

**Interpretation:** A is preferred by ALL investors regardless of risk preference.

### 6.2 Second-Order Stochastic Dominance (SSD)

For **risk-averse** breeders:

```
∀v: ∫_{-∞}^{v} F_A(x)dx ≤ ∫_{-∞}^{v} F_B(x)dx

Where F_A, F_B are cumulative distribution functions
```

**Interpretation:** A is preferred by all risk-averse investors (prefer same expected value with less variance).

### 6.3 Practical Application

```python
def dominance_comparison(offspring_values_A, offspring_values_B):
    """Check stochastic dominance between two breeding pairs."""

    # Sort values
    A_sorted = np.sort(offspring_values_A)
    B_sorted = np.sort(offspring_values_B)

    # First-order: Compare CDFs at all points
    all_values = np.union1d(A_sorted, B_sorted)

    A_dominates_FSD = True
    B_dominates_FSD = True

    for v in all_values:
        P_A_geq = np.mean(offspring_values_A >= v)
        P_B_geq = np.mean(offspring_values_B >= v)

        if P_A_geq < P_B_geq:
            A_dominates_FSD = False
        if P_B_geq < P_A_geq:
            B_dominates_FSD = False

    # Second-order: Compare integrated CDFs
    # ... (similar logic with cumulative sums)

    return {
        'A_FSD_dominates_B': A_dominates_FSD,
        'B_FSD_dominates_A': B_dominates_FSD,
        'A_SSD_dominates_B': A_dominates_SSD,
        'B_SSD_dominates_A': B_dominates_SSD,
    }
```

**Sources:**
- [Stochastic Dominance (Wikipedia)](https://en.wikipedia.org/wiki/Stochastic_dominance)
- [Stochastic Dominance in Finance (DayTrading.com)](https://www.daytrading.com/stochastic-dominance)
- [Stochastic Dominance Book (SpringerLink)](https://link.springer.com/book/10.1007/0-387-29311-6)

---

## Part 7: Arbitrage Scoring System

### 7.1 Breeding Opportunity Score (BOS)

Combine multiple metrics into a single score:

```
BOS = w₁ × NEV_normalized + w₂ × Sharpe + w₃ × P(profit) + w₄ × Kelly_f

Where:
- NEV_normalized = (E[V_offspring] - C_total) / C_total
- Sharpe = E[profit] / σ(profit)
- P(profit) = Probability of positive net return
- Kelly_f = Optimal Kelly fraction (capped at 0.25)

Suggested weights: w₁=0.3, w₂=0.3, w₃=0.2, w₄=0.2
```

### 7.2 Hidden Value Score (HVS)

Measure "hidden value" in recessive genes:

```
HVS(parent) = Σ [V(R1_part) - V(D_part)] × P(R1_inherited)
            + Σ [V(R2_part) - V(D_part)] × P(R2_inherited)

Where:
- V(part) = Market premium for that part
- P(R1_inherited) = 0.09375
- P(R2_inherited) = 0.03125
```

**High HVS indicates:** Parent has valuable hidden genes not reflected in current price.

### 7.3 Breeding Pair Compatibility Score

```
Compatibility(A, B) = Σ max(V(A.part_i), V(B.part_i)) × P(best_inherited)
                    - Σ |class_mismatch_penalty|
```

### 7.4 Implementation: Arbitrage Scanner

```python
def scan_breeding_arbitrage(available_axies, market_prices, threshold_bos=0.15):
    """Scan for profitable breeding opportunities."""

    opportunities = []

    # Generate all viable pairs
    for axie_a in available_axies:
        for axie_b in available_axies:
            if axie_a.id >= axie_b.id:  # Avoid duplicates
                continue
            if axie_a.breed_count >= 7 or axie_b.breed_count >= 7:
                continue  # Can't breed

            # Simulate offspring distribution
            offspring_values = simulate_offspring(axie_a, axie_b, n=5000)

            # Calculate costs
            breeding_cost = get_breeding_cost(axie_a.breed_count, axie_b.breed_count)
            opp_cost = (breed_slot_value(axie_a.breed_count) +
                        breed_slot_value(axie_b.breed_count))
            total_cost = breeding_cost + opp_cost

            # Calculate metrics
            metrics = breeding_metrics(offspring_values, breeding_cost, opp_cost)

            # Calculate BOS
            nev_norm = metrics['expected_profit'] / total_cost
            bos = (0.3 * nev_norm +
                   0.3 * metrics['sharpe_ratio'] +
                   0.2 * metrics['profit_probability'] +
                   0.2 * min(0.25, kelly_fraction(metrics)))

            if bos > threshold_bos:
                opportunities.append({
                    'parent_a': axie_a.id,
                    'parent_b': axie_b.id,
                    'bos': bos,
                    'expected_profit': metrics['expected_profit'],
                    'profit_probability': metrics['profit_probability'],
                    'best_case': metrics['upside_potential_95'],
                    'worst_case': metrics['value_at_risk_5'],
                })

    return sorted(opportunities, key=lambda x: x['bos'], reverse=True)
```

---

## Part 8: Trend-Adjusted Breeding Strategy

### 8.1 Dynamic Part Valuation

Part values change over time (meta shifts). Incorporate trend signals:

```
V_adjusted(part, t) = V_current(part) × (1 + TrendScore(part) × horizon)

Where:
- TrendScore from valuation model (see AXIE_VALUATION_MODEL_RESEARCH.md)
- horizon = expected time to sell offspring (e.g., 30 days)
```

### 8.2 Forward-Looking Breeding

**Breed for Tomorrow's Meta:**

```python
def forward_looking_value(offspring_parts, days_ahead=30):
    """Estimate offspring value accounting for predicted trend changes."""

    value = 0
    for part in offspring_parts:
        current_value = get_part_premium(part)
        trend = get_trend_score(part)

        # Adjust for expected price change
        expected_value = current_value * (1 + trend * days_ahead / 365)

        # Discount for uncertainty
        uncertainty_discount = 0.1 * abs(trend)  # Higher trend = more uncertain
        adjusted_value = expected_value * (1 - uncertainty_discount)

        value += adjusted_value

    return value
```

### 8.3 Regime-Aware Breeding

Detect market regimes and adjust strategy:

| Regime | Indicator | Breeding Strategy |
|--------|-----------|-------------------|
| Bull Market | Rising floor prices, high volume | Aggressive breeding, target premium |
| Bear Market | Falling floors, low volume | Conservative, breed only high-certainty |
| Meta Shift | Specific parts trending | Target trending parts |
| Stable | Low volatility | Standard expected value optimization |

---

## Part 9: Risk Management

### 9.1 Portfolio Approach to Breeding

Don't put all eggs in one basket:

```
Portfolio_Variance = Σᵢ Σⱼ wᵢ wⱼ Cov(Rᵢ, Rⱼ)

Where:
- wᵢ = Weight (capital allocated) to breeding pair i
- Rᵢ = Return from breeding pair i
- Cov(Rᵢ, Rⱼ) = Covariance of returns
```

**Diversification Strategies:**
1. **Class diversification:** Breed across multiple classes
2. **Part diversification:** Target different meta parts
3. **Time diversification:** Spread breeding over time

### 9.2 Stop-Loss Rules

```python
def should_continue_breeding(breeding_history, params):
    """Determine if breeding program should continue or pause."""

    recent_profits = breeding_history[-params['lookback']:]

    # Cumulative loss threshold
    if sum(recent_profits) < -params['max_drawdown']:
        return False, "Max drawdown exceeded"

    # Win rate threshold
    win_rate = sum(1 for p in recent_profits if p > 0) / len(recent_profits)
    if win_rate < params['min_win_rate']:
        return False, "Win rate too low"

    # Sharpe threshold
    if np.mean(recent_profits) / np.std(recent_profits) < params['min_sharpe']:
        return False, "Risk-adjusted returns too low"

    return True, "Continue"
```

### 9.3 Hedging Strategies

1. **Sell parents after breeding:** Lock in value, remove breed slot risk
2. **Short correlated assets:** If possible, short AXS/SLP to hedge market risk
3. **Pair with floor sweeping:** Buy undervalued floor Axies while breeding premium

---

## Part 10: Implementation Roadmap

### Phase 1: Data Infrastructure (Week 1-2)
- [ ] Parse gene hex strings into structured format
- [ ] Build part → value lookup tables from sales data
- [ ] Create breed count → opportunity cost model
- [ ] Store historical breeding costs (SLP/AXS prices)

### Phase 2: Probability Engine (Week 3-4)
- [ ] Implement gene inheritance probability calculator
- [ ] Build class inheritance probability matrix
- [ ] Create Monte Carlo offspring simulator
- [ ] Validate against known breeding outcomes

### Phase 3: Valuation Integration (Week 5-6)
- [ ] Integrate hedonic pricing model for offspring valuation
- [ ] Implement real options breeding slot valuation
- [ ] Build forward-looking trend adjustments
- [ ] Create BOS (Breeding Opportunity Score) calculator

### Phase 4: Optimization (Week 7-8)
- [ ] Implement Kelly criterion capital allocation
- [ ] Build stochastic dominance comparison
- [ ] Create portfolio optimization across pairs
- [ ] Develop breeding queue prioritization

### Phase 5: Production System (Week 9-10)
- [ ] Real-time arbitrage scanner
- [ ] Alert system for high-BOS opportunities
- [ ] Backtesting framework
- [ ] Risk management dashboard

---

## Part 11: Mathematical Appendix

### A.1 Gene Inheritance Probability Matrix

For a single part with parents having genes (D_A, R1_A, R2_A) and (D_B, R1_B, R2_B):

```
P(offspring_D = g) =
    0.375    if g ∈ {D_A, D_B}
    0.09375  if g ∈ {R1_A, R1_B}
    0.03125  if g ∈ {R2_A, R2_B}
```

### A.2 Expected Value of Breeding (Detailed)

```
E[V] = Σ_{c∈Classes} P(class=c) × Σ_{p∈Parts^6} P(parts=p|class=c) × V(c, p)

Where:
- Classes = {Beast, Bug, Bird, Plant, Aquatic, Reptile, Mech, Dawn, Dusk}
- Parts^6 = Cartesian product of possible parts for each slot
- V(c, p) = V_floor(c) + Σᵢ Premium(pᵢ)
```

### A.3 Kelly Criterion Derivation for Breeding

Maximize expected log wealth:

```
max E[ln(W₁)] = max E[ln(W₀ × (1 + f × R))]
             = ln(W₀) + E[ln(1 + f × R)]

Taking derivative w.r.t. f and setting to 0:
E[R / (1 + f × R)] = 0

For binary outcome (profit p with prob π, loss l with prob 1-π):
f* = (π × p - (1-π) × l) / (p × l)
   = (π/l) - ((1-π)/p)
```

### A.4 Binomial Tree for Breeding Decision

```
         t=0                t=1 (after breeding)
                           ┌─── V_premium × P_premium
                          /
    V_parents ──[Breed]──┤
                          \
                           └─── V_floor × (1-P_premium)
         │
         │
    [Don't Breed] ─────────── V_parents (unchanged)

Decision: Breed if E[V_offspring] - C_breeding > ΔV_parents
```

---

## Part 12: Key Literature References

### Genetics & Probability
1. [Punnett Square Guide (PunnettSquare.org)](https://punnettsquare.org/topics/punnett-square-guide/)
2. [Probabilities in Genetics (Khan Academy)](https://www.khanacademy.org/science/ap-biology/heredity/mendelian-genetics-ap/a/probabilities-in-genetics)
3. [Conditional Probability in Genetics (Biology LibreTexts)](https://bio.libretexts.org/Workbench/Modern_Genetics/03:_Genotype_and_Phenotype_I_-_Monogenic_Traits/3.04:_Conditional_Probability_Bayes_Rule_and_Genetic_Testing)
4. [Monte Carlo Methods in Genetic Analysis (SpringerLink)](https://link.springer.com/chapter/10.1007/978-1-4612-0751-1_2)

### Finance & Options
5. [Real Options Valuation (Wikipedia)](https://en.wikipedia.org/wiki/Real_options_valuation)
6. [Black-Scholes Model (Wikipedia)](https://en.wikipedia.org/wiki/Black–Scholes_model)
7. [Binomial Options Pricing (Wikipedia)](https://en.wikipedia.org/wiki/Binomial_options_pricing_model)
8. [Kelly Criterion (Wikipedia)](https://en.wikipedia.org/wiki/Kelly_criterion)

### Decision Theory
9. [Stochastic Dominance (Wikipedia)](https://en.wikipedia.org/wiki/Stochastic_dominance)
10. [Expected Return (Corporate Finance Institute)](https://corporatefinanceinstitute.com/resources/career-map/sell-side/capital-markets/expected-return/)

### Monte Carlo & Simulation
11. [Look-Ahead Monte Carlo for Parental Selection (Nature)](https://www.nature.com/articles/s41598-021-83634-x)
12. [Predicting Offspring Genetic Variation (Genetics Selection Evolution)](https://link.springer.com/article/10.1186/1297-9686-46-42)

---

## Part 13: SQL Queries for Breeding Analysis

```sql
-- Find high Hidden Value Score (HVS) parents
-- Parents with common dominant parts but potentially valuable recessives
WITH part_values AS (
    SELECT
        m.part_mouth,
        AVG(s.price_usd) as avg_price,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY s.price_usd) as median_price
    FROM axie.axie_sales s
    JOIN axie.axie_metadata m ON s.axie_id = m.axie_id
    WHERE s.price_usd BETWEEN 1 AND 500
    GROUP BY m.part_mouth
    HAVING COUNT(*) >= 30
)
SELECT
    m.axie_id,
    m.class,
    m.breed_count,
    m.part_mouth,
    pv.median_price as mouth_value,
    -- Would need gene parsing to get R1/R2 values
    s.price_usd as current_price
FROM axie.axie_metadata m
JOIN axie.axie_sales s ON m.axie_id = s.axie_id
JOIN part_values pv ON m.part_mouth = pv.part_mouth
WHERE m.breed_count < 4  -- Still has breeding potential
ORDER BY pv.median_price DESC;

-- Breeding cost analysis by breed count
SELECT
    m.breed_count,
    COUNT(*) as sample_size,
    AVG(s.price_usd) as avg_price,
    AVG(s.price_usd) - LAG(AVG(s.price_usd)) OVER (ORDER BY m.breed_count) as breed_slot_value
FROM axie.axie_sales s
JOIN axie.axie_metadata m ON s.axie_id = m.axie_id
WHERE s.price_usd BETWEEN 1 AND 100
GROUP BY m.breed_count
ORDER BY m.breed_count;
```

---

## Appendix: Current Data Assets

| Metric | Value |
|--------|-------|
| Total Axies with genes | 49,415 |
| Axies with parts data | 49,415 |
| Virgin Axies (breed=0) | 17,033 |
| Average breed count | 1.7 |
| Total sales records | 122,188 |

**Gene format:** 256-bit hex string encoding class + 18 genes (D/R1/R2 × 6 parts)

---

*Document prepared for AxiePro breeding arbitrage system development.*
