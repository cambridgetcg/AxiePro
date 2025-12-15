"""
Price Ingestion Lambda

Runs every 5 minutes to capture price snapshots from the marketplace.
Stores data in Aurora PostgreSQL for trend analysis.
"""
import json
import os
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import boto3
import httpx
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit

logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Sky Mavis GraphQL endpoint
SKYMAVIS_API = "https://graphql-gateway.axieinfinity.com/graphql"


def get_secrets() -> dict:
    """Retrieve API keys from AWS Secrets Manager."""
    client = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    response = client.get_secret_value(SecretId=os.environ["SECRET_NAME"])
    return json.loads(response["SecretString"])


def get_db_connection():
    """Get database connection from secrets."""
    secrets = get_secrets()
    import psycopg2
    return psycopg2.connect(secrets["DATABASE_URL"])


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
      auction {
        currentPrice
        currentPriceUSD
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

PART_IDS_BY_CLASS = {
    "beast": ["eyes-chubby", "ears-zen", "horn-imp", "mouth-nut-cracker", "back-ronin", "tail-cottontail"],
    "aquatic": ["eyes-clear", "ears-nimo", "horn-anemone", "mouth-lam", "back-goldfish", "tail-nimo"],
    "plant": ["eyes-papi", "ears-leafy", "horn-cactus", "mouth-zigzag", "back-pumpkin", "tail-carrot"],
    "bird": ["eyes-mavis", "ears-pink-cheek", "horn-eggshell", "mouth-peace-maker", "back-pigeon-post", "tail-post-fight"],
    "bug": ["eyes-bookworm", "ears-ear-breathing", "horn-antenna", "mouth-pincer", "back-snail-shell", "tail-fish-snack"],
    "reptile": ["eyes-topaz", "ears-small-frill", "horn-scaly-spear", "mouth-razor-bite", "back-green-thorns", "tail-iguana"],
}


@tracer.capture_method
async def fetch_floor_prices(client: httpx.AsyncClient, axie_class: str, part_id: Optional[str] = None) -> dict:
    """Fetch floor prices for a specific class and optional part."""
    variables = {
        "classes": [axie_class.upper()],
        "sort": "PriceAsc",
        "size": 10,
    }
    if part_id:
        variables["parts"] = [part_id]

    response = await client.post(
        SKYMAVIS_API,
        json={"query": FLOOR_PRICE_QUERY, "variables": variables},
        headers={"Content-Type": "application/json"},
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
        if axie.get("auction") and axie["auction"].get("currentPrice"):
            price_wei = int(axie["auction"]["currentPrice"])
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
        snapshots_stored = 0

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Fetch class-level floor prices
                for axie_class in PART_IDS_BY_CLASS.keys():
                    try:
                        result = await fetch_floor_prices(client, axie_class)
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
                for axie_class, parts in PART_IDS_BY_CLASS.items():
                    for part_id in parts[:2]:  # Sample 2 parts per class
                        try:
                            result = await fetch_floor_prices(client, axie_class, part_id)
                            axies = result.get("data", {}).get("axies", {}).get("results", [])
                            stats = calculate_statistics(axies)

                            store_snapshot(conn, timestamp, f"part:{part_id}", axie_class, stats)
                            snapshots_stored += 1

                        except Exception as e:
                            logger.error(f"Error fetching {axie_class}/{part_id}: {e}")

        finally:
            conn.close()

        return snapshots_stored

    snapshots = asyncio.get_event_loop().run_until_complete(ingest())

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
