import json
import subprocess
import urllib.request

result = subprocess.run(['aws', 'secretsmanager', 'get-secret-value', '--secret-id', 'axie-explorer/api-keys', '--query', 'SecretString', '--output', 'text'], capture_output=True, text=True)
secrets = json.loads(result.stdout)
api_key = secrets.get('SKYMAVIS_API_KEY', '')

headers = {'X-API-Key': api_key, 'Content-Type': 'application/json'}

# Test more detailed axie fields
query = '{"query":"{ axie(axieId:\\"12345\\") { id name class breedCount genes image birthDate owner stats{hp speed skill morale} parts{id name class type specialGenes} order{maker currentPrice currentPriceUsd startedAt endedAt basePrice endedPrice} } }"}'
req = urllib.request.Request('https://api-gateway.skymavis.com/graphql/marketplace', data=query.encode(), headers=headers)
response = urllib.request.urlopen(req)
data = json.loads(response.read())
print("=== Full Axie Data Fields ===")
print(json.dumps(data, indent=2))

# Test market stats
query2 = '{"query":"{ axies(from:0,size:3,sort:PriceAsc,auctionType:Sale,criteria:{classes:[Beast]}) { total results { id class breedCount genes stats{hp speed skill morale} parts{name class type} order{currentPriceUsd} } } }"}'
req2 = urllib.request.Request('https://api-gateway.skymavis.com/graphql/marketplace', data=query2.encode(), headers=headers)
response2 = urllib.request.urlopen(req2)
data2 = json.loads(response2.read())
print("\n=== Sample Beast Listings ===")
print(json.dumps(data2, indent=2))
