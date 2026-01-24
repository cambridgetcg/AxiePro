"""
Price Ingestion Lambda

Runs every 5 minutes to capture price snapshots from the marketplace.
Stores data in Aurora PostgreSQL for trend analysis.
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
    TRACKED_PARTS_BY_CLASS,
    PARTS_SAMPLE_SIZE,
    HTTP_TIMEOUT_SECONDS,
)


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
) -> dict:
    """Fetch floor prices for a specific class and optional part."""
    variables = {
        "classes": [axie_class.capitalize()],
        "sort": "PriceAsc",
        "size": 10,
    }
    if part_id:
        variables["parts"] = [part_id]

    headers = get_skymavis_headers(api_key, internal_secret)
    endpoint = get_skymavis_endpoint()

    response = await client.post(
        endpoint,
        json={"query": FLOOR_PRICE_QUERY, "variables": variables},
        headers=headers,
    )
    response.raise_for_status()
    return response.json()


@tracer.capture_method
def calculate_statistics(axies: list) -> dict:
    """Calculate floor, average, and volume from axie list."""
    if not axies:
        return {"floor_eth": None, "avg_eth": None, "count": 0}

    prices = []
    for axie in axies:
        if axie.get("order") and axie["order"].get("currentPrice"):
            price_wei = int(axie["order"]["currentPrice"])
            price_eth = Decimal(price_wei) / Decimal(10**18)
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

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
                # Fetch class-level floor prices
                for axie_class in TRACKED_PARTS_BY_CLASS.keys():
                    try:
                        result = await fetch_floor_prices(
                            client, axie_class, api_key=api_key, internal_secret=internal_secret
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

                    except Exception as e:
                        logger.error(f"Error fetching {axie_class}: {e}")
                        metrics.add_metric(name="IngestionErrors", unit=MetricUnit.Count, value=1)

                # Fetch part-level floor prices (sample parts)
                for axie_class, parts in TRACKED_PARTS_BY_CLASS.items():
                    for part_id in parts[:PARTS_SAMPLE_SIZE]:
                        try:
                            result = await fetch_floor_prices(
                                client, axie_class, part_id, api_key=api_key, internal_secret=internal_secret
                            )
                            axies = result.get("data", {}).get("axies", {}).get("results", [])
                            stats = calculate_statistics(axies)

                            store_snapshot(conn, timestamp, f"part:{part_id}", axie_class, stats)
                            snapshots_stored += 1

                        except Exception as e:
                            logger.error(f"Error fetching {axie_class}/{part_id}: {e}")

        finally:
            conn.close()

        return snapshots_stored

    snapshots = asyncio.run(ingest())

    metrics.add_metric(name="SnapshotsStored", unit=MetricUnit.Count, value=snapshots)
    logger.info(f"Stored {snapshots} price snapshots")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Price ingestion complete",
            "snapshots_stored": snapshots,
            "timestamp": timestamp.isoformat(),
        }),
    }
