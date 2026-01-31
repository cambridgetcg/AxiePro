"""
Metadata Ingestion Lambda - Moralis-First Approach

CHANGED: Uses Moralis as primary metadata source to avoid SkyMavis rate limiting.
Falls back to SkyMavis only for gene data (Axie-specific).

This version should achieve 100+ axies/hour throughput vs 0 with SkyMavis-only.
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
    get_moralis_api_key,
    get_moralis_headers,
    MORALIS_API_BASE_URL,
    MORALIS_RONIN_CHAIN,
    AXIE_CONTRACT,
)


# Configuration - More aggressive now that we're using Moralis
AXIES_PER_BATCH = 10  # Increased from 1 - Moralis can handle more
MAX_AXIES_PER_RUN = 100  # Increased from 10 - target 100+ axies/hour
MORALIS_TRANSFERS_LIMIT = 100  # Per page
BATCH_DELAY_SECONDS = 2.0  # Reduced from 6s - Moralis has higher limits
INITIAL_JITTER_MAX_SECONDS = 15  # Reduced jitter, less collision risk


# GraphQL query for genes ONLY (fallback to SkyMavis for detailed gene data)
AXIE_GENES_QUERY = """
query GetAxieGenes($axieId: ID!) {
  axie(axieId: $axieId) {
    id
    genes
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
async def fetch_axie_from_moralis(
    client: httpx.AsyncClient,
    axie_id: int,
    moralis_key: str,
) -> Optional[Dict[str, Any]]:
    """
    Fetch Axie metadata from Moralis NFT API.

    Moralis provides:
    - Basic NFT data (token_id, owner, contract)
    - Metadata JSON (may contain Axie-specific data)
    - Token URI

    Returns structured data matching our database schema.
    """
    url = f"{MORALIS_API_BASE_URL}/nft/{AXIE_CONTRACT}/{axie_id}"
    params = {"chain": MORALIS_RONIN_CHAIN, "format": "decimal"}
    headers = get_moralis_headers(moralis_key)

    try:
        response = await client.get(url, params=params, headers=headers)

        # Handle rate limiting gracefully
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            logger.warning(f"Moralis rate limited, waiting {retry_after}s")
            await asyncio.sleep(retry_after)
            # Retry once
            response = await client.get(url, params=params, headers=headers)

        response.raise_for_status()
        data = response.json()

        # Parse Moralis response
        token_id = data.get("token_id")
        owner = data.get("owner_of", "").lower() if data.get("owner_of") else None

        # Metadata might be a JSON string or dict
        metadata = data.get("metadata")
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}
        elif not metadata:
            metadata = {}

        # Extract Axie-specific data from metadata
        # Moralis metadata structure varies, try common patterns
        axie_data = {
            "id": int(token_id or axie_id),
            "name": data.get("name") or metadata.get("name"),
            "owner": owner,
            "token_uri": data.get("token_uri"),
        }

        # Try to extract Axie class from metadata
        # Common patterns: metadata.class, metadata.attributes, etc.
        if "class" in metadata:
            axie_data["class"] = metadata["class"]
        elif "attributes" in metadata:
            # Search attributes for class
            for attr in metadata.get("attributes", []):
                if attr.get("trait_type") == "class":
                    axie_data["class"] = attr.get("value")
                    break

        # Extract other fields if available
        axie_data["breed_count"] = metadata.get("breedCount", 0)
        axie_data["image"] = metadata.get("image") or data.get("token_uri")

        # Stats if available
        stats = metadata.get("stats", {})
        if stats:
            axie_data["stats"] = stats

        return axie_data

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(f"Axie {axie_id} not found in Moralis")
            return None
        elif e.response.status_code == 429:
            logger.error(f"Moralis rate limit exceeded for axie {axie_id}")
            return None
        else:
            logger.error(f"Moralis HTTP error for axie {axie_id}: {e}")
            return None
    except Exception as e:
        logger.error(f"Error fetching axie {axie_id} from Moralis: {e}")
        return None


@tracer.capture_method
async def fetch_genes_from_skymavis(
    client: httpx.AsyncClient,
    axie_id: int,
    api_key: Optional[str] = None,
    internal_secret: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Fetch ONLY gene data from SkyMavis (fallback for detailed Axie data).

    This is a lightweight query compared to full metadata fetch.
    Only used when Moralis data is insufficient.
    """
    headers = get_skymavis_headers(api_key, internal_secret)
    endpoint = get_skymavis_endpoint()

    try:
        response = await client.post(
            endpoint,
            json={
                "query": AXIE_GENES_QUERY,
                "variables": {"axieId": str(axie_id)},
            },
            headers=headers,
            timeout=30.0,
        )

        # Don't retry on 429 - we want to fail fast and rely on Moralis
        if response.status_code == 429:
            logger.warning(f"SkyMavis rate limited for genes {axie_id}, skipping")
            return None

        response.raise_for_status()
        result = response.json()

        try:
            check_graphql_errors(result)
        except GraphQLError as e:
            logger.warning(f"GraphQL error for genes {axie_id}: {e}")
            return None

        return result.get("data", {}).get("axie")

    except Exception as e:
        logger.warning(f"Could not fetch genes for axie {axie_id}: {e}")
        return None


@tracer.capture_method
async def fetch_axie_hybrid(
    client: httpx.AsyncClient,
    axie_id: int,
    moralis_key: str,
    skymavis_key: Optional[str] = None,
    internal_secret: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Hybrid fetch: Moralis first, SkyMavis fallback for genes.

    Strategy:
    1. Fetch from Moralis (fast, higher rate limit)
    2. If Moralis has complete data, use it
    3. If missing genes/parts, try SkyMavis (low priority, may fail)
    4. Return best available data
    """
    # Primary: Moralis
    moralis_data = await fetch_axie_from_moralis(client, axie_id, moralis_key)

    if not moralis_data:
        logger.warning(f"No data from Moralis for axie {axie_id}")
        return None

    # Check if we need gene data
    needs_genes = not moralis_data.get("genes")

    # Optional: Try to enrich with SkyMavis genes (best effort, may fail)
    if needs_genes and skymavis_key:
        logger.debug(f"Attempting to fetch genes for axie {axie_id} from SkyMavis")
        genes_data = await fetch_genes_from_skymavis(
            client, axie_id, skymavis_key, internal_secret
        )

        if genes_data:
            # Merge gene data into Moralis data
            moralis_data["genes"] = genes_data.get("genes", "")
            moralis_data["parts"] = genes_data.get("parts", [])
            logger.debug(f"Enriched axie {axie_id} with SkyMavis gene data")

    return moralis_data


def parse_axie_for_db_moralis(axie_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Convert Moralis/hybrid axie data to database record format.

    Handles data from Moralis + optional SkyMavis enrichment.
    """
    if not axie_data:
        return None

    axie_id = axie_data.get("id")
    if not axie_id:
        return None

    # Parse stats (may be from Moralis metadata or SkyMavis)
    stats = axie_data.get("stats", {}) or {}

    # Parse birth date if available
    birth_date = None
    bd = axie_data.get("birthDate")
    if bd:
        try:
            birth_date = datetime.fromtimestamp(bd, tz=timezone.utc)
        except (ValueError, TypeError, OSError):
            pass

    # Parent IDs (may not be in Moralis)
    matron_id = axie_data.get("matronId") or axie_data.get("matron_id")
    sire_id = axie_data.get("sireId") or axie_data.get("sire_id")
    if matron_id == 0:
        matron_id = None
    if sire_id == 0:
        sire_id = None

    # Calculate purity if we have parts
    purity_score = 0
    parts = axie_data.get("parts", [])
    axie_class = axie_data.get("class", "Unknown")
    if parts and axie_class:
        axie_class_lower = axie_class.lower()
        purity_score = sum(
            1 for part in parts
            if part.get("class", "").lower() == axie_class_lower
        )

    # Owner address (normalize to lowercase)
    owner = axie_data.get("owner")
    if owner:
        owner = owner.lower()

    return {
        "id": int(axie_id),
        "name": axie_data.get("name"),
        "class_": axie_class,
        "breed_count": axie_data.get("breed_count", 0) or axie_data.get("breedCount", 0),
        "genes": axie_data.get("genes", ""),
        "image_url": axie_data.get("image") or axie_data.get("token_uri"),
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


# Import helper functions from original file
# (These are unchanged)
from src.lambdas.metadata_ingestion import (
    get_axie_ids_from_listings,
    get_axie_ids_from_sales,
    get_missing_axie_ids,
    store_axies,
)


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def handler(event, context):
    """
    Lambda handler for metadata ingestion - Moralis-first approach.

    CHANGES vs original:
    - Uses Moralis as primary data source
    - Falls back to SkyMavis only for gene data (optional enrichment)
    - Increased batch size and throughput targets
    - Reduced delays between batches
    """
    timestamp = datetime.now(timezone.utc)
    logger.info(f"Starting Moralis-first metadata ingestion at {timestamp}")

    async def ingest():
        # Reduced jitter since Moralis has separate rate limit
        jitter = random.uniform(0, INITIAL_JITTER_MAX_SECONDS)
        logger.info(f"Applying {jitter:.1f}s initial jitter")
        await asyncio.sleep(jitter)

        conn = get_db_connection()
        secrets = get_secrets()
        skymavis_key = secrets.get("SKYMAVIS_API_KEY")  # Optional now
        internal_secret = secrets.get("INTERNAL_SECRET")
        moralis_key = secrets.get("MORALIS_API_KEY")

        if not moralis_key:
            logger.error("Moralis API key not configured - cannot proceed")
            return {"error": "Moralis API key not configured"}

        total_fetched = 0
        total_stored = 0
        total_enriched = 0  # Track how many got SkyMavis genes
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
                        "total_enriched": 0,
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
                        # Fetch all axies in batch using hybrid approach
                        fetch_tasks = [
                            fetch_axie_hybrid(
                                client, axie_id, moralis_key, skymavis_key, internal_secret
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
                                # Track if we got genes from SkyMavis
                                if data.get("genes"):
                                    total_enriched += 1

                        total_fetched += len(valid_axies)
                        logger.info(f"Batch {batch_num}: fetched {len(valid_axies)}/{len(batch_ids)} axies from Moralis")

                        # Parse and store
                        parsed = [parse_axie_for_db_moralis(a) for a in valid_axies]
                        parsed = [p for p in parsed if p]  # Filter None

                        if parsed:
                            stored = store_axies(conn, parsed)
                            total_stored += stored
                            logger.info(f"Batch {batch_num}: stored {stored} axies")

                        # Delay between batches (shorter now)
                        if i + AXIES_PER_BATCH < len(ids_to_process):
                            await asyncio.sleep(BATCH_DELAY_SECONDS)

                    except Exception as e:
                        logger.error(f"Error processing batch {batch_num}: {e}", exc_info=True)
                        continue

                logger.info(
                    f"Metadata ingestion complete: "
                    f"fetched {total_fetched}, stored {total_stored}, "
                    f"enriched with genes {total_enriched}"
                )

                metrics.add_metric(name="AxiesFetched", unit=MetricUnit.Count, value=total_fetched)
                metrics.add_metric(name="AxiesStored", unit=MetricUnit.Count, value=total_stored)
                metrics.add_metric(name="AxiesEnriched", unit=MetricUnit.Count, value=total_enriched)

                return {
                    "total_fetched": total_fetched,
                    "total_stored": total_stored,
                    "total_enriched": total_enriched,
                }

        except Exception as e:
            logger.error(f"Fatal error in metadata ingestion: {e}", exc_info=True)
            raise
        finally:
            if conn:
                conn.close()

    # Run async function
    return asyncio.run(ingest())
