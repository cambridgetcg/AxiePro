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

# Marketplace contract address
MARKETPLACE = "0x213073989821f738a7ba3520c3d31a1f9ad31bbd"

# Get ALL logs from marketplace contract (no topic filter)
from_block = hex(current_block - 499)
to_block = hex(current_block)

print(f"\nGetting ALL events from marketplace contract...")

logs = rpc_call("eth_getLogs", [{
    "address": MARKETPLACE,
    "fromBlock": from_block,
    "toBlock": to_block
}])

if 'result' in logs:
    events = logs['result']
    print(f"Found {len(events)} total events")
    
    # Collect unique event signatures
    event_sigs = {}
    for event in events:
        sig = event['topics'][0] if event['topics'] else 'no_topic'
        event_sigs[sig] = event_sigs.get(sig, 0) + 1
    
    print("\nEvent signatures found:")
    for sig, count in event_sigs.items():
        print(f"  {sig[:20]}... : {count} events")
else:
    print(f"Error: {logs.get('error')}")

# Also check new Mavis Market contract at 0xfff9ce5f71ca6178d3beecedb61e7eff1602950e
print("\n\nChecking Mavis Market contract...")
MAVIS_MARKET = "0xfff9ce5f71ca6178d3beecedb61e7eff1602950e"

logs2 = rpc_call("eth_getLogs", [{
    "address": MAVIS_MARKET,
    "fromBlock": from_block,
    "toBlock": to_block
}])

if 'result' in logs2:
    events2 = logs2['result']
    print(f"Found {len(events2)} total events in Mavis Market")
else:
    print(f"Error: {logs2.get('error')}")

# Try Ronin Market contract (might be different)
print("\n\nChecking possible alternate addresses...")
POSSIBLE_ADDRS = [
    "0xeea1ec66d0c04c1faabd1dbc6a0ea0a7c2aaf843",  # Possible new marketplace
    "0x7d0556d55ca1a92708681e2e231733ebd922597d",  # Another marketplace variant
]

for addr in POSSIBLE_ADDRS:
    logs3 = rpc_call("eth_getLogs", [{
        "address": addr,
        "fromBlock": from_block,
        "toBlock": to_block
    }])
    if 'result' in logs3:
        print(f"{addr[:15]}...: {len(logs3['result'])} events")

