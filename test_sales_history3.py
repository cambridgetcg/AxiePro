import json
import subprocess
import urllib.request

result = subprocess.run(['aws', 'secretsmanager', 'get-secret-value', '--secret-id', 'axie-explorer/api-keys', '--query', 'SecretString', '--output', 'text'], capture_output=True, text=True)
secrets = json.loads(result.stdout)
api_key = secrets.get('SKYMAVIS_API_KEY', '')

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

# Settled auctions without sort
query_api('{"query":"{ settledAuctions { axies(from:0,size:5) { total results { id name class breedCount } } } }"}', "Settled Auctions Basic")

# Try to get sale price from settled auction
query_api('{"query":"{ settledAuctions { axies(from:0,size:3) { results { id class settledAt seller buyer realPrice } } } }"}', "Settled with Price Fields")

# Try token transfers for sales via different endpoint
query_api('{"query":"{ settledAuctions { axies(from:0,size:3) { results { id transferRecords { txHash from to withPrice withPriceUsd } } } } }"}', "Settled with Transfer Records")

