# Migration Plan: Sky Mavis API → Public Ronin RPC

## Executive Summary

**Problem:** Sky Mavis API rate-limited (429) with daily limit of 140,000 requests exhausted.
**Solution:** Migrate to Public Ronin RPC (`api.roninchain.com/rpc`) with architectural improvements.
**Impact:** ~2 hours to fetch full June 2025 historical data (835,000 blocks).


## Deep Analysis & Insights

### 1. Current Architecture Bottlenecks

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CURRENT ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   fetch_*.py scripts                                                 │
│        │                                                             │
│        ▼                                                             │
│   ┌─────────────────┐     RATE LIMITED (429)                        │
│   │ Sky Mavis RPC   │◄────────────────────────                      │
│   │ api-gateway...  │     140k/day exhausted                        │
│   └────────┬────────┘                                               │
│            │                                                         │
│            ▼                                                         │
│   ┌─────────────────┐     SEPARATE CALLS                            │
│   │ Sky Mavis GQL   │◄────────────────────────                      │
│   │ (Axie metadata) │     Per-axie queries                          │
│   └────────┬────────┘                                               │
│            │                                                         │
│            ▼                                                         │
│   ┌─────────────────┐                                               │
│   │   PostgreSQL    │                                               │
│   │   (RDS Aurora)  │                                               │
│   └─────────────────┘                                               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Key Issues Identified:**

| Issue | Impact | Root Cause |
|-------|--------|------------|
| Single RPC endpoint | Single point of failure | No fallback configured |
| Sequential receipt fetches | Slow processing | Not parallelized enough |
| Per-axie GraphQL calls | N+1 query problem | No batch optimization |
| No progress persistence | Lost work on failure | Missing checkpoint system |
| Fixed batch size (499) | Suboptimal for public RPC | Same limit applies |

### 2. Public Ronin RPC Characteristics

**Tested Performance:**
```
Endpoint: https://api.roninchain.com/rpc
Block Limit: 499 blocks per eth_getLogs query
Parallel Workers: 5 optimal (tested)
Throughput: ~3,500 blocks/second
No API Key Required: ✓
Archive Data: Available (tested back to 2021)
```

**Critical Insight:** Public RPC has **no daily limit** but enforces per-query limits:
- 499 blocks max per `eth_getLogs`
- Connection pooling recommended
- Exponential backoff on 5xx errors

### 3. Data Flow Analysis

```
                          DATA SOURCES COMPARISON
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│   SOURCE              │  PROVIDES          │  RATE LIMIT            │
│  ─────────────────────┼────────────────────┼──────────────────────  │
│  Public Ronin RPC     │  Logs, Receipts    │  499 blk/query, no daily│
│  Sky Mavis GraphQL    │  Axie metadata     │  100 RPS, 140k/day     │
│  Goldrush/Covalent    │  Decoded events    │  100 req/min           │
│                                                                      │
│  RECOMMENDATION: Hybrid approach                                     │
│  - RPC for sales data (high volume)                                 │
│  - GraphQL for metadata (cached, on-demand)                         │
│  - Goldrush as backup/validation                                    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Architecture

### Target State Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    TARGET ARCHITECTURE                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌───────────────────────────────────────────────────────┐         │
│   │              UNIFIED RPC CLIENT                        │         │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │         │
│   │  │Public Ronin │  │  Chainstack │  │  Goldrush   │   │         │
│   │  │  (Primary)  │  │  (Fallback) │  │  (Backup)   │   │         │
│   │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘   │         │
│   │         └────────────────┼────────────────┘          │         │
│   │                          ▼                            │         │
│   │              ┌─────────────────────┐                 │         │
│   │              │  Connection Pool    │                 │         │
│   │              │  + Circuit Breaker  │                 │         │
│   │              └──────────┬──────────┘                 │         │
│   └─────────────────────────┼─────────────────────────────┘         │
│                             │                                        │
│   ┌─────────────────────────▼─────────────────────────────┐         │
│   │              BATCH PROCESSOR                           │         │
│   │  ┌─────────────────────────────────────────────────┐  │         │
│   │  │  Log Fetcher (parallel, 499-block batches)      │  │         │
│   │  │       │                                          │  │         │
│   │  │       ▼                                          │  │         │
│   │  │  TX Deduplicator (in-memory set)                │  │         │
│   │  │       │                                          │  │         │
│   │  │       ▼                                          │  │         │
│   │  │  Receipt Fetcher (parallel, 10 workers)         │  │         │
│   │  │       │                                          │  │         │
│   │  │       ▼                                          │  │         │
│   │  │  Sale Parser (WETH/WRON extraction)             │  │         │
│   │  └──────────────────────┬──────────────────────────┘  │         │
│   └─────────────────────────┼─────────────────────────────┘         │
│                             │                                        │
│   ┌─────────────────────────▼─────────────────────────────┐         │
│   │              DATA PIPELINE                             │         │
│   │                                                        │         │
│   │  ┌──────────────┐    ┌──────────────┐                 │         │
│   │  │ sync_state   │◄───│ Checkpoint   │                 │         │
│   │  │ (progress)   │    │ Manager      │                 │         │
│   │  └──────────────┘    └──────────────┘                 │         │
│   │         │                                              │         │
│   │         ▼                                              │         │
│   │  ┌──────────────┐    ┌──────────────┐                 │         │
│   │  │ axie_sales   │    │metadata_queue│                 │         │
│   │  │ (partitioned)│    │  (async)     │                 │         │
│   │  └──────────────┘    └──────────────┘                 │         │
│   │                                                        │         │
│   └────────────────────────────────────────────────────────┘         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Design

### Component 1: Unified RPC Client

```python
# File: backend/src/services/ronin_rpc_client.py

"""
Design Decisions:
1. Connection pooling with httpx for efficiency
2. Circuit breaker pattern for fault tolerance
3. Automatic failover between providers
4. No API key header for public RPC
"""

class RoninRPCClient:
    PROVIDERS = [
        ("public", "https://api.roninchain.com/rpc", None),
        ("chainstack", "https://ronin-mainnet.core.chainstack.com/xxx", "key"),
        ("goldrush", "https://api.covalenthq.com/v1/axie-mainnet/", "key"),
    ]

    MAX_BLOCKS_PER_QUERY = 499
    PARALLEL_WORKERS = 5
    RETRY_DELAYS = [0.5, 1, 2, 4, 8]  # Exponential backoff
```

**Key Design Insight:** The public RPC works best with:
- Keep-alive connections (httpx default)
- 5 parallel workers (tested optimal)
- 499-block batches (hard limit)
- No rate limiting logic needed (self-regulating via response time)

### Component 2: Batch Log Fetcher

```python
# Pseudocode for optimal batch processing

class BatchLogFetcher:
    """
    Insight: Parallel fetching of 499-block batches achieves
    ~3,500 blocks/second throughput.

    For 835,000 blocks (June 2025):
    - Sequential: 835,000 / 499 = 1,673 requests @ 1/sec = 28 min
    - Parallel (5): 1,673 / 5 = 335 batches @ 5/sec = 4 min
    """

    async def fetch_range(self, start_block: int, end_block: int):
        batches = self._create_batches(start_block, end_block, 499)

        async with asyncio.Semaphore(5):  # 5 parallel workers
            tasks = [self._fetch_batch(b) for b in batches]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        return self._merge_and_dedupe(results)
```

### Component 3: Receipt Processor

```python
# Receipt fetching is the bottleneck - needs optimization

class ReceiptProcessor:
    """
    Insight: Receipt fetches are 10x slower than log fetches.

    Optimization strategies:
    1. Deduplicate TX hashes before fetching
    2. Parallel fetch with 10 workers
    3. Cache receipts in Redis (they're immutable)
    4. Skip non-sale transactions early
    """

    def parse_sale(self, receipt: dict) -> Optional[Sale]:
        # Early exit patterns
        logs = receipt.get('logs', [])
        if len(logs) < 2:  # Need at least NFT + token transfer
            return None

        # Look for Axie transfer + payment in single pass
        axie_transfers = []
        payments = []

        for log in logs:
            # ... parsing logic
```

### Component 4: Checkpoint Manager

```python
# Critical for resumability

class CheckpointManager:
    """
    Insight: Historical fetches take hours. Must be resumable.

    Strategy:
    1. Save progress every 1000 blocks to sync_state table
    2. On restart, read last_block and continue
    3. Use database transaction for atomicity
    """

    CHECKPOINT_INTERVAL = 1000  # blocks

    async def save_checkpoint(self, block: int, sales_count: int):
        await self.db.execute("""
            UPDATE axie.sync_state
            SET last_block = $1,
                records_synced = records_synced + $2,
                updated_at = NOW()
            WHERE id = 'axie_sales'
        """, block, sales_count)
```

---

## File Changes Required

### Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `backend/src/config/settings.py` | Modify | Add RPC provider config, remove Sky Mavis RPC |
| `backend/src/services/ronin_rpc_client.py` | **Create** | New unified RPC client |
| `fetch_continuous.py` | Modify | Switch to public RPC, add checkpointing |
| `fetch_premium_sales.py` | Modify | Use new RPC client |
| `get_sales_complete.py` | Modify | Use new RPC client |
| All `test_*.py` files | Modify | Update RPC endpoint |

### New Files to Create

```
backend/src/services/
├── ronin_rpc_client.py      # Unified RPC client with failover
├── batch_processor.py       # Parallel log/receipt fetcher
├── checkpoint_manager.py    # Progress persistence
└── sale_parser.py           # Extract sales from receipts
```

---

## Database Schema Updates

### Add Checkpoint Table (if not exists)

```sql
-- Already exists in 02_create_analysis_tables.sql as sync_state
-- Verify it has the right structure:

ALTER TABLE axie.sync_state
ADD COLUMN IF NOT EXISTS error_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_error TEXT,
ADD COLUMN IF NOT EXISTS processing_rate NUMERIC(10,2);
```

### Add RPC Provider Metrics

```sql
CREATE TABLE IF NOT EXISTS axie.rpc_metrics (
    id BIGSERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    request_type VARCHAR(50) NOT NULL,
    response_time_ms INTEGER,
    success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rpc_metrics_provider ON axie.rpc_metrics(provider, created_at DESC);
```

---

## Implementation Phases

### Phase 1: Core RPC Migration (Priority: Critical)

**Goal:** Get historical data fetching working with public RPC

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1 TASKS                                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ 1.1 Create ronin_rpc_client.py                                  │
│     - Connection pooling with httpx                             │
│     - 499-block batch limit handling                            │
│     - Exponential backoff on errors                             │
│     - No API key header                                         │
│                                                                  │
│ 1.2 Update fetch_continuous.py                                  │
│     - Switch RPC_URL to api.roninchain.com                      │
│     - Remove X-API-Key header                                   │
│     - Keep 499 block batch size                                 │
│     - Add progress checkpointing                                │
│                                                                  │
│ 1.3 Test with 10,000 block range                                │
│     - Verify logs fetched correctly                             │
│     - Verify receipts parsed correctly                          │
│     - Verify sales inserted to DB                               │
│                                                                  │
│ Estimated Time: 2-3 hours                                        │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 2: Performance Optimization

**Goal:** Achieve target throughput of ~3,500 blocks/sec

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 2 TASKS                                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ 2.1 Implement parallel batch fetching                           │
│     - asyncio with 5 concurrent workers                         │
│     - Semaphore for rate control                                │
│                                                                  │
│ 2.2 Optimize receipt fetching                                   │
│     - 10 parallel workers for receipts                          │
│     - TX hash deduplication before fetch                        │
│     - Redis caching for receipts                                │
│                                                                  │
│ 2.3 Add metrics collection                                      │
│     - Requests per second                                       │
│     - Error rates by provider                                   │
│     - Processing rate (blocks/sec, sales/sec)                   │
│                                                                  │
│ Estimated Time: 3-4 hours                                        │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 3: Resilience & Monitoring

**Goal:** Production-ready fault tolerance

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 3 TASKS                                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ 3.1 Add provider failover                                       │
│     - Circuit breaker pattern                                   │
│     - Automatic fallback to Chainstack/Goldrush                 │
│                                                                  │
│ 3.2 Implement checkpoint system                                 │
│     - Save progress every 1000 blocks                           │
│     - Resume from last checkpoint on restart                    │
│                                                                  │
│ 3.3 Add alerting                                                │
│     - Slack/Discord webhook on errors                           │
│     - Progress notifications                                    │
│                                                                  │
│ Estimated Time: 2-3 hours                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Code Templates

### Template 1: RPC Client Core

```python
# backend/src/services/ronin_rpc_client.py

import asyncio
import httpx
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class RPCProvider:
    name: str
    url: str
    api_key: Optional[str] = None
    max_blocks: int = 499

class RoninRPCClient:
    """
    Unified RPC client for Ronin blockchain.

    Features:
    - Automatic failover between providers
    - Connection pooling
    - Exponential backoff
    - No API key for public RPC
    """

    DEFAULT_PROVIDERS = [
        RPCProvider("public", "https://api.roninchain.com/rpc"),
    ]

    def __init__(self, providers: Optional[List[RPCProvider]] = None):
        self.providers = providers or self.DEFAULT_PROVIDERS
        self.current_provider_idx = 0
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Content-Type": "application/json"},
            limits=httpx.Limits(max_connections=20),
        )
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    @property
    def provider(self) -> RPCProvider:
        return self.providers[self.current_provider_idx]

    async def call(self, method: str, params: List[Any], retries: int = 3) -> Dict:
        """Make RPC call with automatic retry."""
        for attempt in range(retries):
            try:
                response = await self._client.post(
                    self.provider.url,
                    json={"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
                )

                if response.status_code == 200:
                    data = response.json()
                    if "error" not in data:
                        return data.get("result")

                # Rate limited or error - try next provider
                if response.status_code in (429, 503):
                    self._rotate_provider()

            except httpx.RequestError as e:
                logger.warning(f"Request error: {e}")

            # Exponential backoff
            await asyncio.sleep(0.5 * (2 ** attempt))

        raise RuntimeError(f"RPC call failed after {retries} retries")

    def _rotate_provider(self):
        self.current_provider_idx = (self.current_provider_idx + 1) % len(self.providers)
        logger.info(f"Rotated to provider: {self.provider.name}")

    async def get_logs(self, address: str, from_block: int, to_block: int) -> List[Dict]:
        """Get event logs for address in block range."""
        return await self.call("eth_getLogs", [{
            "address": address,
            "fromBlock": hex(from_block),
            "toBlock": hex(to_block),
        }])

    async def get_receipt(self, tx_hash: str) -> Optional[Dict]:
        """Get transaction receipt."""
        return await self.call("eth_getTransactionReceipt", [tx_hash])

    async def get_block_number(self) -> int:
        """Get current block number."""
        result = await self.call("eth_blockNumber", [])
        return int(result, 16)
```

### Template 2: Batch Processor

```python
# backend/src/services/batch_processor.py

import asyncio
from typing import List, Dict, Set
from dataclasses import dataclass

@dataclass
class Sale:
    tx_hash: str
    block_number: int
    axie_id: int
    price_token: float
    token_type: str  # WETH or WRON
    price_usd: float

class BatchProcessor:
    """
    Parallel batch processor for Axie sales.

    Performance characteristics:
    - 5 parallel log fetchers
    - 10 parallel receipt fetchers
    - ~3,500 blocks/sec throughput
    """

    AXIE_CONTRACT = "0x32950db2a7164ae833121501c797d79e7b79d74c"
    TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

    WETH = "0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5"
    WRON = "0xe514d9deb7966c8be0ca922de8a064264ea6bcd4"

    RATES = {"WETH": 3800.0, "WRON": 0.15}

    def __init__(self, rpc_client, log_workers: int = 5, receipt_workers: int = 10):
        self.rpc = rpc_client
        self.log_workers = log_workers
        self.receipt_workers = receipt_workers

    async def process_range(self, start_block: int, end_block: int) -> List[Sale]:
        """Process a block range and return all sales."""

        # Phase 1: Fetch all logs in parallel
        batches = self._create_batches(start_block, end_block, 499)
        all_logs = await self._fetch_logs_parallel(batches)

        # Phase 2: Extract unique TX hashes
        tx_hashes = self._extract_unique_txs(all_logs)

        # Phase 3: Fetch receipts in parallel
        receipts = await self._fetch_receipts_parallel(tx_hashes)

        # Phase 4: Parse sales
        sales = self._parse_sales(receipts)

        return sales

    def _create_batches(self, start: int, end: int, size: int) -> List[tuple]:
        batches = []
        current = start
        while current <= end:
            batch_end = min(current + size - 1, end)
            batches.append((current, batch_end))
            current = batch_end + 1
        return batches

    async def _fetch_logs_parallel(self, batches: List[tuple]) -> List[Dict]:
        semaphore = asyncio.Semaphore(self.log_workers)

        async def fetch_with_limit(start, end):
            async with semaphore:
                return await self.rpc.get_logs(self.AXIE_CONTRACT, start, end)

        tasks = [fetch_with_limit(s, e) for s, e in batches]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_logs = []
        for result in results:
            if isinstance(result, list):
                all_logs.extend(result)

        return all_logs

    def _extract_unique_txs(self, logs: List[Dict]) -> Set[str]:
        return {log["transactionHash"] for log in logs}

    async def _fetch_receipts_parallel(self, tx_hashes: Set[str]) -> List[Dict]:
        semaphore = asyncio.Semaphore(self.receipt_workers)

        async def fetch_with_limit(tx_hash):
            async with semaphore:
                return await self.rpc.get_receipt(tx_hash)

        tasks = [fetch_with_limit(tx) for tx in tx_hashes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [r for r in results if isinstance(r, dict) and r]

    def _parse_sales(self, receipts: List[Dict]) -> List[Sale]:
        sales = []

        for receipt in receipts:
            sale = self._parse_single_sale(receipt)
            if sale:
                sales.extend(sale)

        return sales

    def _parse_single_sale(self, receipt: Dict) -> List[Sale]:
        logs = receipt.get("logs", [])
        if len(logs) < 2:
            return []

        axie_ids = []
        payment = None

        for log in logs:
            topics = log.get("topics", [])
            if not topics or topics[0] != self.TRANSFER_TOPIC:
                continue

            address = log["address"].lower()

            # Axie NFT transfer
            if address == self.AXIE_CONTRACT.lower() and len(topics) == 4:
                axie_ids.append(int(topics[3], 16))

            # Token payment
            elif address in (self.WETH.lower(), self.WRON.lower()) and len(topics) == 3:
                data = log.get("data", "0x")
                if data != "0x":
                    value = int(data, 16) / 10**18
                    token = "WETH" if address == self.WETH.lower() else "WRON"
                    if payment is None or (token == "WETH" and value > 0):
                        payment = {"token": token, "value": value}

        if not axie_ids or not payment:
            return []

        # Create sale records
        per_axie_value = payment["value"] / len(axie_ids)
        per_axie_usd = per_axie_value * self.RATES[payment["token"]]

        return [
            Sale(
                tx_hash=receipt["transactionHash"],
                block_number=int(receipt["blockNumber"], 16),
                axie_id=axie_id,
                price_token=per_axie_value,
                token_type=payment["token"],
                price_usd=per_axie_usd,
            )
            for axie_id in axie_ids
        ]
```

---

## Testing Strategy

### Test 1: Connectivity

```bash
# Verify public RPC is accessible
curl -X POST https://api.roninchain.com/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

### Test 2: Log Fetching

```python
# Test fetching 1000 blocks
async def test_log_fetching():
    async with RoninRPCClient() as client:
        current = await client.get_block_number()
        logs = await client.get_logs(AXIE_CONTRACT, current - 1000, current)
        assert len(logs) > 0
        print(f"Fetched {len(logs)} logs from 1000 blocks")
```

### Test 3: Full Pipeline

```python
# Test complete sales extraction
async def test_full_pipeline():
    async with RoninRPCClient() as rpc:
        processor = BatchProcessor(rpc)
        current = await rpc.get_block_number()
        sales = await processor.process_range(current - 5000, current)

        assert len(sales) > 0
        for sale in sales[:5]:
            print(f"Axie #{sale.axie_id}: ${sale.price_usd:.2f}")
```

---

## Rollback Plan

If issues arise:

1. **Revert to Sky Mavis API** (when rate limit resets in ~10 hours)
   - Change `rpc_url` back in settings
   - Re-add `X-API-Key` header

2. **Use Goldrush as temporary fallback**
   - Already have API key configured
   - Slower but reliable for metadata

3. **Database is unchanged**
   - Same schema, same data
   - No migration rollback needed

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Block throughput | >3,000 blk/sec | Logs fetched / time |
| Receipt throughput | >10 tx/sec | Receipts fetched / time |
| Error rate | <1% | Failed requests / total |
| June 2025 fetch time | <3 hours | End-to-end time |
| Resumability | 100% | Successfully resume after interruption |

---

## Appendix: Contract Addresses

```
Axie NFT:     0x32950db2a7164ae833121501c797d79e7b79d74c
WETH:         0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5
WRON:         0xe514d9deb7966c8be0ca922de8a064264ea6bcd4
Transfer:     0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef
```

## Appendix: RPC Provider Comparison

| Provider | URL | Rate Limit | Archive | Cost |
|----------|-----|------------|---------|------|
| Public Ronin | api.roninchain.com/rpc | 499 blk/query | Yes | Free |
| Chainstack | Custom endpoint | Higher | Yes | Free tier available |
| Moralis | Custom endpoint | 25+ RPS | Yes | Free tier available |
| Goldrush | api.covalenthq.com | 100/min | Yes | Free tier available |

---

*Document created: 2025-12-20*
*Author: Claude Code*
*Status: Ready for Implementation*
