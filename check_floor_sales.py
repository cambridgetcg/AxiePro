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

# Verify floor price from GraphQL
floor = gql_call('{ axies(from:0,size:1,sort:PriceAsc,auctionType:Sale) { results { id class order { currentPriceUsd } } } }')
floor_price = floor['data']['axies']['results'][0]['order']['currentPriceUsd']
print(f"Current Floor Price: ${float(floor_price):.2f}")
print("=" * 70)

# Token addresses
TOKENS = {
    "0xe514d9deb7966c8be0ca922de8a064264ea6bcd4": ("WETH", ETH_USD, 18),
    "0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5": ("WRON", RON_USD, 18),
}

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
    print(f"\nAnalyzing {len(events)} transfers for ALL sales...\n")
    
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
                        'block': int(event['blockNumber'], 16),
                        'batch_size': len(axie_ids)
                    })
    
    # Sort by USD price
    sales_sorted = sorted(sales, key=lambda x: x['usd'])
    
    print(f"ALL SALES (sorted by price, lowest first):")
    print("-" * 70)
    print(f"{'Axie ID':>10} | {'Price':>12} | {'USD':>10} | {'Batch'}")
    print("-" * 70)
    
    for sale in sales_sorted[:25]:
        batch_info = f"(1 of {sale['batch_size']})" if sale['batch_size'] > 1 else ""
        print(f"#{sale['axie_id']:>9} | {sale['price']:>10.6f} {sale['token']:<4} | ${sale['usd']:>8.2f} | {batch_info}")
    
    print("-" * 70)
    print(f"\nPrice Distribution:")
    under_5 = len([s for s in sales if s['usd'] < 5])
    under_10 = len([s for s in sales if s['usd'] < 10])
    under_100 = len([s for s in sales if s['usd'] < 100])
    over_100 = len([s for s in sales if s['usd'] >= 100])
    print(f"  Under $5:    {under_5} sales")
    print(f"  $5-$10:      {under_10 - under_5} sales")
    print(f"  $10-$100:    {under_100 - under_10} sales")
    print(f"  Over $100:   {over_100} sales")

