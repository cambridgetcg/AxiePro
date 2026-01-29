"""
Sales Ingestion Lambda

Runs every 30 minutes to capture settled marketplace sales.
Fetches from Sky Mavis GraphQL API and stores in Aurora PostgreSQL.

Uses rate limiting and circuit breaker for API resilience.
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any

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
    safe_validate_timestamp,
    ValidationError,
    retry_on_transient_error,
    HTTP_TIMEOUT_SECONDS,
)

# Import rate limiting components
from src.services.rate_limiter import get_skymavis_rate_limiter
from src.services.circuit_breaker import get_skymavis_circuit_breaker, CircuitOpenError


# GraphQL query for recently sold axies with transfer history
SETTLED_AUCTIONS_QUERY = """
query GetSettledAuctions($from: Int!, $size: Int!) {
  settledAuctions {
    axies(from: $from, size: $size, sort: Latest) {
      total
      results {
        id
        class
        transferHistory {
          timestamp
          txHash
          withPrice
          withPriceUsd
          from
          to
        }
      }
    }
  }
}
"""


@tracer.capture_method
async def fetch_settled_sales(
    client: httpx.AsyncClient,
    page_from: int = 0,
    page_size: int = 50,
    api_key: Optional[str] = None,
    internal_secret: Optional[str] = None,
    rate_limiter=None,
    circuit_breaker=None,
) -> Dict[str, Any]:
    """Fetch settled auction sales from Sky Mavis API.

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
        "from": page_from,
        "size": page_size,
    }

    headers = get_skymavis_headers(api_key, internal_secret)
    endpoint = get_skymavis_endpoint()

    try:
        response = await client.post(
            endpoint,
            json={"query": SETTLED_AUCTIONS_QUERY, "variables": variables},
            headers=headers,
        )

        # Handle rate limiting from API
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 30))
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
def parse_sales_from_response(response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse sales data from GraphQL response.

    Extracts the most recent sale from each axie's transfer history.
    """
    sales = []

    axies_data = (
        response_data.get("data", {})
        .get("settledAuctions", {})
        .get("axies", {})
        .get("results", [])
    )

    for axie in axies_data:
        axie_id = axie.get("id")
        axie_class = axie.get("class", "Unknown")
        transfers = axie.get("transferHistory", [])

        if not axie_id or not transfers:
            continue

        # Find transfers with price (these are sales, not gifts)
        for transfer in transfers:
            price_wei = transfer.get("withPrice")
            if not price_wei:
                continue

            tx_hash = transfer.get("txHash")
            timestamp = transfer.get("timestamp")
            seller = transfer.get("from")
            buyer = transfer.get("to")
            price_usd = transfer.get("withPriceUsd")

            if not all([tx_hash, timestamp, seller, buyer]):
                continue

            # Validate and convert price using validation utility
            price_eth, price_error = safe_validate_price_wei(
                price_wei, f"price for axie {axie_id}"
            )
            if price_error:
                logger.warning(price_error)
                continue

            # Validate timestamp using validation utility
            sold_at, ts_error = safe_validate_timestamp(
                timestamp, f"timestamp for axie {axie_id}"
            )
            if ts_error:
                logger.warning(ts_error)
                continue

            sales.append({
                "axie_id": int(axie_id),
                "class_": axie_class,
                "seller_address": seller.lower() if seller else None,
                "buyer_address": buyer.lower() if buyer else None,
                "price_eth": price_eth,
                "price_usd": Decimal(str(price_usd)) if price_usd else None,
                "tx_hash": tx_hash,
                "sold_at": sold_at,
                "marketplace": "official",
            })

    return sales


@tracer.capture_method
def store_sales(conn, sales: List[Dict[str, Any]]) -> int:
    """
    Store sales in database with deduplication.

    Uses ON CONFLICT DO NOTHING on tx_hash to avoid duplicates.
    Returns the number of new sales inserted.
    """
    if not sales:
        return 0

    inserted = 0

    with conn.cursor() as cur:
        for sale in sales:
            try:
                cur.execute(
                    """
                    INSERT INTO sales (
                        axie_id, seller_address, buyer_address,
                        price_eth, price_usd, tx_hash, sold_at, marketplace
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (tx_hash) DO NOTHING
                    """,
                    (
                        sale["axie_id"],
                        sale["seller_address"],
                        sale["buyer_address"],
                        sale["price_eth"],
                        sale["price_usd"],
                        sale["tx_hash"],
                        sale["sold_at"],
                        sale["marketplace"],
                    ),
                )
                if cur.rowcount > 0:
                    inserted += 1
            except Exception as e:
                logger.error(f"Error inserting sale {sale.get('tx_hash')}: {e}")
                continue

        conn.commit()

    return inserted


@tracer.capture_method
def get_cutoff_timestamp(conn, hours: int = 48) -> Optional[datetime]:
    """
    Get the most recent sale timestamp to avoid fetching old data.

    Returns the timestamp of the most recent sale, or a default cutoff.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    with conn.cursor() as cur:
        cur.execute("SELECT MAX(sold_at) FROM sales")
        result = cur.fetchone()
        if result and result[0]:
            # If we have recent data, only go back a bit
            most_recent = result[0]
            if most_recent.tzinfo is None:
                most_recent = most_recent.replace(tzinfo=timezone.utc)
            # Go back 2 hours from most recent to catch any stragglers
            return max(cutoff, most_recent - timedelta(hours=2))

    return cutoff


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def handler(event, context):
    """Lambda handler for sales ingestion."""
    timestamp = datetime.now(timezone.utc)
    logger.info(f"Starting sales ingestion at {timestamp}")

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

        total_inserted = 0
        total_fetched = 0
        pages_fetched = 0
        max_pages = 10  # Limit to prevent runaway fetching
        page_size = 100

        try:
            cutoff = get_cutoff_timestamp(conn)
            logger.info(f"Fetching sales since {cutoff}")

            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
                page_from = 0

                while pages_fetched < max_pages:
                    try:
                        result = await fetch_settled_sales(
                            client,
                            page_from=page_from,
                            page_size=page_size,
                            api_key=api_key,
                            internal_secret=internal_secret,
                            rate_limiter=rate_limiter,
                            circuit_breaker=circuit_breaker,
                        )

                        sales = parse_sales_from_response(result)
                        total_fetched += len(sales)

                        if not sales:
                            logger.info(f"No more sales found at page {pages_fetched}")
                            break

                        # Filter to only recent sales
                        recent_sales = [s for s in sales if s["sold_at"] >= cutoff]

                        if not recent_sales:
                            logger.info(f"No sales after cutoff at page {pages_fetched}")
                            break

                        inserted = store_sales(conn, recent_sales)
                        total_inserted += inserted
                        pages_fetched += 1

                        logger.info(
                            f"Page {pages_fetched}: fetched {len(sales)}, "
                            f"recent {len(recent_sales)}, inserted {inserted}"
                        )

                        # If we inserted fewer than expected, we might be hitting duplicates
                        if inserted == 0 and pages_fetched > 1:
                            logger.info("No new sales inserted, stopping pagination")
                            break

                        page_from += page_size

                    except CircuitOpenError as e:
                        logger.warning(f"Circuit open, stopping: {e}")
                        break

                    except httpx.HTTPStatusError as e:
                        logger.error(f"HTTP error fetching page {pages_fetched}: {e}")
                        metrics.add_metric(name="IngestionHTTPErrors", unit=MetricUnit.Count, value=1)
                        break
                    except Exception as e:
                        logger.error(f"Error fetching page {pages_fetched}: {e}")
                        metrics.add_metric(name="IngestionErrors", unit=MetricUnit.Count, value=1)
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

        return {
            "total_fetched": total_fetched,
            "total_inserted": total_inserted,
            "pages_fetched": pages_fetched,
        }

    result = asyncio.run(ingest())

    metrics.add_metric(name="SalesFetched", unit=MetricUnit.Count, value=result["total_fetched"])
    metrics.add_metric(name="SalesInserted", unit=MetricUnit.Count, value=result["total_inserted"])
    metrics.add_metric(name="PagesFetched", unit=MetricUnit.Count, value=result["pages_fetched"])

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

    logger.info(
        f"Sales ingestion complete: fetched {result['total_fetched']}, "
        f"inserted {result['total_inserted']} from {result['pages_fetched']} pages"
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Sales ingestion complete",
            "sales_fetched": result["total_fetched"],
            "sales_inserted": result["total_inserted"],
            "pages_fetched": result["pages_fetched"],
            "timestamp": timestamp.isoformat(),
        }),
    }
