#!/usr/bin/env python3
"""
Axie Sales Fetcher - Public RPC Version

High-performance async sales fetcher using the public Ronin RPC.
No API key required, no daily rate limits.

Features:
- Parallel log fetching (5 workers, 499-block batches)
- Parallel receipt fetching (10 workers)
- Checkpoint-based resumability
- ~3,500 blocks/second throughput

Usage:
    # Fetch last 10,000 blocks
    python3 fetch_sales_public_rpc.py --blocks 10000

    # Fetch specific range
    python3 fetch_sales_public_rpc.py --start-block 46000000 --end-block 47000000

    # Resume from checkpoint
    python3 fetch_sales_public_rpc.py --resume --job-id june2025_sales
"""

import asyncio
import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from typing import Optional, List

import psycopg2

# Add backend to path
sys.path.insert(0, '/Users/alex/Ronin_API/backend/src')

from services.ronin_rpc_client import RoninRPCClient
from services.batch_processor import BatchProcessor, Sale, ProcessingStats
from services.checkpoint_manager import CheckpointManager, ProgressTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configuration
RATES = {'WETH': 3800.0, 'WRON': 0.15}
JUNE_2025_START_BLOCK = 45626000
CHECKPOINT_INTERVAL = 5000  # blocks


def get_config():
    """Get API keys and DB config from Secrets Manager."""
    result = subprocess.run(
        ['aws', 'secretsmanager', 'get-secret-value',
         '--secret-id', 'axie-explorer/api-keys',
         '--query', 'SecretString', '--output', 'text',
         '--region', 'us-east-1'],
        capture_output=True, text=True
    )
    secrets = json.loads(result.stdout)

    return {
        'db': {
            'host': secrets.get('RDS_HOST', 'cardforum.cn4c2su0o42n.us-east-1.rds.amazonaws.com'),
            'port': 5432,
            'dbname': secrets.get('RDS_DATABASE', 'postgres'),
            'user': secrets.get('RDS_USER', 'postgres'),
            'password': secrets.get('RDS_PASSWORD', '***REMOVED-ROTATE-ME***')
        }
    }


async def fetch_axie_classes(conn, axie_ids: List[int]) -> dict:
    """Fetch Axie classes from metadata table."""
    if not axie_ids:
        return {}

    cur = conn.cursor()
    cur.execute("SET search_path TO axie, public")

    # Get classes from metadata table
    placeholders = ','.join(['%s'] * len(axie_ids))
    cur.execute(f"""
        SELECT axie_id, class FROM axie_metadata
        WHERE axie_id IN ({placeholders})
    """, axie_ids)

    classes = {row[0]: row[1] for row in cur.fetchall()}
    cur.close()
    return classes


def insert_sales(conn, sales: List[Sale], classes: dict) -> int:
    """Insert sales into database."""
    if not sales:
        return 0

    cur = conn.cursor()
    cur.execute("SET search_path TO axie, public")

    inserted = 0
    for sale in sales:
        try:
            axie_class = classes.get(sale.axie_id)

            cur.execute("""
                INSERT INTO axie_sales (
                    tx_hash, axie_id, class, price_token, token_type, price_usd,
                    eth_usd_rate, ron_usd_rate, seller, buyer, block_number, block_timestamp
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tx_hash, axie_id) DO NOTHING
            """, (
                sale.tx_hash,
                sale.axie_id,
                axie_class,
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
            logger.warning(f"Failed to insert sale {sale.tx_hash}: {e}")

    conn.commit()
    cur.close()
    return inserted


async def main():
    parser = argparse.ArgumentParser(description='Fetch Axie sales using public RPC')
    parser.add_argument('--start-block', type=int, help='Start block number')
    parser.add_argument('--end-block', type=int, help='End block number')
    parser.add_argument('--blocks', type=int, default=10000, help='Number of recent blocks to fetch')
    parser.add_argument('--job-id', type=str, default='public_rpc_fetch', help='Job ID for checkpointing')
    parser.add_argument('--resume', action='store_true', help='Resume from last checkpoint')
    parser.add_argument('--log-workers', type=int, default=5, help='Parallel log workers')
    parser.add_argument('--receipt-workers', type=int, default=10, help='Parallel receipt workers')
    parser.add_argument('--dry-run', action='store_true', help='Fetch but do not insert to DB')
    args = parser.parse_args()

    config = get_config()

    print("=" * 70)
    print("AXIE SALES FETCHER - PUBLIC RPC")
    print("=" * 70)
    print(f"RPC: https://api.roninchain.com/rpc (no API key)")
    print(f"Workers: {args.log_workers} log, {args.receipt_workers} receipt")
    print(f"Job ID: {args.job_id}")
    print()

    # Connect to RPC
    async with RoninRPCClient() as rpc:
        current_block = await rpc.get_block_number()
        print(f"Current block: {current_block:,}")

        # Determine block range
        if args.start_block and args.end_block:
            start_block = args.start_block
            end_block = args.end_block
        elif args.resume:
            # Try to resume from checkpoint
            conn = psycopg2.connect(**config['db'])
            cur = conn.cursor()
            cur.execute("SET search_path TO axie, public")
            cur.execute("""
                SELECT last_block, records_synced FROM sync_state WHERE id = %s
            """, (args.job_id,))
            row = cur.fetchone()
            cur.close()
            conn.close()

            if row and row[0]:
                start_block = row[0] + 1
                print(f"Resuming from checkpoint: block {start_block:,} ({row[1]:,} records synced)")
            else:
                start_block = current_block - args.blocks
                print("No checkpoint found, starting fresh")
            end_block = current_block
        else:
            start_block = current_block - args.blocks
            end_block = current_block

        total_blocks = end_block - start_block + 1
        print(f"Block range: {start_block:,} - {end_block:,} ({total_blocks:,} blocks)")
        print()

        # Initialize batch processor
        processor = BatchProcessor(
            rpc,
            log_workers=args.log_workers,
            receipt_workers=args.receipt_workers,
            rates=RATES
        )

        # Progress tracker
        progress = ProgressTracker(total_blocks, start_block)

        # Connect to database
        conn = psycopg2.connect(**config['db']) if not args.dry_run else None

        # Track totals
        total_sales = 0
        total_inserted = 0
        t0 = time.time()

        # Progress callback
        def on_progress(phase: str, current: int, total: int, stats: ProcessingStats):
            report = progress.report(
                start_block + stats.blocks_processed,
                stats.sales_found
            )
            if report:
                print(report)

        # Checkpoint callback
        def on_checkpoint(block: int, sales_count: int):
            if conn and not args.dry_run:
                cur = conn.cursor()
                cur.execute("SET search_path TO axie, public")
                rate = stats.blocks_per_second if 'stats' in dir() else 0
                cur.execute("""
                    INSERT INTO sync_state (id, last_block, last_timestamp, records_synced, processing_rate, updated_at)
                    VALUES (%s, %s, NOW(), %s, %s, NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        last_block = EXCLUDED.last_block,
                        last_timestamp = NOW(),
                        records_synced = EXCLUDED.records_synced,
                        processing_rate = EXCLUDED.processing_rate,
                        updated_at = NOW()
                """, (args.job_id, block, sales_count, rate))
                conn.commit()
                cur.close()

        print("--- Starting Fetch ---")
        print()

        try:
            # Process in chunks for better progress visibility
            chunk_size = 50000  # Process 50k blocks at a time
            current = start_block

            while current <= end_block:
                chunk_end = min(current + chunk_size - 1, end_block)

                sales, stats = await processor.process_range(
                    from_block=current,
                    to_block=chunk_end,
                    progress_callback=on_progress,
                    checkpoint_callback=on_checkpoint,
                    checkpoint_interval=CHECKPOINT_INTERVAL
                )

                total_sales += len(sales)

                # Insert to database
                if conn and sales and not args.dry_run:
                    # Get classes for axies
                    axie_ids = list(set(s.axie_id for s in sales))
                    classes = await fetch_axie_classes(conn, axie_ids)

                    inserted = insert_sales(conn, sales, classes)
                    total_inserted += inserted
                    print(f"  Inserted {inserted:,} sales to database")

                current = chunk_end + 1

        except KeyboardInterrupt:
            print("\n\nInterrupted! Saving checkpoint...")
            if conn:
                on_checkpoint(current, total_sales)
            print("Checkpoint saved. Run with --resume to continue.")

        finally:
            if conn:
                conn.close()

        # Summary
        elapsed = time.time() - t0
        print()
        print("=" * 70)
        print("COMPLETE")
        print("=" * 70)
        print(f"Blocks processed: {total_blocks:,}")
        print(f"Sales found: {total_sales:,}")
        print(f"Sales inserted: {total_inserted:,}")
        print(f"Time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
        print(f"Throughput: {total_blocks/elapsed:.0f} blocks/sec")
        print(f"             {total_sales/elapsed:.1f} sales/sec")


if __name__ == "__main__":
    asyncio.run(main())
