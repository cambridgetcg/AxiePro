#!/usr/bin/env python3
"""
Fetch Axie sales with automatic rate limit recovery.
Waits for rate limits to clear, then fetches slowly.
"""

import asyncio
import json
import logging
import subprocess
import signal
import sys
import time
from datetime import datetime, timedelta

import psycopg2
import httpx

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s', datefmt='%H:%M:%S')
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

RPC_URL = "https://api.roninchain.com/rpc"
AXIE = "0x32950db2a7164ae833121501c797d79e7b79d74c"
WETH = "0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5"
WRON = "0xe514d9deb7966c8be0ca922de8a064264ea6bcd4"
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
RATES = {'WETH': 3800.0, 'WRON': 0.15}

JOB_ID = "dec2025_update"

shutdown = False
def handle_signal(s, f):
    global shutdown
    shutdown = True
    logger.info("Shutdown requested")
signal.signal(signal.SIGINT, handle_signal)


def get_db():
    r = subprocess.run(['aws', 'secretsmanager', 'get-secret-value',
        '--secret-id', 'axie-explorer/api-keys', '--query', 'SecretString',
        '--output', 'text', '--region', 'us-east-1'], capture_output=True, text=True)
    s = json.loads(r.stdout)
    return psycopg2.connect(
        host=s.get('RDS_HOST', 'cardforum.cn4c2su0o42n.us-east-1.rds.amazonaws.com'),
        port=5432, dbname='postgres', user='postgres',
        password=s.get('RDS_PASSWORD', '***REMOVED-ROTATE-ME***'))


async def wait_for_rpc(client):
    """Wait until RPC is accessible."""
    logger.info("Waiting for RPC rate limit to clear...")
    while not shutdown:
        try:
            r = await client.post(RPC_URL,
                json={'jsonrpc':'2.0','method':'eth_blockNumber','params':[],'id':1},
                timeout=30)
            if r.status_code == 200 and 'result' in r.json():
                block = int(r.json()['result'], 16)
                logger.info(f"RPC accessible! Block: {block:,}")
                return block
            if r.status_code == 429:
                wait = int(r.headers.get('Retry-After', 60))
                logger.info(f"Rate limited. Waiting {wait}s...")
                await asyncio.sleep(wait)
        except Exception as e:
            logger.warning(f"Connection error: {e}")
            await asyncio.sleep(30)
    return None


async def rpc(client, method, params):
    """RPC call with 2-second delay to be very conservative."""
    await asyncio.sleep(2)  # Always wait 2 seconds between requests
    for attempt in range(5):
        try:
            r = await client.post(RPC_URL,
                json={"jsonrpc":"2.0","method":method,"params":params,"id":1},
                timeout=30)
            if r.status_code == 200:
                data = r.json()
                if 'error' not in data:
                    return data.get('result')
            if r.status_code == 429:
                wait = int(r.headers.get('Retry-After', 60))
                logger.warning(f"Rate limited during request. Waiting {wait}s...")
                await asyncio.sleep(wait)
                continue
        except Exception as e:
            logger.warning(f"Request error: {e}")
        await asyncio.sleep(10)
    return None


def parse_receipt(receipt):
    logs = receipt.get("logs", [])
    if len(logs) < 2:
        return []

    tx = receipt.get("transactionHash", "")
    block = int(receipt.get("blockNumber", "0x0"), 16)
    axies, pays = [], []
    seller = buyer = None

    for log in logs:
        topics = log.get("topics", [])
        if not topics or topics[0] != TRANSFER:
            continue
        addr = log.get("address", "").lower()

        if addr == AXIE.lower() and len(topics) == 4:
            axies.append(int(topics[3], 16))
            seller = "0x" + topics[1][-40:]
            buyer = "0x" + topics[2][-40:]
        elif addr in (WETH.lower(), WRON.lower()) and len(topics) == 3:
            data = log.get("data", "0x")
            if data != "0x":
                val = int(data, 16) / 1e18
                tok = "WETH" if addr == WETH.lower() else "WRON"
                pays.append({"token": tok, "value": val, "usd": val * RATES[tok]})

    if not axies or not pays:
        return []

    best = max(pays, key=lambda p: p["usd"])
    ts = datetime(2025, 6, 1) + timedelta(seconds=(block - 45626000) * 3)

    return [{
        "tx": tx, "axie": a, "token_amt": best["value"]/len(axies),
        "token": best["token"], "usd": best["usd"]/len(axies),
        "seller": seller, "buyer": buyer, "block": block, "ts": ts
    } for a in axies]


def save_sales(conn, sales):
    if not sales:
        return 0
    cur = conn.cursor()
    cur.execute("SET search_path TO axie, public")
    n = 0
    for s in sales:
        try:
            cur.execute("""
                INSERT INTO axie_sales (tx_hash, axie_id, price_token, token_type, price_usd,
                    eth_usd_rate, ron_usd_rate, seller, buyer, block_number, block_timestamp)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (tx_hash, axie_id) DO NOTHING
            """, (s["tx"], s["axie"], s["token_amt"], s["token"], s["usd"],
                  RATES['WETH'], RATES['WRON'], s["seller"], s["buyer"], s["block"], s["ts"]))
            if cur.rowcount > 0:
                n += 1
        except:
            pass
    conn.commit()
    cur.close()
    return n


def checkpoint(conn, block, sales, rate):
    cur = conn.cursor()
    cur.execute("SET search_path TO axie, public")
    cur.execute("""
        INSERT INTO sync_state (id, last_block, last_timestamp, records_synced, processing_rate, updated_at)
        VALUES (%s, %s, NOW(), %s, %s, NOW())
        ON CONFLICT (id) DO UPDATE SET last_block=EXCLUDED.last_block, last_timestamp=NOW(),
            records_synced=EXCLUDED.records_synced, processing_rate=EXCLUDED.processing_rate, updated_at=NOW()
    """, (JOB_ID, block, sales, rate))
    conn.commit()
    cur.close()


async def main():
    conn = get_db()

    # Get last block from database
    cur = conn.cursor()
    cur.execute("SET search_path TO axie, public")
    cur.execute("SELECT MAX(block_number) FROM axie_sales")
    last_db_block = cur.fetchone()[0] or 51315000  # Dec 15 approximate
    cur.close()

    logger.info("=" * 50)
    logger.info("AXIE SALES FETCHER - WITH RATE LIMIT RECOVERY")
    logger.info("=" * 50)
    logger.info(f"Last DB block: {last_db_block:,}")

    async with httpx.AsyncClient(timeout=30) as client:
        # Wait for RPC to be accessible
        end_block = await wait_for_rpc(client)
        if not end_block or shutdown:
            logger.info("Aborted")
            conn.close()
            return

        start_block = last_db_block + 1
        total = end_block - start_block

        logger.info(f"Fetching: {start_block:,} - {end_block:,} ({total:,} blocks)")
        logger.info("Using 2-second delay between requests (very conservative)")
        logger.info("")

        t0 = time.time()
        block = start_block
        sales = 0
        last_log = t0

        while block <= end_block and not shutdown:
            batch_end = min(block + 499, end_block)

            logs = await rpc(client, "eth_getLogs", [{
                "address": AXIE, "topics": [TRANSFER],
                "fromBlock": hex(block), "toBlock": hex(batch_end)
            }])

            if logs:
                txs = list(set(l["transactionHash"] for l in logs))
                for tx in txs:
                    if shutdown:
                        break
                    receipt = await rpc(client, "eth_getTransactionReceipt", [tx])
                    if receipt:
                        parsed = parse_receipt(receipt)
                        n = save_sales(conn, parsed)
                        sales += n

            block = batch_end + 1

            now = time.time()
            if now - last_log >= 60:
                elapsed = now - t0
                done = block - start_block
                rate = done / elapsed if elapsed > 0 else 0
                pct = done / total * 100 if total > 0 else 0
                eta = (end_block - block) / rate / 3600 if rate > 0 else 0

                logger.info(f"[{pct:5.1f}%] Block {block:,} | New sales: {sales} | {rate:.1f} blk/s | ETA: {eta:.1f}h")
                checkpoint(conn, block, sales, rate)
                last_log = now

        elapsed = time.time() - t0
        checkpoint(conn, block, sales, (block-start_block)/elapsed if elapsed > 0 else 0)

        logger.info("")
        logger.info("=" * 50)
        logger.info("DONE" if not shutdown else "STOPPED")
        logger.info(f"New sales inserted: {sales}")

    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
