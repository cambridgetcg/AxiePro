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

# Search last 200 blocks (limit to 500 max)
from_block = hex(current_block - 200)
to_block = hex(current_block)

# Mavis Market contract
logs = rpc_call("eth_getLogs", [{
    "address": "0xfff9ce5f71ca6178d3beecedb61e7eff1602950e",
    "fromBlock": from_block,
    "toBlock": to_block
}])

print(f"\n=== Mavis Market Events (last 200 blocks) ===")
if 'result' in logs:
    events = logs['result']
    print(f"Found {len(events)} events")
    for i, event in enumerate(events[:5]):  # Show first 5
        print(f"\nEvent {i+1}:")
        print(f"  Block: {int(event['blockNumber'], 16)}")
        print(f"  TX: {event['transactionHash']}")
        print(f"  Topics: {len(event['topics'])} topics")
        if event['topics']:
            print(f"  Event Sig: {event['topics'][0][:20]}...")
        if event['data'] and event['data'] != '0x':
            print(f"  Data length: {len(event['data'])} chars")
else:
    print(f"Error: {logs.get('error')}")

# Also check the old marketplace for any activity
old_logs = rpc_call("eth_getLogs", [{
    "address": "0x213073989821f738a7ba3520c3d31a1f9ad31bbd",
    "fromBlock": from_block,
    "toBlock": to_block
}])

print(f"\n=== Old Marketplace Events (last 200 blocks) ===")
if 'result' in old_logs:
    events = old_logs['result']
    print(f"Found {len(events)} events")
else:
    print(f"Error: {old_logs.get('error')}")

