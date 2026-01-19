#!/usr/bin/env python3
"""
Simple RPC connectivity test.
"""

import asyncio
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'backend'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'backend', 'src'))

from src.services.ronin_rpc_client import RoninRPCClient


async def main():
    print("Testing Public Ronin RPC...")
    print("URL: https://api.roninchain.com/rpc")
    print()

    async with RoninRPCClient() as rpc:
        # Test 1: Get current block
        print("1. Getting current block...")
        block = await rpc.get_block_number()
        print(f"   Current block: {block:,}")

        # Test 2: Get block details
        print("\n2. Getting block details...")
        await asyncio.sleep(1)  # Rate limit protection
        block_data = await rpc.get_block(block)
        from datetime import datetime
        timestamp = int(block_data['timestamp'], 16)
        block_time = datetime.fromtimestamp(timestamp)
        print(f"   Block time: {block_time}")
        print(f"   Transactions: {len(block_data.get('transactions', []))}")

        # Test 3: Get logs (small range)
        print("\n3. Getting logs (100 blocks)...")
        await asyncio.sleep(1)
        AXIE_CONTRACT = "0x32950db2a7164ae833121501c797d79e7b79d74c"
        TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

        logs = await rpc.get_logs(
            AXIE_CONTRACT,
            block - 100,
            block,
            topics=[TRANSFER_TOPIC]
        )
        print(f"   Logs found: {len(logs)}")

        if logs:
            tx_hashes = list(set(log['transactionHash'] for log in logs))[:3]

            # Test 4: Get receipt
            print(f"\n4. Getting receipt for {len(tx_hashes)} transactions...")
            await asyncio.sleep(1)

            for tx in tx_hashes:
                receipt = await rpc.get_transaction_receipt(tx)
                if receipt:
                    print(f"   TX {tx[:20]}... - {len(receipt.get('logs', []))} logs")
                await asyncio.sleep(0.5)

        print("\n" + "=" * 50)
        print("All tests passed!")
        print("=" * 50)

        # Provider stats
        stats = rpc.get_provider_stats()
        for s in stats:
            print(f"\nProvider: {s['name']}")
            print(f"  Requests: {s['total_requests']}")
            print(f"  Errors: {s['total_errors']}")


if __name__ == "__main__":
    asyncio.run(main())
