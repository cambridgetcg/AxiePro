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

# Get exchange rates for USD conversion
rates = gql_call("{ exchangeRate { eth { usd } ron { usd } } }")['data']['exchangeRate']
WETH_USD = rates['eth']['usd']  # WETH pegged to ETH
RON_USD = rates['ron']['usd']

print(f"Exchange Rates: WETH=${WETH_USD:.2f}, RON=${RON_USD:.4f}")
print("=" * 70)

# Token addresses for identification
TOKENS = {
    "0xe514d9deb7966c8be0ca922de8a064264ea6bcd4": ("WETH", WETH_USD),
    "0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5": ("WRON", RON_USD),
}

# Get current block and transfers
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
    for event in events[:30]:
        tx_hash = event['transactionHash']
        receipt = rpc_call("eth_getTransactionReceipt", [tx_hash])
        
        if 'result' in receipt and receipt['result']:
            r = receipt['result']
            
            payment_value = 0
            payment_token = "UNKNOWN"
            usd_rate = 0
            axie_id = None
            
            for log in r['logs']:
                sig = log['topics'][0] if log['topics'] else None
                
                if sig == TRANSFER_TOPIC and log['address'].lower() == AXIE_CONTRACT.lower():
                    if len(log['topics']) >= 4:
                        axie_id = int(log['topics'][3], 16)
                
                if sig == TRANSFER_TOPIC and log['address'].lower() != AXIE_CONTRACT.lower():
                    if len(log['topics']) == 3 and log['data'] and log['data'] != '0x':
                        token_addr = log['address'].lower()
                        value = int(log['data'], 16) / 10**18
                        
                        if token_addr in TOKENS:
                            token_name, rate = TOKENS[token_addr]
                            if value > payment_value:
                                payment_value = value
                                payment_token = token_name
                                usd_rate = rate
            
            if axie_id and payment_value > 0:
                usd_value = payment_value * usd_rate
                sales.append({
                    'axie_id': axie_id,
                    'price': payment_value,
                    'token': payment_token,
                    'usd': usd_value,
                    'block': int(event['blockNumber'], 16)
                })
    
    print(f"RECENT AXIE SALES (last ~25 min):")
    print("-" * 70)
    
    for sale in sorted(sales, key=lambda x: x['block'], reverse=True):
        print(f"Axie #{sale['axie_id']:>8} | {sale['price']:>10.4f} {sale['token']:<4} | ${sale['usd']:>10.2f} USD")
    
    print("-" * 70)
    print(f"Total sales found: {len(sales)}")
    if sales:
        total_usd = sum(s['usd'] for s in sales)
        avg_usd = total_usd / len(sales)
        print(f"Total volume: ${total_usd:,.2f}")
        print(f"Average price: ${avg_usd:.2f}")
else:
    print(f"Error: {logs.get('error')}")

