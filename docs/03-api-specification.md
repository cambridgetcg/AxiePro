# API Specification

## Overview

The REST API provides endpoints for Axie discovery, market analysis, breeding calculations, and wallet tracking. All responses are JSON.

**Base URL**: `http://localhost:8000/api/v1`

## Authentication

Public endpoints require no authentication. Rate limiting applies:
- Anonymous: 100 requests/minute
- Authenticated: 1000 requests/minute (future feature)

## Common Response Format

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "total": 1000,
    "page": 1,
    "per_page": 20,
    "total_pages": 50
  }
}
```

Error responses:
```json
{
  "success": false,
  "error": {
    "code": "AXIE_NOT_FOUND",
    "message": "Axie with ID 12345 not found"
  }
}
```

---

## Endpoints

### Axies

#### GET /axies

Search and filter Axies.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `class` | string | Filter by class (beast, bug, bird, etc.) |
| `classes` | string | Multiple classes, comma-separated |
| `purity` | int | Minimum purity score (0-6) |
| `breed_count` | int | Maximum breed count (0-7) |
| `parts` | string | Required parts, comma-separated (e.g., `mouth:nut-cracker,horn:little-branch`) |
| `parts_match` | string | `all` (default) or `any` |
| `gene_type` | string | Gene type for parts filter: `d`, `r1`, `r2`, `any` (default: `d`) |
| `min_price` | float | Minimum listing price (ETH) |
| `max_price` | float | Maximum listing price (ETH) |
| `listed_only` | bool | Only return listed Axies |
| `owner` | string | Filter by owner wallet address |
| `sort` | string | Sort field: `price`, `purity`, `id`, `breed_count` |
| `order` | string | `asc` or `desc` |
| `page` | int | Page number (default: 1) |
| `per_page` | int | Results per page (default: 20, max: 100) |

**Example Request:**
```
GET /axies?class=beast&purity=6&parts=mouth:nut-cracker&listed_only=true&sort=price&order=asc
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 12345678,
      "name": "Beastie Boy",
      "class": "beast",
      "breed_count": 2,
      "purity_score": 6,
      "image_url": "https://axiecdn.com/axies/12345678/axie.png",
      "owner": "0x1234...abcd",
      "stats": {
        "hp": 31,
        "speed": 35,
        "skill": 31,
        "morale": 43
      },
      "parts": {
        "eyes": { "d": "Chubby", "r1": "Chubby", "r2": "Papi" },
        "ears": { "d": "Nut Cracker", "r1": "Nut Cracker", "r2": "Puppy" },
        "mouth": { "d": "Nut Cracker", "r1": "Axie Kiss", "r2": "Nut Cracker" },
        "horn": { "d": "Little Branch", "r1": "Imp", "r2": "Little Branch" },
        "back": { "d": "Ronin", "r1": "Ronin", "r2": "Hero" },
        "tail": { "d": "Cottontail", "r1": "Hare", "r2": "Cottontail" }
      },
      "listing": {
        "price_eth": 0.025,
        "price_usd": 45.50,
        "listed_at": "2025-01-15T10:30:00Z"
      }
    }
  ],
  "meta": {
    "total": 156,
    "page": 1,
    "per_page": 20,
    "total_pages": 8
  }
}
```

#### GET /axies/{id}

Get detailed information for a single Axie.

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 12345678,
    "name": "Beastie Boy",
    "class": "beast",
    "breed_count": 2,
    "genes": "0x0000000000000000...",
    "purity_score": 6,
    "gene_purity_score": 14,
    "image_url": "https://axiecdn.com/axies/12345678/axie.png",
    "owner": "0x1234...abcd",
    "birth_date": "2022-03-15T08:00:00Z",
    "matron_id": 11111111,
    "sire_id": 22222222,
    "stats": {
      "hp": 31,
      "speed": 35,
      "skill": 31,
      "morale": 43
    },
    "parts": {
      "eyes": {
        "d": { "id": "eyes-chubby", "name": "Chubby", "class": "beast" },
        "r1": { "id": "eyes-chubby", "name": "Chubby", "class": "beast" },
        "r2": { "id": "eyes-papi", "name": "Papi", "class": "bug" }
      }
      // ... other parts
    },
    "abilities": [
      {
        "name": "Nut Cracker",
        "part": "mouth",
        "damage": 105,
        "shield": 30,
        "energy": 1,
        "description": "Apply 2 Fragile to target."
      }
    ],
    "listing": {
      "id": 999,
      "price_eth": 0.025,
      "price_usd": 45.50,
      "listed_at": "2025-01-15T10:30:00Z",
      "expires_at": "2025-02-15T10:30:00Z"
    },
    "sales_history": [
      {
        "price_eth": 0.030,
        "price_usd": 54.00,
        "sold_at": "2024-12-01T14:00:00Z",
        "seller": "0xaaaa...bbbb",
        "buyer": "0x1234...abcd"
      }
    ],
    "children": [12345679, 12345680]
  }
}
```

#### GET /axies/{id}/siblings

Get Axies with the same parents.

#### GET /axies/{id}/children

Get all offspring of this Axie.

---

### Market Data

#### GET /market/listings

Get current marketplace listings.

**Query Parameters:**
- Same filters as `/axies` endpoint
- `marketplace` - Filter by marketplace: `official`, `all`

#### GET /market/sales

Get recent sales.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `class` | string | Filter by Axie class |
| `min_price` | float | Minimum sale price (ETH) |
| `max_price` | float | Maximum sale price (ETH) |
| `from_date` | string | Start date (ISO 8601) |
| `to_date` | string | End date (ISO 8601) |
| `seller` | string | Seller wallet address |
| `buyer` | string | Buyer wallet address |
| `sort` | string | `date`, `price` |
| `page` | int | Page number |
| `per_page` | int | Results per page |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 555,
      "axie_id": 12345678,
      "axie_class": "beast",
      "axie_purity": 6,
      "price_eth": 0.025,
      "price_usd": 45.50,
      "sold_at": "2025-01-15T10:30:00Z",
      "seller": "0xaaaa...bbbb",
      "buyer": "0xcccc...dddd",
      "tx_hash": "0x..."
    }
  ]
}
```

#### GET /market/floor-prices

Get current floor prices by class and traits.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `class` | string | Filter by class |
| `group_by` | string | `class`, `purity`, `part` |
| `part_type` | string | If group_by=part: `mouth`, `horn`, `back`, `tail` |

**Response:**
```json
{
  "success": true,
  "data": {
    "timestamp": "2025-01-15T12:00:00Z",
    "floors": [
      {
        "class": "beast",
        "purity": 6,
        "floor_eth": 0.018,
        "floor_usd": 32.40,
        "count": 245
      },
      {
        "class": "beast",
        "purity": 5,
        "floor_eth": 0.012,
        "floor_usd": 21.60,
        "count": 512
      }
    ]
  }
}
```

#### GET /market/stats

Get market-wide statistics.

**Response:**
```json
{
  "success": true,
  "data": {
    "24h": {
      "volume_eth": 125.5,
      "volume_usd": 225900,
      "sales_count": 4521,
      "avg_price_eth": 0.0277,
      "median_price_eth": 0.015,
      "unique_buyers": 892,
      "unique_sellers": 756
    },
    "7d": { ... },
    "30d": { ... }
  }
}
```

---

### Price History

#### GET /prices/history

Get historical price data for traits.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `trait_key` | string | Trait identifier (e.g., `class:beast`, `mouth:nut-cracker`) |
| `class` | string | Filter by class |
| `interval` | string | `1h`, `4h`, `1d`, `1w` |
| `from_date` | string | Start date |
| `to_date` | string | End date |

**Response:**
```json
{
  "success": true,
  "data": {
    "trait_key": "mouth:nut-cracker",
    "class": "beast",
    "interval": "1d",
    "history": [
      {
        "timestamp": "2025-01-14T00:00:00Z",
        "floor_eth": 0.022,
        "avg_eth": 0.028,
        "median_eth": 0.025,
        "volume": 45,
        "volume_eth": 1.26
      },
      {
        "timestamp": "2025-01-15T00:00:00Z",
        "floor_eth": 0.020,
        "avg_eth": 0.026,
        "median_eth": 0.023,
        "volume": 52,
        "volume_eth": 1.35
      }
    ]
  }
}
```

#### GET /prices/compare

Compare prices across multiple traits.

**Query Parameters:**
- `traits` - Comma-separated trait keys
- `interval` - Time interval
- `from_date`, `to_date` - Date range

---

### Breeding

#### POST /breeding/simulate

Simulate breeding outcomes.

**Request Body:**
```json
{
  "matron_id": 12345678,
  "sire_id": 87654321
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "matron": {
      "id": 12345678,
      "class": "beast",
      "breed_count": 2
    },
    "sire": {
      "id": 87654321,
      "class": "beast",
      "breed_count": 1
    },
    "cost": {
      "axs": 0.5,
      "slp": 900,
      "total_usd": 12.50
    },
    "class_probabilities": {
      "beast": 0.875,
      "mech": 0.0625,
      "dusk": 0.0625
    },
    "part_probabilities": {
      "mouth": [
        { "part": "Nut Cracker", "class": "beast", "probability": 0.46875 },
        { "part": "Tiny Turtle", "class": "reptile", "probability": 0.28125 },
        { "part": "Axie Kiss", "class": "beast", "probability": 0.15625 },
        { "part": "Cute Bunny", "class": "beast", "probability": 0.09375 }
      ],
      "horn": [ ... ],
      "back": [ ... ],
      "tail": [ ... ]
    },
    "expected_outcomes": [
      {
        "description": "6-purity Beast with Nut Cracker mouth",
        "probability": 0.125,
        "estimated_value_eth": 0.035,
        "expected_value_eth": 0.00437
      },
      {
        "description": "5-purity Beast",
        "probability": 0.35,
        "estimated_value_eth": 0.018,
        "expected_value_eth": 0.0063
      }
    ],
    "total_expected_value_eth": 0.022,
    "roi": {
      "expected_profit_eth": 0.0095,
      "expected_profit_usd": 17.10,
      "break_even_probability": 0.68
    }
  }
}
```

#### GET /breeding/history

Get breeding history for an Axie.

**Query Parameters:**
- `axie_id` - Axie ID
- `role` - `matron`, `sire`, `both` (default)

#### GET /breeding/best-pairs

Find optimal breeding pairs.

**Query Parameters:**
- `axie_id` - Your Axie's ID
- `target_traits` - Desired traits in offspring
- `max_cost_usd` - Maximum breeding cost
- `min_roi` - Minimum expected ROI

---

### Wallets

#### GET /wallets/{address}

Get wallet overview.

**Response:**
```json
{
  "success": true,
  "data": {
    "address": "0x1234...abcd",
    "alias": "WhaleTrader",
    "first_seen": "2021-06-15T00:00:00Z",
    "last_active": "2025-01-15T14:30:00Z",
    "holdings": {
      "axie_count": 45,
      "total_value_eth": 2.5,
      "total_value_usd": 4500
    },
    "trading_stats": {
      "total_buys": 234,
      "total_sells": 189,
      "total_volume_eth": 15.6,
      "realized_profit_eth": 3.2,
      "win_rate": 0.72
    },
    "class_distribution": {
      "beast": 12,
      "plant": 8,
      "aquatic": 10,
      "bird": 8,
      "bug": 4,
      "reptile": 3
    }
  }
}
```

#### GET /wallets/{address}/axies

Get Axies owned by wallet.

**Query Parameters:**
- Same as `/axies` filters
- `include_value` - Include estimated value

#### GET /wallets/{address}/trades

Get trading history.

**Query Parameters:**
- `type` - `buy`, `sell`, `all`
- `from_date`, `to_date` - Date range
- `page`, `per_page` - Pagination

---

### Analytics

#### GET /analytics/trending

Get trending traits and Axie types.

**Response:**
```json
{
  "success": true,
  "data": {
    "trending_up": [
      {
        "trait_key": "mouth:nut-cracker",
        "class": "beast",
        "price_change_24h": 0.15,
        "volume_change_24h": 0.45
      }
    ],
    "trending_down": [ ... ],
    "most_traded": [ ... ],
    "highest_volume": [ ... ]
  }
}
```

#### GET /analytics/arbitrage

Find potential arbitrage opportunities.

**Query Parameters:**
- `min_discount` - Minimum discount from fair value (default: 0.1 = 10%)
- `max_price` - Maximum price to consider
- `class` - Filter by class

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "axie_id": 12345678,
      "class": "beast",
      "purity": 6,
      "listing_price_eth": 0.018,
      "estimated_value_eth": 0.025,
      "discount": 0.28,
      "comparable_sales": [
        { "axie_id": 11111111, "price_eth": 0.024, "sold_at": "..." },
        { "axie_id": 22222222, "price_eth": 0.026, "sold_at": "..." }
      ]
    }
  ]
}
```

#### GET /analytics/whale-activity

Track large wallet movements.

---

### Parts & Abilities

#### GET /parts

List all body parts.

**Query Parameters:**
- `class` - Filter by class
- `type` - Filter by type (mouth, horn, back, tail, eyes, ears)

#### GET /parts/{part_id}

Get part details including ability.

#### GET /abilities

List all abilities.

---

## Webhooks (Future)

```
POST /webhooks
{
  "url": "https://your-server.com/webhook",
  "events": ["sale.created", "listing.created"],
  "filters": {
    "class": "beast",
    "min_price_eth": 0.1
  }
}
```

---

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_PARAMS` | 400 | Invalid query parameters |
| `AXIE_NOT_FOUND` | 404 | Axie ID not found |
| `WALLET_NOT_FOUND` | 404 | Wallet address not found |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |
| `EXTERNAL_API_ERROR` | 502 | Upstream API failure |
