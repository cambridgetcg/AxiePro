import json
import subprocess
import urllib.request

result = subprocess.run(['aws', 'secretsmanager', 'get-secret-value', '--secret-id', 'axie-explorer/api-keys', '--query', 'SecretString', '--output', 'text'], capture_output=True, text=True)
secrets = json.loads(result.stdout)
api_key = secrets.get('SKYMAVIS_API_KEY', '')

rpc_url = 'https://api-gateway.skymavis.com/rpc'
gql_url = 'https://api-gateway.skymavis.com/graphql/marketplace'
headers = {'X-API-Key': api_key, 'Content-Type': 'application/json'}

def rpc_call(method, params):
    data = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    req = urllib.request.Request(rpc_url, data=json.dumps(data).encode(), headers=headers, method='POST')
    response = urllib.request.urlopen(req, timeout=30)
    return json.loads(response.read())

def gql_call(query):
    req = urllib.request.Request(gql_url, data=json.dumps({"query": query}).encode(), headers=headers)
    response = urllib.request.urlopen(req, timeout=30)
    return json.loads(response.read())

# Get exchange rates
rates = gql_call("{ exchangeRate { eth { usd } ron { usd } } }")['data']['exchangeRate']
ETH_USD = rates['eth']['usd']
RON_USD = rates['ron']['usd']

print(f"Exchange Rates: WETH=${ETH_USD:.2f}, RON=${RON_USD:.4f}")

# Token addresses (CORRECTED)
TOKENS = {
    "0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5": ("WETH", ETH_USD, 18),
    "0xe514d9deb7966c8be0ca922de8a064264ea6bcd4": ("WRON", RON_USD, 18),
}

AXIE_CONTRACT = "0x32950db2a7164ae833121501c797d79e7b79d74c"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

# Get current block
block_result = rpc_call("eth_blockNumber", [])
current_block = int(block_result['result'], 16)
print(f"Current block: {current_block}")

sales = []
seen_tx = set()
end_block = current_block
batch_size = 499  # Max blocks per query

print(f"\nFetching sales (target: 100)...")

while len(sales) < 100:
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
            
            axie_ids = []
            payments = []
            
            for log in r['logs']:
                sig = log['topics'][0] if log['topics'] else None
                
                if sig == TRANSFER_TOPIC and log['address'].lower() == AXIE_CONTRACT.lower():
                    if len(log['topics']) >= 4:
                        axie_ids.append(int(log['topics'][3], 16))
                
                if sig == TRANSFER_TOPIC and log['address'].lower() in TOKENS:
                    token_addr = log['address'].lower()
                    token_name, rate, decimals = TOKENS[token_addr]
                    
                    if len(log['topics']) == 3 and log['data'] and log['data'] != '0x':
                        raw_value = int(log['data'], 16)
                        value = raw_value / (10**decimals)
                        usd = value * rate
                        payments.append((token_name, value, usd))
            
            if axie_ids and payments:
                best_payment = max(payments, key=lambda x: x[2])
                token_name, value, usd = best_payment
                per_axie_usd = usd / len(axie_ids)
                
                for axie_id in axie_ids:
                    sales.append({
                        'axie_id': axie_id,
                        'price': value / len(axie_ids),
                        'token': token_name,
                        'usd': per_axie_usd,
                        'block': int(event['blockNumber'], 16)
                    })
                    batch_sales += 1
    
    print(f" -> {batch_sales} sales (total: {len(sales)})")
    
    end_block = start_block - 1
    
    if len(transfers) == 0:
        print("No more transfers found")
        break

# Sort by block (most recent first)
sales_sorted = sorted(sales, key=lambda x: -x['block'])[:100]

print(f"\n{'='*70}")
print(f"MOST RECENT 100 AXIE SALES")
print(f"{'='*70}")
print(f"{'#':>3} | {'Axie ID':>10} | {'Price':>14} | {'USD':>10} | Block")
print(f"{'-'*70}")

for i, sale in enumerate(sales_sorted, 1):
    print(f"{i:>3} | #{sale['axie_id']:>9} | {sale['price']:>10.6f} {sale['token']:<4} | ${sale['usd']:>8.2f} | {sale['block']}")

print(f"{'-'*70}")
print(f"\nSummary:")
print(f"  Total sales: {len(sales_sorted)}")
if sales_sorted:
    prices = [s['usd'] for s in sales_sorted]
    print(f"  Min: ${min(prices):.2f}")
    print(f"  Max: ${max(prices):.2f}")
    print(f"  Avg: ${sum(prices)/len(prices):.2f}")
    print(f"  Median: ${sorted(prices)[len(prices)//2]:.2f}")

