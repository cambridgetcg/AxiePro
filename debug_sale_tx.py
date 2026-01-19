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

# Get a recent Axie transfer and examine the full transaction
block_result = rpc_call("eth_blockNumber", [])
current_block = int(block_result['result'], 16)

AXIE_CONTRACT = "0x32950db2a7164ae833121501c797d79e7b79d74c"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

logs = rpc_call("eth_getLogs", [{
    "address": AXIE_CONTRACT,
    "topics": [TRANSFER_TOPIC],
    "fromBlock": hex(current_block - 100),
    "toBlock": hex(current_block)
}])

if 'result' in logs and logs['result']:
    # Get first transfer
    tx_hash = logs['result'][0]['transactionHash']
    print(f"Examining transaction: {tx_hash}\n")
    
    # Get full transaction
    tx = rpc_call("eth_getTransactionByHash", [tx_hash])
    if 'result' in tx and tx['result']:
        t = tx['result']
        value_wei = int(t['value'], 16)
        value_ron = value_wei / 10**18
        print(f"TX Value (native RON): {value_ron:.6f} RON (${value_ron * 0.169:.2f} USD)")
        print(f"From: {t['from']}")
        print(f"To: {t['to']}")
        print(f"Gas Price: {int(t['gasPrice'], 16) / 10**9:.2f} gwei")
    
    # Get receipt for all logs
    receipt = rpc_call("eth_getTransactionReceipt", [tx_hash])
    if 'result' in receipt and receipt['result']:
        r = receipt['result']
        print(f"\nLogs in this transaction: {len(r['logs'])}")
        
        for i, log in enumerate(r['logs']):
            print(f"\n--- Log {i+1} ---")
            print(f"Contract: {log['address']}")
            sig = log['topics'][0][:20] + "..." if log['topics'] else "none"
            print(f"Event sig: {sig}")
            
            # Identify known contracts
            addr = log['address'].lower()
            if addr == AXIE_CONTRACT.lower():
                print("  -> AXIE NFT Transfer")
                if len(log['topics']) >= 4:
                    axie_id = int(log['topics'][3], 16)
                    print(f"  -> Axie ID: {axie_id}")
            elif addr == "0xe514d9deb7966c8be0ca922de8a064264ea6bcd4":
                print("  -> WETH Transfer")
            elif addr == "0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5":
                print("  -> WRON Transfer")
            
            # Show data if ERC20 transfer
            if log['topics'] and log['topics'][0] == TRANSFER_TOPIC:
                if len(log['topics']) == 3 and log['data'] != '0x':
                    value = int(log['data'], 16) / 10**18
                    print(f"  -> Amount: {value:.6f}")

