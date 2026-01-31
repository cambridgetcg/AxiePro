# Foundation Task: B4 - Fix Rate Limiting

**Status**: CURRENT BLOCKER
**Priority**: P0 (Critical)
**Blocks**: All data flow to W1

## Problem Statement

All Lambda data ingestion functions are failing with HTTP 429 (Too Many Requests) from SkyMavis API. Without fixing this, no new data enters the system.

```
Error fetching beast: Client error '429 Too Many Requests'
for url 'https://api-gateway.skymavis.com/graphql/axie-marketplace'
```

## Root Cause Analysis

1. **Concurrent requests**: Multiple Lambda functions hitting API simultaneously
2. **Aggressive frequency**: Price ingestion every 5 min, all functions together
3. **No backoff**: Simple retry without exponential delay
4. **No circuit breaker**: Keeps hammering failing API
5. **No caching**: Repeated requests for same data

## Current State

| Component | Current | Issue |
|-----------|---------|-------|
| `skymavis_client.py:299-316` | Simple counter rate limit | Resets too fast, no global coordination |
| `skymavis_client.py:276-280` | Waits on 429, retries immediately | No exponential backoff |
| `compute-stack.ts:486` | 5 min interval | Too frequent |
| `compute-stack.ts:494` | 15 min interval | Multiple concurrent with price |
| No circuit breaker | - | Keeps failing |

## Solution Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    NEW RATE LIMITING STACK                      │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │ Token Bucket │───▶│ Circuit      │───▶│ Exponential  │      │
│  │ Rate Limiter │    │ Breaker      │    │ Backoff      │      │
│  │ (10 req/min) │    │ (5 failures) │    │ (2-60s)      │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                   │                   │               │
│         └───────────────────┴───────────────────┘               │
│                             │                                   │
│                             ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Response Cache                         │  │
│  │              (Redis, 5-15 min TTL)                        │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    REDUCED FREQUENCIES                          │
│                                                                 │
│  price_ingestion:    5 min  →  15 min (3x reduction)           │
│  sales_ingestion:   15 min  →  30 min (2x reduction)           │
│  listings_ingestion: 5 min  →  15 min (3x reduction)           │
│  meta_analyzer:     60 min  →  60 min (unchanged)              │
│                                                                 │
│  STAGGER: Offset start times to prevent concurrent requests    │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Tasks

### Task 4.1: Add Tenacity Exponential Backoff

**File**: `backend/src/services/skymavis_client.py`

```python
# Add to imports
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import httpx

# Wrap _graphql_request with retry
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
async def _graphql_request_with_retry(self, ...):
    ...
```

**Validation**:
```bash
cd backend && python -c "
import asyncio
from src.services.skymavis_client import SkyMavisClient
async def test():
    async with SkyMavisClient() as client:
        # Should retry with backoff on 429
        result = await client.get_axie(1)
        print(result)
asyncio.run(test())
"
```

---

### Task 4.2: Implement Token Bucket Rate Limiter

**File**: `backend/src/services/rate_limiter.py` (NEW)

```python
"""
Token bucket rate limiter for SkyMavis API.
"""
import asyncio
import time
import logging

logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter.

    Allows burst up to max_tokens, then refills at rate_per_second.
    """

    def __init__(
        self,
        requests_per_minute: int = 10,
        burst_size: int = 5,
    ):
        self.rate_per_second = requests_per_minute / 60.0
        self.max_tokens = burst_size
        self.tokens = float(burst_size)
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, timeout: float = 60.0) -> bool:
        """
        Acquire a token, waiting if necessary.

        Returns True if token acquired, False if timeout.
        """
        start = time.monotonic()

        while True:
            async with self._lock:
                self._refill()

                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return True

            # Calculate wait time
            elapsed = time.monotonic() - start
            if elapsed >= timeout:
                return False

            # Wait for approximately one token
            wait_time = min(1.0 / self.rate_per_second, timeout - elapsed)
            logger.debug(f"Rate limited, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.rate_per_second)
        self.last_refill = now


# Global rate limiter instance
_rate_limiter: TokenBucketRateLimiter | None = None


def get_rate_limiter() -> TokenBucketRateLimiter:
    """Get or create global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = TokenBucketRateLimiter(
            requests_per_minute=10,
            burst_size=5,
        )
    return _rate_limiter
```

---

### Task 4.3: Implement Circuit Breaker

**File**: `backend/src/services/circuit_breaker.py` (NEW)

```python
"""
Circuit breaker pattern for external API resilience.
"""
import asyncio
import time
import logging
from enum import Enum
from typing import Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"        # Normal operation
    OPEN = "open"            # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker for external API calls.

    Opens after failure_threshold consecutive failures.
    Stays open for recovery_timeout seconds.
    Then moves to half-open to test recovery.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 1,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.half_open_calls = 0
        self._lock = asyncio.Lock()

    async def can_execute(self) -> bool:
        """Check if request should be allowed."""
        async with self._lock:
            if self.state == CircuitState.CLOSED:
                return True

            if self.state == CircuitState.OPEN:
                # Check if recovery timeout passed
                if time.monotonic() - self.last_failure_time >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    logger.info("Circuit breaker: OPEN -> HALF_OPEN (testing recovery)")
                    return True
                return False

            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls < self.half_open_max_calls:
                    self.half_open_calls += 1
                    return True
                return False

            return False

    async def record_success(self):
        """Record successful call."""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker: HALF_OPEN -> CLOSED (recovered)")
            else:
                self.failure_count = 0

    async def record_failure(self):
        """Record failed call."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.monotonic()

            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                logger.warning("Circuit breaker: HALF_OPEN -> OPEN (recovery failed)")
            elif self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(
                    f"Circuit breaker: CLOSED -> OPEN "
                    f"(threshold {self.failure_threshold} reached)"
                )


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


# Global circuit breaker instance
_circuit_breaker: CircuitBreaker | None = None


def get_circuit_breaker() -> CircuitBreaker:
    """Get or create global circuit breaker."""
    global _circuit_breaker
    if _circuit_breaker is None:
        _circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
        )
    return _circuit_breaker
```

---

### Task 4.4: Reduce Lambda Trigger Frequencies

**File**: `infrastructure/lib/stacks/compute-stack.ts`

```typescript
// Line ~486: Price ingestion
const priceIngestionRule = new events.Rule(this, 'PriceIngestionRule', {
  ruleName: getResourceName('price-ingestion-trigger', config),
  description: 'Triggers price ingestion every 15 minutes',
  schedule: events.Schedule.rate(cdk.Duration.minutes(15)),  // Changed from 5
  targets: [new targets.LambdaFunction(priceIngestionLambda)],
});

// Line ~494: Sales ingestion
const salesIngestionRule = new events.Rule(this, 'SalesIngestionRule', {
  ruleName: getResourceName('sales-ingestion-trigger', config),
  description: 'Triggers sales ingestion every 30 minutes',
  schedule: events.Schedule.rate(cdk.Duration.minutes(30)),  // Changed from 15
  targets: [new targets.LambdaFunction(salesIngestionLambda)],
});

// Line ~500: Meta analysis (unchanged at 1 hour)
```

**Alternative - Staggered cron schedules**:
```typescript
// Price: 0, 15, 30, 45 past the hour
schedule: events.Schedule.cron({ minute: '0,15,30,45' }),

// Sales: 5, 35 past the hour (offset by 5 min)
schedule: events.Schedule.cron({ minute: '5,35' }),

// Listings: 10, 25, 40, 55 past the hour (offset by 10 min)
schedule: events.Schedule.cron({ minute: '10,25,40,55' }),
```

---

### Task 4.5: Add Response Caching

**File**: `backend/src/services/skymavis_client.py`

```python
# Add caching decorator
from src.services.cache import cache_response

class SkyMavisClient:
    ...

    @cache_response(ttl=300, prefix="skymavis:axie:")
    async def get_axie(self, axie_id: int) -> Optional[AxieData]:
        ...

    @cache_response(ttl=60, prefix="skymavis:floor:")
    async def get_floor_prices(self, classes: Optional[list[str]] = None) -> dict:
        ...
```

---

## Verification Checklist

### Pre-deployment
- [ ] `tenacity` added to requirements.txt
- [ ] Unit tests for rate limiter pass
- [ ] Unit tests for circuit breaker pass
- [ ] Local test shows backoff working

### Post-deployment
- [ ] Lambda logs show no 429 errors
- [ ] CloudWatch metrics show successful invocations
- [ ] Database has new records (< 30 min old)
- [ ] Redis has floor prices populated

### Validation Commands

```bash
# Check for 429 errors (should be 0)
aws logs filter-log-events \
  --log-group-name /aws/lambda/axiepro-price-ingestion-dev \
  --filter-pattern "429" \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --region us-east-1

# Check for successful completions
aws logs filter-log-events \
  --log-group-name /aws/lambda/axiepro-price-ingestion-dev \
  --filter-pattern "SUCCESS" \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --region us-east-1

# Check database freshness
psql -c "SELECT MAX(created_at) as latest FROM price_snapshots"

# Check floor prices API
curl -s https://api.axiepro.io/api/v1/valuation/stats/floors | jq .
```

## Exit Criteria

All of the following must be true:

- [ ] No 429 errors in Lambda logs for 1 hour
- [ ] At least 1 successful price ingestion cycle
- [ ] At least 1 successful sales ingestion cycle
- [ ] Circuit breaker test passes (manual trip and recovery)
- [ ] Rate limiter test passes (burst handling)

## Dependencies

- `tenacity>=8.2.0` - retry with backoff
- `redis>=4.0.0` - already installed for caching

## Rollback Plan

If issues occur:
1. Revert CDK deploy: `cdk deploy --rollback`
2. Disable EventBridge rules in console
3. Restore original `skymavis_client.py` from git

## Notes

- SkyMavis API key may have quota limits beyond rate limiting
- Check API dashboard for usage stats
- Consider reaching out to SkyMavis for higher limits if needed
