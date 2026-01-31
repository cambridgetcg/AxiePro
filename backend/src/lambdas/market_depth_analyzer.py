"""
Market Depth Analyzer Lambda

Tracks order book depth across all axie classes hourly.
Uses 7.2% of daily API capacity (1.4k requests/day).

This Lambda represents CREATIVE path-building - using unused API capacity
to provide liquidity intelligence that enables strategic market positioning.

Purpose Prompter alignment:
- CREATIVITY: Pioneering market depth tracking in uncharted territory
- JUSTICE: Right place for market analysis (dedicated Lambda)
- BEAUTY: Elegant order book construction from search queries
- UNDERSTANDING: Deep comprehension of market liquidity dynamics
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from decimal import Decimal

import httpx
from aws_lambda_powertools.metrics import MetricUnit

from src.lambdas.common import (
    logger,
    tracer,
    metrics,
    get_secrets,
    get_db_connection,
    HTTP_TIMEOUT_SECONDS,
)
from src.services.skymavis_client import SkyMavisClient


# Configuration
CLASSES_TO_ANALYZE = ["beast", "plant", "aquatic", "bird", "bug", "reptile"]

# Price buckets in ETH (10 buckets per class)
PRICE_BUCKETS = [
    (0, 0.001),      # Free/extremely cheap
    (0.001, 0.005),  # < $5 (assuming 1 ETH = $1000)
    (0.005, 0.01),   # $5-10
    (0.01, 0.02),    # $10-20
    (0.02, 0.05),    # $20-50
    (0.05, 0.1),     # $50-100
    (0.1, 0.2),      # $100-200
    (0.2, 0.5),      # $200-500
    (0.5, 1.0),      # $500-1000
    (1.0, 999),      # $1000+
]


def store_market_depth(
    conn,
    axie_class: str,
    price_min_eth: Decimal,
    price_max_eth: Decimal,
    listing_count: int,
) -> bool:
    """Store market depth snapshot in database."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO market_depth (
                    class,
                    price_min_eth,
                    price_max_eth,
                    listing_count,
                    snapshot_time
                )
                VALUES (%s, %s, %s, %s, NOW())
                """,
                (axie_class, price_min_eth, price_max_eth, listing_count),
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error storing market depth: {e}")
        conn.rollback()
        return False


@tracer.capture_method
async def analyze_price_bucket(
    client: SkyMavisClient,
    conn,
    axie_class: str,
    price_min: float,
    price_max: float,
) -> int:
    """
    Analyze market depth for a specific price bucket.

    Returns number of listings in this bucket.
    """
    try:
        # Convert ETH to wei for API
        price_min_wei = int(price_min * 10**18)
        price_max_wei = int(price_max * 10**18)

        # Search for listings in this price range
        axies, total = await client.search_axies(
            classes=[axie_class],
            price_min=price_min_wei,
            price_max=price_max_wei,
            auction_type="Sale",
            sort_by="PriceAsc",
            size=1,  # We only need the count, not the actual data
        )

        logger.debug(
            f"{axie_class} ${price_min:.3f}-${price_max:.3f}: {total} listings"
        )

        # Store snapshot
        store_market_depth(
            conn,
            axie_class,
            Decimal(str(price_min)),
            Decimal(str(price_max)),
            total,
        )

        return total

    except Exception as e:
        logger.error(
            f"Error analyzing {axie_class} bucket ${price_min}-${price_max}: {e}"
        )
        return 0


@tracer.capture_method
async def analyze_class_depth(
    client: SkyMavisClient,
    conn,
    axie_class: str,
) -> Dict[str, int]:
    """
    Analyze market depth for one class across all price buckets.

    Returns summary statistics.
    """
    total_listings = 0
    buckets_analyzed = 0

    logger.info(f"Analyzing market depth for {axie_class}...")

    for price_min, price_max in PRICE_BUCKETS:
        count = await analyze_price_bucket(
            client,
            conn,
            axie_class,
            price_min,
            price_max,
        )
        total_listings += count
        buckets_analyzed += 1

        # Small delay to avoid rate limiting
        await asyncio.sleep(0.1)

    # Calculate market health metrics
    # Thin market: <50 total listings
    # Deep market: >200 total listings
    market_health = "deep" if total_listings > 200 else "thin" if total_listings < 50 else "medium"

    logger.info(
        f"{axie_class}: {total_listings} total listings, "
        f"market health: {market_health}"
    )

    return {
        "class": axie_class,
        "total_listings": total_listings,
        "buckets_analyzed": buckets_analyzed,
        "market_health": market_health,
    }


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def handler(event, context):
    """
    Lambda handler for market depth analysis.

    Runs hourly, analyzes 6 classes × 10 price buckets = 60 requests per run.
    API usage: 60 requests × 24 runs/day = 1,440 requests/day (7.2%).
    """
    timestamp = datetime.now(timezone.utc)
    logger.info(f"Starting market depth analysis at {timestamp}")

    async def analyze():
        conn = get_db_connection()
        secrets = get_secrets()

        total_buckets = 0
        total_listings = 0
        class_summaries = []

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as http_client:
                client = SkyMavisClient(
                    http_client=http_client,
                    api_key=secrets.get("SKYMAVIS_API_KEY"),
                )

                # Analyze each class
                for axie_class in CLASSES_TO_ANALYZE:
                    summary = await analyze_class_depth(client, conn, axie_class)
                    class_summaries.append(summary)
                    total_buckets += summary["buckets_analyzed"]
                    total_listings += summary["total_listings"]

                logger.info(
                    f"Market depth analysis complete: "
                    f"{total_buckets} buckets analyzed, "
                    f"{total_listings} total listings tracked"
                )

                # Metrics
                metrics.add_metric(name="BucketsAnalyzed", unit=MetricUnit.Count, value=total_buckets)
                metrics.add_metric(name="TotalListings", unit=MetricUnit.Count, value=total_listings)

                # Market health metrics
                deep_markets = sum(1 for s in class_summaries if s["market_health"] == "deep")
                thin_markets = sum(1 for s in class_summaries if s["market_health"] == "thin")

                metrics.add_metric(name="DeepMarkets", unit=MetricUnit.Count, value=deep_markets)
                metrics.add_metric(name="ThinMarkets", unit=MetricUnit.Count, value=thin_markets)

                return {
                    "total_buckets": total_buckets,
                    "total_listings": total_listings,
                    "class_summaries": class_summaries,
                    "timestamp": timestamp.isoformat(),
                }

        except Exception as e:
            logger.error(f"Fatal error in market depth analysis: {e}", exc_info=True)
            raise
        finally:
            if conn:
                conn.close()

    # Run async function
    result = asyncio.run(analyze())

    logger.info(
        f"Market depth analysis complete: {result['total_listings']} listings tracked"
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Market depth analysis complete",
            "buckets_analyzed": result["total_buckets"],
            "total_listings": result["total_listings"],
            "class_summaries": result["class_summaries"],
            "timestamp": result["timestamp"],
        }),
    }
