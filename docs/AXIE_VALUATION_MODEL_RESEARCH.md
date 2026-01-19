# Axie Fair Market Value Model: Research Plan

**Date:** 2025-12-23
**Objective:** Develop a robust fair market value (FMV) model for Axies to enable value arbitrage detection

---

## Executive Summary

This document outlines a comprehensive research plan for building an Axie valuation model that:
1. **Estimates fair market value** for any Axie based on its characteristics
2. **Detects arbitrage opportunities** when listings deviate significantly from FMV
3. **Captures market trend dynamics** to predict shifts in valuations over time

The approach synthesizes methodologies from **finance**, **economics**, **real estate appraisal**, **machine learning**, and **big data analysis**.

---

## Part 1: Current Data Analysis

### 1.1 Available Data Assets

| Table | Records | Key Fields |
|-------|---------|------------|
| `axie_sales` | 122,188 | price_usd, axie_id, class, block_timestamp, tx_hash |
| `axie_metadata` | 49,415 | class, breed_count, parts_json, pure_part_count, genes, stats |
| `axie_parts` | 0 (pending) | part_id, part_name, part_type, part_class |

### 1.2 Key Data Insights from Current Dataset

#### Price Distribution (Right-Skewed)
```
Range       | Count  | Percentage
------------|--------|------------
$0-2        | 11,853 |  9.70%
$2-5        | 59,772 | 48.90%  ← Mode
$5-10       | 35,368 | 28.93%
$10-20      |  9,142 |  7.48%
$20-50      |  4,540 |  3.71%
$50-100     |    956 |  0.78%
$100-500    |    560 |  0.46%
$500+       |     49 |  0.04%
```

**Insight:** Log-transformation required for regression models due to heavy right skew.

#### Breed Count Impact (Counter-Intuitive)
```
Breed Count | Median Price | Interpretation
------------|--------------|----------------
0 (Virgin)  | $4.44        | Lowest (no breeding history)
1-3         | $4.48-5.05   | Slight premium
4-6         | $8.96-13.16  | Significant premium
7 (Max)     | $22.80       | Highest (proven breeder)
```

**Insight:** Higher breed counts correlate with HIGHER prices, suggesting breeding history signals quality or the Axie has produced valuable offspring.

#### Part Value Premiums
```
Part (Mouth)          | Median Price | Premium vs Floor
----------------------|--------------|------------------
mouth-dark-kiss-2     | $50.35       | 11.2x
mouth-doombringer-2   | $44.42       | 9.9x
mouth-bubble-fish     | $30.40       | 6.8x
Average floor         | $4.50        | 1.0x
```

**Insight:** Specific parts command 10x+ premiums—critical for hedonic model.

#### Purity Paradox
```
Pure Parts | Median Price | Note
-----------|--------------|------
0 (None)   | $5.32        | Premium (cross-class builds)
6 (Pure)   | $4.81        | Standard pure class
```

**Insight:** Low purity can indicate valuable cross-class "meta" builds.

---

## Part 2: Valuation Methodologies

### 2.1 Hedonic Pricing Model (Primary Approach)

**Origin:** Rosen (1974), Real Estate Economics
**Concept:** Decompose asset price into implicit prices of constituent characteristics.

**Mathematical Formulation:**
```
ln(P_i) = α + Σ β_j * X_ij + ε_i

Where:
- P_i = Sale price of Axie i
- X_ij = Characteristic j of Axie i (class, breed_count, parts, purity, etc.)
- β_j = Implicit price (coefficient) of characteristic j
- ε_i = Error term
```

**For Axies, characteristics include:**
- **Categorical:** class (9 levels), each of 6 parts (~50 options each)
- **Numeric:** breed_count (0-7), pure_part_count (0-6), stats (HP, Speed, Skill, Morale)
- **Derived:** is_pure, has_meta_parts, gene_quality

**Recent NFT Research:**
- [Pixels to Prices (arXiv 2024)](https://arxiv.org/abs/2509.24879): 94,039 NFT transactions, 196 image descriptors, mixed-effects hedonic model
- [European Financial Management (2025)](https://onlinelibrary.wiley.com/doi/full/10.1111/eufm.12506): 875,389 art NFT sales, hedonic + repeat-sales regression
- [HackerNoon CryptoPunks Study](https://hackernoon.com/using-hedonic-regression-for-cryptopunks-nft-valuation): Rarity as key hedonic factor

**Implementation Plan:**
1. One-hot encode categorical variables (class, parts)
2. Log-transform price (dependent variable)
3. Fit OLS regression with robust standard errors
4. Use mixed-effects model for panel structure (same Axie sold multiple times)

---

### 2.2 Comparable Sales Approach (Secondary Validation)

**Origin:** Real Estate Appraisal (Fannie Mae Guidelines)
**Concept:** Value = Comparable Sale Price ± Adjustments for Differences

**For Axies:**
```
FMV(target) = Median(P_comparable) + Σ Adjustment_j

Where:
- Comparable set = Same class, similar breed_count (±1), similar parts
- Adjustment_j = Implicit price difference from hedonic model
```

**Sources:**
- [Sales Comparison Approach (Wikipedia)](https://en.wikipedia.org/wiki/Sales_comparison_approach)
- [McKissock Learning](https://www.mckissock.com/blog/appraisal/the-sales-comparison-approach-a-cornerstone-of-real-estate-appraisal/)
- [Fannie Mae B4-1.3-09](https://selling-guide.fanniemae.com/sel/b4-1.3-09/adjustments-comparable-sales)

**Algorithm:**
```python
def estimate_fmv(target_axie, recent_sales, hedonic_coefficients):
    # Step 1: Find comparables (same class, similar attributes)
    comparables = find_similar(target_axie, recent_sales,
                               max_breed_diff=1, min_part_overlap=4)

    # Step 2: Adjust each comparable to target
    adjusted_prices = []
    for comp in comparables:
        adj = comp.price
        for attr in ['breed_count', 'parts', 'purity']:
            diff = target_axie[attr] - comp[attr]
            adj += diff * hedonic_coefficients[attr]
        adjusted_prices.append(adj)

    # Step 3: Central tendency
    return np.median(adjusted_prices)
```

---

### 2.3 Machine Learning Ensemble (Feature Discovery)

**Purpose:** Capture non-linear relationships hedonic model misses

**Recommended Models:**
| Model | Strength | Use Case |
|-------|----------|----------|
| Random Forest | Feature importance, handles categoricals | Primary predictor |
| XGBoost/LightGBM | Gradient boosting, high accuracy | Ensemble member |
| Neural Network | Complex interactions | Visual feature extraction |

**Feature Importance Analysis (Shapley Values):**
```
SHAP value = Contribution of feature j to prediction for instance i
```

**Sources:**
- [ScienceDirect (2023)](https://www.sciencedirect.com/science/article/abs/pii/S1044028323000996): Random forests achieve 80-90% accuracy for 14-21 day forecasts
- [ResearchGate (2023)](https://www.researchgate.net/publication/368261051_Predictors_of_NFT_Prices_An_Automated_Machine_Learning_Approach): 81 models tested, RF superior
- [IEEE Xplore](https://ieeexplore.ieee.org/document/10035064/): Multimodal learning for NFT price prediction

**Implementation:**
```python
from sklearn.ensemble import RandomForestRegressor
from shap import TreeExplainer

# Train
rf = RandomForestRegressor(n_estimators=500, max_depth=15)
rf.fit(X_train, np.log(y_train))

# Explain
explainer = TreeExplainer(rf)
shap_values = explainer.shap_values(X_test)

# Top features drive valuation model coefficients
```

---

### 2.4 Factor Model Approach (Fama-French Style)

**Origin:** Fama & French (1992, 2015), Asset Pricing
**Concept:** Returns explained by exposure to systematic factors

**Adapted for Axies:**
```
R_i = α + β_class * F_class + β_meta * F_meta + β_breed * F_breed + ε_i

Where:
- R_i = Return (price change) of Axie i
- F_class = Class factor (e.g., Bird returns - Bug returns)
- F_meta = Meta factor (meta parts portfolio - non-meta portfolio)
- F_breed = Virgin premium factor (breed_0 - breed_4+ returns)
```

**Factors to Construct:**
| Factor | Long Portfolio | Short Portfolio |
|--------|----------------|-----------------|
| Class Premium | Top-performing class | Bottom-performing class |
| Meta Parts | Axies with meta parts | Axies without |
| Virgin Premium | Breed count 0-1 | Breed count 4+ |
| Purity | 6 pure parts | 0-2 pure parts |

**Sources:**
- [Wikipedia: Fama-French](https://en.wikipedia.org/wiki/Fama–French_three-factor_model)
- [SSRN: Five-Factor Model](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2287202)
- [CFA Institute](https://blogs.cfainstitute.org/investor/2022/01/10/fama-and-french-the-five-factor-model-revisited/)

---

## Part 3: Trend Detection & Market Dynamics

### 3.1 Time Series Models for Price Trends

**ARIMA for Level Forecasting:**
```
Price_t = c + Σ φ_i * Price_{t-i} + Σ θ_j * ε_{t-j} + ε_t
```

**GARCH for Volatility Clustering:**
```
σ²_t = ω + α * ε²_{t-1} + β * σ²_{t-1}

Where σ²_t = conditional variance (volatility) at time t
```

**Sources:**
- [Wiley (2024)](https://onlinelibrary.wiley.com/doi/10.1155/2024/6305525): Hybrid GARCH + Deep Learning
- [Emerald (2024)](https://www.emerald.com/insight/content/doi/10.1108/baj-05-2024-0027/full/html): ARIMA-GARCH for Bitcoin
- [ResearchGate](https://www.researchgate.net/publication/384664982_Forecasting_Volatility_Comparative_Analysis_of_ARIMA_GARCH_and_Deep_Learning_Models_for_Predicting_Stock_Market_Volatility): Comparative analysis

**Application to Axie Market:**
```python
# Daily floor price series by class
floor_series = sales.groupby(['date', 'class']).price_usd.min()

# Fit ARIMA(1,1,1) for trend
from statsmodels.tsa.arima.model import ARIMA
model = ARIMA(floor_series['Beast'], order=(1,1,1))
fit = model.fit()

# Forecast next 7 days
forecast = fit.forecast(steps=7)
```

---

### 3.2 Exponential Moving Averages for Trend Detection

**EMA Formula:**
```
EMA_t = α * Price_t + (1 - α) * EMA_{t-1}

Where α = 2 / (N + 1), N = lookback period
```

**Double EMA (DEMA) for Reduced Lag:**
```
DEMA_t = 2 * EMA_t - EMA(EMA_t)
```

**Trend Signals:**
- **Golden Cross:** Short EMA (e.g., 10-day) crosses above Long EMA (e.g., 50-day) → Bullish
- **Death Cross:** Short EMA crosses below Long EMA → Bearish

**Sources:**
- [LuxAlgo](https://www.luxalgo.com/blog/double-exponential-moving-average-reducing-lag-in-trend-analysis/): DEMA for reduced lag
- [Springer (2025)](https://link.springer.com/article/10.1007/s10479-025-06542-7): Turning point detection in high-frequency data

**Implementation for Part Meta Tracking:**
```python
def detect_meta_shift(part_id, window_short=7, window_long=30):
    prices = get_part_floor_history(part_id)
    ema_short = prices.ewm(span=window_short).mean()
    ema_long = prices.ewm(span=window_long).mean()

    # Detect crossovers
    golden_cross = (ema_short > ema_long) & (ema_short.shift(1) <= ema_long.shift(1))
    death_cross = (ema_short < ema_long) & (ema_short.shift(1) >= ema_long.shift(1))

    return golden_cross, death_cross
```

---

### 3.3 Change Point Detection for Regime Shifts

**Methods:**
1. **CUSUM (Cumulative Sum):** Detects shift in mean
2. **Bayesian Change Point:** Probabilistic regime detection
3. **Structural Break Tests:** Chow test, Bai-Perron

**Formula (CUSUM):**
```
S_t = max(0, S_{t-1} + (x_t - μ_0 - k))

Alarm when S_t > h (threshold)
```

**Application:** Detect when a part becomes "meta" (sustained price increase)

---

### 3.4 Mathematical Framework for Trend Prediction

**Proposed Trend Score Formula:**
```
TrendScore_j(t) = w_1 * Momentum_j + w_2 * Volatility_j + w_3 * Volume_j

Where:
- Momentum_j = (EMA_7 - EMA_30) / EMA_30  (% deviation)
- Volatility_j = σ(returns_7d) / σ(returns_30d)  (volatility ratio)
- Volume_j = Volume_7d / Volume_30d  (volume surge)
```

**Interpretation:**
| TrendScore | Interpretation |
|------------|----------------|
| > 0.3 | Strong uptrend (emerging meta) |
| 0.1 to 0.3 | Mild uptrend |
| -0.1 to 0.1 | Neutral/stable |
| -0.3 to -0.1 | Mild downtrend |
| < -0.3 | Strong downtrend (falling out of meta) |

---

## Part 4: Uncertainty Quantification

### 4.1 Bayesian Hierarchical Model

**Purpose:** Provide confidence intervals, not just point estimates

**Model Structure:**
```
Level 1 (Individual Axie):
ln(P_i) ~ Normal(μ_i, σ²)

Level 2 (Class-level):
μ_i = α_class[i] + X_i * β

Level 3 (Hyperpriors):
α_class ~ Normal(μ_α, σ²_α)
β ~ Normal(0, σ²_β)
```

**Output:** Posterior distribution P(FMV | data) with 95% credible interval

**Sources:**
- [Wiley (2023)](https://onlinelibrary.wiley.com/doi/10.1111/jiec.13339): Hierarchical Bayesian reduces uncertainty 50%+
- [arXiv (2024)](https://arxiv.org/html/2512.15739): Bayesian DLM outperforms GARCH/LSTM for uncertainty
- [LSEEE (2024)](https://lseee.net/index.php/te/article/view/2128): Bayesian hierarchical for stock forecasting

**Implementation:**
```python
import pymc as pm

with pm.Model() as hierarchical_model:
    # Hyperpriors
    mu_class = pm.Normal('mu_class', mu=0, sigma=10)
    sigma_class = pm.HalfNormal('sigma_class', sigma=5)

    # Class-level intercepts
    alpha = pm.Normal('alpha', mu=mu_class, sigma=sigma_class, dims='class')

    # Coefficients
    beta_breed = pm.Normal('beta_breed', mu=0, sigma=1)
    beta_purity = pm.Normal('beta_purity', mu=0, sigma=1)

    # Likelihood
    mu = alpha[class_idx] + beta_breed * breed_count + beta_purity * purity
    sigma = pm.HalfNormal('sigma', sigma=1)

    y = pm.Normal('y', mu=mu, sigma=sigma, observed=log_price)

    trace = pm.sample(2000)
```

---

## Part 5: Arbitrage Detection Framework

### 5.1 Fair Market Value Deviation Score

```
Z_i = (P_listing - FMV_i) / σ_FMV

Where:
- P_listing = Current listing price
- FMV_i = Estimated fair market value
- σ_FMV = Standard error of FMV estimate
```

**Arbitrage Signals:**
| Z-Score | Interpretation | Action |
|---------|----------------|--------|
| < -2.0 | Significantly undervalued | Strong buy signal |
| -2.0 to -1.0 | Moderately undervalued | Consider buying |
| -1.0 to 1.0 | Fairly priced | Hold/pass |
| 1.0 to 2.0 | Moderately overvalued | Consider selling |
| > 2.0 | Significantly overvalued | Strong sell signal |

### 5.2 Liquidity-Adjusted Valuation

```
Adjusted_FMV = FMV * (1 - Illiquidity_Discount)

Illiquidity_Discount = f(time_to_sell, spread, volume)
```

**Sources:**
- [Binance Academy](https://academy.binance.com/en/glossary/bid-ask-spread): Bid-ask spread as liquidity measure
- [SSRN: Bitcoin Microstructure](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2949807): Adverse selection in crypto

---

## Part 6: Implementation Roadmap

### Phase 1: Data Foundation (Week 1-2)
- [ ] Populate `axie_parts` reference table
- [ ] Create `axie_part_mapping` for normalized part queries
- [ ] Build daily floor price time series by class and part
- [ ] Calculate rolling statistics (7d, 30d, 90d)

### Phase 2: Hedonic Model (Week 3-4)
- [ ] Feature engineering (one-hot encoding, interactions)
- [ ] Train OLS hedonic regression
- [ ] Validate with holdout set (RMSE, MAE, R²)
- [ ] Extract implicit prices for each characteristic

### Phase 3: ML Ensemble (Week 5-6)
- [ ] Train Random Forest, XGBoost, LightGBM
- [ ] Compute SHAP values for feature importance
- [ ] Build ensemble (weighted average of models)
- [ ] Compare performance vs hedonic model

### Phase 4: Bayesian Uncertainty (Week 7-8)
- [ ] Implement hierarchical Bayesian model in PyMC
- [ ] Generate posterior distributions for FMV
- [ ] Create confidence interval estimates

### Phase 5: Trend Detection (Week 9-10)
- [ ] Implement EMA/DEMA trend indicators
- [ ] Build ARIMA-GARCH models for floor prices
- [ ] Create TrendScore metric for parts
- [ ] Set up alerts for meta shifts

### Phase 6: Production System (Week 11-12)
- [ ] Build real-time FMV API endpoint
- [ ] Create arbitrage alert system (Z-score < -2)
- [ ] Dashboard for trend monitoring
- [ ] Backtesting framework for strategy validation

---

## Part 7: Key Literature References

### Finance & Economics
1. Rosen, S. (1974). "Hedonic Prices and Implicit Markets." *Journal of Political Economy*
2. Fama, E. & French, K. (1993). "Common Risk Factors in Stock and Bond Returns." *Journal of Financial Economics*
3. Fama, E. & French, K. (2015). "A Five-Factor Asset Pricing Model." *Journal of Financial Economics*
4. Engle, R. (1982). "Autoregressive Conditional Heteroscedasticity." *Econometrica* (ARCH/GARCH)

### NFT & Crypto Valuation
5. [Pixels to Prices (2024)](https://arxiv.org/abs/2509.24879) - Hedonic NFT valuation with visual features
6. [Pricing Dynamics and Herding in NFTs (2025)](https://onlinelibrary.wiley.com/doi/full/10.1111/eufm.12506) - 875k NFT sales analysis
7. [Beyond Scarcity: Social Value in NFTs (2024)](https://academic.oup.com/jcr/article/51/1/140/7672977) - Social vs intrinsic value

### Machine Learning
8. [NFT Price Prediction ML (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S1044028323000996) - Feature significance analysis
9. [Automated ML for NFT Prices](https://www.researchgate.net/publication/368261051_Predictors_of_NFT_Prices_An_Automated_Machine_Learning_Approach) - 81 model comparison
10. [Deep Learning for NFT Valuation](https://arxiv.org/html/2312.05346v1) - DeepNFTValue

### Bayesian Methods
11. [Hierarchical Bayesian for Material Demand](https://onlinelibrary.wiley.com/doi/10.1111/jiec.13339) - 50% uncertainty reduction
12. [Bayesian Stock Forecasting](https://lseee.net/index.php/te/article/view/2128) - Probabilistic framework

### Time Series
13. [Hybrid GARCH + Deep Learning (2024)](https://onlinelibrary.wiley.com/doi/10.1155/2024/6305525) - Volatility forecasting
14. [ARIMA-GARCH for Bitcoin](https://www.emerald.com/insight/content/doi/10.1108/baj-05-2024-0027/full/html) - Crypto price prediction

---

## Part 8: Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| FMV Prediction RMSE | < 30% | Out-of-sample prediction error |
| Arbitrage Win Rate | > 65% | % of buy signals that profit |
| Trend Detection Lead | > 3 days | Days before 20% price move |
| Uncertainty Calibration | 95% CI covers 95% | Bayesian interval accuracy |

---

## Appendix A: Mathematical Notation Summary

| Symbol | Meaning |
|--------|---------|
| P_i | Price of Axie i |
| X_ij | Characteristic j of Axie i |
| β_j | Coefficient (implicit price) of characteristic j |
| EMA_t | Exponential moving average at time t |
| σ²_t | Conditional variance (GARCH) |
| FMV | Fair Market Value |
| Z_i | Standardized deviation from FMV |

---

## Appendix B: SQL Queries for Data Extraction

```sql
-- Daily floor prices by class
SELECT
    DATE(block_timestamp) as date,
    class,
    MIN(price_usd) as floor_price,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_usd) as median_price,
    COUNT(*) as volume
FROM axie.axie_sales s
JOIN axie.axie_metadata m ON s.axie_id = m.axie_id
WHERE price_usd > 0
GROUP BY 1, 2;

-- Part premium analysis
SELECT
    m.part_mouth,
    COUNT(*) as sales,
    AVG(s.price_usd) as avg_price,
    AVG(s.price_usd) / MIN(s.price_usd) OVER() as premium_ratio
FROM axie.axie_sales s
JOIN axie.axie_metadata m ON s.axie_id = m.axie_id
WHERE s.price_usd BETWEEN 1 AND 500
GROUP BY m.part_mouth
HAVING COUNT(*) >= 50;
```

---

*Document prepared for AxiePro valuation model development.*
