#!/bin/bash
# Launch EC2 instance for Axie data fetching
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

echo "=== Launching EC2 Instance ==="
echo "Region: $AWS_REGION"
echo "Type: $EC2_INSTANCE_TYPE"
echo "AMI: $EC2_AMI"

# Check if instance already exists
EXISTING=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=axie-fetcher" "Name=instance-state-name,Values=running,stopped" \
    --query 'Reservations[0].Instances[0].InstanceId' \
    --output text --region $AWS_REGION 2>/dev/null || echo "None")

if [ "$EXISTING" != "None" ] && [ -n "$EXISTING" ]; then
    echo ""
    echo "Existing instance found: $EXISTING"

    STATE=$(aws ec2 describe-instances --instance-ids $EXISTING \
        --query 'Reservations[0].Instances[0].State.Name' --output text --region $AWS_REGION)

    if [ "$STATE" == "stopped" ]; then
        echo "Starting stopped instance..."
        aws ec2 start-instances --instance-ids $EXISTING --region $AWS_REGION > /dev/null
        echo "Waiting for instance to start..."
        aws ec2 wait instance-running --instance-ids $EXISTING --region $AWS_REGION
    fi

    EC2_INSTANCE_ID=$EXISTING
else
    # Launch new instance
    echo ""
    echo "Launching new instance..."

    EC2_INSTANCE_ID=$(aws ec2 run-instances \
        --image-id $EC2_AMI \
        --instance-type $EC2_INSTANCE_TYPE \
        --key-name $EC2_KEY_NAME \
        --security-group-ids $EC2_SECURITY_GROUP \
        --subnet-id $EC2_SUBNET \
        --iam-instance-profile Name=$EC2_IAM_ROLE \
        --user-data file://$SCRIPT_DIR/../setup/user-data.sh \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=axie-fetcher}]" \
        --query 'Instances[0].InstanceId' \
        --output text \
        --region $AWS_REGION)

    echo "Instance ID: $EC2_INSTANCE_ID"
    echo "Waiting for instance to be running..."
    aws ec2 wait instance-running --instance-ids $EC2_INSTANCE_ID --region $AWS_REGION
fi

# Get public IP
EC2_PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids $EC2_INSTANCE_ID \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text --region $AWS_REGION)

echo ""
echo "=== Instance Ready ==="
echo "Instance ID: $EC2_INSTANCE_ID"
echo "Public IP: $EC2_PUBLIC_IP"
echo ""
echo "SSH command:"
echo "  ssh -i $EC2_KEY_PATH ec2-user@$EC2_PUBLIC_IP"
echo ""

# Update config with instance details
sed -i '' "s/^export EC2_INSTANCE_ID=.*/export EC2_INSTANCE_ID=\"$EC2_INSTANCE_ID\"/" "$SCRIPT_DIR/../config.sh"
sed -i '' "s/^export EC2_PUBLIC_IP=.*/export EC2_PUBLIC_IP=\"$EC2_PUBLIC_IP\"/" "$SCRIPT_DIR/../config.sh"

echo "Waiting 60s for user-data script to complete..."
sleep 60

echo ""
echo "Testing SSH connection..."
ssh -i $EC2_KEY_PATH -o StrictHostKeyChecking=no -o ConnectTimeout=10 ec2-user@$EC2_PUBLIC_IP "echo 'SSH OK'" 2>/dev/null || {
    echo "SSH not ready yet, waiting 30s more..."
    sleep 30
}

echo ""
echo "=== Launch Complete ==="
echo "Run: ./ec2/scripts/deploy.sh   to deploy scripts"
echo "Run: ./ec2/scripts/ssh.sh      to connect"
