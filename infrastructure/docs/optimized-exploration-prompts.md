# Optimized Codebase Exploration Prompts
## Aligned with AxiePro's Purpose: Axie Infinity Analytics Platform

*Generated from systematic analysis of prompt effectiveness against actual codebase*

---

## Executive Summary: Prompt Performance Analysis

### What Worked Well
| Prompt Category | Effectiveness | Key Insight |
|-----------------|---------------|-------------|
| Architecture Discovery | **Excellent** | Revealed clear 3-layer separation and 10-stack CDK structure |
| Data Flow Tracing | **Excellent** | Exposed the complete pipeline: External APIs → Lambda → DB → Cache → API |
| Domain Model Analysis | **Good** | Identified 65% coverage of Axie domain, critical gaps in runes/charms/land |
| Infrastructure Alignment | **Excellent** | 9/10 score - infrastructure matches analytics platform needs |
| Integration Mapping | **Good** | Found 4 external APIs, revealed missing CoinGecko/price feeds |

### What Needed Refinement
| Gap Identified | Original Prompt Issue | Optimized Approach |
|----------------|----------------------|-------------------|
| Missing domain concepts | Generic "what's missing" too broad | Domain-specific checklist prompts |
| Real-time capability assessment | Not explicit enough | Dedicated latency/streaming prompts |
| Valuation model depth | Treated as generic feature | Dedicated ML/pricing model prompts |
| Cross-service data consistency | Not addressed | Added data integrity prompts |

---

## Part 1: Domain-Specific Discovery Prompts

### 1.1 Axie Domain Model Completeness
```
Audit the data models against Axie Infinity's complete domain:

CORE ENTITIES (Must Have):
□ Axie (genes, class, parts, stats, breed count, purity)
□ Parts (6 positions × 3 gene types, abilities linked)
□ Listings (price, seller, status, timestamps)
□ Sales (buyer, seller, tx_hash, marketplace)
□ Wallets (address, holdings, trade history)

EXTENDED ENTITIES (Should Have):
□ Runes & Charms (recent game mechanics)
□ Land plots (Lunacia real estate)
□ Items/Equipment (cosmetics, tools)
□ Token economics (SLP, AXS prices over time)

ANALYTICS ENTITIES (Value-Add):
□ Price snapshots (time-series for trend analysis)
□ Trait statistics (avg/median/std per trait)
□ Hedonic coefficients (valuation model)
□ Deal opportunities (undervalued listings)

For each missing entity, assess:
- Business impact (High/Medium/Low)
- Implementation complexity
- Data source availability
```

### 1.2 Valuation Model Architecture
```
Analyze the valuation/pricing infrastructure:

1. MODEL TYPE: What pricing model is implemented?
   - Hedonic regression (log-linear)?
   - Comparable sales analysis?
   - ML-based (gradient boosting, neural net)?

2. FEATURE ENGINEERING:
   - What Axie attributes feed the model?
   - How are categorical features encoded (one-hot, embedding)?
   - Are interaction terms included (class × part combinations)?

3. MODEL LIFECYCLE:
   - How is the model trained/retrained?
   - Where are coefficients stored?
   - Is there model versioning?
   - What's the retraining frequency?

4. CONFIDENCE METRICS:
   - R², RMSE, MAE tracked?
   - Confidence intervals provided?
   - Out-of-sample validation?

5. DEAL DETECTION:
   - How is "undervalued" defined (z-score, % below FMV)?
   - What thresholds trigger alerts?
   - How fresh is the comparison data?
```

### 1.3 Market Data Pipeline Latency
```
Trace market data from source to user with timing:

SOURCE → INGESTION → PROCESSING → STORAGE → API → CLIENT

For each stage, identify:
1. Data source (Sky Mavis API, Ronin RPC, etc.)
2. Ingestion method (polling interval, webhook, stream)
3. Processing latency (Lambda cold start, computation time)
4. Storage write latency (Aurora, Redis, DynamoDB)
5. API response time (cache hit vs miss)
6. Total end-to-end latency

Target benchmarks for analytics platform:
- Floor prices: < 5 min staleness
- New listings: < 30 sec detection
- Deal alerts: < 1 min from listing
- Valuation queries: < 500ms response
```

---

## Part 2: Integration & External API Prompts

### 2.1 External API Dependency Map
```
For each external API integration, document:

┌─────────────────────────────────────────────────────────┐
│ API: [Name]                                             │
├─────────────────────────────────────────────────────────┤
│ Purpose:     [What data/functionality it provides]      │
│ Endpoint:    [Base URL]                                 │
│ Auth:        [API key, OAuth, none]                     │
│ Rate Limit:  [X requests per Y time]                    │
│ Client File: [path/to/client.py]                        │
├─────────────────────────────────────────────────────────┤
│ CRITICAL DATA PROVIDED:                                 │
│ □ [Data type 1]                                         │
│ □ [Data type 2]                                         │
├─────────────────────────────────────────────────────────┤
│ FALLBACK STRATEGY:                                      │
│ □ Alternative API: [name]                               │
│ □ Cached data TTL: [duration]                           │
│ □ Graceful degradation: [behavior]                      │
├─────────────────────────────────────────────────────────┤
│ FAILURE IMPACT:                                         │
│ [What breaks if this API is unavailable]                │
└─────────────────────────────────────────────────────────┘

Required integrations for Axie analytics:
1. Sky Mavis GraphQL - Axie data, marketplace (PRIMARY)
2. Moralis/Alchemy - Ronin blockchain data
3. Ronin RPC - Direct chain queries, event logs
4. CoinGecko/CoinMarketCap - Token prices (ETH, RON, AXS, SLP)
5. Price Oracle - Real-time exchange rates
```

### 2.2 Data Freshness Audit
```
For each data type, verify freshness guarantees:

| Data Type | Source | Update Frequency | Cache TTL | Staleness Risk |
|-----------|--------|------------------|-----------|----------------|
| Floor prices | Sky Mavis | ? | ? | HIGH if > 5 min |
| Active listings | Sky Mavis | ? | ? | HIGH if > 1 min |
| Sales history | Ronin RPC | ? | ? | LOW |
| Axie metadata | Sky Mavis | ? | ? | LOW (static) |
| Token prices | [Missing?] | ? | ? | CRITICAL |
| Wallet balances | Moralis | ? | ? | MEDIUM |

Identify any data without automated refresh.
```

---

## Part 3: Infrastructure-Purpose Alignment Prompts

### 3.1 Real-Time Capability Assessment
```
Assess infrastructure support for real-time analytics:

STREAMING INFRASTRUCTURE:
□ Kinesis/Kafka for event ingestion?
□ WebSocket API for client push?
□ Lambda with stream triggers?
□ Fan-out pattern for multiple consumers?

LATENCY REQUIREMENTS vs ACTUAL:
| Use Case | Required | Actual | Gap |
|----------|----------|--------|-----|
| Deal alerts | < 30s | ? | ? |
| Price updates | < 5m | ? | ? |
| New listing detection | < 1m | ? | ? |
| Portfolio sync | < 5m | ? | ? |

BOTTLENECKS:
- Cold start latency for Lambda?
- Database connection pooling?
- Cache miss penalty?
- External API rate limits?
```

### 3.2 Batch Analytics Infrastructure
```
Assess batch processing capability:

COMPUTE RESOURCES:
□ ECS Fargate / EKS for batch jobs?
□ Lambda for lightweight batch?
□ Step Functions for orchestration?

BATCH JOB INVENTORY:
| Job Name | Trigger | Frequency | Duration | Purpose |
|----------|---------|-----------|----------|---------|
| ? | ? | ? | ? | ? |

DATA WAREHOUSE:
□ S3 data lake for historical data?
□ Athena/Redshift for analytics queries?
□ Data partitioning strategy?

MISSING BATCH CAPABILITIES:
- Historical backfill jobs?
- Model retraining pipelines?
- Daily/weekly aggregation jobs?
```

### 3.3 Cost-Performance Trade-off Analysis
```
For each infrastructure component, assess:

| Component | Current Config | Monthly Cost Est | Performance | Optimization |
|-----------|---------------|------------------|-------------|--------------|
| Aurora | ? ACUs | $? | ? | ? |
| ElastiCache | ? node type | $? | ? | ? |
| Lambda | ? memory | $? | ? | ? |
| App Runner | ? vCPU/mem | $? | ? | ? |
| Kinesis | ? shards | $? | ? | ? |

Identify:
- Over-provisioned resources (cost savings)
- Under-provisioned resources (performance risk)
- Scaling triggers and thresholds
```

---

## Part 4: Code Quality & Maintainability Prompts

### 4.1 Error Handling Completeness
```
Audit error handling for analytics reliability:

EXTERNAL API ERRORS:
□ Rate limit (429) handling with backoff?
□ Timeout handling with retry?
□ Partial failure handling (batch operations)?
□ Circuit breaker for failing services?

DATABASE ERRORS:
□ Connection pool exhaustion?
□ Query timeout handling?
□ Deadlock detection and retry?
□ Data integrity constraint violations?

CACHE ERRORS:
□ Redis connection failure fallback?
□ Cache miss vs cache error distinction?
□ Graceful degradation to DB-only mode?

USER-FACING ERRORS:
□ Meaningful error messages (not stack traces)?
□ Error categorization (4xx vs 5xx)?
□ Retry guidance in error responses?
```

### 4.2 Data Consistency Audit
```
Verify data consistency across storage layers:

CONSISTENCY SCENARIOS:
1. Cache vs Database divergence
   - When cache is updated, is DB updated atomically?
   - What's the max cache staleness acceptable?

2. Cross-table consistency
   - When Axie is sold, are both listings and sales tables updated?
   - Are wallet holdings decremented atomically?

3. External data vs local data
   - How often is Sky Mavis data reconciled with local DB?
   - What happens if external data contradicts local?

4. Event ordering
   - Are Kinesis events processed in order?
   - Can out-of-order events cause incorrect state?

AUDIT QUERIES:
- SELECT * FROM listings WHERE status='active' AND axie_id IN
  (SELECT axie_id FROM sales WHERE sold_at > listings.listed_at)
- [Find listings marked active but already sold]
```

---

## Part 5: Security & Compliance Prompts

### 5.1 Secrets Management Audit
```
Inventory all secrets and their management:

| Secret | Storage Location | Rotation | Access Control |
|--------|-----------------|----------|----------------|
| DB password | Secrets Manager? | Auto? | IAM role? |
| API keys (Sky Mavis) | ? | Manual? | ? |
| API keys (Moralis) | ? | ? | ? |
| Redis auth | ? | ? | ? |

VULNERABILITIES TO CHECK:
□ Secrets in environment variables (acceptable) vs code (bad)
□ Secrets in logs (ERROR level prints)
□ Secrets in error messages returned to client
□ Secrets committed to git history
```

### 5.2 Data Privacy Assessment
```
For user/wallet data, assess:

WALLET DATA:
□ Are wallet addresses considered PII?
□ Is there user consent for tracking?
□ Can users request data deletion?

ANALYTICS DATA:
□ Is trading behavior anonymized?
□ Are whale wallets flagged publicly?
□ Is there rate limiting per wallet query?

COMPLIANCE:
□ GDPR considerations for EU users?
□ Data retention policies defined?
□ Audit logging for data access?
```

---

## Part 6: Quick Reference Checklists

### 6.1 New Feature Readiness Checklist
```
Before implementing [FEATURE], verify:

□ Data model exists or needs extension?
□ External API provides required data?
□ Cache strategy defined (TTL, invalidation)?
□ Error handling for all failure modes?
□ API endpoint design (REST conventions)?
□ Frontend integration requirements?
□ Performance impact assessed?
□ Cost impact estimated?
```

### 6.2 Production Readiness Checklist
```
Before deploying to production, verify:

RELIABILITY:
□ Health check endpoint works?
□ Graceful shutdown handling?
□ Connection pooling configured?
□ Retry logic for transient failures?

OBSERVABILITY:
□ Structured logging enabled?
□ Metrics exported to CloudWatch?
□ Distributed tracing (X-Ray)?
□ Alerting rules configured?

SECURITY:
□ No secrets in code/logs?
□ Input validation on all endpoints?
□ Rate limiting enabled?
□ TLS for all connections?

PERFORMANCE:
□ Load testing completed?
□ Cache warming strategy?
□ Database indexes optimized?
□ Cold start latency acceptable?
```

---

## Appendix: AxiePro-Specific Quick Commands

```bash
# Find all Axie domain models
grep -r "class Axie\|class Listing\|class Sale" backend/src/models/

# Find external API calls
grep -r "httpx\|aiohttp\|requests" backend/src/services/

# Find cache operations
grep -r "redis\|cache" backend/src/

# Find scheduled jobs
grep -r "schedule\|cron\|EventBridge" infrastructure/lib/

# Find environment variables used
grep -r "getenv\|environ\|settings\." backend/src/

# Find error handling patterns
grep -r "try:\|except\|raise\|Error" backend/src/

# Find database queries
grep -r "select\|insert\|update\|delete" --include="*.py" backend/src/

# Check for hardcoded secrets (should return nothing)
grep -r "api_key\s*=\s*['\"]" --include="*.py" backend/src/
```

---

## Findings Summary: AxiePro Alignment Score

| Category | Score | Key Finding |
|----------|-------|-------------|
| **Core Axie Domain** | 85% | Excellent coverage of Axies, market, breeding |
| **Extended Domain** | 40% | Missing runes, charms, land, items |
| **Valuation Engine** | 90% | Sophisticated hedonic model with deal detection |
| **Real-Time Capability** | 75% | Kinesis + WebSocket ready, needs message routing |
| **External Integrations** | 70% | Good API coverage, missing price feeds |
| **Infrastructure** | 90% | Enterprise-grade AWS setup |
| **Data Freshness** | 70% | 5-min floor prices, needs faster listing detection |
| **Error Handling** | 75% | Good patterns, needs circuit breakers |

**Overall Platform Readiness: 75%**

**Critical Gaps to Address:**
1. Add CoinGecko/price feed integration for USD valuations
2. Implement WebSocket message handlers for real-time updates
3. Add runes/charms data model for modern Axie valuations
4. Configure automated batch job scheduling
5. Add circuit breaker pattern for external API resilience

---

*Generated: 2025-01-20 | Based on systematic codebase analysis*
