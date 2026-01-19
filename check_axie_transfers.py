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

# Get current block
block_result = rpc_call("eth_blockNumber", [])
current_block = int(block_result['result'], 16)
print(f"Current block: {current_block}")

# Axie NFT contract - check for Transfer events
AXIE_CONTRACT = "0x32950db2a7164ae833121501c797d79e7b79d74c"

# ERC721 Transfer event signature: Transfer(address,address,uint256)
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

from_block = hex(current_block - 499)
to_block = hex(current_block)

print(f"\nSearching for Axie NFT Transfer events...")

logs = rpc_call("eth_getLogs", [{
    "address": AXIE_CONTRACT,
    "topics": [TRANSFER_TOPIC],
    "fromBlock": from_block,
    "toBlock": to_block
}])

if 'result' in logs:
    events = logs['result']
    print(f"Found {len(events)} Axie Transfer events")
    
    for i, event in enumerate(events[:10]):
        print(f"\n--- Transfer {i+1} ---")
        print(f"  Block: {int(event['blockNumber'], 16)}")
        print(f"  TX: {event['transactionHash'][:30]}...")
        
        if len(event['topics']) >= 4:
            from_addr = '0x' + event['topics'][1][-40:]
            to_addr = '0x' + event['topics'][2][-40:]
            token_id = int(event['topics'][3], 16)
            
            print(f"  From: {from_addr[:15]}...")
            print(f"  To: {to_addr[:15]}...")
            print(f"  Axie ID: {token_id}")
            
            # Check if from marketplace (indicating sale)
            if from_addr.lower() == "0x213073989821f738a7ba3520c3d31a1f9ad31bbd":
                print(f"  ** SALE FROM MARKETPLACE **")
else:
    print(f"Error: {logs.get('error')}")

