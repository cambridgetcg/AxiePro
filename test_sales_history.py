import json
import subprocess
import urllib.request

# Get API key
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

# Test 1: settledAuctions with more fields
query_api('{"query":"{ settledAuctions { axies(from:0,size:3,sort:Latest) { total results { id class transferHistory { timestamp txHash withPrice withPriceUsd from to } } } } }"}', "Settled Auctions with transferHistory")

# Test 2: Try exchangeRate for context
query_api('{"query":"{ exchangeRate { eth { usd } ron { usd } axs { usd } slp { usd } } }"}', "Exchange Rates")

# Test 3: Activity/history endpoints
query_api('{"query":"{ recentlyAxiesSold(from:0,size:3) { total results { id class order { currentPriceUsd } } } }"}', "recentlyAxiesSold")

# Test 4: Auction history on specific axie
query_api('{"query":"{ axie(axieId:\\"12345\\") { id class battleInfo { banned level } auction { startingPrice endingPrice startingTimestamp endingTimestamp currentPrice currentPriceUSD } } }"}', "Axie Auction Info")

# Test 5: Try sales endpoint
query_api('{"query":"{ sales(from:0,size:3) { total results { axieId price timestamp } } }"}', "Sales Query")

