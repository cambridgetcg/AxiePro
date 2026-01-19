import json
import subprocess
import os

# Get API key
result = subprocess.run(['aws', 'secretsmanager', 'get-secret-value', '--secret-id', 'axie-explorer/api-keys', '--query', 'SecretString', '--output', 'text'], capture_output=True, text=True)
secrets = json.loads(result.stdout)
api_key = secrets.get('SKYMAVIS_API_KEY', '')

import urllib.request

headers = {
    'X-API-Key': api_key,
    'Content-Type': 'application/json'
}

# Test transfer history
query = '{"query":"{ axie(axieId:\\"12345\\") { id transferHistory { timestamp txHash withPrice } } }"}'
req = urllib.request.Request('https://api-gateway.skymavis.com/graphql/marketplace', data=query.encode(), headers=headers)
response = urllib.request.urlopen(req)
data = json.loads(response.read())
print("=== Transfer History for Axie #12345 ===")
print(json.dumps(data, indent=2))

# Test marketplace activity query
query2 = '{"query":"{ publicProfileWithRoninAddress(roninAddress:\\"0xb58ac3036d70b053760190cd82c46a0fee728d26\\") { name axies { total } } }"}'
req2 = urllib.request.Request('https://api-gateway.skymavis.com/graphql/marketplace', data=query2.encode(), headers=headers)
try:
    response2 = urllib.request.urlopen(req2)
    data2 = json.loads(response2.read())
    print("\n=== Profile/Wallet Query ===")
    print(json.dumps(data2, indent=2))
except Exception as e:
    print(f"\nProfile query: {e}")
