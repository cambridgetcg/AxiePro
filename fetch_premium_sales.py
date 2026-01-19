#!/usr/bin/env python3
"""Fetch premium Axie sales (>2x floor) from June 2025.

Strategy:
1. Fetch all transfers in large batches
2. Process receipts to extract sales with prices
3. Calculate floor per class
4. Filter to premium sales only
"""

import json
import subprocess
import urllib.request
import psycopg2
from datetime import datetime
from collections import defaultdict
import time

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

# June 2025 block range
START_BLOCK = 45_626_000  # June 1, 2025
END_BLOCK = 46_461_000    # June 30, 2025
FLOOR_MULTIPLIER = 2.0

# Historical rates for June 2025
RATES = {'eth_usd': 3800.0, 'ron_usd': 0.15}


def rpc_call(method, params):
    data = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    req = urllib.request.Request(rpc_url, data=json.dumps(data).encode(), headers=headers, method='POST')
    response = urllib.request.urlopen(req, timeout=60)
    return json.loads(response.read())


def gql_call(query):
    req = urllib.request.Request(gql_url, data=json.dumps({"query": query}).encode(), headers=headers)
    response = urllib.request.urlopen(req, timeout=30)
    return json.loads(response.read())


def get_axie_class(axie_id):
    """Fetch Axie class from GraphQL."""
    query = f'''{{ axie(axieId: "{axie_id}") {{ class }} }}'''
    try:
        result = gql_call(query)
        axie = result.get('data', {}).get('axie')
        return axie.get('class') if axie else None
    except:
        return None


def extract_sale_from_receipt(tx_hash, block_num, block_timestamp):
    """Extract sale details from transaction receipt."""
    try:
        receipt = rpc_call("eth_getTransactionReceipt", [tx_hash])
        if 'result' not in receipt or not receipt['result']:
            return []

        r = receipt['result']
        axie_ids = []
        payments = []
        seller = None
        buyer = None

        for log in r['logs']:
            sig = log['topics'][0] if log['topics'] else None

            # Axie transfer
            if sig == TRANSFER_TOPIC and log['address'].lower() == AXIE_CONTRACT.lower():
                if len(log['topics']) >= 4:
                    axie_ids.append(int(log['topics'][3], 16))
                    seller = '0x' + log['topics'][1][-40:]
                    buyer = '0x' + log['topics'][2][-40:]

            # Payment token
            if sig == TRANSFER_TOPIC and log['address'].lower() in TOKENS:
                token_addr = log['address'].lower()
                token_name, decimals = TOKENS[token_addr]

                if len(log['topics']) == 3 and log['data'] and log['data'] != '0x':
                    raw_value = int(log['data'], 16)
                    value = raw_value / (10**decimals)
                    usd = value * RATES['eth_usd'] if token_name == 'WETH' else value * RATES['ron_usd']
                    payments.append((token_name, value, raw_value, usd))

        if not axie_ids or not payments:
            return []

        best_payment = max(payments, key=lambda x: x[3])
        token_name, value, raw_value, usd = best_payment
        per_axie_value = value / len(axie_ids)
        per_axie_usd = usd / len(axie_ids)

        sales = []
        for axie_id in axie_ids:
            sales.append({
                'tx_hash': tx_hash,
                'axie_id': axie_id,
                'price_raw': raw_value // len(axie_ids),
                'price_token': per_axie_value,
                'token_type': token_name,
                'price_usd': per_axie_usd,
                'eth_usd_rate': RATES['eth_usd'],
                'ron_usd_rate': RATES['ron_usd'],
                'seller': seller,
                'buyer': buyer,
                'block_number': block_num,
                'block_timestamp': block_timestamp
            })
        return sales

    except Exception as e:
        return []


def main():
    print("=" * 60)
    print("PREMIUM AXIE SALES - JUNE 2025")
    print(f"Blocks {START_BLOCK:,} to {END_BLOCK:,}")
    print(f"Filter: >{FLOOR_MULTIPLIER}x floor price")
    print("=" * 60)

    # Phase 1: Collect all transfers and process them
    print("\n--- PHASE 1: Collecting sales ---")
    all_sales = []
    seen_tx = set()
    batch_size = 499  # Max allowed by RPC
    current_block = START_BLOCK
    total_batches = (END_BLOCK - START_BLOCK) // batch_size

    batch_num = 0
    while current_block <= END_BLOCK:
        end_block = min(current_block + batch_size, END_BLOCK)
        batch_num += 1

        # Get timestamp for progress
        if batch_num % 50 == 1:
            block_data = rpc_call("eth_getBlockByNumber", [hex(current_block), False])
            ts = datetime.fromtimestamp(int(block_data['result']['timestamp'], 16))
            progress = (current_block - START_BLOCK) / (END_BLOCK - START_BLOCK) * 100
            print(f"  [{progress:5.1f}%] Block {current_block:,} ({ts.strftime('%Y-%m-%d')}) - {len(all_sales)} sales so far")

        # Get transfer logs
        logs = rpc_call("eth_getLogs", [{
            "address": AXIE_CONTRACT,
            "topics": [TRANSFER_TOPIC],
            "fromBlock": hex(current_block),
            "toBlock": hex(end_block)
        }])

        if 'result' in logs:
            for event in logs['result']:
                tx_hash = event['transactionHash']
                if tx_hash in seen_tx:
                    continue
                seen_tx.add(tx_hash)

                block_num = int(event['blockNumber'], 16)
                block_data = rpc_call("eth_getBlockByNumber", [event['blockNumber'], False])
                block_timestamp = datetime.fromtimestamp(int(block_data['result']['timestamp'], 16))

                sales = extract_sale_from_receipt(tx_hash, block_num, block_timestamp)
                all_sales.extend(sales)

        current_block = end_block + 1
        time.sleep(0.05)

    print(f"\nTotal sales collected: {len(all_sales)}")

    if not all_sales:
        print("No sales found!")
        return

    # Phase 2: Fetch classes
    print("\n--- PHASE 2: Fetching Axie classes ---")
    unique_axies = list(set(s['axie_id'] for s in all_sales))
    axie_classes = {}

    for i, axie_id in enumerate(unique_axies):
        if i % 100 == 0:
            print(f"  Classes: {i}/{len(unique_axies)}")
        axie_classes[axie_id] = get_axie_class(axie_id)
        time.sleep(0.03)

    for sale in all_sales:
        sale['class'] = axie_classes.get(sale['axie_id'])

    # Phase 3: Calculate floors
    print("\n--- PHASE 3: Calculating floor prices ---")
    class_prices = defaultdict(list)
    for sale in all_sales:
        if sale['class']:
            class_prices[sale['class']].append(sale['price_usd'])

    floor_prices = {}
    print("\nFloor by class:")
    for axie_class in sorted(class_prices.keys()):
        prices = class_prices[axie_class]
        floor = min(prices)
        floor_prices[axie_class] = floor
        print(f"  {axie_class:10}: ${floor:>6.2f} ({len(prices):>5} sales)")

    overall_floor = min(s['price_usd'] for s in all_sales)
    print(f"\n  Overall:   ${overall_floor:.2f}")

    # Phase 4: Filter premium
    print(f"\n--- PHASE 4: Filtering premium (>{FLOOR_MULTIPLIER}x floor) ---")
    premium_sales = []

    for sale in all_sales:
        axie_class = sale['class']
        floor = floor_prices.get(axie_class, overall_floor)
        threshold = floor * FLOOR_MULTIPLIER

        if sale['price_usd'] > threshold:
            sale['floor_price'] = floor
            sale['floor_multiple'] = sale['price_usd'] / floor
            premium_sales.append(sale)

    print(f"Premium sales: {len(premium_sales)} / {len(all_sales)} ({100*len(premium_sales)/len(all_sales):.1f}%)")

    # Phase 5: Insert to DB
    print("\n--- PHASE 5: Inserting to database ---")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SET search_path TO axie, public")

    inserted = 0
    for sale in premium_sales:
        try:
            cur.execute("""
                INSERT INTO axie_sales (
                    tx_hash, axie_id, class, price_raw, price_token, token_type, price_usd,
                    eth_usd_rate, ron_usd_rate, seller, buyer, block_number, block_timestamp
                ) VALUES (
                    %(tx_hash)s, %(axie_id)s, %(class)s, %(price_raw)s, %(price_token)s, %(token_type)s, %(price_usd)s,
                    %(eth_usd_rate)s, %(ron_usd_rate)s, %(seller)s, %(buyer)s, %(block_number)s, %(block_timestamp)s
                )
                ON CONFLICT (tx_hash, axie_id, block_timestamp) DO NOTHING
            """, sale)
            if cur.rowcount > 0:
                inserted += 1
        except Exception as e:
            pass

    conn.commit()

    # Also queue for metadata fetch
    for sale in premium_sales:
        try:
            cur.execute("SELECT queue_metadata_fetch(%s, %s, %s)",
                       (sale['axie_id'], 'premium_june2025', 5))
        except:
            pass
    conn.commit()

    cur.close()
    conn.close()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY - JUNE 2025 PREMIUM SALES")
    print("=" * 60)
    print(f"Total sales in period: {len(all_sales)}")
    print(f"Premium sales (>{FLOOR_MULTIPLIER}x): {len(premium_sales)}")
    print(f"Inserted to DB: {inserted}")

    if premium_sales:
        prices = [s['price_usd'] for s in premium_sales]
        print(f"\nPremium stats:")
        print(f"  Range: ${min(prices):.2f} - ${max(prices):.2f}")
        print(f"  Average: ${sum(prices)/len(prices):.2f}")

        print(f"\nTop 15 sales:")
        for s in sorted(premium_sales, key=lambda x: x['price_usd'], reverse=True)[:15]:
            print(f"  #{s['axie_id']:>8} | {s.get('class','?'):>8} | ${s['price_usd']:>8.2f} | {s['floor_multiple']:.1f}x | {s['block_timestamp'].strftime('%m-%d')}")


if __name__ == "__main__":
    main()
