"""
Metadata Ingestion Lambda - SkyMavis GraphQL

Uses new SkyMavis API key with sufficient rate limits (20k requests/day).
Fetches complete axie metadata from SkyMavis GraphQL API.

Optimized configuration:
- 25 axies per batch (concurrent requests)
- 500 axies per run
- 0.5s delay between batches (respects 50 req/sec limit)
"""

import asyncio
import json
import random
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Set

import httpx
from aws_lambda_powertools.metrics import MetricUnit

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
    retry_on_transient_error,
    HTTP_TIMEOUT_SECONDS,
)


# Configuration - Optimized for new API key rate limits
AXIES_PER_BATCH = 25  # Concurrent requests per batch
MAX_AXIES_PER_RUN = 500  # 500 axies per run
BATCH_DELAY_SECONDS = 0.5  # 50 req/sec = 25 per 0.5s
INITIAL_JITTER_MAX_SECONDS = 5  # Minimal jitter needed


# GraphQL query for complete axie metadata
AXIE_METADATA_QUERY = """
query GetAxieMetadata($axieId: ID!) {
  axie(axieId: $axieId) {
    id
    name
    class
    breedCount
    genes
    image
    owner
    birthDate
    matronId
    sireId
    stats {
      hp
      speed
      skill
      morale
    }
    parts {
      id
      name
      type
      class
    }
  }
}
"""


@tracer.capture_method
@retry_on_transient_error
async def fetch_axie_from_skymavis(
    client: httpx.AsyncClient,
    axie_id: int,
    api_key: Optional[str] = None,
    internal_secret: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Fetch complete axie metadata from SkyMavis GraphQL.

    Returns all fields needed for database storage:
    - Basic info: id, name, class, breedCount
    - Genetics: genes, parts
    - Stats: hp, speed, skill, morale
    - Lineage: matronId, sireId, birthDate
    - Ownership: owner
    """
    headers = get_skymavis_headers(api_key, internal_secret)
    endpoint = get_skymavis_endpoint()

    try:
        response = await client.post(
            endpoint,
            json={
                "query": AXIE_METADATA_QUERY,
                "variables": {"axieId": str(axie_id)},
            },
            headers=headers,
            timeout=30.0,
        )

        # Handle rate limiting with exponential backoff
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 5))
            logger.warning(f"SkyMavis rate limited, waiting {retry_after}s")
            metrics.add_metric(name="APIErrors429", unit=MetricUnit.Count, value=1)
            await asyncio.sleep(retry_after)
            # Retry once
            response = await client.post(
                endpoint,
                json={
                    "query": AXIE_METADATA_QUERY,
                    "variables": {"axieId": str(axie_id)},
                },
                headers=headers,
                timeout=30.0,
            )

        response.raise_for_status()
        result = response.json()

        try:
            check_graphql_errors(result)
        except GraphQLError as e:
            logger.warning(f"GraphQL error for axie {axie_id}: {e}")
            return None

        return result.get("data", {}).get("axie")

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(f"Axie {axie_id} not found")
            return None
        logger.error(f"HTTP error for axie {axie_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching axie {axie_id}: {e}")
        return None


def calculate_purity_score(axie_data: Dict[str, Any]) -> int:
    """
    Calculate purity score based on matching part classes.

    A 6-part pure axie (all parts match class) = 6.
    """
    axie_class = axie_data.get("class", "").lower()
    parts = axie_data.get("parts", [])

    if not axie_class or not parts:
        return 0

    matching = sum(
        1 for part in parts
        if part.get("class", "").lower() == axie_class
    )
    return matching


def parse_axie_for_db(axie_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Convert SkyMavis axie data to database record format.

    Returns None if axie data is invalid or missing required fields.
    """
    if not axie_data:
        return None

    axie_id = axie_data.get("id")
    if not axie_id:
        return None

    # Parse stats
    stats = axie_data.get("stats", {}) or {}

    # Parse birth date
    birth_date = None
    bd = axie_data.get("birthDate")
    if bd:
        try:
            birth_date = datetime.fromtimestamp(bd, tz=timezone.utc)
        except (ValueError, TypeError, OSError):
            pass

    # Parse parent IDs
    matron_id = axie_data.get("matronId")
    sire_id = axie_data.get("sireId")
    if matron_id == 0:
        matron_id = None
    if sire_id == 0:
        sire_id = None

    # Calculate purity
    purity_score = calculate_purity_score(axie_data)

    # Owner address (normalize to lowercase)
    owner = axie_data.get("owner")
    if owner:
        owner = owner.lower()

    # Normalize class to lowercase to match database enum
    axie_class = axie_data.get("class", "unknown")
    if axie_class:
        axie_class = axie_class.lower()

    return {
        "id": int(axie_id),
        "name": axie_data.get("name"),
        "class_": axie_class,
        "breed_count": axie_data.get("breedCount", 0),
        "genes": axie_data.get("genes", ""),
        "image_url": axie_data.get("image"),
        "owner_address": owner,
        "birth_date": birth_date,
        "matron_id": matron_id,
        "sire_id": sire_id,
        "purity_score": purity_score,
        "hp": stats.get("hp"),
        "speed": stats.get("speed"),
        "skill": stats.get("skill"),
        "morale": stats.get("morale"),
    }


# Helper functions (from original metadata_ingestion.py)
def get_missing_axie_ids(conn, axie_ids: Set[int]) -> Set[int]:
    """Find which axie_ids don't exist in the axies table."""
    if not axie_ids:
        return set()

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id FROM axies WHERE id = ANY(%s)
            """,
            (list(axie_ids),),
        )
        existing = {row[0] for row in cur.fetchall()}

    return axie_ids - existing


@tracer.capture_method
def get_axie_ids_from_sales(conn, limit: int = 500) -> Set[int]:
    """Get axie_ids from sales that don't have metadata."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT s.axie_id
            FROM sales s
            LEFT JOIN axies a ON s.axie_id = a.id
            WHERE a.id IS NULL
            LIMIT %s
            """,
            (limit,),
        )
        return {row[0] for row in cur.fetchall()}


@tracer.capture_method
def get_axie_ids_from_listings(conn, limit: int = 500) -> Set[int]:
    """
    Get axie_ids from active listings that don't have metadata.

    PRIORITY: These axies are currently for sale, so their metadata
    is most valuable for deal detection and valuation.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT l.axie_id
            FROM listings l
            LEFT JOIN axies a ON l.axie_id = a.id
            WHERE a.id IS NULL
              AND l.status = 'active'
            LIMIT %s
            """,
            (limit,),
        )
        return {row[0] for row in cur.fetchall()}


@tracer.capture_method
def store_axies(conn, axies: List[Dict[str, Any]]) -> int:
    """
    Store axie metadata in database with upsert.

    Returns number of records inserted/updated.
    """
    if not axies:
        return 0

    stored = 0

    with conn.cursor() as cur:
        for axie in axies:
            if not axie:
                continue

            try:
                # Skip parent IDs (matron/sire) to avoid foreign key violations
                # Parent axies may not exist yet in the database
                cur.execute(
                    """
                    INSERT INTO axies (
                        id, name, class, breed_count, genes, image_url,
                        owner_address, birth_date,
                        purity_score, hp, speed, skill, morale,
                        created_at, updated_at
                    )
                    VALUES (
                        %(id)s, %(name)s, %(class_)s, %(breed_count)s, %(genes)s, %(image_url)s,
                        %(owner_address)s, %(birth_date)s,
                        %(purity_score)s, %(hp)s, %(speed)s, %(skill)s, %(morale)s,
                        NOW(), NOW()
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        class = EXCLUDED.class,
                        breed_count = EXCLUDED.breed_count,
                        owner_address = EXCLUDED.owner_address,
                        purity_score = EXCLUDED.purity_score,
                        updated_at = NOW()
                    """,
                    axie,
                )
                stored += 1
            except Exception as e:
                logger.error(f"Error storing axie {axie.get('id')}: {e}")
                # Rollback this transaction and continue
                conn.rollback()
                continue

        conn.commit()

    return stored


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def handler(event, context):
    """
    Lambda handler for metadata ingestion - SkyMavis GraphQL.

    Optimized for new API key with higher rate limits:
    - 25 concurrent requests per batch
    - 500 axies per run
    - 0.5s delay between batches (respects 50 req/sec limit)
    """
    timestamp = datetime.now(timezone.utc)
    logger.info(f"Starting metadata ingestion at {timestamp}")

    async def ingest():
        # Minimal jitter needed
        jitter = random.uniform(0, INITIAL_JITTER_MAX_SECONDS)
        logger.info(f"Applying {jitter:.1f}s initial jitter")
        await asyncio.sleep(jitter)

        conn = get_db_connection()
        secrets = get_secrets()
        skymavis_key = secrets.get("SKYMAVIS_API_KEY")
        internal_secret = secrets.get("INTERNAL_SECRET")

        total_fetched = 0
        total_stored = 0
        axie_ids_to_fetch: Set[int] = set()

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
                # PRIORITY 1: Active listings (most valuable)
                missing_from_listings = get_axie_ids_from_listings(conn, limit=MAX_AXIES_PER_RUN)
                axie_ids_to_fetch.update(missing_from_listings)
                logger.info(f"Found {len(missing_from_listings)} axies from active listings missing metadata")

                # PRIORITY 2: Recent sales
                if len(axie_ids_to_fetch) < MAX_AXIES_PER_RUN:
                    remaining = MAX_AXIES_PER_RUN - len(axie_ids_to_fetch)
                    missing_from_sales = get_axie_ids_from_sales(conn, limit=remaining)
                    missing_from_sales -= axie_ids_to_fetch
                    axie_ids_to_fetch.update(missing_from_sales)
                    logger.info(f"Found {len(missing_from_sales)} additional axies from sales")

                # Filter to only missing
                missing_ids = get_missing_axie_ids(conn, axie_ids_to_fetch)
                logger.info(f"After filtering, {len(missing_ids)} axies need metadata")

                if not missing_ids:
                    logger.info("No missing axie metadata to fetch")
                    metrics.add_metric(name="AxiesFetched", unit=MetricUnit.Count, value=0)
                    metrics.add_metric(name="AxiesStored", unit=MetricUnit.Count, value=0)
                    return {
                        "total_fetched": 0,
                        "total_stored": 0,
                    }

                # Limit to max per run
                ids_to_process = list(missing_ids)[:MAX_AXIES_PER_RUN]
                logger.info(f"Processing {len(ids_to_process)} axies (limit: {MAX_AXIES_PER_RUN})")

                # Fetch metadata in batches
                for i in range(0, len(ids_to_process), AXIES_PER_BATCH):
                    batch_ids = ids_to_process[i:i + AXIES_PER_BATCH]
                    batch_num = i // AXIES_PER_BATCH + 1
                    total_batches = (len(ids_to_process) + AXIES_PER_BATCH - 1) // AXIES_PER_BATCH

                    logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch_ids)} axies)")

                    try:
                        # Fetch all axies in batch concurrently
                        fetch_tasks = [
                            fetch_axie_from_skymavis(
                                client, axie_id, skymavis_key, internal_secret
                            )
                            for axie_id in batch_ids
                        ]
                        axies_data = await asyncio.gather(*fetch_tasks, return_exceptions=True)

                        # Filter out None and exceptions
                        valid_axies = []
                        for data in axies_data:
                            if isinstance(data, Exception):
                                logger.error(f"Exception in batch: {data}")
                                continue
                            if data:
                                valid_axies.append(data)

                        total_fetched += len(valid_axies)
                        logger.info(f"Batch {batch_num}: fetched {len(valid_axies)}/{len(batch_ids)} axies from SkyMavis")

                        # Parse and store
                        parsed = [parse_axie_for_db(a) for a in valid_axies]
                        parsed = [p for p in parsed if p]  # Filter None

                        if parsed:
                            stored = store_axies(conn, parsed)
                            total_stored += stored
                            logger.info(f"Batch {batch_num}: stored {stored} axies")

                        # Delay between batches to respect rate limit
                        if i + AXIES_PER_BATCH < len(ids_to_process):
                            await asyncio.sleep(BATCH_DELAY_SECONDS)

                    except Exception as e:
                        logger.error(f"Error processing batch {batch_num}: {e}", exc_info=True)
                        continue

                logger.info(
                    f"Metadata ingestion complete: "
                    f"fetched {total_fetched}, stored {total_stored}"
                )

                metrics.add_metric(name="AxiesFetched", unit=MetricUnit.Count, value=total_fetched)
                metrics.add_metric(name="AxiesStored", unit=MetricUnit.Count, value=total_stored)

                # Calculate and log success rate
                if total_fetched > 0:
                    success_rate = (total_stored / total_fetched) * 100
                    metrics.add_metric(name="SuccessRate", unit=MetricUnit.Percent, value=success_rate)

                return {
                    "total_fetched": total_fetched,
                    "total_stored": total_stored,
                }

        except Exception as e:
            logger.error(f"Fatal error in metadata ingestion: {e}", exc_info=True)
            raise
        finally:
            if conn:
                conn.close()

    # Run async function
    result = asyncio.run(ingest())

    if "error" in result:
        return {
            "statusCode": 500,
            "body": json.dumps(result),
        }

    logger.info(
        f"Metadata ingestion complete: fetched {result['total_fetched']}, "
        f"stored {result['total_stored']}"
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Metadata ingestion complete",
            "axies_fetched": result["total_fetched"],
            "axies_stored": result["total_stored"],
            "timestamp": timestamp.isoformat(),
        }),
    }
