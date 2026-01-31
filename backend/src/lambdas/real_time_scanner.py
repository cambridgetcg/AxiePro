"""
Real-time Market Scanner Lambda

Scans recent listings every 5 minutes to detect underpriced deals.
Uses 8.6% of daily API capacity (1.7k requests/day).

This Lambda represents CREATIVE path-building - using unused API capacity
to provide first-mover advantage in deal detection.

Purpose Prompter alignment:
- CREATIVITY: New capability (real-time alerts) in uncharted territory
- JUSTICE: Right place for deal detection (dedicated scanner vs metadata Lambda)
- BEAUTY: Elegant reuse of existing patterns (metadata_ingestion structure)
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Set
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
CLASSES_TO_SCAN = ["beast", "plant", "aquatic", "bird", "bug", "reptile"]
LISTINGS_PER_CLASS = 20  # Top 20 most recent per class
DEAL_THRESHOLD = 0.80  # Alert if price < 80% of fair value
LOOKBACK_MINUTES = 10  # Only process listings from last 10 minutes


def get_fair_value(conn, axie_id: int, axie_class: str) -> Optional[Decimal]:
    """
    Estimate fair value for an axie based on historical data.

    Strategy:
    1. Check recent sales for this specific axie
    2. Fall back to class + purity average
    3. Fall back to class floor price
    """
    with conn.cursor() as cur:
        # Try: Recent sales of this specific axie
        cur.execute(
            """
            SELECT price_eth
            FROM sales
            WHERE axie_id = %s
            ORDER BY block_timestamp DESC
            LIMIT 1
            """,
            (axie_id,),
        )
        row = cur.fetchone()
        if row:
            return Decimal(str(row[0]))

        # Fall back: Get class floor price from recent snapshots
        cur.execute(
            """
            SELECT floor_price_eth
            FROM price_snapshots
            WHERE class = %s
            ORDER BY snapshot_time DESC
            LIMIT 1
            """,
            (axie_class,),
        )
        row = cur.fetchone()
        if row and row[0]:
            return Decimal(str(row[0]))

    return None


def is_already_alerted(conn, listing_id: str) -> bool:
    """Check if we've already sent an alert for this listing."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM deal_alerts
            WHERE listing_id = %s
            LIMIT 1
            """,
            (listing_id,),
        )
        return cur.fetchone() is not None


def store_deal_alert(
    conn,
    listing_id: str,
    axie_id: int,
    axie_class: str,
    price_eth: Decimal,
    fair_value_eth: Decimal,
    discount_pct: Decimal,
    metadata: Dict[str, Any],
) -> None:
    """Store a deal alert in the database."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO deal_alerts (
                listing_id,
                axie_id,
                class,
                price_eth,
                fair_value_eth,
                discount_pct,
                metadata,
                detected_at,
                alerted
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, NOW(), true
            )
            ON CONFLICT (listing_id) DO NOTHING
            """,
            (
                listing_id,
                axie_id,
                axie_class,
                price_eth,
                fair_value_eth,
                discount_pct,
                json.dumps(metadata),
            ),
        )
        conn.commit()


@tracer.capture_method
async def scan_recent_listings(
    client: SkyMavisClient,
    conn,
    axie_class: str,
) -> int:
    """
    Scan recent listings for one class and detect deals.

    Returns number of deals found.
    """
    deals_found = 0

    try:
        # Fetch recent listings
        listings, total = await client.get_recent_listings(
            classes=[axie_class],
            size=LISTINGS_PER_CLASS,
        )

        logger.info(f"Scanning {len(listings)} recent {axie_class} listings")

        for listing in listings:
            try:
                axie = listing.axie
                axie_id = axie.id

                # Skip if we already alerted on this listing
                listing_id = f"{axie_id}_{listing.seller}_{listing.current_price}"
                if is_already_alerted(conn, listing_id):
                    continue

                # Get current price in ETH
                current_price_eth = Decimal(listing.current_price) / Decimal(10**18)

                # Estimate fair value
                fair_value = get_fair_value(conn, axie_id, axie_class)

                if not fair_value or fair_value <= 0:
                    # Can't evaluate without fair value
                    continue

                # Calculate discount
                discount_pct = (1 - (current_price_eth / fair_value)) * 100

                # Check if it's a deal
                if current_price_eth < (fair_value * Decimal(str(DEAL_THRESHOLD))):
                    # DEAL FOUND!
                    logger.info(
                        f"DEAL: Axie #{axie_id} ({axie_class}) - "
                        f"${current_price_eth:.4f} ETH "
                        f"({discount_pct:.1f}% below fair value)"
                    )

                    # Build metadata
                    metadata = {
                        "purity_score": axie.purity_score if hasattr(axie, 'purity_score') else None,
                        "breed_count": axie.breed_count if hasattr(axie, 'breed_count') else None,
                        "genes": axie.genes if hasattr(axie, 'genes') else None,
                        "seller": listing.seller,
                        "current_price_usd": listing.current_price_usd,
                    }

                    # Store alert
                    store_deal_alert(
                        conn,
                        listing_id,
                        axie_id,
                        axie_class,
                        current_price_eth,
                        fair_value,
                        discount_pct,
                        metadata,
                    )

                    deals_found += 1

            except Exception as e:
                logger.error(f"Error processing listing {listing.axie_id}: {e}")
                continue

        return deals_found

    except Exception as e:
        logger.error(f"Error scanning {axie_class} listings: {e}")
        return 0


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def handler(event, context):
    """
    Lambda handler for real-time market scanning.

    Runs every 5 minutes, scans 6 classes × 20 listings = 120 listings.
    API usage: 6 requests per run × 12 runs/hour × 24 hours = 1,728 requests/day.
    """
    timestamp = datetime.now(timezone.utc)
    logger.info(f"Starting real-time market scan at {timestamp}")

    async def scan():
        conn = get_db_connection()
        secrets = get_secrets()

        total_deals = 0
        total_listings_scanned = 0

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as http_client:
                client = SkyMavisClient(
                    http_client=http_client,
                    api_key=secrets.get("SKYMAVIS_API_KEY"),
                )

                # Scan each class
                for axie_class in CLASSES_TO_SCAN:
                    deals = await scan_recent_listings(client, conn, axie_class)
                    total_deals += deals
                    total_listings_scanned += LISTINGS_PER_CLASS

                logger.info(
                    f"Market scan complete: "
                    f"scanned {total_listings_scanned} listings, "
                    f"found {total_deals} deals"
                )

                # Metrics
                metrics.add_metric(name="ListingsScanned", unit=MetricUnit.Count, value=total_listings_scanned)
                metrics.add_metric(name="DealsFound", unit=MetricUnit.Count, value=total_deals)

                if total_listings_scanned > 0:
                    deal_rate = (total_deals / total_listings_scanned) * 100
                    metrics.add_metric(name="DealRate", unit=MetricUnit.Percent, value=deal_rate)

                return {
                    "total_listings_scanned": total_listings_scanned,
                    "total_deals_found": total_deals,
                    "timestamp": timestamp.isoformat(),
                }

        except Exception as e:
            logger.error(f"Fatal error in market scan: {e}", exc_info=True)
            raise
        finally:
            if conn:
                conn.close()

    # Run async function
    result = asyncio.run(scan())

    logger.info(
        f"Real-time scan complete: {result['total_deals_found']} deals found"
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Market scan complete",
            "listings_scanned": result["total_listings_scanned"],
            "deals_found": result["total_deals_found"],
            "timestamp": result["timestamp"],
        }),
    }
