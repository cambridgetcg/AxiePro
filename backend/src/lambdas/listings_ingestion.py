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


# GraphQL fragment for axie listing data (reduces query size)
AXIE_LISTING_FRAGMENT = """
fragment AxieListing on Axie {
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
"""

# GraphQL query for single class (backward compatibility)
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


def build_aliased_listings_query(classes: list, page_from: int, page_size: int, sort: str = "PriceAsc") -> str:
    """
    Build a GraphQL query with aliases to fetch multiple classes in one request.

    This reduces API calls by batching: instead of 3 requests for 3 classes,
    we make 1 request with 3 aliased queries.

    Example output:
    query {
      beast: axies(from: 0, size: 100, auctionType: Sale, criteria: { classes: [Beast] }, sort: PriceAsc) { ... }
      plant: axies(from: 0, size: 100, auctionType: Sale, criteria: { classes: [Plant] }, sort: PriceAsc) { ... }
    }
    """
    alias_queries = []

    for axie_class in classes:
        alias_name = axie_class.lower()
        alias_queries.append(f'''
  {alias_name}: axies(
    from: {page_from}
    size: {page_size}
    auctionType: Sale
    criteria: {{ classes: [{axie_class}] }}
    sort: {sort}
  ) {{
    total
    results {{
      ...AxieListing
    }}
  }}''')

    query = AXIE_LISTING_FRAGMENT + "\nquery GetActiveListingsBatched {" + "".join(alias_queries) + "\n}"
    return query


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
@retry_on_transient_error
async def fetch_listings_batched(
    client: httpx.AsyncClient,
    classes: List[str],
    page_from: int = 0,
    page_size: int = 100,
    sort: str = "PriceAsc",
    api_key: Optional[str] = None,
    internal_secret: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch listings for multiple classes in a single request using GraphQL aliases.

    This is more efficient than separate requests per class:
    - 1 request for 3 classes instead of 3 separate requests
    - Reduces API call count by 66%
    - Sky Mavis recommends this approach for rate limit optimization
    """
    query = build_aliased_listings_query(classes, page_from, page_size, sort)
    headers = get_skymavis_headers(api_key, internal_secret)
    endpoint = get_skymavis_endpoint()

    response = await client.post(
        endpoint,
        json={"query": query},
        headers=headers,
    )
    response.raise_for_status()

    result = response.json()
    check_graphql_errors(result)
    return result


@tracer.capture_method
def parse_listings_from_batched_response(
    response_data: Dict[str, Any],
    classes: List[str]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Parse listings from a batched/aliased GraphQL response.

    Returns a dict mapping class name to list of listings:
    {
        "Beast": [...listings...],
        "Plant": [...listings...],
        "Aquatic": [...listings...]
    }
    """
    results_by_class = {}
    data = response_data.get("data", {})

    for axie_class in classes:
        alias_name = axie_class.lower()
        class_data = data.get(alias_name, {})
        axies_data = class_data.get("results", [])

        listings = []
        for axie in axies_data:
            axie_id = axie.get("id")
            order = axie.get("order")

            if not axie_id or not order:
                continue

            # Validate and convert price
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

            # Parse timestamps
            listed_at, ts_error = safe_validate_timestamp(
                started_at, f"listed_at for axie {axie_id}"
            )
            if ts_error:
                logger.debug(f"Using current time for listing: {ts_error}")
                listed_at = datetime.now(timezone.utc)

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

        results_by_class[axie_class] = listings

    return results_by_class


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
                    INSERT INTO axie.listings (
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
            UPDATE axie.listings
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


def get_class_rotation(timestamp: datetime) -> list:
    """
    Get subset of classes to fetch based on current time.
    Rotates through 3 groups every 5 minutes to reduce API load.

    This reduces requests from 9 classes × 20 pages = 180 requests
    to 3 classes × 10 pages = 30 requests per run.
    """
    class_groups = [
        ["Beast", "Plant", "Aquatic"],
        ["Bird", "Bug", "Reptile"],
        ["Mech", "Dawn", "Dusk"],
    ]
    # Rotate based on 5-minute interval
    interval = timestamp.minute // 5
    group_index = interval % 3
    return class_groups[group_index]


# Rate limiting configuration
RATE_LIMIT_MODE = True  # Set to False to fetch all classes
MAX_PAGES_PER_CLASS = 10  # Reduced from 20 to reduce API calls
REQUEST_DELAY_SECONDS = 0.5  # Increased from 0.1 to be gentler on API


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

        # Determine which classes to fetch
        if RATE_LIMIT_MODE:
            classes_to_fetch = get_class_rotation(timestamp)
            max_pages = MAX_PAGES_PER_CLASS
            request_delay = REQUEST_DELAY_SECONDS
            logger.info(f"Rate limit mode: fetching {classes_to_fetch} with {max_pages} pages, {request_delay}s delay")
        else:
            classes_to_fetch = AXIE_CLASSES
            max_pages = 20
            request_delay = 0.1

        logger.info(
            "API configuration",
            extra={
                "has_api_key": bool(api_key),
                "api_key_prefix": api_key[:8] if api_key else None,
                "endpoint": get_skymavis_endpoint(),
                "rate_limit_mode": RATE_LIMIT_MODE,
                "classes": classes_to_fetch,
            },
        )

        total_inserted = 0
        total_updated = 0
        total_fetched = 0
        all_seen_axie_ids = set()
        rate_limited = False  # Circuit breaker flag

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
                # Use GraphQL aliases to fetch ALL classes in a single request
                # This reduces API calls by 66%: 1 request fetches 3 classes instead of 3 requests
                pages_fetched = 0
                page_size = 100
                page_from = 0
                classes_exhausted = set()  # Track which classes have no more data

                logger.info(
                    f"Using GraphQL aliases to batch {len(classes_to_fetch)} classes per request"
                )

                while pages_fetched < max_pages and not rate_limited:
                    # Skip if all classes are exhausted
                    active_classes = [c for c in classes_to_fetch if c not in classes_exhausted]
                    if not active_classes:
                        logger.info("All classes exhausted, stopping pagination")
                        break

                    try:
                        # Single batched request for all classes using GraphQL aliases
                        result = await fetch_listings_batched(
                            client,
                            classes=active_classes,
                            page_from=page_from,
                            page_size=page_size,
                            sort="PriceAsc",
                            api_key=api_key,
                            internal_secret=internal_secret,
                        )

                        # Parse batched response - returns dict by class
                        listings_by_class = parse_listings_from_batched_response(
                            result, active_classes
                        )

                        page_total_fetched = 0
                        page_total_inserted = 0
                        page_total_updated = 0

                        # Process listings for each class
                        for axie_class, listings in listings_by_class.items():
                            if not listings:
                                if axie_class not in classes_exhausted:
                                    logger.info(f"No more {axie_class} listings at page {pages_fetched}")
                                    classes_exhausted.add(axie_class)
                                continue

                            page_total_fetched += len(listings)

                            # Track seen axie IDs
                            for l in listings:
                                all_seen_axie_ids.add(l["axie_id"])

                            # Store listings
                            inserted, updated = store_listings(conn, listings, timestamp)
                            page_total_inserted += inserted
                            page_total_updated += updated

                            # Publish new listings to Kinesis
                            if inserted > 0:
                                kinesis_result = publish_listings_batch_to_kinesis(listings)
                                logger.debug(
                                    f"Published {axie_class} to Kinesis: {kinesis_result['succeeded']} succeeded"
                                )

                            # Mark class as exhausted if fewer than page_size
                            if len(listings) < page_size:
                                classes_exhausted.add(axie_class)

                        total_fetched += page_total_fetched
                        total_inserted += page_total_inserted
                        total_updated += page_total_updated
                        pages_fetched += 1

                        logger.info(
                            f"Page {pages_fetched} (batched): fetched {page_total_fetched}, "
                            f"inserted {page_total_inserted}, updated {page_total_updated}, "
                            f"classes active: {len(active_classes)}"
                        )

                        page_from += page_size

                        # Delay between pages to respect rate limits
                        await asyncio.sleep(request_delay)

                    except httpx.HTTPStatusError as e:
                        if e.response.status_code == 429:
                            logger.warning("Rate limited (429) - activating circuit breaker")
                            metrics.add_metric(name="RateLimited429", unit=MetricUnit.Count, value=1)
                            rate_limited = True
                        else:
                            logger.error(f"HTTP error on batched fetch page {pages_fetched}: {e}")
                        metrics.add_metric(name="IngestionHTTPErrors", unit=MetricUnit.Count, value=1)
                        break
                    except Exception as e:
                        logger.error(f"Error on batched fetch page {pages_fetched}: {e}")
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
            "rate_limited": rate_limited,
        }

    result = asyncio.run(ingest())

    metrics.add_metric(name="ListingsFetched", unit=MetricUnit.Count, value=result["total_fetched"])
    metrics.add_metric(name="ListingsInserted", unit=MetricUnit.Count, value=result["total_inserted"])
    metrics.add_metric(name="ListingsUpdated", unit=MetricUnit.Count, value=result["total_updated"])
    metrics.add_metric(name="UniqueAxies", unit=MetricUnit.Count, value=result["unique_axies"])

    if result["rate_limited"]:
        logger.warning(
            f"Listings ingestion rate limited: fetched {result['total_fetched']}, "
            f"inserted {result['total_inserted']}, updated {result['total_updated']}"
        )
    else:
        logger.info(
            f"Listings ingestion complete: fetched {result['total_fetched']}, "
            f"inserted {result['total_inserted']}, updated {result['total_updated']}, "
            f"unique axies {result['unique_axies']}"
        )

    return {
        "statusCode": 200 if not result["rate_limited"] else 429,
        "body": json.dumps({
            "message": "Listings ingestion rate limited" if result["rate_limited"] else "Listings ingestion complete",
            "listings_fetched": result["total_fetched"],
            "listings_inserted": result["total_inserted"],
            "listings_updated": result["total_updated"],
            "unique_axies": result["unique_axies"],
            "rate_limited": result["rate_limited"],
            "timestamp": timestamp.isoformat(),
        }),
    }
