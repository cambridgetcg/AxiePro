"""
Price Ingestion Lambda

Runs every 15 minutes to capture price snapshots from the marketplace.
Stores data in Aurora PostgreSQL for trend analysis.

Uses rate limiting and circuit breaker for API resilience.
"""

import asyncio
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import httpx
from aws_lambda_powertools.metrics import MetricUnit

# Import shared utilities from common module
from src.lambdas.common import (
    logger,
    tracer,
    metrics,
    get_secrets,
    get_db_connection,
    get_skymavis_endpoint,
    get_skymavis_headers,
    check_graphql_errors,
    GraphQLError,
    safe_validate_price_wei,
    ValidationError,
    TRACKED_PARTS_BY_CLASS,
    PARTS_SAMPLE_SIZE,
    HTTP_TIMEOUT_SECONDS,
)

# Import rate limiting components
from src.services.rate_limiter import get_skymavis_rate_limiter
from src.services.circuit_breaker import get_skymavis_circuit_breaker, CircuitOpenError


# GraphQL query for floor prices
FLOOR_PRICE_QUERY = """
query GetMarketplaceFloors($classes: [AxieClass!], $parts: [String!], $sort: SortBy, $size: Int) {
  axies(
    auctionType: Sale
    criteria: { classes: $classes, parts: $parts }
    sort: $sort
    size: $size
  ) {
    results {
      id
      class
      order {
        currentPrice
        currentPriceUsd
      }
      parts {
        id
        name
        type
        class
      }
    }
    total
  }
}
"""


@tracer.capture_method
async def fetch_floor_prices(
    client: httpx.AsyncClient,
    axie_class: str,
    part_id: Optional[str] = None,
    api_key: Optional[str] = None,
    internal_secret: Optional[str] = None,
    rate_limiter=None,
    circuit_breaker=None,
) -> dict:
    """Fetch floor prices for a specific class and optional part.

    Uses rate limiting and circuit breaker for API resilience.
    """
    # Check circuit breaker first
    if circuit_breaker and not await circuit_breaker.can_execute():
        recovery_time = circuit_breaker.time_until_recovery()
        logger.warning(f"Circuit breaker open, skipping request. Recovery in {recovery_time:.1f}s")
        raise CircuitOpenError(f"Circuit breaker open, recovery in {recovery_time:.1f}s")

    # Acquire rate limit token
    if rate_limiter:
        acquired = await rate_limiter.acquire(timeout=30.0)
        if not acquired:
            logger.warning("Rate limiter timeout, skipping request")
            raise Exception("Rate limiter timeout")

    variables = {
        "classes": [axie_class.capitalize()],
        "sort": "PriceAsc",
        "size": 10,
    }
    if part_id:
        variables["parts"] = [part_id]

    headers = get_skymavis_headers(api_key, internal_secret)
    endpoint = get_skymavis_endpoint()

    try:
        response = await client.post(
            endpoint,
            json={"query": FLOOR_PRICE_QUERY, "variables": variables},
            headers=headers,
        )

        # Handle rate limiting from API
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 30))
            # Cap retry wait to avoid Lambda timeout - let the next scheduled run handle it
            max_wait = 10  # Max 10 seconds wait within Lambda
            if retry_after > max_wait:
                logger.warning(
                    f"API rate limited (429), retry_after={retry_after}s exceeds max_wait={max_wait}s, failing fast"
                )
                if circuit_breaker:
                    await circuit_breaker.record_failure(Exception("Rate limited - long wait"))
                raise httpx.HTTPStatusError(
                    f"Rate limited (retry_after={retry_after}s)",
                    request=response.request,
                    response=response
                )
            logger.warning(f"API rate limited (429), waiting {retry_after}s")
            if circuit_breaker:
                await circuit_breaker.record_failure(Exception("Rate limited"))
            await asyncio.sleep(retry_after)
            raise httpx.HTTPStatusError(
                f"Rate limited",
                request=response.request,
                response=response
            )

        response.raise_for_status()

        result = response.json()
        check_graphql_errors(result)  # Raise if GraphQL errors present

        # Record success
        if circuit_breaker:
            await circuit_breaker.record_success()

        return result

    except Exception as e:
        if circuit_breaker:
            await circuit_breaker.record_failure(e)
        raise


@tracer.capture_method
def calculate_statistics(axies: list) -> dict:
    """Calculate floor, average, and volume from axie list."""
    if not axies:
        return {"floor_eth": None, "avg_eth": None, "count": 0}

    prices = []
    for axie in axies:
        if axie.get("order") and axie["order"].get("currentPrice"):
            price_wei = axie["order"]["currentPrice"]
            # Use validation utility for bounds checking
            price_eth, error = safe_validate_price_wei(
                price_wei, f"price for axie {axie.get('id', 'unknown')}"
            )
            if error:
                logger.debug(f"Skipping invalid price: {error}")
                continue
            prices.append(price_eth)

    if not prices:
        return {"floor_eth": None, "avg_eth": None, "count": 0}

    return {
        "floor_eth": min(prices),
        "avg_eth": sum(prices) / len(prices),
        "count": len(prices),
    }


@tracer.capture_method
def store_snapshot(conn, timestamp: datetime, trait_key: str, axie_class: str, stats: dict):
    """Store price snapshot in database."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO price_snapshots (time, trait_key, class, floor_eth, avg_eth, listings_count)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (time, trait_key, class) DO UPDATE SET
                floor_eth = EXCLUDED.floor_eth,
                avg_eth = EXCLUDED.avg_eth,
                listings_count = EXCLUDED.listings_count
            """,
            (
                timestamp,
                trait_key,
                axie_class,
                stats["floor_eth"],
                stats["avg_eth"],
                stats["count"],
            ),
        )
    conn.commit()


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def handler(event, context):
    """Lambda handler for price ingestion."""
    timestamp = datetime.now(timezone.utc)
    logger.info(f"Starting price ingestion at {timestamp}")

    # Initialize rate limiting components
    rate_limiter = get_skymavis_rate_limiter()
    circuit_breaker = get_skymavis_circuit_breaker()

    logger.info(
        "Rate limiting initialized",
        extra={
            "rate_limit": f"{rate_limiter.requests_per_minute} req/min",
            "circuit_breaker_state": circuit_breaker.state.value,
        },
    )

    async def ingest():
        conn = get_db_connection()
        secrets = get_secrets()
        api_key = secrets.get("SKYMAVIS_API_KEY")
        internal_secret = secrets.get("INTERNAL_SECRET")

        logger.info(
            "API configuration",
            extra={
                "has_api_key": bool(api_key),
                "api_key_prefix": api_key[:8] if api_key else None,
                "endpoint": get_skymavis_endpoint(),
            },
        )

        snapshots_stored = 0
        errors_count = 0

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
                # Fetch class-level floor prices
                for axie_class in TRACKED_PARTS_BY_CLASS.keys():
                    try:
                        result = await fetch_floor_prices(
                            client,
                            axie_class,
                            api_key=api_key,
                            internal_secret=internal_secret,
                            rate_limiter=rate_limiter,
                            circuit_breaker=circuit_breaker,
                        )
                        axies = result.get("data", {}).get("axies", {}).get("results", [])
                        stats = calculate_statistics(axies)

                        store_snapshot(conn, timestamp, f"class:{axie_class}", axie_class, stats)
                        snapshots_stored += 1

                        metrics.add_metric(
                            name=f"FloorPrice_{axie_class}",
                            unit=MetricUnit.Count,
                            value=float(stats["floor_eth"]) if stats["floor_eth"] else 0
                        )

                    except CircuitOpenError as e:
                        logger.warning(f"Circuit open, skipping {axie_class}: {e}")
                        errors_count += 1
                        break  # Stop making requests when circuit is open

                    except Exception as e:
                        logger.error(f"Error fetching {axie_class}: {e}")
                        errors_count += 1
                        metrics.add_metric(name="IngestionErrors", unit=MetricUnit.Count, value=1)

                # Skip part-level if circuit is open
                if circuit_breaker.state.value == "open":
                    logger.warning("Circuit breaker open, skipping part-level prices")
                else:
                    # Fetch part-level floor prices (sample parts)
                    for axie_class, parts in TRACKED_PARTS_BY_CLASS.items():
                        for part_id in parts[:PARTS_SAMPLE_SIZE]:
                            try:
                                result = await fetch_floor_prices(
                                    client,
                                    axie_class,
                                    part_id,
                                    api_key=api_key,
                                    internal_secret=internal_secret,
                                    rate_limiter=rate_limiter,
                                    circuit_breaker=circuit_breaker,
                                )
                                axies = result.get("data", {}).get("axies", {}).get("results", [])
                                stats = calculate_statistics(axies)

                                store_snapshot(conn, timestamp, f"part:{part_id}", axie_class, stats)
                                snapshots_stored += 1

                            except CircuitOpenError:
                                logger.warning(f"Circuit open, stopping part-level ingestion")
                                break

                            except Exception as e:
                                logger.error(f"Error fetching {axie_class}/{part_id}: {e}")
                                errors_count += 1

                        # Check if circuit opened during loop
                        if circuit_breaker.state.value == "open":
                            break

        finally:
            conn.close()

        # Log final circuit breaker state
        logger.info(
            "Ingestion complete",
            extra={
                "circuit_breaker_state": circuit_breaker.state.value,
                "circuit_breaker_failures": circuit_breaker.failure_count,
            },
        )

        return snapshots_stored, errors_count

    snapshots, errors = asyncio.run(ingest())

    metrics.add_metric(name="SnapshotsStored", unit=MetricUnit.Count, value=snapshots)

    # Publish circuit breaker metrics for CloudWatch alarms
    circuit_state = circuit_breaker.state.value
    metrics.add_metric(
        name="CircuitBreakerOpen",
        unit=MetricUnit.Count,
        value=1 if circuit_state == "open" else 0
    )
    metrics.add_metric(
        name="CircuitBreakerFailures",
        unit=MetricUnit.Count,
        value=circuit_breaker.failure_count
    )

    logger.info(f"Stored {snapshots} price snapshots, {errors} errors")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Price ingestion complete",
            "snapshots_stored": snapshots,
            "errors": errors,
            "timestamp": timestamp.isoformat(),
        }),
    }
