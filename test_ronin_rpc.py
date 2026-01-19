import json
import subprocess
import urllib.request

result = subprocess.run(['aws', 'secretsmanager', 'get-secret-value', '--secret-id', 'axie-explorer/api-keys', '--query', 'SecretString', '--output', 'text'], capture_output=True, text=True)
secrets = json.loads(result.stdout)
api_key = secrets.get('SKYMAVIS_API_KEY', '')
goldrush_key = secrets.get('GOLDRUSH_API_KEY', '')

# Try Sky Mavis RPC endpoint to get marketplace events
rpc_url = 'https://api-gateway.skymavis.com/rpc'
headers = {'X-API-Key': api_key, 'Content-Type': 'application/json'}

# Axie Marketplace contract address (old): 0x213073989821f738a7ba3520c3d31a1f9ad31bbd
# Try to get recent logs from marketplace

def try_request(url, data, headers, label):
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method='POST')
        response = urllib.request.urlopen(req, timeout=30)
        result = json.loads(response.read())
        print(f"\n=== {label} ===")
        print(json.dumps(result, indent=2)[:2000])
        return result
    except Exception as e:
        print(f"\n=== {label} === FAILED: {e}")
        return None

# Test RPC endpoint
try_request(rpc_url, {
    "jsonrpc": "2.0",
    "method": "eth_blockNumber",
    "params": [],
    "id": 1
}, headers, "Ronin RPC Block Number")

# Try to get logs from marketplace
try_request(rpc_url, {
    "jsonrpc": "2.0",
    "method": "eth_getLogs",
    "params": [{
        "address": "0x213073989821f738a7ba3520c3d31a1f9ad31bbd",
        "fromBlock": "latest",
        "toBlock": "latest"
    }],
    "id": 1
}, headers, "Marketplace Logs (latest block)")

# Try Goldrush transaction decode
import base64
auth = base64.b64encode(f"{goldrush_key}:".encode()).decode()
gr_headers = {'Authorization': f'Basic {auth}'}

try:
    # Get a sample axie transfer tx
    url = "https://api.covalenthq.com/v1/axie-mainnet/transaction_v2/0x1234/?no-logs=false"
    req = urllib.request.Request(url, headers=gr_headers)
    response = urllib.request.urlopen(req, timeout=30)
    print("\n=== Goldrush TX decode available ===")
except Exception as e:
    print(f"\nGoldrush TX decode: {type(e).__name__}")

# Try public Ronin API
try:
    url = "https://api.roninchain.com/api"
    req = urllib.request.Request(url, headers={'Content-Type': 'application/json'})
    response = urllib.request.urlopen(req, timeout=10)
    data = json.loads(response.read())
    print(f"\n=== Public Ronin API ===")
    print(json.dumps(data, indent=2)[:500])
except Exception as e:
    print(f"\nPublic Ronin API: {e}")

