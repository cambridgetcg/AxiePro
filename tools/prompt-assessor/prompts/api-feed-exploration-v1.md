# API Data Endpoint Exploration Prompts - Version 1

## Purpose
Prompts for exploring and understanding the AxiePro API architecture to enable creation of new data feeds for Axie Infinity analytics.

---

## Prompt 1: API Architecture Discovery (ARCH-API-001)

**Category:** Discovery
**Target:** API structure, routing, middleware

```
Analyze the FastAPI backend architecture in /backend/src to answer:

1. What is the API routing structure? Map all endpoint prefixes and their purposes.
2. How is authentication/authorization implemented? What middleware is used?
3. What response models and schemas are defined? Where are they located?
4. How do routers connect to services and repositories?
5. What error handling patterns are used across endpoints?

Output as:
- Endpoint map (prefix → router file → purpose)
- Auth flow diagram
- Schema inventory table
- Service dependency graph
```

---

## Prompt 2: Data Model Alignment (DATA-API-001)

**Category:** Analysis
**Target:** Data models, database schema, API contracts

```
Examine the data models in /backend/src/models and /backend/src/schemas:

1. What are the core domain entities (Axie, Listing, Price, etc.)?
2. How do SQLAlchemy models map to Pydantic schemas?
3. What relationships exist between entities?
4. Which fields are exposed via API vs internal only?
5. What validation rules are applied to incoming data?

Produce:
- Entity relationship diagram (text-based)
- Model-to-schema mapping table
- Validation rules summary
- Missing/incomplete model gaps
```

---

## Prompt 3: External API Integration Points (EXT-API-001)

**Category:** Tracing
**Target:** Third-party API connections, data sources

```
Trace all external API integrations in the codebase:

1. What external APIs does AxiePro consume? (Sky Mavis, Ronin RPC, Goldrush, etc.)
2. Where are API clients defined and how are they configured?
3. What data transformations occur between external response and internal models?
4. How is rate limiting handled for each external API?
5. What caching strategies are used for external data?

Deliver:
- External API inventory (name, base URL, auth method, rate limits)
- Data flow: External API → Transform → Internal Model → Cache
- Error handling patterns per integration
- Retry/backoff configurations
```

---

## Prompt 4: Feed Creation Blueprint (FEED-API-001)

**Category:** Alignment
**Target:** Pattern for adding new data feeds

```
Based on existing endpoint patterns, define how to create a new data feed endpoint:

1. What files need to be created/modified to add a new feed?
2. What is the standard pattern for a feed endpoint? (router → service → repository → model)
3. How should pagination be implemented for feed endpoints?
4. What caching should be applied to feed data?
5. How should real-time updates be handled (WebSocket, SSE, polling)?

Provide:
- Step-by-step checklist for adding a new feed
- Code template/skeleton for each layer
- Configuration requirements
- Testing approach
```

---

## Prompt 5: Feed Data Sources Analysis (SOURCE-API-001)

**Category:** Diagnostic
**Target:** Available data for feed creation

```
Analyze what data sources are available for creating new feeds:

1. What market data is currently being collected? (listings, sales, prices)
2. What Axie metadata is available? (genes, stats, parts, breeding)
3. What analytics/aggregations are computed? (floor prices, volume, trends)
4. What real-time events are captured? (new listings, sales, price changes)
5. What historical data is stored and queryable?

Output:
- Data source inventory with refresh rates
- Available fields per data source
- Query patterns for each source
- Gaps: What data would enable better feeds?
```

---

## Usage Notes

- Run each prompt using Task agent with Explore subtype
- Assess each prompt output using the prompt-assessor tool
- Target score: 4.5+ (Grade A) for production readiness
- Iterate on low-scoring attributes

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

*Version 1.0 - Initial prompts for assessment*
