#!/usr/bin/env python3
"""
Fetch premium Axie sales from June 2025 (>2x floor).
Optimized for speed with progress saving.

Run: python3 fetch_june2025_premium.py
Progress saved to: june2025_progress.json
"""

import json
import subprocess
import urllib.request
import psycopg2
from datetime import datetime
from collections import defaultdict
import time
import os
import sys

# Unbuffered output
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
    'port': 5432,
    'dbname': 'postgres',
    'user': 'postgres',
    'password': '***REMOVED-ROTATE-ME***'
}

TOKENS = {
    "0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5": ("WETH", 18),
    "0xe514d9deb7966c8be0ca922de8a064264ea6bcd4": ("WRON", 18),
}
AXIE_CONTRACT = "0x32950db2a7164ae833121501c797d79e7b79d74c"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

# June 2025 blocks
START_BLOCK = 45_626_000
END_BLOCK = 46_461_000
FLOOR_MULTIPLIER = 2.0
RATES = {'eth_usd': 3800.0, 'ron_usd': 0.15}

PROGRESS_FILE = 'june2025_progress.json'


def rpc_call(method, params, retries=3):
    for attempt in range(retries):
        try:
            data = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
            req = urllib.request.Request(rpc_url, data=json.dumps(data).encode(), headers=headers, method='POST')
            response = urllib.request.urlopen(req, timeout=30)
            return json.loads(response.read())
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                return None


def gql_call(query):
    try:
        req = urllib.request.Request(gql_url, data=json.dumps({"query": query}).encode(), headers=headers)
        response = urllib.request.urlopen(req, timeout=15)
        return json.loads(response.read())
    except:
        return None


def get_axie_class(axie_id):
    result = gql_call(f'{{ axie(axieId: "{axie_id}") {{ class }} }}')
    if result and result.get('data', {}).get('axie'):
        return result['data']['axie'].get('class')
    return None


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {'current_block': START_BLOCK, 'sales': [], 'seen_tx': []}


def save_progress(current_block, sales, seen_tx):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump({
            'current_block': current_block,
            'sales': sales[-10000:],  # Keep last 10k to limit file size
            'seen_tx': list(seen_tx)[-50000:]
        }, f)


def process_receipt(tx_hash, block_num, block_ts):
    """Extract sale from receipt."""
    receipt = rpc_call("eth_getTransactionReceipt", [tx_hash])
    if not receipt or 'result' not in receipt or not receipt['result']:
        return []

    r = receipt['result']
    axie_ids = []
    payments = []

    for log in r['logs']:
        if not log.get('topics'):
            continue
        sig = log['topics'][0]

        # Axie transfer
        if sig == TRANSFER_TOPIC and log['address'].lower() == AXIE_CONTRACT.lower():
            if len(log['topics']) >= 4:
                axie_ids.append(int(log['topics'][3], 16))

        # Payment
        if sig == TRANSFER_TOPIC and log['address'].lower() in TOKENS:
            token_name, decimals = TOKENS[log['address'].lower()]
            if len(log['topics']) == 3 and log.get('data') and log['data'] != '0x':
                value = int(log['data'], 16) / (10**decimals)
                usd = value * RATES['eth_usd'] if token_name == 'WETH' else value * RATES['ron_usd']
                payments.append((token_name, value, usd))

    if not axie_ids or not payments:
        return []

    best = max(payments, key=lambda x: x[2])
    per_axie = best[2] / len(axie_ids)

    return [{'axie_id': aid, 'price_usd': per_axie, 'token': best[0],
             'block': block_num, 'ts': block_ts.isoformat(), 'tx': tx_hash}
            for aid in axie_ids]


def main():
    print("=" * 60)
    print("JUNE 2025 PREMIUM SALES FETCHER")
    print(f"Blocks: {START_BLOCK:,} - {END_BLOCK:,}")
    print("=" * 60)

    # Load progress
    progress = load_progress()
    current_block = progress['current_block']
    all_sales = progress['sales']
    seen_tx = set(progress['seen_tx'])

    if current_block > START_BLOCK:
        print(f"Resuming from block {current_block:,} ({len(all_sales)} sales so far)")

    start_time = time.time()
    batch_size = 499

    try:
        while current_block <= END_BLOCK:
            end_block = min(current_block + batch_size, END_BLOCK)

            # Progress update every ~25k blocks
            if (current_block - START_BLOCK) % 25000 < batch_size:
                progress_pct = (current_block - START_BLOCK) / (END_BLOCK - START_BLOCK) * 100
                block_data = rpc_call("eth_getBlockByNumber", [hex(current_block), False])
                if block_data and block_data.get('result'):
                    ts = datetime.fromtimestamp(int(block_data['result']['timestamp'], 16))
                    elapsed = time.time() - start_time
                    rate = (current_block - progress['current_block']) / max(1, elapsed) * 3600
                    print(f"[{progress_pct:5.1f}%] Block {current_block:,} ({ts.strftime('%Y-%m-%d')}) | {len(all_sales)} sales | {rate:.0f} blk/hr")

            # Get logs
            logs = rpc_call("eth_getLogs", [{
                "address": AXIE_CONTRACT,
                "topics": [TRANSFER_TOPIC],
                "fromBlock": hex(current_block),
                "toBlock": hex(end_block)
            }])

            if logs and 'result' in logs:
                for event in logs['result']:
                    tx_hash = event['transactionHash']
                    if tx_hash in seen_tx:
                        continue
                    seen_tx.add(tx_hash)

                    block_num = int(event['blockNumber'], 16)
                    block_data = rpc_call("eth_getBlockByNumber", [event['blockNumber'], False])
                    if not block_data or not block_data.get('result'):
                        continue
                    block_ts = datetime.fromtimestamp(int(block_data['result']['timestamp'], 16))

                    sales = process_receipt(tx_hash, block_num, block_ts)
                    all_sales.extend(sales)

            current_block = end_block + 1

            # Save progress every 50k blocks
            if (current_block - START_BLOCK) % 50000 < batch_size:
                save_progress(current_block, all_sales, seen_tx)

    except KeyboardInterrupt:
        print("\n\nInterrupted! Saving progress...")
        save_progress(current_block, all_sales, seen_tx)
        print(f"Progress saved. {len(all_sales)} sales collected.")
        return

    # Phase 2: Get classes and calculate floors
    print(f"\n--- PHASE 2: Fetching classes for {len(set(s['axie_id'] for s in all_sales))} unique Axies ---")

    unique_axies = list(set(s['axie_id'] for s in all_sales))
    axie_classes = {}

    for i, axie_id in enumerate(unique_axies):
        if i % 200 == 0:
            print(f"  Classes: {i}/{len(unique_axies)}")
        axie_classes[axie_id] = get_axie_class(axie_id)
        time.sleep(0.02)

    # Calculate floors
    class_prices = defaultdict(list)
    for s in all_sales:
        cls = axie_classes.get(s['axie_id'])
        if cls:
            s['class'] = cls
            class_prices[cls].append(s['price_usd'])

    floor_prices = {}
    print("\nFloor by class:")
    for cls in sorted(class_prices.keys()):
        floor = min(class_prices[cls])
        floor_prices[cls] = floor
        print(f"  {cls:10}: ${floor:>6.2f} ({len(class_prices[cls]):>5} sales)")

    overall_floor = min(s['price_usd'] for s in all_sales) if all_sales else 1.0

    # Filter premium
    premium = []
    for s in all_sales:
        cls = s.get('class')
        floor = floor_prices.get(cls, overall_floor)
        if s['price_usd'] > floor * FLOOR_MULTIPLIER:
            s['floor'] = floor
            s['multiple'] = s['price_usd'] / floor
            premium.append(s)

    print(f"\n=== PREMIUM SALES (>{FLOOR_MULTIPLIER}x floor) ===")
    print(f"Count: {len(premium)} / {len(all_sales)} ({100*len(premium)/max(1,len(all_sales)):.1f}%)")

    # Insert to DB
    print("\n--- Inserting to database ---")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SET search_path TO axie, public")

    inserted = 0
    for s in premium:
        try:
            ts = datetime.fromisoformat(s['ts'])
            cur.execute("""
                INSERT INTO axie_sales (tx_hash, axie_id, class, price_token, token_type, price_usd,
                    eth_usd_rate, ron_usd_rate, block_number, block_timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tx_hash, axie_id, block_timestamp) DO NOTHING
            """, (s['tx'], s['axie_id'], s.get('class'), s['price_usd']/RATES['eth_usd'], s['token'],
                  s['price_usd'], RATES['eth_usd'], RATES['ron_usd'], s['block'], ts))
            if cur.rowcount > 0:
                inserted += 1
        except:
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
    print("\n" + "=" * 60)
    print("COMPLETE - JUNE 2025 PREMIUM SALES")
    print("=" * 60)
    print(f"Total sales: {len(all_sales)}")
    print(f"Premium (>{FLOOR_MULTIPLIER}x): {len(premium)}")
    print(f"Inserted: {inserted}")

    if premium:
        prices = [s['price_usd'] for s in premium]
        print(f"\nStats: ${min(prices):.2f} - ${max(prices):.2f} (avg ${sum(prices)/len(prices):.2f})")

        print(f"\nTop 20 sales:")
        for s in sorted(premium, key=lambda x: x['price_usd'], reverse=True)[:20]:
            print(f"  #{s['axie_id']:>8} | {s.get('class','?'):>8} | ${s['price_usd']:>8.2f} | {s.get('multiple',0):.1f}x")

    # Cleanup progress file
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)


if __name__ == "__main__":
    main()
