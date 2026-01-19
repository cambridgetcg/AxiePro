#!/bin/bash
# Run a fetch job on EC2
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

if [ -z "$EC2_PUBLIC_IP" ] || [ "$EC2_PUBLIC_IP" == '""' ]; then
    echo "Error: EC2_PUBLIC_IP not set. Run ./ec2/scripts/launch.sh first"
    exit 1
fi

SCRIPT_NAME="${1:-fetch_june2025_parallel.py}"
LOG_FILE="${SCRIPT_NAME%.py}.log"

echo "=== Running Job on EC2 ==="
echo "Script: $SCRIPT_NAME"
echo "Log: $LOG_FILE"
echo ""

# Check if script exists
ssh -i $EC2_KEY_PATH -o StrictHostKeyChecking=no ec2-user@$EC2_PUBLIC_IP \
    "test -f $REMOTE_DIR/$SCRIPT_NAME" || {
    echo "Error: $SCRIPT_NAME not found on EC2. Run deploy.sh first."
    exit 1
}

# Check if already running
RUNNING=$(ssh -i $EC2_KEY_PATH -o StrictHostKeyChecking=no ec2-user@$EC2_PUBLIC_IP \
    "pgrep -f '$SCRIPT_NAME' 2>/dev/null || echo ''")

if [ -n "$RUNNING" ]; then
    echo "Job already running (PID: $RUNNING)"
    echo "Use check-job.sh to monitor progress"
    exit 0
fi

# Start the job with nohup
echo "Starting job..."
ssh -i $EC2_KEY_PATH -o StrictHostKeyChecking=no ec2-user@$EC2_PUBLIC_IP \
    "cd $REMOTE_DIR && nohup python3 -u $SCRIPT_NAME > $LOG_FILE 2>&1 &"

sleep 2

# Verify it started
PID=$(ssh -i $EC2_KEY_PATH -o StrictHostKeyChecking=no ec2-user@$EC2_PUBLIC_IP \
    "pgrep -f '$SCRIPT_NAME' 2>/dev/null || echo ''")

if [ -n "$PID" ]; then
    echo ""
    echo "=== Job Started ==="
    echo "PID: $PID"
    echo "Log: $REMOTE_DIR/$LOG_FILE"
    echo ""
    echo "Monitor with: ./ec2/scripts/check-job.sh"
    echo "SSH to EC2:   ./ec2/scripts/ssh.sh"
else
    echo "Error: Job failed to start. Check logs:"
    ssh -i $EC2_KEY_PATH -o StrictHostKeyChecking=no ec2-user@$EC2_PUBLIC_IP \
        "tail -20 $REMOTE_DIR/$LOG_FILE 2>/dev/null || echo 'No log file'"
fi
