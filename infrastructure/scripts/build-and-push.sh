#!/bin/bash
# Build and push Docker image to ECR
# Run this script from the infrastructure directory

set -e

AWS_REGION="us-east-1"
AWS_ACCOUNT="034362054546"
ECR_REPO="axiepro-backend"
IMAGE_TAG="latest"
BACKEND_DIR="../backend"

echo "=== AxiePro Docker Build and Push ==="
echo "Region: $AWS_REGION"
echo "Repository: $ECR_REPO"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker Desktop."
    exit 1
fi

# Login to ECR
echo ""
echo "1. Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com

# Build the image
echo ""
echo "2. Building Docker image..."
cd $BACKEND_DIR
docker build -t $ECR_REPO:$IMAGE_TAG .

# Tag for ECR
echo ""
echo "3. Tagging image for ECR..."
docker tag $ECR_REPO:$IMAGE_TAG $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:$IMAGE_TAG

# Push to ECR
echo ""
echo "4. Pushing image to ECR..."
docker push $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:$IMAGE_TAG

echo ""
echo "=== Success! ==="
echo "Image pushed: $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:$IMAGE_TAG"
echo ""
echo "Next step: Run 'npx cdk deploy AxiePro-Compute-dev --require-approval never' from infrastructure/"
