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

# Token addresses on Ronin - lowercase (CORRECTED)
TOKENS = {
    "0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5": ("WETH", ETH_USD, 18),  # WETH on Ronin
    "0xe514d9deb7966c8be0ca922de8a064264ea6bcd4": ("WRON", RON_USD, 18),  # WRON on Ronin
    "0xa8754b9fa15fc18bb59458815510e40a12cd2014": ("SLP", 0.00084, 0),    # SLP has 0 decimals
    "0x97a9107c1793bc407d6f527b77e7fff4d812bece": ("AXS", 0.98, 18),
}

print(f"Exchange Rates: ETH=${ETH_USD:.2f}, RON=${RON_USD:.4f}")
print("=" * 80)

# Get transfers
block_result = rpc_call("eth_blockNumber", [])
current_block = int(block_result['result'], 16)

AXIE_CONTRACT = "0x32950db2a7164ae833121501c797d79e7b79d74c"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

from_block = hex(current_block - 499)
to_block = hex(current_block)

logs = rpc_call("eth_getLogs", [{
    "address": AXIE_CONTRACT,
    "topics": [TRANSFER_TOPIC],
    "fromBlock": from_block,
    "toBlock": to_block
}])

if 'result' in logs:
    events = logs['result']
    print(f"\nAnalyzing {len(events)} transfers...\n")
    
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
            
            # Collect all transfers in this tx
            axie_ids = []
            payments = []
            
            for log in r['logs']:
                sig = log['topics'][0] if log['topics'] else None
                
                # Axie NFT transfer
                if sig == TRANSFER_TOPIC and log['address'].lower() == AXIE_CONTRACT.lower():
                    if len(log['topics']) >= 4:
                        axie_ids.append(int(log['topics'][3], 16))
                
                # Token transfer (potential payment)
                if sig == TRANSFER_TOPIC and log['address'].lower() in TOKENS:
                    token_addr = log['address'].lower()
                    token_name, rate, decimals = TOKENS[token_addr]
                    
                    if len(log['topics']) == 3 and log['data'] and log['data'] != '0x':
                        raw_value = int(log['data'], 16)
                        value = raw_value / (10**decimals) if decimals > 0 else raw_value
                        payments.append((token_name, value, rate))
            
            # Match axies to largest payment
            if axie_ids and payments:
                # Get the largest payment
                best_payment = max(payments, key=lambda x: x[1] * x[2])
                token_name, value, rate = best_payment
                usd_value = value * rate
                
                for axie_id in axie_ids:
                    if usd_value > 0.01:  # Filter out dust
                        sales.append({
                            'axie_id': axie_id,
                            'price': value,
                            'token': token_name,
                            'usd': usd_value / len(axie_ids),  # Split if batch
                            'block': int(event['blockNumber'], 16)
                        })
    
    print(f"RECENT AXIE SALES WITH PRICES:")
    print("-" * 80)
    print(f"{'Axie ID':>10} | {'Price':>12} {'Token':<5} | {'USD Value':>12} | Block")
    print("-" * 80)
    
    for sale in sorted(sales, key=lambda x: x['block'], reverse=True)[:20]:
        print(f"#{sale['axie_id']:>9} | {sale['price']:>12.4f} {sale['token']:<5} | ${sale['usd']:>11.2f} | {sale['block']}")
    
    print("-" * 80)
    print(f"Total sales with price data: {len(sales)}")
    if sales:
        total_usd = sum(s['usd'] for s in sales)
        avg_usd = total_usd / len(sales)
        print(f"Total volume: ${total_usd:,.2f}")
        print(f"Average price: ${avg_usd:.2f}")
else:
    print(f"Error: {logs.get('error')}")

