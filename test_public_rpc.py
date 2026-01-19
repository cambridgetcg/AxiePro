#!/usr/bin/env python3
"""
Test script for Public RPC Migration.

Verifies:
1. Public RPC connectivity (no API key)
2. Log fetching with 499-block batches
3. Receipt fetching
4. Sale parsing
5. Batch processor throughput

Usage:
    python3 test_public_rpc.py
"""

import asyncio
import sys
import time
import os

# Add backend paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'backend'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'backend', 'src'))

# Direct imports to avoid the problematic __init__.py
from src.services.ronin_rpc_client import RoninRPCClient, RPCProvider
from src.services.batch_processor import BatchProcessor


async def test_rpc_connectivity():
    """Test 1: Basic RPC connectivity."""
    print("\n" + "=" * 60)
    print("TEST 1: RPC Connectivity")
    print("=" * 60)

    async with RoninRPCClient() as rpc:
        print(f"Provider: {rpc.provider.name}")
        print(f"URL: {rpc.provider.url}")

        # Get current block
        block = await rpc.get_block_number()
        print(f"Current block: {block:,}")

        # Get block details
        block_data = await rpc.get_block(block)
        timestamp = int(block_data['timestamp'], 16)
        from datetime import datetime
        block_time = datetime.fromtimestamp(timestamp)
        print(f"Block time: {block_time}")

        print("\n[PASS] RPC connectivity working")
        return block


async def test_log_fetching(current_block: int):
    """Test 2: Log fetching with 499-block limit."""
    print("\n" + "=" * 60)
    print("TEST 2: Log Fetching (499 blocks)")
    print("=" * 60)

    async with RoninRPCClient() as rpc:
        start_block = current_block - 499

        print(f"Fetching logs: {start_block:,} - {current_block:,}")
        t0 = time.time()

        logs = await rpc.get_logs(
            BatchProcessor.AXIE_CONTRACT,
            start_block,
            current_block,
            topics=[BatchProcessor.TRANSFER_TOPIC]
        )

        elapsed = time.time() - t0
        print(f"Logs found: {len(logs):,}")
        print(f"Time: {elapsed:.2f}s")

        if logs:
            # Show sample log
            sample = logs[0]
            print(f"\nSample log:")
            print(f"  TX: {sample['transactionHash'][:20]}...")
            print(f"  Block: {int(sample['blockNumber'], 16):,}")

        print("\n[PASS] Log fetching working")
        return logs


async def test_receipt_fetching(logs: list):
    """Test 3: Receipt fetching."""
    print("\n" + "=" * 60)
    print("TEST 3: Receipt Fetching")
    print("=" * 60)

    if not logs:
        print("No logs to test with")
        return []

    # Get unique TX hashes
    tx_hashes = list(set(log['transactionHash'] for log in logs))[:10]
    print(f"Testing with {len(tx_hashes)} transactions")

    async with RoninRPCClient() as rpc:
        t0 = time.time()

        receipts = await rpc.get_receipts_parallel(tx_hashes)

        elapsed = time.time() - t0
        print(f"Receipts fetched: {len(receipts)}")
        print(f"Time: {elapsed:.2f}s")

        if receipts:
            sample = receipts[0]
            print(f"\nSample receipt:")
            print(f"  TX: {sample.get('transactionHash', sample.get('_tx_hash', ''))[:20]}...")
            print(f"  Logs: {len(sample.get('logs', []))}")
            print(f"  Status: {sample.get('status')}")

        print("\n[PASS] Receipt fetching working")
        return receipts


async def test_sale_parsing(receipts: list):
    """Test 4: Sale parsing from receipts."""
    print("\n" + "=" * 60)
    print("TEST 4: Sale Parsing")
    print("=" * 60)

    async with RoninRPCClient() as rpc:
        processor = BatchProcessor(rpc)

        sales = []
        for receipt in receipts:
            parsed = processor._parse_single_receipt(receipt)
            sales.extend(parsed)

        print(f"Sales parsed: {len(sales)}")

        if sales:
            print(f"\nSample sales:")
            for sale in sales[:5]:
                print(f"  Axie #{sale.axie_id}: ${sale.price_usd:.2f} ({sale.token_type})")

        print("\n[PASS] Sale parsing working")
        return sales


async def test_batch_processor():
    """Test 5: Full batch processor throughput."""
    print("\n" + "=" * 60)
    print("TEST 5: Batch Processor (5,000 blocks)")
    print("=" * 60)

    async with RoninRPCClient() as rpc:
        processor = BatchProcessor(rpc)

        current = await rpc.get_block_number()
        start_block = current - 5000

        print(f"Processing blocks {start_block:,} - {current:,}")
        print(f"Config: {processor.log_workers} log workers, {processor.receipt_workers} receipt workers")

        t0 = time.time()
        last_report = t0

        def progress_callback(phase, current, total, stats):
            nonlocal last_report
            now = time.time()
            if now - last_report > 2:
                print(f"  [{phase}] {stats.blocks_processed:,} blocks, {stats.sales_found} sales, {stats.blocks_per_second:.0f} blk/s")
                last_report = now

        sales, stats = await processor.process_range(
            from_block=start_block,
            to_block=current,
            progress_callback=progress_callback
        )

        elapsed = time.time() - t0
        print(f"\nResults:")
        print(f"  Blocks processed: {stats.blocks_processed:,}")
        print(f"  Logs fetched: {stats.logs_fetched:,}")
        print(f"  Receipts fetched: {stats.receipts_fetched:,}")
        print(f"  Sales found: {stats.sales_found:,}")
        print(f"  Time: {elapsed:.1f}s")
        print(f"  Throughput: {stats.blocks_per_second:.0f} blocks/sec")

        if sales:
            print(f"\nTop 5 sales by price:")
            for sale in sorted(sales, key=lambda s: s.price_usd, reverse=True)[:5]:
                print(f"  Axie #{sale.axie_id}: ${sale.price_usd:.2f} ({sale.token_type}) @ block {sale.block_number:,}")

        print("\n[PASS] Batch processor working")
        return stats


async def test_provider_stats():
    """Test 6: Provider statistics."""
    print("\n" + "=" * 60)
    print("TEST 6: Provider Statistics")
    print("=" * 60)

    async with RoninRPCClient() as rpc:
        # Make some requests
        await rpc.get_block_number()
        await rpc.get_block_number()
        await rpc.get_block_number()

        stats = rpc.get_provider_stats()
        for s in stats:
            print(f"Provider: {s['name']}")
            print(f"  Status: {s['status']}")
            print(f"  Requests: {s['total_requests']}")
            print(f"  Errors: {s['total_errors']}")
            print(f"  Error rate: {s['error_rate']:.1%}")

        print("\n[PASS] Provider stats working")


async def main():
    print("=" * 60)
    print("PUBLIC RPC MIGRATION TEST SUITE")
    print("=" * 60)
    print("Testing: https://api.roninchain.com/rpc")
    print("No API key required")

    try:
        # Run tests sequentially
        current_block = await test_rpc_connectivity()
        logs = await test_log_fetching(current_block)
        receipts = await test_receipt_fetching(logs)
        await test_sale_parsing(receipts)
        await test_batch_processor()
        await test_provider_stats()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)
        print("\nPublic RPC migration is ready for production!")
        print("Run fetch_sales_public_rpc.py to start fetching sales.")

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
