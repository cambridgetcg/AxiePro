"""
Metadata Ingestion Lambda

Runs hourly to populate axie metadata for recently traded axies.
Uses Moralis to find recent transfers, then SkyMavis GraphQL for full metadata.

This populates the `axies` table which enables:
- Sales to have complete axie information
- Floor price queries by class/breed count
- Deal detection with accurate trait data
"""

import asyncio
import json
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
    get_moralis_api_key,
    get_moralis_headers,
    MORALIS_API_BASE_URL,
    MORALIS_RONIN_CHAIN,
    AXIE_CONTRACT,
)


# Configuration
AXIES_PER_BATCH = 1  # Single axie to minimize rate limit impact
MAX_AXIES_PER_RUN = 20  # Very conservative - 20 axies per hourly run
MORALIS_TRANSFERS_LIMIT = 100  # Per page
BATCH_DELAY_SECONDS = 3.0  # 3 second delay between SkyMavis API calls


# GraphQL query for axie metadata
AXIE_METADATA_QUERY = """
query GetAxieMetadata($axieId: ID!) {
  axie(axieId: $axieId) {
    id
    name
    class
    breedCount
    image
    owner
    birthDate
    matronId
    sireId
    genes
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

AXIE_BATCH_QUERY = """
query GetAxieBatch($axieIds: [ID!]!) {
  axies(ids: $axieIds) {
    results {
      id
      name
      class
      breedCount
      image
      owner
      birthDate
      matronId
      sireId
      genes
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
}
"""


@tracer.capture_method
@retry_on_transient_error
async def fetch_recent_transfers(
    client: httpx.AsyncClient,
    moralis_key: str,
    from_block: Optional[int] = None,
    to_block: Optional[int] = None,
    cursor: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch recent Axie transfers from Moralis."""
    url = f"{MORALIS_API_BASE_URL}/nft/{AXIE_CONTRACT}/transfers"
    params = {
        "chain": MORALIS_RONIN_CHAIN,
        "limit": MORALIS_TRANSFERS_LIMIT,
    }
    if from_block:
        params["from_block"] = from_block
    if to_block:
        params["to_block"] = to_block
    if cursor:
        params["cursor"] = cursor

    headers = get_moralis_headers(moralis_key)
    response = await client.get(url, params=params, headers=headers)
    response.raise_for_status()
    return response.json()


@tracer.capture_method
@retry_on_transient_error
async def fetch_axie_metadata(
    client: httpx.AsyncClient,
    axie_id: int,
    api_key: Optional[str] = None,
    internal_secret: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Fetch single axie metadata from SkyMavis GraphQL."""
    headers = get_skymavis_headers(api_key, internal_secret)
    endpoint = get_skymavis_endpoint()

    response = await client.post(
        endpoint,
        json={
            "query": AXIE_METADATA_QUERY,
            "variables": {"axieId": str(axie_id)},
        },
        headers=headers,
    )
    response.raise_for_status()

    result = response.json()
    try:
        check_graphql_errors(result)
    except GraphQLError as e:
        logger.warning(f"GraphQL error for axie {axie_id}: {e}")
        return None

    return result.get("data", {}).get("axie")


@tracer.capture_method
@retry_on_transient_error
async def fetch_axie_batch(
    client: httpx.AsyncClient,
    axie_ids: List[int],
    api_key: Optional[str] = None,
    internal_secret: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Fetch batch of axie metadata from SkyMavis GraphQL."""
    headers = get_skymavis_headers(api_key, internal_secret)
    endpoint = get_skymavis_endpoint()

    response = await client.post(
        endpoint,
        json={
            "query": AXIE_BATCH_QUERY,
            "variables": {"axieIds": [str(id) for id in axie_ids]},
        },
        headers=headers,
    )
    response.raise_for_status()

    result = response.json()
    try:
        check_graphql_errors(result)
    except GraphQLError as e:
        logger.warning(f"GraphQL error for batch: {e}")
        return []

    return result.get("data", {}).get("axies", {}).get("results", [])


@tracer.capture_method
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
    """Convert SkyMavis axie data to database record format."""
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

    return {
        "id": int(axie_id),
        "name": axie_data.get("name"),
        "class_": axie_data.get("class", "Unknown"),
        "breed_count": axie_data.get("breedCount", 0),
        "genes": axie_data.get("genes", ""),
        "image_url": axie_data.get("image"),
        "owner_address": axie_data.get("owner", "").lower() if axie_data.get("owner") else None,
        "birth_date": birth_date,
        "matron_id": matron_id,
        "sire_id": sire_id,
        "purity_score": purity_score,
        "hp": stats.get("hp"),
        "speed": stats.get("speed"),
        "skill": stats.get("skill"),
        "morale": stats.get("morale"),
    }


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
                cur.execute(
                    """
                    INSERT INTO axies (
                        id, name, class, breed_count, genes, image_url,
                        owner_address, birth_date, matron_id, sire_id,
                        purity_score, hp, speed, skill, morale,
                        created_at, updated_at
                    )
                    VALUES (
                        %(id)s, %(name)s, %(class_)s, %(breed_count)s, %(genes)s, %(image_url)s,
                        %(owner_address)s, %(birth_date)s, %(matron_id)s, %(sire_id)s,
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
                continue

        conn.commit()

    return stored


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def handler(event, context):
    """Lambda handler for metadata ingestion."""
    timestamp = datetime.now(timezone.utc)
    logger.info(f"Starting metadata ingestion at {timestamp}")

    async def ingest():
        conn = get_db_connection()
        secrets = get_secrets()
        api_key = secrets.get("SKYMAVIS_API_KEY")
        internal_secret = secrets.get("INTERNAL_SECRET")
        moralis_key = secrets.get("MORALIS_API_KEY")

        if not moralis_key:
            logger.error("Moralis API key not configured")
            return {"error": "Moralis API key not configured"}

        total_fetched = 0
        total_stored = 0
        axie_ids_to_fetch: Set[int] = set()

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
                # Strategy 1: Get axie_ids from sales that are missing metadata
                missing_from_sales = get_axie_ids_from_sales(conn, limit=MAX_AXIES_PER_RUN)
                axie_ids_to_fetch.update(missing_from_sales)
                logger.info(f"Found {len(missing_from_sales)} axies from sales missing metadata")

                # Strategy 2: Get recent transfers from Moralis
                if len(axie_ids_to_fetch) < MAX_AXIES_PER_RUN:
                    try:
                        transfers_response = await fetch_recent_transfers(
                            client, moralis_key
                        )
                        transfers = transfers_response.get("result", [])
                        for transfer in transfers:
                            token_id = transfer.get("token_id")
                            if token_id:
                                axie_ids_to_fetch.add(int(token_id))
                        logger.info(f"Found {len(transfers)} recent transfers from Moralis")
                    except Exception as e:
                        logger.warning(f"Could not fetch Moralis transfers: {e}")

                # Filter to only missing axies
                missing_ids = get_missing_axie_ids(conn, axie_ids_to_fetch)
                logger.info(f"After filtering, {len(missing_ids)} axies need metadata")

                if not missing_ids:
                    logger.info("No missing axie metadata to fetch")
                    return {
                        "total_fetched": 0,
                        "total_stored": 0,
                    }

                # Limit to max per run
                ids_to_process = list(missing_ids)[:MAX_AXIES_PER_RUN]

                # Fetch metadata in batches
                for i in range(0, len(ids_to_process), AXIES_PER_BATCH):
                    batch_ids = ids_to_process[i:i + AXIES_PER_BATCH]

                    try:
                        axies_data = await fetch_axie_batch(
                            client, batch_ids, api_key, internal_secret
                        )
                        total_fetched += len(axies_data)

                        # Parse and store
                        parsed = [parse_axie_for_db(a) for a in axies_data]
                        parsed = [p for p in parsed if p]  # Filter None

                        stored = store_axies(conn, parsed)
                        total_stored += stored

                        logger.info(
                            f"Batch {i // AXIES_PER_BATCH + 1}: "
                            f"fetched {len(axies_data)}, stored {stored}"
                        )

                        # Rate limit friendly - longer delay for SkyMavis API
                        await asyncio.sleep(BATCH_DELAY_SECONDS)

                    except Exception as e:
                        error_msg = str(e)
                        if "429" in error_msg or "Too Many Requests" in error_msg:
                            logger.warning(f"Rate limited at batch {i}, stopping to avoid further limits")
                            break  # Stop processing - we're rate limited
                        logger.error(f"Error processing batch at {i}: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error during metadata ingestion: {e}")
            metrics.add_metric(name="MetadataIngestionErrors", unit=MetricUnit.Count, value=1)
            raise

        finally:
            conn.close()

        return {
            "total_fetched": total_fetched,
            "total_stored": total_stored,
        }

    result = asyncio.run(ingest())

    if "error" in result:
        return {
            "statusCode": 500,
            "body": json.dumps(result),
        }

    metrics.add_metric(name="AxiesFetched", unit=MetricUnit.Count, value=result["total_fetched"])
    metrics.add_metric(name="AxiesStored", unit=MetricUnit.Count, value=result["total_stored"])

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
