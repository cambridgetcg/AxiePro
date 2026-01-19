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

# AuctionSuccessful event topic
AUCTION_SUCCESSFUL_TOPIC = "0x0c0258cd7f0d9474f62106c6981c027ea54bee0b323ea1991f4caa7e288a5725"

# Search with topic filter - try larger range
from_block = hex(current_block - 500)
to_block = hex(current_block)

print(f"\nSearching for AuctionSuccessful events in blocks {current_block - 500} to {current_block}")

logs = rpc_call("eth_getLogs", [{
    "address": "0x213073989821f738a7ba3520c3d31a1f9ad31bbd",
    "topics": [AUCTION_SUCCESSFUL_TOPIC],
    "fromBlock": from_block,
    "toBlock": to_block
}])

if 'result' in logs:
    events = logs['result']
    print(f"Found {len(events)} AuctionSuccessful events")
    
    for i, event in enumerate(events[:10]):
        print(f"\n--- Sale {i+1} ---")
        print(f"  Block: {int(event['blockNumber'], 16)}")
        print(f"  TX: {event['transactionHash']}")
        
        # Decode topics (seller, buyer indexed)
        if len(event['topics']) >= 3:
            seller = '0x' + event['topics'][1][-40:]
            buyer = '0x' + event['topics'][2][-40:]
            print(f"  Seller: {seller}")
            print(f"  Buyer: {buyer}")
        
        # Decode data (listingIndex, token, totalPrice)
        data = event['data'][2:]  # Remove 0x
        if len(data) >= 192:  # 3 x 64 chars
            listing_index = int(data[0:64], 16)
            token_addr = '0x' + data[64:128][-40:]
            total_price = int(data[128:192], 16)
            
            # Price in readable format (assuming 18 decimals for WETH)
            price_readable = total_price / (10**18)
            print(f"  Listing Index: {listing_index}")
            print(f"  Payment Token: {token_addr}")
            print(f"  Total Price: {price_readable:.6f} (raw: {total_price})")
else:
    print(f"Error: {logs.get('error')}")

