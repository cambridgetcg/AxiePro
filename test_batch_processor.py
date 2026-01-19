#!/usr/bin/env python3
"""
Test the batch processor with 1,000 blocks.
"""

import asyncio
import sys
import os
import time

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'backend'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'backend', 'src'))

from src.services.ronin_rpc_client import RoninRPCClient
from src.services.batch_processor import BatchProcessor


async def main():
    print("=" * 60)
    print("BATCH PROCESSOR TEST - 1,000 blocks")
    print("=" * 60)

    async with RoninRPCClient() as rpc:
        processor = BatchProcessor(
            rpc,
            log_workers=3,      # Reduced for rate limit safety
            receipt_workers=5   # Reduced for rate limit safety
        )

        current = await rpc.get_block_number()
        start_block = current - 1000

        print(f"Current block: {current:,}")
        print(f"Testing range: {start_block:,} - {current:,}")
        print()

        t0 = time.time()
        last_report = t0

        def progress_callback(phase, current, total, stats):
            nonlocal last_report
            now = time.time()
            if now - last_report > 3 or phase == "checkpoint":
                elapsed = stats.elapsed_seconds
                print(f"  [{phase:10}] {stats.blocks_processed:,} blocks | {stats.sales_found} sales | {stats.blocks_per_second:.0f} blk/s")
                last_report = now

        print("Starting batch processing...")
        sales, stats = await processor.process_range(
            from_block=start_block,
            to_block=current,
            progress_callback=progress_callback
        )

        elapsed = time.time() - t0

        print()
        print("=" * 60)
        print("RESULTS")
        print("=" * 60)
        print(f"Blocks processed: {stats.blocks_processed:,}")
        print(f"Logs fetched: {stats.logs_fetched:,}")
        print(f"Receipts fetched: {stats.receipts_fetched:,}")
        print(f"Sales found: {stats.sales_found}")
        print(f"Time: {elapsed:.1f}s")
        print(f"Throughput: {stats.blocks_per_second:.0f} blocks/sec")

        if sales:
            print(f"\nRecent sales (top 10 by price):")
            for sale in sorted(sales, key=lambda s: s.price_usd, reverse=True)[:10]:
                print(f"  Axie #{sale.axie_id:>8}: ${sale.price_usd:>10.2f} ({sale.token_type})")

        print("\n[PASS] Batch processor working!")


if __name__ == "__main__":
    asyncio.run(main())
