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

# Test activityLog
query_api('{"query":"{ activityLog(from:0,size:5) { total results { axieId action price timestamp } } }"}', "Activity Log")

# Test axieActivities  
query_api('{"query":"{ axieActivities(axieId:\\"12345\\",from:0,size:5) { total results { action price timestamp } } }"}', "Axie Activities")

# Test tokenTransfers
query_api('{"query":"{ tokenTransfers(from:0,size:5) { total results { tokenId price from to timestamp } } }"}', "Token Transfers")

# Try marketplace analytics
query_api('{"query":"{ marketplaceStats { axies { totalListed totalSold floorPrice averagePrice volume24h } } }"}', "Marketplace Stats")

# Try order history
query_api('{"query":"{ orderHistory(from:0,size:5) { total results { axieId price settledAt buyer seller } } }"}', "Order History")

# Test specific axie's history  
query_api('{"query":"{ axie(axieId:\\"12345\\") { id class ownerHistory { address timestamp } } }"}', "Axie Owner History")

# Check what's in settledAuctions children
query_api('{"query":"{ settledAuctions { axies(from:0,size:1) { results { id } } lands(from:0,size:1) { results { tokenId } } items(from:0,size:1) { results { tokenId } } } }"}', "Settled Auctions All Types")

