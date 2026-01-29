"""
Listings Ingestion Lambda

Runs every 5 minutes to capture active marketplace listings.
Fetches from Sky Mavis GraphQL API and stores in Aurora PostgreSQL.

This populates the `listings` table which enables:
- Floor price calculations per class/trait
- Deal detection (comparing current listings to historical prices)
- Market depth analysis
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
    validate_address,
    validate_axie_id,
    ValidationError,
    retry_on_transient_error,
    publish_listings_batch_to_kinesis,
    AXIE_CLASSES,
    HTTP_TIMEOUT_SECONDS,
)


# GraphQL query for active marketplace listings
ACTIVE_LISTINGS_QUERY = """
query GetActiveListings($from: Int!, $size: Int!, $classes: [AxieClass!], $sort: SortBy) {
  axies(
    from: $from
    size: $size
    auctionType: Sale
    criteria: { classes: $classes }
    sort: $sort
  ) {
    total
    results {
      id
      name
      class
      breedCount
      owner
      image
      order {
        id
        maker
        currentPrice
        currentPriceUsd
        startedAt
        expiredAt
        basePrice
        endedPrice
      }
      parts {
        id
        name
        type
        class
      }
    }
  }
}
"""


@tracer.capture_method
@retry_on_transient_error
async def fetch_listings_page(
    client: httpx.AsyncClient,
    page_from: int = 0,
    page_size: int = 100,
    axie_class: Optional[str] = None,
    sort: str = "PriceAsc",
    api_key: Optional[str] = None,
    internal_secret: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch a page of active listings from Sky Mavis API with automatic retry."""
    variables = {
        "from": page_from,
        "size": page_size,
        "sort": sort,
    }

    if axie_class:
        variables["classes"] = [axie_class.capitalize()]

    headers = get_skymavis_headers(api_key, internal_secret)
    endpoint = get_skymavis_endpoint()

    response = await client.post(
        endpoint,
        json={"query": ACTIVE_LISTINGS_QUERY, "variables": variables},
        headers=headers,
    )
    response.raise_for_status()

    result = response.json()
    check_graphql_errors(result)  # Raise if GraphQL errors present
    return result


@tracer.capture_method
def parse_listings_from_response(response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse listings data from GraphQL response.

    Extracts active listings with price and seller information.
    """
    listings = []

    axies_data = (
        response_data.get("data", {})
        .get("axies", {})
        .get("results", [])
    )

    for axie in axies_data:
        axie_id = axie.get("id")
        order = axie.get("order")

        if not axie_id or not order:
            continue

        # Validate and convert price using validation utility
        price_wei = order.get("currentPrice")
        if not price_wei:
            continue

        price_eth, price_error = safe_validate_price_wei(
            price_wei, f"price for axie {axie_id}"
        )
        if price_error:
            logger.warning(price_error)
            continue

        price_usd = order.get("currentPriceUsd")
        seller = order.get("maker")
        started_at = order.get("startedAt")
        expired_at = order.get("expiredAt")

        if not seller:
            continue

        # Parse timestamps with validation
        # For listings, use current time as fallback if started_at is invalid
        listed_at, ts_error = safe_validate_timestamp(
            started_at, f"listed_at for axie {axie_id}"
        )
        if ts_error:
            logger.debug(f"Using current time for listing: {ts_error}")
            listed_at = datetime.now(timezone.utc)

        # expires_at is optional, just skip if invalid
        expires_at = None
        if expired_at:
            expires_at, exp_error = safe_validate_timestamp(
                expired_at, f"expires_at for axie {axie_id}", default=None
            )
            if exp_error:
                logger.debug(f"Skipping expires_at: {exp_error}")

        listings.append({
            "axie_id": int(axie_id),
            "class_": axie.get("class", "Unknown"),
            "breed_count": axie.get("breedCount", 0),
            "seller_address": seller.lower() if seller else None,
            "price_eth": price_eth,
            "price_usd": Decimal(str(price_usd)) if price_usd else None,
            "listed_at": listed_at or datetime.now(timezone.utc),
            "expires_at": expires_at,
            "order_id": order.get("id"),
        })

    return listings


@tracer.capture_method
def store_listings(conn, listings: List[Dict[str, Any]], timestamp: datetime) -> tuple:
    """
    Store listings in database with upsert logic.

    - Inserts new listings
    - Updates existing listings if price changed
    - Returns (inserted, updated) counts
    """
    if not listings:
        return 0, 0

    inserted = 0
    updated = 0
    seen_axie_ids = set()

    with conn.cursor() as cur:
        for listing in listings:
            seen_axie_ids.add(listing["axie_id"])

            try:
                # Use upsert with partial unique index on active listings
                # The index is: CREATE UNIQUE INDEX idx_listings_active_axie ON listings (axie_id) WHERE status = 'active'
                cur.execute(
                    """
                    INSERT INTO listings (
                        axie_id, seller_address, price_eth, price_usd,
                        listed_at, expires_at, status, class_, breed_count,
                        created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, 'active', %s, %s, %s, %s)
                    ON CONFLICT (axie_id) WHERE status = 'active'
                    DO UPDATE SET
                        price_eth = EXCLUDED.price_eth,
                        price_usd = EXCLUDED.price_usd,
                        seller_address = EXCLUDED.seller_address,
                        expires_at = EXCLUDED.expires_at,
                        class_ = EXCLUDED.class_,
                        breed_count = EXCLUDED.breed_count,
                        updated_at = EXCLUDED.updated_at
                    RETURNING (xmax = 0) AS inserted
                    """,
                    (
                        listing["axie_id"],
                        listing["seller_address"],
                        listing["price_eth"],
                        listing["price_usd"],
                        listing["listed_at"],
                        listing["expires_at"],
                        listing["class_"],
                        listing["breed_count"],
                        timestamp,
                        timestamp,
                    ),
                )

                result = cur.fetchone()
                if result and result[0]:
                    inserted += 1
                else:
                    updated += 1

            except Exception as e:
                logger.error(f"Error storing listing for axie {listing['axie_id']}: {e}")
                continue

        conn.commit()

    return inserted, updated


@tracer.capture_method
def mark_stale_listings(conn, seen_axie_ids: set, max_age_hours: int = 1) -> int:
    """
    Mark listings as cancelled if not seen in recent fetch.

    Only marks listings that are older than max_age_hours to avoid
    race conditions with pagination.
    """
    if not seen_axie_ids:
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

    with conn.cursor() as cur:
        # Mark old listings not seen as sold/cancelled
        cur.execute(
            """
            UPDATE listings
            SET status = 'sold', updated_at = NOW()
            WHERE status = 'active'
            AND updated_at < %s
            AND axie_id NOT IN %s
            """,
            (cutoff, tuple(seen_axie_ids) if seen_axie_ids else (0,)),
        )

        marked = cur.rowcount
        conn.commit()

    return marked


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def handler(event, context):
    """Lambda handler for listings ingestion."""
    timestamp = datetime.now(timezone.utc)
    logger.info(f"Starting listings ingestion at {timestamp}")

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
        total_updated = 0
        total_fetched = 0
        all_seen_axie_ids = set()

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
                # Fetch listings for each class to ensure coverage
                for axie_class in AXIE_CLASSES:
                    pages_fetched = 0
                    max_pages = 20  # Limit per class
                    page_size = 100
                    page_from = 0

                    while pages_fetched < max_pages:
                        try:
                            result = await fetch_listings_page(
                                client,
                                page_from=page_from,
                                page_size=page_size,
                                axie_class=axie_class,
                                sort="PriceAsc",  # Get cheapest first
                                api_key=api_key,
                                internal_secret=internal_secret,
                            )

                            listings = parse_listings_from_response(result)
                            total_fetched += len(listings)

                            if not listings:
                                logger.info(f"No more {axie_class} listings at page {pages_fetched}")
                                break

                            # Track seen axie IDs
                            for l in listings:
                                all_seen_axie_ids.add(l["axie_id"])

                            # Store listings
                            inserted, updated = store_listings(conn, listings, timestamp)
                            total_inserted += inserted
                            total_updated += updated
                            pages_fetched += 1

                            # Publish new listings to Kinesis for deal detection
                            # Only publish if we have new listings to avoid noise
                            if inserted > 0:
                                kinesis_result = publish_listings_batch_to_kinesis(listings)
                                logger.debug(
                                    f"Published to Kinesis: {kinesis_result['succeeded']} succeeded, "
                                    f"{kinesis_result['failed']} failed"
                                )

                            logger.info(
                                f"{axie_class} page {pages_fetched}: fetched {len(listings)}, "
                                f"inserted {inserted}, updated {updated}"
                            )

                            # If we got fewer than page_size, we've reached the end
                            if len(listings) < page_size:
                                break

                            page_from += page_size

                            # Small delay to be nice to the API
                            await asyncio.sleep(0.1)

                        except httpx.HTTPStatusError as e:
                            logger.error(f"HTTP error fetching {axie_class} page {pages_fetched}: {e}")
                            metrics.add_metric(name="IngestionHTTPErrors", unit=MetricUnit.Count, value=1)
                            break
                        except Exception as e:
                            logger.error(f"Error fetching {axie_class} page {pages_fetched}: {e}")
                            metrics.add_metric(name="IngestionErrors", unit=MetricUnit.Count, value=1)
                            break

                # Mark stale listings as sold
                marked_sold = mark_stale_listings(conn, all_seen_axie_ids)
                logger.info(f"Marked {marked_sold} listings as sold")

        finally:
            conn.close()

        return {
            "total_fetched": total_fetched,
            "total_inserted": total_inserted,
            "total_updated": total_updated,
            "unique_axies": len(all_seen_axie_ids),
        }

    result = asyncio.run(ingest())

    metrics.add_metric(name="ListingsFetched", unit=MetricUnit.Count, value=result["total_fetched"])
    metrics.add_metric(name="ListingsInserted", unit=MetricUnit.Count, value=result["total_inserted"])
    metrics.add_metric(name="ListingsUpdated", unit=MetricUnit.Count, value=result["total_updated"])
    metrics.add_metric(name="UniqueAxies", unit=MetricUnit.Count, value=result["unique_axies"])

    logger.info(
        f"Listings ingestion complete: fetched {result['total_fetched']}, "
        f"inserted {result['total_inserted']}, updated {result['total_updated']}, "
        f"unique axies {result['unique_axies']}"
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Listings ingestion complete",
            "listings_fetched": result["total_fetched"],
            "listings_inserted": result["total_inserted"],
            "listings_updated": result["total_updated"],
            "unique_axies": result["unique_axies"],
            "timestamp": timestamp.isoformat(),
        }),
    }
