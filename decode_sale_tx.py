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

# Get transaction receipt for a sample Axie transfer
sample_tx = "0x19f71dff47d740c8e069724ceef193af1d6110f31ac37d31cfdaf1c80fe6e09a"  # From transfer 2

print(f"Getting transaction receipt for: {sample_tx[:30]}...")

receipt = rpc_call("eth_getTransactionReceipt", [sample_tx])

if 'result' in receipt and receipt['result']:
    r = receipt['result']
    print(f"\nTransaction Status: {'Success' if r['status'] == '0x1' else 'Failed'}")
    print(f"Gas Used: {int(r['gasUsed'], 16)}")
    print(f"Logs count: {len(r['logs'])}")
    
    # Known event signatures
    EVENT_SIGS = {
        "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef": "Transfer (ERC20/721)",
        "0x0c0258cd7f0d9474f62106c6981c027ea54bee0b323ea1991f4caa7e288a5725": "AuctionSuccessful",
        "0x9b1bfa7fa9ee420a16e124f794c35ac9f90472acc99140eb2f6447c714cad8eb": "OrdersMatched",
    }
    
    for i, log in enumerate(r['logs']):
        sig = log['topics'][0] if log['topics'] else 'no_topic'
        event_name = EVENT_SIGS.get(sig, f"Unknown ({sig[:20]}...)")
        
        print(f"\n--- Log {i+1}: {event_name} ---")
        print(f"  Contract: {log['address']}")
        print(f"  Topics: {len(log['topics'])}")
        
        # If it's a token transfer, decode price
        if sig == "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef":
            # Could be ERC20 (WETH payment) or ERC721 (Axie transfer)
            if len(log['topics']) == 3:
                # ERC20: Transfer(from, to, value in data)
                from_addr = '0x' + log['topics'][1][-40:]
                to_addr = '0x' + log['topics'][2][-40:]
                value = int(log['data'], 16) if log['data'] != '0x' else 0
                print(f"  ERC20 From: {from_addr[:15]}...")
                print(f"  ERC20 To: {to_addr[:15]}...")
                print(f"  Value: {value / 10**18:.6f}")
            elif len(log['topics']) == 4:
                # ERC721: Transfer(from, to, tokenId)
                token_id = int(log['topics'][3], 16)
                print(f"  NFT TokenID: {token_id}")
else:
    print(f"Error or empty receipt")

