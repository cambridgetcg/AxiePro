#!/usr/bin/env python3
"""Load Axie sales data from Ronin RPC into PostgreSQL database."""

import json
import subprocess
import urllib.request
import psycopg2
from datetime import datetime

# Get API key
result = subprocess.run(['aws', 'secretsmanager', 'get-secret-value', '--secret-id', 'axie-explorer/api-keys', '--query', 'SecretString', '--output', 'text'], capture_output=True, text=True)
secrets = json.loads(result.stdout)
api_key = secrets.get('SKYMAVIS_API_KEY', '')

# RPC and GraphQL endpoints
rpc_url = 'https://api-gateway.skymavis.com/rpc'
gql_url = 'https://api-gateway.skymavis.com/graphql/marketplace'
headers = {'X-API-Key': api_key, 'Content-Type': 'application/json'}

# Database connection
DB_CONFIG = {
    'host': 'cardforum.cn4c2su0o42n.us-east-1.rds.amazonaws.com',
    'port': 5432,
    'dbname': 'postgres',
    'user': 'postgres',
    'password': '***REMOVED-ROTATE-ME***'
}

# Token addresses (CORRECTED)
TOKENS = {
    "0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5": ("WETH", 18),
    "0xe514d9deb7966c8be0ca922de8a064264ea6bcd4": ("WRON", 18),
}

AXIE_CONTRACT = "0x32950db2a7164ae833121501c797d79e7b79d74c"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def rpc_call(method, params):
    data = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    req = urllib.request.Request(rpc_url, data=json.dumps(data).encode(), headers=headers, method='POST')
    response = urllib.request.urlopen(req, timeout=30)
    return json.loads(response.read())


def gql_call(query):
    req = urllib.request.Request(gql_url, data=json.dumps({"query": query}).encode(), headers=headers)
    response = urllib.request.urlopen(req, timeout=30)
    return json.loads(response.read())


def get_exchange_rates():
    rates = gql_call("{ exchangeRate { eth { usd } ron { usd } } }")['data']['exchangeRate']
    return {
        'eth_usd': float(rates['eth']['usd']),
        'ron_usd': float(rates['ron']['usd'])
    }


def fetch_sales(target_count=100):
    """Fetch recent sales from Ronin RPC."""
    rates = get_exchange_rates()
    print(f"Exchange rates: ETH=${rates['eth_usd']:.2f}, RON=${rates['ron_usd']:.4f}")

    block_result = rpc_call("eth_blockNumber", [])
    current_block = int(block_result['result'], 16)
    print(f"Current block: {current_block}")

    sales = []
    seen_tx = set()
    end_block = current_block
    batch_size = 499

    while len(sales) < target_count:
        start_block = end_block - batch_size

        logs = rpc_call("eth_getLogs", [{
            "address": AXIE_CONTRACT,
            "topics": [TRANSFER_TOPIC],
            "fromBlock": hex(start_block),
            "toBlock": hex(end_block)
        }])

        if 'result' not in logs:
            print(f"Error: {logs.get('error')}")
            break

        transfers = logs['result']
        print(f"  Blocks {start_block}-{end_block}: {len(transfers)} transfers", end="")

        batch_sales = 0
        for event in transfers:
            tx_hash = event['transactionHash']
            if tx_hash in seen_tx:
                continue
            seen_tx.add(tx_hash)

            receipt = rpc_call("eth_getTransactionReceipt", [tx_hash])

            if 'result' in receipt and receipt['result']:
                r = receipt['result']
                block_num = int(event['blockNumber'], 16)

                # Get block timestamp
                block_data = rpc_call("eth_getBlockByNumber", [event['blockNumber'], False])
                block_timestamp = datetime.fromtimestamp(int(block_data['result']['timestamp'], 16))

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

                            if token_name == 'WETH':
                                usd = value * rates['eth_usd']
                            else:
                                usd = value * rates['ron_usd']

                            payments.append((token_name, value, raw_value, usd))

                if axie_ids and payments:
                    best_payment = max(payments, key=lambda x: x[3])
                    token_name, value, raw_value, usd = best_payment
                    per_axie_value = value / len(axie_ids)
                    per_axie_usd = usd / len(axie_ids)

                    for axie_id in axie_ids:
                        sales.append({
                            'tx_hash': tx_hash,
                            'axie_id': axie_id,
                            'price_raw': raw_value // len(axie_ids),
                            'price_token': per_axie_value,
                            'token_type': token_name,
                            'price_usd': per_axie_usd,
                            'eth_usd_rate': rates['eth_usd'],
                            'ron_usd_rate': rates['ron_usd'],
                            'seller': seller,
                            'buyer': buyer,
                            'block_number': block_num,
                            'block_timestamp': block_timestamp
                        })
                        batch_sales += 1

        print(f" -> {batch_sales} sales (total: {len(sales)})")
        end_block = start_block - 1

        if len(transfers) == 0:
            break

    return sales[:target_count]


def insert_sales(sales):
    """Insert sales into PostgreSQL database."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Set schema
    cur.execute("SET search_path TO axie, public")

    inserted = 0
    skipped = 0

    for sale in sales:
        try:
            cur.execute("""
                INSERT INTO axie_sales (
                    tx_hash, axie_id, price_raw, price_token, token_type, price_usd,
                    eth_usd_rate, ron_usd_rate, seller, buyer, block_number, block_timestamp
                ) VALUES (
                    %(tx_hash)s, %(axie_id)s, %(price_raw)s, %(price_token)s, %(token_type)s, %(price_usd)s,
                    %(eth_usd_rate)s, %(ron_usd_rate)s, %(seller)s, %(buyer)s, %(block_number)s, %(block_timestamp)s
                )
                ON CONFLICT (tx_hash, axie_id, block_timestamp) DO NOTHING
            """, sale)

            if cur.rowcount > 0:
                inserted += 1
            else:
                skipped += 1

        except Exception as e:
            print(f"Error inserting sale {sale['axie_id']}: {e}")
            skipped += 1

    conn.commit()
    cur.close()
    conn.close()

    return inserted, skipped


def update_sync_state(last_block, last_timestamp, records):
    """Update sync state tracking."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SET search_path TO axie, public")
    cur.execute("""
        UPDATE sync_state
        SET last_block = %s, last_timestamp = %s, records_synced = records_synced + %s, updated_at = NOW()
        WHERE id = 'axie_sales'
    """, (last_block, last_timestamp, records))
    conn.commit()
    cur.close()
    conn.close()


def main():
    print("=" * 60)
    print("LOADING AXIE SALES TO DATABASE")
    print("=" * 60)

    # Fetch sales
    print("\nFetching sales from Ronin RPC...")
    sales = fetch_sales(target_count=100)
    print(f"\nFetched {len(sales)} sales")

    if not sales:
        print("No sales to insert")
        return

    # Insert to database
    print("\nInserting to database...")
    inserted, skipped = insert_sales(sales)
    print(f"Inserted: {inserted}, Skipped (duplicates): {skipped}")

    # Update sync state
    if sales:
        max_block = max(s['block_number'] for s in sales)
        max_ts = max(s['block_timestamp'] for s in sales)
        update_sync_state(max_block, max_ts, inserted)
        print(f"Sync state updated: block {max_block}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    prices = [s['price_usd'] for s in sales]
    print(f"Sales loaded: {inserted}")
    print(f"Price range: ${min(prices):.2f} - ${max(prices):.2f}")
    print(f"Average: ${sum(prices)/len(prices):.2f}")


if __name__ == "__main__":
    main()
