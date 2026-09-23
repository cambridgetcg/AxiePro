# Implementation Roadmap

> Historical exploration. All acquisition, conversion, revenue, pricing and growth targets in this document are retired. They are not requirements or an active launch plan; see [the current orientation](../PRICING.md). Research and factual technical evidence remain available.

## Overview

This document outlines the phased implementation plan for the Axie Ronin Explorer. The project is divided into 5 phases, each building upon the previous to deliver incremental value.

---

## Phase 1: Foundation & Data Infrastructure

### Objective
Set up the core infrastructure, database, and data ingestion pipeline.

### Deliverables

#### 1.1 Project Setup
- [ ] Initialize Python backend with FastAPI
- [ ] Initialize Next.js frontend with TypeScript
- [ ] Set up Docker Compose for local development
- [ ] Configure environment variables management
- [ ] Set up linting and formatting (Black, ESLint, Prettier)

#### 1.2 Database Setup
- [ ] Install PostgreSQL with TimescaleDB extension
- [ ] Create database migrations (Alembic)
- [ ] Implement core tables:
  - `axies`
  - `parts`
  - `abilities`
  - `axie_parts`
- [ ] Set up Redis for caching
- [ ] Create seed data for parts and abilities

#### 1.3 External API Integration
- [ ] Create Moralis API client
  - Wallet balances
  - NFT transfers
  - Token prices
- [ ] Create Sky Mavis GraphQL client
  - Axie metadata
  - Marketplace listings
  - Gene data
- [ ] Implement rate limiting and retry logic
- [ ] Create data normalization layer

#### 1.4 Gene Parser
- [ ] Implement gene hex decoder
- [ ] Map gene values to body parts
- [ ] Calculate purity scores
- [ ] Unit tests for gene parsing

### Technical Tasks

```python
# backend/src/utils/gene_parser.py
class GeneParser:
    def parse(self, gene_hex: str) -> AxieGenes:
        """Parse 256-bit gene into structured parts data."""
        pass

    def get_purity_score(self, genes: AxieGenes, axie_class: str) -> int:
        """Calculate how many dominant parts match the Axie's class."""
        pass

    def get_part_probabilities(
        self, parent_a: AxieGenes, parent_b: AxieGenes
    ) -> dict[str, list[PartProbability]]:
        """Calculate breeding outcome probabilities."""
        pass
```

```sql
-- Initial migration
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Run seed script for parts/abilities
\i seeds/parts.sql
\i seeds/abilities.sql
```

### Verification Checklist
- [ ] Can connect to PostgreSQL and Redis
- [ ] Can fetch Axie data from Sky Mavis API
- [ ] Gene parser correctly decodes sample genes
- [ ] Parts and abilities seeded correctly

---

## Phase 2: Core Backend API

### Objective
Implement the primary API endpoints for Axie search and market data.

### Deliverables

#### 2.1 Axie Endpoints
- [ ] `GET /axies` - Search with filters
- [ ] `GET /axies/{id}` - Single Axie details
- [ ] `GET /axies/{id}/siblings`
- [ ] `GET /axies/{id}/children`
- [ ] Implement pagination
- [ ] Add query parameter validation

#### 2.2 Market Endpoints
- [ ] `GET /market/listings` - Active listings
- [ ] `GET /market/sales` - Sales history
- [ ] `GET /market/floor-prices` - Floor by class/trait
- [ ] `GET /market/stats` - Volume, averages

#### 2.3 Data Indexing Jobs
- [ ] Set up Celery with Redis broker
- [ ] Marketplace listing syncer (every 5 min)
- [ ] Sales history indexer (every 1 min)
- [ ] Axie metadata updater (daily)
- [ ] Price aggregation job (hourly)

#### 2.4 Caching Strategy
- [ ] Cache listings in Redis (5 min TTL)
- [ ] Cache floor prices (1 min TTL)
- [ ] Cache Axie details (10 min TTL)
- [ ] Implement cache invalidation

### Technical Tasks

```python
# backend/src/api/routes/axies.py
@router.get("/axies")
async def search_axies(
    class_: Optional[str] = Query(None, alias="class"),
    purity: Optional[int] = Query(None, ge=0, le=6),
    parts: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    listed_only: bool = Query(False),
    sort: str = Query("price"),
    order: str = Query("asc"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Search Axies with filters."""
    pass
```

```python
# backend/src/services/market_service.py
class MarketService:
    async def get_floor_prices(
        self, group_by: str = "class"
    ) -> list[FloorPrice]:
        """Get current floor prices grouped by class or trait."""
        pass

    async def get_sales(
        self, filters: SalesFilter, page: int, per_page: int
    ) -> PaginatedResponse[Sale]:
        """Get sales history with filters."""
        pass
```

### Verification Checklist
- [ ] API returns paginated Axie results
- [ ] Filters work correctly (class, purity, price)
- [ ] Floor prices update automatically
- [ ] Sales history is accurate
- [ ] Response times < 200ms for cached data

---

## Phase 3: Frontend Core

### Objective
Build the primary user interface for browsing and exploring Axies.

### Deliverables

#### 3.1 Project Setup
- [ ] Configure Tailwind CSS
- [ ] Install and configure shadcn/ui
- [ ] Set up TanStack Query
- [ ] Create API client library
- [ ] Implement base layout (header, sidebar, footer)

#### 3.2 Explorer Page
- [ ] AxieCard component
- [ ] AxieGrid component (with virtual scrolling)
- [ ] AxieFilters sidebar
- [ ] Search functionality
- [ ] Pagination / infinite scroll
- [ ] Sort controls

#### 3.3 Axie Detail Page
- [ ] Axie image and basic info
- [ ] Gene/parts display table
- [ ] Stats visualization
- [ ] Abilities list
- [ ] Listing info (if listed)
- [ ] Sales history section
- [ ] Family tree (parents, children)

#### 3.4 Dashboard
- [ ] Market overview cards (volume, sales, floor)
- [ ] Trending traits list
- [ ] Recent sales feed
- [ ] Floor prices by class chart

### Technical Tasks

```tsx
// frontend/src/components/axie/AxieCard.tsx
export function AxieCard({ axie, onSelect, selected }: AxieCardProps) {
  return (
    <Card className={cn("cursor-pointer", selected && "ring-2 ring-primary")}>
      <CardContent>
        <Image src={axie.image_url} alt={axie.name} />
        <div className="flex justify-between">
          <span>#{axie.id}</span>
          <PurityBadge score={axie.purity_score} />
        </div>
        <ClassBadge class={axie.class} />
        {axie.listing && (
          <div className="text-lg font-bold">
            {axie.listing.price_eth} ETH
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

```tsx
// frontend/src/hooks/useAxies.ts
export function useAxies(filters: FilterState) {
  return useInfiniteQuery({
    queryKey: ['axies', filters],
    queryFn: async ({ pageParam = 1 }) => {
      const response = await api.get('/axies', {
        params: { ...filters, page: pageParam }
      });
      return response.data;
    },
    getNextPageParam: (lastPage) =>
      lastPage.meta.page < lastPage.meta.total_pages
        ? lastPage.meta.page + 1
        : undefined,
  });
}
```

### Verification Checklist
- [ ] Can browse Axies with filters
- [ ] Can view Axie details
- [ ] Dashboard shows live market data
- [ ] Mobile responsive layout works
- [ ] Page load time < 2s

---

## Phase 4: Breeding & Analytics

### Objective
Implement breeding simulation and advanced analytics features.

### Deliverables

#### 4.1 Breeding Simulator Backend
- [ ] `POST /breeding/simulate` endpoint
- [ ] Gene probability calculations
- [ ] Expected value calculations
- [ ] ROI analysis

#### 4.2 Breeding Simulator Frontend
- [ ] Parent selector components
- [ ] Breeding store (Zustand)
- [ ] Outcome probability display
- [ ] Part probability breakdown
- [ ] Cost calculator
- [ ] ROI analysis display

#### 4.3 Price History
- [ ] Create price_history hypertable
- [ ] Price aggregation jobs (1h, 1d intervals)
- [ ] `GET /prices/history` endpoint
- [ ] Price comparison endpoint
- [ ] Continuous aggregates for performance

#### 4.4 Analytics Frontend
- [ ] Price chart component (TradingView)
- [ ] Trait comparison view
- [ ] Trending traits display
- [ ] Volume charts

### Technical Tasks

```python
# backend/src/services/breeding_service.py
class BreedingService:
    GENE_PROBABILITIES = {
        'd_d': 0.375,    # Both parents D
        'd_r1': 0.09375,
        'd_r2': 0.03125,
        'r1_r1': 0.09375,
        'r1_r2': 0.03125,
        'r2_r2': 0.03125,
    }

    def simulate(
        self, matron_id: int, sire_id: int
    ) -> BreedingSimulation:
        """Simulate breeding outcomes."""
        matron = self.get_axie(matron_id)
        sire = self.get_axie(sire_id)

        return BreedingSimulation(
            cost=self.calculate_cost(matron, sire),
            class_probabilities=self.calc_class_probs(matron, sire),
            part_probabilities=self.calc_part_probs(matron, sire),
            expected_outcomes=self.calc_expected_outcomes(...),
            roi=self.calc_roi(...),
        )
```

```sql
-- Price history hypertable
CREATE TABLE price_history (
    time TIMESTAMPTZ NOT NULL,
    class axie_class,
    trait_key VARCHAR(100),
    floor_price_eth DECIMAL(20, 8),
    avg_price_eth DECIMAL(20, 8),
    volume INTEGER,
    PRIMARY KEY (time, class, trait_key)
);

SELECT create_hypertable('price_history', 'time');

-- Continuous aggregate for daily rollups
CREATE MATERIALIZED VIEW price_daily
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS day,
    class,
    trait_key,
    AVG(floor_price_eth) AS avg_floor,
    SUM(volume) AS total_volume
FROM price_history
GROUP BY day, class, trait_key;
```

### Verification Checklist
- [ ] Breeding simulation matches known probabilities
- [ ] ROI calculation is accurate
- [ ] Price history charts render correctly
- [ ] Analytics queries perform well (< 500ms)
- [ ] Continuous aggregates refresh properly

---

## Phase 5: Wallet & Advanced Features

### Objective
Add wallet tracking, arbitrage detection, and alerting.

### Deliverables

#### 5.1 Wallet Features
- [ ] `GET /wallets/{address}` - Wallet overview
- [ ] `GET /wallets/{address}/axies` - Holdings
- [ ] `GET /wallets/{address}/trades` - Trade history
- [ ] P&L calculations
- [ ] Wallet tracking (watchlist)

#### 5.2 Wallet Frontend
- [ ] Wallet portfolio page
- [ ] Holdings table with values
- [ ] Trade history timeline
- [ ] P&L chart
- [ ] Performance metrics

#### 5.3 Arbitrage Detection
- [ ] Fair value estimation model
- [ ] `GET /analytics/arbitrage` endpoint
- [ ] Undervalued Axie alerts
- [ ] Comparable sales lookup

#### 5.4 Alerts & Notifications
- [ ] Price alert system
- [ ] New listing alerts (by trait)
- [ ] Whale activity alerts
- [ ] Email notification integration (optional)
- [ ] Webhook support

#### 5.5 Best Pairs Finder
- [ ] `GET /breeding/best-pairs` endpoint
- [ ] Optimize for target traits
- [ ] Factor in breeding costs
- [ ] ROI ranking

### Technical Tasks

```python
# backend/src/services/arbitrage_service.py
class ArbitrageService:
    def estimate_fair_value(self, axie: Axie) -> Decimal:
        """
        Estimate fair value based on:
        - Recent sales of similar Axies
        - Floor price for class/purity
        - Premium for specific traits
        """
        base_value = self.get_floor_price(axie.class_, axie.purity_score)
        trait_premium = self.calculate_trait_premium(axie.parts)
        return base_value + trait_premium

    def find_opportunities(
        self, min_discount: float = 0.1, max_price: float = None
    ) -> list[ArbitrageOpportunity]:
        """Find Axies listed below fair value."""
        pass
```

```python
# backend/src/services/wallet_service.py
class WalletService:
    def calculate_pnl(self, address: str) -> WalletPnL:
        """Calculate realized and unrealized P&L for wallet."""
        trades = self.get_trades(address)
        holdings = self.get_holdings(address)

        realized = sum(
            trade.price_eth - self.get_acquisition_cost(trade.axie_id)
            for trade in trades if trade.type == 'sell'
        )

        unrealized = sum(
            self.estimate_value(h.axie) - h.acquisition_price_eth
            for h in holdings
        )

        return WalletPnL(realized=realized, unrealized=unrealized)
```

### Verification Checklist
- [ ] Wallet portfolio shows accurate holdings
- [ ] P&L calculations are correct
- [ ] Arbitrage finder surfaces real opportunities
- [ ] Alerts trigger correctly
- [ ] Best pairs recommendations are sensible

---

## Implementation Order Summary

```
Phase 1: Foundation (Core Infrastructure)
    │
    ├── 1.1 Project setup
    ├── 1.2 Database & migrations
    ├── 1.3 External API clients
    └── 1.4 Gene parser
           │
           ▼
Phase 2: Backend API (Data Access Layer)
    │
    ├── 2.1 Axie endpoints
    ├── 2.2 Market endpoints
    ├── 2.3 Background jobs
    └── 2.4 Caching
           │
           ▼
Phase 3: Frontend Core (User Interface)
    │
    ├── 3.1 Project setup
    ├── 3.2 Explorer page
    ├── 3.3 Detail page
    └── 3.4 Dashboard
           │
           ▼
Phase 4: Breeding & Analytics
    │
    ├── 4.1 Breeding backend
    ├── 4.2 Breeding UI
    ├── 4.3 Price history
    └── 4.4 Analytics UI
           │
           ▼
Phase 5: Advanced Features
    │
    ├── 5.1 Wallet backend
    ├── 5.2 Wallet UI
    ├── 5.3 Arbitrage
    ├── 5.4 Alerts
    └── 5.5 Best pairs
```

---

## Getting Started

### Recommended First Steps

1. **Set up development environment**
   ```bash
   cd /Users/alex/Ronin_API

   # Backend
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install fastapi uvicorn sqlalchemy alembic httpx redis celery

   # Start services
   docker-compose up -d db redis
   ```

2. **Get API keys**
   - Sign up at https://admin.moralis.io/ for Moralis API
   - Register at https://developers.skymavis.com/ for Sky Mavis API

3. **Create initial backend structure**
   ```bash
   # Create main.py, implement health check
   # Create config.py for settings
   # Implement database connection
   ```

4. **Implement gene parser**
   - This is a standalone utility with no dependencies
   - Can be tested immediately with sample gene data
   - Critical for all Axie-related features

### Success Metrics

| Metric | Target |
|--------|--------|
| API Response Time (p95) | < 200ms |
| Listing Sync Delay | < 5 minutes |
| Price History Retention | 1 year |
| Breeding Calc Accuracy | 99%+ |
| Uptime | 99.5% |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| API rate limits | Implement caching, batch requests |
| Data accuracy | Cross-validate with on-chain data |
| Gene parser bugs | Extensive unit tests, reference implementation |
| Database growth | TimescaleDB compression, retention policies |
| External API changes | Version API clients, monitoring alerts |
