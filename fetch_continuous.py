#!/usr/bin/env python3
"""
Continuous Axie Sales Fetcher - Parameterized for Pipeline

Fetches premium Axie sales (>2x floor) for a given block range.
Used by the Lambda orchestrator pipeline.

Usage:
    python3 fetch_continuous.py --job-id 1 --start-block 46461001 --end-block 47353800
"""

import json
import subprocess
import urllib.request
import psycopg2
import argparse
import sys
import time
import os
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(line_buffering=True)

# Configuration
FLOOR_MULT = 2.0
RATES = {'eth_usd': 3800.0, 'ron_usd': 0.15}
WORKERS = 5            # Conservative to share RPC with backfill job
BATCH_BLOCKS = 499
BATCH_DELAY = 1.5      # Longer delay to avoid rate limits on public RPC
PROGRESS_INTERVAL = 10  # batches between progress updates
SAVE_INTERVAL = 100     # batches between saves

# Contracts
TOKENS = {
    "0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5": ("WETH", 18),
    "0xe514d9deb7966c8be0ca922de8a064264ea6bcd4": ("WRON", 18),
}
AXIE = "0x32950db2a7164ae833121501c797d79e7b79d74c"
TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


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
        'api_key': secrets.get('SKYMAVIS_API_KEY', ''),
        'db': {
            'host': secrets.get('RDS_HOST', 'cardforum.cn4c2su0o42n.us-east-1.rds.amazonaws.com'),
            'port': 5432,
            'dbname': secrets.get('RDS_DATABASE', 'postgres'),
            'user': secrets.get('RDS_USER', 'postgres'),
            'password': secrets.get('RDS_PASSWORD', '***REMOVED-ROTATE-ME***')
        }
    }


config = get_config()
# Use public RPC to avoid rate limits (premium API shared with other jobs)
rpc_url = 'https://api.roninchain.com/rpc'
gql_url = 'https://api-gateway.skymavis.com/graphql/marketplace'
headers = {'X-API-Key': config['api_key'], 'Content-Type': 'application/json'}
rpc_headers = {'Content-Type': 'application/json'}  # Public RPC doesn't need API key


def rpc(method, params, retries=5):
    """Make RPC call with retries and rate limit handling."""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(rpc_url,
                data=json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode(),
                headers=rpc_headers, method='POST')
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read())
            if 'error' not in result:
                return result
        except urllib.error.HTTPError as e:
            if e.code == 429:  # Rate limited
                wait = (attempt + 1) * 5  # Longer backoff for public RPC
                print(f"[RATE LIMITED] Waiting {wait}s...")
                time.sleep(wait)
            else:
                time.sleep(1.0)
        except:
            time.sleep(1.0)
        if attempt < retries - 1:
            time.sleep(1.0 * (attempt + 1))
    return None


def gql(query):
    """Make GraphQL call."""
    try:
        req = urllib.request.Request(gql_url, data=json.dumps({"query": query}).encode(), headers=headers)
        return json.loads(urllib.request.urlopen(req, timeout=15).read())
    except:
        return None


def get_class(axie_id):
    """Get Axie class from GraphQL."""
    r = gql(f'{{ axie(axieId: "{axie_id}") {{ class }} }}')
    if r and r.get('data', {}).get('axie'):
        return r['data']['axie'].get('class')
    return None


def fetch_receipt(tx_hash):
    """Fetch receipt and extract sale info."""
    r = rpc("eth_getTransactionReceipt", [tx_hash])
    if not r or 'result' not in r or not r['result']:
        return None

    logs = r['result']['logs']
    axies, pays = [], []

    for log in logs:
        if not log.get('topics'):
            continue
        sig = log['topics'][0]

        if sig == TOPIC and log['address'].lower() == AXIE.lower() and len(log['topics']) >= 4:
            axies.append(int(log['topics'][3], 16))

        if sig == TOPIC and log['address'].lower() in TOKENS and len(log['topics']) == 3:
            if log.get('data') and log['data'] != '0x':
                tok, dec = TOKENS[log['address'].lower()]
                val = int(log['data'], 16) / 10**dec
                usd = val * RATES['eth_usd'] if tok == 'WETH' else val * RATES['ron_usd']
                pays.append((tok, val, usd))

    if not axies or not pays:
        return None

    best = max(pays, key=lambda x: x[2])
    return {'axies': axies, 'token': best[0], 'token_amount': best[1], 'usd': best[2]}


def update_job_progress(conn, job_id, current_block, sales_count, premium_count):
    """Update job progress in database."""
    try:
        cur = conn.cursor()
        cur.execute("SELECT axie.update_job_progress(%s, %s, %s, %s)",
                    (job_id, current_block, sales_count, premium_count))
        conn.commit()
        cur.close()
    except Exception as e:
        print(f"Warning: Could not update progress: {e}")


def complete_job(conn, job_id, sales_count, premium_count):
    """Mark job as completed."""
    try:
        cur = conn.cursor()
        cur.execute("SELECT axie.complete_job(%s, %s, %s)", (job_id, sales_count, premium_count))
        conn.commit()
        cur.close()
    except Exception as e:
        print(f"Warning: Could not complete job: {e}")


def main():
    parser = argparse.ArgumentParser(description='Fetch Axie sales for a block range')
    parser.add_argument('--job-id', type=int, required=True, help='Job ID from fetch_jobs table')
    parser.add_argument('--start-block', type=int, required=True, help='Start block number')
    parser.add_argument('--end-block', type=int, required=True, help='End block number')
    args = parser.parse_args()

    job_id = args.job_id
    start_block = args.start_block
    end_block = args.end_block

    print("=" * 60)
    print(f"CONTINUOUS FETCH - Job #{job_id}")
    print(f"Blocks: {start_block:,} - {end_block:,} ({end_block - start_block:,} total)")
    print(f"Workers: {WORKERS} | Batch: {BATCH_BLOCKS} blocks")
    print("=" * 60)

    conn = psycopg2.connect(**config['db'])

    # Phase 1: Collect all sales
    print("\n--- Phase 1: Collecting Sales ---")
    all_sales = []
    seen = set()
    current = start_block
    t0 = time.time()
    batches_done = 0
    total_batches = (end_block - start_block) // BATCH_BLOCKS + 1

    try:
        while current <= end_block:
            batch_end = min(current + BATCH_BLOCKS, end_block)

            # Get logs for batch
            logs = rpc("eth_getLogs", [{
                "address": AXIE, "topics": [TOPIC],
                "fromBlock": hex(current), "toBlock": hex(batch_end)
            }])

            if logs and 'result' in logs:
                new_txs = list(set(e['transactionHash'] for e in logs['result'] if e['transactionHash'] not in seen))

                # Parallel fetch receipts
                if new_txs:
                    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
                        futures = {executor.submit(fetch_receipt, tx): tx for tx in new_txs}
                        for future in as_completed(futures):
                            tx = futures[future]
                            seen.add(tx)
                            try:
                                r = future.result()
                                if r:
                                    per_axie = r['usd'] / len(r['axies'])
                                    per_axie_token = r['token_amount'] / len(r['axies'])
                                    for aid in r['axies']:
                                        all_sales.append({
                                            'axie_id': aid, 'price_usd': per_axie,
                                            'price_token': per_axie_token,
                                            'token': r['token'], 'block': current, 'tx': tx
                                        })
                            except:
                                pass

            batches_done += 1
            current = batch_end + 1

            # Rate limiting delay between batches
            time.sleep(BATCH_DELAY)

            # Progress update
            if batches_done % PROGRESS_INTERVAL == 0:
                elapsed = time.time() - t0
                pct = (current - start_block) / (end_block - start_block) * 100
                rate = batches_done * BATCH_BLOCKS / elapsed
                eta = (end_block - current) / rate / 3600 if rate > 0 else 0
                print(f"[{pct:5.1f}%] Block {current:,} | Sales: {len(all_sales):,} | {rate:.0f} blk/s | ETA: {eta:.1f}h")

            # Update job progress
            if batches_done % SAVE_INTERVAL == 0:
                update_job_progress(conn, job_id, current, len(all_sales), 0)

    except KeyboardInterrupt:
        print("\nInterrupted - saving progress...")
        update_job_progress(conn, job_id, current, len(all_sales), 0)
        conn.close()
        return

    elapsed = time.time() - t0
    print(f"\nPhase 1 Complete: {len(all_sales):,} sales in {elapsed/60:.1f} min")

    if not all_sales:
        print("No sales found!")
        complete_job(conn, job_id, 0, 0)
        conn.close()
        return

    # Phase 2: Get classes
    print("\n--- Phase 2: Fetching Axie Classes ---")
    unique = list(set(s['axie_id'] for s in all_sales))
    classes = {}

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(get_class, aid): aid for aid in unique}
        done = 0
        for future in as_completed(futures):
            aid = futures[future]
            classes[aid] = future.result()
            done += 1
            if done % 1000 == 0:
                print(f"  Classes: {done}/{len(unique)}")

    # Calculate floors
    class_prices = defaultdict(list)
    for s in all_sales:
        s['class'] = classes.get(s['axie_id'])
        if s['class']:
            class_prices[s['class']].append(s['price_usd'])

    floors = {c: min(p) for c, p in class_prices.items()}
    overall = min(s['price_usd'] for s in all_sales)

    print("\nFloor prices:")
    for c in sorted(floors):
        print(f"  {c:10}: ${floors[c]:>6.2f} ({len(class_prices[c]):>5} sales)")
    print(f"  {'Overall':10}: ${overall:>6.2f}")

    # Filter premium
    premium = []
    for s in all_sales:
        floor = floors.get(s['class'], overall)
        if s['price_usd'] > floor * FLOOR_MULT:
            s['floor'] = floor
            s['mult'] = s['price_usd'] / floor
            premium.append(s)

    print(f"\nPremium (>{FLOOR_MULT}x floor): {len(premium):,} / {len(all_sales):,} ({100*len(premium)/len(all_sales):.1f}%)")

    # Phase 3: Insert to DB
    print("\n--- Phase 3: Inserting to Database ---")
    cur = conn.cursor()
    cur.execute("SET search_path TO axie, public")

    inserted = 0
    for s in premium:
        try:
            # Estimate timestamp from block (3 sec/block from June 1)
            est_ts = datetime(2025, 6, 1) + __import__('datetime').timedelta(seconds=(s['block'] - 45626000) * 3)
            cur.execute("""
                INSERT INTO axie_sales (tx_hash, axie_id, class, price_token, token_type, price_usd,
                    eth_usd_rate, ron_usd_rate, block_number, block_timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tx_hash, axie_id, block_timestamp) DO NOTHING
            """, (s['tx'], s['axie_id'], s['class'], s['price_token'], s['token'],
                  s['price_usd'], RATES['eth_usd'], RATES['ron_usd'], s['block'], est_ts))
            if cur.rowcount > 0:
                inserted += 1
        except:
            pass

    conn.commit()

    # Queue metadata fetch
    print("Queuing metadata fetch...")
    for s in premium:
        try:
            cur.execute("SELECT queue_metadata_fetch(%s, %s::varchar, %s::smallint)",
                        (s['axie_id'], f'job_{job_id}', 5))
        except:
            pass
    conn.commit()
    cur.close()

    # Mark job complete
    complete_job(conn, job_id, len(all_sales), len(premium))
    conn.close()

    # Summary
    total_time = time.time() - t0
    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)
    print(f"Job ID: {job_id}")
    print(f"Blocks: {start_block:,} - {end_block:,}")
    print(f"Total sales: {len(all_sales):,}")
    print(f"Premium sales: {len(premium):,}")
    print(f"Inserted to DB: {inserted}")
    print(f"Total time: {total_time/60:.1f} minutes")

    if premium:
        prices = [s['price_usd'] for s in premium]
        print(f"\nPrice range: ${min(prices):.2f} - ${max(prices):.2f}")
        print(f"\nTop 10 premium sales:")
        for s in sorted(premium, key=lambda x: x['price_usd'], reverse=True)[:10]:
            print(f"  #{s['axie_id']:>8} | {s.get('class','?'):>8} | ${s['price_usd']:>9.2f}")


if __name__ == "__main__":
    main()
