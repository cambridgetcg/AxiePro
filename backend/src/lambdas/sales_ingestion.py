"""
Sales Ingestion Lambda

Runs every 30 minutes to capture settled marketplace sales.
Fetches directly from Ronin blockchain via RPC and stores in Aurora PostgreSQL.

Uses on-chain event parsing - no external API rate limits.
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any

from aws_lambda_powertools.metrics import MetricUnit

# Import shared utilities from common module
from src.lambdas.common import (
    logger,
    tracer,
    metrics,
    get_db_connection,
)

# Import Ronin RPC client
from src.services.ronin_rpc_client import RoninRPCClient, Sale, RoninRPCError


# Configuration
BLOCKS_PER_30_MIN = 900  # ~2 sec block time = 900 blocks in 30 min
MAX_BLOCKS_PER_RUN = 1500  # Conservative limit for public RPC rate limits
DEFAULT_LOOKBACK_BLOCKS = 1000  # ~33 min lookback on first run (conservative)


@tracer.capture_method
def get_last_processed_block(conn) -> Optional[int]:
    """
    Get the last processed block number from database.

    Uses a metadata table to track ingestion progress.
    Falls back to estimating from recent sales if not available.
    """
    # Try metadata table first
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT value FROM ingestion_metadata WHERE key = 'sales_last_block'"
            )
            result = cur.fetchone()
            if result and result[0] and result[0] != '0':
                return int(result[0])
    except Exception as e:
        logger.debug(f"Metadata table not available: {e}")
        # Rollback to clear the failed transaction state
        conn.rollback()

    # Fall back to checking if we have any sales data
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(sold_at) FROM sales")
            result = cur.fetchone()
            if result and result[0]:
                # We have sales but no block tracking - use time-based lookback
                logger.info("No block metadata found, will use time-based lookback")
                return None
    except Exception as e:
        logger.debug(f"Could not check sales table: {e}")
        conn.rollback()

    return None


@tracer.capture_method
def save_last_processed_block(conn, block_number: int):
    """Save the last processed block number to database."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ingestion_metadata (key, value, updated_at)
                VALUES ('sales_last_block', %s, %s)
                ON CONFLICT (key) DO UPDATE SET
                    value = EXCLUDED.value,
                    updated_at = EXCLUDED.updated_at
                """,
                (str(block_number), datetime.now(timezone.utc)),
            )
            conn.commit()
    except Exception as e:
        logger.warning(f"Could not save block metadata (table may not exist): {e}")
        # Rollback to clear failed transaction state
        try:
            conn.rollback()
        except Exception:
            pass
        # Don't fail the whole ingestion for this


@tracer.capture_method
def convert_sale_to_record(sale: Sale) -> Dict[str, Any]:
    """Convert RPC Sale object to database record format."""
    # Convert token price to ETH equivalent for consistency
    # WETH is already in ETH units, WRON needs conversion
    if sale.token_type == "WETH":
        price_eth = Decimal(str(sale.price_token))
    else:
        # WRON price - store as-is, price_usd is the reference
        price_eth = Decimal(str(sale.price_token))

    return {
        "axie_id": sale.axie_id,
        "seller_address": sale.seller.lower() if sale.seller else None,
        "buyer_address": sale.buyer.lower() if sale.buyer else None,
        "price_eth": price_eth,
        "price_usd": Decimal(str(sale.price_usd)) if sale.price_usd else None,
        "tx_hash": sale.tx_hash,
        "sold_at": sale.block_timestamp or datetime.now(timezone.utc),
        "marketplace": "official",
        "token_type": sale.token_type,  # New field to track payment token
    }


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
async def fetch_block_timestamps(
    rpc_client: RoninRPCClient,
    sales: List[Sale],
) -> List[Sale]:
    """Fetch and attach block timestamps to sales."""
    # Get unique block numbers
    block_numbers = list(set(s.block_number for s in sales))

    # Fetch timestamps in parallel (limit concurrency)
    timestamps = {}

    async def fetch_timestamp(block_num: int):
        try:
            ts = await rpc_client.get_block_timestamp(block_num)
            timestamps[block_num] = ts
        except Exception as e:
            logger.warning(f"Could not get timestamp for block {block_num}: {e}")
            timestamps[block_num] = datetime.now(timezone.utc)

    # Process in batches of 10
    for i in range(0, len(block_numbers), 10):
        batch = block_numbers[i:i+10]
        await asyncio.gather(*[fetch_timestamp(b) for b in batch])

    # Attach timestamps to sales
    for sale in sales:
        sale.block_timestamp = timestamps.get(sale.block_number)

    return sales


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def handler(event, context):
    """Lambda handler for sales ingestion via Ronin RPC."""
    timestamp = datetime.now(timezone.utc)
    logger.info(f"Starting sales ingestion (Ronin RPC) at {timestamp}")

    async def ingest():
        conn = get_db_connection()

        total_inserted = 0
        total_fetched = 0
        from_block = 0
        to_block = 0

        try:
            async with RoninRPCClient() as rpc_client:
                # Get current block
                current_block = await rpc_client.get_block_number()
                logger.info(f"Current Ronin block: {current_block}")

                # Determine block range to scan
                last_block = get_last_processed_block(conn)

                if last_block:
                    # Resume from last processed block
                    from_block = last_block + 1
                else:
                    # First run or no metadata - use conservative lookback
                    from_block = max(1, current_block - DEFAULT_LOOKBACK_BLOCKS)
                    logger.info(f"No previous block found, looking back {DEFAULT_LOOKBACK_BLOCKS} blocks")

                to_block = current_block

                # Safety limit
                if to_block - from_block > MAX_BLOCKS_PER_RUN:
                    logger.warning(
                        f"Block range too large ({to_block - from_block}), "
                        f"limiting to {MAX_BLOCKS_PER_RUN} blocks"
                    )
                    from_block = to_block - MAX_BLOCKS_PER_RUN

                # Skip if no new blocks
                if from_block > to_block:
                    logger.info("No new blocks to process")
                    return {
                        "total_fetched": 0,
                        "total_inserted": 0,
                        "from_block": from_block,
                        "to_block": to_block,
                    }

                logger.info(
                    f"Scanning blocks {from_block} to {to_block} "
                    f"({to_block - from_block + 1} blocks)"
                )

                # Fetch sales from blockchain
                def progress_callback(phase: str, current: int, total: int):
                    if total > 0 and current % 100 == 0:
                        logger.info(f"Progress [{phase}]: {current}/{total}")

                sales = await rpc_client.fetch_sales(
                    from_block=from_block,
                    to_block=to_block,
                    log_workers=3,  # Conservative for public RPC
                    receipt_workers=5,  # Reduced to avoid rate limits
                    progress_callback=progress_callback,
                )

                total_fetched = len(sales)
                logger.info(f"Found {total_fetched} sales in block range")

                if sales:
                    # Fetch block timestamps
                    sales = await fetch_block_timestamps(rpc_client, sales)

                    # Convert to database format
                    records = [convert_sale_to_record(s) for s in sales]

                    # Store in database
                    total_inserted = store_sales(conn, records)
                    logger.info(f"Inserted {total_inserted} new sales")

                # Save progress
                save_last_processed_block(conn, to_block)

                # Log provider stats
                provider_stats = rpc_client.get_provider_stats()
                logger.info(
                    "RPC provider stats",
                    extra={"providers": provider_stats},
                )

        except RoninRPCError as e:
            logger.error(f"RPC error during ingestion: {e}")
            metrics.add_metric(name="IngestionRPCErrors", unit=MetricUnit.Count, value=1)
            raise

        except Exception as e:
            logger.error(f"Error during ingestion: {e}")
            metrics.add_metric(name="IngestionErrors", unit=MetricUnit.Count, value=1)
            raise

        finally:
            conn.close()

        return {
            "total_fetched": total_fetched,
            "total_inserted": total_inserted,
            "from_block": from_block,
            "to_block": to_block,
        }

    result = asyncio.run(ingest())

    # Record metrics
    metrics.add_metric(name="SalesFetched", unit=MetricUnit.Count, value=result["total_fetched"])
    metrics.add_metric(name="SalesInserted", unit=MetricUnit.Count, value=result["total_inserted"])
    metrics.add_metric(
        name="BlocksScanned",
        unit=MetricUnit.Count,
        value=max(0, result["to_block"] - result["from_block"] + 1),
    )

    logger.info(
        f"Sales ingestion complete: fetched {result['total_fetched']}, "
        f"inserted {result['total_inserted']} from blocks "
        f"{result['from_block']}-{result['to_block']}"
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Sales ingestion complete",
            "sales_fetched": result["total_fetched"],
            "sales_inserted": result["total_inserted"],
            "from_block": result["from_block"],
            "to_block": result["to_block"],
            "timestamp": timestamp.isoformat(),
        }),
    }
