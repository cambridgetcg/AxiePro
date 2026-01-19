#!/bin/bash
SKYMAVIS_KEY=$(aws secretsmanager get-secret-value --secret-id axie-explorer/api-keys --query SecretString --output text | python3 -c "import sys,json; print(json.load(sys.stdin).get('SKYMAVIS_API_KEY',''))")

echo "=== Floor Prices by Class ==="
for CLASS in Beast Plant Aquatic Bird Bug Reptile Mech Dawn Dusk; do
  RESULT=$(curl -s "https://api-gateway.skymavis.com/graphql/marketplace" \
    -H "X-API-Key: $SKYMAVIS_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"query\":\"{ axies(from:0,size:1,sort:PriceAsc,auctionType:Sale,criteria:{classes:[$CLASS]}) { total results { order { currentPriceUsd } } } }\"}" 2>/dev/null)

  PRICE=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); r=d.get('data',{}).get('axies',{}).get('results',[]); print(f\"\${r[0]['order']['currentPriceUsd']:.2f}\" if r else 'N/A')" 2>/dev/null)
  TOTAL=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('axies',{}).get('total',0))" 2>/dev/null)
  printf "%-10s Floor: %-10s Listed: %s\n" "$CLASS" "$PRICE" "$TOTAL"
done

echo ""
echo "=== Breed Count Distribution (for sale) ==="
for BC in 0 1 2 3 4 5 6 7; do
  RESULT=$(curl -s "https://api-gateway.skymavis.com/graphql/marketplace" \
    -H "X-API-Key: $SKYMAVIS_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"query\":\"{ axies(from:0,size:1,auctionType:Sale,criteria:{breedCount:[$BC]}) { total } }\"}" 2>/dev/null)
  TOTAL=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('axies',{}).get('total',0))" 2>/dev/null)
  printf "Breed Count %d: %s listed\n" "$BC" "$TOTAL"
done

echo ""
echo "=== Parts Filter Test ==="
curl -s "https://api-gateway.skymavis.com/graphql/marketplace" \
  -H "X-API-Key: $SKYMAVIS_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ axies(from:0,size:1,sort:PriceAsc,auctionType:Sale,criteria:{parts:[\"mouth-nut-cracker\"]}) { total results { id class order { currentPriceUsd } } } }"}' | python3 -c "import sys,json; d=json.load(sys.stdin); a=d.get('data',{}).get('axies',{}); print(f\"Nut Cracker mouth: {a.get('total',0)} listed, Floor: \${a.get('results',[{}])[0].get('order',{}).get('currentPriceUsd','N/A')}\")"

echo ""
echo "=== Recently Sold Test ==="
curl -s "https://api-gateway.skymavis.com/graphql/marketplace" \
  -H "X-API-Key: $SKYMAVIS_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ settledAuctions { axies(from:0,size:3) { total results { id class } } } }"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"Settled auctions query: {d}\")" 2>&1 | head -5
