#!/usr/bin/env python3
"""
Fetch sales from December 15, 2025 to now.
Conservative rate: 1 request per 2 seconds.
"""

import asyncio
import json
import subprocess
import signal
import sys
import time
from datetime import datetime, timedelta

import psycopg2
import httpx

RPC = 'https://api.roninchain.com/rpc'
AXIE = '0x32950db2a7164ae833121501c797d79e7b79d74c'
WETH = '0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5'
WRON = '0xe514d9deb7966c8be0ca922de8a064264ea6bcd4'
TRANSFER = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
RATES = {'WETH': 3800.0, 'WRON': 0.15}
DELAY = 2.0

shutdown = False
def handle_sig(s, f):
    global shutdown
    print("\nShutting down...")
    shutdown = True
signal.signal(signal.SIGINT, handle_sig)


def get_db():
    r = subprocess.run(['aws', 'secretsmanager', 'get-secret-value',
        '--secret-id', 'axie-explorer/api-keys', '--query', 'SecretString',
        '--output', 'text', '--region', 'us-east-1'], capture_output=True, text=True)
    s = json.loads(r.stdout)
    conn = psycopg2.connect(
        host=s.get('RDS_HOST', 'cardforum.cn4c2su0o42n.us-east-1.rds.amazonaws.com'),
        port=5432, dbname='postgres', user='postgres',
        password=s.get('RDS_PASSWORD', '12345Cardforum'))
    cur = conn.cursor()
    cur.execute('SET search_path TO axie, public')
    conn.commit()
    return conn


async def rpc_call(client, method, params):
    await asyncio.sleep(DELAY)
    for _ in range(3):
        try:
            r = await client.post(RPC, json={'jsonrpc':'2.0','method':method,'params':params,'id':1}, timeout=30)
            if r.status_code == 429:
                wait = int(r.headers.get('Retry-After', 60))
                print(f"Rate limited, waiting {wait}s")
                await asyncio.sleep(wait)
                continue
            if r.status_code == 200:
                data = r.json()
                if 'error' not in data:
                    return data.get('result')
        except Exception as e:
            print(f"Error: {e}")
        await asyncio.sleep(5)
    return None


def parse_receipt(receipt):
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

        if addr == AXIE.lower() and len(topics) == 4:
            axies.append(int(topics[3], 16))
            seller = '0x' + topics[1][-40:]
            buyer = '0x' + topics[2][-40:]
        elif addr in (WETH.lower(), WRON.lower()) and len(topics) == 3:
            data = log.get('data', '0x')
            if data != '0x':
                val = int(data, 16) / 1e18
                tok = 'WETH' if addr == WETH.lower() else 'WRON'
                pays.append({'token': tok, 'value': val, 'usd': val * RATES[tok]})

    if not axies or not pays:
        return []

    best = max(pays, key=lambda p: p['usd'])
    ts = datetime(2025, 6, 1) + timedelta(seconds=(block - 45626000) * 3)

    return [{
        'tx': tx, 'axie': a, 'token_amt': best['value']/len(axies),
        'token': best['token'], 'usd': best['usd']/len(axies),
        'seller': seller, 'buyer': buyer, 'block': block, 'ts': ts
    } for a in axies]


def insert_sales(conn, sales):
    if not sales:
        return 0
    cur = conn.cursor()
    n = 0
    for s in sales:
        try:
            cur.execute('''
                INSERT INTO axie_sales (tx_hash, axie_id, price_token, token_type, price_usd,
                    eth_usd_rate, ron_usd_rate, seller, buyer, block_number, block_timestamp)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (tx_hash, axie_id) DO NOTHING
            ''', (s['tx'], s['axie'], s['token_amt'], s['token'], s['usd'],
                  RATES['WETH'], RATES['WRON'], s['seller'], s['buyer'], s['block'], s['ts']))
            if cur.rowcount > 0:
                n += 1
        except Exception as e:
            print(f"Insert error: {e}")
    conn.commit()
    return n


async def main():
    global shutdown

    conn = get_db()
    cur = conn.cursor()

    # Get last block in DB
    cur.execute('SELECT MAX(block_number) FROM axie_sales')
    last_block = cur.fetchone()[0] or 51315301

    print("=" * 50)
    print("AXIE SALES FETCHER - DEC 15 TO NOW")
    print("=" * 50)
    print(f"Starting from block: {last_block + 1:,}")

    async with httpx.AsyncClient(timeout=30) as client:
        result = await rpc_call(client, 'eth_blockNumber', [])
        if not result:
            print("Failed to get block number")
            return

        end_block = int(result, 16)
        start_block = last_block + 1
        total = end_block - start_block

        print(f"End block: {end_block:,}")
        print(f"Blocks to fetch: {total:,}")
        print(f"Estimated time: {total / 250 / 60:.0f} minutes")
        print()

        block = start_block
        total_sales = 0
        t0 = time.time()
        last_log = t0

        while block <= end_block and not shutdown:
            batch_end = min(block + 498, end_block)  # 499 blocks max

            logs = await rpc_call(client, 'eth_getLogs', [{
                'address': AXIE, 'topics': [TRANSFER],
                'fromBlock': hex(block), 'toBlock': hex(batch_end)
            }])

            if logs:
                txs = list(set(l['transactionHash'] for l in logs))

                for tx in txs:
                    if shutdown:
                        break

                    receipt = await rpc_call(client, 'eth_getTransactionReceipt', [tx])
                    if receipt:
                        sales = parse_receipt(receipt)
                        n = insert_sales(conn, sales)
                        total_sales += n

            block = batch_end + 1

            # Progress every 60 seconds
            now = time.time()
            if now - last_log >= 60:
                elapsed = now - t0
                done = block - start_block
                rate = done / elapsed if elapsed > 0 else 0
                pct = done / total * 100 if total > 0 else 0
                eta = (end_block - block) / rate / 60 if rate > 0 else 0

                print(f"[{pct:5.1f}%] Block {block:,} | Sales: {total_sales} | {rate:.1f} blk/s | ETA: {eta:.0f}m")
                last_log = now

        elapsed = time.time() - t0

        # Final count
        cur.execute('SELECT COUNT(*) FROM axie_sales')
        final_count = cur.fetchone()[0]

        print()
        print("=" * 50)
        print("COMPLETE" if not shutdown else "STOPPED")
        print(f"New sales inserted: {total_sales}")
        print(f"Total sales in DB: {final_count:,}")
        print(f"Time: {elapsed/60:.1f} minutes")

    conn.close()


if __name__ == '__main__':
    asyncio.run(main())
