# AxiePro Access Inventory

**Generated:** December 15, 2025
**Purpose:** Comprehensive list of all API and infrastructure access for Axie Infinity market analysis

---

## AWS Infrastructure

### Account
- **Account ID:** 034362054546
- **IAM User:** YuCheung
- **Region:** us-east-1

### RDS PostgreSQL Databases
| Instance | Status | Endpoint |
|----------|--------|----------|
| cardforum | available | cardforum.cn4c2su0o42n.us-east-1.rds.amazonaws.com |
| op-price-data-instance-1 | available | op-price-data-instance-1.cn4c2su0o42n.us-east-1.rds.amazonaws.com |
| tcgpricingdata | available | tcgpricingdata.cn4c2su0o42n.us-east-1.rds.amazonaws.com |

### Secrets Manager
Secrets available for secure API key storage:
- `axie-explorer/api-keys` - **Contains GOLDRUSH_API_KEY and SKYMAVIS_API_KEY**
- `trading-card-pricer/api-keys`
- `Shopify/Update_Price/APIKey`
- Multiple RDS credentials

---

## Hosting & Domains

### Cloudflare Pages
- **Project:** axiepro
- **Production URL:** https://axiepro.io
- **Domains:** axiepro.io, www.axiepro.io

### Frontend Stack
- Next.js 14 (Static Export)
- Tailwind CSS + shadcn/ui
- TypeScript

---

## External APIs

### Sky Mavis GraphQL API (Primary Data Source)

**Endpoint:** `https://api-gateway.skymavis.com/graphql/marketplace`
**Auth:** X-API-Key header
**Status:** ACTIVE

#### Available Data Points

##### Marketplace Listings
- **Total Axies for Sale:** 153,956
- **Current Floor Price:** $2.08 (Plant class)

##### Axie Detail Fields
| Field | Description | Trading Value |
|-------|-------------|---------------|
| `id` | Unique Axie identifier | Reference |
| `name` | User-assigned name | - |
| `class` | Beast, Plant, Aquatic, Bird, Bug, Reptile, Mech, Dawn, Dusk | HIGH |
| `breedCount` | 0-7 breeding uses | HIGH |
| `genes` | 256-bit genetic code | HIGH |
| `image` | Full transparent PNG URL | Display |
| `birthDate` | Unix timestamp | Medium |
| `owner` | Ronin wallet address | Tracking |
| `stats.hp` | Health points (27-61) | HIGH |
| `stats.speed` | Speed stat (27-61) | HIGH |
| `stats.skill` | Skill stat (27-61) | HIGH |
| `stats.morale` | Morale stat (27-61) | HIGH |
| `parts` | 6 body parts with class/type | HIGH |
| `order.currentPriceUsd` | Current listing price | HIGH |
| `order.maker` | Seller address | Tracking |
| `order.startedAt` | Listing start time | Medium |
| `order.basePrice` | Starting auction price | HIGH |
| `order.endedPrice` | Ending auction price | HIGH |

##### Query Capabilities
| Feature | Query Parameter | Trading Value |
|---------|-----------------|---------------|
| Filter by Class | `criteria:{classes:[Beast]}` | HIGH |
| Filter by Breed Count | `criteria:{breedCount:[0,1,2]}` | HIGH |
| Filter by Parts | `criteria:{parts:["mouth-nut-cracker"]}` | HIGH |
| Sort by Price | `sort:PriceAsc` or `sort:PriceDesc` | HIGH |
| Pagination | `from:0, size:100` | - |
| Sale Type | `auctionType:Sale` | - |

##### Recently Sold (settledAuctions)
```graphql
{ settledAuctions { axies(from:0,size:100) { total results { id class } } } }
```
**Status:** Working - Returns last 100 settled auctions (IDs only, no prices)

---

### Sky Mavis Ronin RPC (SALES HISTORY WITH PRICES)

**Endpoint:** `https://api-gateway.skymavis.com/rpc`
**Auth:** X-API-Key header
**Status:** ACTIVE - CRITICAL FOR PRICE TRACKING

#### How to Get Sales with Prices

The GraphQL API doesn't expose historical sale prices, but the RPC endpoint does via blockchain event logs:

1. **Get Axie NFT Transfer events** from contract `0x32950db2a7164ae833121501c797d79e7b79d74c`
2. **Get transaction receipt** for each transfer
3. **Parse WETH/WRON payment** from ERC20 Transfer events in same transaction

#### Sample Sales Data (Live Test)
```
Recent Sales (last ~25 minutes):
Axie #92605    |  0.000650 WETH | $2.05 USD
Axie #2949661  |  0.000660 WETH | $2.08 USD
Axie #3153054  |  0.000660 WETH | $2.08 USD
Axie #12183368 |  0.000665 WETH | $2.10 USD
...
Total sales: 64 | Median: $2.12 | Average: $2.26
```

#### Payment Token Addresses (Ronin Chain)
| Token | Address | Decimals | USD Rate Source |
|-------|---------|----------|-----------------|
| WETH | `0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5` | 18 | GraphQL exchangeRate (eth.usd) |
| WRON | `0xe514d9deb7966c8be0ca922de8a064264ea6bcd4` | 18 | GraphQL exchangeRate (ron.usd) |
| SLP | `0xa8754b9fa15fc18bb59458815510e40a12cd2014` | 0 | External |
| AXS | `0x97a9107c1793bc407d6f527b77e7fff4d812bece` | 18 | GraphQL exchangeRate |

**Note:** Most Axie sales use WETH. Floor price Axies trade at ~0.00065 WETH (~$2 USD).

#### RPC Limits
- Max 500 blocks per `eth_getLogs` query
- ~3 sec/block = ~25 min of history per query
- Can paginate backwards for longer history

---

### Goldrush (Covalent) API

**Endpoint:** `https://api.covalenthq.com/v1/axie-mainnet/`
**Auth:** Basic auth with API key
**Status:** ACTIVE (Limited Axie Support)

#### Available Endpoints
| Endpoint | Description | Trading Value |
|----------|-------------|---------------|
| `/address/{wallet}/balances_v2/` | Token balances (RON, AXS, SLP) | Medium |
| `/address/{wallet}/transactions_v3/` | Transaction history | Medium |
| `/address/{wallet}/balances_nft/` | NFT holdings | Low (limited metadata) |

**Note:** Goldrush provides blockchain transaction data but limited Axie-specific metadata. Use Sky Mavis for detailed Axie data.

---

### Sky Mavis Origins API

**Base URL:** `https://api-gateway.skymavis.com/origins/v2/`
**Status:** ACTIVE

| Endpoint | Description | Trading Value |
|----------|-------------|---------------|
| `/community/items` | Game items | Low |
| `/community/cards` | Card data | Low |

---

## CRUCIAL DATA FOR MARKET TREND ANALYSIS

### Tier 1: Essential for Profitable Trading

#### 1. Floor Prices by Class
```
Current Market Snapshot:
Beast      - 16,745 listed
Plant      - 35,938 listed (highest supply)
Aquatic    - 32,846 listed
Bird       - 12,095 listed
Bug        - 8,216 listed (lowest pure class)
Reptile    - 18,613 listed
Mech       - 8,913 listed
Dawn       - 4,769 listed (lowest supply - rare)
Dusk       - 15,721 listed
```
**Strategy:** Dawn/Mech have lower supply - potential for higher prices. Track supply changes.

#### 2. Breed Count Distribution
```
Breed Count 0: 64,954 listed (42% - virgins command premium)
Breed Count 1: 16,140 listed
Breed Count 2: 28,033 listed
Breed Count 3: 29,004 listed
Breed Count 4: 11,908 listed
Breed Count 5: 3,012 listed
Breed Count 6: 690 listed
Breed Count 7: 216 listed (max bred - lowest value)
```
**Strategy:** Virgin (0 breed) Axies have highest breeding value. Monitor breed count pricing differentials.

#### 3. Parts-Based Pricing (Meta Analysis)
- Query specific parts combinations to find undervalued Axies
- Example: "Nut Cracker mouth" - 8,632 listed, Floor: $2.11
- **Strategy:** Track meta-relevant parts (competitive builds) vs floor price

#### 4. Stats Optimization
```
Stats Range: 27-61 per stat (164 total)
Classes determine base stats allocation
Parts modify stats based on their class
```
**Strategy:** Find Axies with stats optimized for their build at floor prices

### Tier 2: Important for Breeding Profit

#### 1. Gene Analysis
- 256-bit genetic code determines:
  - Dominant genes (visible parts)
  - Recessive genes (R1, R2)
  - Hidden genes for breeding outcomes
- **Strategy:** Target Axies with pure genes for breeding predictability

#### 2. Class Purity
- Pure class Axies (6 parts matching class) have premium
- Mixed Axies may have strategic part combinations
- **Strategy:** Calculate purity premium vs strategic mixing value

#### 3. Breeding Economics
```
Breeding Cost: SLP + AXS (varies by breed count)
Higher breed count = higher breeding cost
Output value depends on gene inheritance
```
**Strategy:** Calculate expected breeding ROI based on parent genes

### Tier 3: Market Intelligence (CRITICAL - NOW ACCESSIBLE)

#### 1. Sales History with Prices (via RPC)
- **Method:** Parse Axie NFT transfers + WETH/WRON payment events from blockchain
- **Coverage:** Full history available by paginating blocks backwards
- **Data:** Axie ID, sale price (WETH/WRON), USD value, buyer/seller addresses, timestamp
- **Strategy:** Build historical price database for trend analysis, identify undervalued listings

#### 2. Volume Tracking
- Real-time sales volume in 25-minute windows (500 blocks)
- Track daily/weekly volume trends
- **Strategy:** Identify market momentum, time entries/exits

#### 3. Wallet Tracking
- Monitor large holders/breeders for market moves
- Track breeding activity of successful players
- **Strategy:** Follow smart money patterns

#### 4. Price Trend Analysis
- Compare current listing prices vs recent sale prices
- Identify bid-ask spreads by class/parts/breed count
- **Strategy:** Find arbitrage opportunities

---

## Recommended Data Collection Pipeline

### Daily Collection
1. Floor prices by class (9 classes)
2. Total listings count
3. Breed count distribution
4. Top 100 recent sales

### Hourly Collection (High Priority)
1. Lowest 10 listings per class
2. Virgin (0 breed) floor price
3. Meta-relevant parts floor prices

### Real-time Alerts
1. Large sales (>$100)
2. Significant floor price movements (>5%)
3. New listings matching criteria

---

## Database Schema Recommendations

### Core Tables for Market Analysis
```sql
-- Price history tracking
axie_price_history (axie_id, timestamp, price_usd, sale_type)

-- Axie metadata cache
axie_metadata (axie_id, class, breed_count, genes, stats_json, parts_json)

-- Market snapshots
market_snapshots (timestamp, class, floor_price, total_listed, avg_price)

-- Parts pricing
parts_pricing (part_id, part_name, class, floor_price, total_with_part, timestamp)
```

---

## Action Items

1. **Build sales history collector** - Use RPC to collect historical sales with prices (script ready: `get_sales_complete.py`)
2. **Build price tracking pipeline** - Collect floor prices hourly via GraphQL
3. **Implement gene decoder** - Parse 256-bit genes for breeding analysis
4. **Create alert system** - Notify on undervalued listings vs recent sale prices
5. **Track meta parts** - Monitor competitive build parts pricing
6. **Build breeding calculator** - Expected offspring value calculator
7. **Create price database** - Store historical sales for trend analysis

## Working Scripts

| Script | Purpose |
|--------|---------|
| `test_all_apis.sh` | Test all API endpoints |
| `test_market_data.sh` | Get floor prices by class, breed count distribution |
| `get_sales_complete.py` | Get recent sales with USD prices from RPC |
| `test_schema.py` | Verify available GraphQL fields |

---

## API Rate Limits (Estimated)

| API | Rate Limit | Notes |
|-----|------------|-------|
| Sky Mavis GraphQL | ~100 req/min | Unconfirmed, test carefully |
| Sky Mavis RPC | ~100 req/min | Max 500 blocks per getLogs query |
| Goldrush | 5 req/sec | Based on plan tier |

---

## Security Notes

- All API keys stored in AWS Secrets Manager
- Never commit keys to repository
- Use IAM roles for production deployments
- Rotate keys periodically
