#!/bin/bash
# Backend Deployment Script for AWS App Runner
# Usage: ./scripts/deploy-apprunner.sh
#
# Prerequisites:
# - Docker installed
# - AWS CLI configured with appropriate credentials
# - Logged into ECR: aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 034362054546.dkr.ecr.us-east-1.amazonaws.com

set -e

REGION="us-east-1"
ACCOUNT_ID="034362054546"
ECR_REPO="axiepro-backend"
SERVICE_NAME="axiepro-api"
IMAGE_TAG="latest"

ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO}"

echo "=========================================="
echo "AxiePro Backend Deployment"
echo "=========================================="
echo "Region: ${REGION}"
echo "ECR Repository: ${ECR_URI}"
echo "Service: ${SERVICE_NAME}"
echo "=========================================="

# Step 1: Login to ECR
echo ""
echo "Step 1: Logging into ECR..."
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ECR_URI}

# Step 2: Build Docker image for amd64 (App Runner runs on x86_64)
echo ""
echo "Step 2: Building Docker image for amd64..."
cd "$(dirname "$0")/.."
docker build --platform linux/amd64 -t ${ECR_REPO}:${IMAGE_TAG} .

# Step 3: Tag and push to ECR
echo ""
echo "Step 3: Tagging and pushing to ECR..."
docker tag ${ECR_REPO}:${IMAGE_TAG} ${ECR_URI}:${IMAGE_TAG}
docker push ${ECR_URI}:${IMAGE_TAG}

# Step 4: Trigger App Runner deployment
echo ""
echo "Step 4: Triggering App Runner deployment..."
SERVICE_ARN=$(aws apprunner list-services --region ${REGION} \
    --query "ServiceSummaryList[?ServiceName=='${SERVICE_NAME}'].ServiceArn" \
    --output text)

if [ -z "$SERVICE_ARN" ]; then
    echo "Error: App Runner service '${SERVICE_NAME}' not found"
    exit 1
fi

echo "Service ARN: ${SERVICE_ARN}"

aws apprunner start-deployment --service-arn ${SERVICE_ARN} --region ${REGION}

# Step 5: Wait for deployment
echo ""
echo "Step 5: Waiting for deployment to complete..."
echo "This may take 2-5 minutes..."

while true; do
    STATUS=$(aws apprunner describe-service --service-arn ${SERVICE_ARN} --region ${REGION} \
        --query "Service.Status" --output text)

    echo "Status: ${STATUS}"

    if [ "$STATUS" = "RUNNING" ]; then
        echo ""
        echo "Deployment complete!"
        break
    elif [ "$STATUS" = "CREATE_FAILED" ] || [ "$STATUS" = "DELETE_FAILED" ] || [ "$STATUS" = "UPDATE_FAILED" ]; then
        echo ""
        echo "Deployment failed with status: ${STATUS}"
        exit 1
    fi

    sleep 10
done

# Step 6: Verify health
echo ""
echo "Step 6: Verifying health endpoint..."
SERVICE_URL=$(aws apprunner describe-service --service-arn ${SERVICE_ARN} --region ${REGION} \
    --query "Service.ServiceUrl" --output text)

echo "Service URL: https://${SERVICE_URL}"

sleep 5
curl -s "https://${SERVICE_URL}/health"
echo ""

echo ""
echo "=========================================="
echo "Deployment complete!"
echo "API URL: https://api.axiepro.io"
echo "=========================================="
