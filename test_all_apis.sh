#!/bin/bash

# Get API keys
GOLDRUSH_KEY=$(aws secretsmanager get-secret-value --secret-id axie-explorer/api-keys --query SecretString --output text | python3 -c "import sys,json; print(json.load(sys.stdin).get('GOLDRUSH_API_KEY',''))")
SKYMAVIS_KEY=$(aws secretsmanager get-secret-value --secret-id axie-explorer/api-keys --query SecretString --output text | python3 -c "import sys,json; print(json.load(sys.stdin).get('SKYMAVIS_API_KEY',''))")

echo "============================================"
echo "SKY MAVIS API CAPABILITIES"
echo "============================================"

echo ""
echo "--- Marketplace: Total Listings ---"
curl -s "https://api-gateway.skymavis.com/graphql/marketplace" \
  -H "X-API-Key: $SKYMAVIS_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ axies(from:0,size:1,auctionType:Sale) { total } }"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"Total Axies for Sale: {d['data']['axies']['total']:,}\")"

echo ""
echo "--- Marketplace: Floor Price (Cheapest Axie) ---"
curl -s "https://api-gateway.skymavis.com/graphql/marketplace" \
  -H "X-API-Key: $SKYMAVIS_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ axies(from:0,size:1,sort:PriceAsc,auctionType:Sale) { results { id class order { currentPriceUsd } } } }"}' | python3 -c "import sys,json; d=json.load(sys.stdin); a=d['data']['axies']['results'][0]; print(f\"Floor: \${a['order']['currentPriceUsd']} ({a['class']})\")"

echo ""
echo "--- Single Axie Detail Fields ---"
curl -s "https://api-gateway.skymavis.com/graphql/marketplace" \
  -H "X-API-Key: $SKYMAVIS_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ axie(axieId:\"12345\") { id name class breedCount genes image stats{hp speed skill morale} parts{id name class type specialGenes} birthDate owner } }"}' | python3 -c "import sys,json; d=json.load(sys.stdin)['data']['axie']; print(f\"Available fields: {list(d.keys())}\")"

echo ""
echo "--- Origins API: Items ---"
curl -s "https://api-gateway.skymavis.com/origins/v2/community/items?limit=1" \
  -H "X-API-Key: $SKYMAVIS_KEY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"Origins Items available: {len(d.get('_items',[]))} items returned\")"

echo ""
echo "--- Origins API: Cards ---"
curl -s "https://api-gateway.skymavis.com/origins/v2/community/cards?limit=1" \
  -H "X-API-Key: $SKYMAVIS_KEY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"Origins Cards available: {'Yes' if d.get('_items') else 'No'}\")"

echo ""
echo "============================================"
echo "GOLDRUSH (COVALENT) API CAPABILITIES"
echo "============================================"

echo ""
echo "--- Token Balances ---"
curl -s "https://api.covalenthq.com/v1/axie-mainnet/address/0xb58ac3036d70b053760190cd82c46a0fee728d26/balances_v2/" \
  -u "$GOLDRUSH_KEY:" | python3 -c "import sys,json; d=json.load(sys.stdin); items=d.get('data',{}).get('items',[]); print(f\"Token types found: {len(items)}\")"

echo ""
echo "--- Transaction History ---"
curl -s "https://api.covalenthq.com/v1/axie-mainnet/address/0xb58ac3036d70b053760190cd82c46a0fee728d26/transactions_v3/?page-size=1" \
  -u "$GOLDRUSH_KEY:" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"Transaction history: {'Available' if d.get('data',{}).get('items') else 'Not available'}\")"

echo ""
echo "--- NFT Balances ---"
curl -s "https://api.covalenthq.com/v1/axie-mainnet/address/0xb58ac3036d70b053760190cd82c46a0fee728d26/balances_nft/" \
  -u "$GOLDRUSH_KEY:" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"NFT balances: {'Available' if d.get('data',{}).get('items') else 'Not available'}\")"

echo ""
echo "============================================"
echo "DATABASE TABLES (cardforum RDS)"
echo "============================================"
