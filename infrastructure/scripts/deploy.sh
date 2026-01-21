#!/bin/bash
# AxiePro Infrastructure Deployment Script
# Usage: ./scripts/deploy.sh [environment] [stack]
# Examples:
#   ./scripts/deploy.sh development
#   ./scripts/deploy.sh staging
#   ./scripts/deploy.sh production
#   ./scripts/deploy.sh development Networking

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT=${1:-development}
STACK=${2:-""}

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
    echo -e "${RED}Error: Invalid environment '$ENVIRONMENT'${NC}"
    echo "Valid environments: development, staging, production"
    exit 1
fi

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}   AxiePro Infrastructure Deployment${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo -e "Environment: ${GREEN}$ENVIRONMENT${NC}"
echo -e "Stack:       ${GREEN}${STACK:-All stacks}${NC}"
echo ""

# Check if AWS credentials are configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo -e "${RED}Error: AWS credentials not configured${NC}"
    echo "Please run 'aws configure' or set AWS environment variables"
    exit 1
fi

# Get AWS account info
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region || echo "us-east-1")
echo -e "AWS Account: ${YELLOW}$AWS_ACCOUNT${NC}"
echo -e "AWS Region:  ${YELLOW}$AWS_REGION${NC}"
echo ""

# Navigate to infrastructure directory
cd "$(dirname "$0")/.."

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    npm install
fi

# Build TypeScript
echo -e "${YELLOW}Building TypeScript...${NC}"
npm run build

# Bootstrap CDK if needed (first-time setup)
if [ "$ENVIRONMENT" == "development" ] || [ ! -z "$BOOTSTRAP" ]; then
    echo -e "${YELLOW}Checking CDK bootstrap status...${NC}"
    if ! aws cloudformation describe-stacks --stack-name CDKToolkit > /dev/null 2>&1; then
        echo -e "${YELLOW}Bootstrapping CDK...${NC}"
        npx cdk bootstrap aws://$AWS_ACCOUNT/$AWS_REGION
    fi
fi

# Show diff first
echo ""
echo -e "${YELLOW}Showing changes (cdk diff)...${NC}"
echo ""

if [ -z "$STACK" ]; then
    npx cdk diff --all -c environment=$ENVIRONMENT || true
else
    npx cdk diff "AxiePro-$STACK-*" -c environment=$ENVIRONMENT || true
fi

# Confirm deployment for staging/production
if [[ "$ENVIRONMENT" =~ ^(staging|production)$ ]]; then
    echo ""
    echo -e "${RED}⚠️  WARNING: Deploying to $ENVIRONMENT environment${NC}"
    read -p "Are you sure you want to proceed? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "Deployment cancelled."
        exit 0
    fi
fi

# Deploy
echo ""
echo -e "${GREEN}Deploying infrastructure...${NC}"
echo ""

APPROVAL_FLAG="--require-approval never"
if [[ "$ENVIRONMENT" =~ ^(staging|production)$ ]]; then
    APPROVAL_FLAG="--require-approval broadening"
fi

if [ -z "$STACK" ]; then
    npx cdk deploy --all -c environment=$ENVIRONMENT $APPROVAL_FLAG
else
    npx cdk deploy "AxiePro-$STACK-*" -c environment=$ENVIRONMENT $APPROVAL_FLAG
fi

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}   Deployment Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

# Show outputs
echo -e "${BLUE}Stack Outputs:${NC}"
aws cloudformation describe-stacks \
    --query "Stacks[?contains(StackName, 'AxiePro')].{Name:StackName,Status:StackStatus}" \
    --output table
