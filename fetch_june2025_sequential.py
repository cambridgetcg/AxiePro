#!/usr/bin/env python3
"""
Fetch Axie sales from June 2025 - Sequential version with rate limiting.

Uses sequential requests to avoid Cloudflare rate limits.
Slower but more reliable for long-running fetches.
"""

import asyncio
import json
import logging
import subprocess
import signal
import sys
import os
import time
from datetime import datetime, timedelta
from typing import List, Optional

import psycopg2
import httpx

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('fetch_june2025.log')
    ]
)
logger = logging.getLogger(__name__)

# Disable httpx logging
logging.getLogger("httpx").setLevel(logging.WARNING)

# Configuration
RPC_URL = "https://api.roninchain.com/rpc"
AXIE_CONTRACT = "0x32950db2a7164ae833121501c797d79e7b79d74c"
WETH_CONTRACT = "0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5"
WRON_CONTRACT = "0xe514d9deb7966c8be0ca922de8a064264ea6bcd4"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

JUNE_2025_START = 45626000
JOB_ID = "june2025_to_present"
BATCH_SIZE = 499
REQUEST_DELAY = 0.3  # 300ms between requests
RATES = {'WETH': 3800.0, 'WRON': 0.15}

# Shutdown flag
shutdown_requested = False

def signal_handler(sig, frame):
    global shutdown_requested
    logger.info("Shutdown requested...")
    shutdown_requested = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def get_db_config():
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
        'dbname': 'postgres',
        'user': 'postgres',
        'password': secrets.get('RDS_PASSWORD', '12345Cardforum')
    }


async def rpc_call(client: httpx.AsyncClient, method: str, params: list, retries: int = 5):
    """Make RPC call with retry and backoff."""
    for attempt in range(retries):
        try:
            response = await client.post(
                RPC_URL,
                json={"jsonrpc": "2.0", "method": method, "params": params, "id": 1},
                timeout=30.0
            )

            if response.status_code == 429:
                wait = int(response.headers.get("Retry-After", 30))
                logger.warning(f"Rate limited, waiting {wait}s...")
                await asyncio.sleep(wait)
                continue

            if response.status_code == 200:
                data = response.json()
                if "error" not in data:
                    return data.get("result")

        except Exception as e:
            logger.warning(f"RPC error (attempt {attempt+1}): {e}")

        await asyncio.sleep(2 ** attempt)  # Exponential backoff

    return None


def parse_sales_from_receipt(receipt: dict) -> list:
    """Extract sales from receipt."""
    logs = receipt.get("logs", [])
    if len(logs) < 2:
        return []

    tx_hash = receipt.get("transactionHash", "")
    block_number = int(receipt.get("blockNumber", "0x0"), 16)

    axie_transfers = []
    payments = []
    seller = buyer = None

    for log in logs:
        topics = log.get("topics", [])
        if not topics or topics[0] != TRANSFER_TOPIC:
            continue

        address = log.get("address", "").lower()

        # Axie NFT transfer
        if address == AXIE_CONTRACT.lower() and len(topics) == 4:
            axie_transfers.append(int(topics[3], 16))
            seller = "0x" + topics[1][-40:]
            buyer = "0x" + topics[2][-40:]

        # Token payment
        elif address in (WETH_CONTRACT.lower(), WRON_CONTRACT.lower()) and len(topics) == 3:
            data = log.get("data", "0x")
            if data and data != "0x":
                value = int(data, 16) / 10**18
                token = "WETH" if address == WETH_CONTRACT.lower() else "WRON"
                usd = value * RATES.get(token, 0)
                payments.append({"token": token, "value": value, "usd": usd})

    if not axie_transfers or not payments:
        return []

    best = max(payments, key=lambda p: p["usd"])
    per_axie = best["value"] / len(axie_transfers)
    per_usd = best["usd"] / len(axie_transfers)

    # Estimate timestamp
    ref_block = 45626000
    ref_time = datetime(2025, 6, 1)
    block_diff = block_number - ref_block
    timestamp = ref_time + timedelta(seconds=block_diff * 3)

    return [
        {
            "tx_hash": tx_hash,
            "axie_id": axie_id,
            "price_token": per_axie,
            "token_type": best["token"],
            "price_usd": per_usd,
            "seller": seller,
            "buyer": buyer,
            "block_number": block_number,
            "block_timestamp": timestamp
        }
        for axie_id in axie_transfers
    ]


def save_checkpoint(conn, block: int, records: int, rate: float):
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
    """, (JOB_ID, block, records, rate))
    conn.commit()
    cur.close()


def get_checkpoint(conn):
    cur = conn.cursor()
    cur.execute("SET search_path TO axie, public")
    cur.execute("SELECT last_block, records_synced FROM sync_state WHERE id = %s", (JOB_ID,))
    row = cur.fetchone()
    cur.close()
    return (row[0], row[1]) if row and row[0] else (None, 0)


def insert_sales(conn, sales: list) -> int:
    if not sales:
        return 0

    cur = conn.cursor()
    cur.execute("SET search_path TO axie, public")

    inserted = 0
    for s in sales:
        try:
            cur.execute("""
                INSERT INTO axie_sales (
                    tx_hash, axie_id, price_token, token_type, price_usd,
                    eth_usd_rate, ron_usd_rate, seller, buyer,
                    block_number, block_timestamp
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tx_hash, axie_id) DO NOTHING
            """, (
                s["tx_hash"], s["axie_id"], s["price_token"], s["token_type"],
                s["price_usd"], RATES['WETH'], RATES['WRON'],
                s["seller"], s["buyer"], s["block_number"], s["block_timestamp"]
            ))
            if cur.rowcount > 0:
                inserted += 1
        except Exception as e:
            pass

    conn.commit()
    cur.close()
    return inserted


async def main():
    global shutdown_requested

    db_config = get_db_config()
    conn = psycopg2.connect(**db_config)

    # Get checkpoint
    last_block, total_records = get_checkpoint(conn)
    start_block = (last_block + 1) if last_block else JUNE_2025_START

    logger.info("=" * 60)
    logger.info("AXIE SALES FETCHER - SEQUENTIAL MODE")
    logger.info("=" * 60)

    async with httpx.AsyncClient() as client:
        # Get current block
        current = await rpc_call(client, "eth_blockNumber", [])
        end_block = int(current, 16)

        total_blocks = end_block - start_block
        logger.info(f"Start block: {start_block:,}" + (f" (resumed)" if last_block else ""))
        logger.info(f"End block: {end_block:,}")
        logger.info(f"Blocks to process: {total_blocks:,}")
        logger.info(f"Previous records: {total_records:,}")
        logger.info("")

        t0 = time.time()
        current_block = start_block
        batch_sales = 0
        total_sales = total_records
        last_log = t0

        while current_block <= end_block and not shutdown_requested:
            batch_end = min(current_block + BATCH_SIZE - 1, end_block)

            # Get logs
            logs = await rpc_call(client, "eth_getLogs", [{
                "address": AXIE_CONTRACT,
                "topics": [TRANSFER_TOPIC],
                "fromBlock": hex(current_block),
                "toBlock": hex(batch_end)
            }])

            await asyncio.sleep(REQUEST_DELAY)

            if logs:
                # Get unique TX hashes
                tx_hashes = list(set(log["transactionHash"] for log in logs))

                # Fetch receipts sequentially
                for tx_hash in tx_hashes:
                    if shutdown_requested:
                        break

                    receipt = await rpc_call(client, "eth_getTransactionReceipt", [tx_hash])
                    await asyncio.sleep(REQUEST_DELAY)

                    if receipt:
                        sales = parse_sales_from_receipt(receipt)
                        if sales:
                            inserted = insert_sales(conn, sales)
                            batch_sales += inserted
                            total_sales += inserted

            current_block = batch_end + 1

            # Progress logging every 30 seconds
            now = time.time()
            if now - last_log >= 30:
                elapsed = now - t0
                blocks_done = current_block - start_block
                rate = blocks_done / elapsed if elapsed > 0 else 0
                pct = blocks_done / total_blocks * 100 if total_blocks > 0 else 0
                eta = (end_block - current_block) / rate / 3600 if rate > 0 else 0

                logger.info(f"[{pct:5.1f}%] Block {current_block:,} | "
                           f"Sales: {total_sales:,} (+{batch_sales}) | "
                           f"{rate:.0f} blk/s | ETA: {eta:.1f}h")

                # Save checkpoint
                save_checkpoint(conn, current_block - 1, total_sales, rate)
                batch_sales = 0
                last_log = now

        # Final checkpoint
        elapsed = time.time() - t0
        rate = (current_block - start_block) / elapsed if elapsed > 0 else 0
        save_checkpoint(conn, current_block - 1, total_sales, rate)

        logger.info("")
        logger.info("=" * 60)
        logger.info("COMPLETE" if not shutdown_requested else "INTERRUPTED")
        logger.info("=" * 60)
        logger.info(f"Blocks processed: {current_block - start_block:,}")
        logger.info(f"Total sales: {total_sales:,}")
        logger.info(f"Time: {elapsed/3600:.2f} hours")
        logger.info(f"Speed: {rate:.0f} blk/s")

    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
