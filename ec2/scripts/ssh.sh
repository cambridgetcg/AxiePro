#!/bin/bash
# SSH to EC2 instance
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

if [ -z "$EC2_PUBLIC_IP" ] || [ "$EC2_PUBLIC_IP" == '""' ]; then
    echo "Error: EC2_PUBLIC_IP not set. Run ./ec2/scripts/launch.sh first"
    exit 1
fi

if [ -n "$1" ]; then
    # Run command
    ssh -i $EC2_KEY_PATH -o StrictHostKeyChecking=no ec2-user@$EC2_PUBLIC_IP "$@"
else
    # Interactive shell
    ssh -i $EC2_KEY_PATH -o StrictHostKeyChecking=no ec2-user@$EC2_PUBLIC_IP
fi
