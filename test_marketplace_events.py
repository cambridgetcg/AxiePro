import json
import subprocess
import urllib.request

result = subprocess.run(['aws', 'secretsmanager', 'get-secret-value', '--secret-id', 'axie-explorer/api-keys', '--query', 'SecretString', '--output', 'text'], capture_output=True, text=True)
secrets = json.loads(result.stdout)
api_key = secrets.get('SKYMAVIS_API_KEY', '')

rpc_url = 'https://api-gateway.skymavis.com/rpc'
headers = {'X-API-Key': api_key, 'Content-Type': 'application/json'}

def rpc_call(method, params, label):
    try:
        data = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
        req = urllib.request.Request(rpc_url, data=json.dumps(data).encode(), headers=headers, method='POST')
        response = urllib.request.urlopen(req, timeout=30)
        result = json.loads(response.read())
        print(f"\n=== {label} ===")
        if 'result' in result:
            print(json.dumps(result['result'], indent=2)[:3000] if isinstance(result['result'], (dict, list)) else result['result'])
        elif 'error' in result:
            print(f"Error: {result['error']}")
        return result
    except Exception as e:
        print(f"\n=== {label} === FAILED: {e}")
        return None

# Get current block
block_result = rpc_call("eth_blockNumber", [], "Current Block")
current_block = int(block_result['result'], 16) if block_result else 0
print(f"Current block: {current_block}")

# Calculate recent blocks (last 1000 blocks ~ 50 minutes at 3s/block)
from_block = hex(current_block - 1000)
to_block = hex(current_block)

# Marketplace V2 contract: 0xfff9ce5f71ca6178d3beecedb61e7eff1602950e
# AuctionCreated event topic: 0x9b1... (need to find)
# AuctionSuccessful event topic

# Get logs from new marketplace contract
print(f"\nSearching blocks {current_block - 1000} to {current_block}")

# Try to get any events from marketplace
rpc_call("eth_getLogs", [{
    "address": "0xfff9ce5f71ca6178d3beecedb61e7eff1602950e",  # Mavis Market
    "fromBlock": from_block,
    "toBlock": to_block
}], "Mavis Market Events (last 1000 blocks)")

# Try old Axie marketplace  
rpc_call("eth_getLogs", [{
    "address": "0x213073989821f738a7ba3520c3d31a1f9ad31bbd",  # Old marketplace
    "fromBlock": from_block,
    "toBlock": to_block
}], "Old Marketplace Events")

