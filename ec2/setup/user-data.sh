#!/bin/bash
# EC2 User Data Script - Axie Data Fetcher Setup
# This runs automatically on first boot

set -e

# Log everything
exec > >(tee /var/log/user-data.log) 2>&1
echo "=== Starting EC2 setup $(date) ==="

# Update system
dnf update -y

# Install Python and dependencies
dnf install -y python3 python3-pip postgresql15

# Install Python packages
pip3 install psycopg2-binary

# Create working directory
mkdir -p /home/ec2-user/axie
chown ec2-user:ec2-user /home/ec2-user/axie

# Create a simple test script to verify setup
cat > /home/ec2-user/axie/test_setup.py << 'EOF'
#!/usr/bin/env python3
"""Test EC2 setup - verify all dependencies work."""
import json
import subprocess
import urllib.request

print("=== EC2 Setup Test ===")

# Test 1: AWS CLI + Secrets Manager
print("\n1. Testing AWS Secrets Manager access...")
try:
    result = subprocess.run(
        ['aws', 'secretsmanager', 'get-secret-value',
         '--secret-id', 'axie-explorer/api-keys',
         '--query', 'SecretString', '--output', 'text',
         '--region', 'us-east-1'],
        capture_output=True, text=True, check=True
    )
    secrets = json.loads(result.stdout)
    print(f"   OK - Found {len(secrets)} keys")
except Exception as e:
    print(f"   FAIL - {e}")

# Test 2: PostgreSQL connection
print("\n2. Testing PostgreSQL connection...")
try:
    import psycopg2
    conn = psycopg2.connect(
        host='cardforum.cn4c2su0o42n.us-east-1.rds.amazonaws.com',
        port=5432, dbname='postgres', user='postgres', password='12345Cardforum'
    )
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM axie.axie_sales")
    count = cur.fetchone()[0]
    conn.close()
    print(f"   OK - {count} sales in database")
except Exception as e:
    print(f"   FAIL - {e}")

# Test 3: Sky Mavis API
print("\n3. Testing Sky Mavis API...")
try:
    result = subprocess.run(
        ['aws', 'secretsmanager', 'get-secret-value',
         '--secret-id', 'axie-explorer/api-keys',
         '--query', 'SecretString', '--output', 'text',
         '--region', 'us-east-1'],
        capture_output=True, text=True, check=True
    )
    api_key = json.loads(result.stdout).get('SKYMAVIS_API_KEY', '')

    req = urllib.request.Request(
        'https://api-gateway.skymavis.com/rpc',
        data=json.dumps({"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}).encode(),
        headers={'X-API-Key': api_key, 'Content-Type': 'application/json'}
    )
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read())
    block = int(data['result'], 16)
    print(f"   OK - Current block: {block:,}")
except Exception as e:
    print(f"   FAIL - {e}")

print("\n=== Setup test complete ===")
EOF

chown ec2-user:ec2-user /home/ec2-user/axie/test_setup.py
chmod +x /home/ec2-user/axie/test_setup.py

echo "=== EC2 setup complete $(date) ==="
