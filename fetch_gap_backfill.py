#!/usr/bin/env python3
"""
Fetch Axie sales for the missing gap (June 6 - December 15, 2025).

Uses correct ON CONFLICT clause with block_timestamp to match partitioned table constraint.
Conservative rate limiting to avoid 429 errors.

Usage:
    python3 fetch_gap_backfill.py                    # Start from gap beginning
    python3 fetch_gap_backfill.py --resume           # Resume from checkpoint
    python3 fetch_gap_backfill.py --test             # Test with 1000 blocks
"""

import asyncio
import argparse
import json
import subprocess
import signal
import sys
import time
from datetime import datetime, timedelta

import psycopg2
import httpx

# Configuration
RPC = 'https://api.roninchain.com/rpc'
AXIE = '0x32950db2a7164ae833121501c797d79e7b79d74c'
WETH = '0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5'
WRON = '0xe514d9deb7966c8be0ca922de8a064264ea6bcd4'
TRANSFER = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
RATES = {'WETH': 3800.0, 'WRON': 0.15}

# Gap definition (from analysis)
GAP_START_BLOCK = 45765001  # First missing block (June 6, 2025)
GAP_END_BLOCK = 51313844    # Last missing block (Dec 15, 2025)

# Rate limiting - conservative to avoid 429s
DELAY_LOGS = 1.0      # Delay after getLogs call
DELAY_RECEIPT = 0.5   # Delay after getReceipt call
BATCH_SIZE = 499      # Max blocks per getLogs call

# Progress
CHECKPOINT_INTERVAL = 10000  # Save checkpoint every N blocks
PROGRESS_INTERVAL = 60       # Log progress every N seconds
JOB_ID = 'gap_backfill'

shutdown = False

def handle_sig(s, f):
    global shutdown
    print("\n[CTRL+C] Graceful shutdown requested...")
    shutdown = True

signal.signal(signal.SIGINT, handle_sig)
signal.signal(signal.SIGTERM, handle_sig)


def get_db():
    """Get database connection."""
    r = subprocess.run(
        ['aws', 'secretsmanager', 'get-secret-value',
         '--secret-id', 'axie-explorer/api-keys', '--query', 'SecretString',
         '--output', 'text', '--region', 'us-east-1'],
        capture_output=True, text=True
    )
    s = json.loads(r.stdout)
    conn = psycopg2.connect(
        host=s.get('RDS_HOST', 'cardforum.cn4c2su0o42n.us-east-1.rds.amazonaws.com'),
        port=5432, dbname='postgres', user='postgres',
        password=s.get('RDS_PASSWORD', '12345Cardforum')
    )
    cur = conn.cursor()
    cur.execute('SET search_path TO axie, public')
    conn.commit()
    return conn


def get_checkpoint(conn):
    """Get last checkpoint block."""
    cur = conn.cursor()
    cur.execute("SELECT last_block FROM sync_state WHERE id = %s", (JOB_ID,))
    row = cur.fetchone()
    return row[0] if row else None


def save_checkpoint(conn, block, sales_count, rate):
    """Save checkpoint to database."""
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO sync_state (id, last_block, last_timestamp, records_synced, processing_rate, updated_at)
        VALUES (%s, %s, NOW(), %s, %s, NOW())
        ON CONFLICT (id) DO UPDATE SET
            last_block = EXCLUDED.last_block,
            last_timestamp = NOW(),
            records_synced = sync_state.records_synced + EXCLUDED.records_synced,
            processing_rate = EXCLUDED.processing_rate,
            updated_at = NOW()
    """, (JOB_ID, block, sales_count, rate))
    conn.commit()


async def rpc_call(client, method, params, delay=1.0):
    """Make RPC call with retry and rate limiting."""
    await asyncio.sleep(delay)

    for attempt in range(5):
        try:
            r = await client.post(
                RPC,
                json={'jsonrpc': '2.0', 'method': method, 'params': params, 'id': 1},
                timeout=30
            )

            if r.status_code == 429:
                wait = int(r.headers.get('Retry-After', 60))
                print(f"[RATE LIMITED] Waiting {wait}s...")
                await asyncio.sleep(wait)
                continue

            if r.status_code == 200:
                data = r.json()
                if 'error' not in data:
                    return data.get('result')
                else:
                    print(f"[RPC ERROR] {data.get('error', {}).get('message', 'Unknown')}")

        except Exception as e:
            print(f"[REQUEST ERROR] {e}")

        await asyncio.sleep(5 * (attempt + 1))

    return None


def parse_receipt(receipt):
    """Parse sale data from transaction receipt."""
    logs = receipt.get('logs', [])
    if len(logs) < 2:
        return []

    tx = receipt.get('transactionHash', '')
    block = int(receipt.get('blockNumber', '0x0'), 16)
    axies, pays = [], []
    seller = buyer = None

    for log in logs:
        topics = log.get('topics', [])
        if not topics or topics[0] != TRANSFER:
            continue
        addr = log.get('address', '').lower()

        # Axie NFT transfer
        if addr == AXIE.lower() and len(topics) == 4:
            axies.append(int(topics[3], 16))
            seller = '0x' + topics[1][-40:]
            buyer = '0x' + topics[2][-40:]

        # Token payment
        elif addr in (WETH.lower(), WRON.lower()) and len(topics) == 3:
            data = log.get('data', '0x')
            if data != '0x':
                val = int(data, 16) / 1e18
                tok = 'WETH' if addr == WETH.lower() else 'WRON'
                pays.append({'token': tok, 'value': val, 'usd': val * RATES[tok]})

    if not axies or not pays:
        return []

    best = max(pays, key=lambda p: p['usd'])
    # Estimate timestamp: Block 45626000 = June 1, 2025, 3 sec/block
    ts = datetime(2025, 6, 1) + timedelta(seconds=(block - 45626000) * 3)

    return [{
        'tx': tx, 'axie': a, 'token_amt': best['value'] / len(axies),
        'token': best['token'], 'usd': best['usd'] / len(axies),
        'seller': seller, 'buyer': buyer, 'block': block, 'ts': ts
    } for a in axies]


def insert_sales(conn, sales):
    """Insert sales with correct ON CONFLICT clause for partitioned table."""
    if not sales:
        return 0

    cur = conn.cursor()
    inserted = 0

    for s in sales:
        try:
            # Use correct constraint that includes block_timestamp (partition key)
            cur.execute('''
                INSERT INTO axie_sales (
                    tx_hash, axie_id, price_token, token_type, price_usd,
                    eth_usd_rate, ron_usd_rate, seller, buyer, block_number, block_timestamp
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tx_hash, axie_id, block_timestamp) DO NOTHING
            ''', (
                s['tx'], s['axie'], s['token_amt'], s['token'], s['usd'],
                RATES['WETH'], RATES['WRON'], s['seller'], s['buyer'], s['block'], s['ts']
            ))

            if cur.rowcount > 0:
                inserted += 1

        except Exception as e:
            # Rollback just this statement, not the whole transaction
            conn.rollback()
            cur.execute('SET search_path TO axie, public')
            print(f"[INSERT ERROR] {s['tx'][:20]}... : {e}")

    conn.commit()
    return inserted


async def main():
    global shutdown

    parser = argparse.ArgumentParser(description='Backfill missing Axie sales data')
    parser.add_argument('--resume', action='store_true', help='Resume from last checkpoint')
    parser.add_argument('--test', action='store_true', help='Test mode - process 1000 blocks only')
    parser.add_argument('--start-block', type=int, help='Override start block')
    parser.add_argument('--end-block', type=int, help='Override end block')
    args = parser.parse_args()

    conn = get_db()

    # Determine start block
    if args.start_block:
        start_block = args.start_block
    elif args.resume:
        checkpoint = get_checkpoint(conn)
        if checkpoint:
            start_block = checkpoint + 1
            print(f"Resuming from checkpoint: block {start_block:,}")
        else:
            start_block = GAP_START_BLOCK
    else:
        start_block = GAP_START_BLOCK

    # Determine end block
    if args.end_block:
        end_block = args.end_block
    elif args.test:
        end_block = min(start_block + 999, GAP_END_BLOCK)
    else:
        end_block = GAP_END_BLOCK

    total_blocks = end_block - start_block + 1

    print("=" * 60)
    print("AXIE SALES GAP BACKFILL")
    print("=" * 60)
    print(f"Block range: {start_block:,} - {end_block:,}")
    print(f"Total blocks: {total_blocks:,}")
    print(f"Estimated time: {total_blocks / 250 / 60:.1f} hours @ 250 blk/min")
    print(f"Mode: {'TEST' if args.test else 'FULL'}")
    print("=" * 60)
    print()

    async with httpx.AsyncClient(timeout=30) as client:
        block = start_block
        total_sales = 0
        chunk_sales = 0
        t0 = time.time()
        last_log = t0
        last_checkpoint = start_block

        while block <= end_block and not shutdown:
            batch_end = min(block + BATCH_SIZE - 1, end_block)

            # Fetch logs for this batch
            logs = await rpc_call(
                client, 'eth_getLogs',
                [{'address': AXIE, 'topics': [TRANSFER],
                  'fromBlock': hex(block), 'toBlock': hex(batch_end)}],
                delay=DELAY_LOGS
            )

            if logs:
                # Get unique transactions
                txs = list(set(l['transactionHash'] for l in logs))

                for tx in txs:
                    if shutdown:
                        break

                    receipt = await rpc_call(
                        client, 'eth_getTransactionReceipt', [tx],
                        delay=DELAY_RECEIPT
                    )

                    if receipt:
                        sales = parse_receipt(receipt)
                        n = insert_sales(conn, sales)
                        total_sales += n
                        chunk_sales += n

            block = batch_end + 1

            # Progress logging
            now = time.time()
            if now - last_log >= PROGRESS_INTERVAL:
                elapsed = now - t0
                done = block - start_block
                rate = done / elapsed if elapsed > 0 else 0
                pct = done / total_blocks * 100
                eta_hours = (end_block - block + 1) / rate / 3600 if rate > 0 else 0

                print(f"[{pct:5.1f}%] Block {block:,} | Sales: {total_sales:,} | "
                      f"{rate:.1f} blk/s | ETA: {eta_hours:.1f}h")
                last_log = now

            # Checkpoint
            if block - last_checkpoint >= CHECKPOINT_INTERVAL:
                elapsed = time.time() - t0
                rate = (block - start_block) / elapsed if elapsed > 0 else 0
                save_checkpoint(conn, block - 1, chunk_sales, rate)
                print(f"[CHECKPOINT] Saved at block {block - 1:,} ({chunk_sales} sales)")
                last_checkpoint = block
                chunk_sales = 0

        # Final checkpoint
        elapsed = time.time() - t0
        rate = (block - start_block) / elapsed if elapsed > 0 else 0
        save_checkpoint(conn, block - 1, chunk_sales, rate)

        # Summary
        print()
        print("=" * 60)
        print("COMPLETE" if not shutdown else "INTERRUPTED")
        print("=" * 60)
        print(f"Blocks processed: {block - start_block:,}")
        print(f"Sales inserted: {total_sales:,}")
        print(f"Time: {elapsed/3600:.2f} hours")
        print(f"Avg rate: {(block - start_block) / elapsed:.1f} blk/s")

        if not shutdown:
            # Get final count
            cur = conn.cursor()
            cur.execute('SELECT COUNT(*) FROM axie_sales')
            final_count = cur.fetchone()[0]
            print(f"Total sales in DB: {final_count:,}")

    conn.close()


if __name__ == '__main__':
    asyncio.run(main())
