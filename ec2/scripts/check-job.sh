#!/bin/bash
# Check job progress on EC2
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

if [ -z "$EC2_PUBLIC_IP" ] || [ "$EC2_PUBLIC_IP" == '""' ]; then
    echo "Error: EC2_PUBLIC_IP not set. Run ./ec2/scripts/launch.sh first"
    exit 1
fi

SCRIPT_NAME="${1:-fetch_june2025_parallel.py}"
LOG_FILE="${SCRIPT_NAME%.py}.log"

echo "=== EC2 Job Status ==="
echo "Instance: $EC2_PUBLIC_IP"
echo ""

# Check if process is running
PID=$(ssh -i $EC2_KEY_PATH -o StrictHostKeyChecking=no ec2-user@$EC2_PUBLIC_IP \
    "pgrep -f '$SCRIPT_NAME' 2>/dev/null || echo ''")

if [ -n "$PID" ]; then
    echo "Status: RUNNING (PID: $PID)"

    # Get CPU usage
    CPU=$(ssh -i $EC2_KEY_PATH -o StrictHostKeyChecking=no ec2-user@$EC2_PUBLIC_IP \
        "ps -p $PID -o %cpu --no-headers 2>/dev/null || echo '?'")
    echo "CPU: ${CPU}%"
else
    echo "Status: NOT RUNNING"
fi

echo ""
echo "=== Latest Log Output ==="
ssh -i $EC2_KEY_PATH -o StrictHostKeyChecking=no ec2-user@$EC2_PUBLIC_IP \
    "tail -15 $REMOTE_DIR/$LOG_FILE 2>/dev/null || echo 'No log file found'"

echo ""
echo "---"
echo "Full log: ./ec2/scripts/ssh.sh 'tail -f $REMOTE_DIR/$LOG_FILE'"
