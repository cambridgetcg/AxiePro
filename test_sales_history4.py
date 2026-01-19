import json
import subprocess
import urllib.request

result = subprocess.run(['aws', 'secretsmanager', 'get-secret-value', '--secret-id', 'axie-explorer/api-keys', '--query', 'SecretString', '--output', 'text'], capture_output=True, text=True)
secrets = json.loads(result.stdout)
api_key = secrets.get('SKYMAVIS_API_KEY', '')
goldrush_key = secrets.get('GOLDRUSH_API_KEY', '')

headers = {'X-API-Key': api_key, 'Content-Type': 'application/json'}
url = 'https://api-gateway.skymavis.com/graphql/marketplace'

def query_api(query_str, label):
    try:
        req = urllib.request.Request(url, data=query_str.encode(), headers=headers)
        response = urllib.request.urlopen(req)
        data = json.loads(response.read())
        print(f"\n=== {label} ===")
        print(json.dumps(data, indent=2))
        return data
    except urllib.error.HTTPError as e:
        print(f"\n=== {label} === FAILED: {e.code}")
        error_body = e.read().decode() if e.fp else ""
        if error_body:
            print(error_body[:500])
        return None

# Check if there's an activityLog or history on settledAuctions
query_api('{"query":"{ settledAuctions { total ethereum lands items axies(from:0,size:3) { results { id } } } }"}', "Settled Auctions Structure")

# Try erc721Transfers for marketplace contract
print("\n=== Checking Goldrush for Axie NFT Transfers ===")
# Axie contract: 0x32950db2a7164ae833121501c797d79e7b79d74c
import base64
auth = base64.b64encode(f"{goldrush_key}:".encode()).decode()
gr_headers = {'Authorization': f'Basic {auth}'}

try:
    # Get NFT transfers for Axie contract
    gr_url = "https://api.covalenthq.com/v1/axie-mainnet/tokens/0x32950db2a7164ae833121501c797d79e7b79d74c/nft_transactions/3271181/?page-size=5"
    req = urllib.request.Request(gr_url, headers=gr_headers)
    response = urllib.request.urlopen(req)
    data = json.loads(response.read())
    print(json.dumps(data, indent=2))
except Exception as e:
    print(f"Goldrush NFT transactions: {e}")

# Try marketplace events 
try:
    # Marketplace contract
    gr_url2 = "https://api.covalenthq.com/v1/axie-mainnet/events/address/0x213073989821f738a7ba3520c3d31a1f9ad31bbd/?page-size=3"
    req2 = urllib.request.Request(gr_url2, headers=gr_headers)
    response2 = urllib.request.urlopen(req2)
    data2 = json.loads(response2.read())
    print("\n=== Marketplace Contract Events ===")
    print(json.dumps(data2, indent=2)[:2000])
except Exception as e:
    print(f"Marketplace events: {e}")

