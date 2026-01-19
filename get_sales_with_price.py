import json
import subprocess
import urllib.request

result = subprocess.run(['aws', 'secretsmanager', 'get-secret-value', '--secret-id', 'axie-explorer/api-keys', '--query', 'SecretString', '--output', 'text'], capture_output=True, text=True)
secrets = json.loads(result.stdout)
api_key = secrets.get('SKYMAVIS_API_KEY', '')

rpc_url = 'https://api-gateway.skymavis.com/rpc'
headers = {'X-API-Key': api_key, 'Content-Type': 'application/json'}

def rpc_call(method, params):
    data = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    req = urllib.request.Request(rpc_url, data=json.dumps(data).encode(), headers=headers, method='POST')
    response = urllib.request.urlopen(req, timeout=30)
    return json.loads(response.read())

# Get current block and Axie transfers
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
    print(f"Analyzing {len(events)} transfers to find sales with prices...\n")
    
    # Get receipts for first few transfers
    sales_found = []
    
    for event in events[:20]:
        tx_hash = event['transactionHash']
        receipt = rpc_call("eth_getTransactionReceipt", [tx_hash])
        
        if 'result' in receipt and receipt['result']:
            r = receipt['result']
            
            # Look for WETH/WRON transfer in same tx (indicates sale)
            weth_value = 0
            axie_id = None
            from_addr = None
            to_addr = None
            
            for log in r['logs']:
                sig = log['topics'][0] if log['topics'] else None
                
                # ERC721 Transfer (Axie)
                if sig == TRANSFER_TOPIC and log['address'].lower() == AXIE_CONTRACT.lower():
                    if len(log['topics']) >= 4:
                        from_addr = '0x' + log['topics'][1][-40:]
                        to_addr = '0x' + log['topics'][2][-40:]
                        axie_id = int(log['topics'][3], 16)
                
                # ERC20 Transfer (WETH/WRON payment)
                if sig == TRANSFER_TOPIC and log['address'].lower() != AXIE_CONTRACT.lower():
                    if len(log['topics']) == 3 and log['data'] != '0x':
                        value = int(log['data'], 16) / 10**18
                        if value > weth_value:
                            weth_value = value
            
            if axie_id and weth_value > 0:
                sales_found.append({
                    'axie_id': axie_id,
                    'price': weth_value,
                    'from': from_addr,
                    'to': to_addr,
                    'tx': tx_hash,
                    'block': int(event['blockNumber'], 16)
                })
    
    print(f"Found {len(sales_found)} sales with price data:\n")
    for sale in sales_found:
        print(f"Axie #{sale['axie_id']}: {sale['price']:.4f} WETH/RON")
        print(f"  Block: {sale['block']}, TX: {sale['tx'][:20]}...")
        print()
    
else:
    print(f"Error: {logs.get('error')}")

