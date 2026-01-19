#!/usr/bin/env python3
"""
Fetch premium Axie sales from June 2025 - PARALLEL VERSION
Uses 500-block batches (API limit) with parallel receipt fetching

Rate limit: ~100 req/s safe
Estimated time: ~2-3 hours
"""

import json
import subprocess
import urllib.request
import psycopg2
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import os
import sys

sys.stdout.reconfigure(line_buffering=True)

# Get API key
result = subprocess.run(['aws', 'secretsmanager', 'get-secret-value', '--secret-id', 'axie-explorer/api-keys', '--query', 'SecretString', '--output', 'text'], capture_output=True, text=True)
secrets = json.loads(result.stdout)
api_key = secrets.get('SKYMAVIS_API_KEY', '')

rpc_url = 'https://api-gateway.skymavis.com/rpc'
gql_url = 'https://api-gateway.skymavis.com/graphql/marketplace'
headers = {'X-API-Key': api_key, 'Content-Type': 'application/json'}

DB_CONFIG = {
    'host': 'cardforum.cn4c2su0o42n.us-east-1.rds.amazonaws.com',
    'port': 5432, 'dbname': 'postgres', 'user': 'postgres', 'password': '12345Cardforum'
}

TOKENS = {
    "0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5": ("WETH", 18),
    "0xe514d9deb7966c8be0ca922de8a064264ea6bcd4": ("WRON", 18),
}
AXIE = "0x32950db2a7164ae833121501c797d79e7b79d74c"
TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

START_BLOCK = 45_626_000
END_BLOCK = 46_461_000
FLOOR_MULT = 2.0
RATES = {'eth_usd': 3800.0, 'ron_usd': 0.15}
WORKERS = 15
BATCH_BLOCKS = 499  # API limit is 500
PROGRESS_FILE = 'june2025_parallel_progress.json'


def rpc(method, params, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(rpc_url,
                data=json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode(),
                headers=headers, method='POST')
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read())
            if 'error' not in result:
                return result
        except:
            pass
        if attempt < retries - 1:
            time.sleep(0.3 * (attempt + 1))
    return None


def gql(query):
    try:
        req = urllib.request.Request(gql_url, data=json.dumps({"query": query}).encode(), headers=headers)
        return json.loads(urllib.request.urlopen(req, timeout=15).read())
    except:
        return None


def get_class(axie_id):
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
                pays.append((tok, usd))

    if not axies or not pays:
        return None

    best = max(pays, key=lambda x: x[1])
    return {'axies': axies, 'token': best[0], 'usd': best[1]}


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {'block': START_BLOCK, 'sales': [], 'seen': []}


def save_progress(block, sales, seen):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump({'block': block, 'sales': sales[-30000:], 'seen': list(seen)[-100000:]}, f)


def main():
    print("=" * 60)
    print("JUNE 2025 PREMIUM SALES - PARALLEL FETCH")
    print(f"Blocks: {START_BLOCK:,} - {END_BLOCK:,} ({END_BLOCK-START_BLOCK:,} total)")
    print(f"Workers: {WORKERS} | Batch: {BATCH_BLOCKS} blocks")
    print("=" * 60)

    progress = load_progress()
    current = progress['block']
    all_sales = progress['sales']
    seen = set(progress['seen'])

    if current > START_BLOCK:
        print(f"Resuming from block {current:,} ({len(all_sales)} sales)")

    t0 = time.time()
    batches_done = 0
    total_batches = (END_BLOCK - START_BLOCK) // BATCH_BLOCKS

    try:
        while current <= END_BLOCK:
            batch_t0 = time.time()
            end = min(current + BATCH_BLOCKS, END_BLOCK)

            # Get logs for this 500-block batch
            logs = rpc("eth_getLogs", [{
                "address": AXIE, "topics": [TOPIC],
                "fromBlock": hex(current), "toBlock": hex(end)
            }])

            if not logs or 'result' not in logs:
                current = end + 1
                continue

            # Unique transactions not yet seen
            new_txs = list(set(e['transactionHash'] for e in logs['result'] if e['transactionHash'] not in seen))

            # Parallel fetch receipts
            batch_sales = []
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
                                for aid in r['axies']:
                                    batch_sales.append({
                                        'axie_id': aid, 'price_usd': per_axie,
                                        'token': r['token'], 'block': current, 'tx': tx
                                    })
                        except:
                            pass

            all_sales.extend(batch_sales)
            batches_done += 1
            current = end + 1

            # Progress every 10 batches (~5000 blocks)
            if batches_done % 10 == 0:
                elapsed = time.time() - t0
                pct = (current - START_BLOCK) / (END_BLOCK - START_BLOCK) * 100
                rate = batches_done * BATCH_BLOCKS / elapsed
                eta = (END_BLOCK - current) / rate / 3600 if rate > 0 else 0
                print(f"[{pct:5.1f}%] Block {current:,} | Sales: {len(all_sales):,} | {rate:.0f} blk/s | ETA: {eta:.1f}h")

            # Save every 100 batches (~50k blocks)
            if batches_done % 100 == 0:
                save_progress(current, all_sales, seen)

    except KeyboardInterrupt:
        print("\nInterrupted - saving...")
        save_progress(current, all_sales, seen)
        print(f"Saved at block {current:,} with {len(all_sales)} sales")
        return

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"Phase 1 Complete: {len(all_sales):,} sales in {elapsed/60:.1f} min")
    print(f"{'='*60}")

    if not all_sales:
        print("No sales found!")
        return

    # Phase 2: Classes
    print("\n--- Phase 2: Fetching Axie classes ---")
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
    print("\n--- Phase 3: Inserting to database ---")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SET search_path TO axie, public")

    inserted = 0
    for s in premium:
        try:
            # Use block number to estimate timestamp (3 sec/block)
            est_ts = datetime(2025, 6, 1) + (s['block'] - START_BLOCK) * 3 / 86400 * __import__('datetime').timedelta(days=1)
            cur.execute("""
                INSERT INTO axie_sales (tx_hash, axie_id, class, price_token, token_type, price_usd,
                    eth_usd_rate, ron_usd_rate, block_number, block_timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tx_hash, axie_id, block_timestamp) DO NOTHING
            """, (s['tx'], s['axie_id'], s['class'], s['price_usd']/RATES['eth_usd'], s['token'],
                  s['price_usd'], RATES['eth_usd'], RATES['ron_usd'], s['block'], est_ts))
            if cur.rowcount > 0:
                inserted += 1
        except Exception as e:
            pass

    conn.commit()

    # Queue metadata
    for s in premium:
        try:
            cur.execute("SELECT queue_metadata_fetch(%s, %s, %s)", (s['axie_id'], 'june2025_premium', 5))
        except:
            pass
    conn.commit()
    cur.close()
    conn.close()

    # Summary
    total_time = time.time() - t0
    print(f"\n{'='*60}")
    print("COMPLETE")
    print(f"{'='*60}")
    print(f"Total sales found: {len(all_sales):,}")
    print(f"Premium sales (>{FLOOR_MULT}x): {len(premium):,}")
    print(f"Inserted to DB: {inserted}")
    print(f"Total time: {total_time/60:.1f} minutes ({total_time/3600:.2f} hours)")

    if premium:
        prices = [s['price_usd'] for s in premium]
        print(f"\nPrice range: ${min(prices):.2f} - ${max(prices):.2f}")
        print(f"\nTop 20 premium sales:")
        for s in sorted(premium, key=lambda x: x['price_usd'], reverse=True)[:20]:
            print(f"  #{s['axie_id']:>8} | {s.get('class','?'):>8} | ${s['price_usd']:>9.2f} | {s.get('mult',0):.1f}x floor")

    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)


if __name__ == "__main__":
    main()
