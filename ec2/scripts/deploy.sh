#!/bin/bash
# Deploy scripts to EC2 instance
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

if [ -z "$EC2_PUBLIC_IP" ] || [ "$EC2_PUBLIC_IP" == '""' ]; then
    echo "Error: EC2_PUBLIC_IP not set. Run ./ec2/scripts/launch.sh first"
    exit 1
fi

echo "=== Deploying to EC2 ==="
echo "Target: ec2-user@$EC2_PUBLIC_IP:$REMOTE_DIR"
echo ""

# Files to deploy
FILES=(
    "fetch_june2025_parallel.py"
    "fetch_june2025_premium.py"
    "fetch_premium_sales.py"
    "fetch_axie_metadata.py"
)

# Create remote directory
ssh -i $EC2_KEY_PATH -o StrictHostKeyChecking=no ec2-user@$EC2_PUBLIC_IP \
    "mkdir -p $REMOTE_DIR"

# Copy files
for file in "${FILES[@]}"; do
    if [ -f "$PROJECT_DIR/$file" ]; then
        echo "Copying $file..."
        scp -i $EC2_KEY_PATH -o StrictHostKeyChecking=no \
            "$PROJECT_DIR/$file" "ec2-user@$EC2_PUBLIC_IP:$REMOTE_DIR/"
    fi
done

# Copy database directory
if [ -d "$PROJECT_DIR/database" ]; then
    echo "Copying database/ directory..."
    scp -i $EC2_KEY_PATH -o StrictHostKeyChecking=no -r \
        "$PROJECT_DIR/database" "ec2-user@$EC2_PUBLIC_IP:$REMOTE_DIR/"
fi

echo ""
echo "=== Deploy Complete ==="
echo ""
echo "Files on EC2:"
ssh -i $EC2_KEY_PATH -o StrictHostKeyChecking=no ec2-user@$EC2_PUBLIC_IP \
    "ls -la $REMOTE_DIR/*.py 2>/dev/null || echo 'No .py files'"
