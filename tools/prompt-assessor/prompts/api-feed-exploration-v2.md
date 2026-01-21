# API Data Endpoint Exploration Prompts - Version 2

## Purpose
Optimized prompts for API feed exploration. Refined for **efficiency** while maintaining depth.

**Changes from v1:**
- Added token constraints (max 2500 tokens)
- Table-focused output format
- Skip obvious/standard patterns
- Focus on actionable insights
- Explicit gap detection

---

## Prompt 1: API Architecture Discovery (ARCH-API-002)

**Category:** Discovery | **Token Budget:** 2500

```
Analyze FastAPI backend in /backend/src. Output in tables only, max 2500 tokens.

REQUIRED TABLES:

1. **Endpoint Map** (columns: Prefix, Router File, Method, Endpoint, Purpose)
   - Include all 26 endpoints

2. **Auth & Middleware** (columns: Component, Status, Configuration)
   - CORS, rate limiting, auth mechanisms

3. **Service Dependencies** (columns: Router, Services Used, External APIs, Cache)
   - How each router connects to backend services

4. **Error Handling** (columns: Pattern, HTTP Code, Usage Location)
   - Only non-standard patterns

CONSTRAINTS:
- Skip standard FastAPI boilerplate descriptions
- No code blocks unless showing AxiePro-specific deviations
- Assume reader knows FastAPI/SQLAlchemy basics

GAPS TO IDENTIFY:
- Missing auth implementation
- Unimplemented rate limiting
- Incomplete error handling
```

---

## Prompt 2: Data Model Quick Map (DATA-API-002)

**Category:** Analysis | **Token Budget:** 2000

```
Map data models in /backend/src/models. Concise table format, max 2000 tokens.

REQUIRED TABLES:

1. **Entity Inventory** (columns: Model, Table, Primary Key, Key Fields, Relationships)
   - All SQLAlchemy models in one table

2. **Schema Coverage** (columns: Model, Has Pydantic Schema?, Response Used In, Gap)
   - Focus on missing Pydantic schemas

3. **Validation Rules** (columns: Field, Type, Constraint, Enforced By)
   - Only custom/business validations, skip obvious types

4. **Critical Indexes** (columns: Table, Index Name, Columns, Query Pattern)

CONSTRAINTS:
- No ASCII diagrams (use relationship column instead)
- Skip standard SQLAlchemy patterns
- Focus on gaps and inconsistencies

GAPS TO IDENTIFY:
- Missing response schemas
- Validation holes
- Index opportunities
```

---

## Prompt 3: External API Integration Summary (EXT-API-002)

**Category:** Tracing | **Token Budget:** 2000

```
Trace external API integrations in /backend/src/services. Table format, max 2000 tokens.

REQUIRED TABLES:

1. **API Inventory** (columns: API Name, Base URL, Auth Method, Rate Limit, Client File)

2. **Data Flow** (columns: Source API, Endpoint, Transform Function, Internal Model, Cache TTL)
   - How external data becomes internal models

3. **Error & Retry** (columns: API, Error Type, Handling, Retry Strategy, Circuit Breaker?)

4. **Caching Strategy** (columns: Data Type, Cache Key Pattern, TTL, Invalidation Trigger)

CONSTRAINTS:
- No code examples unless non-obvious
- Assume reader knows REST/GraphQL basics
- Focus on production configuration

GAPS:
- Missing retry logic
- No circuit breaker (where needed)
- Static/hardcoded values that should be configurable
```

---

## Prompt 4: Feed Creation Checklist (FEED-API-002)

**Category:** Alignment | **Token Budget:** 2500

```
Define feed endpoint creation pattern in /backend/src. Checklist format, max 2500 tokens.

REQUIRED OUTPUT:

1. **Files Checklist** (table: Layer, File Path, Template, Required?)
   - Exact files to create/modify for a new feed

2. **Standard Pattern** (numbered steps only):
   - Minimal steps: Router → Service → Model → Cache → Test

3. **Pagination Pattern** (single code block, 20 lines max)
   - Copy-paste ready pagination implementation

4. **Real-time Options** (comparison table: Method, Latency, Complexity, Use Case)
   - SSE vs WebSocket vs Polling - when to use each

5. **Testing Checklist** (bullet points):
   - What tests are required for a new feed

CONSTRAINTS:
- No lengthy explanations
- Assume reader can write Python/FastAPI
- Focus on AxiePro-specific conventions
- One code example per pattern (minimal)

OUTPUT FORMAT:
- Checklist items with [ ] for actionable steps
- Tables for comparisons
- Code blocks minimal (<25 lines each)
```

---

## Prompt 5: Data Sources for Feeds (SOURCE-API-002)

**Category:** Diagnostic | **Token Budget:** 2000

```
Inventory data sources for feed creation in /backend/src. Max 2000 tokens.

REQUIRED TABLES:

1. **Data Source Inventory** (columns: Category, Source, Fields Available, Refresh Rate, Query Pattern)
   - Market, Axie, Breeding, Wallet, Analytics categories

2. **Real-time Events** (columns: Event Type, Source, Payload Fields, Processing Location)
   - What triggers real-time updates

3. **Historical Data** (columns: Data Type, Time Range, Granularity, Query Capability)

4. **Feed Readiness** (columns: Potential Feed, Data Sources Needed, Available?, Gap)
   - What feeds can be built now vs need data enrichment

5. **Top 5 Data Gaps** (table: Gap, Impact, Data Needed, Priority)
   - Most impactful missing data

CONSTRAINTS:
- No prose - tables only
- Skip fields that are obvious from model names
- Focus on what enables better feeds

OUTPUT: Tables only, no explanatory text.
```

---

## Efficiency Guidelines

### Token Efficiency Targets
| Output Type | Tokens/Point | Target |
|-------------|--------------|--------|
| Tables | 500 | < 1500 tokens/point |
| Code blocks | 750 | < 2000 tokens/point |
| Mixed | 600 | < 1800 tokens/point |

### What to Skip
- Standard FastAPI patterns (async, Depends, Query)
- SQLAlchemy basics (Column, relationship)
- Obvious field types (id, created_at, updated_at)
- Generic error handling (404 not found)

### What to Include
- AxiePro-specific conventions
- Domain-specific validation rules
- Non-obvious architectural decisions
- Production configuration values
- Integration gotchas

---

## Assessment Criteria (v2 targets)

| Attribute | v1 Score | v2 Target | Improvement Strategy |
|-----------|----------|-----------|---------------------|
| CD | 4.5-5.0 | 4.5+ | Maintain |
| CB | 4.5-5.0 | 4.5+ | Maintain |
| AC | 5.0 | 5.0 | Maintain |
| AT | 4.0-5.0 | 4.5+ | More specific file:line refs |
| BC | 4.5-5.0 | 4.5+ | Maintain |
| DA | 4.5-5.0 | 5.0 | Maintain |
| CS | 5.0 | 5.0 | Maintain tables |
| **EF** | **3.0-3.5** | **4.5+** | **Token limits, tables only** |
| GD | 3.5-5.0 | 4.5+ | Explicit gap sections |
| RP | 4.5 | 4.5+ | Maintain |

**Goal:** All prompts achieve Grade A (4.5+)

---

*Version 2.0 - Optimized for efficiency*
