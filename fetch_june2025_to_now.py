#!/usr/bin/env python3
"""
Fetch all Axie sales from June 2025 to present.

Features:
- Checkpoint-based resumability
- Progress logging
- Database insertion
- Graceful interrupt handling

Usage:
    python3 fetch_june2025_to_now.py
    python3 fetch_june2025_to_now.py --resume  # Resume from checkpoint
"""

import asyncio
import argparse
import json
import logging
import subprocess
import signal
import sys
import os
import time
from datetime import datetime
from typing import List

import psycopg2

# Setup paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

from src.services.ronin_rpc_client import RoninRPCClient
from src.services.batch_processor import BatchProcessor, Sale

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('fetch_june2025.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuration
JUNE_2025_START_BLOCK = 45626000
JOB_ID = "june2025_to_present"
CHUNK_SIZE = 10000  # Process 10k blocks at a time
CHECKPOINT_INTERVAL = 5000  # Save checkpoint every 5k blocks
RATES = {'WETH': 3800.0, 'WRON': 0.15}

# Graceful shutdown
shutdown_requested = False

def signal_handler(signum, frame):
    global shutdown_requested
    logger.info("Shutdown requested, finishing current chunk...")
    shutdown_requested = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def get_db_config():
    """Get DB config from AWS Secrets Manager."""
    result = subprocess.run(
        ['aws', 'secretsmanager', 'get-secret-value',
         '--secret-id', 'axie-explorer/api-keys',
         '--query', 'SecretString', '--output', 'text',
         '--region', 'us-east-1'],
        capture_output=True, text=True
    )
    secrets = json.loads(result.stdout)

    return {
        'host': secrets.get('RDS_HOST', 'cardforum.cn4c2su0o42n.us-east-1.rds.amazonaws.com'),
        'port': 5432,
        'dbname': secrets.get('RDS_DATABASE', 'postgres'),
        'user': secrets.get('RDS_USER', 'postgres'),
        'password': secrets.get('RDS_PASSWORD', '12345Cardforum')
    }


def get_checkpoint(conn, job_id: str) -> tuple:
    """Get last checkpoint from database."""
    cur = conn.cursor()
    cur.execute("SET search_path TO axie, public")
    cur.execute("""
        SELECT last_block, records_synced FROM sync_state WHERE id = %s
    """, (job_id,))
    row = cur.fetchone()
    cur.close()

    if row and row[0]:
        return row[0], row[1] or 0
    return None, 0


def save_checkpoint(conn, job_id: str, block: int, records: int, rate: float):
    """Save checkpoint to database."""
    cur = conn.cursor()
    cur.execute("SET search_path TO axie, public")
    cur.execute("""
        INSERT INTO sync_state (id, last_block, last_timestamp, records_synced, processing_rate, updated_at)
        VALUES (%s, %s, NOW(), %s, %s, NOW())
        ON CONFLICT (id) DO UPDATE SET
            last_block = EXCLUDED.last_block,
            last_timestamp = NOW(),
            records_synced = EXCLUDED.records_synced,
            processing_rate = EXCLUDED.processing_rate,
            updated_at = NOW()
    """, (job_id, block, records, rate))
    conn.commit()
    cur.close()


def insert_sales(conn, sales: List[Sale]) -> int:
    """Insert sales into database."""
    if not sales:
        return 0

    cur = conn.cursor()
    cur.execute("SET search_path TO axie, public")

    inserted = 0
    for sale in sales:
        try:
            cur.execute("""
                INSERT INTO axie_sales (
                    tx_hash, axie_id, price_token, token_type, price_usd,
                    eth_usd_rate, ron_usd_rate, seller, buyer,
                    block_number, block_timestamp
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tx_hash, axie_id) DO NOTHING
            """, (
                sale.tx_hash,
                sale.axie_id,
                sale.price_token,
                sale.token_type,
                sale.price_usd,
                RATES['WETH'],
                RATES['WRON'],
                sale.seller,
                sale.buyer,
                sale.block_number,
                sale.block_timestamp
            ))

            if cur.rowcount > 0:
                inserted += 1

        except Exception as e:
            logger.warning(f"Insert error for {sale.tx_hash}: {e}")

    conn.commit()
    cur.close()
    return inserted


async def fetch_chunk(rpc, processor, start_block: int, end_block: int) -> tuple:
    """Fetch a chunk of blocks and return sales."""
    sales, stats = await processor.process_range(
        from_block=start_block,
        to_block=end_block,
        checkpoint_interval=CHECKPOINT_INTERVAL
    )
    return sales, stats


async def main():
    global shutdown_requested

    parser = argparse.ArgumentParser()
    parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    parser.add_argument('--start-block', type=int, help='Override start block')
    parser.add_argument('--end-block', type=int, help='Override end block')
    args = parser.parse_args()

    db_config = get_db_config()
    conn = psycopg2.connect(**db_config)

    logger.info("=" * 70)
    logger.info("AXIE SALES FETCHER - JUNE 2025 TO PRESENT")
    logger.info("=" * 70)

    async with RoninRPCClient() as rpc:
        current_block = await rpc.get_block_number()

        # Determine start block
        if args.start_block:
            start_block = args.start_block
        elif args.resume:
            checkpoint_block, checkpoint_records = get_checkpoint(conn, JOB_ID)
            if checkpoint_block:
                start_block = checkpoint_block + 1
                logger.info(f"Resuming from checkpoint: block {start_block:,} ({checkpoint_records:,} records)")
            else:
                start_block = JUNE_2025_START_BLOCK
        else:
            start_block = JUNE_2025_START_BLOCK

        end_block = args.end_block or current_block
        total_blocks = end_block - start_block

        logger.info(f"Block range: {start_block:,} - {end_block:,}")
        logger.info(f"Total blocks: {total_blocks:,}")
        logger.info(f"Estimated time: {total_blocks/30/3600:.1f} hours @ 30 blk/s")
        logger.info("")

        processor = BatchProcessor(
            rpc,
            log_workers=3,
            receipt_workers=5,
            rates=RATES
        )

        # Process in chunks
        total_sales = 0
        total_inserted = 0
        t0 = time.time()
        current = start_block

        while current <= end_block and not shutdown_requested:
            chunk_end = min(current + CHUNK_SIZE - 1, end_block)
            chunk_start_time = time.time()

            # Progress
            progress = (current - start_block) / total_blocks * 100
            elapsed = time.time() - t0
            rate = (current - start_block) / elapsed if elapsed > 0 else 0
            eta_hours = (end_block - current) / rate / 3600 if rate > 0 else 0

            logger.info(f"[{progress:5.1f}%] Processing blocks {current:,} - {chunk_end:,} | "
                       f"Sales: {total_sales:,} | ETA: {eta_hours:.1f}h")

            try:
                # Fetch chunk
                sales, stats = await fetch_chunk(rpc, processor, current, chunk_end)
                total_sales += len(sales)

                # Insert to database
                if sales:
                    inserted = insert_sales(conn, sales)
                    total_inserted += inserted
                    logger.info(f"         Chunk: {len(sales)} sales found, {inserted} inserted")

                # Save checkpoint
                save_checkpoint(conn, JOB_ID, chunk_end, total_sales, stats.blocks_per_second)

            except Exception as e:
                logger.error(f"Error processing chunk: {e}")
                # Save checkpoint on error
                save_checkpoint(conn, JOB_ID, current - 1, total_sales, 0)
                raise

            current = chunk_end + 1

        # Final summary
        elapsed = time.time() - t0
        logger.info("")
        logger.info("=" * 70)
        if shutdown_requested:
            logger.info("INTERRUPTED - Checkpoint saved")
        else:
            logger.info("COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Blocks processed: {current - start_block:,}")
        logger.info(f"Sales found: {total_sales:,}")
        logger.info(f"Sales inserted: {total_inserted:,}")
        logger.info(f"Time: {elapsed/3600:.1f} hours")
        logger.info(f"Avg speed: {(current - start_block)/elapsed:.0f} blk/s")

        # Final checkpoint
        save_checkpoint(conn, JOB_ID, current - 1, total_sales, (current - start_block)/elapsed)

    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
