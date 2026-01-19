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

print(f"Exchange Rates: ETH=${ETH_USD:.2f}, RON=${RON_USD:.4f}")

# CORRECTED token addresses!
TOKENS = {
    "0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5": ("WETH", ETH_USD, 18),  # WETH
    "0xe514d9deb7966c8be0ca922de8a064264ea6bcd4": ("WRON", RON_USD, 18),  # WRON
}

# Get transfers
block_result = rpc_call("eth_blockNumber", [])
current_block = int(block_result['result'], 16)

AXIE_CONTRACT = "0x32950db2a7164ae833121501c797d79e7b79d74c"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

logs = rpc_call("eth_getLogs", [{
    "address": AXIE_CONTRACT,
    "topics": [TRANSFER_TOPIC],
    "fromBlock": hex(current_block - 499),
    "toBlock": hex(current_block)
}])

if 'result' in logs:
    events = logs['result']
    print(f"Analyzing {len(events)} transfers...\n")
    
    sales = []
    seen_tx = set()
    
    for event in events:
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
    
    # Sort by USD price
    sales_sorted = sorted(sales, key=lambda x: x['usd'])
    
    print(f"AXIE SALES (sorted by price):")
    print("-" * 60)
    print(f"{'Axie ID':>10} | {'Price':>14} | {'USD':>10}")
    print("-" * 60)
    
    for sale in sales_sorted[:30]:
        print(f"#{sale['axie_id']:>9} | {sale['price']:>10.6f} {sale['token']:<4} | ${sale['usd']:>8.2f}")
    
    print("-" * 60)
    print(f"\nTotal sales: {len(sales)}")
    if sales:
        avg = sum(s['usd'] for s in sales) / len(sales)
        median = sorted(sales, key=lambda x: x['usd'])[len(sales)//2]['usd']
        print(f"Average: ${avg:.2f}")
        print(f"Median: ${median:.2f}")

