# Axie Metadata API Implementation Plan

**Date:** 2025-12-20
**Status:** Research Complete

## Executive Summary

Implement a metadata enrichment system to fetch Axie class, breed count, and other attributes for ~49,167 axies missing metadata. The existing queue-based infrastructure can be reused with a high-throughput batch fetcher.

## Current State

| Metric | Value |
|--------|-------|
| Unique Axies in Sales | 49,313 |
| Axies with Metadata | 146 |
| **Missing Metadata** | **49,167** |
| Coverage | 0.3% |

## API Research Findings

### Endpoint

```
URL: https://api-gateway.skymavis.com/graphql/marketplace
Method: POST
Auth: X-API-Key header
```

### Batch Query Support ✅

The API supports **aliased batch queries** - multiple axies in one request:

```graphql
{
    axie1: axie(axieId: "12345") { id name class breedCount parts { ... } }
    axie2: axie(axieId: "12346") { id name class breedCount parts { ... } }
    axie3: axie(axieId: "12347") { id name class breedCount parts { ... } }
}
```

**Performance:** 3 axies in ~211ms = ~70ms per axie

### Rate Limits

| Finding | Value |
|---------|-------|
| Tested | 10 rapid requests |
| Rate limited | 0 |
| Auth required | Yes (X-API-Key) |

Rate limits are tiered (Basic → Intermediate → Advanced) via the Ronin Developer Console. Current key appears to have generous limits.

### Query Structure

```graphql
query GetAxieDetails($axieId: ID!) {
    axie(axieId: $axieId) {
        id
        name
        class
        breedCount
        genes
        image
        owner
        birthDate
        stats { hp speed skill morale }
        parts {
            id
            name
            class
            type
            specialGenes
        }
    }
}
```

### Response Example

```json
{
  "data": {
    "axie": {
      "id": "12345",
      "name": "Lucky Charmz",
      "class": "Beast",
      "breedCount": 2,
      "parts": [
        {"id": "eyes-telescope", "name": "Telescope", "class": "Aquatic", "type": "Eyes"},
        {"id": "ears-clover", "name": "Clover", "class": "Plant", "type": "Ears"},
        ...
      ],
      "stats": {"hp": 42, "speed": 40, "skill": 31, "morale": 51}
    }
  }
}
```

## Existing Infrastructure

### Database Tables

```sql
-- Metadata storage
axie_metadata (
    axie_id, name, class, breed_count, genes,
    hp, speed, skill, morale,
    parts_json, part_eyes, part_ears, part_mouth, part_horn, part_back, part_tail,
    pure_part_count, birth_date, image_url, owner
)

-- Queue for pending fetches
metadata_fetch_queue (
    axie_id, status, priority, retry_count, max_retries,
    next_retry_at, created_at, completed_at, last_error
)
```

### Stored Procedures

| Procedure | Purpose |
|-----------|---------|
| `queue_metadata_fetch(axie_id, source, priority)` | Add to queue |
| `get_fetch_batch(batch_size)` | Get pending items |
| `get_retry_batch(batch_size)` | Get failed items for retry |
| `mark_fetch_completed(axie_id)` | Mark as done |
| `mark_fetch_failed(axie_id, error, permanent)` | Mark as failed |
| `process_metadata_complete(axie_id)` | Full workflow: mark complete → backfill sales → populate parts |

### Existing Script

`fetch_axie_metadata.py` - Queue-based fetcher (single axie per request)

## Implementation Strategy

### Option A: Enhance Existing Script (Recommended)

Modify `fetch_axie_metadata.py` to use batch queries:

```python
async def fetch_batch(axie_ids: list[int], batch_size=20) -> dict:
    """Fetch multiple axies in one GraphQL request."""
    query_parts = []
    for i, axie_id in enumerate(axie_ids[:batch_size]):
        query_parts.append(f'''
            axie{i}: axie(axieId: "{axie_id}") {{
                id name class breedCount genes image owner birthDate
                stats {{ hp speed skill morale }}
                parts {{ id name class type specialGenes }}
            }}
        ''')

    query = "{ " + " ".join(query_parts) + " }"
    response = await graphql_call(query)

    results = {}
    for i, axie_id in enumerate(axie_ids[:batch_size]):
        results[axie_id] = response.get(f'axie{i}')

    return results
```

### Option B: New High-Throughput Script

Create `fetch_metadata_batch.py` with:
- Async HTTP client (httpx)
- Batch size of 20 axies per request
- Parallel requests (3-5 concurrent)
- Progress tracking and checkpointing

## Estimated Performance

| Approach | Axies/Request | Requests/sec | Axies/sec | Time for 49K |
|----------|---------------|--------------|-----------|--------------|
| Current (single) | 1 | 10 | 10 | ~82 minutes |
| Batch (20) | 20 | 5 | 100 | ~8 minutes |
| Batch + Parallel | 20 × 3 | 5 | 300 | ~3 minutes |

## Implementation Plan

### Phase 1: Queue Population (5 min)

```sql
-- Add all axies without metadata to queue
INSERT INTO metadata_fetch_queue (axie_id, first_seen_in, priority)
SELECT DISTINCT s.axie_id, 'backfill', 5
FROM axie_sales s
WHERE NOT EXISTS (
    SELECT 1 FROM axie_metadata m WHERE m.axie_id = s.axie_id
)
ON CONFLICT (axie_id) DO NOTHING;
```

### Phase 2: Create Batch Fetcher

Create `fetch_metadata_batch.py`:

```python
#!/usr/bin/env python3
"""
High-throughput Axie metadata fetcher using batch GraphQL queries.

Features:
- Batch queries (20 axies per request)
- Async HTTP with concurrency control
- Queue-based workflow integration
- Progress tracking
"""

import asyncio
import json
import subprocess
import httpx
import psycopg2
from datetime import datetime

# Configuration
BATCH_SIZE = 20
MAX_CONCURRENT = 3
GRAPHQL_URL = 'https://api-gateway.skymavis.com/graphql/marketplace'

class BatchMetadataFetcher:
    def __init__(self):
        self.api_key = self._get_api_key()
        self.db_config = self._get_db_config()

    def _get_api_key(self):
        result = subprocess.run([
            'aws', 'secretsmanager', 'get-secret-value',
            '--secret-id', 'axie-explorer/api-keys',
            '--query', 'SecretString', '--output', 'text',
            '--region', 'us-east-1'
        ], capture_output=True, text=True)
        return json.loads(result.stdout).get('SKYMAVIS_API_KEY')

    async def fetch_batch(self, client, axie_ids):
        """Fetch multiple axies in one request."""
        query_parts = []
        for i, axie_id in enumerate(axie_ids):
            query_parts.append(f'''
                axie{i}: axie(axieId: "{axie_id}") {{
                    id name class breedCount genes image owner birthDate
                    stats {{ hp speed skill morale }}
                    parts {{ id name class type specialGenes }}
                }}
            ''')

        query = "{ " + " ".join(query_parts) + " }"

        response = await client.post(
            GRAPHQL_URL,
            json={"query": query},
            headers={'X-API-Key': self.api_key, 'Content-Type': 'application/json'}
        )

        data = response.json().get('data', {})
        return {axie_ids[i]: data.get(f'axie{i}') for i in range(len(axie_ids))}

    async def process_queue(self):
        """Main processing loop."""
        conn = psycopg2.connect(**self.db_config)
        cur = conn.cursor()
        cur.execute("SET search_path TO axie, public")

        # Get pending count
        cur.execute("SELECT COUNT(*) FROM metadata_fetch_queue WHERE status = 'pending'")
        total = cur.fetchone()[0]
        print(f"Processing {total:,} pending axies...")

        async with httpx.AsyncClient(timeout=30) as client:
            processed = 0
            while True:
                # Get batch from queue
                cur.execute("SELECT * FROM get_fetch_batch(%s)", (BATCH_SIZE,))
                batch = [row[0] for row in cur.fetchall()]

                if not batch:
                    break

                # Fetch metadata
                results = await self.fetch_batch(client, batch)

                # Process results
                for axie_id, axie_data in results.items():
                    if axie_data:
                        self._insert_metadata(cur, axie_id, axie_data)
                        cur.execute("CALL process_metadata_complete(%s)", (axie_id,))
                    else:
                        cur.execute("SELECT mark_fetch_failed(%s, %s, %s)",
                                    (axie_id, "Axie not found", True))

                conn.commit()
                processed += len(batch)

                if processed % 100 == 0:
                    print(f"[{processed}/{total}] {processed/total*100:.1f}%")

        print(f"Complete! Processed {processed} axies.")
        conn.close()

if __name__ == "__main__":
    fetcher = BatchMetadataFetcher()
    asyncio.run(fetcher.process_queue())
```

### Phase 3: Run on EC2

```bash
# Deploy to EC2
scp fetch_metadata_batch.py ec2-user@3.91.12.195:/home/ec2-user/axie/

# SSH and run
ssh ec2-user@3.91.12.195
cd /home/ec2-user/axie
nohup python3 -u fetch_metadata_batch.py > metadata_batch.log 2>&1 &
```

### Phase 4: Verify & Backfill Sales

```sql
-- Verify coverage
SELECT
    COUNT(DISTINCT s.axie_id) as sales_axies,
    COUNT(DISTINCT m.axie_id) as with_metadata,
    ROUND(COUNT(DISTINCT m.axie_id)::numeric / COUNT(DISTINCT s.axie_id) * 100, 1) as coverage_pct
FROM axie_sales s
LEFT JOIN axie_metadata m ON s.axie_id = m.axie_id;

-- Backfill class in axie_sales (already handled by process_metadata_complete)
-- But for bulk backfill:
UPDATE axie_sales s
SET class = m.class, breed_count = m.breed_count
FROM axie_metadata m
WHERE s.axie_id = m.axie_id AND s.class IS NULL;
```

## Risk Mitigation

### Rate Limiting

- Start conservatively (1 batch/sec)
- Monitor for 429 responses
- Implement exponential backoff

### API Errors

- Log failed axie_ids
- Use retry queue with exponential backoff
- Mark permanently failed (burned axies) as `status = 'not_found'`

### Data Consistency

- Use transactions for insert + queue update
- Verify with `process_metadata_complete()` stored procedure

## Monitoring

```bash
# Queue status
psql -c "SELECT status, COUNT(*) FROM axie.metadata_fetch_queue GROUP BY status"

# Progress
psql -c "SELECT COUNT(*) FROM axie.axie_metadata"

# Coverage
psql -c "SELECT COUNT(DISTINCT s.axie_id) as total, COUNT(DISTINCT m.axie_id) as with_meta
         FROM axie.axie_sales s LEFT JOIN axie.axie_metadata m ON s.axie_id = m.axie_id"
```

## Timeline Estimate

| Task | Duration |
|------|----------|
| Queue population | 1 min |
| Create batch script | 30 min |
| Deploy to EC2 | 5 min |
| Run metadata fetch | 10-30 min |
| Verify & cleanup | 5 min |
| **Total** | **~1 hour** |

## Next Steps

1. ✅ Research complete (API works, batch supported)
2. ⏳ Populate queue with missing axie_ids
3. ⏳ Create batch fetcher script
4. ⏳ Deploy and run on EC2
5. ⏳ Verify coverage and data quality

## References

- [Sky Mavis Developer Portal](https://docs.skymavis.com/)
- [Rate Limits Documentation](https://docs.skymavis.com/api/rate-limits)
- [Unofficial GraphQL Docs](https://github.com/ShaneMaglangit/axie-graphql-documentation)
- Existing code: `fetch_axie_metadata.py`, `backend/src/services/skymavis_client.py`
