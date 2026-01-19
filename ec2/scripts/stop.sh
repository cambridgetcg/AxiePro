#!/bin/bash
# Stop EC2 instance (saves money when not in use)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

if [ -z "$EC2_INSTANCE_ID" ] || [ "$EC2_INSTANCE_ID" == '""' ]; then
    echo "Error: EC2_INSTANCE_ID not set. No instance to stop."
    exit 1
fi

echo "=== Stopping EC2 Instance ==="
echo "Instance: $EC2_INSTANCE_ID"

# Check for running jobs
if [ -n "$EC2_PUBLIC_IP" ] && [ "$EC2_PUBLIC_IP" != '""' ]; then
    RUNNING=$(ssh -i $EC2_KEY_PATH -o StrictHostKeyChecking=no -o ConnectTimeout=5 ec2-user@$EC2_PUBLIC_IP \
        "pgrep -f 'python3.*fetch' 2>/dev/null || echo ''" 2>/dev/null || echo "")

    if [ -n "$RUNNING" ]; then
        echo ""
        echo "WARNING: Jobs still running (PIDs: $RUNNING)"
        read -p "Stop anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Cancelled."
            exit 0
        fi
    fi
fi

aws ec2 stop-instances --instance-ids $EC2_INSTANCE_ID --region $AWS_REGION > /dev/null
echo "Stopping... (billing stops when instance is stopped)"
echo ""
echo "To restart: ./ec2/scripts/launch.sh"
